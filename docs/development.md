# Development

Tests and manual runs use a temporary copy of a songbook rather than a
repository `.songbook`. The repository songbooks are real song libraries; see
[AGENTS.md](../AGENTS.md).

## Manual setup

`./start_softChord.py` (see the [README](../README.md#running-from-source)) is
enough for most work. To set up the venv by hand:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Then run either `./start_softChord.py` or:

```bash
.venv/bin/python src/softchord.py
```

`.venv` is listed in `.gitignore`.

To pick up changes to `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Tests

### Desktop (Python)

Run from `src/` with the venv active (so `import softchord` works):

```bash
cd src
python3 test_song.py          # unit tests
python3 softchord_test.py     # integration tests (starts a Qt application)
```

### Web

The web app's tests run with Node (version 22 or newer):

```bash
cd softChord_web
node --test
```

The tests of the Edit text and Edit chords modes and the layout drive the real page in headless Chrome. Chrome is found in the usual places, or set `CHROME_BIN` to its path. Without Chrome those tests are **skipped, not passed**: the run prints a `WARNING ... did NOT run` message and reports them as skipped. To make a missing Chrome a failure (for a CI that must test the browser), run with `SOFTCHORD_REQUIRE_BROWSER=1 node --test`.

### iOS

The project is `softChord Viewer/softChord Viewer.xcodeproj`, with the app
target `softChord Viewer` and the test targets `softChord ViewerTests` and
`softChord ViewerUITests` (iOS 26.4 or newer). The repository has no shared
scheme; Xcode and `xcodebuild` use the scheme they create for the app,
`softChord Viewer`. Run the tests on a simulator (use one you have installed,
see `xcrun simctl list devices available`):

```bash
xcodebuild test \
  -project "softChord Viewer/softChord Viewer.xcodeproj" \
  -scheme "softChord Viewer" \
  -destination "platform=iOS Simulator,name=iPhone 17"
```

A build step (`softChord Viewer/copy_songbook.sh`) copies `zvuki_neba.songbook`
into the app; the app reads that copy and never writes it.

The shared cases in `tests/` are run by the Python, Swift and JS tests alike:
`chord_vectors.json` (chord strings), `lyric_chord_vectors.json` (chords
following lyric edits) and `chord_move_vectors.json` (chord moves).

## Regenerating UI modules

Windows are defined in Qt Designer `.ui` files. After editing them, regenerate the Python modules:

```bash
pyuic6 src/softchord_main_window.ui -o src/softchord_main_window_ui.py
pyuic6 src/softchord_chord_dialog.ui -o src/softchord_chord_dialog_ui.py
pyuic6 src/softchord_pdf_dialog.ui -o src/softchord_pdf_dialog_ui.py
```

Do not edit the generated `*_ui.py` files by hand.

## Songbook format

A `.songbook` is a SQLite file with `PRAGMA user_version = 2`. Each chord is one
text string such as `Am7/G` or `(1:C♯m)`, stored in `song_chord_link.chord`. The
string grammar and the tolerant parser are described in
[chord_format.md](chord_format.md). The whole file format (song uuids,
`updated_at`, `meta`, deleted-song tombstones) is in
[songbook_format.md](songbook_format.md). The same parser cases
(`tests/chord_vectors.json`) are run by the Python, Swift and JS tests.

The desktop editor still opens the old format (separate note, type, bass,
marker and parentheses columns). It converts the file when it opens it, after
saving a backup next to it as `<name>.songbook.v1.bak`. If the file cannot be
changed, it opens a converted temporary copy and asks you to use Save As. The
iPhone app and the web viewer read version 2 only. To convert a file without
the editor: `python3 tools/convert_songbook_v1_to_v2.py FILE...`. Version 2 files
made before song uuids existed are upgraded the same way (backup
`<name>.songbook.pre-uuid.bak`, or `python3 tools/upgrade_songbook_v2.py`).

## The shared song toolbar (MIRRORED UI)

The three apps have the same song toolbar: the buttons, their order and
groups, the icons, the labels and tooltips, and when each button shows or is
dimmed. Code marked `MIRRORED UI` (or `Mirror:`) has a counterpart in the other
apps; change all of them together. The main places:

- Web: `softChord_web/index.html` (the toolbar) and `softChord_web/viewer.css`.
- iOS: `softChord Viewer/softChord Viewer/SongToolbar.swift`, with the icons in
  `Assets.xcassets/Toolbar`.
- Desktop: `src/softchord_toolbar.py`. Its header comment lists the intended
  desktop differences (for example the desktop-only Fonts group).

The toolbar wraps the same way in all three, measured rather than at a fixed
width: the width of the buttons on one row is worked out for every mode
(viewing, Edit Text, Edit Chords, each with what it hides) and the widest
decides (it is viewing with Save and Discard showing). When it fits, every
mode is one row; when it does not, the edit groups (Edit, the chord buttons,
Undo and Redo, Discard and Save) start the next row in every mode, so the
rows do not move when the mode changes. On the web and iOS only the buttons
are measured: one row holds Back, the title (at least 60 px) and the 38 px
buttons; else Back and the title sit above the 34 px buttons, which follow
the rule above. See `layoutToolbar` (viewer.js), `SongToolbarMetrics`
(SongToolbar.swift) and `rowWidth` (softchord_toolbar.py).

The icons are drawn inline in `softChord_web/index.html`, which is the source.
After changing one there, run

```bash
node tools/export_toolbar_icons.js
```

and commit what it writes: `softChord_web/icons/toolbar/<button id>.svg` (used
by the desktop, bundled by `softchord.spec`) and the iOS imagesets.
`softChord_web/tests/toolbar_mirror.test.js` fails while they differ. The
desktop-only `font-lyrics.svg` and `font-chords.svg` live in the same folder
but are not drawn in `index.html`, so the script neither writes nor checks them.

## Packaging and releases

See [releasing.md](releasing.md).
