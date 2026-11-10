import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { createApp, type AppDeps } from "../src/app.ts";
import type { AppConfig } from "../src/config.ts";
import type { SqlDatabase } from "../src/db.ts";
import { RecordingMailer, type LoginMailer } from "../src/mailer.ts";
import { allowAllLimiter, type IpRateLimiter } from "../src/rate-limit.ts";
import { openSqlite } from "./sqlite.ts";

export const PUBLIC_ORIGIN = "https://songs.example";

export const VERIFIER = "Gom_dJiEsQeMik8sm58Q4xt4rDESd-H8z2s-jNvPnAE";
export const VERIFIER_HASH = "409a1dfd38791e76dbd352152207e00a8a3379fe17a96122eb07eb449b7d288e";
export const WRONG_VERIFIER = "Qr4MgDAm0aB-s6pLkfOAoK-64CTFRrUNtVZLA0X-GJw";

export const testEnv: AppConfig = {
  ENVIRONMENT: "development",
  MAILER: "recording",
  PUBLIC_ORIGIN,
  SESSION_COOKIE_NAME: "sc_session",
  VERIFIER_COOKIE_NAME: "sc_verifier",
  COOKIE_SECURE: "false",
};

export interface TestApp {
  app: ReturnType<typeof createApp>;
  db: SqlDatabase;
  mailer: LoginMailer;
  env: AppConfig;
  tasks: Promise<unknown>[];
}

function migrationSql(): string {
  const directory = join(dirname(fileURLToPath(import.meta.url)), "../migrations");
  return readdirSync(directory)
    .filter((name) => name.endsWith(".sql"))
    .sort()
    .map((name) => readFileSync(join(directory, name), "utf8"))
    .join("\n");
}

export function createTestApp(options?: {
  now?: () => number;
  limiter?: IpRateLimiter;
  mailer?: LoginMailer;
  env?: AppConfig;
  yield?: boolean;
}): TestApp {
  const mailer = options?.mailer ?? new RecordingMailer();
  const db = openSqlite(migrationSql(), { yield: options?.yield });
  const tasks: Promise<unknown>[] = [];
  const env = options?.env ?? testEnv;
  const deps: AppDeps = {
    db,
    mailer,
    ipLimiter: options?.limiter ?? allowAllLimiter(),
    env,
    waitUntil(promise) {
      tasks.push(promise);
    },
  };
  if (options?.now) deps.now = options.now;
  return { app: createApp(deps), db, mailer, env, tasks };
}

export function recorded(mailer: LoginMailer): RecordingMailer["sent"] {
  if (!(mailer instanceof RecordingMailer)) throw new Error("mailer is not recording");
  return mailer.sent;
}

export async function settle(tasks: Promise<unknown>[]): Promise<void> {
  await Promise.all(tasks);
}

export function tokenFromLoginUrl(loginUrl: string): string {
  const url = new URL(loginUrl);
  const token = new URLSearchParams(url.hash.replace(/^#/, "")).get("t");
  if (!token) throw new Error("login url is missing the token fragment");
  return token;
}

export async function postJson(
  app: { fetch: (request: Request) => Promise<Response> | Response },
  path: string,
  body: unknown,
  headers: Record<string, string> = {},
): Promise<Response> {
  return app.fetch(
    new Request(`${PUBLIC_ORIGIN}${path}`, {
      method: "POST",
      headers: { "content-type": "application/json", ...headers },
      body: JSON.stringify(body),
    }),
  );
}
