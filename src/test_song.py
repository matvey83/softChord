"""
Unit tests for softChord domain classes.

Focus:
- Thorough tests for the Song class (core data model)
- Basic tests for smaller supporting classes

Run from the src/ directory:
    python3 test_song.py

Or via the project test runner:
    python3 test_song.py
"""

import unittest
import sqlite3
import copy
import os
import shutil
import tempfile

from PyQt6 import QtCore, QtGui, QtWidgets, QtPrintSupport
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

import softchord
from softchord import (
    Song,
    SongChord,
    SongChar,
    SongsTableRow,
    AddChordCommand,
    DeleteChordCommand,
    ReplaceChordCommand,
    DeleteSongsCommand,
    PREFER_SHARPS,
    PREFER_FLATS,
    PREFER_NEITHER,
    transpose_note,
    read_import_text_file,
    best_detected_key,
    detect_region_start_indices,
    format_auto_detected_key_text,
    auto_detected_key_labels,
    score_key,
    family_score,
    prefer_from_major_tonic,
    key_label,
    replace_russian_characeters,
    SONGS_TABLE_SQL,
    SONG_CHORD_LINK_TABLE_SQL,
)

# ---------------------------------------------------------------------------
# Minimal Test Harness
# ---------------------------------------------------------------------------


class _FakeClipboard:
    """Minimal clipboard stand-in for tests."""

    def __init__(self):
        self._text = ""

    def setText(self, t):
        self._text = t

    def text(self):
        return self._text


class MinimalTestApp:
    """
    A minimal stub App that the Song class and related objects can use
    for unit testing without requiring a full GUI or the real main window.
    """

    def __init__(self):
        self.store = softchord.SongbookStore()
        self.curs = sqlite3.connect(":memory:")
        self.store.use(self.curs)
        self._create_minimal_tables()

        # Support for SongsTableModel / SongsProxyModel
        self.win = None  # SongsProxyModel passes this to super()
        self.filter_string = ""  # Used by SongsProxyModel for filtering

        # Support for CustomTextEdit testing
        self.current_song = None
        self.hover_char_num = None
        self.selected_char_num = None
        self.chords_font = QtGui.QFont()
        self.chords_color = QtGui.QColor("blue")
        self.lyrics_font = QtGui.QFont()
        self.undo_stack = _DummyUndoStack()

        # Fake clipboard for cut/copy/paste tests
        self.clipboard = _FakeClipboard()

        # Stubs for dialog methods used by many App operations
        self._last_warning = None
        self._last_error = None
        self._last_info = None
        self._last_question_result = True  # default to accepting questions

        # Build the same data structures that App builds at startup.
        # We do this here so Song / SongChord can work without a full App.

        # notes
        self.notes_list = []
        self.note_text_id_dict = {}
        for note_id, text, alt_text in softchord.global_notes_list:
            self.notes_list.append((text, alt_text))
            self.note_text_id_dict[text] = note_id
            self.note_text_id_dict[alt_text] = note_id

        # chord types
        self.chord_type_names = []
        self.chord_type_prints = []
        for _, name, print_text in softchord.chord_types_list:
            if print_text:
                name = "%s - %s" % (print_text, name)
            self.chord_type_names.append(name)
            self.chord_type_prints.append(print_text)

        self.chord_type_texts_dict = {}
        for id, print_text in enumerate(self.chord_type_prints):
            self.chord_type_texts_dict[print_text] = id
            for alt, official in softchord.alternative_type_names.items():
                if print_text == official:
                    self.chord_type_texts_dict[alt] = id

        # Fonts (Song creates a QTextDocument)
        self.lyrics_font = QtGui.QFont("Courier New", 12)
        self.chord_font = QtGui.QFont("Courier New", 10)

        # Stubs for things Song touches during normal operation
        self.undo_stack = _DummyUndoStack()
        self.editor = _DummyEditor()
        self.selected_char_num = None
        self.ignore_song_text_changed = False
        self.doc_editor_offset = 0

        # Provide the methods Song calls on self.app
        self._setup_method_stubs()

    def _create_minimal_tables(self):
        self.curs.execute(SONGS_TABLE_SQL)
        self.curs.execute(SONG_CHORD_LINK_TABLE_SQL)
        self.curs.commit()

    def _setup_method_stubs(self):
        # These are called by Song.setDocMargins and other methods.
        # We provide minimal safe implementations for unit testing.

        def _get_heights():
            # Return (chords_height, lyrics_height, line_height)
            return (18.0, 14.0, 18.0)

        self.getHeightsWithChords = _get_heights
        self.getHeightsWithoutChords = _get_heights

        def _viewport_update():
            pass

        # The real editor has .viewport().update()
        class _DummyViewport:

            def update(self):
                pass

        self.editor.viewport = lambda: _DummyViewport()

    def getHeightsWithChords(self):
        return (18.0, 14.0, 18.0)

    def getHeightsWithoutChords(self):
        return (0.0, 14.0, 14.0)

    # --- Stubs needed by CustomTextEdit ---
    def determineClickedLetter(self, x, y, dragging):
        """Stub - tests can override this on a per-test basis."""
        return None

    def getChordWidth(self, chord_text):
        return len(chord_text) * 8

    def drawChord(self, painter, rect, text):
        pass

    def drawSongToRect(self, song, painter, editor, rect):
        pass

    def processKeyPressed(self, key):
        return False

    def deleteSelectedChord(self):
        pass

    def processSongCharEdit(self, char_num):
        pass

    def getCharRects(self, editor, char_num, chord):
        # Very rough stub
        return (QtCore.QRect(0, 0, 10, 10), QtCore.QRect(0, 0, 10, 10))

    def __del__(self):
        # Do not close the in-memory sqlite connection here. __del__ can run
        # during GC while tests still hold the instance, wiping usable state.
        pass

    # --- Stubs for common App dialog / warning methods used in songbook & import ops ---
    def warning(self, text):
        self._last_warning = text

    def error(self, text):
        self._last_error = text

    def info(self, text):
        self._last_info = text

    def question(self, msg, button1="OK", button2="Cancel", title=None):
        return self._last_question_result

    # --- Helpers for testing core keyboard input (processKeyPressed) ---
    def _setup_for_key_input(self, text="This is a test line for chords"):
        """Prepare this MinimalTestApp + a song for processKeyPressed testing."""
        song = create_test_song(self, text=text)
        self.current_song = song
        self.selected_char_num = 0
        self.previous_song_text = text
        return song

    # --- Minimal support for font + clipboard + printing tests ---
    def updateEditorFonts(self):
        pass


class _DummyUndoStack:
    """Minimal stand-in for QUndoStack used by Song chord operations."""

    def __init__(self):
        self.commands = []

    def push(self, command):
        # For unit tests we usually want to test the _addChord etc. internal
        # methods directly, or we can execute the command immediately.
        self.commands.append(command)
        command.redo(
        )  # simulate the effect for tests that go through public API


class _DummyEditor:
    """Stand-in so Song doesn't blow up when it touches the editor."""

    def __init__(self):
        self._viewport = _DummyViewport()

    def viewport(self):
        return self._viewport


class _DummyViewport:

    def update(self):
        pass


def create_test_song(app,
                     song_id=1,
                     title="Test Song",
                     text="Amazing grace\nHow sweet the sound"):
    """Helper: insert a minimal song into the test DB and return a Song instance."""
    app.curs.execute(
        """
        INSERT INTO songs (id, number, title, subtitle, text)
        VALUES (?, 1, ?, '', ?)
    """, (song_id, title, text))
    app.curs.commit()

    song = Song(app, song_id)
    return song


def open_empty_temp_songbook(app):
    """Open a throwaway songbook so tests do not write zvuki_neba.songbook."""
    td = tempfile.mkdtemp()
    path = os.path.join(td, "t.songbook")
    conn = sqlite3.connect(path)
    conn.execute(SONG_CHORD_LINK_TABLE_SQL)
    conn.execute(SONGS_TABLE_SQL)
    conn.commit()
    conn.close()
    app.setCurrentSongbook(path)
    return td


def insert_and_select_song(app,
                           song_id=0,
                           title="Test Song",
                           text="Amazing grace\nHow sweet the sound",
                           with_chord=False):
    app.curs.execute(
        "INSERT INTO songs (id, number, title, subtitle, text) "
        "VALUES (?, 1, ?, '', ?)", (song_id, title, text))
    if with_chord:
        app.curs.execute(
            "INSERT INTO song_chord_link (id, song_id, character_num, "
            "note_id, chord_type_id, bass_note_id, marker, in_parentheses) "
            "VALUES (0, ?, 0, 0, 0, -1, '', 0)", (song_id,))
    app.curs.commit()
    app.songs_model.updateFromDatabase()
    app.ui.songs_view.selectRow(0)


# ---------------------------------------------------------------------------
# Tests for SongChord and SongChar (basic)
# ---------------------------------------------------------------------------


class TestSongChord(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not QtWidgets.QApplication.instance():
            cls.qapp = QtWidgets.QApplication([])
        else:
            cls.qapp = QtWidgets.QApplication.instance()

    def setUp(self):
        self.app = MinimalTestApp()

    def test_basic_creation(self):
        # Need a real Song because SongChord stores a reference to it
        song = create_test_song(self.app, song_id=99, text="x")
        chord = SongChord(song, 5, 0, 0, -1, "", 0)
        self.assertEqual(chord.character_num, 5)
        self.assertEqual(chord.note_id, 0)
        self.assertEqual(chord.chord_type_id, 0)

    def test_get_chord_text(self):
        song = create_test_song(self.app, song_id=101, text="x")
        chord = SongChord(song, 0, 0, 0, -1, "", 0)  # C
        self.assertIn("C", chord.getChordText())

        chord2 = SongChord(song, 0, 0, 5, -1, "", 0)  # C7
        self.assertIn("7", chord2.getChordText())

    def test_null_marker_and_parentheses_normalize(self):
        song = create_test_song(self.app, song_id=102, text="x")
        for marker in (None, "-1", "None"):
            chord = SongChord(song, 0, 0, 0, -1, marker, None)
            self.assertEqual(chord.marker, "")
            self.assertEqual(chord.in_parentheses, 0)

    def test_get_chord_text_includes_parentheses(self):
        song = create_test_song(self.app, song_id=103, text="x")
        chord = SongChord(song, 0, 0, 0, -1, "", 1)
        self.assertEqual(chord.getChordText(), "(C)")

    def test_transpose_moves_bass_note(self):
        song = create_test_song(self.app, song_id=104, text="x")
        chord = SongChord(song, 0, 0, 0, 4, "", 0)  # C/E
        chord.transpose(2)
        self.assertEqual(chord.note_id, 2)  # D
        self.assertEqual(chord.bass_note_id, 6)  # F#


class TestSongChar(unittest.TestCase):

    def test_basic(self):
        # Signature: (text, song_char_num, chord, char_left, char_right, chord_left, chord_right)
        char = SongChar("A", 3, None, 10, 11, 12, 13)
        self.assertEqual(char.text, "A")
        self.assertEqual(char.song_char_num, 3)


# ---------------------------------------------------------------------------
# Thorough tests for the Song class
# ---------------------------------------------------------------------------


class TestSong(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not QtWidgets.QApplication.instance():
            cls.qapp = QtWidgets.QApplication([])
        else:
            cls.qapp = QtWidgets.QApplication.instance()

    def setUp(self):
        self.app = MinimalTestApp()
        self.song = create_test_song(self.app,
                                     song_id=42,
                                     text="Test line one\nTest line two")

    def test_basic_properties(self):
        self.assertEqual(self.song.id, 42)
        self.assertEqual(self.song.title, "Test Song")
        self.assertIn("Test line one", self.song.getAllText())

    def test_add_and_remove_chord(self):
        chord = SongChord(self.song, 0, 0, 0, -1, "", 0)  # C at start
        self.song._addChord(
            chord)  # use internal version to avoid GUI side effects

        chords = list(self.song.iterateAllChords())
        self.assertEqual(len(chords), 1)
        self.assertEqual(chords[0].note_id, 0)

        self.song._deleteChord(chord)
        self.assertEqual(len(list(self.song.iterateAllChords())), 0)

    def test_get_as_text_without_chords(self):
        text = self.song.getAsText(include_chords=False)
        self.assertIn("Test line one", text)
        self.assertIn("Test line two", text)

    def test_get_as_chordpro_text(self):
        # Add one chord
        chord = SongChord(self.song, 5, 0, 0, -1, "", 0)
        self.song._addChord(chord)

        chordpro = self.song.getAsChordProText()
        self.assertIn("{title:Test Song}", chordpro)
        self.assertIn("[C]",
                      chordpro)  # or similar depending on exact rendering

    def test_transpose(self):
        # Add a C chord
        chord = SongChord(self.song, 0, 0, 0, -1, "", 0)
        self.song._addChord(chord)

        self.song.transpose(2)  # C -> D

        chord_texts = [c.getChordText() for c in self.song.iterateAllChords()]
        self.assertTrue(any("D" in t for t in chord_texts))

    def test_update_sharps_or_flats(self):
        chord = SongChord(self.song, 0, 1, 0, -1, "", 0)  # C#
        self.song._addChord(chord)

        self.song.updateSharpsOrFlats()
        # Just make sure it doesn't crash and sets a preference
        self.assertIn(self.song.prefer,
                      (PREFER_SHARPS, PREFER_FLATS, PREFER_NEITHER))

    def test_add_chord_with_bass_note(self):
        # Add C/E (C major with E bass)
        chord = SongChord(self.song, 0, 0, 0, 4, "", 0)  # C / E
        self.song._addChord(chord)

        chords = list(self.song.iterateAllChords())
        self.assertEqual(len(chords), 1)
        self.assertEqual(chords[0].bass_note_id, 4)

        chord_text = chords[0].getChordText()
        self.assertIn("/", chord_text)
        self.assertIn("E", chord_text)

    def test_add_chord_with_marker(self):
        chord = SongChord(self.song, 0, 0, 0, -1, "1", 0)  # 1:C
        self.song._addChord(chord)

        chord_text = list(self.song.iterateAllChords())[0].getChordText()
        self.assertIn("1:", chord_text)

    def test_add_chord_in_parentheses(self):
        chord = SongChord(self.song, 0, 0, 0, -1, "", 1)  # (C)
        self.song._addChord(chord)

        stored_chord = list(self.song.iterateAllChords())[0]
        self.assertEqual(stored_chord.in_parentheses, 1)
        self.assertEqual(stored_chord.getChordText(), "(C)")

    def test_copy_chord(self):
        original = SongChord(self.song, 5, 2, 1, -1, "", 0)  # D minor at pos 5
        self.song._addChord(original)

        copied = self.song.copyChord(original, 12)

        all_chords = list(self.song.iterateAllChords())
        self.assertEqual(len(all_chords), 2)

        self.assertEqual(copied.character_num, 12)
        self.assertEqual(copied.note_id, 2)
        self.assertEqual(copied.chord_type_id, 1)

    def test_get_chord_methods(self):
        chord1 = SongChord(self.song, 3, 0, 0, -1, "", 0)
        chord2 = SongChord(self.song, 10, 4, 0, -1, "", 0)
        self.song._addChord(chord1)
        self.song._addChord(chord2)

        self.assertIs(self.song.getChordAtPosition(3), chord1)
        self.assertIs(self.song.getChordAtPosition(10), chord2)
        self.assertIsNone(self.song.getChordAtPosition(99))

        self.assertIs(self.song.getChord(3), chord1)
        self.assertIs(self.song.getChord(10), chord2)

        with self.assertRaises(ValueError):
            self.song.getChord(999)

    def test_get_as_text_with_multiple_chords(self):
        # Add two chords on first line
        c_chord = SongChord(self.song, 0, 0, 0, -1, "", 0)  # C at start
        g_chord = SongChord(self.song, 12, 7, 0, -1, "", 0)  # G at position 12
        self.song._addChord(c_chord)
        self.song._addChord(g_chord)

        text_with_chords = self.song.getAsText(include_chords=True)
        lines = text_with_chords.splitlines()

        # First line should have chords above lyrics
        self.assertTrue(len(lines) >= 2)
        self.assertIn("C", lines[0])
        self.assertIn("G", lines[0])
        self.assertIn("Test line one", lines[1])

    def test_get_as_chordpro_with_bass_and_marker(self):
        chord = SongChord(self.song, 0, 0, 0, 4, "2", 0)  # 2:C/E
        self.song._addChord(chord)

        chordpro = self.song.getAsChordProText()
        self.assertIn("[2:C/E]", chordpro)

    def test_transpose_with_key_and_negative_steps(self):
        chord = SongChord(self.song, 0, 0, 0, -1, "", 0)  # C
        self.song._addChord(chord)

        self.song.transpose(-1)  # C -> B

        chord_text = list(self.song.iterateAllChords())[0].getChordText()
        self.assertIn("B", chord_text)

    def test_transpose_multiple_chords(self):
        c = SongChord(self.song, 0, 0, 0, -1, "", 0)
        dm = SongChord(self.song, 5, 2, 1, -1, "", 0)  # Dm
        self.song._addChord(c)
        self.song._addChord(dm)

        self.song.transpose(5)  # +5 semitones

        texts = [ch.getChordText() for ch in self.song.iterateAllChords()]
        self.assertTrue(any("F" in t for t in texts))  # C -> F
        self.assertTrue(any("Gm" in t or "G m" in t
                            for t in texts))  # rough check for Dm transposed

    def test_get_as_text_chords_only_false(self):
        chord = SongChord(self.song, 0, 0, 0, -1, "", 0)
        self.song._addChord(chord)

        plain = self.song.getAsText(include_chords=False)
        self.assertNotIn("C", plain.split("\n")[0])  # No chord line
        self.assertIn("Test line one", plain)

    def test_line_and_song_char_conversion(self):
        # "Test line one" is 13 chars; newline at 13; line 2 starts at 14.
        self.assertEqual(self.song.songCharToLineChar(0), (0, 0))
        self.assertEqual(self.song.songCharToLineChar(12), (0, 12))
        self.assertEqual(self.song.songCharToLineChar(14), (1, 0))
        self.assertEqual(self.song.lineCharToSongChar(0, 0), 0)
        self.assertEqual(self.song.lineCharToSongChar(1, 0), 14)
        self.assertEqual(self.song.lineCharToSongChar(1, 3), 17)

    def test_get_line_has_chords(self):
        self.assertFalse(self.song.getLineHasChords(0))
        self.song._addChord(SongChord(self.song, 0, 0, 0, -1, "", 0))
        self.assertTrue(self.song.getLineHasChords(0))
        self.assertFalse(self.song.getLineHasChords(1))

    def test_get_note_string_follows_prefer(self):
        self.song._regions = [(0, PREFER_SHARPS, "A")]
        self.song.prefer = PREFER_SHARPS
        self.assertEqual(self.song._getNoteString(1, 0), "C♯")
        self.song._regions = [(0, PREFER_FLATS, "B♭")]
        self.song.prefer = PREFER_FLATS
        self.assertEqual(self.song._getNoteString(1, 0), "D♭")

    def test_remove_trailing_spaces_remaps_chords_in_database(self):
        # "Hi  \nGo": trailing spaces on line 1; G is at song char 5.
        text = "Hi  \nGo"
        song = create_test_song(self.app, song_id=8, text=text)
        self.app.curs.execute(
            "INSERT INTO song_chord_link (id, song_id, character_num, "
            "note_id, chord_type_id, bass_note_id, marker, in_parentheses) "
            "VALUES (1, 8, 5, 7, 0, -1, '', 0)")
        self.app.curs.commit()
        song = Song(self.app, 8)

        song.removeTrailingSpaces()

        stored = self.app.curs.execute(
            "SELECT text FROM songs WHERE id=8").fetchone()[0]
        self.assertEqual(stored, "Hi\nGo")
        char_num = self.app.curs.execute(
            "SELECT character_num FROM song_chord_link WHERE song_id=8"
        ).fetchone()[0]
        self.assertEqual(char_num, 3)

    def test_remove_trailing_spaces_deletes_chords_on_trimmed_spaces(self):
        # "Hi  \nGo": C sits on the second trailing space (char 3).
        text = "Hi  \nGo"
        song = create_test_song(self.app, song_id=9, text=text)
        self.app.curs.execute(
            "INSERT INTO song_chord_link (id, song_id, character_num, "
            "note_id, chord_type_id, bass_note_id, marker, in_parentheses) "
            "VALUES (1, 9, 3, 0, 0, -1, '', 0)")
        self.app.curs.commit()
        song = Song(self.app, 9)

        song.removeTrailingSpaces()

        stored = self.app.curs.execute(
            "SELECT text FROM songs WHERE id=9").fetchone()[0]
        self.assertEqual(stored, "Hi\nGo")
        remaining = list(self.app.curs.execute(
            "SELECT character_num FROM song_chord_link WHERE song_id=9"))
        self.assertEqual(remaining, [])

    def test_remove_trailing_spaces_updates_in_memory_song(self):
        # G at char 5 (kept); C at char 3 (trailing space, dropped).
        text = "Hi  \nGo"
        song = create_test_song(self.app, song_id=10, text=text)
        self.app.curs.execute(
            "INSERT INTO song_chord_link (id, song_id, character_num, "
            "note_id, chord_type_id, bass_note_id, marker, in_parentheses) "
            "VALUES (1, 10, 5, 7, 0, -1, '', 0), "
            "(2, 10, 3, 0, 0, -1, '', 0)")
        self.app.curs.commit()
        song = Song(self.app, 10)
        self.app.current_song = song

        song.removeTrailingSpaces()

        self.assertEqual(song.getAllText(), "Hi\nGo")
        chords = sorted(c.character_num for c in song.iterateAllChords())
        self.assertEqual(chords, [3])
        db_chars = sorted(
            row[0] for row in self.app.curs.execute(
                "SELECT character_num FROM song_chord_link WHERE song_id=10"))
        self.assertEqual(db_chars, [3])

    def test_song_reads_and_writes_through_the_store(self):
        loaded = []
        saved = []
        real_load = self.app.store.load_song
        real_save = self.app.store.update_song_text

        def load_song(song_id):
            loaded.append(song_id)
            return real_load(song_id)

        def update_song_text(song_id, text):
            saved.append((song_id, text))
            return real_save(song_id, text)

        self.app.store.load_song = load_song
        self.app.store.update_song_text = update_song_text
        song = create_test_song(self.app, song_id=11, text="Hi  ")
        song.removeTrailingSpaces()
        self.assertEqual(loaded, [11])
        self.assertEqual(saved, [(11, "Hi")])
        stored = self.app.curs.execute(
            "SELECT text FROM songs WHERE id=11").fetchone()[0]
        self.assertEqual(stored, "Hi")

    def test_loads_legacy_schema_without_subtitle(self):
        app = MinimalTestApp()
        app.curs.execute("DROP TABLE songs")
        app.curs.execute(
            "CREATE TABLE songs (id INTEGER PRIMARY KEY, title TEXT, "
            "number INTEGER, text TEXT)")
        app.curs.execute(
            "INSERT INTO songs (id, title, number, text) "
            "VALUES (1, 'Old', 3, 'hi')")
        app.curs.commit()

        song = Song(app, 1)
        self.assertEqual(song.title, "Old")
        self.assertEqual(song.number, 3)
        self.assertEqual(song.subtitle, "")
        self.assertEqual(song.getAllText(), "hi")
        columns = [
            row[1] for row in app.curs.execute("PRAGMA table_info(songs)")
        ]
        self.assertIn("subtitle", columns)


# ---------------------------------------------------------------------------
# Basic tests for table row and undo commands
# ---------------------------------------------------------------------------


class TestSongsTableRow(unittest.TestCase):

    def test_basic(self):
        row = SongsTableRow(1, 23, "Amazing Grace")
        self.assertEqual(row.id, 1)
        self.assertEqual(row.number, 23)
        self.assertEqual(row.title, "Amazing Grace")


class TestUndoCommands(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not QtWidgets.QApplication.instance():
            cls.qapp = QtWidgets.QApplication([])
        else:
            cls.qapp = QtWidgets.QApplication.instance()

    def setUp(self):
        self.app = MinimalTestApp()
        self.song = create_test_song(self.app, text="Chord test line")

    def test_add_chord_command(self):
        chord = SongChord(self.song, 0, 0, 0, -1, "", 0)
        cmd = AddChordCommand(self.song, chord)
        cmd.redo()
        self.assertIn(chord, list(self.song.iterateAllChords()))
        cmd.undo()
        self.assertNotIn(chord, list(self.song.iterateAllChords()))

    def test_delete_chord_command(self):
        chord = SongChord(self.song, 0, 0, 0, -1, "", 0)
        self.song._addChord(chord)

        cmd = DeleteChordCommand(self.song, chord)
        cmd.redo()
        self.assertNotIn(chord, list(self.song.iterateAllChords()))
        cmd.undo()
        self.assertIn(chord, list(self.song.iterateAllChords()))

    def test_replace_chord_command(self):
        prev = SongChord(self.song, 0, 0, 0, -1, "", 0)  # C
        self.song._addChord(prev)
        new = SongChord(self.song, 0, 7, 0, -1, "", 0)  # G

        cmd = ReplaceChordCommand(self.song, prev, new)
        cmd.redo()
        chords = list(self.song.iterateAllChords())
        self.assertEqual(chords, [new])

        cmd.undo()
        chords = list(self.song.iterateAllChords())
        self.assertEqual(chords, [prev])


# ---------------------------------------------------------------------------
# Tests for SongsTableModel and SongsProxyModel
# ---------------------------------------------------------------------------


class TestSongsTableModels(unittest.TestCase):

    def setUp(self):
        self.app = MinimalTestApp()

        # Insert some test songs directly into the DB
        self.app.curs.executemany(
            """
            INSERT INTO songs (id, number, title, subtitle, text)
            VALUES (?, ?, ?, '', 'lyrics here')
        """,
            [
                (1, 10, "Amazing Grace"),
                (2, 20, "How Great Thou Art"),
                (3, -1, "Untitled Song"),  # song with no number
                (4, 30, "Be Thou My Vision"),
            ])
        self.app.curs.commit()

        self.table_model = softchord.SongsTableModel(self.app)
        self.proxy_model = softchord.SongsProxyModel(self.app)
        self.proxy_model.setSourceModel(self.table_model)

    def test_table_lists_songs_through_the_store(self):
        seen = []
        real = self.app.store.list_song_rows

        def list_song_rows():
            seen.append(True)
            return real()

        self.app.store.list_song_rows = list_song_rows
        self.table_model.updateFromDatabase()
        self.assertEqual(seen, [True])
        self.assertEqual(self.table_model.rowCount(), 4)

    def test_table_model_basic_population(self):
        self.assertEqual(self.table_model.rowCount(), 4)
        self.assertEqual(self.table_model.columnCount(), 2)

        # Check headers
        self.assertEqual(
            self.table_model.headerData(0, QtCore.Qt.Orientation.Horizontal,
                                        Qt.ItemDataRole.DisplayRole), "Number")
        self.assertEqual(
            self.table_model.headerData(1, QtCore.Qt.Orientation.Horizontal,
                                        Qt.ItemDataRole.DisplayRole), "Title")

    def test_table_model_data(self):
        # Row 0: Amazing Grace (number 10)
        self.assertEqual(self.table_model.data(self.table_model.index(0, 0)),
                         10)
        self.assertEqual(self.table_model.data(self.table_model.index(0, 1)),
                         "Amazing Grace")

        # Row 2: Untitled Song (number -1 → should return None for number column)
        self.assertIsNone(self.table_model.data(self.table_model.index(2, 0)))
        self.assertEqual(self.table_model.data(self.table_model.index(2, 1)),
                         "Untitled Song")

    def test_table_model_helper_methods(self):
        self.assertEqual(self.table_model.getRowSongID(1), 2)  # second song
        self.assertEqual(self.table_model.getAllSongIds(), [1, 2, 3, 4])

        title, num = self.table_model.getTitleAndNumFromId(4)
        self.assertEqual(title, "Be Thou My Vision")
        self.assertEqual(num, 30)

        row_index = self.table_model.getSongsRow(  # we need a Song object for this
            type("FakeSong", (), {"id": 3})())
        self.assertEqual(row_index, 2)

    def test_table_model_update_from_database(self):
        # Add a new song directly to DB
        self.app.curs.execute("""
            INSERT INTO songs (id, number, title, subtitle, text)
            VALUES (5, 40, "New Song Added Later", '', '')
        """)
        self.app.curs.commit()

        self.table_model.updateFromDatabase()

        self.assertEqual(self.table_model.rowCount(), 5)
        self.assertIn(5, self.table_model.getAllSongIds())

    def test_proxy_model_no_filter(self):
        self.app.filter_string = ""
        # All rows should be accepted when no filter
        for row in range(self.table_model.rowCount()):
            self.assertTrue(
                self.proxy_model.filterAcceptsRow(row, QtCore.QModelIndex()))

    def test_proxy_model_filter_by_title(self):
        self.app.filter_string = "grace"
        # Only "Amazing Grace" should match
        self.assertTrue(
            self.proxy_model.filterAcceptsRow(0, QtCore.QModelIndex()))
        self.assertFalse(
            self.proxy_model.filterAcceptsRow(1, QtCore.QModelIndex()))
        self.assertFalse(
            self.proxy_model.filterAcceptsRow(3, QtCore.QModelIndex()))

    def test_proxy_model_filter_by_number(self):
        self.app.filter_string = "20"
        self.assertTrue(
            self.proxy_model.filterAcceptsRow(
                1, QtCore.QModelIndex()))  # How Great Thou Art
        self.assertFalse(
            self.proxy_model.filterAcceptsRow(0, QtCore.QModelIndex()))

    def test_proxy_model_filter_case_insensitive(self):
        self.app.filter_string = "VISION"
        self.assertTrue(
            self.proxy_model.filterAcceptsRow(3, QtCore.QModelIndex()))

    def test_table_model_missing_id_raises(self):
        with self.assertRaises(ValueError):
            self.table_model.getTitleAndNumFromId(99)
        with self.assertRaises(ValueError):
            self.table_model.getSongsRow(type("FakeSong", (), {"id": 99})())

    def test_table_model_set_row(self):
        self.table_model.setRow(0, SongsTableRow(1, 11, "Renamed"))
        self.assertEqual(self.table_model.data(self.table_model.index(0, 0)),
                         11)
        self.assertEqual(self.table_model.data(self.table_model.index(0, 1)),
                         "Renamed")

    def test_proxy_less_than(self):
        ten = self.table_model.index(0, 0)
        twenty = self.table_model.index(1, 0)
        untitled = self.table_model.index(2, 0)  # number -1 → None
        self.assertTrue(self.proxy_model.lessThan(ten, twenty))
        self.assertFalse(self.proxy_model.lessThan(twenty, ten))
        self.assertFalse(self.proxy_model.lessThan(untitled, ten))


# ---------------------------------------------------------------------------
# Tests for CustomTextEdit (the interactive chord editor)
# ---------------------------------------------------------------------------


class TestCustomTextEdit(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # We need a QApplication before creating any QWidget
        if not QtWidgets.QApplication.instance():
            cls.qapp = QtWidgets.QApplication([])
        else:
            cls.qapp = QtWidgets.QApplication.instance()

    def setUp(self):
        self.app = MinimalTestApp()
        # Give the editor a parent so it doesn't complain
        self.app.win = QtWidgets.QWidget()

        self.editor = softchord.CustomTextEdit(self.app)

    def test_construction(self):
        self.assertIsNotNone(self.editor)
        self.assertFalse(self.editor.lyric_editor_mode)
        self.assertIsNone(self.editor.dragging_chord)
        self.assertEqual(self.editor.dragging_chord_orig_position, -1)

    def test_lyric_editor_mode_switches_behavior(self):
        self.editor.lyric_editor_mode = True
        # In lyric mode, certain methods should delegate to QTextEdit super
        # We mainly verify the flag works
        self.assertTrue(self.editor.lyric_editor_mode)

        self.editor.lyric_editor_mode = False
        self.assertFalse(self.editor.lyric_editor_mode)

    def test_option_key_toggled_no_dragging(self):
        # Should be a no-op when not dragging
        self.editor.optionKeyToggled(True)
        self.editor.optionKeyToggled(False)
        self.assertIsNone(self.editor.dragging_chord)

    def test_option_key_toggled_with_dragging(self):
        # Simulate a drag in progress
        fake_chord = SongChord(
            type("FakeSong", (), {
                "app": self.app,
                "id": 1
            })(), 5, 0, 0, -1, "", 0)
        self.editor.dragging_chord = fake_chord
        self.editor.dragging_chord_orig_position = 5

        # Need a current_song for copyChord to work
        self.app.current_song = create_test_song(self.app,
                                                 song_id=99,
                                                 text="abcde")

        # Pressing Alt should copy the chord
        self.editor.optionKeyToggled(True)
        self.assertIsNotNone(self.editor.original_chord)

        # Releasing Alt should delete the copy
        self.editor.optionKeyToggled(False)
        self.assertIsNone(self.editor.original_chord)

    def test_alt_key_press_release_via_qtest(self):
        """Send real Alt key events through QTest."""
        # This tests that keyPressEvent / keyReleaseEvent correctly call optionKeyToggled
        self.app.current_song = create_test_song(self.app,
                                                 song_id=100,
                                                 text="test")

        # Create a fake dragging state
        fake_chord = SongChord(self.app.current_song, 2, 0, 0, -1, "", 0)
        self.editor.dragging_chord = fake_chord
        self.editor.dragging_chord_orig_position = 2

        # Simulate pressing Alt
        QTest.keyPress(self.editor, Qt.Key.Key_Alt)
        self.assertIsNotNone(self.editor.original_chord)

        # Simulate releasing Alt
        QTest.keyRelease(self.editor, Qt.Key.Key_Alt)
        self.assertIsNone(self.editor.original_chord)

    def test_delete_key_delegates_to_app(self):
        """Delete/Backspace should call app.deleteSelectedChord()."""
        called = []

        def fake_delete():
            called.append(True)

        self.app.deleteSelectedChord = fake_delete

        QTest.keyPress(self.editor, Qt.Key.Key_Delete)
        self.assertTrue(called)

        called.clear()
        QTest.keyPress(self.editor, Qt.Key.Key_Backspace)
        self.assertTrue(called)


# ---------------------------------------------------------------------------
# Tests for core App functionality (especially keyboard chord input)
# ---------------------------------------------------------------------------


class TestAppCoreFunctionality(unittest.TestCase):
    """
    Tests for high-value core functionality in the App class that was previously
    poorly covered: processKeyPressed (the main way users add/edit chords via
    keyboard), hit testing helpers, etc.
    """

    @classmethod
    def setUpClass(cls):
        # processKeyPressed has complex interactions; using a real (but minimal)
        # App instance gives us the most accurate coverage of core logic.
        if not QtWidgets.QApplication.instance():
            cls.qapp = QtWidgets.QApplication([])
        else:
            cls.qapp = QtWidgets.QApplication.instance()

    def setUp(self):
        # Create a real App and immediately open a songbook so .curs is valid
        self.app = softchord.App([])
        self.app.win = QtWidgets.QWidget()
        open_empty_temp_songbook(self.app)

    def test_process_key_pressed_add_new_chord(self):
        """Pressing a note key (e.g. 'C') on a selected position should add a chord."""
        song = create_test_song(self.app, song_id=9999, text="Amazing Grace")
        self.app.current_song = song
        self.app.selected_char_num = 0
        self.app.previous_song_text = "Amazing Grace"

        # Press 'C' (note 0)
        result = self.app.processKeyPressed(Qt.Key.Key_C)

        self.assertTrue(result)
        chords = list(song.iterateAllChords())
        self.assertEqual(len(chords), 1)
        self.assertEqual(chords[0].note_id, 0)  # C
        self.assertEqual(chords[0].chord_type_id, 0)  # Major
        self.assertEqual(chords[0].character_num, 0)

    def test_process_key_pressed_change_existing_chord(self):
        """Pressing a different note on a position that already has a chord should replace it."""
        song = create_test_song(self.app, song_id=10000, text="Test line")
        self.app.current_song = song
        self.app.selected_char_num = 5
        self.app.previous_song_text = "Test line"

        # First add a C
        self.app.processKeyPressed(Qt.Key.Key_C)
        self.assertEqual(len(list(song.iterateAllChords())), 1)

        # Now change it to G by pressing G
        result = self.app.processKeyPressed(Qt.Key.Key_G)
        self.assertTrue(result)

        chords = list(song.iterateAllChords())
        self.assertEqual(len(chords), 1)
        self.assertEqual(chords[0].note_id, 7)  # G

    def test_process_key_pressed_toggle_major_minor_with_m(self):
        """Pressing 'M' should toggle between major and minor on the selected chord."""
        song = create_test_song(self.app, song_id=10001, text="Test")
        self.app.current_song = song
        self.app.selected_char_num = 0
        self.app.previous_song_text = "Test"

        self.app.processKeyPressed(Qt.Key.Key_C)  # Add C major

        chord = song.getChordAtPosition(0)
        self.assertEqual(chord.chord_type_id, 0)  # Major

        result = self.app.processKeyPressed(Qt.Key.Key_M)
        self.assertTrue(result)
        chord = song.getChordAtPosition(0)
        self.assertEqual(chord.chord_type_id, 1)  # Minor

        result = self.app.processKeyPressed(Qt.Key.Key_M)
        self.assertTrue(result)
        chord = song.getChordAtPosition(0)
        self.assertEqual(chord.chord_type_id, 0)  # Back to Major

    def test_process_key_pressed_m_returns_true_when_toggled(self):
        song = create_test_song(self.app, song_id=0, text="Test")
        self.app.current_song = song
        self.app.selected_char_num = 0
        self.app.previous_song_text = "Test"
        self.app.processKeyPressed(Qt.Key.Key_C)

        result = self.app.processKeyPressed(Qt.Key.Key_M)

        self.assertTrue(result)
        chord = song.getChordAtPosition(0)
        self.assertEqual(chord.chord_type_id, 1)

    def test_process_key_pressed_m_returns_false_without_chord(self):
        song = create_test_song(self.app, song_id=0, text="Test")
        self.app.current_song = song
        self.app.selected_char_num = 0
        result = self.app.processKeyPressed(Qt.Key.Key_M)
        self.assertFalse(result)

    def test_process_key_pressed_arrow_move_chord(self):
        """Left/Right arrows should move the selected chord."""
        song = create_test_song(self.app, song_id=10002, text="0123456789")
        self.app.current_song = song
        self.app.selected_char_num = 3
        self.app.previous_song_text = "0123456789"

        self.app.processKeyPressed(Qt.Key.Key_C)
        self.assertEqual(song.getChordAtPosition(3).character_num, 3)

        self.app.processKeyPressed(Qt.Key.Key_Right)
        self.assertIsNone(song.getChordAtPosition(3))
        self.assertEqual(song.getChordAtPosition(4).character_num, 4)

        self.app.processKeyPressed(Qt.Key.Key_Left)
        self.assertEqual(song.getChordAtPosition(3).character_num, 3)

    def test_process_key_pressed_arrow_transpose(self):
        """Up/Down arrows should transpose the selected chord."""
        song = create_test_song(self.app, song_id=10003, text="Test")
        self.app.current_song = song
        self.app.selected_char_num = 0
        self.app.previous_song_text = "Test"

        self.app.processKeyPressed(Qt.Key.Key_C)
        self.assertEqual(song.getChordAtPosition(0).note_id, 0)

        self.app.processKeyPressed(Qt.Key.Key_Up)  # C -> C#
        self.assertEqual(song.getChordAtPosition(0).note_id, 1)

        self.app.processKeyPressed(Qt.Key.Key_Down)  # C# -> C
        self.assertEqual(song.getChordAtPosition(0).note_id, 0)


# ---------------------------------------------------------------------------
# Tests for hit-testing core functionality (determineClickedLetter + getCharRects)
# These are fundamental for all mouse-based chord interaction.
# ---------------------------------------------------------------------------


class TestAppHitTesting(unittest.TestCase):
    """
    Tests for determineClickedLetter and getCharRects — the core hit-testing
    logic used by mouse events in CustomTextEdit.
    """

    @classmethod
    def setUpClass(cls):
        if not QtWidgets.QApplication.instance():
            cls.qapp = QtWidgets.QApplication([])
        else:
            cls.qapp = QtWidgets.QApplication.instance()

    def setUp(self):
        self.app = softchord.App([])
        self.app.win = QtWidgets.QWidget()
        open_empty_temp_songbook(self.app)
        insert_and_select_song(self.app, with_chord=True)

    def test_determine_clicked_letter_basic(self):
        """Basic smoke test that determineClickedLetter returns something sensible."""
        # Pick a position that should be over some text
        result = self.app.determineClickedLetter(50, 30, False)
        # It may return None or a tuple depending on exact layout, but it shouldn't crash
        self.assertTrue(result is None or isinstance(result, tuple))

    def test_determine_clicked_letter_dragging_flag(self):
        """The dragging flag should affect behavior near chords."""
        # Set up a fake dragging state
        if self.app.current_song and list(
                self.app.current_song.iterateAllChords()):
            chord = list(self.app.current_song.iterateAllChords())[0]
            self.app.editor.dragging_chord = chord

            result = self.app.determineClickedLetter(50, 30, True)
            # Should not crash and may return different results when dragging=True
            self.assertTrue(result is None or isinstance(result, tuple))

            self.app.editor.dragging_chord = None


# ---------------------------------------------------------------------------
# Tests for Chord Dialog editing core functionality
# (processSongCharEdit + ChordDialog)
# This is one of the two primary ways users edit chords (the other being keyboard).
# ---------------------------------------------------------------------------


class TestChordDialogEditing(unittest.TestCase):
    """
    Tests for the chord editing dialog flow:
    - processSongCharEdit (App-level logic)
    - ChordDialog (the actual dialog)
    """

    @classmethod
    def setUpClass(cls):
        if not QtWidgets.QApplication.instance():
            cls.qapp = QtWidgets.QApplication([])
        else:
            cls.qapp = QtWidgets.QApplication.instance()

    def setUp(self):
        self.app = softchord.App([])
        self.app.win = QtWidgets.QWidget()
        open_empty_temp_songbook(self.app)
        insert_and_select_song(self.app, with_chord=True)

    def test_process_song_char_edit_add_new_chord(self):
        """Calling processSongCharEdit on a position with no chord should add one after 'OK'."""
        # Choose a position unlikely to already have a chord in the test song
        song_char_num = 20

        # Patch ChordDialog.display to simulate user pressing OK with a modified chord
        original_display = softchord.ChordDialog.display

        def fake_display(self_dialog, chord):
            chord.note_id = 4  # E
            chord.chord_type_id = 1  # Minor
            chord.bass_note_id = -1
            chord.marker = ""
            chord.in_parentheses = False
            return True  # Simulate OK

        softchord.ChordDialog.display = fake_display

        try:
            initial_count = len(list(self.app.current_song.iterateAllChords()))
            self.app.processSongCharEdit(song_char_num)

            chords = list(self.app.current_song.iterateAllChords())
            new_chord = None
            for c in chords:
                if c.character_num == song_char_num:
                    new_chord = c
                    break

            self.assertIsNotNone(new_chord)
            self.assertEqual(new_chord.note_id, 4)
            self.assertEqual(new_chord.chord_type_id, 1)
            self.assertEqual(len(chords), initial_count + 1)
        finally:
            softchord.ChordDialog.display = original_display

    def test_process_song_char_edit_edit_existing_chord(self):
        """Editing an existing chord via the dialog path should replace it."""
        # Use a position that likely has a chord in the real songbook
        # Pick the first chord if any exist
        chords_before = list(self.app.current_song.iterateAllChords())
        if not chords_before:
            self.skipTest("No chords in the loaded song for this test")

        target_chord = chords_before[0]
        song_char_num = target_chord.character_num

        original_display = softchord.ChordDialog.display

        def fake_display(self_dialog, chord):
            chord.note_id = 7  # G
            chord.chord_type_id = 0  # Major
            return True

        softchord.ChordDialog.display = fake_display

        try:
            self.app.processSongCharEdit(song_char_num)

            updated_chord = self.app.current_song.getChordAtPosition(
                song_char_num)
            self.assertEqual(updated_chord.note_id, 7)
            self.assertEqual(updated_chord.chord_type_id, 0)
        finally:
            softchord.ChordDialog.display = original_display

    def test_process_song_char_edit_cancel_does_nothing(self):
        """If the dialog returns False (Cancel), no change should occur."""
        chords_before = list(self.app.current_song.iterateAllChords())
        if not chords_before:
            self.skipTest("No chords in the loaded song for this test")

        target_chord = chords_before[0]
        song_char_num = target_chord.character_num

        original_display = softchord.ChordDialog.display

        def fake_display(self_dialog, chord):
            return False  # Simulate Cancel

        softchord.ChordDialog.display = fake_display

        try:
            self.app.processSongCharEdit(song_char_num)

            chords_after = list(self.app.current_song.iterateAllChords())
            self.assertEqual(len(chords_after), len(chords_before))
            # The original chord object should be unchanged in its key attributes
            still_there = self.app.current_song.getChordAtPosition(
                song_char_num)
            self.assertIsNotNone(still_there)
        finally:
            softchord.ChordDialog.display = original_display


# ---------------------------------------------------------------------------
# Tests for Rendering / Drawing core functionality
# (drawSongToRect, drawChord, getCharRects, getChordWidth, etc.)
# These are critical because they power both on-screen display and all
# PDF / printing export paths.
# ---------------------------------------------------------------------------


class TestAppRendering(unittest.TestCase):
    """
    Tests for the core rendering pipeline.
    """

    @classmethod
    def setUpClass(cls):
        if not QtWidgets.QApplication.instance():
            cls.qapp = QtWidgets.QApplication([])
        else:
            cls.qapp = QtWidgets.QApplication.instance()

    def setUp(self):
        self.app = softchord.App([])
        self.app.win = QtWidgets.QWidget()
        open_empty_temp_songbook(self.app)
        insert_and_select_song(self.app, with_chord=True)

    def test_get_chord_width(self):
        """getChordWidth should return a reasonable positive width."""
        width = self.app.getChordWidth("C#m7")
        self.assertGreater(width, 0)

        width_sharp = self.app.getChordWidth("C♯")
        self.assertGreater(width_sharp, 0)

    def test_draw_chord_does_not_crash(self):
        """Basic smoke test for drawChord using an offscreen painter."""
        image = QtGui.QImage(200, 50, QtGui.QImage.Format.Format_ARGB32)
        image.fill(QtCore.Qt.GlobalColor.white)
        painter = QtGui.QPainter(image)

        rect = QtCore.QRectF(10, 10, 80, 20)
        self.app.drawChord(painter, rect, "Am7")

        painter.end()
        # If we got here without exception, the method works at a basic level.

    def test_draw_song_to_rect_smoke(self):
        """Call drawSongToRect with a real song and offscreen painter."""
        if not self.app.current_song:
            self.skipTest("No current song available")

        image = QtGui.QImage(400, 300, QtGui.QImage.Format.Format_ARGB32)
        image.fill(QtCore.Qt.GlobalColor.white)
        painter = QtGui.QPainter(image)

        rect = QtCore.QRectF(0, 0, 400, 300)

        # Non-exporting (screen) mode
        self.app.drawSongToRect(self.app.current_song,
                                painter,
                                self.app.editor,
                                rect,
                                exporting=False)

        # Exporting mode
        self.app.drawSongToRect(self.app.current_song,
                                painter,
                                self.app.editor,
                                rect,
                                exporting=True)

        painter.end()
        # Success = no crash

    def test_draw_song_to_rect_exporting_headers(self):
        """When exporting=True, song number/title/key should be considered in layout."""
        if not self.app.current_song:
            self.skipTest("No current song")

        # Ensure the song has some header data
        original_number = self.app.current_song.number
        self.app.current_song.number = 42

        image = QtGui.QImage(400, 300, QtGui.QImage.Format.Format_ARGB32)
        painter = QtGui.QPainter(image)
        rect = QtCore.QRectF(0, 0, 400, 300)

        try:
            self.app.drawSongToRect(self.app.current_song,
                                    painter,
                                    self.app.editor,
                                    rect,
                                    exporting=True)
        finally:
            self.app.current_song.number = original_number
            painter.end()


# ---------------------------------------------------------------------------
# Minimal tests for previously untested large areas:
# - Printing helpers
# - PDF configuration dialog + PdfOptions
# - Font change methods
# - Chord clipboard (cut/copy/pasteSelected)
# ---------------------------------------------------------------------------


class TestPrintingPdfFontClipboard(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not QtWidgets.QApplication.instance():
            cls.qapp = QtWidgets.QApplication([])
        else:
            cls.qapp = QtWidgets.QApplication.instance()

    def setUp(self):
        self.app = softchord.App([])
        self.app.win = QtWidgets.QWidget()

        open_empty_temp_songbook(self.app)
        insert_and_select_song(self.app, with_chord=True)

    # --- Printing helpers ---
    def test_get_printable_height(self):
        """Basic sanity check on getPrintableHeight helper."""
        # Create a dummy printer (we don't need a real one for this calculation)
        printer = QtPrintSupport.QPrinter()
        height = self.app.getPrintableHeight(printer)
        self.assertGreater(height, 0)

    def test_create_print_editor(self):
        """createPrintEditor should return a properly configured editor."""
        editor = self.app.createPrintEditor()
        self.assertIsNotNone(editor)
        self.assertEqual(editor.lineWrapMode(),
                         QtWidgets.QTextEdit.LineWrapMode.NoWrap)

    # --- PDF Configuration (PdfOptions data class) ---
    def test_pdf_options_defaults(self):
        """PdfOptions should have sensible defaults."""
        opts = softchord.PdfOptions()
        self.assertEqual(opts.left_margin, 0.5)
        self.assertFalse(opts.print_4_per_page)
        self.assertTrue(opts.print_song_num)

    # --- Font change methods (mock the Qt dialog) ---
    def test_change_fonts_do_not_crash_with_mocked_dialog(self):
        """Calling the font change methods should not blow up when we mock the dialog."""
        original_get_font = QtWidgets.QFontDialog.getFont

        # Mock: always "accept" and return a slightly modified font
        def fake_get_font(font, parent=None):
            new_font = QtGui.QFont(font)
            new_font.setPointSize(14)
            return new_font, True

        QtWidgets.QFontDialog.getFont = staticmethod(fake_get_font)

        try:
            self.app.changeLyricsFont()
            self.app.changeChordFont()
            # If we reach here, the methods executed their "OK" paths
        finally:
            QtWidgets.QFontDialog.getFont = original_get_font

    # --- Chord clipboard operations ---
    def test_copy_selected_chord(self):
        """copySelected should put the chord text into the (fake) clipboard."""
        if not self.app.current_song or not list(
                self.app.current_song.iterateAllChords()):
            self.skipTest("No chords in loaded song for clipboard test")

        # Select the first chord
        first_chord = list(self.app.current_song.iterateAllChords())[0]
        self.app.selected_char_num = first_chord.character_num

        self.app.copySelected()
        clipboard_text = self.app.clipboard.text()
        self.assertIn(first_chord.getChordText(), clipboard_text)

    def test_cut_selected_chord(self):
        """cutSelected should copy text and remove the chord."""
        if not self.app.current_song or len(
                list(self.app.current_song.iterateAllChords())) < 1:
            self.skipTest("Need at least one chord")

        first_chord = list(self.app.current_song.iterateAllChords())[0]
        pos = first_chord.character_num
        original_count = len(list(self.app.current_song.iterateAllChords()))

        self.app.selected_char_num = pos
        self.app.cutSelected()

        self.assertEqual(len(list(self.app.current_song.iterateAllChords())),
                         original_count - 1)
        # Clipboard should have the text
        self.assertTrue(len(self.app.clipboard.text()) > 0)


# ---------------------------------------------------------------------------
# Additional minimal tests for other zero-coverage areas
# (song metadata editing, songbook file ops, more import helpers)
# ---------------------------------------------------------------------------


class TestSongMetadataAndSongbookOps(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not QtWidgets.QApplication.instance():
            cls.qapp = QtWidgets.QApplication([])
        else:
            cls.qapp = QtWidgets.QApplication.instance()

    def setUp(self):
        self.app = softchord.App([])
        self.app.win = QtWidgets.QWidget()
        open_empty_temp_songbook(self.app)
        insert_and_select_song(self.app, with_chord=True)

    # --- Song metadata editing (title, subtitle, number, key) ---
    def test_current_song_title_edited_updates_model_and_db(self):
        if not self.app.current_song:
            self.skipTest("No current song")

        original_title = self.app.current_song.title or "Original"
        new_title = "Updated Title 12345"

        self.app.currentSongTitleEdited(new_title)

        # Check in-memory song object
        self.assertEqual(self.app.current_song.title, new_title)

        # Check it propagated to the table model
        row_num = self.app.songs_model.getSongsRow(self.app.current_song)
        rowobj = self.app.songs_model.getRow(row_num)
        self.assertEqual(rowobj.title, new_title)

    def test_title_edit_on_readonly_songbook_reverts_and_explains(self):
        previous = self.app.current_song.title
        self.app.curs.execute("PRAGMA query_only = ON")
        errors = []
        self.app.error = lambda text: errors.append(text)

        self.app.currentSongTitleEdited("Nope")

        self.assertEqual(self.app.current_song.title, previous)
        self.assertEqual(self.app.ui.song_title_ef.text(), previous)
        self.assertEqual(len(errors), 1)
        self.assertIn("read-only", errors[0].lower())
        self.assertIn("Save Songbook As", errors[0])
        self.assertNotIn("Traceback", errors[0])
        self.assertNotIn("OperationalError", errors[0])
        saved = self.app.curs.execute("SELECT title FROM songs").fetchone()[0]
        self.assertEqual(saved, previous)

        self.app.currentSongTitleEdited("Still nope")
        self.assertEqual(len(errors), 1)
        self.assertEqual(self.app.current_song.title, previous)

    def test_title_edit_reopens_a_replaced_songbook_file(self):
        path = self.app.current_songbook_filename
        replaced = path + ".replaced"
        os.rename(path, replaced)
        shutil.copy(replaced, path)
        errors = []
        self.app.error = lambda text: errors.append(text)

        self.app.currentSongTitleEdited("After replace")

        self.assertEqual(errors, [])
        self.assertEqual(self.app.current_song.title, "After replace")
        saved = self.app.curs.execute(
            "SELECT title FROM songs WHERE id=?",
            (self.app.current_song.id,)).fetchone()[0]
        self.assertEqual(saved, "After replace")
        old = sqlite3.connect(replaced)
        try:
            old_title = old.execute("SELECT title FROM songs").fetchone()[0]
        finally:
            old.close()
        self.assertEqual(old_title, "Test Song")

    def test_save_readonly_songbook_opens_a_writable_copy(self):
        self.app.curs.execute("PRAGMA query_only = ON")
        dest = os.path.join(tempfile.mkdtemp(), "copy.songbook")
        original_get_save = QtWidgets.QFileDialog.getSaveFileName
        QtWidgets.QFileDialog.getSaveFileName = staticmethod(
            lambda *a, **k: (dest, ""))
        try:
            self.app.saveSongbook()
        finally:
            QtWidgets.QFileDialog.getSaveFileName = original_get_save

        self.assertEqual(os.path.abspath(self.app.current_songbook_filename),
                         os.path.abspath(dest))
        self.app.curs.execute("UPDATE songs SET title=? WHERE id=0",
                              ("Saved",))
        self.app.curs.commit()
        saved = self.app.curs.execute(
            "SELECT title FROM songs WHERE id=0").fetchone()[0]
        self.assertEqual(saved, "Saved")

    def test_switching_songs_on_readonly_songbook_does_not_raise(self):
        # A chord that exists only in memory forces INSERT, the same write
        # that crashed when the selection changed on a read-only songbook.
        song = self.app.current_song
        song._addChord(SongChord(song, 5, 2, 0, -1, "", 0))
        self.app.curs.execute(
            "INSERT INTO songs (id, number, title, subtitle, text) "
            "VALUES (1, 2, 'Other', '', 'line')")
        self.app.curs.commit()
        self.app.songs_model.updateFromDatabase()
        self.app.curs.execute("PRAGMA query_only = ON")

        self.app.setCurrentSong(Song(self.app, 1))
        self.assertEqual(self.app.current_song.id, 1)

        # The selection callback commits, then flushes again. Neither may raise.
        self.app.songsSelectionChangedCallback()
        self.assertIsNotNone(self.app.current_song)

    def test_subtitle_edited(self):
        if not self.app.current_song:
            self.skipTest("No current song")

        self.app.subtitleEdited("New Subtitle Test")
        self.assertEqual(self.app.current_song.subtitle, "New Subtitle Test")

    def test_current_song_number_edited(self):
        if not self.app.current_song:
            self.skipTest("No current song")

        self.app.currentSongNumberEdited("42")
        self.assertEqual(self.app.current_song.number, 42)

    # --- Songbook management (heavily mocked because of dialogs) ---
    def test_close_songbook_clears_current_song(self):
        if not self.app.current_song:
            self.skipTest("No current song")

        self.app.closeSongbook()
        self.assertIsNone(self.app.current_song)
        self.assertIsNone(self.app.current_songbook_filename)

    # --- More import helper smoke tests ---
    def test_import_song_from_text_basic(self):
        """Smoke test for the lower-level import helper."""
        initial_count = self.app.songs_model.rowCount()

        self.app.importSongFromText("Test Title\nSome lyrics here",
                                    "Test Imported Title")

        self.assertEqual(self.app.songs_model.rowCount(), initial_count + 1)


# ---------------------------------------------------------------------------
# Minimal tests for more zero-coverage App operations
# (songbook file ops, ChordPro import, renumber, set ID, paste as new song,
# getSelectedChord, etc.)
# ---------------------------------------------------------------------------


class TestMoreAppOperations(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not QtWidgets.QApplication.instance():
            cls.qapp = QtWidgets.QApplication([])
        else:
            cls.qapp = QtWidgets.QApplication.instance()

    def setUp(self):
        # Use a real App (with mocked dialogs) so curs, models, etc. are properly initialized
        self.app = softchord.App([])
        self.app.win = QtWidgets.QWidget()

        # Mock all dialog methods so nothing blocks
        self.app.info = lambda text: None
        self.app.warning = lambda text: None
        self.app.error = lambda text: None
        self.app.question = lambda *a, **k: True

        open_empty_temp_songbook(self.app)

    # --- Songbook file operations (dialogs heavily mocked) ---
    def test_new_songbook_creates_tables(self):
        # Mock the save dialog to return a fake path
        original_get_save = QtWidgets.QFileDialog.getSaveFileName
        QtWidgets.QFileDialog.getSaveFileName = staticmethod(
            lambda *a, **k: ("/tmp/test_new.songbook", ""))

        try:
            self.app.newSongbook()
            # After newSongbook, curs should be set and tables should exist
            self.assertIsNotNone(self.app.curs)
            tables = [
                row[0] for row in self.app.curs.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")
            ]
            self.assertIn("songs", tables)
            self.assertIn("song_chord_link", tables)
        finally:
            QtWidgets.QFileDialog.getSaveFileName = original_get_save

    def test_new_songbook_opens_a_single_connection(self):
        self._open_empty_temp_songbook()
        path = os.path.join(tempfile.mkdtemp(), "brand_new.songbook")
        original_get_save = QtWidgets.QFileDialog.getSaveFileName
        QtWidgets.QFileDialog.getSaveFileName = staticmethod(
            lambda *a, **k: (path, ""))
        original_connect = sqlite3.connect
        created = []

        def tracking_connect(*args, **kwargs):
            conn = original_connect(*args, **kwargs)
            created.append(conn)
            return conn

        sqlite3.connect = tracking_connect
        try:
            self.app.newSongbook()
        finally:
            sqlite3.connect = original_connect
            QtWidgets.QFileDialog.getSaveFileName = original_get_save

        self.assertEqual(len(created), 1)
        self.assertIs(created[0], self.app.curs)
        tables = [
            row[0] for row in self.app.curs.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")
        ]
        self.assertIn("songs", tables)
        self.assertIn("song_chord_link", tables)

    def test_save_songbook_error_text_and_format_filter(self):
        self._open_empty_temp_songbook()
        captured = {}
        original_get_save = QtWidgets.QFileDialog.getSaveFileName

        def fake_get_save(*args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs
            return ("/tmp/new_place.songbook", "")

        QtWidgets.QFileDialog.getSaveFileName = staticmethod(fake_get_save)
        errors = []
        self.app.error = lambda text: errors.append(text)
        original_copy = shutil.copyfile

        def boom(src, dst):
            raise OSError("disk full")

        shutil.copyfile = boom
        original_set = self.app.setCurrentSongbook
        self.app.setCurrentSongbook = lambda filename: None
        try:
            self.app.saveSongbook()
        finally:
            QtWidgets.QFileDialog.getSaveFileName = original_get_save
            shutil.copyfile = original_copy
            self.app.setCurrentSongbook = original_set

        filter_text = " ".join(str(a) for a in captured["args"])
        self.assertIn("Songbook format", filter_text)
        self.assertNotIn("foramt", filter_text)
        self.assertEqual(len(errors), 1)
        self.assertIn("Could not save", errors[0])
        self.assertNotIn("Could save the", errors[0])

    def test_save_songbook_failed_copy_keeps_current_songbook(self):
        self._open_empty_temp_songbook()
        original_path = self.app.current_songbook_filename
        dest = os.path.join(tempfile.mkdtemp(), "new.songbook")
        original_get_save = QtWidgets.QFileDialog.getSaveFileName
        QtWidgets.QFileDialog.getSaveFileName = staticmethod(
            lambda *a, **k: (dest, ""))
        errors = []
        self.app.error = lambda text: errors.append(text)
        original_copy = shutil.copyfile

        def boom(src, dst):
            raise OSError("disk full")

        shutil.copyfile = boom
        try:
            self.app.saveSongbook()
        finally:
            QtWidgets.QFileDialog.getSaveFileName = original_get_save
            shutil.copyfile = original_copy

        self.assertEqual(len(errors), 1)
        self.assertIn("Could not save", errors[0])
        self.assertEqual(self.app.current_songbook_filename, original_path)
        self.assertFalse(os.path.exists(dest))

    def test_close_songbook_clears_state(self):
        # Setup a fake current song
        song = create_test_song(self.app, song_id=999, text="test")
        self.app.current_song = song
        self.app.current_songbook_filename = "something.songbook"

        self.app.closeSongbook()

        self.assertIsNone(self.app.current_song)
        self.assertIsNone(self.app.current_songbook_filename)

    # --- ChordPro import path ---
    def test_import_from_chordpro_text(self):
        chordpro_content = "{title:Test ChordPro Song}\n[C]Hello [G]World"

        initial_count = len(list(self.app.current_song.iterateAllChords())
                            ) if self.app.current_song else 0

        # This should not crash and should attempt parsing
        self.app.importSongFromChordProText(chordpro_content)

        # We mainly check it didn't raise and the method is exercised
        self.assertTrue(True)

    # --- Renumber songs ---
    def test_renumber_all_songs(self):
        # Force the question to return True (user accepts)
        self.app._last_question_result = True

        # Should not crash even with no songs or some songs
        self.app.renumberAllSongs()
        self.assertTrue(True)  # If we reach here, basic path worked

    # --- Paste as new song ---
    def test_paste_as_new_song(self):
        self.app.clipboard.setText("Pasted Song Title\nSome lyrics")

        initial_count = self.app.songs_model.rowCount() if hasattr(
            self.app, 'songs_model') else 0

        self.app.pasteAsNewSong()

        # It should have attempted an import (exact count depends on harness)
        self.assertTrue(True)

    def test_paste_as_new_song_readonly_database(self):
        self._open_empty_temp_songbook()
        self.app.curs.execute("PRAGMA query_only = ON")
        errors = []
        self.app.error = lambda text: errors.append(text)
        self.app.clipboard.setText("Pasted Song Title\nSome lyrics")

        self.app.pasteAsNewSong()

        self.assertEqual(len(errors), 1)
        self.assertIn("read-only", errors[0].lower())
        self.assertNotIn("Traceback", errors[0])
        self.assertNotIn("OperationalError", errors[0])
        self.assertEqual(self.app.songs_model.rowCount(), 0)

    # --- getSelectedChord helper ---
    def test_get_selected_chord(self):
        song = create_test_song(self.app, song_id=600, text="chord test")
        self.app.current_song = song
        self.app.selected_char_num = 0

        # Add a chord manually
        chord = SongChord(song, 0, 0, 0, -1, "", 0)
        song._addChord(chord)

        result = self.app.getSelectedChord()
        self.assertIsNotNone(result)
        self.assertEqual(result.character_num, 0)

    def _open_empty_temp_songbook(self):
        return open_empty_temp_songbook(self.app)

    def test_import_chordpro_and_text_with_non_ascii_filenames(self):
        """Issue #1: import files whose names have spaces and non-ASCII letters."""
        td = self._open_empty_temp_songbook()
        chordpro_path = os.path.join(td, "Bláznova ukolébavka.chordpro")
        text_path = os.path.join(td, "Bláznova ukolébavka.txt")
        with open(chordpro_path, "w", encoding="utf-8") as fh:
            fh.write("{title:Bláznova ukolébavka}\n[C]Ahoj [G]světe\n")
        with open(text_path, "w", encoding="utf-8") as fh:
            fh.write("Bláznova ukolébavka\nAhoj světe\n")

        self.app.importFromChordPro(chordpro_path)
        self.app.importTextFiles([text_path])
        self.assertEqual(self.app.songs_model.rowCount(), 2)

    def test_import_cp1250_encoded_files(self):
        """Issue #1: Czech Windows-1250 files that are not valid UTF-8."""
        td = self._open_empty_temp_songbook()
        chordpro_path = os.path.join(td, "Bláznova ukolébavka cp1250.chordpro")
        text_path = os.path.join(td, "Bláznova ukolébavka cp1250.txt")
        with open(chordpro_path, "wb") as fh:
            fh.write("{title:Bláznova ukolébavka}\n[C]Ahoj [G]světe\n".encode(
                "cp1250"))
        with open(text_path, "wb") as fh:
            fh.write("Bláznova ukolébavka\nAhoj světe\n".encode("cp1250"))

        self.app.importFromChordPro(chordpro_path)
        self.app.importTextFiles([text_path])
        self.assertEqual(self.app.songs_model.rowCount(), 2)

    def test_paste_as_new_song_requires_open_songbook(self):
        self.app.closeSongbook()
        warnings = []
        self.app.warning = lambda text: warnings.append(text)
        self.app.clipboard.setText("Title\nLyrics")
        self.app.pasteAsNewSong()
        self.assertEqual(len(warnings), 1)
        self.assertIn("song book", warnings[0].lower())

    def test_import_writes_the_song_through_the_store(self):
        inserted = []
        real = self.app.store.insert_song

        def insert_song(*args):
            inserted.append(args)
            return real(*args)

        self.app.store.insert_song = insert_song
        self.app.importSongFromText("Hello\nthere")
        self.assertEqual(len(inserted), 1)
        self.assertEqual(inserted[0][0], 0)
        self.assertEqual(inserted[0][2], "Hello")

    def test_import_song_from_text_uses_first_line_as_title(self):
        self._open_empty_temp_songbook()
        self.app.importSongFromText("1. Amazing grace\nHow sweet the sound")
        title, number, text = self.app.curs.execute(
            "SELECT title, number, text FROM songs").fetchone()
        self.assertEqual(title, "Amazing grace")
        self.assertEqual(number, -1)
        self.assertIn("How sweet the sound", text)

    def test_import_song_from_text_strips_chorus_and_pripev_prefixes(self):
        self._open_empty_temp_songbook()
        self.app.importSongFromText("Chorus Amazing grace\nHow sweet the sound")
        title = self.app.curs.execute("SELECT title FROM songs").fetchone()[0]
        self.assertEqual(title, "Amazing grace")

        self.app.curs.execute("DELETE FROM songs")
        self.app.curs.commit()
        self.app.importSongFromText("Припев Amazing grace\nHow sweet the sound")
        title = self.app.curs.execute("SELECT title FROM songs").fetchone()[0]
        self.assertEqual(title, "Amazing grace")

    def test_import_chordpro_stores_title_number_and_chords(self):
        self._open_empty_temp_songbook()
        self.app.importSongFromChordProText(
            "# comment\n{t:Hello}\n{subtitle:12}\n[C]Hi [G]there\n")
        title, number, text = self.app.curs.execute(
            "SELECT title, number, text FROM songs").fetchone()
        self.assertEqual(title, "Hello")
        self.assertEqual(number, 12)
        self.assertIn("Hi", text)
        notes = [
            row[0] for row in self.app.curs.execute(
                "SELECT note_id FROM song_chord_link ORDER BY character_num")
        ]
        self.assertEqual(notes, [0, 7])  # C, G

    def test_import_chordpro_stores_non_numeric_subtitle(self):
        self._open_empty_temp_songbook()
        self.app.importSongFromChordProText(
            "{title:Hello}\n{subtitle:Some note}\n[C]Hi\n")
        title, number, subtitle = self.app.curs.execute(
            "SELECT title, number, subtitle FROM songs").fetchone()
        self.assertEqual(title, "Hello")
        self.assertEqual(number, -1)
        self.assertEqual(subtitle, "Some note")

    def test_import_chordpro_st_alias_stores_subtitle(self):
        self._open_empty_temp_songbook()
        self.app.importSongFromChordProText(
            "{title:Hello}\n{st:From the alias}\n[C]Hi\n")
        title, subtitle = self.app.curs.execute(
            "SELECT title, subtitle FROM songs").fetchone()
        self.assertEqual(title, "Hello")
        self.assertEqual(subtitle, "From the alias")

    def test_import_empty_text_uses_unknown_title(self):
        self._open_empty_temp_songbook()
        self.app.importSongFromText("")
        title = self.app.curs.execute("SELECT title FROM songs").fetchone()[0]
        self.assertEqual(title, "Unknown")
        self.assertEqual(self.app.songs_model.rowCount(), 1)

    def test_lyrics_text_changed_shifts_chords_after_insert(self):
        self._open_empty_temp_songbook()
        song = create_test_song(self.app, song_id=0, text="Hello")
        self.app.current_song = song
        self.app.editor.setDocument(song.doc)
        song._addChord(SongChord(song, 0, 0, 0, -1, "", 0))
        self.app.ignore_song_text_changed = True
        self.app.editor.setPlainText("xHello")
        self.app.ignore_song_text_changed = False
        self.app.previous_song_text = "Hello"

        self.app.lyricsTextChanged()

        self.assertIsNone(song.getChordAtPosition(0))
        self.assertEqual(song.getChordAtPosition(1).note_id, 0)

    def test_lyrics_text_changed_drops_chord_on_deleted_char(self):
        self._open_empty_temp_songbook()
        song = create_test_song(self.app, song_id=0, text="Hello")
        self.app.current_song = song
        self.app.editor.setDocument(song.doc)
        song._addChord(SongChord(song, 0, 0, 0, -1, "", 0))
        self.app.ignore_song_text_changed = True
        self.app.editor.setPlainText("ello")
        self.app.ignore_song_text_changed = False
        self.app.previous_song_text = "Hello"

        self.app.lyricsTextChanged()

        self.assertEqual(list(song.iterateAllChords()), [])

    def test_save_songbook_copy_opens_new_file(self):
        self._open_empty_temp_songbook()
        dest = os.path.join(tempfile.mkdtemp(), "copied.songbook")
        original_get_save = QtWidgets.QFileDialog.getSaveFileName
        QtWidgets.QFileDialog.getSaveFileName = staticmethod(
            lambda *a, **k: (dest, ""))
        try:
            self.app.saveSongbook()
        finally:
            QtWidgets.QFileDialog.getSaveFileName = original_get_save
        self.assertEqual(self.app.current_songbook_filename, dest)
        self.assertTrue(os.path.isfile(dest))

    def test_export_text_and_chordpro(self):
        self._open_empty_temp_songbook()
        self.app.importSongFromChordProText("{title:Export Me}\n[C]Hello\n")
        self.app.ui.songs_view.selectRow(0)
        td = tempfile.mkdtemp()
        text_path = os.path.join(td, "out.txt")
        chordpro_path = os.path.join(td, "out.chordpro")
        self.app.exportToText(text_path)
        self.app.exportToChordPro(chordpro_path)
        with open(text_path, encoding="utf-8-sig") as fh:
            exported_text = fh.read()
        with open(chordpro_path, encoding="utf-8-sig") as fh:
            exported_chordpro = fh.read()
        self.assertIn("Hello", exported_text)
        self.assertIn("{title:Export Me}", exported_chordpro)
        self.assertIn("[C]", exported_chordpro)

    def test_export_writes_with_builtin_utf8_sig_open(self):
        self._open_empty_temp_songbook()
        self.app.importSongFromChordProText("{title:Export Me}\n[C]Hello\n")
        self.app.ui.songs_view.selectRow(0)
        td = tempfile.mkdtemp()
        text_path = os.path.join(td, "out.txt")
        chordpro_path = os.path.join(td, "out.chordpro")
        import builtins
        real_open = builtins.open
        opened = []

        def tracking_open(*args, **kwargs):
            opened.append((args, kwargs))
            return real_open(*args, **kwargs)

        builtins.open = tracking_open
        try:
            self.app.exportToText(text_path)
            self.app.exportToChordPro(chordpro_path)
        finally:
            builtins.open = real_open

        encodings = {}
        for args, kwargs in opened:
            if args and args[0] in (text_path, chordpro_path):
                encodings[args[0]] = kwargs.get("encoding")
        self.assertEqual(encodings.get(text_path), "utf-8-sig")
        self.assertEqual(encodings.get(chordpro_path), "utf-8-sig")

    def test_export_text_requires_one_selected_song(self):
        self._open_empty_temp_songbook()
        errors = []
        self.app.error = lambda text: errors.append(text)
        self.app.exportToText(os.path.join(tempfile.mkdtemp(), "out.txt"))
        self.assertEqual(len(errors), 1)
        self.assertIn("No songs are selected", errors[0])

    def _count_wait_cursor_calls(self, func, *args):
        waits = []
        restores = []
        orig_wait = self.app.setWaitCursor
        orig_restore = self.app.restoreCursor

        def wait():
            waits.append(1)
            orig_wait()

        def restore():
            restores.append(1)
            orig_restore()

        self.app.setWaitCursor = wait
        self.app.restoreCursor = restore
        try:
            func(*args)
        finally:
            self.app.setWaitCursor = orig_wait
            self.app.restoreCursor = orig_restore
        return waits, restores

    def test_export_restores_cursor_when_selection_is_invalid(self):
        self._open_empty_temp_songbook()
        errors = []
        self.app.error = lambda text: errors.append(text)
        out = os.path.join(tempfile.mkdtemp(), "out.txt")

        waits, restores = self._count_wait_cursor_calls(
            self.app.exportToText, out)
        self.assertGreaterEqual(len(waits), 1)
        self.assertEqual(len(waits), len(restores))

        waits, restores = self._count_wait_cursor_calls(
            self.app.exportToChordPro, out)
        self.assertGreaterEqual(len(waits), 1)
        self.assertEqual(len(waits), len(restores))
        self.assertEqual(len(errors), 2)

    def test_append_songbook_copies_songs(self):
        self._open_empty_temp_songbook()
        self.app.importSongFromText("Keep me\nAlready here")
        source_dir = tempfile.mkdtemp()
        source_path = os.path.join(source_dir, "source.songbook")
        conn = sqlite3.connect(source_path)
        conn.execute(SONG_CHORD_LINK_TABLE_SQL)
        conn.execute(SONGS_TABLE_SQL)
        conn.execute(
            "INSERT INTO songs (id, number, title, subtitle, text) "
            "VALUES (0, 5, 'Appended', 'sub', 'New lyrics')")
        conn.commit()
        conn.close()

        self.app.appendSongbookFile(source_path)
        rows = list(self.app.curs.execute(
            "SELECT title, number, subtitle, text FROM songs ORDER BY id"))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][0], "Keep me")
        self.assertEqual(rows[1], ("Appended", 5, "sub", "New lyrics"))

    def test_append_songbook_copies_chords_onto_new_song_ids(self):
        """Appending must copy chords by source song id onto new dest ids."""
        self._open_empty_temp_songbook()
        self.app.importSongFromText("Keep me\nAlready here")
        source_path = os.path.join(tempfile.mkdtemp(), "source.songbook")
        conn = sqlite3.connect(source_path)
        conn.execute(SONG_CHORD_LINK_TABLE_SQL)
        conn.execute(SONGS_TABLE_SQL)
        conn.execute(
            "INSERT INTO songs (id, number, title, subtitle, text) "
            "VALUES (0, 1, 'First', '', 'Hello'), "
            "(1, 2, 'Second', '', 'World')")
        conn.execute(
            "INSERT INTO song_chord_link (id, song_id, character_num, "
            "note_id, chord_type_id, bass_note_id, marker, in_parentheses) "
            "VALUES (0, 0, 0, 0, 0, -1, '', 0), "
            "(1, 1, 0, 7, 0, -1, '', 1)")
        conn.commit()
        conn.close()

        self.app.appendSongbookFile(source_path)

        dest_songs = list(
            self.app.curs.execute("SELECT id, title FROM songs ORDER BY id"))
        self.assertEqual([row[1] for row in dest_songs],
                         ["Keep me", "First", "Second"])
        dest_ids = {title: song_id for song_id, title in dest_songs}
        chords = list(
            self.app.curs.execute(
                "SELECT song_id, character_num, note_id, in_parentheses "
                "FROM song_chord_link ORDER BY song_id"))
        self.assertEqual(chords, [
            (dest_ids["First"], 0, 0, 0),
            (dest_ids["Second"], 0, 7, 1),
        ])

    def test_remove_trailing_spaces_updates_current_song(self):
        self._open_empty_temp_songbook()
        self.app.curs.execute(
            "INSERT INTO songs (id, number, title, subtitle, text) "
            "VALUES (0, 1, 'Trim Me', '', 'Hi  \nGo')")
        self.app.curs.commit()
        self.app.songs_model.updateFromDatabase()
        self.app.ui.songs_view.selectRow(0)

        self.assertIsNotNone(self.app.current_song)
        self.assertEqual(self.app.current_song.getAllText(), "Hi  \nGo")

        self.app.removeTrailingSpaces()

        self.assertEqual(self.app.current_song.getAllText(), "Hi\nGo")
        self.assertEqual(self.app.editor.toPlainText(), "Hi\nGo")
        stored = self.app.curs.execute("SELECT text FROM songs").fetchone()[0]
        self.assertEqual(stored, "Hi\nGo")

    def test_remove_trailing_spaces_keeps_unsaved_lyric_edits(self):
        self._open_empty_temp_songbook()
        self.app.curs.execute(
            "INSERT INTO songs (id, number, title, subtitle, text) "
            "VALUES (0, 1, 'Trim Me', '', 'Hi  \nGo')")
        self.app.curs.commit()
        self.app.songs_model.updateFromDatabase()
        self.app.ui.songs_view.selectRow(0)
        self.app.current_song.doc.setPlainText("xHi  \nGo")
        self.app.previous_song_text = "xHi  \nGo"

        self.app.removeTrailingSpaces()

        self.assertEqual(self.app.current_song.getAllText(), "xHi\nGo")
        stored = self.app.curs.execute("SELECT text FROM songs").fetchone()[0]
        self.assertEqual(stored, "xHi\nGo")


class TestReadImportTextFile(unittest.TestCase):

    def test_utf8_and_cp1250(self):
        td = tempfile.mkdtemp()
        utf8_path = os.path.join(td, "utf8.txt")
        cp1250_path = os.path.join(td, "cp1250.txt")
        text = "Bláznova ukolébavka"
        with open(utf8_path, "w", encoding="utf-8") as fh:
            fh.write(text)
        with open(cp1250_path, "wb") as fh:
            fh.write(text.encode("cp1250"))
        self.assertEqual(read_import_text_file(utf8_path), text)
        self.assertEqual(read_import_text_file(cp1250_path), text)


class TestConnectExistingSongbook(unittest.TestCase):
    """connect_existing_songbook rejects junk files and opens real songbooks."""

    def _write_songbook(self, path, with_songs_table=True):
        conn = sqlite3.connect(path)
        if with_songs_table:
            conn.execute(SONG_CHORD_LINK_TABLE_SQL)
            conn.execute(SONGS_TABLE_SQL)
            conn.execute(
                "INSERT INTO songs (id, number, title, subtitle, text) "
                "VALUES (0, 1, 'One', '', 'lyrics')")
        else:
            conn.execute("CREATE TABLE other (id INTEGER)")
        conn.commit()
        conn.close()

    def test_opens_valid_songbook(self):
        path = os.path.join(tempfile.mkdtemp(), "ok.songbook")
        self._write_songbook(path)
        conn = softchord.connect_existing_songbook(path)
        try:
            title = conn.execute("SELECT title FROM songs").fetchone()[0]
            self.assertEqual(title, "One")
        finally:
            conn.close()

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            softchord.connect_existing_songbook(
                os.path.join(tempfile.mkdtemp(), "missing.songbook"))

    def test_empty_file(self):
        path = os.path.join(tempfile.mkdtemp(), "empty.songbook")
        open(path, "wb").close()
        with self.assertRaises(ValueError) as ctx:
            softchord.connect_existing_songbook(path)
        self.assertIn("empty", str(ctx.exception).lower())

    def test_not_sqlite(self):
        path = os.path.join(tempfile.mkdtemp(), "junk.songbook")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("not a database")
        with self.assertRaises(ValueError) as ctx:
            softchord.connect_existing_songbook(path)
        self.assertIn("not a valid", str(ctx.exception).lower())

    def test_sqlite_without_songs_table(self):
        path = os.path.join(tempfile.mkdtemp(), "other.songbook")
        self._write_songbook(path, with_songs_table=False)
        with self.assertRaises(ValueError) as ctx:
            softchord.connect_existing_songbook(path)
        self.assertIn("missing songs table", str(ctx.exception).lower())

    def test_normalize_local_path(self):
        self.assertEqual(softchord._normalize_local_path(""), "")
        self.assertEqual(softchord._normalize_local_path(None), None)
        path = "/tmp/foo.songbook"
        url = QtCore.QUrl.fromLocalFile(path).toString()
        self.assertTrue(url.startswith("file:"))
        self.assertEqual(softchord._normalize_local_path(url), path)
        self.assertEqual(softchord._normalize_local_path(path), path)


class _Root:
    """Minimal chord stand-in: (note_id, is_minor)."""

    def __init__(self, char, note_id, chord_type_id=0):
        self.character_num = char
        self.note_id = note_id
        self.chord_type_id = chord_type_id


def _repeat_prog(prog, times, start_char=0, step=4):
    chords = []
    char = start_char
    for _ in range(times):
        for note, typ in prog:
            chords.append(_Root(char, note, typ))
            char += step
    return chords


class TestAutoDetectedKey(unittest.TestCase):
    """Issue-style: spell accidentals from local key, including modulations."""

    @classmethod
    def setUpClass(cls):
        if not QtWidgets.QApplication.instance():
            cls.qapp = QtWidgets.QApplication([])
        else:
            cls.qapp = QtWidgets.QApplication.instance()

    A_PROG = [(9, 0), (4, 0), (6, 1), (2, 0)]  # A E F#m D
    BB_PROG = [(10, 0), (5, 0), (7, 1), (3, 0)]  # Bb F Gm Eb

    def test_a_major_region_uses_sharps(self):
        chords = _repeat_prog(self.A_PROG, 3)
        key = best_detected_key(chords)
        self.assertEqual(key.label, "A")
        self.assertEqual(key.prefer, PREFER_SHARPS)
        app = MinimalTestApp()
        song = create_test_song(app, text="x" * 80)
        for i, ch in enumerate(chords):
            song._addChord(SongChord(song, ch.character_num, ch.note_id,
                                     ch.chord_type_id, -1, "", 0))
        fsharp = [c for c in song.iterateAllChords() if c.note_id == 6][0]
        self.assertIn("F♯", fsharp.getChordText())
        self.assertNotIn("G♭", fsharp.getChordText())

    def test_bb_major_region_uses_flats(self):
        chords = _repeat_prog(self.BB_PROG, 3)
        key = best_detected_key(chords)
        self.assertEqual(key.label, "B♭")
        self.assertEqual(key.prefer, PREFER_FLATS)
        app = MinimalTestApp()
        song = create_test_song(app, text="x" * 80)
        for ch in chords:
            song._addChord(SongChord(song, ch.character_num, ch.note_id,
                                     ch.chord_type_id, -1, "", 0))
        bb = [c for c in song.iterateAllChords() if c.note_id == 10][0]
        eb = [c for c in song.iterateAllChords() if c.note_id == 3][0]
        self.assertIn("B♭", bb.getChordText())
        self.assertIn("E♭", eb.getChordText())

    def test_modulation_splits_without_lyrics(self):
        a_chords = _repeat_prog(self.A_PROG, 4, start_char=0)
        bb_chords = _repeat_prog(self.BB_PROG, 4, start_char=200)
        chords = a_chords + bb_chords
        starts = detect_region_start_indices(chords)
        self.assertGreaterEqual(len(starts), 2)
        self.assertEqual(starts[0], 0)
        # Second region should begin at or after the Bb block
        self.assertGreaterEqual(starts[1], len(a_chords) - 1)

        app = MinimalTestApp()
        song = create_test_song(app, text="x" * 400)
        for ch in chords:
            song._addChord(SongChord(song, ch.character_num, ch.note_id,
                                     ch.chord_type_id, -1, "", 0))
        labels = format_auto_detected_key_text(song._regions)
        self.assertEqual(labels, "Auto-detected key: A, B♭")
        first_fsharp = [
            c for c in song.iterateAllChords()
            if c.note_id == 6 and c.character_num < 200
        ][0]
        first_bb = [
            c for c in song.iterateAllChords()
            if c.note_id == 10 and c.character_num >= 200
        ][0]
        self.assertIn("F♯", first_fsharp.getChordText())
        self.assertIn("B♭", first_bb.getChordText())

    def test_all_flats_no_false_split(self):
        chords = _repeat_prog(self.BB_PROG, 6)
        self.assertEqual(detect_region_start_indices(chords), [0])
        self.assertEqual(best_detected_key(chords).prefer, PREFER_FLATS)

    def test_relative_pair_is_one_key(self):
        # F#m-centered but relative of A: F#m, C#m, D, A, E
        prog = [(6, 1), (1, 1), (2, 0), (9, 0), (4, 0)]
        chords = _repeat_prog(prog, 3)
        key = best_detected_key(chords)
        self.assertIn(key.label, ("A", "F♯m"))
        self.assertEqual(key.prefer, PREFER_SHARPS)
        self.assertEqual(detect_region_start_indices(chords), [0])

    def test_am_to_bm_modulation(self):
        """Am (no accidentals) then Bm (sharps) must split, not stay one key."""
        am_prog = [(9, 1), (2, 1), (4, 0), (9, 1), (2, 1), (7, 0), (0, 0),
                   (9, 1)]  # Am Dm E Am Dm G C Am
        bm_prog = [(11, 1), (4, 1), (6, 0), (11, 1), (4, 1), (9, 0), (2, 0),
                   (11, 1)]  # Bm Em F# Bm Em A D Bm
        am_chords = _repeat_prog(am_prog, 2, start_char=0)
        pivot = [_Root(400, 6, 0)]  # F#
        bm_chords = _repeat_prog(bm_prog, 2, start_char=420)
        chords = am_chords + pivot + bm_chords
        self.assertEqual(best_detected_key(am_chords).label, "Am")
        self.assertEqual(best_detected_key(bm_chords).label, "Bm")
        starts = detect_region_start_indices(chords)
        self.assertGreaterEqual(len(starts), 2)
        # F# pivot belongs with the Bm half (V of Bm).
        self.assertEqual(starts[1], len(am_chords))
        app = MinimalTestApp()
        song = create_test_song(app, text="x" * 600)
        for ch in chords:
            song._addChord(
                SongChord(song, ch.character_num, ch.note_id, ch.chord_type_id,
                          -1, "", 0))
        self.assertEqual(format_auto_detected_key_text(song._regions),
                         "Auto-detected key: Am, Bm")

    def test_nebo_nebes_am_then_bm(self):
        """«Поднимаю глаза…»: verse/chorus in Am, then F♯ modulation to Bm.

        Equal Am/Dm (and Bm/Em) counts must not win as Dm then Em.
        """
        # Exact chord_type/root sequence from zvuki_neba song 178.
        seq = [
            (9, 1), (2, 1), (4, 0), (9, 1), (2, 1), (7, 0), (0, 0), (9, 1),
            (2, 1), (7, 0), (0, 0), (9, 1), (2, 1), (4, 0), (9, 1), (2, 1),
            (7, 0), (0, 0), (9, 1), (2, 1), (4, 0), (9, 1),
            (6, 0),  # F♯ modulation
            (11, 1), (4, 1), (6, 0), (11, 1), (4, 1), (9, 0), (2, 0), (11, 1),
            (4, 1), (9, 0), (2, 0), (11, 1), (4, 1), (6, 0), (11, 1),
            (4, 1), (9, 0), (2, 0), (11, 1), (4, 1), (6, 0), (11, 1),
        ]
        chords = [_Root(i * 10, n, t) for i, (n, t) in enumerate(seq)]
        self.assertEqual(best_detected_key(chords[:22]).label, "Am")
        self.assertEqual(best_detected_key(chords[22:]).label, "Bm")
        starts = detect_region_start_indices(chords)
        self.assertEqual(starts[:2], [0, 22])
        app = MinimalTestApp()
        song = create_test_song(app, text="x" * 500)
        for ch in chords:
            song._addChord(
                SongChord(song, ch.character_num, ch.note_id, ch.chord_type_id,
                          -1, "", 0))
        self.assertEqual(format_auto_detected_key_text(song._regions),
                         "Auto-detected key: Am, Bm")
        fsharp = [
            c for c in song.iterateAllChords()
            if c.note_id == 6 and c.character_num >= 220
        ][0]
        self.assertIn("F♯", fsharp.getChordText())

    def test_beliy_sneg_is_dm(self):
        """«Белый снег…»: Dm with A/A7 cadences, not Gm (iv) or F."""
        # Exact sequence from zvuki_neba song 222.
        seq = [
            (2, 1), (7, 1), (9, 0), (2, 1), (7, 1), (0, 0), (5, 0), (2, 1),
            (7, 1), (0, 0), (5, 0), (10, 0), (7, 1), (9, 0), (2, 1),
            (7, 1), (0, 0), (5, 0), (2, 1), (7, 1), (9, 0), (2, 1), (2, 0),
            (7, 1), (0, 0), (5, 0), (2, 1), (7, 1), (9, 0), (10, 0), (9, 4),
            (7, 4), (9, 5), (2, 1),
        ]
        chords = [_Root(i * 10, n, t) for i, (n, t) in enumerate(seq)]
        key = best_detected_key(chords)
        self.assertEqual(key.label, "Dm")
        self.assertEqual(key.prefer, PREFER_FLATS)
        self.assertEqual(detect_region_start_indices(chords), [0])
        app = MinimalTestApp()
        song = create_test_song(app, text="x" * 400)
        for ch in chords:
            song._addChord(
                SongChord(song, ch.character_num, ch.note_id, ch.chord_type_id,
                          -1, "", 0))
        self.assertEqual(format_auto_detected_key_text(song._regions),
                         "Auto-detected key: Dm")
        bb = [c for c in song.iterateAllChords() if c.note_id == 10][0]
        self.assertIn("B♭", bb.getChordText())
        self.assertNotIn("A♯", bb.getChordText())

    def test_bass_note_ignored_for_key(self):
        """Slash bass must not count as a chord root for key detection."""
        roots = [(2, 1), (7, 1), (9, 0), (2, 1)] * 3  # Dm Gm A Dm
        plain = [_Root(i * 10, n, t) for i, (n, t) in enumerate(roots)]
        with_bass = []
        for i, (n, t) in enumerate(roots):
            ch = _Root(i * 10, n, t)
            # Descending bass line unrelated to the tonic: /C /B /Bb /Ab
            ch.bass_note_id = [0, 11, 10, 8][i % 4]
            with_bass.append(ch)
        self.assertEqual(best_detected_key(plain).label, "Dm")
        self.assertEqual(best_detected_key(with_bass).label, "Dm")
        self.assertEqual(detect_region_start_indices(plain),
                         detect_region_start_indices(with_bass))

    def test_nagrady_slash_chords_single_region(self):
        """«Все награды…»: inversions (Dm/C, G/B, A/C♯) must not split the key.

        Verses mix C and Dm; a single region is enough. Dm is preferred if
        the detector can tell, but C is acceptable.
        """
        # Roots/types from zvuki_neba song 175 (bass stored separately).
        seq = [
            (7, 0), (2, 1), (2, 1), (7, 0), (0, 0),
            (2, 1), (2, 1), (7, 0), (0, 0),
            (4, 1), (4, 1), (9, 0), (2, 0),
            (7, 0), (0, 0), (9, 0), (0, 0),
            (2, 1), (2, 1), (7, 0), (0, 0),
            (2, 1), (2, 1), (7, 0), (0, 0),
            (4, 1), (4, 1), (9, 0), (2, 0),
            (7, 0), (0, 0), (9, 0), (0, 0),
            (9, 1), (4, 1), (7, 0), (2, 0),
            (9, 1), (4, 1), (0, 0),
            (9, 1), (4, 1), (7, 0), (2, 0), (0, 0),
            (4, 1), (9, 1), (2, 2), (2, 0), (0, 0),
            (4, 1), (9, 1), (2, 2), (2, 0),
            (4, 1), (9, 1), (2, 2), (2, 0),
        ]
        basses = {
            2: 0, 3: 11, 6: 0, 7: 11, 10: 2, 11: 1, 13: 11, 15: 1,
            18: 0, 19: 11, 22: 0, 23: 11, 26: 2, 27: 1, 29: 11, 31: 1,
        }
        chords = []
        for i, (n, t) in enumerate(seq):
            ch = _Root(i * 10, n, t)
            ch.bass_note_id = basses.get(i, -1)
            chords.append(ch)
        starts = detect_region_start_indices(chords)
        self.assertEqual(starts, [0])
        self.assertIn(best_detected_key(chords).label, ("Dm", "C"))

    def test_pivot_does_not_flatten_first_half(self):
        a_chords = _repeat_prog(self.A_PROG, 4, start_char=0)
        pivot = [_Root(190, 5, 0)]  # F
        bb_chords = _repeat_prog(self.BB_PROG, 4, start_char=200)
        chords = a_chords + pivot + bb_chords
        app = MinimalTestApp()
        song = create_test_song(app, text="x" * 400)
        for ch in chords:
            song._addChord(SongChord(song, ch.character_num, ch.note_id,
                                     ch.chord_type_id, -1, "", 0))
        first_fsharp = [
            c for c in song.iterateAllChords()
            if c.note_id == 6 and c.character_num < 190
        ][0]
        self.assertIn("F♯", first_fsharp.getChordText())

    def test_legacy_stored_key_does_not_affect_spelling(self):
        """Old songbooks may store Bb; A-major chords must still use sharps."""
        app = MinimalTestApp()
        app.curs.execute("DROP TABLE songs")
        app.curs.execute(
            "CREATE TABLE songs (id INTEGER PRIMARY KEY, number INTEGER, "
            "text TEXT, title TEXT, subtitle TEXT, key_note_id INTEGER, "
            "key_is_major INTEGER)"
        )
        app.curs.execute(
            "INSERT INTO songs (id, number, title, subtitle, text, "
            "key_note_id, key_is_major) VALUES (1, 1, 'x', '', ?, 10, 1)",
            ("x" * 80,),
        )
        app.curs.commit()
        song = Song(app, 1)
        self.assertFalse(hasattr(song, "key_note_id"))
        for i, (n, t) in enumerate(self.A_PROG * 3):
            song._addChord(SongChord(song, i * 4, n, t, -1, "", 0))
        fsharp = [c for c in song.iterateAllChords() if c.note_id == 6][0]
        self.assertIn("F♯", fsharp.getChordText())
        self.assertNotIn("G♭", fsharp.getChordText())


class TestKeyScoring(unittest.TestCase):
    """Unit tests for chord-to-key scoring (no GUI)."""

    def test_major_v_beats_minor_v_for_am_vs_dm(self):
        # Am and E major: harmonic V of Am, not of Dm.
        chords = [(9, 1), (4, 0)] * 4
        self.assertGreater(score_key(chords, 9, True), score_key(chords, 2, True))

    def test_v_i_cadence_outweighs_reverse(self):
        a_to_dm = [(9, 0), (2, 1)] * 3
        dm_to_a = [(2, 1), (9, 0)] * 3
        self.assertGreater(score_key(a_to_dm, 2, True),
                           score_key(dm_to_a, 2, True))

    def test_m7_counts_as_minor_tonic(self):
        am7 = [(9, 4)] * 4
        self.assertGreater(score_key(am7, 9, True), score_key(am7, 9, False))

    def test_family_score_relative_pair(self):
        chords = [(6, 1), (9, 0), (4, 0)] * 2  # F♯m A E → A family
        self.assertGreater(family_score(chords, 9), family_score(chords, 10))

    def test_auto_detected_key_labels_dedupes(self):
        regions = [(0, PREFER_SHARPS, "A"), (10, PREFER_SHARPS, "A"),
                   (20, PREFER_FLATS, "B♭")]
        self.assertEqual(auto_detected_key_labels(regions), ["A", "B♭"])
        self.assertEqual(format_auto_detected_key_text(regions),
                         "Auto-detected key: A, B♭")

    def test_empty_input(self):
        self.assertIsNone(best_detected_key([]))
        self.assertEqual(detect_region_start_indices([]), [])
        self.assertEqual(auto_detected_key_labels([]), [])
        self.assertEqual(format_auto_detected_key_text([]),
                         "Auto-detected key:")
        self.assertEqual(auto_detected_key_labels([(0, PREFER_SHARPS, "")]),
                         [])

    def test_prefer_from_major_tonic(self):
        self.assertEqual(prefer_from_major_tonic(0), PREFER_NEITHER)  # C
        self.assertEqual(prefer_from_major_tonic(7), PREFER_SHARPS)  # G
        self.assertEqual(prefer_from_major_tonic(5), PREFER_FLATS)  # F

    def test_key_label(self):
        self.assertEqual(key_label(9, False, PREFER_SHARPS), "A")
        self.assertEqual(key_label(9, True, PREFER_SHARPS), "Am")
        self.assertEqual(key_label(10, False, PREFER_FLATS), "B♭")
        self.assertEqual(key_label(10, False, PREFER_SHARPS), "A♯")


class TestTransposeNote(unittest.TestCase):
    """transpose_note wraps a chromatic note id into 0..11."""

    def test_up_and_down(self):
        self.assertEqual(transpose_note(0, 2), 2)  # C -> D
        self.assertEqual(transpose_note(2, -2), 0)

    def test_wraps_octave(self):
        self.assertEqual(transpose_note(11, 1), 0)  # B -> C
        self.assertEqual(transpose_note(0, -1), 11)  # C -> B
        self.assertEqual(transpose_note(0, 12), 0)
        self.assertEqual(transpose_note(0, -12), 0)


class TestReplaceRussianCharacters(unittest.TestCase):
    """Look-alike letters used when pasting chords from Russian sheets."""

    def test_cyrillic_and_european_h(self):
        self.assertEqual(replace_russian_characeters("Е"), "E")
        self.assertEqual(replace_russian_characeters("С"), "C")
        self.assertEqual(replace_russian_characeters("В"), "B")
        self.assertEqual(replace_russian_characeters("А"), "A")
        self.assertEqual(replace_russian_characeters("H"), "B")
        self.assertEqual(replace_russian_characeters("Н"), "B")

    def test_leaves_ascii_notes_alone(self):
        self.assertEqual(replace_russian_characeters("Am"), "Am")
        self.assertEqual(replace_russian_characeters("C#"), "C#")


class _ChordParseApp:
    """Duck-typed stand-in with the dicts convertChordFromString reads."""

    def __init__(self):
        self.note_text_id_dict = {}
        for note_id, text, alt_text in softchord.global_notes_list:
            self.note_text_id_dict[text] = note_id
            self.note_text_id_dict[alt_text] = note_id
        self.chord_type_texts_dict = {}
        for type_id, (_i, _name, print_text) in enumerate(
                softchord.chord_types_list):
            self.chord_type_texts_dict[print_text] = type_id
            for alt, official in softchord.alternative_type_names.items():
                if print_text == official:
                    self.chord_type_texts_dict[alt] = type_id


class TestConvertChordFromString(unittest.TestCase):
    """Parse pasted chord tokens into (marker, note, type, bass, parens)."""

    def setUp(self):
        self.parser = _ChordParseApp()

    def convert(self, text):
        return softchord.App.convertChordFromString(self.parser, text)

    def test_major_minor_and_seventh(self):
        self.assertEqual(self.convert("C"), (None, 0, 0, -1, False))
        self.assertEqual(self.convert("Am"), (None, 9, 1, -1, False))
        self.assertEqual(self.convert("G7"), (None, 7, 5, -1, False))

    def test_accidentals_and_aliases(self):
        self.assertEqual(self.convert("F#m"), self.convert("F♯m"))
        self.assertEqual(self.convert("Bb"), self.convert("B♭"))
        self.assertEqual(self.convert("F#m"), (None, 6, 1, -1, False))
        self.assertEqual(self.convert("Csus"), self.convert("Csus4"))
        self.assertEqual(self.convert("Cmaj7"), (None, 0, 3, -1, False))

    def test_bass_marker_and_parentheses(self):
        self.assertEqual(self.convert("C/E"), (None, 0, 0, 4, False))
        self.assertEqual(self.convert("1:C"), ("1", 0, 0, -1, False))
        self.assertEqual(self.convert("(Am)"), (None, 9, 1, -1, True))
        self.assertEqual(self.convert("(1:G7/B)"), ("1", 7, 5, 11, True))

    def test_russian_lookalikes(self):
        self.assertEqual(self.convert("Нm"), (None, 11, 1, -1, False))  # Bm
        self.assertEqual(self.convert("С"), (None, 0, 0, -1, False))  # C

    def test_invalid_chords_raise_value_error(self):
        for text, fragment in (
            ("", "Empty string"),
            ("X", "First chord letter is not a note"),
            ("C:", "nothing after a colon"),
            ("/E", "before the bass slash"),
            ("C/", "after the bass slash"),
            ("Cxyz", "Unkown chord type"),
            ("C/Z", "Unrecognized bass note string"),
        ):
            with self.subTest(text=text):
                with self.assertRaises(ValueError) as ctx:
                    self.convert(text)
                self.assertIn(fragment, str(ctx.exception))


class TestSongbookKeySchema(unittest.TestCase):
    """New songbooks omit key columns; old files still open."""

    @classmethod
    def setUpClass(cls):
        if not QtWidgets.QApplication.instance():
            cls.qapp = QtWidgets.QApplication([])
        else:
            cls.qapp = QtWidgets.QApplication.instance()

    def test_new_schema_has_no_key_columns(self):
        conn = sqlite3.connect(":memory:")
        conn.execute(SONGS_TABLE_SQL)
        names = [row[1] for row in conn.execute("PRAGMA table_info(songs)")]
        self.assertNotIn("key_note_id", names)
        self.assertNotIn("key_is_major", names)

    def test_save_leaves_legacy_key_columns_untouched(self):
        app = MinimalTestApp()
        app.curs.execute("DROP TABLE songs")
        app.curs.execute(
            "CREATE TABLE songs (id INTEGER PRIMARY KEY, number INTEGER, "
            "text TEXT, title TEXT, subtitle TEXT, key_note_id INTEGER, "
            "key_is_major INTEGER)"
        )
        app.curs.execute(
            "INSERT INTO songs (id, number, title, subtitle, text, "
            "key_note_id, key_is_major) VALUES (1, 7, 'Old', 'note', 'hi', 10, 1)"
        )
        app.curs.commit()
        song = Song(app, 1)
        self.assertEqual(song.title, "Old")
        app.curs.execute(
            "UPDATE songs SET number=?, title=?, subtitle=?, text=? WHERE id=?",
            (song.number, song.title, song.subtitle, song.getAllText(), song.id),
        )
        app.curs.commit()
        stored = app.curs.execute(
            "SELECT key_note_id, key_is_major FROM songs WHERE id=1"
        ).fetchone()
        self.assertEqual(stored, (10, 1))

    def test_import_into_new_schema_does_not_require_key_columns(self):
        app = MinimalTestApp()
        song_id = app.curs.execute("SELECT MAX(id) FROM songs").fetchone()[0]
        self.assertIsNone(song_id)
        app.curs.execute(
            "INSERT INTO songs (id, number, title, subtitle, text) "
            "VALUES (0, -1, '', '', '')"
        )
        app.curs.commit()
        names = [row[1] for row in app.curs.execute("PRAGMA table_info(songs)")]
        self.assertNotIn("key_note_id", names)


class TestSongsContextMenu(unittest.TestCase):
    """Right-click Delete on the songs table."""

    @classmethod
    def setUpClass(cls):
        # One App for the class. App is a QApplication, and constructing
        # another per test crashes the interpreter at shutdown.
        cls.app = softchord.App([])
        cls._td = tempfile.TemporaryDirectory()
        path = os.path.join(cls._td.name, "songs.songbook")
        conn = sqlite3.connect(path)
        conn.execute(SONG_CHORD_LINK_TABLE_SQL)
        conn.execute(SONGS_TABLE_SQL)
        conn.commit()
        conn.close()
        cls.app.setCurrentSongbook(path)

    @classmethod
    def tearDownClass(cls):
        cls.app.closeSongbook()
        cls.app.win.close()
        cls._td.cleanup()

    def setUp(self):
        self.questions = []
        self.question_buttons = []
        self.accept_delete = True

        def question(msg,
                     button1="OK",
                     button2="Cancel",
                     title="softChord - Question"):
            self.questions.append(msg)
            self.question_buttons.append(button1)
            return self.accept_delete

        self.app.question = question
        self.app.clearUndoStack()
        self.app.ui.songs_view.clearSelection()
        self.app.curs.execute("DELETE FROM song_chord_link")
        self.app.curs.execute("DELETE FROM songs")
        for number, title in ((1, "One"), (2, "Two"), (3, "Three")):
            self.app.curs.execute(
                "INSERT INTO songs (id, number, title, subtitle, text) "
                "VALUES (?, ?, ?, '', '')", (number, number, title))
        self.app.curs.commit()
        self.app.songs_model.updateFromDatabase()
        self.app.ui.songs_view.clearSelection()

    def _proxy_index(self, song_number):
        model = self.app.songs_model
        for row in range(model.rowCount()):
            if model.getRow(row).number == song_number:
                source = model.index(row, 0)
                return self.app.songs_proxy_model.mapFromSource(source)
        self.fail("missing song %s" % song_number)

    def _select_numbers(self, numbers):
        selection = self.app.ui.songs_view.selectionModel()
        selection.clearSelection()
        flags = (QtCore.QItemSelectionModel.SelectionFlag.Select
                 | QtCore.QItemSelectionModel.SelectionFlag.Rows)
        for number in numbers:
            selection.select(self._proxy_index(number), flags)

    def _song_ids(self):
        return set(self.app.songs_model.getAllSongIds())

    def test_context_menu_policy_is_custom(self):
        self.assertEqual(self.app.ui.songs_view.contextMenuPolicy(),
                         Qt.ContextMenuPolicy.CustomContextMenu)

    def test_no_selection_selects_clicked_song_and_deletes_without_confirm(self):
        menu = self.app.buildSongsContextMenu(self._proxy_index(2))
        self.assertEqual([action.text() for action in menu.actions()],
                         ["Delete"])
        self.assertEqual(self.app.getSelectedSongIds(), [2])

        self.accept_delete = False
        self.app.deleteSongsFromContextMenu()
        self.assertEqual(self.questions, [])
        self.assertEqual(self._song_ids(), {1, 3})

    def test_one_selected_song_deletes_without_confirm(self):
        self._select_numbers([1])
        menu = self.app.buildSongsContextMenu(self._proxy_index(1))
        self.assertEqual(menu.actions()[0].text(), "Delete")
        self.assertEqual(self.app.getSelectedSongIds(), [1])

        self.app.deleteSongsFromContextMenu()
        self.assertEqual(self.questions, [])
        self.assertEqual(self._song_ids(), {2, 3})

    def test_right_click_outside_selection_selects_that_song(self):
        self._select_numbers([1, 2])
        menu = self.app.buildSongsContextMenu(self._proxy_index(3))
        self.assertEqual(menu.actions()[0].text(), "Delete")
        self.assertEqual(self.app.getSelectedSongIds(), [3])

    def test_multiple_songs_confirm_then_delete(self):
        self._select_numbers([1, 3])
        menu = self.app.buildSongsContextMenu(self._proxy_index(1))
        self.assertEqual(menu.actions()[0].text(), "Delete...")
        self.assertEqual(set(self.app.getSelectedSongIds()), {1, 3})

        self.app.deleteSongsFromContextMenu()
        self.assertEqual(self.questions, ["Delete 2 songs?"])
        self.assertEqual(self.question_buttons, ["Delete"])
        self.assertEqual(self._song_ids(), {2})

    def test_multiple_songs_cancel_keeps_them(self):
        self._select_numbers([1, 2, 3])
        menu = self.app.buildSongsContextMenu(self._proxy_index(2))
        self.assertEqual(menu.actions()[0].text(), "Delete...")

        self.accept_delete = False
        self.app.deleteSongsFromContextMenu()
        self.assertEqual(self.questions, ["Delete 3 songs?"])
        self.assertEqual(self.question_buttons, ["Delete"])
        self.assertEqual(self._song_ids(), {1, 2, 3})

    def test_invalid_index_has_no_menu(self):
        self.assertIsNone(self.app.buildSongsContextMenu(QtCore.QModelIndex()))

    def test_context_menu_event_deletes_clicked_song(self):
        view = self.app.ui.songs_view
        self.app.win.resize(1000, 700)
        QtWidgets.QApplication.processEvents()
        index = self._proxy_index(2)
        rect = view.visualRect(index)
        self.assertFalse(rect.isEmpty())

        def fake_exec(menu, *args, **kwargs):
            fake_exec.labels = [action.text() for action in menu.actions()]
            return menu.actions()[0]

        orig_exec = QtWidgets.QMenu.exec
        QtWidgets.QMenu.exec = fake_exec
        try:
            global_pos = view.viewport().mapToGlobal(rect.center())
            event = QtGui.QContextMenuEvent(
                QtGui.QContextMenuEvent.Reason.Mouse, rect.center(),
                global_pos)
            QtWidgets.QApplication.sendEvent(view.viewport(), event)
        finally:
            QtWidgets.QMenu.exec = orig_exec

        self.assertEqual(fake_exec.labels, ["Delete"])
        self.assertEqual(self.questions, [])
        self.assertEqual(self._song_ids(), {1, 3})


class TestEditorModeMenu(unittest.TestCase):
    """Edit menu check marks stay in sync with the editor mode buttons."""

    @classmethod
    def setUpClass(cls):
        cls.app = softchord.App([])

    @classmethod
    def tearDownClass(cls):
        cls.app.win.close()

    def test_chord_mode_is_checked_at_startup(self):
        self.app.chordEditorSelected()
        self.assertTrue(self.app.ui.actionChordEditorMode.isCheckable())
        self.assertTrue(self.app.ui.actionLyricEditorMode.isCheckable())
        self.assertTrue(self.app.ui.actionChordEditorMode.isChecked())
        self.assertFalse(self.app.ui.actionLyricEditorMode.isChecked())
        self.assertTrue(self.app.ui.chord_editor_button.isDown())
        self.assertFalse(self.app.ui.lyric_editor_button.isDown())
        self.assertFalse(self.app.editor.lyric_editor_mode)

    def test_menu_and_buttons_follow_the_active_mode(self):
        self.app.ui.actionLyricEditorMode.trigger()
        self.assertTrue(self.app.ui.actionLyricEditorMode.isChecked())
        self.assertFalse(self.app.ui.actionChordEditorMode.isChecked())
        self.assertTrue(self.app.ui.lyric_editor_button.isDown())
        self.assertFalse(self.app.ui.chord_editor_button.isDown())
        self.assertTrue(self.app.editor.lyric_editor_mode)

        self.app.ui.chord_editor_button.click()
        self.assertTrue(self.app.ui.actionChordEditorMode.isChecked())
        self.assertFalse(self.app.ui.actionLyricEditorMode.isChecked())
        self.assertTrue(self.app.ui.chord_editor_button.isDown())
        self.assertFalse(self.app.ui.lyric_editor_button.isDown())
        self.assertFalse(self.app.editor.lyric_editor_mode)

        self.app.ui.lyric_editor_button.click()
        self.assertTrue(self.app.ui.actionLyricEditorMode.isChecked())
        self.assertFalse(self.app.ui.actionChordEditorMode.isChecked())
        self.assertTrue(self.app.editor.lyric_editor_mode)

        self.app.ui.actionChordEditorMode.trigger()
        self.assertTrue(self.app.ui.actionChordEditorMode.isChecked())
        self.assertTrue(self.app.ui.chord_editor_button.isDown())
        self.assertFalse(self.app.editor.lyric_editor_mode)


# Chord-sheet round trips.
#
# Each example is text you paste (monospaced or proportional) and the
# monospaced text Copy Song Text (with chords) should produce. Chord names
# may sit one column to either side of the sample. To add an example, append
# another ("name", source, expected) entry. Keep the song text flush left
# inside the quotes so the spaces stay exact.

KOSARI_TEXT = """\
                     Cm                                     Fm
Косари на лугу размахалися острыми косами,
                             Cm                      G                               Cm
Что им Божий цветок, им бы закончить работу свою.
                                Fm                                           Cm
Я на милость Твою уповаю, Спаситель мой, Господи,
                          G                                                             Cm
На милость, на милость, лишь только на милость Твою.
"""

KOSARI_MONOSPACED = """\
            Cm                     Fm
Косари на лугу размахалися острыми косами,
                Cm             G              Cm
Что им Божий цветок, им бы закончить работу свою.
                  Fm                        Cm
Я на милость Твою уповаю, Спаситель мой, Господи,
               G                                 Cm
На милость, на милость, лишь только на милость Твою.
"""

ZHATVA_TEXT = """\
     E
1. “Жатва есть кончина века” – 
B                                    E
  Так Господь сказал.
/
  И всегда у человека 
B                                    E
  В жизни есть финал.
                A                      B
Пр: Небо для меня открыто,
G#m               C#m
Я  навек спасен.
A                E
Иисус моя защита,
B                        E
Я Им утвержден.
(2 раза)
"""

ZHATVA_MONOSPACED = """\
   E
1. “Жатва есть кончина века” –
  B                E
  Так Господь сказал.
  И всегда у человека 
  B                E
  В жизни есть финал.
         A            B
Пр: Небо для меня открыто,
  G♯m       C♯m
Я  навек спасен.
A         E
Иисус моя защита,
B            E
Я Им утвержден.
(2 раза)
"""

# name, pasted text, monospaced copy-with-chords text
CHORD_SHEET_ROUND_TRIPS = [
    ("kosari", KOSARI_TEXT, KOSARI_MONOSPACED),
    ("zhatva", ZHATVA_TEXT, ZHATVA_MONOSPACED),
]


def _sheet_lines(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if text.endswith("\n"):
        text = text[:-1]
    return text.split("\n")


def _line_tokens(line):
    tokens = []
    current = ""
    start = None
    for index, char in enumerate(line.rstrip()):
        if char.isspace():
            if current:
                tokens.append((current, start))
                current = ""
                start = None
        else:
            if start is None:
                start = index
            current += char
    if current:
        tokens.append((current, start))
    return tokens


def _is_chord_name(text):
    if not text or text[0] not in "ABCDEFG":
        return False
    rest = text[1:]
    if rest[:1] in "#b♯♭":
        rest = rest[1:]
    return rest == "" or rest.isalnum()


def _is_chord_line(line):
    tokens = _line_tokens(line)
    return bool(tokens) and all(_is_chord_name(name) for name, _start in tokens)


def _word_at(text, index):
    start = index
    while start > 0 and not text[start - 1].isspace():
        start -= 1
    end = index + 1
    while end < len(text) and not text[end].isspace():
        end += 1
    return text[start:end]


class TestChordOverLyricPlacement(unittest.TestCase):
    """Chord-over-lyric paste maps chords onto letters without padding."""

    @classmethod
    def setUpClass(cls):
        cls.app = softchord.App([])
        cls._td = tempfile.TemporaryDirectory()
        path = os.path.join(cls._td.name, "songs.songbook")
        conn = sqlite3.connect(path)
        conn.execute(SONG_CHORD_LINK_TABLE_SQL)
        conn.execute(SONGS_TABLE_SQL)
        conn.commit()
        conn.close()
        cls.app.setCurrentSongbook(path)

    @classmethod
    def tearDownClass(cls):
        cls.app.closeSongbook()
        cls.app.win.close()
        cls._td.cleanup()

    def setUp(self):
        self.app.ui.songs_view.clearSelection()
        self.app.clearUndoStack()
        self.app.curs.execute("DELETE FROM song_chord_link")
        self.app.curs.execute("DELETE FROM songs")
        self.app.curs.commit()
        self.app.songs_model.updateFromDatabase()

    def _parse(self, text):
        # Same trailing-newline handling as importSongFromText.
        lines = text.split("\n")
        if lines and lines[-1] == "":
            lines.pop(-1)
        return softchord.parse_chord_over_lyrics(
            lines, self.app.convertChordFromString,
            self.app.lyrics_font_metrics)

    def test_song_is_held_by_the_session(self):
        song = create_test_song(self.app, song_id=1, text="Hello")
        self.assertIs(song.session, self.app.session)
        self.assertNotIsInstance(song.session, QtWidgets.QApplication)
        self.assertIs(self.app.editor.app, self.app.session)

    def test_kosari_is_proportional_and_chords_sit_on_words(self):
        lines, proportional = self._parse(KOSARI_TEXT)
        self.assertTrue(proportional)
        lyrics = [lyric for lyric, _chords in lines]
        self.assertEqual(lyrics, [
            "Косари на лугу размахалися острыми косами,",
            "Что им Божий цветок, им бы закончить работу свою.",
            "Я на милость Твою уповаю, Спаситель мой, Господи,",
            "На милость, на милость, лишь только на милость Твою.",
        ])
        for lyric, chords in lines:
            for index in chords:
                self.assertFalse(lyric[index].isspace())
                self.assertGreaterEqual(index, 0)
                self.assertLess(index, len(lyric))

        words = [[_word_at(lyric, index) for index in sorted(chords)]
                 for lyric, chords in lines]
        self.assertEqual(words[0], ["лугу", "косами,"])
        self.assertEqual(words[1], ["цветок,", "закончить", "свою."])
        self.assertEqual(words[2], ["уповаю,", "Господи,"])
        self.assertEqual(words[3][1], "Твою.")
        second_milost = lyrics[3].find("милость", lyrics[3].find("милость") + 1)
        g_index = sorted(lines[3][1])[0]
        self.assertTrue(second_milost <= g_index < second_milost + len("милость"))

    def test_monospaced_sheet_uses_chord_start_column(self):
        text = "Cm        G\nКосари на лугу"
        lines, proportional = self._parse(text)
        self.assertFalse(proportional)
        lyric, chords = lines[0]
        self.assertEqual(lyric, "Косари на лугу")
        # "Cm" starts on column 0 ("К"); "G" starts on column 10 ("л").
        self.assertEqual(sorted(chords), [0, 10])
        self.assertEqual(lyric[0], "К")
        self.assertEqual(lyric[10], "л")

    def test_long_monospaced_chord_line_is_not_padded(self):
        # Character length is much greater, but the spaces are not a
        # proportional visual alignment (the chord line is wider, not similar).
        text = "C" + (" " * 20) + "G\nHello"
        lines, proportional = self._parse(text)
        self.assertFalse(proportional)
        lyric, chords = lines[0]
        self.assertEqual(lyric, "Hello")
        self.assertNotIn(" ", lyric)
        indexes = sorted(chords)
        self.assertEqual(lyric[indexes[0]], "H")
        self.assertEqual(lyric[indexes[1]], "o")

    def test_trailing_chord_line_is_kept(self):
        text = "C  G\nHello\nAm"
        lines, _proportional = self._parse(text)
        self.assertEqual(len(lines), 2)
        hello, hello_chords = lines[0]
        self.assertEqual(hello, "Hello")
        self.assertEqual(len(hello_chords), 2)
        last_lyric, last_chords = lines[1]
        self.assertIn("Am", last_lyric)
        self.assertEqual(len(last_chords), 1)
        note_id = list(last_chords.values())[0][1]
        self.assertEqual(note_id, 9)  # A

    def test_two_chords_do_not_share_a_letter(self):
        placed = softchord.assign_chord_anchors(
            "CD", "AB", [(0, 0, "C"), (0, 0, "D")],
            self.app.lyrics_font_metrics, False)
        self.assertEqual([index for index, _payload in placed], [0, 1])

    def test_import_keeps_lyric_text_and_positions(self):
        self.app.importSongFromText(KOSARI_TEXT, "Kosari")
        song = self.app.current_song
        lines, _proportional = self._parse(KOSARI_TEXT)
        expected_text = "".join(lyric + "\n" for lyric, _chords in lines)
        self.assertEqual(song.getAllText(), expected_text)
        self.assertFalse(any(line.endswith(" ") for line in expected_text.split("\n")))

        expected = {}
        offset = 0
        for lyric, chords in lines:
            for index, chord in chords.items():
                _marker, note_id, type_id, _bass, _paren = chord
                expected[offset + index] = (note_id, type_id)
            offset += len(lyric) + 1
        actual = {
            chord.character_num: (chord.note_id, chord.chord_type_id)
            for chord in song.iterateAllChords()
        }
        self.assertEqual(actual, expected)

    def test_round_trip_examples_match_monospaced_copy(self):
        """Paste each example and compare Copy Song Text (with chords).

        Chord columns may differ by one character. Edit the source and
        expected strings above to change or add an example.
        """
        for name, source, expected in CHORD_SHEET_ROUND_TRIPS:
            with self.subTest(name=name):
                self.app.importSongFromText(source, name)
                self.app.copySongTextWithChords()
                self._assert_monospaced_similar(
                    self.app.clipboard.text(), expected, name)

    def _assert_monospaced_similar(self, got, expected, name):
        got_lines = _sheet_lines(got)
        expected_lines = _sheet_lines(expected)
        self.assertEqual(
            len(got_lines), len(expected_lines),
            "%s: line count\n got %r\n expected %r" %
            (name, got_lines, expected_lines))
        for line_num, (got_line, expected_line) in enumerate(
                zip(got_lines, expected_lines)):
            where = "%s line %d" % (name, line_num + 1)
            if _is_chord_line(got_line) or _is_chord_line(expected_line):
                self.assertTrue(
                    _is_chord_line(got_line) and _is_chord_line(expected_line),
                    "%s: chord line mismatch\n got %r\n expected %r" %
                    (where, got_line, expected_line))
                got_tokens = _line_tokens(got_line)
                expected_tokens = _line_tokens(expected_line)
                self.assertEqual(
                    [token for token, _start in got_tokens],
                    [token for token, _start in expected_tokens],
                    "%s chords\n got %r\n expected %r" %
                    (where, got_line, expected_line))
                for (got_name, got_col), (expected_name, expected_col) in zip(
                        got_tokens, expected_tokens):
                    self.assertLessEqual(
                        abs(got_col - expected_col), 1,
                        "%s chord %s is in column %d, expected %d (±1)\n"
                        " got %r\n expected %r" %
                        (where, got_name, got_col, expected_col, got_line,
                         expected_line))
            else:
                self.assertEqual(
                    got_line.rstrip(), expected_line.rstrip(),
                    "%s lyrics\n got %r\n expected %r" %
                    (where, got_line, expected_line))


if __name__ == "__main__":
    unittest.main(verbosity=2)
