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
