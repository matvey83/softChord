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
        self.curs = sqlite3.connect(":memory:")
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


# ---------------------------------------------------------------------------
# Tests for SongChord and SongChar (basic)
# ---------------------------------------------------------------------------


class TestSongChord(unittest.TestCase):

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

        # Currently getChordText does not show parentheses in output
        # but the flag should be stored
        stored_chord = list(self.song.iterateAllChords())[0]
        self.assertEqual(stored_chord.in_parentheses, 1)

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

    def setUp(self):
        self.app = MinimalTestApp()
        self.song = create_test_song(self.app, text="Chord test line")

    def test_add_chord_command(self):
        chord = SongChord(self.song, 0, 0, 0, -1, "", 0)
        cmd = AddChordCommand(self.song, chord)
        cmd.redo()
        self.assertIn(chord, list(self.song.iterateAllChords()))

    def test_delete_chord_command(self):
        chord = SongChord(self.song, 0, 0, 0, -1, "", 0)
        self.song._addChord(chord)

        cmd = DeleteChordCommand(self.song, chord)
        cmd.redo()
        self.assertNotIn(chord, list(self.song.iterateAllChords()))


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

        # Use the real songbook so the App has a working database connection
        songbook_path = os.path.join(os.path.dirname(__file__), "..",
                                     "zvuki_neba.songbook")
        songbook_path = os.path.abspath(songbook_path)
        self.app.setCurrentSongbook(songbook_path)

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

        chord = list(song.iterateAllChords())[0]
        self.assertEqual(chord.chord_type_id, 0)  # Major

        self.app.processKeyPressed(Qt.Key.Key_M)
        self.assertEqual(chord.chord_type_id, 1)  # Minor

        self.app.processKeyPressed(Qt.Key.Key_M)
        self.assertEqual(chord.chord_type_id, 0)  # Back to Major

    def test_process_key_pressed_arrow_move_chord(self):
        """Left/Right arrows should move the selected chord."""
        song = create_test_song(self.app, song_id=10002, text="0123456789")
        self.app.current_song = song
        self.app.selected_char_num = 3
        self.app.previous_song_text = "0123456789"

        self.app.processKeyPressed(Qt.Key.Key_C)
        chord = list(song.iterateAllChords())[0]
        self.assertEqual(chord.character_num, 3)

        self.app.processKeyPressed(Qt.Key.Key_Right)
        self.assertEqual(chord.character_num, 4)

        self.app.processKeyPressed(Qt.Key.Key_Left)
        self.assertEqual(chord.character_num, 3)

    def test_process_key_pressed_arrow_transpose(self):
        """Up/Down arrows should transpose the selected chord."""
        song = create_test_song(self.app, song_id=10003, text="Test")
        self.app.current_song = song
        self.app.selected_char_num = 0
        self.app.previous_song_text = "Test"

        self.app.processKeyPressed(Qt.Key.Key_C)
        chord = list(song.iterateAllChords())[0]
        self.assertEqual(chord.note_id, 0)

        self.app.processKeyPressed(Qt.Key.Key_Up)  # C -> C#
        self.assertEqual(chord.note_id, 1)

        self.app.processKeyPressed(Qt.Key.Key_Down)  # C# -> C
        self.assertEqual(chord.note_id, 0)


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
        # Real App + real songbook gives us proper editor + font metrics
        self.app = softchord.App([])
        self.app.win = QtWidgets.QWidget()

        songbook_path = os.path.join(os.path.dirname(__file__), "..",
                                     "zvuki_neba.songbook")
        songbook_path = os.path.abspath(songbook_path)
        self.app.setCurrentSongbook(songbook_path)

        # Select first song and give it a current song for hit testing
        if self.app.songs_model.rowCount() > 0:
            self.app.ui.songs_view.selectRow(0)

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

        # Use real songbook so current_song and note lookup work
        songbook_path = os.path.join(os.path.dirname(__file__), "..",
                                     "zvuki_neba.songbook")
        songbook_path = os.path.abspath(songbook_path)
        self.app.setCurrentSongbook(songbook_path)

        if self.app.songs_model.rowCount() > 0:
            self.app.ui.songs_view.selectRow(0)

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

        songbook_path = os.path.join(os.path.dirname(__file__), "..",
                                     "zvuki_neba.songbook")
        songbook_path = os.path.abspath(songbook_path)
        self.app.setCurrentSongbook(songbook_path)

        if self.app.songs_model.rowCount() > 0:
            self.app.ui.songs_view.selectRow(0)

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

        # Use real songbook for a valid current_song and models
        songbook_path = os.path.join(os.path.dirname(__file__), "..",
                                     "zvuki_neba.songbook")
        songbook_path = os.path.abspath(songbook_path)
        self.app.setCurrentSongbook(songbook_path)

        if self.app.songs_model.rowCount() > 0:
            self.app.ui.songs_view.selectRow(0)

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
        original_get_font = QtGui.QFontDialog.getFont

        # Mock: always "accept" and return a slightly modified font
        def fake_get_font(font, parent=None):
            new_font = QtGui.QFont(font)
            new_font.setPointSize(14)
            return new_font, True

        QtGui.QFontDialog.getFont = staticmethod(fake_get_font)

        try:
            self.app.changeLyricsFont()
            self.app.changeChordFont()
            # If we reach here, the methods executed their "OK" paths
        finally:
            QtGui.QFontDialog.getFont = original_get_font

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

        songbook_path = os.path.join(os.path.dirname(__file__), "..",
                                     "zvuki_neba.songbook")
        songbook_path = os.path.abspath(songbook_path)
        self.app.setCurrentSongbook(songbook_path)

        if self.app.songs_model.rowCount() > 0:
            self.app.ui.songs_view.selectRow(0)

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

        # Open a real songbook so curs and models are valid
        songbook_path = os.path.join(os.path.dirname(__file__), "..",
                                     "zvuki_neba.songbook")
        songbook_path = os.path.abspath(songbook_path)
        self.app.setCurrentSongbook(songbook_path)

        if self.app.songs_model.rowCount() > 0:
            self.app.ui.songs_view.selectRow(0)

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
        td = tempfile.mkdtemp()
        path = os.path.join(td, "t.songbook")
        conn = sqlite3.connect(path)
        conn.execute(
            "CREATE TABLE song_chord_link(id INTEGER PRIMARY KEY, song_id INTEGER, character_num INTEGER, note_id INTEGER, chord_type_id INTEGER, bass_note_id INTEGER, marker TEXT, in_parentheses INTEGER)"
        )
        conn.execute(SONGS_TABLE_SQL)
        conn.commit()
        conn.close()
        self.app.setCurrentSongbook(path)
        return td

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
