# Decisions

## Login

### 2026-11-10 — Magic link replaces the 6-digit code

The Server Spec's Oct 31 sign-in was a 6-digit email code and no links. This server sends a magic link instead. There is no code to type in this slice.

### 2026-11-10 — The email link is HTTPS, and the token sits in the fragment

The server builds `https://<public origin>/login?client=<web|ios|desktop>&hint=<masked>#t=<token>`. The raw token is never a query parameter and never a `softchord://` URL. `client` only changes that link. `hint` is the masked address (first character, `***`, then the domain) so the page can label the button without a lookup. It is not a secret and it is not used to authenticate. Local dev may set `PUBLIC_ORIGIN` to `http://localhost` or `http://127.0.0.1`. Any other origin, including production, must be `https`. The host comes from `PUBLIC_ORIGIN`, never from the request.

### 2026-11-10 — /login does not verify on load

Mail scanners open links. `GET /login` only returns a page. Verify runs when the person presses **Sign in as m\*\*\*@gmail.com**. For `ios` and `desktop`, the page also shows **Open in SoftChord**. That button, on click, navigates to `softchord://login?token=<token>` and does not call verify. Both controls read the token from the fragment. After a successful web verify the page does `location.replace("/")`, which drops the fragment. This server does not serve the songbook assets; `/` is the song list once the web app is mounted.

A failed verify shows one sentence: "Open this link on the device where you requested it." The API does not say whether the token was unknown, expired, used, or presented from the wrong device.

### 2026-11-10 — PKCE-style device binding

`request-link` requires `verifier_hash`, the hex SHA-256 of a 43–128 character URL-safe verifier. The hash is stored with the login token. Web also sends the raw verifier; the server checks it matches the hash and sets a 15-minute HttpOnly cookie. Native apps keep the verifier and send it on `verify`. Web verify reads the cookie and ignores a verifier in the body, so a copied link cannot supply one. A missing or wrong verifier is the same generic verify error, and the login token stays unused so the original device can still finish.

### 2026-11-10 — Five per email is a D1 count; per IP uses the rate-limit binding

The email cap counts `login_tokens` rows for that address in the last hour, including tokens a newer request has voided. The sixth request still returns `{ "ok": true }` and does not insert or send. The Workers Rate Limiting binding is only the per-IP burst limit: 10 requests per 60 seconds, which is the binding's longer allowed window. Tests inject the limiter. If the binding throws, the request is treated as over the cap (no send, same 200). The key is `ip:<CF-Connecting-IP>`, or `ip:unknown` when that header is absent. Over the IP cap the response matches a normal accept and nothing is stored.

### 2026-11-10 — Session cookie name and Secure come from env, not the Host header

Production name is `__Host-sc_session` (and `__Host-sc_verifier` for the PKCE cookie): HttpOnly, Secure, `Path=/`, `SameSite=Lax`, no `Domain`. Dev sets `SESSION_COOKIE_NAME=sc_session`, `VERIFIER_COOKIE_NAME=sc_verifier`, and `COOKIE_SECURE=false`. A `__Host-` name with `COOKIE_SECURE=false` is refused at startup. The web session cookie's `Max-Age` is 400 days so a browser restart can restore it. The server session itself lasts until logout. Native verify returns the raw session token in JSON and does not set the cookie. Web verify sets the cookie and does not return the raw token.

### 2026-11-10 — Cookie-authenticated POSTs check Origin

`PUBLIC_ORIGIN` must equal the `Origin` header on web `request-link` (it sets the verifier cookie), on web `verify`, and on logout when the session cookie is what authenticated the call. Bearer requests skip the check. A mismatch is 403 and does not consume the login token or revoke the session.

### 2026-11-10 — Sessions record client, device, and hourly last use

`sessions` stores `created_at`, `last_used_at`, `client` (copied from the login token), and optional `device_label` (trimmed, at most 200 characters). `last_used_at` is updated only when it is at least an hour old. There is no idle timeout.

### 2026-11-10 — The only mailer is a recording fake, and it cannot be the production binding

`sendLoginEmail({ to, loginUrl })` has one implementation, `RecordingMailer`, used by tests and `wrangler dev`. There is no Resend client, SMTP, API key, or wrangler secret. `ENVIRONMENT=production` with `MAILER=recording`, or a `RecordingMailer` instance in production, throws before a request is handled. `wrangler.production.jsonc` sets `MAILER` to `unconfigured` and is not a deploy target. The send is passed to `waitUntil`, so the 200 is not waiting on the mailer. Logs do not include the token, its hash, or the address.

### 2026-11-10 — Tokens are random, hashed, single-use, and voided by a newer request

Login and session tokens are 32 bytes from `crypto.getRandomValues`, encoded as base64url. The database stores SHA-256 hex only. A login token lasts 15 minutes. `consumed_at` null means it can still be used; a timestamp means it was used or voided. A new request for the same email voids older unused tokens before inserting the new one. No `users` row is written until verify succeeds. Valid, unknown, and rate-limited addresses share the `{ "ok": true }` body. Only bad syntax is a 400, and that path does not send.

### 2026-11-10 — Tests hit the same SQL through in-memory SQLite

The Node test runner applies `migrations/0001_init.sql` to `node:sqlite`. An injected clock covers the 15-minute and hourly windows. Miniflare is not required for these tests. `server/api-contract.json` holds the request, response, and error examples, and a test runs them against the server.

### 2026-11-10 — Local wrangler config has no account and is not deployed

`database_id` `11111111-1111-4111-8111-111111111111` and rate-limit `namespace_id` `1001` are local placeholders. `workers_dev` and preview URLs are off. No routes and no secrets are configured.
