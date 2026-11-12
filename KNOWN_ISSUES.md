# Known issues

- Desktop: Undo cannot cross a Save. Save drops the draft's undo steps (by design).
- Desktop tests: under pytest, `softchord_test.py` can exit 139 when Qt tears down after the tests have passed. pytest is not a repo dependency. The direct runner is `python softchord_test.py` from `src/` (it reports the test result and exits before that teardown).
- Web. Symptom: the songbook ▾ menu does not move focus into the menu when it opens, has no arrow-key navigation, and Escape closes it without returning focus to the songbook button. Not fixed here.
- Web. Symptom: opening a file whose name is already in My songbooks adds another row with the same name. The check mark shows which copy is open. Not fixed here.
- Web. Symptom: Ctrl or Cmd+K during IME composition on Lyrics can leave `composing` true. Suspected cause: `selectSegment` does not check or clear `composing`, which the old `startEditing` did before it changed mode.
- Web. Symptom: when `showModal` is unavailable, leaving a dirty song offers only discard or cancel, and there is no Save. Suspected cause: `askBeforeLeaving` falls back to `window.confirm`, which has only those two answers, and OK runs the leave callback without saving.
- Web. Symptom: a chord placed past the end of the text in a damaged file is never shown. It used to stay visible until the first edit. Suspected cause: the song is always opened through the normalized draft (`beginDraft` calls `normalizeSong`), so that chord is dropped before the first paint.
- Web. Symptom: the account menu (the signed-in email) does not move focus into the menu when it opens, has no arrow-key navigation, and Escape closes it without returning focus to the email button. Same gap as the songbook menu. Not fixed here.
- Web. Symptom: Sign in says the server is not configured and does not call an API. `softChord_web/config.js` leaves the origin empty because there is no SoftChord domain yet. When a server exists, that origin has to be this page's own address. Needs that origin. Not fixed here.


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
- Login: There is no SoftChord domain or Cloudflare account yet. `server/wrangler.jsonc` uses placeholder D1 id `11111111-1111-4111-8111-111111111111` and rate-limit namespace `1001` for local dev only. The production origin, a real D1 id, and a real rate-limit namespace need the account owner before any deploy.
- Login: The per-IP burst is 10 requests per 60 seconds, because the Workers Rate Limiting binding only allows a 10- or 60-second window. Say if that burst should be different before launch.
- Login: The web session cookie lasts 400 days, and the server session lasts until sign-out. Say if sign-in on the web should expire sooner. There is no server-side session expiry yet.
- Login: The masked address is in the login link query (`hint`), so it can show up in access logs.
- Login: Check what Workers tracing records for `/login` and `verify`, so a trace cannot keep the token or the address.
- Login (Low): The cap key doesn't cover other provider aliases (Yahoo '-', Fastmail subdomains, IDN).
- Login: api-contract.json logout errors omit invalid_request; add it, then re-copy the contract to web, desktop and iOS fixtures.
- Login: The web and desktop mocks don't enforce a {} body.

## Fixed

- 2026-11-10: `src/softchord_test.py` now opens `test_тест_song.txt` from the test file's directory (`__file__`), so the text fixture does not depend on the working directory. The sample songbook path was already resolved from `__file__`.
- 2026-11-10: `test_renumber_stays_on_the_segment` restores `app.question` after forcing an answer, so the stand-in does not stay on the shared test app.
- 2026-11-10: Dirty leave with `keep_open=True` had no test. `test_dirty_keep_open_cancel_discard_and_save` covers Save, Don't Save, and Cancel while the song stays on screen.
