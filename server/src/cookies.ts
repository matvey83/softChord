import { deleteCookie, getCookie, setCookie } from "hono/cookie";
import type { Context } from "hono";

import { cookieSecure, type AppConfig } from "./config.ts";

type CookieContext = Context;

export function readCookie(c: CookieContext, name: string): string | undefined {
  return getCookie(c, name);
}

export function writeCookie(
  c: CookieContext,
  env: AppConfig,
  name: string,
  value: string,
  maxAge: number,
): void {
  setCookie(c, name, value, {
    httpOnly: true,
    secure: cookieSecure(env),
    sameSite: "Lax",
    path: "/",
    maxAge,
  });
}

export function clearCookie(c: CookieContext, env: AppConfig, name: string): void {
  deleteCookie(c, name, {
    path: "/",
    secure: cookieSecure(env),
    sameSite: "Lax",
  });
}

export function originAllowed(request: Request, publicOrigin: string): boolean {
  return request.headers.get("origin") === publicOrigin;
}
