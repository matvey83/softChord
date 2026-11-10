import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { describe, it } from "node:test";
import { fileURLToPath } from "node:url";

import { assertRuntimeConfig } from "../src/config.ts";
import worker from "../src/index.ts";
import { RecordingMailer, assertMailerAllowed, mailerFromEnv } from "../src/mailer.ts";
import { limiterFromBinding } from "../src/rate-limit.ts";
import { createTestApp } from "./harness.ts";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

function parseJsonc(text: string): Record<string, unknown> {
  const withoutBlock = text.replace(/\/\*[\s\S]*?\*\//g, "");
  const withoutLine = withoutBlock.replace(/^\s*\/\/.*$/gm, "");
  return JSON.parse(withoutLine) as Record<string, unknown>;
}

describe("recording mailer guard", () => {
  it("refuses the recording mailer as the production binding", () => {
    const production = parseJsonc(readFileSync(join(root, "wrangler.production.jsonc"), "utf8"));
    const dev = parseJsonc(readFileSync(join(root, "wrangler.jsonc"), "utf8"));
    const productionVars = production.vars as Record<string, string>;
    const devVars = dev.vars as Record<string, string>;
    assert.equal(production.account_id, undefined);
    assert.equal(dev.account_id, undefined);
    assert.equal(productionVars.ENVIRONMENT, "production");
    assert.notEqual(productionVars.MAILER, "recording");
    assert.equal(productionVars.MAILER, "unconfigured");
    assert.equal(productionVars.SESSION_COOKIE_NAME, "__Host-sc_session");
    assert.equal(productionVars.VERIFIER_COOKIE_NAME, "__Host-sc_verifier");
    assert.equal(productionVars.COOKIE_SECURE, "true");
    assert.equal(devVars.ENVIRONMENT, "development");
    assert.equal(devVars.MAILER, "recording");
    assert.equal(devVars.SESSION_COOKIE_NAME, "sc_session");
    assert.equal(devVars.COOKIE_SECURE, "false");
    const ratelimits = dev.ratelimits as Array<{ name: string; simple: { limit: number; period: number } }>;
    assert.equal(ratelimits[0]?.name, "IP_RATE_LIMITER");
    assert.equal(ratelimits[0]?.simple.limit, 10);
    assert.equal(ratelimits[0]?.simple.period, 60);
    assert.equal(JSON.stringify(production).includes("resend"), false);
    assert.equal(JSON.stringify(dev).includes("resend"), false);

    assert.throws(() => assertMailerAllowed({ ENVIRONMENT: "production", MAILER: "recording" }));
    assert.throws(() => assertMailerAllowed(
      { ENVIRONMENT: "production", MAILER: "unconfigured" },
      new RecordingMailer(),
    ));
    assert.throws(() => mailerFromEnv({ ENVIRONMENT: "production", MAILER: "recording" }));
    assert.throws(() => mailerFromEnv({ ENVIRONMENT: "production", MAILER: "unconfigured" }));
    const local = mailerFromEnv({ ENVIRONMENT: "development", MAILER: "recording" });
    assert.equal(local instanceof RecordingMailer, true);
    assert.throws(() => createTestApp({
      env: {
        ENVIRONMENT: "production",
        MAILER: "unconfigured",
        PUBLIC_ORIGIN: "https://example.invalid",
        SESSION_COOKIE_NAME: "__Host-sc_session",
        VERIFIER_COOKIE_NAME: "__Host-sc_verifier",
        COOKIE_SECURE: "true",
      },
    }));
  });

  it("rejects a production worker that is bound to the recording mailer", async () => {
    const env = {
      ENVIRONMENT: "production",
      MAILER: "recording",
      PUBLIC_ORIGIN: "https://example.invalid",
      SESSION_COOKIE_NAME: "__Host-sc_session",
      VERIFIER_COOKIE_NAME: "__Host-sc_verifier",
      COOKIE_SECURE: "true",
      DB: {},
      IP_RATE_LIMITER: { limit: () => Promise.resolve({ success: true }) },
    };
    const ctx = { waitUntil() {}, passThroughOnException() {}, props: {} };
    await assert.rejects(() => worker.fetch(new Request("https://example.invalid/api/me"), env, ctx));
  });

  it("does not choose cookie security from the request host", () => {
    assert.throws(() => assertRuntimeConfig({
      ENVIRONMENT: "development",
      MAILER: "recording",
      PUBLIC_ORIGIN: "http://localhost:8787",
      SESSION_COOKIE_NAME: "__Host-sc_session",
      VERIFIER_COOKIE_NAME: "sc_verifier",
      COOKIE_SECURE: "false",
    }));
    assert.throws(() => assertRuntimeConfig({
      ENVIRONMENT: "production",
      MAILER: "unconfigured",
      PUBLIC_ORIGIN: "http://localhost:8787",
      SESSION_COOKIE_NAME: "__Host-sc_session",
      VERIFIER_COOKIE_NAME: "__Host-sc_verifier",
      COOKIE_SECURE: "true",
    }));
  });

  it("adapts the rate-limit binding by IP key and fails closed", async () => {
    const keys: string[] = [];
    const allow = limiterFromBinding({
      async limit(options) {
        keys.push(options.key);
        return { success: false };
      },
    });
    assert.equal(await allow.allow("203.0.113.8"), false);
    assert.deepEqual(keys, ["ip:203.0.113.8"]);
    const down = limiterFromBinding({
      limit() {
        return Promise.reject(new Error("binding down"));
      },
    });
    assert.equal(await down.allow("203.0.113.8"), false);
  });
});
