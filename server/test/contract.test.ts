import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { describe, it } from "node:test";
import { fileURLToPath } from "node:url";

import { sha256Hex } from "../src/tokens.ts";
import { createTestApp, PUBLIC_ORIGIN, recorded, settle, tokenFromLoginUrl } from "./harness.ts";

interface ContractStep {
  mailerDelta?: number;
  request: {
    method: string;
    path: string;
    headers?: Record<string, string>;
    cookies?: string[];
    json?: unknown;
  };
  response: {
    status: number;
    json?: unknown;
    headers?: Record<string, string>;
    textIncludes?: string[];
    textExcludes?: string[];
    setCookie?: {
      name: string;
      value?: string;
      includes?: string[];
      excludes?: string[];
    };
  };
}

interface ContractCase {
  name: string;
  endpoint: string;
  covers?: string[];
  steps: ContractStep[];
}

interface Contract {
  publicOrigin: string;
  verifier: { value: string; sha256: string };
  endpoints: Array<{ id: string; errors: string[] }>;
  cookies: { production: { session: string; verifier: string; secure: boolean } };
  cases: ContractCase[];
}

const contractPath = join(dirname(fileURLToPath(import.meta.url)), "../api-contract.json");
const contract = JSON.parse(readFileSync(contractPath, "utf8")) as Contract;

function matches(actual: unknown, expected: unknown): boolean {
  if (expected && typeof expected === "object" && !Array.isArray(expected) && "$type" in expected) {
    const kind = (expected as { $type: string }).$type;
    return kind === "string" && typeof actual === "string" && actual.length > 0;
  }
  if (Array.isArray(expected)) {
    return Array.isArray(actual)
      && actual.length === expected.length
      && expected.every((item, index) => matches(actual[index], item));
  }
  if (expected && typeof expected === "object") {
    if (!actual || typeof actual !== "object" || Array.isArray(actual)) return false;
    const actualRecord = actual as Record<string, unknown>;
    const expectedRecord = expected as Record<string, unknown>;
    const actualKeys = Object.keys(actualRecord);
    const expectedKeys = Object.keys(expectedRecord);
    if (actualKeys.length !== expectedKeys.length) return false;
    return expectedKeys.every((key) => matches(actualRecord[key], expectedRecord[key]));
  }
  return Object.is(actual, expected);
}

function substitute(value: unknown, state: { loginToken: string; sessionToken: string; previousSessionToken: string }): unknown {
  if (typeof value === "string") {
    return value
      .replaceAll("$lastLoginToken", state.loginToken)
      .replaceAll("$previousSessionToken", state.previousSessionToken)
      .replaceAll("$sessionToken", state.sessionToken);
  }
  if (Array.isArray(value)) return value.map((item) => substitute(item, state));
  if (value && typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const [key, item] of Object.entries(value)) out[key] = substitute(item, state);
    return out;
  }
  return value;
}

describe("api contract", () => {
  it("publishes a verifier pair and an example for every endpoint", async () => {
    assert.equal(contract.publicOrigin, PUBLIC_ORIGIN);
    assert.equal(await sha256Hex(contract.verifier.value), contract.verifier.sha256);
    for (const endpoint of contract.endpoints) {
      const covered = contract.cases.some((item) =>
        item.endpoint === endpoint.id || item.covers?.includes(endpoint.id));
      assert.equal(covered, true, endpoint.id);
      for (const code of endpoint.errors) {
        const shown = contract.cases.some((item) => {
          const covers = item.endpoint === endpoint.id || item.covers?.includes(endpoint.id);
          if (!covers) return false;
          return item.steps.some((step) =>
            JSON.stringify(step.response.json) === JSON.stringify({ error: code }));
        });
        assert.equal(shown, true, `${endpoint.id} ${code}`);
      }
    }
  });

  for (const example of contract.cases) {
    it(example.name, async () => {
      const { app, mailer, tasks } = createTestApp();
      const state = { loginToken: "", sessionToken: "", previousSessionToken: "" };
      const jar = new Map<string, string>();
      for (const step of example.steps) {
        const before = recorded(mailer).length;
        const request = substitute(step.request, state) as ContractStep["request"];
        const headers = new Headers(request.headers);
        if (request.method === "POST" && !headers.has("content-type")) {
          headers.set("content-type", "application/json");
        }
        if (request.json !== undefined) headers.set("content-type", headers.get("content-type") ?? "application/json");
        if (request.cookies) {
          headers.set("cookie", request.cookies.map((name) => `${name}=${jar.get(name) ?? ""}`).join("; "));
        }
        const response = await app.fetch(new Request(`${PUBLIC_ORIGIN}${request.path}`, {
          method: request.method,
          headers,
          body: request.json === undefined ? undefined : JSON.stringify(request.json),
        }));
        await settle(tasks);
        assert.equal(response.status, step.response.status, example.name);
        if (step.response.headers) {
          for (const [name, value] of Object.entries(step.response.headers)) {
            assert.equal(response.headers.get(name), value, name);
          }
        }
        if (step.response.json !== undefined) {
          const body = await response.json();
          assert.equal(matches(body, step.response.json), true, JSON.stringify(body));
          if (body && typeof body === "object" && "token" in body && typeof body.token === "string") {
            if (state.sessionToken) state.previousSessionToken = state.sessionToken;
            state.sessionToken = body.token;
          }
        } else {
          const text = await response.text();
          for (const snippet of step.response.textIncludes ?? []) assert.equal(text.includes(snippet), true, snippet);
          for (const snippet of step.response.textExcludes ?? []) assert.equal(text.includes(snippet), false, snippet);
        }
        if (step.response.setCookie) {
          const expected = step.response.setCookie;
          const line = response.headers.getSetCookie().find((item) => item.startsWith(`${expected.name}=`));
          assert.ok(line, response.headers.getSetCookie().join("\n"));
          if (expected.value) {
            assert.equal(line.split(";")[0], `${expected.name}=${expected.value}`);
          }
          for (const flag of expected.includes ?? []) {
            assert.equal(line.toLowerCase().includes(flag.toLowerCase()), true, line);
          }
          for (const flag of expected.excludes ?? []) {
            assert.equal(line.includes(flag), false, line);
          }
        }
        for (const line of response.headers.getSetCookie()) {
          const pair = line.split(";")[0] ?? "";
          const eq = pair.indexOf("=");
          const name = pair.slice(0, eq);
          const value = pair.slice(eq + 1);
          jar.set(name, value);
          if (name === "sc_session") state.sessionToken = value;
        }
        if (recorded(mailer).length > before) {
          state.loginToken = tokenFromLoginUrl(recorded(mailer).at(-1)?.loginUrl ?? "");
        }
        if (step.mailerDelta !== undefined) {
          assert.equal(recorded(mailer).length - before, step.mailerDelta);
        }
      }
    });
  }
});
