# Known issues

- Desktop: Undo cannot cross a Save. Save drops the draft's undo steps (by design).
- Desktop tests: under pytest, `softchord_test.py` can exit 139 when Qt tears down after the tests have passed. pytest is not a repo dependency. The direct runner is `python softchord_test.py` from `src/` (it reports the test result and exits before that teardown).

## Fixed

- 2026-11-10: `src/softchord_test.py` now opens `test_тест_song.txt` from the test file's directory (`__file__`), so the text fixture does not depend on the working directory. The sample songbook path was already resolved from `__file__`.
- 2026-11-10: `test_renumber_stays_on_the_segment` restores `app.question` after forcing an answer, so the stand-in does not stay on the shared test app.
- 2026-11-10: Dirty leave with `keep_open=True` had no test. `test_dirty_keep_open_cancel_discard_and_save` covers Save, Don't Save, and Cancel while the song stays on screen.
