export const EMAIL_LIMIT = 5;
export const EMAIL_WINDOW_SECONDS = 60 * 60;
export const LOGIN_TTL_SECONDS = 15 * 60;
export const VERIFIER_COOKIE_SECONDS = LOGIN_TTL_SECONDS;
export const SESSION_COOKIE_SECONDS = 400 * 24 * 60 * 60;
export const LAST_USED_INTERVAL_SECONDS = 60 * 60;
export const DEVICE_LABEL_MAX = 200;

export interface AppConfig {
  ENVIRONMENT: string;
  MAILER: string;
  PUBLIC_ORIGIN: string;
  SESSION_COOKIE_NAME: string;
  VERIFIER_COOKIE_NAME: string;
  COOKIE_SECURE: string;
}

export function cookieSecure(env: AppConfig): boolean {
  return env.COOKIE_SECURE === "true";
}

export function assertRuntimeConfig(env: AppConfig): void {
  const secure = cookieSecure(env);
  if (env.COOKIE_SECURE !== "true" && env.COOKIE_SECURE !== "false") {
    throw new Error("COOKIE_SECURE must be true or false");
  }
  for (const name of [env.SESSION_COOKIE_NAME, env.VERIFIER_COOKIE_NAME]) {
    if (!name) throw new Error("cookie name is empty");
    if (name.startsWith("__Host-") && !secure) {
      throw new Error(`${name} requires COOKIE_SECURE=true`);
    }
  }
  if (env.ENVIRONMENT === "production" && !secure) {
    throw new Error("production cookies must be Secure");
  }
  if (env.ENVIRONMENT === "production") {
    for (const name of [env.SESSION_COOKIE_NAME, env.VERIFIER_COOKIE_NAME]) {
      if (!name.startsWith("__Host-")) {
        throw new Error("production cookie names must use the __Host- prefix");
      }
    }
  }

  let origin: URL;
  try {
    origin = new URL(env.PUBLIC_ORIGIN);
  } catch {
    throw new Error("PUBLIC_ORIGIN is not a URL");
  }
  if (origin.pathname !== "/" || origin.search || origin.hash || origin.username || origin.password) {
    throw new Error("PUBLIC_ORIGIN must be an origin");
  }
  const local = origin.hostname === "localhost" || origin.hostname === "127.0.0.1";
  if (!local && origin.protocol !== "https:") {
    throw new Error("PUBLIC_ORIGIN must be https except on localhost");
  }
  if (env.ENVIRONMENT === "production" && origin.protocol !== "https:") {
    throw new Error("production PUBLIC_ORIGIN must be https");
  }
}
