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

Open From Account, Upload to Account, Share, and Open Link only show a message. They do not open or switch a songbook, so they do not call `confirmLeaveEdit`. Sign In used to be in that list; it is the real dialog now (see Login). Open, New, Close, Save Songbook As, Append, and `setCurrentSongbook` (including a file opened from the Finder) already ask first. Cancel returns before the file dialog and leaves the draft.

## 2026-11-10 — The not-available dialog lives with the menu wiring

The spec's file list suggested a helper on the session. It is `show_not_available` in `softchord_menus.py` instead, next to the actions that use it. The editor module is unchanged. The dialog is a `QMessageBox` parented to the main window, with the Information icon, the spec title as the window title, the spec message as the text, and only the OK button.

## 2026-11-10 — Account Settings has no slot

Account Settings... is disabled and is not connected. Enabling it later will not show a dialog until a slot is added. The new actions have no shortcuts.

## 2026-11-10 — The text fixture was the path that still used the working directory

The sample songbook in `softchord_test.py` was already resolved from `__file__`. `test_тест_song.txt` was still opened as a working-directory path. Both fixtures now use the test file's directory.

## 2026-11-10 — The read-only title assertion matches the new capitalization

`test_read_only_new_format_file_opens_read_only_with_a_message` looked for lowercase `read-only` in the window title. It now expects `(Read-only)`. The message shown when a read-only songbook opens is unchanged and still says `read-only`.

## 2026-11-10 — iOS Phase 1 songbook header

- The pull request is based on current `master` (51df31e), which already has the iOS always-edit flow and PR #16 (chord room, hardware Left/Right in Chords). Web and desktop are not part of this change. Editing stays on that always-edit flow (a song opens already editing; Save and Discard stay in the edit).
- The header is only on the song list. Back still asks before leaving a dirty song, which is how you reach the list. The song page keeps the always-edit flow: one `SongDraftHistory` for text and chords (a chord drag or an arrow-key nudge is one undo step), Back's Save / Don't Save / Cancel through `SongLeavePrompt.applying`, and the "Changes do not persist" note.
- Switching songbooks from the menu, or choosing Open from Files…, while the open song's draft is dirty, uses the existing Save / Don't Save / Cancel prompt. Cancel leaves the current songbook and the draft as they are. The file picker opens only after Save or Don't Save. This decision lives in `SongbookSession.request`. Because the header is on the list only, Back has usually already asked, and then the list does not ask again. The list's dirty flag is the draft the song page publishes while it is unsaved (`SongSessionEdits.unsavedDraft`), so the prompt still shows if a page was left without Back asking.
- Edits already saved for this launch are not "unsaved", so switching from the song list does not ask a second time. They are dropped once another songbook actually opens.
- A file that is not a songbook, is the wrong format, is over 50 MB, cannot be read, or is an iCloud file that is not downloaded does not switch, and it does not drop a dirty draft or session edits. Cancelling the system file picker after Don't Save also leaves the draft, because no songbook was opened.
- Save on that dialog still commits the draft the same way as leaving a song. If the switch then happens, those session edits are dropped with the old songbook.
- Opened files are copied under a temporary directory for this launch only, then opened read-only. The original is not written. Each successful Open adds a row under My songbooks, including a repeat of the same name, and its temp copy is kept so switching back works (matching the web session list). Temps are removed on the next launch, not when another file is opened. The name shown is the file name with a trailing `.songbook` removed.
- "Over 50 MB" means `file size > 50 * 1024 * 1024`. The size is checked before the file is copied or read.
- The notice title for a file that cannot be opened is "Can't open songbook". A wrong format version shows the existing `SongbookError` message ("Update this app" for a newer file). An invalid file uses the file's name, including `.songbook`. Sign in and the account items use the wording from the spec, one OK button, and do not fetch.
- File access refused uses "softChord can't read this file." An iCloud item whose downloading status is not current uses "This file isn't downloaded yet. Try again when you're online." Those two cases were classified in unit tests, not checked on a device with a real iCloud placeholder.
- The Code Reviewer Lows from PR 5 are fixed here: `SongPage` uses `SongDraftHistory` (push, undo, redo, moveChord) and `SongLeavePrompt.applying` for the leave prompt, so those tests guard the real path; `dragRecorded` is set only after a real push; a drag that ends where it started is not an undo step; the doc nits in `docs/chord_editing.md` and `docs/development.md` are corrected.

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

## Login web

### 2026-11-10 — Web sign-in is an email field, then Check your email

This change is only `softChord_web`, stacked on the songbook header (PR 6). The API is Login PR 9 (`cursor/magic-link-auth-server-c270`), which is not merged. Download, Rename, Delete, and Share keep their not-available notices and do not fetch. The open songbook stays the one already on screen.

Sign in, when an API origin is set and the browser is online, opens an email field. Cancel closes it and leaves the header signed out. Send and Resend `POST /api/auth/request-link` with `credentials: "include"`, `cache: "no-store"`, `client: "web"`, the trimmed lowercased email, a new 32-byte URL-safe verifier, and its SHA-256 hex as `verifier_hash`. The server checks that pair and sets the HttpOnly verifier cookie. The button label is "Send link". A 200, including the rate-limited same body, shows "Check your email", the address, Resend, and Cancel. This page does not verify the link and does not read `/login`. That page is the server's. A bad address is rejected here with the same syntax rule as the server and is not posted.

On load, when an origin is set, the page `GET /api/me` with `credentials: "include"`. A 200 replaces the Sign in label with that email. The control opens a menu with "Sign out (this device)" and, next to it, "Sign out everywhere". This device `POST`s `/api/auth/logout`. Everywhere asks "Sign out of SoftChord on all your devices?" and `POST`s `/api/auth/logout-all` only when that is confirmed. Both use `Content-Type: application/json`, body `{}`, credentials, and no bearer token. A 200 returns the header to Sign in. A 401 means the session is already gone, so the header returns to Sign in with no error. Any other 4xx keeps the email in the header and says "Could not sign out" with the reason (the request was not accepted, sign-out was refused, or the server rejected it). A 5xx says the server had an error and keeps the email. Only a network failure says the server could not be reached. A network error on the first `/api/me` leaves the header signed out and does not alert. Coming back online tries `/api/me` again. Becoming visible or focused does too, and those two share one check at most every 5 seconds.

The origin is `window.SOFTCHORD_API_ORIGIN` when that string is non-empty, otherwise `<meta name="softchord-api-origin">`. `config.js` sets the window value only when it is not already a string, and the committed value is empty, so the meta tag still works. That value is used only when it equals `location.origin`. The server has no CORS, a foreign Origin is 403, and the cookies are host-only, so a different address cannot sign in. Unset, `file://`, or a value that is not an http(s) origin: Sign in shows "Not available yet" / "Sign-in is coming in a later update." A configured origin on another address shows "Sign-in isn't available yet" / "The server must be on the same address as this page." Neither path makes a request. Offline, Sign in is disabled and the header shows "Offline". Send is not attempted. The published page stays unset until it is served with the API.

`softChord_web/tests/api-contract.json` is a byte copy of `server/api-contract.json` at `0775e8211158c57ff0869d1dbcf961c72ef167bd` on `cursor/magic-link-auth-server-c270`. The source comment is in `softChord_web/tests/auth_mock.js`, which loads that copy into the page mock, because JSON has no comments. A POST is JSON when the media type, before any parameter, is exactly `application/json`, so `application/json; charset=utf-8` is accepted.

The cache buster is `?v=2026-11-10j`.

## Login desktop

### 2026-11-10 — Desktop tests copy the auth contract from 0775e82

`src/fixtures/api-contract.json` is `server/api-contract.json` from `0775e8211158c57ff0869d1dbcf961c72ef167bd` (Login PR 1, branch `cursor/magic-link-auth-server-c270`). `src/fixtures/api-contract.sha` is that commit. It replaces the earlier copy from `42ca7c921a6d811dd80eb7fc533ede4e5964bb9d`, which did not yet have `/api/auth/logout-all`. The desktop tests load the fixture, hash its bytes, and mock HTTP. They do not start the server, send mail, or open a socket.

### 2026-11-10 — The API origin is the env var, then the setting

`SOFTCHORD_API_ORIGIN` wins over QSettings `auth/apiOrigin` (Ini file, organization `softChord`, application `softChord`). The value is an origin with no userinfo, path, query, or fragment. A trailing slash is dropped. It must be `https`, except `http://localhost` and `http://127.0.0.1` (a port is allowed). Any other `http` origin counts as unset, as does an empty string. Sign In then shows a message box titled `Not available yet` whose text is `Sign-in is coming in a later update.`, and the client does not build a request. Sign out with no origin only clears the local session.

### 2026-11-10 — Desktop sign-in is the contract's native verifier flow

There is no password field. The dialog asks for an email, then `POST /api/auth/request-link` with a JSON object `email` (trimmed and lowercased), `client` `desktop`, and `verifier_hash` (hex SHA-256 of a 32-byte base64url verifier). The raw verifier is not in that body. A locally invalid address is not sent. On `{ "ok": true }` the verifier is saved and the dialog says `Check your email`, with a field to paste the link. The person can close the dialog and paste later; the verifier stays until verify or sign-out.

The paste accepts the email link (`#t=<token>`), `softchord://login?token=<token>`, or the raw token. `POST /api/auth/verify` sends `token`, `verifier`, and `device_label` `SoftChord desktop`. The session token is the string `token` in that response, and it must match the same 43–128 character base64url pattern as a login token. Anything else is not stored and is not sent as `Authorization`. The Account menu label is the `email` from `GET /api/me` with `Authorization: Bearer <session>`, not the email in the verify body. 401 from `/api/me` clears the local session. Any other failure leaves the token and leaves the menu signed out.

### 2026-11-10 — Every POST is application/json, including logout

`POST` sets `Content-Type` to exactly `application/json` and a JSON object body. Logout and logout-all send `{}`. No `Origin` header is sent (a foreign Origin is 403 on the server; a missing one is allowed for a native client). `JsonEnforcingTransport`, the test mock, answers 400 `{ "error": "invalid_request" }` for a POST whose content type is not exactly that value or whose body is not a JSON object, and it does not consume the scripted success response.

### 2026-11-10 — The session token is in QSettings for this slice

`auth/sessionToken` and `auth/pendingVerifier` are plain Ini values. The OS keychain is not used, and that blocks a public build. See KNOWN_ISSUES. Sign Out does not ask for confirmation. A logout response of 200 or 401 clears the local session. Any other status or a transport error leaves the token and shows `Could not sign out.` After a successful logout the client does not call `/api/me` again.

### 2026-11-10 — Sign Out Everywhere posts logout-all

The Account menu item `Sign Out Everywhere` is shown with `Sign Out` while an email is on the menu. It `POST`s `/api/auth/logout-all` with `Authorization: Bearer <session>`, `Content-Type: application/json`, and body `{}`, then clears the local session on 200 or 401. A failure leaves the token and shows `Could not sign out everywhere.` It does not ask for confirmation. With no origin it only clears the local session.

### 2026-11-10 — Redirects are errors, and HTTP is off the UI thread

`urllib_transport` builds an opener whose redirect handler never makes a follow-up request, so `Authorization` is not copied onto another URL. A 3xx is a transport error. The timeout is 15 seconds. request-link, verify, `/api/me`, logout, logout-all, and the startup refresh run on a daemon thread, so process exit does not wait out that timeout. Quit also calls `QThreadPool.waitForDone(0)` after clearing queued pool work. Widgets and QSettings change only from the GUI thread. An exception in those calls is logged as its type name only, with no traceback and no `Authorization` value, and does not leave the slot.

### 2026-11-10 — Esc, Cancel, and a newer session drop an in-flight result

Each dialog request (request-link and verify) is tagged with a request generation. Esc and Cancel call `reject()`, which advances that generation, so a verify that finishes afterward does not save a session. A second Sign In while the dialog is open raises the same dialog. Each request is also tagged with a session generation, advanced when the saved token is stored or cleared. A late `/api/me` 401 therefore cannot wipe a newer token, and a late 200 after sign-out cannot show the email again. If that 401 arrives while the sign-in dialog still has a request in flight, the dialog result does not change the session, and the dialog re-enables its button and shows its failure text. Quit advances both generations, silences in-flight emitters so they do not touch Qt objects during teardown, and returns without waiting for workers.

### 2026-11-10 — The pending verifier expires with the server login token

The verifier is kept for `LOGIN_TTL_SECONDS` from the server at `0775e8211158c57ff0869d1dbcf961c72ef167bd`, which is 15 minutes (`15 * 60`). The server treats `expires_at > now` as still live, so a verifier that is exactly that old is dropped and verify is not attempted. The clock is `time.time`. Tests replace it.

### 2026-11-10 — The Account menu keeps the three-dot Sign In label

The label stays `Sign In...`, matching the earlier menu decision. `Sign Out` has no dots. While signed out, the visible items are `Sign In...` and the disabled `Account Settings...`. While signed in, the visible items are the email (a non-command label), `Sign Out`, `Sign Out Everywhere`, and `Account Settings...`. Account Settings is still disabled and has no slot. Open From Account, Upload to Account, Share, and Open Link are still the not-available stubs. None of these actions call `confirmLeaveEdit`.

### 2026-11-12 — main() ends with os._exit, so cleanup happens before it

After the event loop returns, `softchord.main()` flushes stdout and stderr and calls `os._exit` on every platform. atexit handlers and C++ destructors and Qt static cleanup do not run. The cleanup that matters already happened: `aboutToQuit` and `commitDataForLogout`, an explicit SQLite commit after each write, `QSettings.sync()` after each auth write, `abandon_pending` silencing in-flight emitters, and the flushed stdio. The `atexit` hook that closes worker emitters is only a fallback. The refused-second-instance test child also flushes and calls `os._exit`, so it exits 0 without Qt offscreen teardown, and the test expects exactly 0. A request-link whose POST succeeded still reports "ok" and keeps its new verifier when a newer session result (a startup 401, for example) settled first, so the dialog shows Check your email and the paste field, because the email was already sent and the link in it can still be pasted.

## Login iOS

### 2026-11-12 — Shipped iOS keeps Sign in as not available

Sign-in is on hold. When master was merged into this branch, the Phase 1 songbook header stayed, and its Sign in button still calls `presentUnavailable(.signIn)`. `ContentView` does not show `AccountHeader` or take an `AuthModel`, and `SoftChordApp` has no `.onOpenURL`. The auth types below and `AuthTests` stay in the tree, unused by the shipped views.

### 2026-11-10 — iOS follows the magic-link contract, including sign-out everywhere

The iOS client speaks the server contract at `0775e8211158c57ff0869d1dbcf961c72ef167bd` (`server/api-contract.json`). Those bytes are copied to `SoftChord/SoftChordTests/api-contract.json`. SHA-256 `9f213067d7a0e262a998175848dd58c1021443dd04f3abc56881b19df1c990d5`.

Passwordless only. `POST /api/auth/request-link` sends `email`, `client` = `ios`, and `verifier_hash`. The verifier is 32 random bytes, base64url without padding. The hash is the hex SHA-256 of that string, not of the raw bytes. The raw verifier is not sent on `request-link`. It is stored in the Keychain only after `{ "ok": true }`.

`POST /api/auth/verify` sends `{ token, verifier, device_label }`. A session token is stored only when it matches the server's bearer syntax (43–128 characters of base64url). `GET /api/me` with `Authorization: Bearer` is what the row displays. `POST /api/auth/logout` and `POST /api/auth/logout-all` send `{}` with that bearer token, then clear the Keychain on 200 or 401. A transport failure or any other status leaves the Keychain in place.

Every POST sets `Content-Type` to exactly `application/json` (no parameters) and a JSON object body. The app does not send `Origin` or cookies. Redirects are not followed. Calls run in a detached task so they are not on the main thread. The test double returns 400 unless a POST's content type is exactly `application/json`.

### 2026-11-10 — The API origin is an Info.plist key, empty by default

`SoftChordAPIOrigin` is merged from `SoftChord/SoftChord/Info.plist`. Empty means the song list says "Sign-in not configured" and the client makes no request. `https` is allowed. `http` is allowed only for host `localhost` or `127.0.0.1`, any port. A path, userinfo, query, fragment, or any other `http` host is refused with no request. The refused `http` row says "Sign-in requires HTTPS."

### 2026-11-10 — Where sign-in sits, and which links open it

iOS has no account menu. The email field is a row above Search on the song list. After a link is requested the row says "Check your email" and can take a pasted link. `softchord://login?token=` is registered as a URL scheme. The https form is `/login` with the token in the fragment `t`, matching the server. `http` links are accepted only for `localhost` and `127.0.0.1`. There is no associated domain, so the email's https link does not open the app by itself.

`device_label` is `UIDevice.current.model`, trimmed, at most 200 characters, or `iOS` when that is empty.

The session token and the pending verifier are generic passwords, service `com.matveygirey.softChord-Viewer.auth`, accessible after first unlock, this device only. The verifier item also stores the issue time, in milliseconds. At 900 seconds it is deleted, and the row leaves "Check your email" (on appear, before verify, and from a timer while that row is showing). Requests time out at 15 seconds.

Dismiss, sign-out, the start of verify, and storing a session each bump a generation counter. An in-flight verify does not save a session after dismiss. A `/api/me` 401 for an older token does not clear a session stored later, and a late 200 does not show an email after sign-out. Overlapping calls leave the row busy until the last one finishes. Logout clears the Keychain only when the stored token is still the one that started the call. 401 does that. 403 and 405 do not. A failed "Sign Out Everywhere" says "Could not sign out everywhere." The button asks "Sign out of every device?" before it calls the network.

Pasted and opened `https` or `http` links must match `SoftChordAPIOrigin` and the token must be base64url, 43–128 characters. `softchord://login?token=` uses the same token rule. A link that arrives while a call is busy is kept and used when that call finishes, with "This link will be used when the current sign-in finishes." Redirects are refused for every request, including one that already carries `Authorization`. The bearer token is not logged.

### 2026-11-10 — Not built on this machine

This VM has no Xcode. The Swift is limited to iOS 16 APIs. New Swift files and the contract fixture sit in synchronized Xcode folders (app target and SoftChordTests). `Info.plist` is excluded from that folder's resource membership and referenced as `INFOPLIST_FILE` so it merges with the generated plist.
