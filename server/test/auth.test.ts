import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { EMAIL_LIMIT, LOGIN_TTL_SECONDS } from "../src/config.ts";
import type { SqlDatabase } from "../src/db.ts";
import type { LoginEmail, LoginMailer } from "../src/mailer.ts";
import type { IpRateLimiter } from "../src/rate-limit.ts";
import { sha256Hex } from "../src/tokens.ts";
import {
  PUBLIC_ORIGIN,
  VERIFIER,
  VERIFIER_HASH,
  WRONG_VERIFIER,
  createTestApp,
  postJson,
  recorded,
  settle,
  testEnv,
  tokenFromLoginUrl,
} from "./harness.ts";

async function count(db: SqlDatabase, table: "users" | "sessions" | "login_tokens"): Promise<number> {
  const row = await db.prepare(`SELECT COUNT(*) AS n FROM ${table}`).first<{ n: number }>();
  return Number(row?.n ?? 0);
}

function linkBody(email: string, client: "web" | "ios" | "desktop", extra: Record<string, unknown> = {}) {
  const body: Record<string, unknown> = {
    email,
    client,
    verifier_hash: VERIFIER_HASH,
    ...extra,
  };
  if (client === "web") body.verifier = VERIFIER;
  return body;
}

function linkHeaders(client: "web" | "ios" | "desktop", ip = "203.0.113.10"): Record<string, string> {
  const headers: Record<string, string> = { "cf-connecting-ip": ip };
  if (client === "web") headers.origin = PUBLIC_ORIGIN;
  return headers;
}

async function requestLink(
  app: { fetch: (request: Request) => Promise<Response> | Response },
  email: string,
  client: "web" | "ios" | "desktop" = "ios",
  extra: Record<string, unknown> = {},
) {
  return postJson(app, "/api/auth/request-link", linkBody(email, client, extra), linkHeaders(client));
}

describe("magic-link auth", () => {
  it("mails the normalized address once, with the raw token only in the fragment", async () => {
    const { app, db, mailer, tasks } = createTestApp();
    const response = await requestLink(app, "  User@Example.COM ", "ios", {
      redirect: "https://evil.example/phish",
    });
    assert.equal(response.status, 200);
    assert.deepEqual(await response.json(), { ok: true });
    await settle(tasks);

    const sent = recorded(mailer);
    assert.equal(sent.length, 1);
    assert.equal(sent[0]?.to, "user@example.com");
    const raw = tokenFromLoginUrl(sent[0]?.loginUrl ?? "");
    assert.equal(raw.length, 43);
    assert.equal(
      sent[0]?.loginUrl,
      `https://songs.example/login?client=ios&hint=u***%40example.com#t=${raw}`,
    );
    assert.equal(sent[0]?.loginUrl.includes("softchord://"), false);
    assert.equal(sent[0]?.loginUrl.includes("evil.example"), false);
    const hash = await sha256Hex(raw);
    assert.equal(sent[0]?.loginUrl.includes(hash), false);
    const stored = await db
      .prepare("SELECT token_hash, email FROM login_tokens")
      .first<{ token_hash: string; email: string }>();
    assert.equal(stored?.token_hash, hash);
    assert.equal(stored?.email, "user@example.com");
    assert.equal(await count(db, "users"), 0);
  });

  it("does not take the link host from the request", async () => {
    const { app, mailer, tasks } = createTestApp();
    const response = await postJson(
      app,
      "/api/auth/request-link",
      linkBody("singer@example.com", "ios"),
      {
        ...linkHeaders("ios"),
        "x-forwarded-host": "evil.example",
      },
    );
    assert.equal(response.status, 200);
    await settle(tasks);
    assert.equal(recorded(mailer)[0]?.loginUrl.startsWith(`${PUBLIC_ORIGIN}/login?`), true);
  });

  it("voids the previous unused token when a new link is requested", async () => {
    const { app, mailer, tasks } = createTestApp();
    assert.equal((await requestLink(app, "singer@example.com")).status, 200);
    await settle(tasks);
    const first = tokenFromLoginUrl(recorded(mailer)[0]?.loginUrl ?? "");
    assert.equal((await requestLink(app, "singer@example.com")).status, 200);
    await settle(tasks);
    assert.equal(recorded(mailer).length, 2);
    const second = tokenFromLoginUrl(recorded(mailer)[1]?.loginUrl ?? "");
    assert.notEqual(first, second);

    const stale = await postJson(app, "/api/auth/verify", { token: first, verifier: VERIFIER });
    assert.equal(stale.status, 400);
    assert.deepEqual(await stale.json(), { error: "invalid_or_expired" });

    const fresh = await postJson(app, "/api/auth/verify", {
      token: second,
      verifier: VERIFIER,
      device_label: "  rehearsal phone  ",
    });
    assert.equal(fresh.status, 200);
    const body = await fresh.json() as { email: string; token: string };
    assert.equal(body.email, "singer@example.com");
    assert.equal(typeof body.token, "string");
  });

  it("creates a user and session on verify, and rejects reuse, expiry, and a bad token", async () => {
    assert.equal(LOGIN_TTL_SECONDS, 15 * 60);
    let now = Date.parse("2026-11-10T12:00:00Z");
    const { app, db, mailer, tasks } = createTestApp({ now: () => now });
    await requestLink(app, "singer@example.com");
    await settle(tasks);
    const token = tokenFromLoginUrl(recorded(mailer)[0]?.loginUrl ?? "");

    const created = await postJson(app, "/api/auth/verify", {
      token,
      verifier: VERIFIER,
      device_label: "Matvey's iPhone",
      client: "web",
    });
    assert.equal(created.status, 200);
    const session = await created.json() as { email: string; token: string };
    assert.equal(await count(db, "users"), 1);
    assert.equal(await count(db, "sessions"), 1);
    const row = await db
      .prepare("SELECT client, device_label, created_at, last_used_at, token_hash FROM sessions")
      .first<{
        client: string;
        device_label: string;
        created_at: number;
        last_used_at: number;
        token_hash: string;
      }>();
    assert.equal(row?.client, "ios");
    assert.equal(row?.device_label, "Matvey's iPhone");
    assert.equal(row?.created_at, Math.floor(now / 1000));
    assert.equal(row?.last_used_at, row?.created_at);
    assert.equal(row?.token_hash, await sha256Hex(session.token));
    assert.notEqual(row?.token_hash, session.token);

    const reused = await postJson(app, "/api/auth/verify", { token, verifier: VERIFIER });
    assert.equal(reused.status, 400);
    assert.deepEqual(await reused.json(), { error: "invalid_or_expired" });
    assert.equal(reused.headers.get("cache-control"), "no-store");
    assert.equal(reused.headers.get("referrer-policy"), "no-referrer");
    assert.equal(await count(db, "sessions"), 1);

    await requestLink(app, "late@example.com");
    await settle(tasks);
    const expiring = tokenFromLoginUrl(recorded(mailer).at(-1)?.loginUrl ?? "");
    now += LOGIN_TTL_SECONDS * 1000;
    const expired = await postJson(app, "/api/auth/verify", { token: expiring, verifier: VERIFIER });
    assert.equal(expired.status, 400);
    assert.deepEqual(await expired.json(), { error: "invalid_or_expired" });
    assert.equal(await count(db, "users"), 1);

    const bad = await postJson(app, "/api/auth/verify", { token: "not-a-real-token", verifier: VERIFIER });
    assert.equal(bad.status, 400);
    assert.deepEqual(await bad.json(), { error: "invalid_or_expired" });
    assert.equal(await count(db, "sessions"), 1);
  });

  it("returns the same body for new and existing emails and creates no user until verify", async () => {
    const { app, db, mailer, tasks } = createTestApp();
    const first = await requestLink(app, "New.Person@Example.com");
    const firstBody = await first.json();
    assert.equal(await count(db, "users"), 0);
    await settle(tasks);
    const token = tokenFromLoginUrl(recorded(mailer)[0]?.loginUrl ?? "");
    const verified = await postJson(app, "/api/auth/verify", { token, verifier: VERIFIER });
    assert.equal(verified.status, 200);
    assert.equal(await count(db, "users"), 1);

    const existing = await requestLink(app, "new.person@example.com");
    const another = await requestLink(app, "other@example.com");
    assert.deepEqual(await existing.json(), firstBody);
    assert.deepEqual(await another.json(), firstBody);
    assert.equal(existing.status, first.status);
    assert.equal(await count(db, "users"), 1);
  });

  it("stops at five emails an hour and does not mail a bad address", async () => {
    assert.equal(EMAIL_LIMIT, 5);
    let calls = 0;
    const limiter: IpRateLimiter = {
      allow() {
        calls += 1;
        return Promise.resolve(true);
      },
    };
    const { app, db, mailer, tasks } = createTestApp({ limiter });
    const bodies = [];
    for (let attempt = 0; attempt < 5; attempt += 1) {
      const response = await requestLink(app, "singer@example.com", "ios", { attempt });
      bodies.push(await response.json());
      assert.equal(response.status, 200);
    }
    await settle(tasks);
    assert.equal(recorded(mailer).length, 5);
    assert.equal(await count(db, "login_tokens"), 5);

    const sixth = await requestLink(app, "singer@example.com");
    assert.equal(sixth.status, 200);
    assert.deepEqual(await sixth.json(), bodies[0]);
    await settle(tasks);
    assert.equal(recorded(mailer).length, 5);
    assert.equal(await count(db, "login_tokens"), 5);
    assert.equal(calls, 6);

    const syntax = await requestLink(app, "not-an-email");
    assert.equal(syntax.status, 400);
    assert.deepEqual(await syntax.json(), { error: "invalid_request" });
    await settle(tasks);
    assert.equal(recorded(mailer).length, 5);

    const missing = await postJson(app, "/api/auth/request-link", { email: "singer@example.com", client: "ios" });
    assert.equal(missing.status, 400);
    assert.equal(recorded(mailer).length, 5);
  });

  it("does not send when the IP limiter denies the request", async () => {
    const { app, db, mailer, tasks } = createTestApp({
      limiter: { allow: () => Promise.resolve(false) },
    });
    const response = await requestLink(app, "singer@example.com");
    assert.equal(response.status, 200);
    assert.deepEqual(await response.json(), { ok: true });
    await settle(tasks);
    assert.equal(recorded(mailer).length, 0);
    assert.equal(await count(db, "login_tokens"), 0);
    assert.equal(await count(db, "users"), 0);
  });

  it("rejects verify without a verifier and with the wrong verifier", async () => {
    const { app, db, mailer, tasks } = createTestApp();
    await requestLink(app, "singer@example.com");
    await settle(tasks);
    const token = tokenFromLoginUrl(recorded(mailer)[0]?.loginUrl ?? "");

    const missing = await postJson(app, "/api/auth/verify", { token });
    assert.equal(missing.status, 400);
    assert.deepEqual(await missing.json(), { error: "invalid_or_expired" });
    const wrong = await postJson(app, "/api/auth/verify", { token, verifier: WRONG_VERIFIER });
    assert.equal(wrong.status, 400);
    assert.deepEqual(await wrong.json(), { error: "invalid_or_expired" });
    const short = await postJson(app, "/api/auth/verify", { token, verifier: "abc" });
    assert.equal(short.status, 400);
    assert.deepEqual(await short.json(), { error: "invalid_or_expired" });
    assert.equal(await count(db, "users"), 0);
    assert.equal(await count(db, "sessions"), 0);

    const ok = await postJson(app, "/api/auth/verify", { token, verifier: VERIFIER });
    assert.equal(ok.status, 200);
  });

  it("serves a session from a bearer token and revokes it on logout", async () => {
    const { app, mailer, tasks } = createTestApp();
    const anonymous = await app.fetch(new Request(`${PUBLIC_ORIGIN}/api/me`));
    assert.equal(anonymous.status, 401);
    assert.deepEqual(await anonymous.json(), { error: "unauthorized" });

    await requestLink(app, "singer@example.com");
    await settle(tasks);
    const token = tokenFromLoginUrl(recorded(mailer)[0]?.loginUrl ?? "");
    const verified = await postJson(app, "/api/auth/verify", { token, verifier: VERIFIER });
    const session = await verified.json() as { email: string; token: string };
    const headers = { authorization: `Bearer ${session.token}` };
    const me = await app.fetch(new Request(`${PUBLIC_ORIGIN}/api/me`, { headers }));
    assert.equal(me.status, 200);
    assert.deepEqual(await me.json(), { email: "singer@example.com" });

    const loggedOut = await postJson(app, "/api/auth/logout", {}, headers);
    assert.equal(loggedOut.status, 200);
    assert.deepEqual(await loggedOut.json(), { ok: true });
    const after = await app.fetch(new Request(`${PUBLIC_ORIGIN}/api/me`, { headers }));
    assert.equal(after.status, 401);
  });

  it("updates last_used_at at most hourly", async () => {
    let now = Date.parse("2026-11-10T12:00:00Z");
    const { app, db, mailer, tasks } = createTestApp({ now: () => now });
    await requestLink(app, "singer@example.com");
    await settle(tasks);
    const token = tokenFromLoginUrl(recorded(mailer)[0]?.loginUrl ?? "");
    const verified = await postJson(app, "/api/auth/verify", { token, verifier: VERIFIER });
    const session = await verified.json() as { token: string };
    const headers = { authorization: `Bearer ${session.token}` };
    await app.fetch(new Request(`${PUBLIC_ORIGIN}/api/me`, { headers }));
    const before = await db.prepare("SELECT last_used_at FROM sessions").first<{ last_used_at: number }>();
    now += 30 * 60 * 1000;
    await app.fetch(new Request(`${PUBLIC_ORIGIN}/api/me`, { headers }));
    const within = await db.prepare("SELECT last_used_at FROM sessions").first<{ last_used_at: number }>();
    assert.equal(within?.last_used_at, before?.last_used_at);
    now += 31 * 60 * 1000;
    await app.fetch(new Request(`${PUBLIC_ORIGIN}/api/me`, { headers }));
    const after = await db.prepare("SELECT last_used_at FROM sessions").first<{ last_used_at: number }>();
    assert.equal(after?.last_used_at, Math.floor(now / 1000));
  });

  it("binds web verify to the verifier cookie and the session cookie", async () => {
    const { app, mailer, tasks } = createTestApp();
    const issued = await requestLink(app, "singer@example.com", "web");
    assert.equal(issued.status, 200);
    await settle(tasks);
    const verifierCookie = issued.headers.getSetCookie().find((line) => line.startsWith("sc_verifier="));
    assert.ok(verifierCookie);
    assert.match(verifierCookie, new RegExp(`^sc_verifier=${VERIFIER};`));
    assert.match(verifierCookie, /HttpOnly/);
    assert.match(verifierCookie, /Path=\//);
    assert.match(verifierCookie, /SameSite=Lax/);
    assert.match(verifierCookie, /Max-Age=900/);
    assert.equal(verifierCookie.includes("Secure"), false);
    assert.equal(verifierCookie.includes("Domain"), false);
    const token = tokenFromLoginUrl(recorded(mailer)[0]?.loginUrl ?? "");
    assert.match(recorded(mailer)[0]?.loginUrl ?? "", /client=web/);
    assert.equal((recorded(mailer)[0]?.loginUrl ?? "").includes("softchord://"), false);

    const bypass = await postJson(app, "/api/auth/verify", { token, verifier: VERIFIER }, { origin: PUBLIC_ORIGIN });
    assert.equal(bypass.status, 400);

    const verified = await postJson(app, "/api/auth/verify", { token }, {
      origin: PUBLIC_ORIGIN,
      cookie: `sc_verifier=${VERIFIER}`,
    });
    assert.equal(verified.status, 200);
    const body = await verified.json() as { email: string; token?: string };
    assert.deepEqual(body, { email: "singer@example.com" });
    const sessionCookie = verified.headers.getSetCookie().find((line) => line.startsWith("sc_session="));
    assert.ok(sessionCookie);
    assert.match(sessionCookie, /HttpOnly/);
    assert.match(sessionCookie, /Path=\//);
    assert.match(sessionCookie, /SameSite=Lax/);
    assert.match(sessionCookie, /Max-Age=34560000/);
    assert.equal(sessionCookie.includes("Secure"), false);
    assert.equal(sessionCookie.includes("Domain"), false);
    const sessionValue = /^sc_session=([^;]+)/.exec(sessionCookie)?.[1] ?? "";
    assert.equal(sessionValue.includes(await sha256Hex(sessionValue)), false);

    const me = await app.fetch(new Request(`${PUBLIC_ORIGIN}/api/me`, {
      headers: { cookie: `sc_session=${sessionValue}` },
    }));
    assert.equal(me.status, 200);
    assert.deepEqual(await me.json(), { email: "singer@example.com" });

    const crossSite = await postJson(app, "/api/auth/logout", {}, {
      cookie: `sc_session=${sessionValue}`,
      origin: "https://evil.example",
    });
    assert.equal(crossSite.status, 403);
    assert.deepEqual(await crossSite.json(), { error: "forbidden" });
    const still = await app.fetch(new Request(`${PUBLIC_ORIGIN}/api/me`, {
      headers: { cookie: `sc_session=${sessionValue}` },
    }));
    assert.equal(still.status, 200);

    const loggedOut = await postJson(app, "/api/auth/logout", {}, {
      cookie: `sc_session=${sessionValue}`,
      origin: PUBLIC_ORIGIN,
    });
    assert.equal(loggedOut.status, 200);
    const after = await app.fetch(new Request(`${PUBLIC_ORIGIN}/api/me`, {
      headers: { cookie: `sc_session=${sessionValue}` },
    }));
    assert.equal(after.status, 401);
  });

  it("does not verify a login link on GET and keeps the token out of the page", async () => {
    const { app, db } = createTestApp();
    const response = await app.fetch(new Request(
      `${PUBLIC_ORIGIN}/login?client=ios&hint=m***%40gmail.com&token=super-secret-token#t=ignored`,
    ));
    assert.equal(response.status, 200);
    assert.equal(response.headers.get("cache-control"), "no-store");
    assert.equal(response.headers.get("referrer-policy"), "no-referrer");
    const html = await response.text();
    assert.equal(html.includes("super-secret-token"), false);
    assert.equal(html.includes("ignored"), false);
    assert.equal(html.includes("id=\"sign-in\""), false);
    assert.equal(html.includes("You're signed in"), false);
    assert.equal(html.includes('"/api/auth/verify"'), false);
    assert.match(html, /Open in SoftChord/);
    assert.match(html, /Paste this link into SoftChord if the button does not open the app\./);
    const assignAt = html.indexOf("window.location.assign");
    const openAt = html.indexOf('getElementById("open-app").addEventListener');
    assert.ok(openAt !== -1 && openAt < assignAt);
    assert.equal(html.includes("DOMContentLoaded"), false);
    assert.equal(html.includes(".click()"), false);
    assert.equal(await count(db, "users"), 0);

    const desktop = await app.fetch(new Request(`${PUBLIC_ORIGIN}/login?client=desktop`));
    assert.equal((await desktop.text()).includes("id=\"sign-in\""), false);

    const web = await app.fetch(new Request(`${PUBLIC_ORIGIN}/login?client=web&hint=m***%40gmail.com`));
    const webHtml = await web.text();
    assert.equal(webHtml.includes("Open in SoftChord"), false);
    assert.match(webHtml, /Sign in as m\*\*\*@gmail\.com/);
    assert.match(webHtml, /You're signed in\. Return to SoftChord\./);
    assert.equal(webHtml.includes("location.replace"), false);
    assert.match(webHtml, /history\.replaceState/);
    assert.equal(webHtml.includes("<a "), false);
    const loginHtml = async (appUrl: string) => {
      const { app: linkedApp } = createTestApp({ env: { ...testEnv, APP_URL: appUrl } });
      const response = await linkedApp.fetch(new Request(`${PUBLIC_ORIGIN}/login?client=web`));
      return response.text();
    };
    const linkedHtml = await loginHtml("https://app.example/library");
    assert.match(linkedHtml, /<a href="https:\/\/app\.example\/library">Return to SoftChord\.<\/a>/);
    const localHtml = await loginHtml("http://127.0.0.1:8787/songs");
    assert.match(localHtml, /<a href="http:\/\/127\.0\.0\.1:8787\/songs">Return to SoftChord\.<\/a>/);
    assert.match(await loginHtml("http://localhost/songs"), /<a href="http:\/\/localhost\/songs">/);
    for (const appUrl of ["javascript:alert(1)", "http://songs.example", "data:text/html,hi", "//host"]) {
      assert.equal((await loginHtml(appUrl)).includes("<a "), false, appUrl);
    }
    const quotedHtml = await loginHtml('https://app.example/a"b');
    assert.match(quotedHtml, /<a href="https:\/\/app\.example\/a%22b">Return to SoftChord\.<\/a>/);
    assert.equal(quotedHtml.includes('a"b'), false);
    const policy = web.headers.get("content-security-policy") ?? "";
    const nonce = /script-src 'nonce-([^']+)'/.exec(policy)?.[1] ?? "";
    assert.match(policy, /default-src 'none'/);
    assert.match(policy, /connect-src 'self'/);
    assert.match(policy, /form-action 'none'/);
    assert.match(policy, /frame-ancestors 'none'/);
    assert.match(webHtml, new RegExp(`<script nonce="${nonce}">`));
    const verifyAt = webHtml.indexOf('"/api/auth/verify"');
    const clickAt = webHtml.lastIndexOf('addEventListener("click"', verifyAt);
    assert.ok(clickAt !== -1 && clickAt < verifyAt);

    const hostile = await app.fetch(new Request(
      `${PUBLIC_ORIGIN}/login?client=web&hint=${encodeURIComponent("<script>alert(1)</script>")}`,
    ));
    const hostileHtml = await hostile.text();
    assert.equal(hostileHtml.includes("<script>alert"), false);
    assert.match(hostileHtml, /&lt;script&gt;/);
  });

  it("returns the 200 before the mailer finishes", async () => {
    let release = () => {};
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const sent: LoginEmail[] = [];
    const mailer: LoginMailer = {
      async sendLoginEmail(message) {
        sent.push(message);
        await gate;
      },
    };
    const { app, tasks } = createTestApp({ mailer });
    const pending = requestLink(app, "singer@example.com");
    try {
      const raced = await Promise.race([
        pending.then(() => "response"),
        new Promise((resolve) => setTimeout(() => resolve("blocked"), 300)),
      ]);
      assert.equal(raced, "response");
      const response = await pending;
      assert.equal(response.status, 200);
      assert.equal(sent.length, 1);
      assert.equal(sent[0]?.to, "singer@example.com");
    } finally {
      release();
      await pending.catch(() => undefined);
      await settle(tasks);
    }
  });

  it("does not log the raw token or its hash", async () => {
    const lines: string[] = [];
    const originalLog = console.log;
    const originalError = console.error;
    console.log = (...args: unknown[]) => {
      lines.push(args.map(String).join(" "));
    };
    console.error = (...args: unknown[]) => {
      lines.push(args.map(String).join(" "));
    };
    try {
      const { app, mailer, tasks } = createTestApp();
      await requestLink(app, "singer@example.com");
      await settle(tasks);
      const raw = tokenFromLoginUrl(recorded(mailer)[0]?.loginUrl ?? "");
      const hash = await sha256Hex(raw);
      const output = lines.join("\n");
      assert.equal(output.includes(raw), false);
      assert.equal(output.includes(hash), false);
      assert.equal(output.includes("singer@example.com"), false);
    } finally {
      console.log = originalLog;
      console.error = originalError;
    }
  });
});
