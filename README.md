# softChord

A cross-platform editor for songbooks. Enables management of a song book
containing multiple songs with lyrics and chords.  Each chord is attached
to an individual letter, so it stays on its syllable when the text, font,
key, or zoom level changes.

The songbook can be shared as a file, or exported to a printable PDF.

![softChord showing a song with chords](docs/screenshot.jpg)

## Three apps

- **Desktop editor** (macOS, Windows and Linux). The full editor: it opens, edits and
  saves songbooks. Download it from
  [GitHub Releases](https://github.com/matvey83/softChord/releases): signed and
  notarized `.dmg`s for Apple Silicon and Intel Macs, a Windows `.exe` or
  `.zip` (the Windows build is unsigned, so SmartScreen asks first), and a Linux
  `.AppImage` or `.tar.gz` (x86_64). It also runs
  from source on any system with Python (see below).
- **Web app**: [open it in any browser](https://matvey83.github.io/softChord/softChord_web/).
  Shows the songbook in this repository. Changes are not saved yet.
- **iOS app, softChord Viewer** (iPhone and iPad). Shows the songbook in this
  repository. Changes are not saved yet. It is not on the App Store: build it
  from source in Xcode (`softChord Viewer/softChord Viewer.xcodeproj`).

## Features

**Chords on letters**

- Drag a chord to another letter or line; Option-drag (Alt-drag) copies it.
- Move the selected chord with the Left and Right arrow keys.
- A chord can sit up to 10 letters past the end of its line.

**Editing**

- *Edit Text* and *Edit Chords* modes, each ending with Save or Discard.
  Switching between the two modes keeps the changes.
- Undo and Redo.
- Chords follow the lyrics when the text is edited
  ([docs/lyric_editing.md](docs/lyric_editing.md)).

**Keys**

- The key is detected automatically from the chords.
- Transpose up and down, with sharps or flats as the key calls for, and reset
  back to the original key.

**Sharing**

- Copy the song text, the text with chords, or the song as an image.
- Print, or export one or several songs to PDF.
- Import and export [ChordPro](https://www.chordpro.org/) files.
- Import and export plain text with the chords on the line above; the chords
  are placed on the right letters automatically. *Paste As New Song* imports
  such text from the clipboard.

**Viewing**

- Zoom in and out, and back to 100%.
- Any font and size for the lyrics and the chords.
- A short note at the bottom of the song confirms actions such as a copy, a
  zoom or Save.

**Songbooks**

- A songbook is one SQLite file (`.songbook`), with Unicode lyrics in any
  language ([docs/songbook_format.md](docs/songbook_format.md)).
- Search the song list.

## Running from source

Requires [Python](https://www.python.org/) 3.10 or newer.

```bash
git clone https://github.com/matvey83/softChord.git
cd softChord
./start_softChord.py                       # Windows: python start_softChord.py
./start_softChord.py my_songs.songbook     # open a songbook at launch
```

`start_softChord.py` creates a `.venv` if needed, installs `requirements.txt`
(it asks first) and starts the app. The app uses
[PyQt6](https://www.riverbankcomputing.com/software/pyqt/), which bundles Qt.

## More

- [docs/development.md](docs/development.md): setup, tests (Python, web, iOS),
  the songbook format and the toolbar shared by the three apps.
- [docs/releasing.md](docs/releasing.md): packaging, signing and making a release.
- [docs/chord_editing.md](docs/chord_editing.md) and
  [docs/lyric_editing.md](docs/lyric_editing.md): how editing works in each app.

## History

softChord 0.9.x was released on
[SourceForge](https://sourceforge.net/projects/softchord/) in 2011–2013; those
binaries are still there.
