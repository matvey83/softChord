import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import type { AddressInfo } from "node:net";
import { describe, it } from "node:test";
import puppeteer from "puppeteer-core";

import type { Hono } from "hono";
import {
  VERIFIER,
  VERIFIER_HASH,
  createTestApp,
  recorded,
  settle,
  testEnv,
  tokenFromLoginUrl,
} from "./harness.ts";

const CHROME = [
  process.env.CHROME_PATH,
  "/usr/bin/google-chrome",
  "/usr/bin/google-chrome-stable",
  "/usr/bin/chromium",
  "/usr/bin/chromium-browser",
].find((path) => path !== undefined && existsSync(path));

async function readBody(request: IncomingMessage): Promise<Buffer> {
  const chunks: Buffer[] = [];
  for await (const chunk of request) chunks.push(Buffer.from(chunk));
  return Buffer.concat(chunks);
}

function serve(app: () => Hono): Promise<{ origin: string; close: () => Promise<void> }> {
  const server = createServer(async (request: IncomingMessage, response: ServerResponse) => {
    const url = new URL(request.url ?? "/", "http://127.0.0.1");
    const headers = new Headers();
    for (const [name, value] of Object.entries(request.headers)) {
      if (value === undefined) continue;
      if (name === "host" || name === "connection" || name === "content-length" || name === "transfer-encoding") {
        continue;
      }
      headers.set(name, Array.isArray(value) ? value.join(", ") : value);
    }
    const hasBody = request.method !== "GET" && request.method !== "HEAD";
    const upstream = await app().fetch(new Request(url, {
      method: request.method,
      headers,
      body: hasBody ? await readBody(request) : undefined,
    }));
    const outgoing = new Map<string, string | string[]>();
    upstream.headers.forEach((value, name) => {
      if (name === "set-cookie") return;
      outgoing.set(name, value);
    });
    const cookies = upstream.headers.getSetCookie();
    if (cookies.length > 0) outgoing.set("set-cookie", cookies);
    response.writeHead(upstream.status, Object.fromEntries(outgoing));
    response.end(Buffer.from(await upstream.arrayBuffer()));
  });
  return new Promise((resolve) => {
    server.listen(0, "127.0.0.1", () => {
      const address = server.address() as AddressInfo;
      resolve({
        origin: `http://127.0.0.1:${address.port}`,
        close: () => new Promise((done) => server.close(() => done())),
      });
    });
  });
}

describe("login page in a browser", () => {
  it("sends the verify POST when Sign in is clicked", async () => {
    let handler: Hono | undefined;
    const { origin, close } = await serve(() => {
      if (!handler) throw new Error("app is not ready");
      return handler;
    });
    const { app, mailer, tasks } = createTestApp({
      env: { ...testEnv, PUBLIC_ORIGIN: origin },
    });
    handler = app;
    assert.ok(CHROME, "set CHROME_PATH to a Chrome or Chromium binary");
    const browser = await puppeteer.launch({
      executablePath: CHROME,
      headless: true,
      args: ["--no-sandbox", "--disable-dev-shm-usage"],
    });
    try {
      const issued = await app.fetch(new Request(`${origin}/api/auth/request-link`, {
        method: "POST",
        headers: { "content-type": "application/json", origin },
        body: JSON.stringify({
          email: "singer@example.com",
          client: "web",
          verifier: VERIFIER,
          verifier_hash: VERIFIER_HASH,
        }),
      }));
      assert.equal(issued.status, 200);
      await settle(tasks);
      const loginUrl = recorded(mailer)[0]?.loginUrl ?? "";
      const token = tokenFromLoginUrl(loginUrl);
      const verifier = /^sc_verifier=([^;]+)/.exec(
        issued.headers.getSetCookie().find((line) => line.startsWith("sc_verifier=")) ?? "",
      )?.[1] ?? "";
      assert.equal(verifier, VERIFIER);

      const page = await browser.newPage();
      await page.setCookie({ name: "sc_verifier", value: verifier, url: origin });
      await page.goto(loginUrl, { waitUntil: "domcontentloaded" });
      const [verify] = await Promise.all([
        page.waitForResponse((response) =>
          response.request().method() === "POST" && new URL(response.url()).pathname === "/api/auth/verify"),
        page.click("#sign-in"),
      ]);
      assert.equal(verify.status(), 200);
      assert.equal(JSON.parse(verify.request().postData() ?? "{}").token, token);
    } finally {
      await browser.close();
      await close();
    }
  });
});
