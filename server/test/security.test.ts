import assert from "node:assert/strict";
import { describe, it } from "node:test";

import type { SqlDatabase } from "../src/db.ts";
import type { LoginEmail } from "../src/mailer.ts";
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
  tokenFromLoginUrl,
} from "./harness.ts";

async function count(db: SqlDatabase, sql: string): Promise<number> {
  const row = await db.prepare(sql).first<{ n: number }>();
  return Number(row?.n ?? 0);
}

function cookieValue(response: Response, name: string): string {
  const line = response.headers.getSetCookie().find((item) => item.startsWith(`${name}=`));
  assert.ok(line, response.headers.getSetCookie().join("\n"));
  return /^[^=]+=([^;]*)/.exec(line)?.[1] ?? "";
}

describe("login request guards", () => {
  it("allows a missing Origin and rejects a foreign one for every client", async () => {
    const { app, mailer, tasks } = createTestApp();
    for (const client of ["ios", "web"] as const) {
      const response = await postJson(app, "/api/auth/request-link", {
        email: `${client}@example.com`,
        client,
        verifier_hash: VERIFIER_HASH,
        ...(client === "web" ? { verifier: VERIFIER } : {}),
      });
      assert.equal(response.status, 200, client);
      assert.equal(response.headers.get("cache-control"), "no-store");
    }
    await settle(tasks);
    assert.equal(recorded(mailer).length, 2);

    for (const client of ["web", "ios", "desktop"] as const) {
      const foreign = await postJson(
        app,
        "/api/auth/request-link",
        {
          email: "singer@example.com",
          client,
          verifier_hash: VERIFIER_HASH,
          ...(client === "web" ? { verifier: VERIFIER } : {}),
        },
        { origin: client === "desktop" ? "null" : "https://evil.example" },
      );
      assert.equal(foreign.status, 403, client);
      assert.deepEqual(await foreign.json(), { error: "forbidden" });
    }
    await settle(tasks);
    assert.equal(recorded(mailer).length, 2);
  });

  it("accepts only an application/json body", async () => {
    const { app, mailer, tasks } = createTestApp();
    const body = JSON.stringify({
      email: "singer@example.com",
      client: "ios",
      verifier_hash: VERIFIER_HASH,
    });
    const plain = await app.fetch(new Request(`${PUBLIC_ORIGIN}/api/auth/request-link`, {
      method: "POST",
      headers: { "content-type": "text/plain" },
      body,
    }));
    assert.equal(plain.status, 400);
    assert.deepEqual(await plain.json(), { error: "invalid_request" });

    const missing = await app.fetch(new Request(`${PUBLIC_ORIGIN}/api/auth/verify`, {
      method: "POST",
      body: "{}",
    }));
    assert.equal(missing.status, 400);

    const vendor = await app.fetch(new Request(`${PUBLIC_ORIGIN}/api/auth/logout`, {
      method: "POST",
      headers: { "content-type": "application/vnd.api+json" },
      body: "{}",
    }));
    assert.equal(vendor.status, 400);

    const charset = await app.fetch(new Request(`${PUBLIC_ORIGIN}/api/auth/request-link`, {
      method: "POST",
      headers: { "content-type": "application/json; charset=utf-8" },
      body,
    }));
    assert.equal(charset.status, 200);
    await settle(tasks);
    assert.equal(recorded(mailer).length, 1);
  });

  it("shares the hourly cap across plus-aliases and Gmail spellings", async () => {
    const { app, db, mailer, tasks } = createTestApp();
    const send = async (email: string) => {
      const response = await postJson(app, "/api/auth/request-link", {
        email,
        client: "ios",
        verifier_hash: VERIFIER_HASH,
      });
      assert.equal(response.status, 200);
      await settle(tasks);
    };

    await send("user+a@example.com");
    await send("user+b@example.com");
    await send("user+a@example.com");
    await send("user+b@example.com");
    await send("user+a@example.com");
    assert.deepEqual(recorded(mailer).map((message) => message.to), [
      "user+a@example.com",
      "user+b@example.com",
      "user+a@example.com",
      "user+b@example.com",
      "user+a@example.com",
    ]);
    await send("user+c@example.com");
    assert.equal(recorded(mailer).length, 5);
    const latest = tokenFromLoginUrl(recorded(mailer).at(-1)?.loginUrl ?? "");
    await send("user.name@example.com");
    assert.equal(recorded(mailer).at(-1)?.to, "user.name@example.com");
    const still = await postJson(app, "/api/auth/verify", { token: latest, verifier: VERIFIER });
    assert.equal(still.status, 200);

    await send("A.B+tag@Gmail.com");
    assert.equal(recorded(mailer).at(-1)?.to, "a.b+tag@gmail.com");
    await send("ab@googlemail.com");
    await send("ab@googlemail.com");
    await send("ab@googlemail.com");
    await send("ab@googlemail.com");
    const before = recorded(mailer).length;
    await send("a.b@gmail.com");
    assert.equal(recorded(mailer).length, before);
    await send("other@gmail.com");
    assert.equal(recorded(mailer).at(-1)?.to, "other@gmail.com");
    assert.equal(await count(db, "SELECT COUNT(*) AS n FROM login_tokens"), 12);
  });

  it("lets only five of eight concurrent requests through, and only one verify", async () => {
    const { app, db, mailer, tasks } = createTestApp({ yield: true });
    const responses = await Promise.all(
      Array.from({ length: 8 }, () => postJson(app, "/api/auth/request-link", {
        email: "singer@example.com",
        client: "ios",
        verifier_hash: VERIFIER_HASH,
      })),
    );
    assert.equal(responses.every((response) => response.status === 200), true);
    await settle(tasks);
    assert.equal(recorded(mailer).length, 5);
    assert.equal(await count(db, "SELECT COUNT(*) AS n FROM login_tokens"), 5);
    assert.equal(
      await count(db, "SELECT COUNT(*) AS n FROM login_tokens WHERE consumed_at IS NULL"),
      1,
    );

    const token = tokenFromLoginUrl(recorded(mailer).at(-1)?.loginUrl ?? "");
    const verified = await Promise.all([
      postJson(app, "/api/auth/verify", { token, verifier: VERIFIER }),
      postJson(app, "/api/auth/verify", { token, verifier: VERIFIER }),
    ]);
    assert.deepEqual(verified.map((response) => response.status).sort(), [200, 400]);
    assert.equal(await count(db, "SELECT COUNT(*) AS n FROM sessions"), 1);
  });

  it("replaces the previous web session and clears the verifier cookie", async () => {
    const { app, mailer, tasks } = createTestApp();
    const issued = await postJson(app, "/api/auth/request-link", {
      email: "singer@example.com",
      client: "web",
      verifier: VERIFIER,
      verifier_hash: VERIFIER_HASH,
    }, { origin: PUBLIC_ORIGIN });
    await settle(tasks);
    const token = tokenFromLoginUrl(recorded(mailer)[0]?.loginUrl ?? "");
    const verifier = cookieValue(issued, "sc_verifier");
    const first = await postJson(app, "/api/auth/verify", { token }, {
      origin: PUBLIC_ORIGIN,
      cookie: `sc_verifier=${verifier}`,
    });
    assert.equal(first.status, 200);
    const session = cookieValue(first, "sc_session");
    assert.match(first.headers.getSetCookie().join("\n"), /sc_verifier=;/);
    assert.match(first.headers.getSetCookie().join("\n"), /Max-Age=0/);

    const again = await postJson(app, "/api/auth/request-link", {
      email: "singer@example.com",
      client: "web",
      verifier: VERIFIER,
      verifier_hash: VERIFIER_HASH,
    }, { origin: PUBLIC_ORIGIN });
    await settle(tasks);
    const nextToken = tokenFromLoginUrl(recorded(mailer).at(-1)?.loginUrl ?? "");
    const nextVerifier = cookieValue(again, "sc_verifier");
    const failed = await postJson(app, "/api/auth/verify", { token: nextToken }, {
      origin: PUBLIC_ORIGIN,
      cookie: `sc_session=${session}; sc_verifier=${WRONG_VERIFIER}`,
    });
    assert.equal(failed.status, 400);
    const still = await app.fetch(new Request(`${PUBLIC_ORIGIN}/api/me`, {
      headers: { cookie: `sc_session=${session}` },
    }));
    assert.equal(still.status, 200);

    const replaced = await postJson(app, "/api/auth/verify", { token: nextToken }, {
      origin: PUBLIC_ORIGIN,
      cookie: `sc_session=${session}; sc_verifier=${nextVerifier}`,
    });
    assert.equal(replaced.status, 200);
    const old = await app.fetch(new Request(`${PUBLIC_ORIGIN}/api/me`, {
      headers: { cookie: `sc_session=${session}` },
    }));
    assert.equal(old.status, 401);
    const current = cookieValue(replaced, "sc_session");
    const me = await app.fetch(new Request(`${PUBLIC_ORIGIN}/api/me`, {
      headers: { cookie: `sc_session=${current}` },
    }));
    assert.equal(me.status, 200);
  });

  it("sets the __Host- prefix and Secure from the production config", async () => {
    const sent: LoginEmail[] = [];
    const { app, tasks } = createTestApp({
      mailer: {
        async sendLoginEmail(message) {
          sent.push(message);
        },
      },
      env: {
        ENVIRONMENT: "production",
        MAILER: "unconfigured",
        PUBLIC_ORIGIN: "https://example.invalid",
        SESSION_COOKIE_NAME: "__Host-sc_session",
        VERIFIER_COOKIE_NAME: "__Host-sc_verifier",
        COOKIE_SECURE: "true",
      },
    });
    const issued = await postJson(app, "/api/auth/request-link", {
      email: "singer@example.com",
      client: "web",
      verifier: VERIFIER,
      verifier_hash: VERIFIER_HASH,
    }, { origin: "https://example.invalid" });
    await settle(tasks);
    const verifierLine = issued.headers.getSetCookie().find((line) => line.startsWith("__Host-sc_verifier="));
    assert.ok(verifierLine);
    assert.match(verifierLine, /Secure/);
    assert.match(verifierLine, /HttpOnly/);
    assert.match(verifierLine, /Path=\//);
    assert.match(verifierLine, /SameSite=Lax/);
    assert.equal(verifierLine.includes("Domain"), false);

    const token = tokenFromLoginUrl(sent[0]?.loginUrl ?? "");
    const hash = await sha256Hex(VERIFIER);
    assert.equal(hash, VERIFIER_HASH);
    const verified = await postJson(app, "/api/auth/verify", { token }, {
      origin: "https://example.invalid",
      cookie: `__Host-sc_verifier=${VERIFIER}`,
    });
    const sessionLine = verified.headers.getSetCookie().find((line) => line.startsWith("__Host-sc_session="));
    assert.equal(verified.status, 200);
    assert.ok(sessionLine);
    assert.match(sessionLine, /Secure/);
    assert.match(sessionLine, /HttpOnly/);
    assert.equal(sessionLine.includes("Domain"), false);
  });
});
