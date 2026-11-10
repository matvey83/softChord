export interface Prepared {
  bind(...values: Array<string | number | null>): Prepared;
  first<T>(): Promise<T | null>;
  run(): Promise<{ changes: number }>;
}

export interface SqlDatabase {
  prepare(sql: string): Prepared;
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

type Bindable = {
  bind(...values: unknown[]): Bindable;
  first<T>(): Promise<T | null>;
  run(): Promise<{ meta?: { changes?: number } }>;
};

export function adaptDatabase(db: { prepare(sql: string): Bindable }): SqlDatabase {
  return {
    prepare(sql: string): Prepared {
      const wrap = (bound: Bindable): Prepared => ({
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
      });
      return wrap(db.prepare(sql));
    },
  };
}

export async function countRecentLoginTokens(
  db: SqlDatabase,
  email: string,
  since: number,
): Promise<number> {
  const row = await db
    .prepare("SELECT COUNT(*) AS n FROM login_tokens WHERE email = ? AND created_at > ?")
    .bind(email, since)
    .first<{ n: number }>();
  return Number(row?.n ?? 0);
}

export async function voidUnusedLoginTokens(
  db: SqlDatabase,
  email: string,
  consumedAt: number,
): Promise<void> {
  await db
    .prepare("UPDATE login_tokens SET consumed_at = ? WHERE email = ? AND consumed_at IS NULL")
    .bind(consumedAt, email)
    .run();
}

export async function insertLoginToken(
  db: SqlDatabase,
  row: {
    tokenHash: string;
    email: string;
    client: ClientKind;
    verifierHash: string;
    createdAt: number;
    expiresAt: number;
  },
): Promise<void> {
  await db
    .prepare(
      `INSERT INTO login_tokens
        (token_hash, email, client, verifier_hash, created_at, expires_at, consumed_at)
       VALUES (?, ?, ?, ?, ?, ?, NULL)`,
    )
    .bind(row.tokenHash, row.email, row.client, row.verifierHash, row.createdAt, row.expiresAt)
    .run();
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
