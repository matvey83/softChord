# softChord

A cross-platform editor for songs with chords. Chords are attached to individual letters in the lyrics (not lined up with spaces), so they stay in place as you edit. Songs are stored together in a songbook file.

## Features

- Edit lyrics and chords in a simple desktop UI
- Store many songs in one `.songbook` file
- Chords move automatically when lyrics change
- Transpose songs
- Use any font or size for lyrics and chord symbols
- Import and export plain text (chords aligned automatically)
- Import and export [ChordPro](https://www.chordpro.org/)
- Export / print to PDF
- Unicode (UTF-8) lyrics
- Song search

The app is written in Python with [PyQt6](https://www.riverbankcomputing.com/software/pyqt/). PyQt6 bundles Qt, so a separate Qt SDK is not required.

## Running from source

Requires [Python](https://www.python.org/) 3.10 or newer.

```bash
git clone https://github.com/matvey83/softChord.git
cd softChord
./start_softChord.py
```

On Windows:

```bat
python start_softChord.py
```

To open a songbook at launch:

```bash
./start_softChord.py zvuki_neba.songbook
```

`start_softChord.py` creates a `.venv` virtual environment if needed, installs dependencies from `requirements.txt`, and starts the app. It asks before installing packages.

Older pre-built binaries (0.9.x, last updated 2011–2013) are still on [SourceForge](https://sourceforge.net/projects/softchord/). Current development is on GitHub; run from source as above.

## Development

### Manual setup

The launcher above is enough for most work. To set up the venv by hand:

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

### Tests

Run from `src/` with the venv active (so `import softchord` works):

```bash
cd src
python3 test_song.py          # unit tests
python3 softchord_test.py     # integration tests (starts a Qt application)
```

### Regenerating UI modules

Windows are defined in Qt Designer `.ui` files. After editing them, regenerate the Python modules:

```bash
pyuic6 src/softchord_main_window.ui -o src/softchord_main_window_ui.py
pyuic6 src/softchord_chord_dialog.ui -o src/softchord_chord_dialog_ui.py
pyuic6 src/softchord_pdf_dialog.ui -o src/softchord_pdf_dialog_ui.py
```

Do not edit the generated `*_ui.py` files by hand.

## Packaging

Standalone app builds are not maintained for the PyQt6 port.

`mac_compile.py`, `mac_compile.command`, `softchord.spec`, and `win_setup.py` still assume older tooling (PyInstaller paths from the PyQt4 era, Qt 4 `qt_menu.nib`, and py2exe). They will not produce a working current build as written.

Use `./start_softChord.py` to run the app.
