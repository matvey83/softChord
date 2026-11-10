# Decisions

## 2026-11-10 — Account and File items are created in code

The new Account menu and the four File actions are built in `wire_menus` (`src/softchord_menus.py`). `softchord_main_window.ui` is unchanged, so `softchord_main_window_ui.py` was not regenerated. Menu connects already live in that module, and adding the actions there avoids a generated-file diff. `pyuic6` on this machine matches the file's generator (PyQt6 6.11.0), so regenerating would have been valid; code was the smaller change.

## 2026-11-10 — Menu labels use three ASCII dots

Existing File items are labeled `Open Songbook...` and `Save Songbook As...`. The new items use the same three dots: `Sign In...`, `Account Settings...`, `Open From Account...`, `Upload to Account...`, `Share...`, and `Open Link...`. The dialog titles and messages are the spec's strings, unchanged.

## 2026-11-10 — The window title keeps the SoftChord prefix

A local file is `SoftChord - name (Local)[*]`. A read-only file is `SoftChord - name (Read-only)[*]`. No open file stays `SoftChord[*]`. The converted-copy title stays `SoftChord - name (converted copy, not saved)[*]`, including the `SoftChord` spelling and the `[*]` modified-marker placeholder.

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
