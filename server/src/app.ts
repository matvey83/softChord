import { Hono } from "hono";

import { clearCookie, hasForeignOrigin, originAllowed, readCookie, writeCookie } from "./cookies.ts";
import {
  assertRuntimeConfig,
  DEVICE_LABEL_MAX,
  EMAIL_LIMIT,
  EMAIL_WINDOW_SECONDS,
  LAST_USED_INTERVAL_SECONDS,
  LOGIN_TTL_SECONDS,
  SESSION_COOKIE_SECONDS,
  VERIFIER_COOKIE_SECONDS,
  type AppConfig,
} from "./config.ts";
import {
  consumeLoginToken,
  deleteSession,
  deleteUserSessions,
  findLiveLoginToken,
  findSession,
  insertSession,
  issueLoginToken,
  touchSession,
  upsertUser,
  type ClientKind,
  type SessionRow,
  type SqlDatabase,
} from "./db.ts";
import { canonicalEmail, maskEmail, normalizeEmail } from "./email.ts";
import { renderLoginPage } from "./login-page.ts";
import { assertMailerAllowed, type LoginMailer } from "./mailer.ts";
import { clientIp, type IpRateLimiter } from "./rate-limit.ts";
import { buildLoginUrl, hashesEqual, isVerifier, isVerifierHash, randomToken, sha256Hex } from "./tokens.ts";

export interface AppDeps {
  db: SqlDatabase;
  mailer: LoginMailer;
  ipLimiter: IpRateLimiter;
  env: AppConfig;
  now?: () => number;
  waitUntil: (promise: Promise<unknown>) => void;
}

interface RequestLinkBody {
  email: string;
  client: ClientKind;
  verifierHash: string;
  verifier: string | null;
}

interface VerifyBody {
  token: string;
  verifier: string | null;
  deviceLabel: string | null;
}

function nowSeconds(deps: AppDeps): number {
  return Math.floor((deps.now?.() ?? Date.now()) / 1000);
}

function isClient(value: unknown): value is ClientKind {
  return value === "web" || value === "ios" || value === "desktop";
}

function parseRequestLink(body: unknown): RequestLinkBody | null {
  if (!body || typeof body !== "object") return null;
  const record = body as Record<string, unknown>;
  const email = normalizeEmail(record.email);
  if (!email || !isClient(record.client)) return null;
  if (typeof record.verifier_hash !== "string" || !isVerifierHash(record.verifier_hash)) return null;
  if (record.verifier === undefined) {
    if (record.client === "web") return null;
    return { email, client: record.client, verifierHash: record.verifier_hash, verifier: null };
  }
  if (typeof record.verifier !== "string" || !isVerifier(record.verifier)) return null;
  if (record.client !== "web") return null;
  return { email, client: record.client, verifierHash: record.verifier_hash, verifier: record.verifier };
}

function parseVerify(body: unknown): VerifyBody | null {
  if (!body || typeof body !== "object") return null;
  const record = body as Record<string, unknown>;
  if (typeof record.token !== "string" || record.token.length === 0 || record.token.length > 200) return null;
  let verifier: string | null = null;
  if (record.verifier !== undefined && record.verifier !== null) {
    if (typeof record.verifier !== "string") return null;
    verifier = record.verifier;
  }
  if (record.device_label !== undefined && record.device_label !== null && typeof record.device_label !== "string") {
    return null;
  }
  let deviceLabel: string | null = null;
  if (typeof record.device_label === "string") {
    const trimmed = record.device_label.trim();
    deviceLabel = trimmed ? trimmed.slice(0, DEVICE_LABEL_MAX) : null;
  }
  return { token: record.token, verifier, deviceLabel };
}

function accepted(c: { json: (body: unknown, status?: number) => Response }): Response {
  return c.json({ ok: true });
}

function isJsonContentType(value: string | undefined): boolean {
  if (!value) return false;
  const mediaType = value.split(";", 1)[0]?.trim().toLowerCase();
  return mediaType === "application/json";
}

async function readJson(c: { req: { header: (name: string) => string | undefined; json: () => Promise<unknown> } }): Promise<unknown> {
  if (!isJsonContentType(c.req.header("content-type"))) return undefined;
  try {
    return await c.req.json();
  } catch {
    return undefined;
  }
}

function methodNotAllowed(c: { json: (body: unknown, status?: number) => Response }): Response {
  return c.json({ error: "method_not_allowed" }, 405);
}

async function privateHeaders(c: { res: { headers: Headers } }, next: () => Promise<void>): Promise<void> {
  await next();
  c.res.headers.set("cache-control", "no-store");
  c.res.headers.set("referrer-policy", "no-referrer");
}

export function createApp(deps: AppDeps): Hono {
  assertMailerAllowed(deps.env, deps.mailer);
  assertRuntimeConfig(deps.env);
  const app = new Hono();

  app.use("/login", async (c, next) => {
    await privateHeaders(c, next);
    c.res.headers.set("x-content-type-options", "nosniff");
  });
  app.use("/api/auth/request-link", privateHeaders);
  app.use("/api/auth/verify", privateHeaders);
  app.use("/api/me", privateHeaders);
  app.use("/api/auth/logout", privateHeaders);
  app.use("/api/auth/logout-all", privateHeaders);
  app.use("/api/*", async (c, next) => {
    if (c.req.method === "POST" && !isJsonContentType(c.req.header("content-type"))) {
      return c.json({ error: "invalid_request" }, 400);
    }
    await next();
  });

  app.post("/api/auth/request-link", async (c) => {
    const parsed = parseRequestLink(await readJson(c));
    if (!parsed) return c.json({ error: "invalid_request" }, 400);
    if (hasForeignOrigin(c.req.raw, deps.env.PUBLIC_ORIGIN)) {
      return c.json({ error: "forbidden" }, 403);
    }
    if (parsed.verifier) {
      const actual = await sha256Hex(parsed.verifier);
      if (!hashesEqual(actual, parsed.verifierHash)) return c.json({ error: "invalid_request" }, 400);
    }

    let allowed = false;
    try {
      allowed = await deps.ipLimiter.allow(clientIp(c.req.raw));
    } catch {
      allowed = false;
    }
    const now = nowSeconds(deps);
    if (!allowed) {
      console.log(JSON.stringify({ event: "login_link_suppressed", reason: "ip_cap" }));
      return accepted(c);
    }

    const token = randomToken();
    const tokenHash = await sha256Hex(token);
    const issued = await issueLoginToken(deps.db, {
      tokenHash,
      email: parsed.email,
      emailKey: canonicalEmail(parsed.email),
      client: parsed.client,
      verifierHash: parsed.verifierHash,
      createdAt: now,
      expiresAt: now + LOGIN_TTL_SECONDS,
      since: now - EMAIL_WINDOW_SECONDS,
      limit: EMAIL_LIMIT,
    });
    if (!issued) {
      console.log(JSON.stringify({ event: "login_link_suppressed", reason: "email_cap" }));
      return accepted(c);
    }
    const loginUrl = buildLoginUrl(deps.env.PUBLIC_ORIGIN, parsed.client, maskEmail(parsed.email), token);
    const sending = deps.mailer.sendLoginEmail({ to: parsed.email, loginUrl }).then(
      () => {
        console.log(JSON.stringify({ event: "login_email_recorded", client: parsed.client }));
      },
      () => {
        console.error(JSON.stringify({ event: "login_email_failed" }));
      },
    );
    deps.waitUntil(sending);
    if (parsed.verifier) {
      writeCookie(c, deps.env, deps.env.VERIFIER_COOKIE_NAME, parsed.verifier, VERIFIER_COOKIE_SECONDS);
    }
    console.log(JSON.stringify({ event: "login_link_issued", client: parsed.client }));
    return accepted(c);
  });

  app.get("/login", (c) => {
    const client = c.req.query("client");
    const hint = (c.req.query("hint") ?? "").trim().slice(0, 254);
    const nonce = crypto.randomUUID().replaceAll("-", "");
    c.header(
      "content-security-policy",
      `default-src 'none'; script-src 'nonce-${nonce}'; style-src 'unsafe-inline'; connect-src 'self'; form-action 'none'; base-uri 'none'; frame-ancestors 'none'`,
    );
    return c.html(renderLoginPage(isClient(client) ? client : null, hint, nonce, deps.env.APP_URL));
  });

  app.post("/api/auth/verify", async (c) => {
    const parsed = parseVerify(await readJson(c));
    if (!parsed) return c.json({ error: "invalid_or_expired" }, 400);
    const now = nowSeconds(deps);
    const tokenHash = await sha256Hex(parsed.token);
    const row = await findLiveLoginToken(deps.db, tokenHash, now);
    if (!row) return c.json({ error: "invalid_or_expired" }, 400);

    const verifier = row.client === "web"
      ? readCookie(c, deps.env.VERIFIER_COOKIE_NAME) ?? null
      : parsed.verifier;
    if (!verifier || !isVerifier(verifier)) return c.json({ error: "invalid_or_expired" }, 400);
    const verifierHash = await sha256Hex(verifier);
    if (!hashesEqual(verifierHash, row.verifier_hash)) {
      return c.json({ error: "invalid_or_expired" }, 400);
    }
    if (row.client === "web" && !originAllowed(c.req.raw, deps.env.PUBLIC_ORIGIN)) {
      return c.json({ error: "forbidden" }, 403);
    }

    const consumed = await consumeLoginToken(deps.db, tokenHash, now);
    if (!consumed) return c.json({ error: "invalid_or_expired" }, 400);
    if (row.client === "web") {
      const existing = readCookie(c, deps.env.SESSION_COOKIE_NAME);
      if (existing) await deleteSession(deps.db, await sha256Hex(existing));
    }
    const userId = await upsertUser(deps.db, row.email, now);
    const sessionToken = randomToken();
    const sessionHash = await sha256Hex(sessionToken);
    await insertSession(deps.db, {
      tokenHash: sessionHash,
      userId,
      createdAt: now,
      client: row.client,
      deviceLabel: parsed.deviceLabel,
    });
    if (row.client === "web") {
      writeCookie(c, deps.env, deps.env.SESSION_COOKIE_NAME, sessionToken, SESSION_COOKIE_SECONDS);
      clearCookie(c, deps.env, deps.env.VERIFIER_COOKIE_NAME);
      return c.json({ email: row.email });
    }
    return c.json({ email: row.email, token: sessionToken });
  });

  app.get("/api/me", async (c) => {
    const found = await authenticate(c, deps);
    if (!found) return c.json({ error: "unauthorized" }, 401);
    const now = nowSeconds(deps);
    await touchSession(deps.db, found.session.token_hash, now, now - LAST_USED_INTERVAL_SECONDS);
    return c.json({ email: found.session.email });
  });

  app.post("/api/auth/logout", async (c) => {
    const found = await authenticate(c, deps);
    if (!found) return c.json({ error: "unauthorized" }, 401);
    if (found.via === "cookie" && !originAllowed(c.req.raw, deps.env.PUBLIC_ORIGIN)) {
      return c.json({ error: "forbidden" }, 403);
    }
    await deleteSession(deps.db, found.session.token_hash);
    if (found.via === "cookie") clearCookie(c, deps.env, deps.env.SESSION_COOKIE_NAME);
    return c.json({ ok: true });
  });

  app.post("/api/auth/logout-all", async (c) => {
    const found = await authenticate(c, deps);
    if (!found) return c.json({ error: "unauthorized" }, 401);
    if (found.via === "cookie" && !originAllowed(c.req.raw, deps.env.PUBLIC_ORIGIN)) {
      return c.json({ error: "forbidden" }, 403);
    }
    await deleteUserSessions(deps.db, found.session.user_id);
    if (found.via === "cookie") clearCookie(c, deps.env, deps.env.SESSION_COOKIE_NAME);
    return c.json({ ok: true });
  });

  for (const path of ["/login", "/api/auth/request-link", "/api/auth/verify", "/api/me", "/api/auth/logout", "/api/auth/logout-all"]) {
    app.all(path, (c) => methodNotAllowed(c));
  }

  return app;
}

async function authenticate(
  c: { req: { header: (name: string) => string | undefined } },
  deps: AppDeps,
): Promise<{ session: SessionRow; via: "bearer" | "cookie" } | null> {
  const header = c.req.header("authorization");
  if (header !== undefined) {
    const match = /^Bearer ([A-Za-z0-9_-]{43,128})$/.exec(header);
    if (!match) return null;
    const session = await findSession(deps.db, await sha256Hex(match[1]));
    return session ? { session, via: "bearer" } : null;
  }
  const cookie = readCookie(c as Parameters<typeof readCookie>[0], deps.env.SESSION_COOKIE_NAME);
  if (!cookie) return null;
  const session = await findSession(deps.db, await sha256Hex(cookie));
  return session ? { session, via: "cookie" } : null;
}
