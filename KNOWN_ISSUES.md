# Known issues

- Desktop: Undo cannot cross a Save. Save drops the draft's undo steps (by design).
- Desktop tests: under pytest, `softchord_test.py` can exit 139 when Qt tears down after the tests have passed. pytest is not a repo dependency. The direct runner is `python softchord_test.py` from `src/` (it reports the test result and exits before that teardown).
- Login: BLOCKS a public build. The desktop session token and the pending verifier are stored in QSettings as plain text (on Linux, the Ini file under the `softChord` organization). Move them to the OS keychain/keyring before any public build.
- Login: The desktop app does not register the `softchord://` URL scheme, so the email's Open in SoftChord button does not launch it. Paste the link into the sign-in dialog. Say if the desktop should register that scheme.
- Login: There is no Account Settings field for the API origin. Set `SOFTCHORD_API_ORIGIN` or QSettings `auth/apiOrigin`. Say if Account Settings should edit it.
- Login: Pasting a sign-in link does not check that the link's host is the API origin. The token is sent to the configured origin either way. Say if a link from another host should be rejected.

## Fixed

- 2026-11-10: Sign-in HTTP no longer runs on the UI thread. request-link, verify, `/api/me`, logout, logout-all, and the startup refresh run on a worker. The window updates from a signal.
- 2026-11-10: `src/softchord_test.py` now opens `test_тест_song.txt` from the test file's directory (`__file__`), so the text fixture does not depend on the working directory. The sample songbook path was already resolved from `__file__`.
- 2026-11-10: `test_renumber_stays_on_the_segment` restores `app.question` after forcing an answer, so the stand-in does not stay on the shared test app.
- 2026-11-10: Dirty leave with `keep_open=True` had no test. `test_dirty_keep_open_cancel_discard_and_save` covers Save, Don't Save, and Cancel while the song stays on screen.
