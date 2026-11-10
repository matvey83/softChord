# Decisions

## Login

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

Dismiss or sign-out bumps a generation counter. An in-flight verify does not save a session after dismiss. A late `/api/me` does not clear a newer token or show an email after sign-out. Logout clears the Keychain only when the stored token is still the one that started the call. 401 does that. 403 and 405 do not. A failed "Sign Out Everywhere" says "Could not sign out everywhere." The button asks "Sign out of every device?" before it calls the network.

Pasted and opened `https` or `http` links must match `SoftChordAPIOrigin` and the token must be base64url, 43–128 characters. `softchord://login?token=` uses the same token rule. A link that arrives while a call is busy is kept and used when that call finishes, with "This link will be used when the current sign-in finishes." Redirects are refused for every request, including one that already carries `Authorization`. The bearer token is not logged.

### 2026-11-10 — Not built on this machine

This VM has no Xcode. The Swift is limited to iOS 16 APIs. New Swift files and the contract fixture sit in synchronized Xcode folders (app target and SoftChordTests). `Info.plist` is excluded from that folder's resource membership and referenced as `INFOPLIST_FILE` so it merges with the generated plist.
