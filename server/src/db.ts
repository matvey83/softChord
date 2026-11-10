export interface Prepared {
  bind(...values: Array<string | number | null>): Prepared;
  first<T>(): Promise<T | null>;
  run(): Promise<{ changes: number }>;
}

export interface SqlDatabase {
  prepare(sql: string): Prepared;
  /** Runs the statements in one transaction. */
  batch(statements: Prepared[]): Promise<Array<{ changes: number }>>;
}

export type ClientKind = "web" | "ios" | "desktop";

export interface LoginTokenRow {
  email: string;
  client: ClientKind;
  verifier_hash: string;
}

export interface SessionRow {
  token_hash: string;
  user_id: string;
  created_at: number;
  last_used_at: number;
  client: ClientKind;
  device_label: string | null;
  email: string;
}

const d1Statement = Symbol("d1Statement");

type Tracked = Prepared & { [d1Statement]?: D1PreparedStatement };

export function adaptDatabase(db: D1Database): SqlDatabase {
  const wrap = (bound: D1PreparedStatement): Tracked => {
    const statement: Tracked = {
      bind(...values: Array<string | number | null>) {
        return wrap(bound.bind(...values));
      },
      async first<T>() {
        const row = await bound.first<T>();
        return row ?? null;
      },
      async run() {
        const result = await bound.run();
        return { changes: Number(result.meta?.changes ?? 0) };
      },
      [d1Statement]: bound,
    };
    return statement;
  };
  return {
    prepare(sql: string): Prepared {
      return wrap(db.prepare(sql));
    },
    async batch(statements: Prepared[]): Promise<Array<{ changes: number }>> {
      const bound = statements.map((statement) => {
        const inner = (statement as Tracked)[d1Statement];
        if (!inner) throw new Error("cannot batch this statement");
        return inner;
      });
      const results = await db.batch(bound);
      return results.map((result) => ({ changes: Number(result.meta?.changes ?? 0) }));
    },
  };
}

const ISSUE_TOKEN = `
INSERT INTO login_tokens
  (token_hash, email, email_key, client, verifier_hash, created_at, expires_at, consumed_at)
SELECT ?, ?, ?, ?, ?, ?, ?, NULL
WHERE (
  SELECT COUNT(*) FROM login_tokens
  WHERE email_key = ? AND created_at > ?
) < ?
`;

const VOID_OTHERS = `
UPDATE login_tokens
SET consumed_at = ?
WHERE email_key = ?
  AND consumed_at IS NULL
  AND token_hash != ?
  AND EXISTS (
    SELECT 1 FROM login_tokens AS issued WHERE issued.token_hash = ?
  )
`;

/** Inserts under the cap and voids older unused tokens for that key, in one transaction. */
export async function issueLoginToken(
  db: SqlDatabase,
  row: {
    tokenHash: string;
    email: string;
    emailKey: string;
    client: ClientKind;
    verifierHash: string;
    createdAt: number;
    expiresAt: number;
    since: number;
    limit: number;
  },
): Promise<boolean> {
  const [inserted] = await db.batch([
    db.prepare(ISSUE_TOKEN).bind(
      row.tokenHash,
      row.email,
      row.emailKey,
      row.client,
      row.verifierHash,
      row.createdAt,
      row.expiresAt,
      row.emailKey,
      row.since,
      row.limit,
    ),
    db.prepare(VOID_OTHERS).bind(row.createdAt, row.emailKey, row.tokenHash, row.tokenHash),
  ]);
  return inserted?.changes === 1;
}

export async function findLiveLoginToken(
  db: SqlDatabase,
  tokenHash: string,
  now: number,
): Promise<LoginTokenRow | null> {
  return db
    .prepare(
      `SELECT email, client, verifier_hash
       FROM login_tokens
       WHERE token_hash = ? AND consumed_at IS NULL AND expires_at > ?`,
    )
    .bind(tokenHash, now)
    .first<LoginTokenRow>();
}

export async function consumeLoginToken(
  db: SqlDatabase,
  tokenHash: string,
  now: number,
): Promise<boolean> {
  const result = await db
    .prepare(
      `UPDATE login_tokens
       SET consumed_at = ?
       WHERE token_hash = ? AND consumed_at IS NULL AND expires_at > ?`,
    )
    .bind(now, tokenHash, now)
    .run();
  return result.changes === 1;
}

export async function upsertUser(db: SqlDatabase, email: string, now: number): Promise<string> {
  const id = crypto.randomUUID();
  await db
    .prepare("INSERT INTO users (id, email, created_at) VALUES (?, ?, ?) ON CONFLICT (email) DO NOTHING")
    .bind(id, email, now)
    .run();
  const row = await db.prepare("SELECT id FROM users WHERE email = ?").bind(email).first<{ id: string }>();
  if (!row) throw new Error("user insert failed");
  return row.id;
}

export async function insertSession(
  db: SqlDatabase,
  row: {
    tokenHash: string;
    userId: string;
    createdAt: number;
    client: ClientKind;
    deviceLabel: string | null;
  },
): Promise<void> {
  await db
    .prepare(
      `INSERT INTO sessions
        (token_hash, user_id, created_at, last_used_at, client, device_label)
       VALUES (?, ?, ?, ?, ?, ?)`,
    )
    .bind(row.tokenHash, row.userId, row.createdAt, row.createdAt, row.client, row.deviceLabel)
    .run();
}

export async function findSession(db: SqlDatabase, tokenHash: string): Promise<SessionRow | null> {
  return db
    .prepare(
      `SELECT sessions.token_hash, sessions.user_id, sessions.created_at, sessions.last_used_at,
              sessions.client, sessions.device_label, users.email
       FROM sessions
       JOIN users ON users.id = sessions.user_id
       WHERE sessions.token_hash = ?`,
    )
    .bind(tokenHash)
    .first<SessionRow>();
}

export async function touchSession(db: SqlDatabase, tokenHash: string, now: number, staleAt: number): Promise<void> {
  await db
    .prepare("UPDATE sessions SET last_used_at = ? WHERE token_hash = ? AND last_used_at <= ?")
    .bind(now, tokenHash, staleAt)
    .run();
}

export async function deleteSession(db: SqlDatabase, tokenHash: string): Promise<void> {
  await db.prepare("DELETE FROM sessions WHERE token_hash = ?").bind(tokenHash).run();
}
