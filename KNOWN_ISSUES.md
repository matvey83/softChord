# Known issues

- Desktop: Undo cannot cross a Save. Save drops the draft's undo steps (by design).
- Desktop: `src/softchord_test.py` import tests fail when run from the repo root. The fixture `test_тест_song.txt` is opened by a path relative to the current directory (`song_file = "test_тест_song.txt"`, then `open(song_file)`) instead of a path next to `__file__`. Running those tests from `src/` finds the fixture. Running them from the repo root does not. Not fixed here.
- Desktop: the desktop unittest process segfaults with exit 139 at interpreter shutdown after all tests pass. Likely Qt teardown. Not triaged.
- Web: `softChord_web/tests/toolbar_mirror.test.js` fails because `tools/export_toolbar_icons.js` writes and checks `softChord Viewer/softChord Viewer/Assets.xcassets/Toolbar`, and that directory is not in the repo. The iOS catalog is `SoftChord/SoftChord/Assets.xcassets/Toolbar`. Suspected cause: the iOS project was renamed and the exporter path was not updated. Not fixed here (it is outside always-edit, and the check also covers iOS assets).
