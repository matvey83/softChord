# SoftChord auth server

Local magic-link login API. It does not send real email, and it is not set up to deploy.

## Run locally

```bash
cd server
npm install
npx wrangler d1 migrations apply softchord --local
npm test
npx wrangler dev
```

`wrangler dev` serves `http://localhost:8787`. The dev config uses a placeholder D1 id and a placeholder rate-limit namespace. Neither is a real Cloudflare resource. Do not add an account id, a secret, or a mail provider here, and do not run `wrangler deploy`.

`POST /api/auth/request-link` accepts `{ "email", "client", "verifier_hash" }`. `client` is `web`, `ios`, or `desktop`. Web also sends `verifier`, the raw PKCE verifier. A missing `Origin` is allowed. An `Origin` that is present must be `http://localhost:8787`. The response is always `{ "ok": true }` when the address is syntactically valid, including when the hourly cap or the per-IP limiter says not to send. Nothing is delivered: the only mailer is an in-memory recorder used by tests. A dev request schedules that recorder and then drops the message.

The link in a test email looks like `https://<origin>/login?client=ios&hint=m***%40gmail.com#t=<token>`. The token is only in the fragment. The page does not verify on load. On the web, press **Sign in**. `ios` and `desktop` only show **Open in SoftChord**, which goes to `softchord://login?token=<token>` when pressed.

Dev cookies are `sc_verifier` and `sc_session` (HttpOnly, not Secure). Those names come from `wrangler.jsonc`, not from the request host.

After a web sign-in the page stays on `/login` and says you're signed in. Set `APP_URL` to an http or https URL to make "Return to SoftChord." a link; leave it empty for text only. `POST /api/auth/logout-all` ends every session for that user. Signing in on one device leaves the others signed in.

## Tests

`npm test` uses Node's built-in test runner and an in-memory SQLite database that applies `migrations/0001_init.sql`. `npm run typecheck` runs `wrangler types` first, which writes `worker-configuration.d.ts`, and then runs `tsc`. That file is generated and gitignored, so plain `npx tsc` fails without it. `server/api-contract.json` is the request and response examples client mocks should load.
