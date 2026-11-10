# Known issues

- Desktop: Undo cannot cross a Save. Save drops the draft's undo steps (by design).
- Desktop: `src/softchord_test.py` import tests fail when run from the repo root. The fixture `test_тест_song.txt` is opened by a path relative to the current directory (`song_file = "test_тест_song.txt"`, then `open(song_file)`) instead of a path next to `__file__`. Running those tests from `src/` finds the fixture. Running them from the repo root does not. Not fixed here.
- Desktop: the desktop unittest process segfaults with exit 139 at interpreter shutdown after all tests pass. Likely Qt teardown. Not triaged.
- Web: `softChord_web/tests/toolbar_mirror.test.js` fails because `tools/export_toolbar_icons.js` writes and checks `softChord Viewer/softChord Viewer/Assets.xcassets/Toolbar`, and that directory is not in the repo. The iOS catalog is `SoftChord/SoftChord/Assets.xcassets/Toolbar`. Suspected cause: the iOS project was renamed and the exporter path was not updated. Not fixed here (it is outside always-edit, and the check also covers iOS assets).
- Web. Symptom: Ctrl or Cmd+K during IME composition on Lyrics can leave `composing` true. Suspected cause: `selectSegment` does not check or clear `composing`, which the old `startEditing` did before it changed mode.
- Web. Symptom: when `showModal` is unavailable, leaving a dirty song offers only discard or cancel, and there is no Save. Suspected cause: `askBeforeLeaving` falls back to `window.confirm`, which has only those two answers, and OK runs the leave callback without saving.
- Web. Symptom: a chord placed past the end of the text in a damaged file is never shown. It used to stay visible until the first edit. Suspected cause: the song is always opened through the normalized draft (`beginDraft` calls `normalizeSong`), so that chord is dropped before the first paint.
- Desktop. Symptom: no unit test covers a dirty draft going through `confirmLeaveEdit(keep_open=True)` Save or Discard and then resuming on the same segment. The dirty-switch Save and Don't Save paths were checked only by a QA script. Suspected cause: `test_dirty_leave_cancel_discard_and_save` calls `confirmLeaveEdit()` without `keep_open`, so it never checks `_resumeOpenEdit`.
- Desktop. Symptom: `test_renumber_stays_on_the_segment` replaces `app.question` and later tests in that process can still see the replacement. Suspected cause: the test assigns `self.app.question = lambda *args, **kwargs: True` and does not restore the previous `question`.

- iOS: there is no New, Paste, or Import song UI. `SongEditSegment.forOpen` opens an empty new song on Lyrics and everything else on Chords, and that helper is unit-tested, but the app only opens existing songs, so they always start on Chords.
- iOS: title, number, and notes are not editable, so they cannot dirty the draft the way they do on desktop.
- iOS: the song toolbar wraps onto another row instead of putting overflow items in a "..." menu. `SongShareMenu` can include Chords and Lyrics, but the song page does not present that menu, so the segment can only be changed from the toolbar.
- iOS: on Lyrics, the zoom buttons scale the lyric font, but a pinch does not zoom, and the sheet does not fit-to-width. Those both work on Chords.

- iOS: swipe-back on a dirty draft needs a device check. The nav bar is hidden, which should disable swipe-back, but that has not been verified on a device. If swipe-back still works, a dirty draft is lost silently.
- iOS: every keystroke is its own undo step.
- iOS: `lyricDraftChanged` treats retyping back to a history entry as undo or redo.
- iOS: tapping Lyrics is ignored while a switch waits for the keyboard.
- iOS: `commitEdit` can save `steps:0` and lose the key.
- iOS: Lyrics now zooms with the toolbar buttons, fit-to-width applies on Chords, and Copy and Print use the unsaved draft.

- Login (iOS): `SoftChordAPIOrigin` is empty, so sign-in shows "Sign-in not configured" and does not call the network. The production origin still needs the account owner.
- Login (iOS): The email's https link is pasted into the app. There is no associated domain and no apple-app-site-association file, so that link does not open the app by itself. `softchord://login?token=` does, once the system delivers it. Say if universal links should wait for a domain.
- Login (iOS): `device_label` is the device model (`iPhone` or `iPad`), not the device name. Say if that label should be different.
- Login (iOS): The session token and the pending verifier stay in the Keychain on this device only (not iCloud Keychain) until sign-out. Say if a session should sync to the user's other devices.
- Login (iOS): A new sign-in on this phone replaces the Keychain token and does not revoke the previous server session. Sign Out Everywhere does. Say if a new sign-in should revoke the previous session on this phone.
- Login (iOS): This was not built or run. It needs a Mac with Xcode to compile SoftChordTests, confirm the plist key and `softchord` scheme, and walk through sign-in against the local server.
