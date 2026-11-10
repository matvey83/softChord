# Decisions

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

## Login

### 2026-11-10 — Desktop tests copy the auth contract from 0775e82

`src/fixtures/api-contract.json` is `server/api-contract.json` from `0775e8211158c57ff0869d1dbcf961c72ef167bd` (Login PR 1, branch `cursor/magic-link-auth-server-c270`). `src/fixtures/api-contract.sha` is that commit. It replaces the earlier copy from `42ca7c921a6d811dd80eb7fc533ede4e5964bb9d`, which did not yet have `/api/auth/logout-all`. The desktop tests load the fixture, hash its bytes, and mock HTTP. They do not start the server, send mail, or open a socket.

### 2026-11-10 — The API origin is the env var, then the setting

`SOFTCHORD_API_ORIGIN` wins over QSettings `auth/apiOrigin` (Ini file, organization `softChord`, application `softChord`). The value is an origin with no userinfo, path, query, or fragment. A trailing slash is dropped. It must be `https`, except `http://localhost` and `http://127.0.0.1` (a port is allowed). Any other `http` origin counts as unset, as does an empty string. Sign In then shows a message box titled `Sign in` whose text is `Sign-in not configured`, and the client does not build a request. Sign out with no origin only clears the local session.

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

`urllib_transport` builds an opener whose redirect handler never makes a follow-up request, so `Authorization` is not copied onto another URL. A 3xx is a transport error. The timeout is 15 seconds. request-link, verify, `/api/me`, logout, logout-all, and the startup refresh run on `QThreadPool`. Widgets and QSettings change only from the GUI thread. An exception in those calls is logged as its type name only, with no traceback and no `Authorization` value, and does not leave the slot.

### 2026-11-10 — Esc, Cancel, and a newer session drop an in-flight result

Each dialog request (request-link and verify) is tagged with a request generation. Esc and Cancel call `reject()`, which advances that generation, so a verify that finishes afterward does not save a session. A second Sign In while the dialog is open raises the same dialog. Each request is also tagged with a session generation, advanced when the saved token is stored or cleared. A late `/api/me` 401 therefore cannot wipe a newer token, and a late 200 after sign-out cannot show the email again. Quit advances both generations and returns without waiting for the thread pool.

### 2026-11-10 — The pending verifier expires with the server login token

The verifier is kept for `LOGIN_TTL_SECONDS` from the server at `0775e8211158c57ff0869d1dbcf961c72ef167bd`, which is 15 minutes (`15 * 60`). The server treats `expires_at > now` as still live, so a verifier that is exactly that old is dropped and verify is not attempted. The clock is `time.time`. Tests replace it.

### 2026-11-10 — The Account menu keeps the three-dot Sign In label

The label stays `Sign In...`, matching the earlier menu decision. `Sign Out` has no dots. While signed out, the visible items are `Sign In...` and the disabled `Account Settings...`. While signed in, the visible items are the email (a non-command label), `Sign Out`, `Sign Out Everywhere`, and `Account Settings...`. Account Settings is still disabled and has no slot. Open From Account, Upload to Account, Share, and Open Link are still the not-available stubs. None of these actions call `confirmLeaveEdit`.
