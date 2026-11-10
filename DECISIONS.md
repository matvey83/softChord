# Decisions

## Login

### 2026-11-10 — Magic link replaces the 6-digit code

The Server Spec's Oct 31 sign-in was a 6-digit email code and no links. This server sends a magic link instead. There is no code to type in this slice.

### 2026-11-10 — The email link is HTTPS, and the token sits in the fragment

The server builds `https://<public origin>/login?client=<web|ios|desktop>&hint=<masked>#t=<token>`. The raw token is never a query parameter and never a `softchord://` URL. `client` only changes that link. `hint` is the masked address (first character, `***`, then the domain) so the page can label the button without a lookup. It is not a secret and it is not used to authenticate. Local dev may set `PUBLIC_ORIGIN` to `http://localhost` or `http://127.0.0.1`. Any other origin, including production, must be `https`. The host comes from `PUBLIC_ORIGIN`, never from the request.

### 2026-11-10 — /login does not verify on load

Mail scanners open links. `GET /login` only returns a page. For the web client, verify runs when the person presses **Sign in as m\*\*\*@gmail.com**. For `ios` and `desktop`, that button is not on the page. Those clients only get **Open in SoftChord**, plus a hint to paste the link into the app. The button, on click, navigates to `softchord://login?token=<token>` and does not call verify. It reads the token from the fragment. After a successful web verify the page does `location.replace("/")`, which drops the fragment. This server does not serve the songbook assets; `/` is the song list once the web app is mounted. The page sends `Content-Security-Policy` with `default-src 'none'`, `connect-src 'self'` so the Sign in button can call verify, `form-action 'none'`, `frame-ancestors 'none'`, and a per-request nonce on its script.

A failed verify shows one sentence: "Open this link on the device where you requested it." The API does not say whether the token was unknown, expired, used, or presented from the wrong device.

### 2026-11-10 — PKCE-style device binding

`request-link` requires `verifier_hash`, the hex SHA-256 of a 43–128 character URL-safe verifier. The hash is stored with the login token. Web also sends the raw verifier; the server checks it matches the hash and sets a 15-minute HttpOnly cookie. Native apps keep the verifier and send it on `verify`. Web verify reads the cookie and ignores a verifier in the body, so a copied link cannot supply one. A missing or wrong verifier is the same generic verify error, and the login token stays unused so the original device can still finish.

### 2026-11-10 — Five per email is a D1 count; per IP uses the rate-limit binding

The email cap counts `login_tokens` rows for a canonical key in the last hour, including tokens a newer request has voided. The key is the address lowercased, with any `+tag` removed. For `gmail.com` and `googlemail.com` it also drops dots and uses `gmail.com`. The message still goes to the trimmed, lowercased address the person typed. The insert is one conditional `INSERT ... SELECT` that runs only when that count is under 5, in the same transaction as voiding older unused tokens for the key. The void runs only when the insert wrote a row, so a request over the cap leaves the current token usable. Concurrent requests cannot pass the count check separately. The sixth request still returns `{ "ok": true }` and does not insert or send. The Workers Rate Limiting binding is only the per-IP burst limit: 10 requests per 60 seconds, which is the binding's longer allowed window. Tests inject the limiter. If the binding throws, the request is treated as over the cap (no send, same 200). The key is `ip:<CF-Connecting-IP>`, or `ip:unknown` when that header is absent. Over the IP cap the response matches a normal accept and nothing is stored.

### 2026-11-10 — Session cookie name and Secure come from env, not the Host header

Production name is `__Host-sc_session` (and `__Host-sc_verifier` for the PKCE cookie): HttpOnly, Secure, `Path=/`, `SameSite=Lax`, no `Domain`. Dev sets `SESSION_COOKIE_NAME=sc_session`, `VERIFIER_COOKIE_NAME=sc_verifier`, and `COOKIE_SECURE=false`. A `__Host-` name with `COOKIE_SECURE=false` is refused at startup. The web session cookie's `Max-Age` is 400 days so a browser restart can restore it. The server session itself lasts until logout. Native verify returns the raw session token in JSON and does not set the cookie. Web verify sets the cookie and does not return the raw token.

### 2026-11-10 — Cookie-authenticated POSTs check Origin

On `request-link`, a missing `Origin` is allowed for every client. A present `Origin` that is not exactly `PUBLIC_ORIGIN` is 403 for `web`, `ios`, and `desktop`, and nothing is sent. Web `verify`, and logout when the session cookie authenticated the call, still require `Origin` to equal `PUBLIC_ORIGIN`. Bearer requests skip that check. A mismatch is 403 and does not consume the login token or revoke the session. Every POST requires a content type whose media type is exactly `application/json`. Parameters such as `charset` are fine. Anything else is 400 and is not treated as a login attempt. Known routes answer any other method with 405 `{ "error": "method_not_allowed" }`. `request-link`, like the other auth responses, sends `Cache-Control: no-store`.

### 2026-11-10 — Sessions record client, device, and hourly last use

`sessions` stores `created_at`, `last_used_at`, `client` (copied from the login token), and optional `device_label` (trimmed, at most 200 characters). `last_used_at` is updated only when it is at least an hour old. There is no idle timeout.

### 2026-11-10 — The only mailer is a recording fake, and it cannot be the production binding

`sendLoginEmail({ to, loginUrl })` has one implementation, `RecordingMailer`, used by tests and `wrangler dev`. There is no Resend client, SMTP, API key, or wrangler secret. That mailer is allowed only when `ENVIRONMENT` is `development`, `dev`, or `test`. Any other environment, including production, throws before a request is handled if the binding is `recording` or the instance is a `RecordingMailer`. `wrangler.production.jsonc` sets `MAILER` to `unconfigured` and is not a deploy target. The send is passed to `waitUntil`, so the 200 is not waiting on the mailer. Logs do not include the token, its hash, or the address.

### 2026-11-10 — Tokens are random, hashed, single-use, and voided by a newer request

Login and session tokens are 32 bytes from `crypto.getRandomValues`, encoded as base64url. The database stores SHA-256 hex only. A login token lasts 15 minutes. `consumed_at` null means it can still be used; a timestamp means it was used or voided. A new request voids older unused tokens for the same canonical key in the same transaction as the insert. No `users` row is written until verify succeeds. Valid, unknown, and rate-limited addresses share the `{ "ok": true }` body. Only bad syntax is a 400, and that path does not send. An app verifier on `verify` must be 43–128 characters of base64url; a shorter value is the same generic verify error and does not consume the token.

### 2026-11-10 — Tests hit the same SQL through in-memory SQLite

The Node test runner applies `migrations/0001_init.sql` to `node:sqlite`. An injected clock covers the 15-minute and hourly windows. Miniflare is not required for these tests. `server/api-contract.json` holds the request, response, and error examples, and a test runs them against the server. `npm run typecheck` runs `wrangler types` and then `tsc`. `worker-configuration.d.ts` is generated output and is gitignored.

### 2026-11-10 — Web verify replaces the browser's previous session

A successful web verify deletes the session row for the browser's existing session cookie, if it has one, before setting the new cookie. A failed verify leaves that session in place. The verifier cookie is cleared on success.

### 2026-11-10 — Local wrangler config has no account and is not deployed

`database_id` `11111111-1111-4111-8111-111111111111` and rate-limit `namespace_id` `1001` are local placeholders. `workers_dev` and preview URLs are off. No routes and no secrets are configured.
