# Known issues

## Desktop: `src/softchord_test.py` blocks on the save prompt

- App: desktop (Python/Qt).
- Symptom: `QT_QPA_PLATFORM=offscreen python3 src/softchord_test.py` stops in `test_chords_on_neighbouring_letters_keep_a_space_between` and does not finish. The test adds chords, then exports and deletes. A song is already an edit, so that chord change is unsaved, and leaving it opens the Save / Don't Save / Cancel dialog. Nothing answers the dialog, so the process waits.
- Suspected cause: `confirmLeaveEdit` uses `QMessageBox.exec`. `softchord_test.py` stubs `question`, `info`, `warning`, and `error`, and does not stub `QMessageBox.exec`. `src/test_song.py` does, and that suite finishes (451 tests).
