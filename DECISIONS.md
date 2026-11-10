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

## Login web

### 2026-11-10 — Web sign-in is an email field, then Check your email

This change is only `softChord_web`, stacked on the songbook header (PR 6). The API is Login PR 9 (`cursor/magic-link-auth-server-c270`), which is not merged. Download, Rename, Delete, and Share keep their not-available notices and do not fetch. The open songbook stays the one already on screen.

Sign in, when an API origin is set and the browser is online, opens an email field. Cancel closes it and leaves the header signed out. Send and Resend `POST /api/auth/request-link` with `credentials: "include"`, `cache: "no-store"`, `client: "web"`, the trimmed lowercased email, a new 32-byte URL-safe verifier, and its SHA-256 hex as `verifier_hash`. The server checks that pair and sets the HttpOnly verifier cookie. The button label is "Send link". A 200, including the rate-limited same body, shows "Check your email", the address, Resend, and Cancel. This page does not verify the link and does not read `/login`. That page is the server's. A bad address is rejected here with the same syntax rule as the server and is not posted.

On load, when an origin is set, the page `GET /api/me` with `credentials: "include"`. A 200 replaces the Sign in label with that email. The control opens a menu with "Sign out (this device)" and, next to it, "Sign out everywhere". This device `POST`s `/api/auth/logout`. Everywhere `POST`s `/api/auth/logout-all`. Both use `Content-Type: application/json`, body `{}`, credentials, and no bearer token. A 200 returns the header to Sign in. A 401 means the session is already gone, so the header returns to Sign in with no error. Any other 4xx keeps the email in the header and says "Could not sign out" with the reason (the request was not accepted, sign-out was refused, or the server rejected it). A 5xx says the server had an error and keeps the email. Only a network failure says the server could not be reached. A network error on the first `/api/me` leaves the header signed out and does not alert. Coming back online tries `/api/me` again. Becoming visible or focused does too, and those two share one check at most every 5 seconds.

The origin is `window.SOFTCHORD_API_ORIGIN` when that string is non-empty, otherwise `<meta name="softchord-api-origin">`. `config.js` sets the window value only when it is not already a string, and the committed value is empty, so the meta tag still works. That value is used only when it equals `location.origin`. The server has no CORS, a foreign Origin is 403, and the cookies are host-only, so a different address cannot sign in. Unset, `file://`, or a value that is not an http(s) origin: Sign in shows "Sign-in isn't available yet" / "The server is not configured." A configured origin on another address shows "Sign-in isn't available yet" / "The server must be on the same address as this page." Neither path makes a request. Offline, Sign in is disabled and the header shows "Offline". Send is not attempted. The published page stays unset until it is served with the API.

`softChord_web/tests/api-contract.json` is a byte copy of `server/api-contract.json` at `0775e8211158c57ff0869d1dbcf961c72ef167bd` on `cursor/magic-link-auth-server-c270`. The source comment is in `softChord_web/tests/auth_mock.js`, which loads that copy into the page mock, because JSON has no comments. A POST is JSON when the media type, before any parameter, is exactly `application/json`, so `application/json; charset=utf-8` is accepted.

The cache buster is `?v=2026-11-10i`.
