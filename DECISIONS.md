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
