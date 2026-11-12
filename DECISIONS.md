# Decisions

## 2026-11-10 — Web Phase 1 songbook header

- The pull request is based on `cursor/web-always-edit-phase-b-e228` (PR 4, not merged) so the diff is the web header on top of always-edit. Desktop (`src`) and iOS are not part of this change. Editing stays on the always-edit flow already on that branch (a song opens already editing; Save and Discard stay in the edit).
- The header is only on the song list. The song page is unchanged, including the "Changes do not persist" note. Back still asks before leaving a dirty song, which is how you reach the list.
- Switching songbooks from the menu, or choosing Open Songbook File…, while the open song's draft is dirty, uses the existing Save / Don’t Save / Cancel dialog. Cancel leaves the current songbook and the draft as they are. The file picker opens only after Save or Don’t Save.
- Edits already saved for this visit are not "unsaved", so switching from the song list does not ask a second time. They are dropped once another songbook actually opens, as the spec says session edits from the old songbook are dropped.
- A file that is not a songbook, is the wrong format, or is over 50 MB does not switch, and it does not drop a dirty draft. Don’t Save has not left yet if the open fails, so the edit stays. Cancelling the system file picker after Don’t Save also leaves the draft, because no songbook was opened.
- Save on that dialog still commits the draft the same way as leaving a song. If the switch then happens, those session edits are dropped with the old songbook, and the "Saved" toast is cleared so it does not stay up on the new list.
- Opened files are held only in memory for this page visit. The demo's bytes are kept from the first load, so switching back does not fetch it again. Each successful Open adds a row under My songbooks, including a repeat of the same name. The name shown is the file name with a trailing `.songbook` removed.
- "Over 50 MB" means `file.size > 50 * 1024 * 1024`. The size is checked before the file is read.
- The spec states the message for a bad file and not a title. The notice title is "Can't open songbook". A wrong format version shows the existing `checkFormat` message. Sign in and the account items use the same notice dialog, one OK button, and do not fetch.
- The `?v=` cache buster on this branch was already `2026-11-10`, so this change uses `2026-11-10b`.
- `tools/export_toolbar_icons.js` still pointed at `softChord Viewer/softChord Viewer/Assets.xcassets/Toolbar` after the iOS project was renamed. The check now uses `SoftChord/SoftChord/Assets.xcassets/Toolbar`. The icon files were not rewritten.

## 2026-11-10 — Songbook switch history and open races

- Switching songbooks replaces the current history entry with the list (`history.replaceState` to `#/`) and bumps a songbook epoch. Song routes the page creates are `#/e/<epoch>/song/<id>`. Back to an older epoch stays on the new songbook's list instead of opening that song number. Untagged `#/song/<id>` was left as the current songbook here; the later entry on this date treats those routes as epoch 0.
- `readySql` does not keep a rejected SQLite init. The next open tries again.
- Each file open and each menu switch takes a request token. A slower open that finishes later does not become current. If it already parsed, the songbook that won is opened again.
- The search box is cleared when a songbook becomes current.
- The songbook menu still has no arrow keys, no focus move on open, and Escape does not return focus to the name button. Opening the same file name twice still adds a second row. Both are recorded in `KNOWN_ISSUES.md` and left as they are.
- The header comments and `docs/development.md` say the iOS row is pending. iOS does not have it yet.
- The cache buster is `?v=2026-11-10c` so a browser that kept `2026-11-10b` does not mix these scripts.

## 2026-11-10 — SQLite retry, old song routes, and a late reopen

- `sql-wasm.js` keeps its own `initSqlJsPromise`, including a rejection, so clearing the promise in `songbook.js` did not retry. The wrapper now drops that promise when the load rejects and keeps it when the load succeeds. A later open tries again. The wasm loader's own failure is not reported a second time, because the outer promise already rejected. The file is generated in the middle; only this outer promise and that extra rejection handler changed.
- An untagged `#/song/<id>` address is epoch 0, the songbook the page opened with. On that first songbook it still opens the song, which is what the existing links and tests do. After a switch, Back to that address goes to the new songbook's list.
- `reopenActiveSongbook` remembers the request token. If a newer open wins while it is reading, it reads the songbook that won instead of leaving the older bytes in place.
- The cache buster is `?v=2026-11-10d`, including `sql-wasm.js`, so a browser that kept `2026-11-10c` does not mix these files.

## 2026-11-10 — sql.js patch note, reopen identity, and the README line

- `softChord_web/sql-wasm.js` is sql.js 1.15.1 (SQLite 3.54.0). The wasm file matches that release; 1.15.2 ships a different wasm. A comment at the top of the file marks the local patch: a failed init is not cached. Re-apply it if the vendored file is replaced.
- After `reopenActiveSongbook` finishes a read, it keeps those songs only when the current songbook is still the one whose bytes were read. Otherwise that result is dropped and the current songbook is opened.
- The README line about opening a local songbook file into memory, for this session only, was kept. QA asked for it. The Phase 1 spec lists README wording as out of scope.
- The cache buster is `?v=2026-11-10e`.

## 2026-11-10 — Account and File items are created in code

The new Account menu and the four File actions are built in `wire_menus` (`src/softchord_menus.py`). `softchord_main_window.ui` is unchanged, so `softchord_main_window_ui.py` was not regenerated. Menu connects already live in that module, and adding the actions there avoids a generated-file diff. `pyuic6` on this machine matches the file's generator (PyQt6 6.11.0), so regenerating would have been valid; code was the smaller change.

## 2026-11-10 — Menu labels use three ASCII dots

Existing File items are labeled `Open Songbook...` and `Save Songbook As...`. The new items use the same three dots: `Sign In...`, `Account Settings...`, `Open From Account...`, `Upload to Account...`, `Share...`, and `Open Link...`. The dialog titles and messages are the spec's strings, unchanged.

## 2026-11-10 — The window title keeps the SoftChord prefix and the [*] marker, on purpose

The spec writes the title as `softChord - name (Local)`. The desktop title stays `SoftChord - name (Local)[*]` and `SoftChord - name (Read-only)[*]`. Keeping the existing `SoftChord` spelling and the `[*]` modified-marker placeholder is intentional: the converted-copy title and the empty title stay as they already were, `SoftChord - name (converted copy, not saved)[*]` and `SoftChord[*]`.

## 2026-11-10 — A separator follows Open Link

Save Songbook As... was already followed by a separator. The four new items sit under that separator. Another separator is inserted after Open Link... so they stay a group of their own, ahead of Import From Clipboard....

## 2026-11-10 — Not-available actions do not ask about a dirty draft

Sign In, Open From Account, Upload to Account, Share, and Open Link only show a message. They do not open or switch a songbook, so they do not call `confirmLeaveEdit`. Open, New, Close, Save Songbook As, Append, and `setCurrentSongbook` (including a file opened from the Finder) already ask first. Cancel returns before the file dialog and leaves the draft.

## 2026-11-10 — The not-available dialog lives with the menu wiring

The spec's file list suggested a helper on the session. It is `show_not_available` in `softchord_menus.py` instead, next to the actions that use it. The editor module is unchanged. The dialog is a `QMessageBox` parented to the main window, with the Information icon, the spec title as the window title, the spec message as the text, and only the OK button.

## 2026-11-10 — Account Settings has no slot

Account Settings... is disabled and is not connected. Enabling it later will not show a dialog until a slot is added. The new actions have no shortcuts.

## 2026-11-10 — The text fixture was the path that still used the working directory

The sample songbook in `softchord_test.py` was already resolved from `__file__`. `test_тест_song.txt` was still opened as a working-directory path. Both fixtures now use the test file's directory.

## 2026-11-10 — The read-only title assertion matches the new capitalization

`test_read_only_new_format_file_opens_read_only_with_a_message` looked for lowercase `read-only` in the window title. It now expects `(Read-only)`. The message shown when a read-only songbook opens is unchanged and still says `read-only`.

## Login

### 2026-11-10 — Magic link replaces the 6-digit code

The Server Spec's Oct 31 sign-in was a 6-digit email code and no links. This server sends a magic link instead. There is no code to type in this slice.

### 2026-11-10 — The email link is HTTPS, and the token sits in the fragment

The server builds `https://<public origin>/login?client=<web|ios|desktop>&hint=<masked>#t=<token>`. The raw token is never a query parameter and never a `softchord://` URL. `client` only changes that link. `hint` is the masked address (first character, `***`, then the domain) so the page can label the button without a lookup. It is not a secret and it is not used to authenticate. Local dev may set `PUBLIC_ORIGIN` to `http://localhost` or `http://127.0.0.1`. Any other origin, including production, must be `https`. The host comes from `PUBLIC_ORIGIN`, never from the request.

### 2026-11-10 — /login does not verify on load

Mail scanners open links. `GET /login` only returns a page. For the web client, verify runs when the person presses **Sign in as m\*\*\*@gmail.com**. For `ios` and `desktop`, that button is not on the page. Those clients only get **Open in SoftChord**, plus a hint to paste the link into the app. The button, on click, navigates to `softchord://login?token=<token>` and does not call verify. It reads the token from the fragment. After a successful web verify the page stays on `/login` and shows "You're signed in. Return to SoftChord." This worker does not serve the songbook app, so it does not redirect to `/`. When `APP_URL` is https, or http on `localhost` or `127.0.0.1`, "Return to SoftChord." links there. Any other value stays plain text. A successful verify calls `history.replaceState` so the used `#t=` token leaves the address bar and that history entry. The page sends `Content-Security-Policy` with `default-src 'none'`, `connect-src 'self'` so the Sign in button can call verify, `form-action 'none'`, `frame-ancestors 'none'`, and a per-request nonce on its script.

A failed verify shows one sentence: "Open this link on the device where you requested it." The API does not say whether the token was unknown, expired, used, or presented from the wrong device.

### 2026-11-10 — PKCE-style device binding

`request-link` requires `verifier_hash`, the hex SHA-256 of a 43–128 character URL-safe verifier. The hash is stored with the login token. Web also sends the raw verifier; the server checks it matches the hash and sets a 15-minute HttpOnly cookie. Native apps keep the verifier and send it on `verify`. Web verify reads the cookie and ignores a verifier in the body, so a copied link cannot supply one. A missing or wrong verifier is the same generic verify error, and the login token stays unused so the original device can still finish.

### 2026-11-10 — Five per email is a D1 count; per IP uses the rate-limit binding

The email cap counts `login_tokens` rows for a canonical key in the last hour, including tokens a newer request has voided. The key is the address lowercased, with any `+tag` removed. For `gmail.com` and `googlemail.com` it also drops dots and uses `gmail.com`. The message still goes to the trimmed, lowercased address the person typed. The insert is one conditional `INSERT ... SELECT` that runs only when that count is under 5, in the same transaction as voiding older unused tokens for the key. The void runs only when the insert wrote a row, so a request over the cap leaves the current token usable. Concurrent requests cannot pass the count check separately. The sixth request still returns `{ "ok": true }` and does not insert or send. The Workers Rate Limiting binding is only the per-IP burst limit: 10 requests per 60 seconds, which is the binding's longer allowed window. Tests inject the limiter. If the binding throws, the request is treated as over the cap (no send, same 200). The key is `ip:<CF-Connecting-IP>`, or `ip:unknown` when that header is absent. Over the IP cap the response matches a normal accept and nothing is stored.

### 2026-11-10 — Session cookie name and Secure come from env, not the Host header

Production name is `__Host-sc_session` (and `__Host-sc_verifier` for the PKCE cookie): HttpOnly, Secure, `Path=/`, `SameSite=Lax`, no `Domain`. Dev sets `SESSION_COOKIE_NAME=sc_session`, `VERIFIER_COOKIE_NAME=sc_verifier`, and `COOKIE_SECURE=false`. A `__Host-` name with `COOKIE_SECURE=false` is refused at startup. The web session cookie's `Max-Age` is 400 days so a browser restart can restore it. The server session itself lasts until logout. Native verify returns the raw session token in JSON and does not set the cookie. Web verify sets the cookie and does not return the raw token.

### 2026-11-10 — Cookie-authenticated POSTs check Origin

On `request-link`, a missing `Origin` is allowed for every client. A present `Origin` that is not exactly `PUBLIC_ORIGIN` is 403 for `web`, `ios`, and `desktop`, and nothing is sent. Web `verify`, and logout or logout-all when the session cookie authenticated the call, still require `Origin` to equal `PUBLIC_ORIGIN`. Bearer requests skip that check. A mismatch is 403 and does not consume the login token or revoke the session. Every POST requires a content type whose media type is exactly `application/json`. Parameters such as `charset` are fine. Anything else is 400 and is not treated as a login attempt. Known routes answer any other method with 405 `{ "error": "method_not_allowed" }`. `request-link`, like the other auth responses, sends `Cache-Control: no-store`.

### 2026-11-10 — Sessions record client, device, and hourly last use

`sessions` stores `created_at`, `last_used_at`, `client` (copied from the login token), and optional `device_label` (trimmed, at most 200 characters). `last_used_at` is updated only when it is at least an hour old. There is no idle timeout.

### 2026-11-10 — The only mailer is a recording fake, and it cannot be the production binding

`sendLoginEmail({ to, loginUrl })` has one implementation, `RecordingMailer`, used by tests and `wrangler dev`. There is no Resend client, SMTP, API key, or wrangler secret. That mailer is allowed only when `ENVIRONMENT` is `development`, `dev`, or `test`. Any other environment, including production, throws before a request is handled if the binding is `recording` or the instance is a `RecordingMailer`. `wrangler.production.jsonc` sets `MAILER` to `unconfigured` and is not a deploy target. The send is passed to `waitUntil`, so the 200 is not waiting on the mailer. Logs do not include the token, its hash, or the address.

### 2026-11-10 — Tokens are random, hashed, single-use, and voided by a newer request

Login and session tokens are 32 bytes from `crypto.getRandomValues`, encoded as base64url. The database stores SHA-256 hex only. A login token lasts 15 minutes. `consumed_at` null means it can still be used; a timestamp means it was used or voided. A new request voids older unused tokens for the same canonical key in the same transaction as the insert. No `users` row is written until verify succeeds. Valid, unknown, and rate-limited addresses share the `{ "ok": true }` body. Only bad syntax is a 400, and that path does not send. An app verifier on `verify` must be 43–128 characters of base64url; a shorter value is the same generic verify error and does not consume the token.

### 2026-11-10 — Tests hit the same SQL through in-memory SQLite

The Node test runner applies `migrations/0001_init.sql` to `node:sqlite`. An injected clock covers the 15-minute and hourly windows. Miniflare is not required for these tests. `server/api-contract.json` holds the request, response, and error examples, and a test runs them against the server. `npm run typecheck` runs `wrangler types` and then `tsc`. `worker-configuration.d.ts` is generated output and is gitignored.

### 2026-11-10 — Web verify replaces the browser's previous session

A successful web verify deletes the session row for the browser's existing session cookie, if it has one, before setting the new cookie. A failed verify leaves that session in place. The verifier cookie is cleared on success. That replacement is only the same browser. A new sign-in does not revoke other devices' sessions. Multi-device use is normal.

### 2026-11-10 — Sign out everywhere is explicit

`POST /api/auth/logout` and `POST /api/auth/logout-all` require a JSON body that is exactly `{}`. Any other JSON value is 400 `{ "error": "invalid_request" }` and deletes nothing. `logout-all` deletes every session for the signed-in user, including the caller's. Both require a session and `Content-Type: application/json`. Cookie-authenticated calls follow logout's `Origin` rule. Bearer calls skip it. A mismatch is 403 and deletes nothing. Success is `{ "ok": true }`. A web caller's session cookie is cleared.

### 2026-11-10 — Local wrangler config has no account and is not deployed

`database_id` `11111111-1111-4111-8111-111111111111` and rate-limit `namespace_id` `1001` are local placeholders. `workers_dev` and preview URLs are off. No routes and no secrets are configured.
