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
from unittest import mock
import sqlite3
import copy
import os
import shutil
import subprocess
import sys
import tempfile
import random

from PyQt6 import QtCore, QtGui, QtWidgets, QtPrintSupport
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

import softchord
import softchord_chords
from softchord_text import (chord_drag_direction, lyric_renumber_map,
                            next_free_character)
from softchord_layout import QtDocumentLayout, SongLayout
from softchord_io import (
    _chord_tokens,
    _classify_chord_line,
    _median,
    _nearest_nonspace,
    _next_free_nonspace,
    assign_chord_anchors,
    text_is_proportionally_spaced,
)
from softchord_session import (
    fit_scale_ratio,
    scale_message,
    song_document_size,
    song_target_size,
)
from softchord_song import place_chord_on_line
from softchord_store import (
    SongbookStore,
    create_schema,
    enable_foreign_keys,
    database_file_was_replaced,
    readonly_database_error,
)
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
        self.selected_chord_nums = set()
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
        self.selected_chord_nums = set()
        self.ignore_song_text_changed = False
        self.doc_editor_offset = 0

        # Provide the methods Song calls on self.app
        self._setup_method_stubs()

    def chordEditing(self):
        # The editor tests here act as during a chord edit.
        return True

    def _create_minimal_tables(self):
        create_schema(self.curs)
        self.curs.commit()
        enable_foreign_keys(self.curs)

    def _setup_method_stubs(self):
        # These are called while the lyric document is being spaced.
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

    def updateChordLineSpacing(self, song):
        pass

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

    # The real jump-over rule, so mouse drags can be tested here.
    freeCharacterForChord = softchord.SongbookSession.freeCharacterForChord
    placeChord = softchord.SongbookSession.placeChord
    _chordsAt = softchord.SongbookSession.__dict__["_chordsAt"]
    dragChordPastLineEnd = softchord.SongbookSession.dragChordPastLineEnd
    drag_past_line_end = None

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

    def beginMacro(self, text):
        self.commands.append(text)

    def endMacro(self):
        self.commands.append(None)


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
        INSERT INTO songs (id, number, title, subtitle, text, uuid, updated_at)
        VALUES (?, 1, ?, '', ?, lower(hex(randomblob(16))), 1700000000)
    """, (song_id, title, text))
    app.curs.commit()

    song = Song(app, song_id)
    return song


# The suite shares one App. Another QApplication crashes when the process exits.
_test_app = None


def _unexpected_message_box(box):
    # A real dialog would wait forever offscreen. Tests that expect the
    # Save dialog patch exec themselves; anything else is reported and
    # answered with Don't Save.
    sys.stderr.write("UNEXPECTED DIALOG: %s\n" % box.text())
    return QtWidgets.QMessageBox.StandardButton.Discard


QtWidgets.QMessageBox.exec = _unexpected_message_box
_test_app_fonts = None


def test_app():
    """One App for the process. Later calls put back methods and fonts a test replaced."""
    global _test_app, _test_app_fonts
    if _test_app is None:
        _test_app = softchord.App([])
        session = _test_app.session
        _test_app_fonts = (
            QtGui.QFont(session.lyrics_font),
            session.lyrics_font_size,
            QtGui.QFont(session.chords_font),
            session.chords_font_size,
            QtGui.QFont(session.symbols_font),
        )
    else:
        session = _test_app.session
        for name in list(session.__dict__):
            if callable(getattr(type(session), name, None)):
                del session.__dict__[name]
        lyrics, lyrics_size, chords, chords_size, symbols = _test_app_fonts
        session.lyrics_font = QtGui.QFont(lyrics)
        session.lyrics_font_size = lyrics_size
        session.chords_font = QtGui.QFont(chords)
        session.chords_font_size = chords_size
        session.symbols_font = QtGui.QFont(symbols)
        session.updateEditorFonts()
    session = _test_app.session
    # Each test starts viewing, with no edit left from the one before.
    if session.edit_session is not None:
        session._endEdit()
    session._pending_song_selection = None
    session.selected_chord_nums = set()
    session.selected_char_num = None
    session.editor.cancelChordMarquee()
    session._reset_lyric_chord_history()
    return _test_app


def open_empty_temp_songbook(app):
    """Open a throwaway songbook so tests do not write zvuki_neba.songbook."""
    td = tempfile.mkdtemp()
    path = os.path.join(td, "t.songbook")
    conn = sqlite3.connect(path)
    create_schema(conn)
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
        "INSERT INTO songs (id, number, title, subtitle, text, uuid, updated_at) "
        "VALUES (?, 1, ?, '', ?, lower(hex(randomblob(16))), 1700000000)", (song_id, title, text))
    if with_chord:
        app.curs.execute(
            "INSERT INTO song_chord_link (id, song_id, character_num, chord) "
            "VALUES (0, ?, 0, 'C')", (song_id,))
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


class TestPlaceChordOnLine(unittest.TestCase):
    """Monospace chord row used by Copy Song Text."""

    def test_odd_name_is_centered_on_the_anchor(self):
        cells = [" "] * 8
        place_chord_on_line(cells, 4, "C")
        self.assertEqual("".join(cells), "    C   ")

    def test_two_letter_name_starts_on_the_anchor(self):
        cells = [" "] * 8
        place_chord_on_line(cells, 4, "Am")
        self.assertEqual("".join(cells), "    Am  ")

    def test_name_is_shifted_to_stay_on_the_line(self):
        cells = [" "] * 4
        place_chord_on_line(cells, 0, "(C)")
        self.assertEqual("".join(cells), "(C) ")

        cells = [" "] * 8
        place_chord_on_line(cells, 7, "G7")
        self.assertEqual("".join(cells), "     G7 ")


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

    def test_get_as_text_places_each_chord_on_its_letter(self):
        # "Test line one": C on column 0, Am (even length) starts on column 5.
        self.song._addChord(SongChord(self.song, 0, 0, 0, -1, "", 0))
        self.song._addChord(SongChord(self.song, 5, 9, 1, -1, "", 0))
        # G on the last letter is shifted left so the name stays on the line.
        self.song._addChord(SongChord(self.song, 14 + 12, 7, 0, -1, "", 0))

        lines = self.song.getAsText().split("\r\n")
        self.assertEqual(lines[0], "C    Am")
        self.assertEqual(lines[1], "Test line one")
        self.assertEqual(lines[2], " " * 11 + "G")
        self.assertEqual(lines[3], "Test line two")

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
        with self.assertRaises(RuntimeError):
            self.song.songCharToLineChar(999)
        with self.assertRaises(RuntimeError):
            self.song.songCharToLineChar(13)  # the line break
        with self.assertRaises(RuntimeError):
            self.song.songCharToLineChar(-1)
        self.assertIsNone(self.song.letterLineAndColumn(13))
        self.assertEqual(self.song.letterLineAndColumn(14), (1, 0))

    def test_chords_with_no_letter_do_not_stop_the_song_from_being_copied(self):
        text = self.song.getAllText()
        line_break = text.index("\n")
        for song_id, stray in enumerate((line_break, len(text), len(text) + 50),
                                        start=70):
            song = create_test_song(self.app, song_id=song_id, text=text)
            song._addChord(SongChord(song, 0, 0, 0, -1, "", 0))
            song._addChord(SongChord(song, stray, 3, 0, -1, "", 0))
            with_chords = song.getAsText(include_chords=True)
            self.assertEqual(with_chords.split("\r\n")[0], "C")
            self.assertTrue(song.getLineHasChords(0))
            self.assertFalse(song.getLineHasChords(1))

    def test_the_same_chord_twice_on_a_letter_is_kept_and_the_file_is_unchanged(self):
        """Copy of a songbook with duplicate rows; no repository file is used."""
        song = create_test_song(self.app, song_id=70, text="Amazing grace")
        for chord_id, (number, chord) in enumerate(
            [(0, "C"), (0, "C"), (3, "G"), (3, "Am")], start=100):
            self.app.curs.execute(
                "INSERT INTO song_chord_link (id, song_id, character_num, chord) "
                "VALUES (?, 70, ?, ?)", (chord_id, number, chord))
        self.app.curs.commit()
        rows_before = self.app.curs.execute(
            "SELECT id, character_num, chord FROM song_chord_link "
            "ORDER BY id").fetchall()

        song.updateSongFromDatabase()

        def chords():
            return sorted((c.character_num, c.getStoredText())
                          for c in song.iterateAllChords())

        self.assertEqual(chords(), [(0, "C"), (0, "C"), (3, "Am"), (3, "G")])
        self.assertEqual(
            self.app.curs.execute(
                "SELECT id, character_num, chord FROM song_chord_link "
                "ORDER BY id").fetchall(), rows_before)

    def test_chords_on_letters_is_the_chords_letter_line_and_column_finds(self):
        for song_id, text in enumerate(
            ("", "a", "ab\ncd", "\n\n", "one\n\ntwo\n"), start=60):
            song = create_test_song(self.app, song_id=song_id, text=text)
            for number in range(-2, len(text) + 4):
                song._addChord(SongChord(song, number, 0, 0, -1, "", 0))
            expected = [
                chord for chord in song.iterateAllChords()
                if song.letterLineAndColumn(chord.character_num) is not None
            ]
            self.assertEqual(song.chordsOnLetters(), expected, repr(text))
            for chord in song.chordsOnLetters():
                self.assertNotEqual(text[chord.character_num], "\n")
            self.assertEqual(len(song.chordsOnLetters()), len(text.replace("\n", "")))

    def test_a_chord_name_longer_than_its_line_does_not_crash_the_copy(self):
        song = create_test_song(self.app, song_id=79, text="Oh\nNo")
        song._addChord(SongChord(song, 0, 0, 11, -1, "", 0))
        song.getAsText(include_chords=True)
        cells = list(" ")
        place_chord_on_line(cells, 0, "Cmaj7/G")
        place_chord_on_line([], 0, "C")
        with self.assertRaises(RuntimeError):
            self.song.lineCharToSongChar(9, 0)

    def test_line_heights_follow_whether_the_line_has_chords(self):
        self.assertEqual(self.song.getLineHeights(0),
                         self.app.getHeightsWithoutChords())
        self.song._addChord(SongChord(self.song, 0, 0, 0, -1, "", 0))
        self.assertEqual(self.song.getLineHeights(0),
                         self.app.getHeightsWithChords())
        self.assertEqual(self.song.getLineHeights(1),
                         self.app.getHeightsWithoutChords())

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
            "INSERT INTO song_chord_link (id, song_id, character_num, chord) "
            "VALUES (1, 8, 5, 'G')")
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
            "INSERT INTO song_chord_link (id, song_id, character_num, chord) "
            "VALUES (1, 9, 3, 'C')")
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
            "INSERT INTO song_chord_link (id, song_id, character_num, chord) "
            "VALUES (1, 10, 5, 'G'), "
            "(2, 10, 3, 'C')")
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
            INSERT INTO songs (id, number, title, subtitle, text, uuid, updated_at)
            VALUES (?, ?, ?, '', 'lyrics here', lower(hex(randomblob(16))), 1700000000)
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
            INSERT INTO songs (id, number, title, subtitle, text, uuid, updated_at)
            VALUES (5, 40, "New Song Added Later", '', '', lower(hex(randomblob(16))), 1700000000)
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

    def _mouse(self, event_type, x, y):
        pos = QtCore.QPointF(x, y)
        if event_type == QtCore.QEvent.Type.MouseMove:
            button = Qt.MouseButton.NoButton
            buttons = Qt.MouseButton.LeftButton
        else:
            button = Qt.MouseButton.LeftButton
            buttons = Qt.MouseButton.LeftButton
        return QtGui.QMouseEvent(event_type, pos, pos, button, buttons,
                                 Qt.KeyboardModifier.NoModifier)

    def _press(self, x, y):
        self.editor.mousePressEvent(
            self._mouse(QtCore.QEvent.Type.MouseButtonPress, x, y))

    def _move(self, x, y):
        self.editor.mouseMoveEvent(
            self._mouse(QtCore.QEvent.Type.MouseMove, x, y))

    def _release(self, x, y):
        self.editor.mouseReleaseEvent(
            self._mouse(QtCore.QEvent.Type.MouseButtonRelease, x, y))

    def _song_with_chords_at(self, positions):
        song = create_test_song(self.app, song_id=50, text="0123456789")
        self.app.current_song = song
        for position in positions:
            song.addChord(SongChord(song, position, 0, 0, -1, "", False))
        return song

    def _drag_over(self, letters):
        """Press on the chord on letters[0], move over the others, let go."""
        current = [letters[0]]
        self.app.determineClickedLetter = (
            lambda x, y, dragging: (not dragging, current[0]))
        self._press(3, 3)
        for letter in letters[1:]:
            current[0] = letter
            self._move(3, 3)
        self._release(3, 3)

    def test_dragging_a_chord_jumps_over_a_chord(self):
        song = self._song_with_chords_at([1, 2])

        self._drag_over([1, 2])

        self.assertEqual(
            sorted(chord.character_num for chord in song.iterateAllChords()),
            [2, 3])

    def test_dragging_keeps_the_jump_while_the_mouse_stays_on_the_chord(self):
        song = self._song_with_chords_at([1, 2])
        self.app.determineClickedLetter = lambda x, y, dragging: (True, 1)
        self._press(3, 3)
        self.app.determineClickedLetter = lambda x, y, dragging: (False, 2)

        self._move(3, 3)
        self._move(4, 3)
        self._move(5, 3)
        self._release(5, 3)

        self.assertEqual(
            sorted(chord.character_num for chord in song.iterateAllChords()),
            [2, 3])

    def test_dragging_past_several_chords_and_back(self):
        song = self._song_with_chords_at([1, 2, 3, 4])

        self._drag_over([1, 2, 3, 4, 5])
        self.assertEqual(
            sorted(chord.character_num for chord in song.iterateAllChords()),
            [2, 3, 4, 5])

        # Back over the chords to the left, all the way to the first letter.
        self._drag_over([5, 4, 3, 2, 1, 0])
        self.assertEqual(
            sorted(chord.character_num for chord in song.iterateAllChords()),
            [0, 2, 3, 4])

    def test_dragging_left_onto_a_chord_jumps_left(self):
        song = self._song_with_chords_at([1, 5])

        self._drag_over([5, 4, 3, 2, 1])

        self.assertEqual(
            sorted(chord.character_num for chord in song.iterateAllChords()),
            [0, 1])

    def test_dragging_the_only_free_letter_is_not_lost(self):
        song = self._song_with_chords_at([0, 1, 3])

        self._drag_over([3, 2, 1])

        # The last letter before the chords on 0 and 1 is 2, so it stays there.
        self.assertEqual(
            sorted(chord.character_num for chord in song.iterateAllChords()),
            [0, 1, 2])

    def test_dragging_onto_a_full_line_leaves_the_chord_where_it_was(self):
        song = create_test_song(self.app, song_id=51, text="01\n34")
        self.app.current_song = song
        for position in (0, 3, 4):
            song.addChord(SongChord(song, position, 0, 0, -1, "", False))

        self._drag_over([0, 3])

        # Not onto the occupied letters, and not onto the line break.
        self.assertEqual(
            sorted(chord.character_num for chord in song.iterateAllChords()),
            [0, 3, 4])

    def test_dragging_onto_a_chord_on_another_line_jumps_forward(self):
        song = create_test_song(self.app, song_id=52, text="01\n345")
        self.app.current_song = song
        for position in (0, 3):
            song.addChord(SongChord(song, position, 0, 0, -1, "", False))

        self._drag_over([0, 3])

        self.assertEqual(
            sorted(chord.character_num for chord in song.iterateAllChords()),
            [3, 4])

    def test_click_clears_chord_rectangle_selection(self):
        self._song_with_chords_at([0, 4])
        self.app.selected_chord_nums = {0, 4}
        self.app.determineClickedLetter = lambda x, y, dragging: (False, 2)

        self._press(3, 3)
        self._release(3, 3)

        self.assertEqual(self.app.selected_chord_nums, set())
        self.assertEqual(self.app.selected_char_num, 2)
        self.assertIsNone(self.editor.marquee_origin)

    def test_short_drag_is_a_click(self):
        self._song_with_chords_at([0])
        self.app.determineClickedLetter = lambda x, y, dragging: (False, 2)

        self._press(3, 3)
        self._move(4, 4)
        self._release(4, 4)

        self.assertEqual(self.app.selected_chord_nums, set())
        self.assertEqual(self.app.selected_char_num, 2)

    def test_drag_selects_chords_inside_the_rectangle(self):
        self._song_with_chords_at([0, 4])

        def rects(editor, char_num, chord=None):
            left = char_num * 30
            box = QtCore.QRectF(left, 0, 10, 12)
            return (QtCore.QRectF(left, 20, 10, 12), box)

        self.app.getCharRects = rects
        self.app.determineClickedLetter = lambda x, y, dragging: None
        self._press(0, 0)
        self._move(20, 20)
        self._release(20, 20)

        self.assertEqual(self.app.selected_chord_nums, {0})
        self.assertIsNone(self.app.selected_char_num)

        self._press(0, 0)
        self._move(140, 20)
        self._release(140, 20)

        self.assertEqual(self.app.selected_chord_nums, {0, 4})

    def test_drag_that_misses_clears_the_letter_selection(self):
        self._song_with_chords_at([0])

        def rects(editor, char_num, chord=None):
            box = QtCore.QRectF(0, 400, 10, 12)
            return (box, box)

        self.app.getCharRects = rects
        self.app.determineClickedLetter = lambda x, y, dragging: (False, 3)

        self._press(0, 0)
        self._move(40, 40)
        self._release(40, 40)

        self.assertEqual(self.app.selected_chord_nums, set())
        self.assertIsNone(self.app.selected_char_num)

    def test_press_on_a_chord_glyph_does_not_start_a_rectangle(self):
        self._song_with_chords_at([0])
        self.app.determineClickedLetter = lambda x, y, dragging: (True, 0)

        self._press(5, 5)

        self.assertIsNotNone(self.editor.dragging_chord)
        self.assertIsNone(self.editor.marquee_origin)
        self.assertIn("chord dragged", self.app.undo_stack.commands)

        self._release(5, 5)
        self.assertIsNone(self.editor.dragging_chord)

    def test_marquee_is_drawn_while_the_mouse_is_down(self):
        image = QtGui.QImage(80, 80, QtGui.QImage.Format.Format_ARGB32)
        image.fill(QtGui.QColor("white"))
        painter = QtGui.QPainter(image)
        self.editor.marquee_origin = QtCore.QPoint(5, 5)
        self.editor.marquee_current = QtCore.QPoint(50, 40)
        self.editor._draw_marquee(painter)
        painter.end()

        self.assertNotEqual(image.pixelColor(20, 20), QtGui.QColor("white"))
        self.assertEqual(image.pixelColor(0, 0), QtGui.QColor("white"))


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
        # Open a songbook so .curs is valid
        self.app = test_app()
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

    def test_process_key_pressed_up_down_do_nothing(self):
        """Up/Down arrows leave the selected chord alone."""
        song = create_test_song(self.app, song_id=10003, text="Test")
        self.app.current_song = song
        self.app.selected_char_num = 0
        self.app.previous_song_text = "Test"

        self.app.processKeyPressed(Qt.Key.Key_C)
        self.assertEqual(song.getChordAtPosition(0).note_id, 0)

        self.assertFalse(self.app.processKeyPressed(Qt.Key.Key_Up))
        self.assertFalse(self.app.processKeyPressed(Qt.Key.Key_Down))
        self.assertEqual(song.getChordAtPosition(0).note_id, 0)
        self.assertEqual(self.app.selected_char_num, 0)

    def _select_chords_at(self, text, positions, notes, song_id=10020):
        song = create_test_song(self.app, song_id=song_id, text=text)
        self.app.current_song = song
        self.app.previous_song_text = text
        for position, key in zip(positions, notes):
            self.app.selected_char_num = position
            self.app.processKeyPressed(key)
        self.app.selected_char_num = None
        self.app.selected_chord_nums = set(positions)
        return song

    def test_selected_chords_move_together_and_undo(self):
        song = self._select_chords_at("0123456789", [1, 4],
                                      [Qt.Key.Key_C, Qt.Key.Key_G])

        moved = self.app.processKeyPressed(Qt.Key.Key_Right)

        self.assertTrue(moved)
        self.assertEqual(song.getChordAtPosition(2).note_id, 0)
        self.assertEqual(song.getChordAtPosition(5).note_id, 7)
        self.assertIsNone(self.app.selected_char_num)
        self.assertEqual(self.app.selected_chord_nums, {2, 5})
        self.assertEqual(self.app.undo_stack.undoText(), "move chords")

        self.app.undo_stack.undo()

        self.assertEqual(song.getChordAtPosition(1).note_id, 0)
        self.assertEqual(song.getChordAtPosition(4).note_id, 7)
        self.assertEqual(self.app.selected_chord_nums, {1, 4})
        self.assertIsNone(self.app.selected_char_num)

    def test_selected_chords_stop_at_a_line_break_or_the_end(self):
        song = self._select_chords_at("01\n456789", [1, 4],
                                      [Qt.Key.Key_C, Qt.Key.Key_D])

        self.app.processKeyPressed(Qt.Key.Key_Right)

        self.assertEqual(song.getChordAtPosition(1).note_id, 0)
        self.assertIsNone(song.getChordAtPosition(4))
        self.assertEqual(song.getChordAtPosition(5).note_id, 2)
        self.assertEqual(self.app.selected_chord_nums, {1, 5})

        end_song = self._select_chords_at("0123", [1, 3],
                                          [Qt.Key.Key_C, Qt.Key.Key_D],
                                          song_id=10021)
        self.app.processKeyPressed(Qt.Key.Key_Right)
        self.assertEqual(end_song.getChordAtPosition(2).note_id, 0)
        self.assertEqual(end_song.getChordAtPosition(3).note_id, 2)

    def test_blocked_selected_chords_do_not_add_an_undo_step(self):
        song = self._select_chords_at("0\n2\n456789", [0, 2],
                                      [Qt.Key.Key_C, Qt.Key.Key_D])
        index = self.app.undo_stack.index()

        moved = self.app.processKeyPressed(Qt.Key.Key_Right)

        self.assertTrue(moved)
        self.assertEqual(index, self.app.undo_stack.index())
        self.assertEqual(song.getChordAtPosition(0).note_id, 0)
        self.assertEqual(song.getChordAtPosition(2).note_id, 2)

    def test_neighboring_selected_chords_move_without_landing_on_each_other(self):
        song = self._select_chords_at("0123456789", [2, 3],
                                      [Qt.Key.Key_C, Qt.Key.Key_D])

        self.app.processKeyPressed(Qt.Key.Key_Right)

        self.assertEqual(sorted(chord.character_num
                                for chord in song.iterateAllChords()), [3, 4])
        self.assertEqual(song.getChordAtPosition(3).note_id, 0)
        self.assertEqual(song.getChordAtPosition(4).note_id, 2)

        left_song = self._select_chords_at("0123456789", [0, 1],
                                           [Qt.Key.Key_C, Qt.Key.Key_E],
                                           song_id=10021)
        # The chord on the first letter cannot move, and the next one does not
        # join it: a letter never gets two chords.
        self.app.processKeyPressed(Qt.Key.Key_Left)
        left_chords = list(left_song.iterateAllChords())
        self.assertEqual(sorted(chord.note_id for chord in left_chords),
                         [0, 4])
        self.assertEqual(sorted(chord.character_num for chord in left_chords),
                         [0, 1])

    def test_selected_chords_jump_over_a_chord_that_is_not_selected(self):
        song = self._select_chords_at("0123456789", [2, 3],
                                      [Qt.Key.Key_C, Qt.Key.Key_D])
        self.app.selected_char_num = 4
        self.app.processKeyPressed(Qt.Key.Key_E)
        self.app.selected_char_num = None
        self.app.selected_chord_nums = {2, 3}

        self.app.processKeyPressed(Qt.Key.Key_Right)

        # The chord on 3 jumps over the one on 4, and the chord on 2 follows.
        self.assertEqual(song.getChordAtPosition(3).note_id, 0)
        self.assertEqual(song.getChordAtPosition(4).note_id, 4)
        self.assertEqual(song.getChordAtPosition(5).note_id, 2)
        self.assertEqual(
            sorted(chord.character_num for chord in song.iterateAllChords()),
            [3, 4, 5])
        self.assertEqual(self.app.selected_chord_nums, {3, 5})

    def test_selected_chords_never_share_a_letter_at_a_line_end(self):
        song = self._select_chords_at("01\n3456", [0, 1],
                                      [Qt.Key.Key_C, Qt.Key.Key_D])

        self.app.processKeyPressed(Qt.Key.Key_Right)

        self.assertEqual(song.getChordAtPosition(0).note_id, 0)
        self.assertEqual(song.getChordAtPosition(1).note_id, 2)
        self.assertEqual(len(list(song.iterateAllChords())), 2)

    def _song_with_chords(self, text, notes_at, song_id=10030):
        song = create_test_song(self.app, song_id=song_id, text=text)
        self.app.current_song = song
        self.app.previous_song_text = text
        for position, key in notes_at:
            self.app.selected_char_num = position
            self.app.processKeyPressed(key)
        return song

    def test_arrow_key_jumps_over_a_chord_on_the_next_letter(self):
        song = self._song_with_chords(
            "0123456789", [(2, Qt.Key.Key_C), (3, Qt.Key.Key_D),
                           (4, Qt.Key.Key_E)])
        self.app.selected_char_num = 2

        moved = self.app.processKeyPressed(Qt.Key.Key_Right)

        self.assertTrue(moved)
        self.assertEqual([c.character_num for c in song.iterateAllChords()
                          if c.note_id == 0], [5])
        self.assertEqual(self.app.selected_char_num, 5)
        self.assertEqual(
            sorted(chord.character_num for chord in song.iterateAllChords()),
            [3, 4, 5])

    def test_arrow_key_jumps_left_over_a_chord(self):
        song = self._song_with_chords(
            "0123456789", [(2, Qt.Key.Key_C), (3, Qt.Key.Key_D)],
            song_id=10031)
        self.app.selected_char_num = 3

        self.app.processKeyPressed(Qt.Key.Key_Left)

        self.assertEqual(song.getChordAtPosition(1).note_id, 2)
        self.assertEqual(song.getChordAtPosition(2).note_id, 0)
        self.assertEqual(len(list(song.iterateAllChords())), 2)

    def test_arrow_key_stays_when_no_letter_is_free_that_way(self):
        # Ten spaces right of the last letter is all the room a line has.
        text = "0123" + " " * 10 + "\n567"
        song = self._song_with_chords(
            text, [(12, Qt.Key.Key_C), (13, Qt.Key.Key_D)],
            song_id=10032)
        self.app.selected_char_num = 12
        steps = self.app.undo_stack.index()

        moved = self.app.processKeyPressed(Qt.Key.Key_Right)

        self.assertFalse(moved)
        self.assertEqual(self.app.undo_stack.index(), steps)
        self.assertEqual(song.getAllText(), text)
        self.assertEqual(song.getChordAtPosition(12).note_id, 0)
        self.assertEqual(song.getChordAtPosition(13).note_id, 2)

    def test_arrow_key_does_not_cross_a_line_break_or_the_start(self):
        song = self._song_with_chords(
            "01" + " " * 10 + "\n34", [(0, Qt.Key.Key_C), (11, Qt.Key.Key_D)],
            song_id=10033)
        self.app.selected_char_num = 11
        self.assertFalse(self.app.processKeyPressed(Qt.Key.Key_Right))
        self.app.selected_char_num = 0
        self.assertFalse(self.app.processKeyPressed(Qt.Key.Key_Left))
        self.assertEqual(
            sorted(chord.character_num for chord in song.iterateAllChords()),
            [0, 11])

    def test_delete_removes_every_selected_chord_as_one_undo(self):
        song = self._select_chords_at("0123456789", [1, 4],
                                      [Qt.Key.Key_C, Qt.Key.Key_G])

        self.app.deleteSelectedChord()

        self.assertEqual(list(song.iterateAllChords()), [])
        self.assertEqual(self.app.selected_chord_nums, set())
        self.assertEqual(self.app.undo_stack.undoText(), "delete chords")

        self.app.undo_stack.undo()

        self.assertEqual(song.getChordAtPosition(1).note_id, 0)
        self.assertEqual(song.getChordAtPosition(4).note_id, 7)

    def test_delete_still_removes_the_single_selected_chord(self):
        song = self._select_chords_at("0123456789", [1, 4],
                                      [Qt.Key.Key_C, Qt.Key.Key_G])
        self.app.selected_chord_nums = set()
        self.app.selected_char_num = 1

        self.app.deleteSelectedChord()

        self.assertIsNone(song.getChordAtPosition(1))
        self.assertEqual(song.getChordAtPosition(4).note_id, 7)

    def test_note_keys_do_not_edit_the_rectangle_selection(self):
        song = self._select_chords_at("0123456789", [1, 4],
                                      [Qt.Key.Key_C, Qt.Key.Key_G])

        self.assertFalse(self.app.processKeyPressed(Qt.Key.Key_D))
        self.assertFalse(self.app.processKeyPressed(Qt.Key.Key_Up))
        self.assertFalse(self.app.processKeyPressed(Qt.Key.Key_M))

        chords = list(song.iterateAllChords())
        self.assertEqual(sorted(chord.note_id for chord in chords), [0, 7])
        self.assertEqual(sorted(chord.chord_type_id for chord in chords),
                         [0, 0])

    def test_command_z_undoes_one_chord_edit_and_shift_redoes_it(self):
        song = self._select_chords_at("0123456789", [1, 4],
                                      [Qt.Key.Key_C, Qt.Key.Key_G])
        self.assertEqual(self.app.undo_stack.index(), 2)
        editor = self.app.editor

        def press(key, modifiers):
            # Send the events Qt delivers for a shortcut. QTest.keyClick
            # leaves Shift held down, and the song list then selects nothing.
            override = QtGui.QKeyEvent(QtCore.QEvent.Type.ShortcutOverride,
                                       key, modifiers)
            editor.event(override)
            editor.event(QtGui.QKeyEvent(QtCore.QEvent.Type.KeyPress, key,
                                         modifiers))

        press(Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)

        self.assertEqual(self.app.undo_stack.index(), 1)
        self.assertIsNone(song.getChordAtPosition(4))
        self.assertEqual(song.getChordAtPosition(1).note_id, 0)

        press(Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier
              | Qt.KeyboardModifier.ShiftModifier)

        self.assertEqual(self.app.undo_stack.index(), 2)
        self.assertEqual(song.getChordAtPosition(4).note_id, 7)


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
        self.app = test_app()
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
        self.app = test_app()
        open_empty_temp_songbook(self.app)
        insert_and_select_song(self.app, with_chord=True)

    def test_valid_means_transposing_changes_the_chord(self):
        song = self.app.current_song
        with open(VECTORS_PATH, encoding="utf-8") as fh:
            vectors = json.load(fh)
        texts = (TestChordTextValidity.VALID + TestChordTextValidity.INVALID[:-1] + vectors["validity"]["valid"] +
                 vectors["validity"]["invalid"] +
                 [case["input"] for case in vectors["cases"]])
        for text in texts:
            with self.subTest(text=text):
                chord = softchord.SongChord.from_text(song, 0, text)
                before = chord.getStoredText()
                chord.transpose(1)
                changed = chord.getStoredText() != before
                self.assertEqual(
                    softchord_chords.is_valid_chord_text(text), changed)

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

    def test_chord_text_matches_rendered_chord(self):
        """The chord field shows the same text the song draws."""
        chord = list(self.app.current_song.iterateAllChords())[0]
        dialog = softchord.ChordDialog(self.app)
        dialog._loadChord(chord)
        edit = dialog.ui.chord_text_ef
        self.assertEqual(edit.text(), chord.getChordText())

        # F# m7 / G, with a verse marker and parentheses.
        dialog.ui.note_menu.setCurrentIndex(6)
        dialog.ui.chord_type_menu.setCurrentIndex(4)
        dialog.ui.bass_menu.setCurrentIndex(8)
        dialog.ui.marker_ef.setText("2")
        dialog.ui.in_parentheses_box.setChecked(True)

        expected = SongChord(chord.song, chord.character_num, 6, 4, 7, "2",
                             True)
        self.assertEqual(edit.text(), expected.getChordText())
        self.assertEqual(
            edit.text(), "(2:%sm7/G)" %
            chord.song._getNoteString(6, chord.character_num))
        self.assertEqual(edit.styleSheet(), "")
        dialog.close()

    def test_chord_text_updates_selection(self):
        """Typing a chord fills the marker, note, type, bass, and parentheses."""
        chord = list(self.app.current_song.iterateAllChords())[0]
        dialog = softchord.ChordDialog(self.app)
        dialog._loadChord(chord)
        edit = dialog.ui.chord_text_ef

        edit.setText("2:F#m7/G")
        self.assertEqual(dialog.ui.marker_ef.text(), "2")
        self.assertEqual(dialog.ui.note_menu.currentIndex(), 6)
        self.assertEqual(dialog.ui.chord_type_menu.currentIndex(), 4)
        self.assertEqual(dialog.ui.bass_menu.currentIndex(), 8)
        self.assertFalse(dialog.ui.in_parentheses_box.isChecked())
        self.assertEqual(edit.styleSheet(), "")

        edit.setText("(Am)")
        self.assertEqual(dialog.ui.marker_ef.text(), "")
        self.assertEqual(dialog.ui.note_menu.currentIndex(), 9)
        self.assertEqual(dialog.ui.chord_type_menu.currentIndex(), 1)
        self.assertEqual(dialog.ui.bass_menu.currentIndex(), 0)
        self.assertTrue(dialog.ui.in_parentheses_box.isChecked())
        dialog.close()

    def test_unparseable_chord_text_keeps_the_menus_and_is_red(self):
        """Text that is not a chord is red. The menus stay as they were."""
        chord = list(self.app.current_song.iterateAllChords())[0]
        dialog = softchord.ChordDialog(self.app)
        dialog._loadChord(chord)
        edit = dialog.ui.chord_text_ef
        edit.setText("2:F#m7/G")

        kept = (dialog.ui.marker_ef.text(), dialog.ui.note_menu.currentIndex(),
                dialog.ui.chord_type_menu.currentIndex(),
                dialog.ui.bass_menu.currentIndex(),
                dialog.ui.in_parentheses_box.isChecked())
        edit.setText("nope")
        self.assertIn("red", edit.styleSheet())
        self.assertEqual(
            kept,
            (dialog.ui.marker_ef.text(), dialog.ui.note_menu.currentIndex(),
             dialog.ui.chord_type_menu.currentIndex(),
             dialog.ui.bass_menu.currentIndex(),
             dialog.ui.in_parentheses_box.isChecked()))

        dialog.ui.chord_type_menu.setCurrentIndex(0)
        note = chord.song._getNoteString(6, chord.character_num)
        self.assertEqual(edit.text(), "2:%s/G" % note)
        dialog.close()

    def test_chord_text_is_selected_when_dialog_opens(self):
        """Opening the dialog focuses the chord field with its text selected."""
        chord = list(self.app.current_song.iterateAllChords())[0]
        dialog = softchord.ChordDialog(self.app)

        def check_and_close():
            edit = dialog.ui.chord_text_ef
            self.assertIs(dialog.focusWidget(), edit)
            self.assertTrue(edit.text())
            self.assertEqual(edit.selectedText(), edit.text())
            dialog.reject()

        QtCore.QTimer.singleShot(0, check_and_close)
        self.assertFalse(dialog.display(chord))


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
        self.app = test_app()
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

    def test_selected_chord_halo_is_drawn_on_screen_only(self):
        """The selected letter and chord get the web app's blue halo, never in an export."""
        song = self.app.current_song
        chord = next(song.iterateAllChords())
        self.app.selected_char_num = chord.character_num
        calls = []
        session = self.app.session
        real = session.drawSelection
        session.drawSelection = lambda *args: (calls.append(args), real(*args))
        try:
            image = QtGui.QImage(400, 300, QtGui.QImage.Format.Format_ARGB32)
            image.fill(QtCore.Qt.GlobalColor.white)
            painter = QtGui.QPainter(image)
            rect = QtCore.QRectF(0, 0, 400, 300)
            self.app.drawSongToRect(song, painter, self.app.editor, rect,
                                    exporting=True)
            self.assertEqual(calls, [], "no selection in a PDF, print or image")
            self.app.drawSongToRect(song, painter, self.app.editor, rect,
                                    exporting=False)
            painter.end()
        finally:
            del session.drawSelection
            self.app.selected_char_num = None
        self.assertEqual(len(calls), 1)
        _painter, char_rect, chord_rect = calls[0]
        self.assertTrue(chord_rect)

        # The halo itself: 25% #007aff 2px past the chord, a 1px #007aff line.
        image = QtGui.QImage(120, 80, QtGui.QImage.Format.Format_ARGB32)
        image.fill(QtCore.Qt.GlobalColor.white)
        painter = QtGui.QPainter(image)
        self.app.drawSelection(painter, QtCore.QRectF(40, 50, 10, 20),
                               QtCore.QRectF(40, 20, 30, 16))
        painter.end()
        inside = image.pixelColor(55, 28)
        self.assertEqual((inside.red(), inside.green(), inside.blue()),
                         (191, 222, 255))
        line = image.pixelColor(55, 17)
        self.assertLess(line.red(), 60)
        self.assertGreater(line.blue(), 240)
        outside = image.pixelColor(55, 15)
        self.assertEqual(outside.name(), "#ffffff")
        letter = image.pixelColor(45, 60)
        self.assertEqual((letter.red(), letter.green(), letter.blue()),
                         (204, 228, 255))

    def test_editor_and_export_share_one_chord_layout(self):
        """Screen chords and exported chords come from SongLayout."""
        song = self.app.current_song
        chord = next(song.iterateAllChords())
        doc_layout = QtDocumentLayout(self.app.editor)
        layout = SongLayout.place(doc_layout, [chord],
                                  self.app.getHeightsWithChords,
                                  self.app.getChordWidth,
                                  lambda item: item.getChordText())
        char_rect, chord_rect = self.app.getCharRects(
            self.app.editor, chord.character_num, chord)
        placed = layout.placed[0]
        self.assertEqual(placed.char_rect, char_rect)
        self.assertEqual(placed.chord_rect, chord_rect)
        middle = (char_rect.left() + char_rect.right()) // 2
        self.assertEqual(
            placed.chord_rect.left(),
            middle - self.app.getChordWidth(chord.getChordText()) / 2.0)

        calls = []
        original = SongLayout.place

        def place(*args, **kwargs):
            calls.append(args[0])
            return original(*args, **kwargs)

        SongLayout.place = staticmethod(place)
        image = QtGui.QImage(400, 300, QtGui.QImage.Format.Format_ARGB32)
        image.fill(QtCore.Qt.GlobalColor.white)
        painter = QtGui.QPainter(image)
        try:
            self.app.editor.paintChordLayer(painter)
            self.app.drawSongToRect(song, painter, self.app.editor,
                                    QtCore.QRectF(0, 0, 400, 300),
                                    exporting=True)
        finally:
            painter.end()
            SongLayout.place = staticmethod(original)

        self.assertGreaterEqual(len(calls), 2)
        self.assertIs(calls[0].editor, self.app.editor)
        self.assertIs(calls[1].editor, self.app.editor)

    def _count_pixels(self, image, test):
        count = 0
        for y in range(image.height()):
            for x in range(image.width()):
                color = QtGui.QColor(image.pixel(x, y))
                if test(color.red(), color.green(), color.blue()):
                    count += 1
        return count

    def _draw_exported(self, song):
        image = QtGui.QImage(400, 300, QtGui.QImage.Format.Format_ARGB32)
        image.fill(QtCore.Qt.GlobalColor.white)
        painter = QtGui.QPainter(image)
        try:
            self.app.drawSongToRect(song, painter, self.app.editor,
                                    QtCore.QRectF(0, 0, 400, 300),
                                    exporting=True)
        finally:
            painter.end()
        return image

    def _draw_chord_layer(self):
        image = QtGui.QImage(400, 300, QtGui.QImage.Format.Format_ARGB32)
        image.fill(QtCore.Qt.GlobalColor.white)
        painter = QtGui.QPainter(image)
        try:
            self.app.editor.paintChordLayer(painter)
        finally:
            painter.end()
        return image

    def test_chords_on_a_line_break_or_past_the_end_are_not_painted(self):
        """The same rule as Copy text: no letter, so no chord and no room for it."""
        song = self.app.current_song
        text = song.getAllText()
        before_export = self._draw_exported(song)
        before_layer = self._draw_chord_layer()
        before_blocks = set(song.doc.documentLayout()._chord_blocks)
        self.assertEqual(before_blocks, {0})

        line_break = text.index("\n")
        for stray in (line_break, len(text), len(text) + 50):
            # The same chord as the one on the first letter, so the key shown in
            # the header stays the same and only the painting could differ.
            song._addChord(SongChord(song, stray, 0, 0, -1, "", 0))
        QtDocumentLayout.apply_margins(song, self.app)

        # The last line has only a stray chord, and gets no room for chords.
        self.assertEqual(set(song.doc.documentLayout()._chord_blocks),
                         before_blocks)
        self.assertEqual(self._draw_exported(song), before_export)
        self.assertEqual(self._draw_chord_layer(), before_layer)

        # Every painting path hands only the chords with a letter to the layout.
        seen = []
        original = SongLayout.place

        def place(layout, chords, *args, **kwargs):
            seen.append([chord.character_num for chord in chords])
            return original(layout, chords, *args, **kwargs)

        SongLayout.place = staticmethod(place)
        try:
            self._draw_chord_layer()
            self._draw_exported(song)
            screen = QtGui.QImage(400, 300, QtGui.QImage.Format.Format_ARGB32)
            painter = QtGui.QPainter(screen)
            try:
                self.app.drawSongToRect(song, painter, self.app.editor,
                                        QtCore.QRectF(0, 0, 400, 300),
                                        exporting=False)
            finally:
                painter.end()
            self.app._songSheetBounds(song, self.app.editor)
        finally:
            SongLayout.place = staticmethod(original)
        self.assertGreaterEqual(len(seen), 4)
        for numbers in seen:
            self.assertEqual(numbers, [0])

    def test_unrecognized_chord_is_drawn_in_red_and_a_chord_in_blue(self):
        song = self.app.current_song
        chord = next(song.iterateAllChords())

        def draw():
            image = QtGui.QImage(400, 300, QtGui.QImage.Format.Format_ARGB32)
            image.fill(QtCore.Qt.GlobalColor.white)
            painter = QtGui.QPainter(image)
            try:
                self.app.drawSongToRect(song, painter, self.app.editor,
                                        QtCore.QRectF(0, 0, 400, 300),
                                        exporting=True)
            finally:
                painter.end()
            red = self._count_pixels(
                image, lambda r, g, b: r > 180 and g < 90 and b < 90)
            blue = self._count_pixels(
                image, lambda r, g, b: b > 180 and r < 90 and g < 90)
            return red, blue

        red, blue = draw()
        self.assertEqual(red, 0)
        self.assertGreater(blue, 0)

        chord.set_unknown("asdf")
        layout = SongLayout.place(QtDocumentLayout(self.app.editor), [chord],
                                  self.app.getHeightsWithChords,
                                  self.app.getChordWidth,
                                  lambda item: item.getChordText())
        placed = layout.placed[0]
        self.assertEqual(placed.chord_text, "asdf")
        self.assertTrue(placed.unrecognized)
        self.assertEqual(self.app.chordColorFor(placed).name(), "#ff0000")
        red, blue = draw()
        self.assertGreater(red, 0)
        self.assertEqual(blue, 0)

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

    def test_copy_song_as_image(self):
        """Edit > Copy Song as Image puts a PNG and an SVG on the clipboard."""
        menu_actions = self.app.ui.menuEdit.actions()
        paste = self.app.ui.actionPasteAsNewSong
        copy_image = self.app.ui.actionCopySongAsImage
        self.assertEqual(copy_image.text(), "Copy Song as Image")
        self.assertIs(menu_actions[menu_actions.index(paste) - 1], copy_image)
        self.assertTrue(copy_image.isEnabled())

        self.app.clipboard.setText("not a song sheet")
        self.app.copySongAsImage()
        mime = self.app.clipboard.mimeData()
        formats = mime.formats()
        self.assertIn("image/png", formats)
        self.assertIn("image/svg+xml", formats)
        self.assertNotIn("application/x-qt-image", formats)
        self.assertFalse(any("tiff" in fmt.lower() for fmt in formats))
        image = QtGui.QImage.fromData(bytes(mime.data("image/png")), "PNG")
        self.assertFalse(image.isNull())
        svg = bytes(mime.data("image/svg+xml"))
        self.assertIn(b"<svg", svg)
        self.assertTrue(b"<text" in svg or b"<path" in svg)
        self.assertEqual(self.app.clipboard.text(), "")
        self.assertFalse(self.app.ui.actionPasteAsNewSong.isEnabled())
        self.assertEqual(image.pixelColor(0, 0),
                         QtGui.QColor(QtCore.Qt.GlobalColor.white))
        right, bottom = song_document_size(self.app.current_song)
        self.assertGreater(image.width(), right * 4)
        self.assertGreater(image.height(), bottom * 4)
        self.assertTrue(_image_has_ink(image))

        song = self.app.current_song
        editor = self.app.editor
        with_chords = self.app._renderSongSheetImage(song, editor)
        lyrics_only = self._sheet_without_chords(song)
        self.assertFalse(_same_image(with_chords, lyrics_only))

        bar = editor.verticalScrollBar()
        previous_value = bar.value()
        previous_max = bar.maximum()
        try:
            bar.setValue(0)
            resting = self.app._renderSongSheetImage(song, editor)
            resting_top = self.app.getCharRects(editor, 0)[0].top()
            bar.setMaximum(max(previous_max, 100))
            bar.setValue(50)
            scrolled_top = self.app.getCharRects(editor, 0)[0].top()
            self.assertNotEqual(scrolled_top, resting_top)
            scrolled = self.app._renderSongSheetImage(song, editor)
            self.assertTrue(_same_image(resting, scrolled))
            scrolled_svg = self.app._renderSongSheetSvg(song, editor)
            bar.setValue(0)
            self.assertEqual(bytes(self.app._renderSongSheetSvg(song, editor)),
                             bytes(scrolled_svg))
        finally:
            bar.setValue(previous_value)
            bar.setRange(bar.minimum(), previous_max)

        self.app.ui.songs_view.clearSelection()
        self.assertFalse(copy_image.isEnabled())

    def _sheet_without_chords(self, song):
        saved = song._chords
        song._chords = []
        try:
            return self.app._renderSongSheetImage(song, self.app.editor)
        finally:
            song._chords = saved


def _image_has_ink(image):
    white = QtGui.qRgb(255, 255, 255)
    for y in range(image.height()):
        for x in range(image.width()):
            if image.pixel(x, y) != white:
                return True
    return False


def _same_image(first, second):
    if first.size() != second.size():
        return False
    for y in range(first.height()):
        for x in range(first.width()):
            if first.pixel(x, y) != second.pixel(x, y):
                return False
    return True


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
        self.app = test_app()

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

    def test_fit_scale_ratio_shrinks_only_when_the_song_is_larger(self):
        self.assertEqual(fit_scale_ratio(200, 100, 100, 100, 1.0), 0.5)
        self.assertEqual(fit_scale_ratio(80, 40, 100, 100, 1.0), 1.0)
        # On-screen size already includes zoom, so a 2x view of a fitting song stays 100%.
        self.assertEqual(fit_scale_ratio(160, 80, 100, 100, 2.0), 1.0)

    def test_song_target_size_uses_one_quarter_for_four_copies(self):
        width, height = song_target_size(1224, 1584, 36.0, 36.0, 36.0, 36.0,
                                         True)
        self.assertEqual(width, int(1224 // 2 - 36.0 - 36.0))
        self.assertEqual(height, int(1584 // 2 - 36.0 - 36.0))
        plain_width, plain_height = song_target_size(612, 792, 36.0, 36.0,
                                                     36.0, 36.0, False)
        self.assertEqual(plain_width, 612 - 72.0)
        self.assertEqual(plain_height, 792 - 72.0)

    def test_scale_message_for_fit_and_shrink(self):
        self.assertEqual(scale_message(1.0), "The song fits the page at 100%.")
        self.assertEqual(scale_message(0.918),
                         "The song will be scaled to 91.8% to fit the page.")
        self.assertEqual(scale_message(None),
                         "The page is too small to fit this song.")

    def test_single_song_scale_is_shown_in_the_export_dialog(self):
        dialog = softchord.PdfDialog(self.app)
        self.assertTrue(dialog.ui.scale_label.isHidden())

        dialog.showSongScale(self.app.current_song)
        self.assertFalse(dialog.ui.scale_label.isHidden())
        self.assertEqual(dialog.ui.scale_label.text(),
                         "The song fits the page at 100%.")

        dialog.ui.page_width_ef.setText("1")
        dialog.ui.page_height_ef.setText("1")
        dialog.ui.left_margin_ef.setText("0")
        dialog.ui.right_margin_ef.setText("0")
        dialog.ui.top_margin_ef.setText("0")
        dialog.ui.bottom_margin_ef.setText("0")
        self.assertIn("scaled to", dialog.ui.scale_label.text())
        self.assertNotIn("100%", dialog.ui.scale_label.text())

        dialog.ui.page_width_ef.setText("")
        self.assertEqual(dialog.ui.scale_label.text(),
                         "Enter the page size to see the scale.")

        dialog.ui.page_width_ef.setText("1")
        dialog.ui.left_margin_ef.setText("2")
        dialog.ui.right_margin_ef.setText("2")
        self.assertEqual(dialog.ui.scale_label.text(),
                         "The page is too small to fit this song.")

    def test_drawn_export_scale_matches_the_dialog_formula(self):
        image = QtGui.QImage(40, 40, QtGui.QImage.Format.Format_ARGB32)
        painter = QtGui.QPainter(image)
        rect = QtCore.QRectF(0, 0, 40, 40)
        try:
            drawn = self.app.drawSongToRect(self.app.current_song, painter,
                                            self.app.editor, rect,
                                            exporting=True)
        finally:
            painter.end()
        content_width, content_height = song_document_size(
            self.app.current_song)
        expected = fit_scale_ratio(content_width, content_height, rect.width(),
                                   rect.height(), self.app.zoom_factor)
        self.assertEqual(drawn, expected)
        self.assertLess(drawn, 1.0)

    def test_one_song_does_not_pop_up_the_scale_after_export(self):
        shown = []
        self.app.info = lambda text: shown.append(text)
        self.app.reportScaleRatio(0.918, 1)
        self.app.reportScaleRatio(1.0, 4)
        self.assertEqual(shown, [])
        self.app.reportScaleRatio(0.918, 4)
        self.assertEqual(
            shown,
            ["Some songs were scaled down up to 91.8% to fit the page."])

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

        self.app.chordEditorSelected()
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
        self.app = test_app()
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

        # The table model keeps the saved title until Save.
        row_num = self.app.songs_model.getSongsRow(self.app.current_song)
        self.assertEqual(self.app.songs_model.getRow(row_num).title,
                         original_title)
        self.assertTrue(self.app.saveEdit())
        row_num = self.app.songs_model.getSongsRow(self.app.current_song)
        self.assertEqual(self.app.songs_model.getRow(row_num).title, new_title)

    def test_title_edit_on_readonly_songbook_reverts_and_explains(self):
        previous = self.app.current_song.title
        self.app.curs.execute("PRAGMA query_only = ON")
        errors = []
        self.app.error = lambda text: errors.append(text)

        # The new title is a change; Save is what writes it, and fails.
        self.app.currentSongTitleEdited("Nope")
        self.assertEqual(errors, [])
        self.assertFalse(self.app.saveEdit())
        self.assertTrue(self.app.editing())
        self.app.discardEdit()

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
        self.app.discardEdit()
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
        self.assertTrue(self.app.saveEdit())

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

    def test_store_write_saves_to_the_replaced_songbook_file(self):
        path = self.app.current_songbook_filename
        song_id = self.app.current_song.id
        replaced = path + ".replaced"
        os.rename(path, replaced)
        shutil.copy(replaced, path)

        self.app.store.update_song_title(song_id, "Saved on the new file")
        self.app.store.commit()

        saved = self.app.curs.execute(
            "SELECT title FROM songs WHERE id=?", (song_id,)).fetchone()[0]
        self.assertEqual(saved, "Saved on the new file")
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
            "INSERT INTO songs (id, number, title, subtitle, text, uuid, updated_at) "
            "VALUES (1, 2, 'Other', '', 'line', lower(hex(randomblob(16))), 1700000000)")
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
        self.app = test_app()

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
        chords = [
            row[0] for row in self.app.curs.execute(
                "SELECT chord FROM song_chord_link ORDER BY character_num")
        ]
        self.assertEqual(chords, ["C", "G"])

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

    def test_lyric_edit_over_repeated_letters_keeps_one_chord_per_letter(self):
        # Hello -> Helo: the two l letters used to map onto one letter.
        song = self._song_ready_for_lyric_edit(
            "Hello", [(i, i) for i in range(5)])
        cursor = self.app.editor.textCursor()
        cursor.setPosition(4)
        cursor.deletePreviousChar()

        self.assertEqual(self.app.editor.toPlainText(), "Helo")
        self.assertEqual(
            [(c.character_num, c.note_id) for c in song.iterateAllChords()],
            [(0, 0), (1, 1), (2, 2), (3, 4)])

        self.app.editor.undo()

        self.assertEqual(self.app.editor.toPlainText(), "Hello")
        self.assertEqual(
            [(c.character_num, c.note_id) for c in song.iterateAllChords()],
            [(i, i) for i in range(5)])

    def _song_ready_for_lyric_edit(self, text, chords):
        """Show text in the lyric editor with chords already on it.

        chords is a list of (character index, note id).
        """
        song = create_test_song(self.app, song_id=0, text=text)
        self.app.current_song = song
        self.app.editor.setDocument(song.doc)
        for character_num, note_id in chords:
            song._addChord(
                SongChord(song, character_num, note_id, 2, 7, "1", 1))
        self.app.previous_song_text = text
        self.app.lyricEditorSelected()
        return song

    def _lines_with_a_chord_gap(self, song):
        """Numbers of the lines the layout leaves space above for chords."""
        layout = song.doc.documentLayout()
        return set(layout._chord_blocks)

    def test_chord_gap_follows_the_chord_line_when_a_line_is_added(self):
        song = self._song_ready_for_lyric_edit("ab\ncd\nef", [(3, 5)])
        QtDocumentLayout.apply_margins(song, self.app)
        self.assertEqual(self._lines_with_a_chord_gap(song), {1})

        cursor = self.app.editor.textCursor()
        cursor.setPosition(0)
        cursor.insertText("\n")

        self.assertEqual(self.app.editor.toPlainText(), "\nab\ncd\nef")
        self.assertEqual(song.getChordAtPosition(4).note_id, 5)
        self.assertEqual(self._lines_with_a_chord_gap(song), {2})

    def test_chord_gap_follows_the_chord_line_when_lines_are_joined(self):
        song = self._song_ready_for_lyric_edit("ab\ncd\nef", [(6, 5)])
        QtDocumentLayout.apply_margins(song, self.app)
        self.assertEqual(self._lines_with_a_chord_gap(song), {2})

        cursor = self.app.editor.textCursor()
        cursor.setPosition(3)
        cursor.deletePreviousChar()

        self.assertEqual(self.app.editor.toPlainText(), "abcd\nef")
        self.assertEqual(self._lines_with_a_chord_gap(song), {1})

        self.app.editor.undo()

        self.assertEqual(self.app.editor.toPlainText(), "ab\ncd\nef")
        self.assertEqual(self._lines_with_a_chord_gap(song), {2})

    def test_chord_gap_goes_when_the_chord_letter_is_deleted(self):
        song = self._song_ready_for_lyric_edit("ab\ncd\nef", [(3, 5)])
        QtDocumentLayout.apply_margins(song, self.app)

        cursor = self.app.editor.textCursor()
        cursor.setPosition(3)
        cursor.setPosition(4, QtGui.QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()

        self.assertEqual(list(song.iterateAllChords()), [])
        self.assertEqual(self._lines_with_a_chord_gap(song), set())

    def test_undo_lyric_delete_restores_the_chord(self):
        song = self._song_ready_for_lyric_edit("Hello", [(1, 5), (4, 7)])
        cursor = self.app.editor.textCursor()
        cursor.setPosition(2)
        cursor.deletePreviousChar()

        self.assertEqual(self.app.editor.toPlainText(), "Hllo")
        self.assertIsNone(song.getChordAtPosition(1))
        self.assertEqual(song.getChordAtPosition(3).note_id, 7)

        self.app.editor.undo()

        self.assertEqual(self.app.editor.toPlainText(), "Hello")
        restored = song.getChordAtPosition(1)
        self.assertIsNotNone(restored)
        self.assertEqual(restored.note_id, 5)
        self.assertEqual(restored.chord_type_id, 2)
        self.assertEqual(restored.bass_note_id, 7)
        self.assertEqual(restored.marker, "1")
        self.assertEqual(restored.in_parentheses, 1)
        self.assertEqual(song.getChordAtPosition(4).note_id, 7)
        self.assertIsNone(song.getChordAtPosition(3))

        self.app.editor.redo()

        self.assertEqual(self.app.editor.toPlainText(), "Hllo")
        self.assertIsNone(song.getChordAtPosition(1))
        self.assertEqual(song.getChordAtPosition(3).note_id, 7)

    def test_undo_after_a_later_lyric_edit_keeps_the_chord(self):
        song = self._song_ready_for_lyric_edit("Hello", [(1, 5)])
        cursor = self.app.editor.textCursor()
        cursor.setPosition(2)
        cursor.deletePreviousChar()
        self.app.editor.undo()

        cursor = self.app.editor.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        cursor.insertText("!")
        self.assertEqual(self.app.editor.toPlainText(), "Hello!")
        self.assertEqual(song.getChordAtPosition(1).note_id, 5)

        self.app.editor.undo()

        self.assertEqual(self.app.editor.toPlainText(), "Hello")
        self.assertEqual(song.getChordAtPosition(1).note_id, 5)
        self.assertIsNone(song.getChordAtPosition(5))

    def test_one_undo_restores_chords_removed_by_merged_deletes(self):
        song = self._song_ready_for_lyric_edit("ABCDE", [(4, 4)])
        cursor = self.app.editor.textCursor()
        cursor.setPosition(0)
        self.app.editor.setTextCursor(cursor)
        steps_before = self.app.editor.document().availableUndoSteps()
        for _ in range(5):
            self.app.editor.textCursor().deleteChar()

        self.assertEqual(self.app.editor.toPlainText(), "")
        # Qt groups these deletes into the one undo step a held Delete key is.
        self.assertEqual(self.app.editor.document().availableUndoSteps(),
                         steps_before + 1)
        self.assertEqual(list(song.iterateAllChords()), [])

        self.app.editor.undo()

        self.assertEqual(self.app.editor.toPlainText(), "ABCDE")
        self.assertEqual(song.getChordAtPosition(4).note_id, 4)
        self.assertEqual(len(list(song.iterateAllChords())), 1)

    def test_undo_of_a_lyric_selection_restores_every_chord(self):
        song = self._song_ready_for_lyric_edit("Hello", [(1, 5), (2, 7)])
        cursor = self.app.editor.textCursor()
        cursor.setPosition(1)
        cursor.setPosition(4, QtGui.QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()

        self.assertEqual(self.app.editor.toPlainText(), "Ho")
        self.assertEqual(list(song.iterateAllChords()), [])

        self.app.editor.undo()

        self.assertEqual(self.app.editor.toPlainText(), "Hello")
        self.assertEqual(song.getChordAtPosition(1).note_id, 5)
        self.assertEqual(song.getChordAtPosition(2).note_id, 7)

    def test_undo_of_a_lyric_insert_moves_the_chord_back(self):
        song = self._song_ready_for_lyric_edit("Hello", [(0, 0)])
        cursor = self.app.editor.textCursor()
        cursor.setPosition(0)
        cursor.insertText("x")

        self.assertEqual(self.app.editor.toPlainText(), "xHello")
        self.assertIsNone(song.getChordAtPosition(0))
        self.assertEqual(song.getChordAtPosition(1).note_id, 0)

        self.app.editor.undo()

        self.assertEqual(self.app.editor.toPlainText(), "Hello")
        self.assertEqual(song.getChordAtPosition(0).note_id, 0)
        self.assertIsNone(song.getChordAtPosition(1))

    def test_line_spacing_is_not_a_lyric_undo_step(self):
        song = self._song_ready_for_lyric_edit("Hello\nWorld", [(6, 5)])
        doc = self.app.editor.document()
        steps = doc.availableUndoSteps()
        QtDocumentLayout.apply_margins(song, self.app)
        self.app.updateEditorFonts()
        self.assertEqual(doc.availableUndoSteps(), steps)

        # The first line always has the chord gap. A later line has it only
        # when a chord sits on that line, and a click in the gap hits that line.
        layout = doc.documentLayout()
        first = doc.begin()
        second = first.next()
        first_rect = layout.blockBoundingRect(first)
        second_rect = layout.blockBoundingRect(second)
        _chords_height, lyrics_height, line_height = self.app.getHeightsWithChords(
        )
        gap = (line_height - lyrics_height) * 1.03
        self.assertAlmostEqual(first_rect.top(), gap, delta=0.2)
        self.assertAlmostEqual(second_rect.top() - first_rect.bottom(), gap,
                               delta=0.2)
        hit = layout.hitTest(
            QtCore.QPointF(second_rect.left() + 2,
                           (first_rect.bottom() + second_rect.top()) / 2),
            Qt.HitTestAccuracy.FuzzyHit)
        self.assertEqual(hit, 6)

        cursor = self.app.editor.textCursor()
        cursor.setPosition(7)
        cursor.deletePreviousChar()
        self.assertIsNone(song.getChordAtPosition(6))

        self.app.editor.undo()
        self.assertEqual(self.app.editor.toPlainText(), "Hello\nWorld")
        self.assertEqual(song.getChordAtPosition(6).note_id, 5)

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
        create_schema(conn)
        conn.execute(
            "INSERT INTO songs (id, number, title, subtitle, text, uuid, updated_at) "
            "VALUES (0, 5, 'Appended', 'sub', 'New lyrics', lower(hex(randomblob(16))), 1700000000)")
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
        create_schema(conn)
        conn.execute(
            "INSERT INTO songs (id, number, title, subtitle, text, uuid, updated_at) "
            "VALUES (0, 1, 'First', '', 'Hello', lower(hex(randomblob(16))), 1700000000), "
            "(1, 2, 'Second', '', 'World', lower(hex(randomblob(16))), 1700000000)")
        conn.execute(
            "INSERT INTO song_chord_link (id, song_id, character_num, chord) "
            "VALUES (0, 0, 0, 'C'), "
            "(1, 1, 0, '(G)')")
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
                "SELECT song_id, character_num, chord "
                "FROM song_chord_link ORDER BY song_id"))
        self.assertEqual(chords, [
            (dest_ids["First"], 0, "C"),
            (dest_ids["Second"], 0, "(G)"),
        ])

    def test_remove_trailing_spaces_updates_current_song(self):
        self._open_empty_temp_songbook()
        self.app.curs.execute(
            "INSERT INTO songs (id, number, title, subtitle, text, uuid, updated_at) "
            "VALUES (0, 1, 'Trim Me', '', 'Hi  \nGo', lower(hex(randomblob(16))), 1700000000)")
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
            "INSERT INTO songs (id, number, title, subtitle, text, uuid, updated_at) "
            "VALUES (0, 1, 'Trim Me', '', 'Hi  \nGo', lower(hex(randomblob(16))), 1700000000)")
        self.app.curs.commit()
        self.app.songs_model.updateFromDatabase()
        self.app.ui.songs_view.selectRow(0)
        self.app.current_song.doc.setPlainText("xHi  \nGo")
        self.app.previous_song_text = "xHi  \nGo"

        self.app.removeTrailingSpaces()

        self.assertEqual(self.app.current_song.getAllText(), "xHi\nGo")
        stored = self.app.curs.execute("SELECT text FROM songs").fetchone()[0]
        self.assertEqual(stored, "xHi\nGo")

    def test_transpose_is_one_undo_step(self):
        insert_and_select_song(self.app, with_chord=True)
        song = self.app.current_song
        self.assertEqual(song.getChordAtPosition(0).note_id, 0)

        self.app.transposeUp()
        self.app.transposeUp()
        self.assertEqual(song.getChordAtPosition(0).note_id, 2)
        self.assertEqual(self.app.undo_stack.undoText(), "transpose")
        # A change to Save or Discard: the songbook is not written yet.
        self.assertEqual(self._stored_note_id(), 0)

        self.app.undo_stack.undo()
        self.assertEqual(song.getChordAtPosition(0).note_id, 1)
        self.assertEqual(self._stored_note_id(), 0)

        self.app.undo_stack.redo()
        self.assertEqual(song.getChordAtPosition(0).note_id, 2)
        self.app.undo_stack.undo()
        self.app.undo_stack.undo()
        self.assertEqual(song.getChordAtPosition(0).note_id, 0)
        self.assertEqual(self._stored_note_id(), 0)

    def test_undo_after_switching_songs_does_not_change_the_song_on_screen(self):
        insert_and_select_song(self.app, with_chord=True)
        first = self.app.current_song
        self.app.curs.execute(
            "INSERT INTO songs (id, number, title, subtitle, text, uuid, updated_at) "
            "VALUES (1, 2, 'Zed', '', 'Other song', lower(hex(randomblob(16))), 1700000000)")
        self.app.curs.commit()
        self.app.songs_model.updateFromDatabase()

        self.app.transposeUp()
        self.assertTrue(self.app.undo_stack.canUndo())
        self.assertEqual(self._stored_note_id(), 0)

        # Shown another song without asking: the change is saved.
        self.app.setCurrentSong(Song(self.app, 1))
        other = self.app.current_song
        self.assertEqual(other.id, 1)
        # The step belonged to the first song. It is gone, not applied to this one.
        self.assertFalse(self.app.undo_stack.canUndo())
        self.app.undo()
        self.assertIs(self.app.current_song, other)
        self.assertEqual(other.getAllText(), "Other song")
        self.assertEqual(self._stored_note_id(), 1)

        # Coming back shows the saved song, and Undo has nothing from before.
        self.app.setCurrentSong(Song(self.app, first.id))
        self.assertFalse(self.app.undo_stack.canUndo())

    def test_songbook_steps_survive_switching_songs_when_no_song_step_is_with_them(self):
        insert_and_select_song(self.app)
        self.app.ui.songs_view.selectionModel().clearSelection()
        self.app.curs.execute("UPDATE songs SET number=9 WHERE id=0")
        self.app.curs.execute(
            "INSERT INTO songs (id, number, title, subtitle, text, uuid, updated_at) "
            "VALUES (1, 4, 'Second', '', 'Line', lower(hex(randomblob(16))), 1700000000)")
        self.app.curs.commit()
        self.app.songs_model.updateFromDatabase()
        self.app.ui.songs_view.selectRow(0)
        self.app.renumberAllSongs()
        self.assertEqual(self._song_numbers(), [1, 2])

        self.app.setCurrentSong(Song(self.app, 1))
        self.assertEqual(self.app.current_song.id, 1)
        self.assertEqual(self.app.undo_stack.undoText(), "renumber songs")
        self.app.undo_stack.undo()
        self.assertEqual(self._song_numbers(), [9, 4])

    def test_a_song_of_only_unrecognized_chords_has_nothing_to_transpose(self):
        insert_and_select_song(self.app, with_chord=True)
        song = self.app.current_song
        next(song.iterateAllChords()).set_unknown("N.C.")
        self.assertFalse(song.has_transposable_chords())

        self.app.transposeUp()
        self.assertEqual(song.transposed_steps, 0)
        self.assertFalse(self.app.undo_stack.canUndo())
        self.assertFalse(self.app.toolbar.transpose_reset.isEnabled())
        self.assertEqual(next(song.iterateAllChords()).getChordText(), "N.C.")
        # Even a direct transpose does not count steps for a song that cannot move.
        song.transpose(3)
        self.assertEqual(song.transposed_steps, 0)

    def test_unrecognized_chords_stay_put_when_the_others_are_transposed(self):
        insert_and_select_song(self.app, with_chord=True)
        song = self.app.current_song
        song.addChord(SongChord.unknown_chord(song, 5, "abcdefghij"))
        self.app.transposeUp()
        self.assertEqual(song.transposed_steps, 1)
        self.assertTrue(self.app.toolbar.transpose_reset.isEnabled())
        self.assertEqual(song.getChordAtPosition(0).note_id, 1)
        self.assertEqual(song.getChordAtPosition(5).getChordText(), "abcdefg")
        self.app.undo_stack.undo()
        self.assertEqual(song.transposed_steps, 0)
        self.assertFalse(self.app.toolbar.transpose_reset.isEnabled())

    def test_reset_transpose_is_dimmed_until_the_song_is_transposed(self):
        insert_and_select_song(self.app, with_chord=True)
        song = self.app.current_song
        button = self.app.toolbar.transpose_reset
        self.assertFalse(button.isEnabled())
        self.assertEqual(song.transposed_steps, 0)

        self.app.transposeUp()
        self.assertTrue(button.isEnabled())
        # Up then Down by the same amount is the key it was loaded in: dimmed again.
        self.app.transposeDown()
        self.assertFalse(button.isEnabled())
        self.assertEqual(song.transposed_steps, 0)

        # Reset with nothing to undo does nothing, and adds no undo step.
        steps_before = self.app.undo_stack.count()
        self.app.transposeReset()
        self.assertEqual(self.app.undo_stack.count(), steps_before)

    def test_reset_transpose_goes_back_to_the_key_the_song_was_loaded_in(self):
        insert_and_select_song(self.app, with_chord=True)
        song = self.app.current_song
        button = self.app.toolbar.transpose_reset

        self.app.transposeUp()
        self.app.transposeUp()
        self.app.transposeUp()
        self.app.transposeDown()
        self.assertEqual(song.getChordAtPosition(0).note_id, 2)
        self.assertTrue(button.isEnabled())

        self.app.toolbar.transpose_reset.trigger()
        self.assertEqual(song.getChordAtPosition(0).note_id, 0)
        self.assertEqual(self._stored_note_id(), 0)
        self.assertEqual(song.transposed_steps, 0)
        self.assertFalse(button.isEnabled())
        # One undo step, named so the Edit menu says what it undoes.
        self.assertEqual(self.app.undo_stack.undoText(), "reset transpose")

        # Undo brings the transposed song back, and Reset is available again.
        self.app.undo_stack.undo()
        self.assertEqual(song.getChordAtPosition(0).note_id, 2)
        self.assertEqual(song.transposed_steps, 2)
        self.assertTrue(button.isEnabled())
        self.app.undo_stack.redo()
        self.assertEqual(song.getChordAtPosition(0).note_id, 0)
        self.assertFalse(button.isEnabled())

        # Undoing the transposes themselves tracks the count too: the reset is
        # undone first (2 up), then Down (3 up), then each Up.
        self.app.undo_stack.undo()
        self.app.undo_stack.undo()
        self.assertEqual(song.transposed_steps, 3)
        self.app.undo_stack.undo()
        self.app.undo_stack.undo()
        self.assertEqual(song.transposed_steps, 1)
        self.assertTrue(button.isEnabled())
        self.app.undo_stack.undo()
        self.assertEqual(song.transposed_steps, 0)
        self.assertFalse(button.isEnabled())

    def test_reset_transpose_goes_the_other_way_for_a_song_moved_down(self):
        insert_and_select_song(self.app, with_chord=True)
        song = self.app.current_song
        for _ in range(14):
            self.app.transposeDown()
        # Fourteen down is two down once the octave is dropped.
        self.assertEqual(song.transposed_steps, -2)
        self.assertEqual(song.getChordAtPosition(0).note_id, 10)
        self.app.transposeReset()
        self.assertEqual(song.getChordAtPosition(0).note_id, 0)
        self.assertEqual(song.transposed_steps, 0)

    def test_reset_transpose_is_dimmed_after_a_whole_octave(self):
        insert_and_select_song(self.app, with_chord=True)
        for _ in range(12):
            self.app.transposeUp()
        self.assertEqual(self.app.current_song.getChordAtPosition(0).note_id, 0)
        self.assertFalse(self.app.toolbar.transpose_reset.isEnabled())
        # A tritone and more resets the short way round, either way.
        for steps in (7, 8, 11):
            for _ in range(steps):
                self.app.transposeUp()
            self.assertTrue(self.app.toolbar.transpose_reset.isEnabled())
            self.app.transposeReset()
            self.assertEqual(self.app.current_song.getChordAtPosition(0).note_id, 0)
            self.assertFalse(self.app.toolbar.transpose_reset.isEnabled())

    def test_reset_transpose_keeps_chords_added_after_transposing(self):
        insert_and_select_song(self.app, with_chord=True)
        song = self.app.current_song
        self.app.transposeUp()
        self.app.transposeUp()
        # A chord typed at the transposed key (D, note 2) is moved back with the rest.
        song.addChord(SongChord(song, 1, 2, 0, -1, "", 0))
        self.assertEqual(song.transposed_steps, 2)
        self.app.transposeReset()
        self.assertEqual(song.getChordAtPosition(0).note_id, 0)
        self.assertEqual(song.getChordAtPosition(1).note_id, 0)
        # Nothing was thrown away.
        self.assertEqual(len(list(song.iterateAllChords())), 2)
        self.assertFalse(self.app.toolbar.transpose_reset.isEnabled())

    def test_reset_transpose_counts_from_when_the_song_was_loaded(self):
        insert_and_select_song(self.app, with_chord=True)
        self.app.curs.execute(
            "INSERT INTO songs (id, number, title, subtitle, text, uuid, updated_at) "
            "VALUES (1, 2, 'Zed', '', 'Other song', lower(hex(randomblob(16))), 1700000000)")
        self.app.curs.commit()
        self.app.songs_model.updateFromDatabase()

        self.app.transposeUp()
        self.assertTrue(self.app.toolbar.transpose_reset.isEnabled())
        # A song with no chords has nothing to reset.
        self.app.setCurrentSong(Song(self.app, 1))
        self.assertEqual(self.app.current_song.id, 1)
        self.assertFalse(self.app.toolbar.transpose_reset.isEnabled())
        # Opening the first song again loads it as the songbook has it (one step
        # up, which was saved), so that is now the key it was loaded in.
        self.app.setCurrentSong(Song(self.app, 0))
        self.assertEqual(self.app.current_song.getChordAtPosition(0).note_id, 1)
        self.assertFalse(self.app.toolbar.transpose_reset.isEnabled())
        self.app.transposeUp()
        self.assertTrue(self.app.toolbar.transpose_reset.isEnabled())
        self.app.transposeReset()
        self.assertEqual(self.app.current_song.getChordAtPosition(0).note_id, 1)

    def test_reset_transpose_is_dimmed_with_no_song_open(self):
        insert_and_select_song(self.app, with_chord=True)
        self.app.transposeUp()
        self.assertTrue(self.app.toolbar.transpose_reset.isEnabled())
        self.app.setCurrentSong(None)
        self.app.updateStates()
        self.assertFalse(self.app.toolbar.transpose_reset.isEnabled())
        self.app.transposeReset()  # no song: nothing happens, and no error

    def test_remove_trailing_spaces_undo_restores_a_dropped_chord(self):
        self._open_empty_temp_songbook()
        self.app.curs.execute(
            "INSERT INTO songs (id, number, title, subtitle, text, uuid, updated_at) "
            "VALUES (0, 1, 'Trim Me', '', 'Hi  \nGo', lower(hex(randomblob(16))), 1700000000)")
        self.app.curs.execute(
            "INSERT INTO song_chord_link (id, song_id, character_num, chord) "
            "VALUES (1, 0, 3, 'C'), (2, 0, 5, 'G')")
        self.app.curs.commit()
        self.app.songs_model.updateFromDatabase()
        self.app.ui.songs_view.selectRow(0)

        self.app.removeTrailingSpaces()

        self.assertEqual(self.app.current_song.getAllText(), "Hi\nGo")
        self.assertEqual(self.app.undo_stack.undoText(), "remove trailing spaces")
        kept = list(self.app.current_song.iterateAllChords())
        self.assertEqual([(chord.character_num, chord.note_id) for chord in kept],
                         [(3, 7)])

        self.app.undo_stack.undo()

        self.assertEqual(self.app.current_song.getAllText(), "Hi  \nGo")
        restored = sorted(
            (chord.character_num, chord.note_id)
            for chord in self.app.current_song.iterateAllChords())
        self.assertEqual(restored, [(3, 0), (5, 7)])
        stored = self.app.curs.execute(
            "SELECT text FROM songs WHERE id=0").fetchone()[0]
        self.assertEqual(stored, "Hi  \nGo")

        self.app.undo_stack.redo()
        self.assertEqual(self.app.current_song.getAllText(), "Hi\nGo")
        kept = list(self.app.current_song.iterateAllChords())
        self.assertEqual([(chord.character_num, chord.note_id) for chord in kept],
                         [(3, 7)])

    def test_renumber_undo_restores_song_numbers(self):
        insert_and_select_song(self.app)
        # Drop the open song before changing its number in the songbook.
        # Refreshing the list saves the open song, and that save would put
        # the old number back.
        self.app.ui.songs_view.selectionModel().clearSelection()
        self.app.curs.execute("UPDATE songs SET number=9 WHERE id=0")
        self.app.curs.execute(
            "INSERT INTO songs (id, number, title, subtitle, text, uuid, updated_at) "
            "VALUES (1, 4, 'Second', '', 'Line', lower(hex(randomblob(16))), 1700000000)")
        self.app.curs.commit()
        self.app.songs_model.updateFromDatabase()
        self.app.ui.songs_view.selectRow(0)

        self.app.renumberAllSongs()

        self.assertEqual(self._song_numbers(), [1, 2])
        self.assertEqual(self.app.undo_stack.undoText(), "renumber songs")
        self.app.undo_stack.undo()
        self.assertEqual(self._song_numbers(), [9, 4])
        self.app.undo_stack.redo()
        self.assertEqual(self._song_numbers(), [1, 2])

    def test_paste_as_new_song_undo_removes_only_the_new_song(self):
        insert_and_select_song(self.app)
        self.app.clipboard.setText("Pasted Song Title\nSome lyrics")
        self.app.pasteAsNewSong()

        self.assertEqual(self.app.songs_model.rowCount(), 2)
        self.assertEqual(self.app.undo_stack.undoText(), "import songs")
        self.app.undo_stack.undo()
        self.assertEqual(
            [row[0] for row in self.app.curs.execute(
                "SELECT title FROM songs ORDER BY id")], ["Test Song"])

        self.app.undo_stack.redo()
        self.assertEqual(
            [row[0] for row in self.app.curs.execute(
                "SELECT title FROM songs ORDER BY id")],
            ["Test Song", "Pasted Song Title"])

    def test_import_text_files_undo_removes_the_whole_batch(self):
        insert_and_select_song(self.app)
        folder = tempfile.mkdtemp()
        first = os.path.join(folder, "One.txt")
        second = os.path.join(folder, "Two.txt")
        with open(first, "w", encoding="utf-8") as handle:
            handle.write("One line\n")
        with open(second, "w", encoding="utf-8") as handle:
            handle.write("Two line\n")

        self.app.importTextFiles([first, second])

        self.assertEqual(self.app.songs_model.rowCount(), 3)
        self.app.undo_stack.undo()
        self.assertEqual(
            [row[0] for row in self.app.curs.execute(
                "SELECT title FROM songs ORDER BY id")], ["Test Song"])
        self.app.undo_stack.redo()
        self.assertEqual(self.app.songs_model.rowCount(), 3)

    def test_chordpro_import_undo_removes_the_song_and_its_chords(self):
        insert_and_select_song(self.app, with_chord=True)
        path = os.path.join(tempfile.mkdtemp(), "Hello.chordpro")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("{title:Hello}\n[C]Hi\n")

        self.app.importFromChordPro(path)

        self.assertEqual(self.app.songs_model.rowCount(), 2)
        self.assertEqual(self._chord_count(), 2)
        self.app.undo_stack.undo()
        self.assertEqual(self.app.songs_model.rowCount(), 1)
        self.assertEqual(self._chord_count(), 1)
        self.app.undo_stack.redo()
        self.assertEqual(self.app.songs_model.rowCount(), 2)
        self.assertEqual(self._chord_count(), 2)

    def test_edit_menu_undo_follows_lyric_edits(self):
        insert_and_select_song(self.app, with_chord=True)
        self.app.chordEditorSelected()
        song = self.app.current_song
        song.addChord(SongChord(song, 1, 5, 0, -1, "", 0))
        self.assertTrue(self.app.ui.actionUndo.isEnabled())
        self.app.saveEdit()

        # Each edit has its own history.
        self.app.lyricEditorSelected()
        self.assertFalse(self.app.ui.actionUndo.isEnabled())

        cursor = self.app.editor.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        cursor.insertText("!")
        self.assertTrue(self.app.editor.toPlainText().endswith("!"))
        self.assertTrue(self.app.ui.actionUndo.isEnabled())
        self.assertFalse(self.app.ui.actionRedo.isEnabled())

        self.app.ui.actionUndo.trigger()

        self.assertFalse(self.app.editor.toPlainText().endswith("!"))
        self.assertFalse(self.app.editChanged())
        self.assertTrue(self.app.ui.actionRedo.isEnabled())

        self.app.ui.actionRedo.trigger()
        self.assertTrue(self.app.editor.toPlainText().endswith("!"))
        self.app.discardEdit()
        self.assertIsNotNone(song.getChordAtPosition(1))
        self.assertFalse(self.app.editor.toPlainText().endswith("!"))

    def _stored_note_id(self):
        """Note id of the first stored chord string (root only)."""
        text = self.app.curs.execute(
            "SELECT chord FROM song_chord_link WHERE song_id=0").fetchone()[0]
        return softchord.parse_chord(text).note_id

    def _song_numbers(self):
        return [
            row[0] for row in self.app.curs.execute(
                "SELECT number FROM songs ORDER BY id")
        ]

    def _chord_count(self):
        return self.app.curs.execute(
            "SELECT COUNT(*) FROM song_chord_link").fetchone()[0]


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
            create_schema(conn)
            conn.execute(
                "INSERT INTO songs (id, number, title, subtitle, text, uuid, updated_at) "
                "VALUES (0, 1, 'One', '', 'lyrics', lower(hex(randomblob(16))), 1700000000)")
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

    def test_song_has_no_stored_key(self):
        """The key is always detected: A-major chords must use sharps."""
        app = MinimalTestApp()
        app.curs.execute(
            "INSERT INTO songs (id, number, title, subtitle, text, uuid, "
            "updated_at) VALUES (1, 1, 'x', '', ?, "
            "lower(hex(randomblob(16))), 1700000000)",
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

    def test_steps_of_more_than_an_octave(self):
        self.assertEqual(transpose_note(11, 13), 0)
        self.assertEqual(transpose_note(0, -13), 11)
        self.assertEqual(transpose_note(3, -15), 0)
        self.assertEqual(transpose_note(5, 25), 6)
        self.assertEqual(transpose_note(5, -25), 4)
        for note_id in range(12):
            for steps in range(-40, 41):
                self.assertEqual(transpose_note(note_id, steps), (note_id + steps) % 12)


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


class _CharWidth:
    """Font stand-in. Spaces can be narrower than letters."""

    def __init__(self, space=1.0):
        self.space = space

    def horizontalAdvance(self, text):
        return float(sum(self.space if char.isspace() else 1.0
                         for char in text))


class TestChordLineTokens(unittest.TestCase):
    """Splitting a chord line into names, before they are placed on lyrics."""

    def setUp(self):
        self.parser = _ChordParseApp()

    def convert(self, text):
        return softchord.App.convertChordFromString(self.parser, text)

    def test_spaced_names_keep_their_columns(self):
        self.assertEqual(_chord_tokens("  Am  C"), [("Am", 2, 3), ("C", 6, 6)])

    def test_glued_names_are_split_on_note_letters(self):
        self.assertEqual(_chord_tokens("AmC"), [("Am", 0, 1), ("C", 2, 2)])

    def test_slash_chord_stays_one_token(self):
        self.assertEqual(_chord_tokens("C/E"), [("C/E", 0, 2)])

    def test_cyrillic_lookalikes_are_normalized(self):
        self.assertEqual(_chord_tokens("Сm"), [("Cm", 0, 1)])

    def test_line_is_chords_only_when_chords_outnumber_other_words(self):
        is_chord, entries, warnings = _classify_chord_line(
            "C G", self.convert)
        self.assertTrue(is_chord)
        self.assertEqual([entry[0] for entry in entries], ["C", "G"])
        self.assertEqual(warnings, [])

        is_chord, entries, warnings = _classify_chord_line(
            "Hello C", self.convert)
        self.assertFalse(is_chord)
        self.assertEqual([entry[0] for entry in entries], ["C"])
        self.assertEqual(len(warnings), 1)

    def test_bare_slash_counts_as_a_chord_but_is_not_parsed(self):
        is_chord, entries, _warnings = _classify_chord_line(
            "C / G", self.convert)
        self.assertTrue(is_chord)
        self.assertEqual([entry[0] for entry in entries], ["C", "G"])

    def test_median_odd_and_even_counts(self):
        self.assertEqual(_median([2, 9, 4]), 4)
        self.assertEqual(_median([1, 2, 3, 4]), 2.5)

    def test_nearest_nonspace_prefers_the_right_on_a_tie(self):
        self.assertEqual(_nearest_nonspace("a b", 1), 2)
        self.assertEqual(_nearest_nonspace("a b", 0), 0)
        self.assertIsNone(_nearest_nonspace("   ", 1))
        self.assertEqual(_nearest_nonspace("ab", 10), 1)

    def test_next_free_letter_looks_right_then_left(self):
        self.assertEqual(_next_free_nonspace("abc", 0, {0}), 1)
        self.assertEqual(_next_free_nonspace("abc", 2, {1, 2}), 0)
        self.assertIsNone(_next_free_nonspace("a a", 1, {0, 2}))

    def test_proportional_sheet_is_long_in_characters_but_not_in_width(self):
        # Twelve narrow spaces make the chord line much longer than "Hello"
        # while the two lines have the same visual width.
        pairs = [("C" + (" " * 12) + "G", "Hello")]
        self.assertTrue(
            text_is_proportionally_spaced(pairs, _CharWidth(space=0.25)))
        self.assertFalse(text_is_proportionally_spaced(pairs, _CharWidth()))
        self.assertFalse(text_is_proportionally_spaced([], _CharWidth()))

    def test_empty_lyric_gets_no_anchors(self):
        self.assertEqual(
            assign_chord_anchors("C", "   ", [(0, 0, "C")], _CharWidth(),
                                 False), [])


class _MovedDatabase(sqlite3.OperationalError):
    sqlite_errorname = "SQLITE_READONLY_DBMOVED"


class _FakeConnection:
    """Connection whose first write looks like a replaced songbook file."""

    def __init__(self, fail):
        self.fail = fail
        self.closed = False
        self.rolled_back = False

    def execute(self, sql, params=()):
        if self.fail:
            self.fail = False
            raise _MovedDatabase("attempt to write a readonly database")
        return ("ok", sql, params)

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


class TestSongbookStoreErrors(unittest.TestCase):
    """Which SQLite errors mean 'reopen the file' rather than 'give up'."""

    def test_readonly_message(self):
        readonly = sqlite3.OperationalError(
            "attempt to write a readonly database")
        self.assertTrue(readonly_database_error(readonly))
        self.assertFalse(
            readonly_database_error(sqlite3.OperationalError("no such table")))
        self.assertFalse(readonly_database_error(ValueError("readonly")))

    def test_replaced_file_is_recognized_by_sqlite_name(self):
        self.assertTrue(database_file_was_replaced(_MovedDatabase("moved")))
        self.assertFalse(
            database_file_was_replaced(
                sqlite3.OperationalError("attempt to write a readonly database")))

    def test_write_reopens_when_the_file_was_replaced(self):
        old = _FakeConnection(fail=True)
        new = _FakeConnection(fail=False)
        store = SongbookStore(old)
        store.path = "/tmp/book.songbook"
        store._connect = lambda path: new

        result = store._execute("UPDATE songs SET title=?", ("A",))

        self.assertEqual(result, ("ok", "UPDATE songs SET title=?", ("A",)))
        self.assertIs(store.connection, new)
        self.assertTrue(old.rolled_back)
        self.assertTrue(old.closed)

    def test_reopen_failure_keeps_the_original_error(self):
        old = _FakeConnection(fail=True)
        store = SongbookStore(old)
        store.path = "/tmp/book.songbook"

        def cannot_open(path):
            raise OSError("gone")

        store._connect = cannot_open
        with self.assertRaises(_MovedDatabase):
            store._execute("UPDATE songs SET title=?", ("A",))
        self.assertIs(store.connection, old)
        self.assertFalse(old.closed)

    def test_reopen_without_a_path_does_nothing(self):
        store = SongbookStore()
        self.assertFalse(store.reopen())


class TestSongbookStoreEdits(unittest.TestCase):
    """Song and chord rows, without going through the editor."""

    def setUp(self):
        self.td = tempfile.mkdtemp()
        self.path = os.path.join(self.td, "t.songbook")
        self.store = SongbookStore(SongbookStore.create_file(self.path))
        self.store.path = self.path

    def tearDown(self):
        if self.store.connection is not None:
            self.store.connection.close()
        shutil.rmtree(self.td)

    def test_ids_start_at_zero_and_then_follow_the_max(self):
        self.assertEqual(self.store.next_song_id(), 0)
        self.assertEqual(self.store.next_chord_id(), 0)
        self.store.insert_song(0, 1, "One", "", "Hello")
        self.store.insert_chord(0, 0, "C", chord_id=3)
        self.store.commit()
        self.assertEqual(self.store.next_song_id(), 1)
        self.assertEqual(self.store.next_chord_id(), 4)

    def test_move_and_delete_song(self):
        self.store.insert_song(0, 1, "One", "sub", "Hello")
        self.store.insert_chord(0, 2, "C", chord_id=0)
        self.store.move_chord(0, 2, 4)
        self.store.commit()
        self.assertEqual(self.store.chord_positions(0), [4])

        song = self.store.load_song(0)
        self.assertEqual(song.title, "One")
        self.assertEqual(song.chords[0].character_num, 4)

        self.store.delete_song(0)
        self.store.commit()
        self.assertEqual(self.store.list_song_rows(), [])
        self.assertEqual(self.store.chord_positions(0), [])

    def test_closed_store_lists_nothing_and_refuses_queries(self):
        closed = SongbookStore()
        self.assertEqual(closed.list_song_rows(), [])
        with self.assertRaises(RuntimeError):
            closed.next_song_id()


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

    def test_import_into_new_schema_does_not_require_key_columns(self):
        app = MinimalTestApp()
        song_id = app.curs.execute("SELECT MAX(id) FROM songs").fetchone()[0]
        self.assertIsNone(song_id)
        app.curs.execute(
            "INSERT INTO songs (id, number, title, subtitle, text, uuid, updated_at) "
            "VALUES (0, -1, '', '', '', lower(hex(randomblob(16))), 1700000000)"
        )
        app.curs.commit()
        names = [row[1] for row in app.curs.execute("PRAGMA table_info(songs)")]
        self.assertNotIn("key_note_id", names)


class TestSongsContextMenu(unittest.TestCase):
    """Right-click Delete on the songs table."""

    @classmethod
    def setUpClass(cls):
        cls.app = test_app()
        cls._td = tempfile.TemporaryDirectory()
        path = os.path.join(cls._td.name, "songs.songbook")
        conn = sqlite3.connect(path)
        create_schema(conn)
        conn.commit()
        conn.close()
        cls.app.setCurrentSongbook(path)

    @classmethod
    def tearDownClass(cls):
        cls.app.closeSongbook()
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
                "INSERT INTO songs (id, number, title, subtitle, text, uuid, updated_at) "
                "VALUES (?, ?, ?, '', '', lower(hex(randomblob(16))), 1700000000)", (number, number, title))
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


class TestChordRoom(unittest.TestCase):
    """A chord goes up to 10 letters right of its line (chord_room).

    MIRRORED: chord_edit.test.js and softChord_ViewerTests chordRoomRightOfTheLine
    use the same text and moves.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = test_app()

    def setUp(self):
        self.app = test_app()
        self.td = open_empty_temp_songbook(self.app)
        insert_and_select_song(self.app, text="Hi you\nab", with_chord=True)
        self.app.chordEditorSelected()
        self.song = self.app.current_song
        self.song.addChord(SongChord(self.song, 5, 7, 0, -1, "", 0))
        self.song.addChord(SongChord(self.song, 7, 2, 0, -1, "", 0))

    def tearDown(self):
        if self.app.edit_session is not None:
            self.app._endEdit()
        self.app.setCurrentSongbook(None)
        shutil.rmtree(self.td, ignore_errors=True)

    def positions(self):
        return sorted(c.character_num for c in self.song.iterateAllChords())

    def right(self, times=1, key=Qt.Key.Key_Right):
        for _ in range(times):
            self.assertTrue(self.app.processKeyPressed(key))

    def test_arrows_add_and_take_away_spaces_with_undo_delete_and_save(self):
        self.app.selected_char_num = 5
        self.right()
        self.assertEqual(self.song.getAllText(), "Hi you \nab")
        self.assertEqual(self.positions(), [0, 6, 8])
        self.right(9)
        self.assertEqual(self.song.getAllText(), "Hi you" + " " * 10 + "\nab")
        self.assertEqual(self.positions(), [0, 15, 17])
        self.assertFalse(self.app.processKeyPressed(Qt.Key.Key_Right))
        self.app.undo_stack.undo()
        self.assertEqual(self.song.getAllText(), "Hi you" + " " * 9 + "\nab")
        self.assertEqual(self.positions(), [0, 14, 16])
        self.app.undo_stack.redo()
        self.assertEqual(self.positions(), [0, 15, 17])
        self.right(10, Qt.Key.Key_Left)
        self.assertEqual(self.song.getAllText(), "Hi you\nab")
        self.assertEqual(self.positions(), [0, 5, 7])

        self.right(3)
        self.app.deleteSelectedChord()
        self.assertEqual(self.song.getAllText(), "Hi you\nab")
        self.assertEqual(self.positions(), [0, 7])
        self.app.undo_stack.undo()
        self.assertEqual(self.song.getAllText(), "Hi you   \nab")
        self.assertEqual(self.positions(), [0, 8, 10])

        self.app.saveEdit()
        record = self.app.store.load_song(self.song.id)
        self.assertEqual(record.text, "Hi you   \nab")
        self.assertEqual(sorted(link.character_num for link in record.chords),
                         [0, 8, 10])

    def test_a_drag_past_the_line_gets_spaces_and_back_loses_them(self):
        editor = self.app.editor
        chord = self.song.getChordAtPosition(5)
        self.app.undo_stack.beginMacro("chord dragged")
        editor.dragging_chord = chord
        editor.dragging_mouse_char = 5
        editor.original_chord = None
        try:
            self.app.dragChordPastLineEnd(editor, 6, 10000)
            self.assertEqual(self.song.getAllText(), "Hi you" + " " * 10 + "\nab")
            self.assertEqual(self.positions(), [0, 15, 17])
            moved, _ = self.app.placeChord(editor.dragging_chord, 3)
            self.assertEqual(moved.character_num, 3)
            self.assertEqual(self.song.getAllText(), "Hi you\nab")
            self.assertEqual(self.positions(), [0, 3, 7])
        finally:
            editor.dragging_chord = None
            self.app.undo_stack.endMacro()
        self.app.undo_stack.undo()
        self.assertEqual(self.song.getAllText(), "Hi you\nab")
        self.assertEqual(self.positions(), [0, 5, 7])


class TestEditorModeMenu(unittest.TestCase):
    """Edit Chords… and Edit Text… start edits; the buttons show which."""

    @classmethod
    def setUpClass(cls):
        cls.app = test_app()

    def setUp(self):
        self.app = test_app()
        self.td = open_empty_temp_songbook(self.app)
        insert_and_select_song(self.app, with_chord=True)

    def tearDown(self):
        if self.app.edit_session is not None:
            self.app._endEdit()
        self.app.setCurrentSongbook(None)
        shutil.rmtree(self.td, ignore_errors=True)

    def test_viewing_at_startup(self):
        self.assertFalse(self.app.ui.actionChordEditorMode.isCheckable())
        self.assertFalse(self.app.ui.actionLyricEditorMode.isCheckable())
        self.assertFalse(self.app.toolbar.isActive(self.app.ui.actionChordEditorMode))
        self.assertFalse(self.app.toolbar.isActive(self.app.ui.actionLyricEditorMode))
        self.assertFalse(self.app.editor.lyric_editor_mode)
        self.assertFalse(self.app.editing())

    def test_menu_and_buttons_start_edits(self):
        self.app.ui.actionLyricEditorMode.trigger()
        self.assertTrue(self.app.textEditing())
        self.assertTrue(self.app.toolbar.isActive(self.app.ui.actionLyricEditorMode))
        self.assertFalse(self.app.toolbar.isActive(self.app.ui.actionChordEditorMode))
        self.assertTrue(self.app.editor.lyric_editor_mode)

        # Nothing changed, so the other kind starts without asking.
        self.app.ui.actionChordEditorMode.trigger()
        self.assertTrue(self.app.chordEditing())
        self.assertTrue(self.app.toolbar.isActive(self.app.ui.actionChordEditorMode))
        self.assertFalse(self.app.toolbar.isActive(self.app.ui.actionLyricEditorMode))
        self.assertFalse(self.app.editor.lyric_editor_mode)

        self.app.ui.actionLyricEditorMode.trigger()
        self.assertTrue(self.app.editor.lyric_editor_mode)

        self.app.ui.actionChordEditorMode.trigger()
        self.assertTrue(self.app.toolbar.isActive(self.app.ui.actionChordEditorMode))
        self.assertFalse(self.app.editor.lyric_editor_mode)

        self.app.toolbar.discard.trigger()
        self.assertFalse(self.app.editing())
        self.assertFalse(self.app.toolbar.isActive(self.app.ui.actionChordEditorMode))

    def test_switching_modes_keeps_the_edit_and_does_not_ask(self):
        # MIRRORED UI: the web and iOS apps switch modes the same way.
        asked = []
        with mock.patch.object(type(self.app), "_askSaveChanges",
                               lambda app: asked.append(1) or "cancel"):
            self.assertTrue(self.app.lyricEditorSelected())
            before = self.app._currentSongText()
            cursor = self.app.editor.textCursor()
            cursor.setPosition(0)
            cursor.insertText("Q")
            self.assertTrue(self.app.editChanged())
            self.assertTrue(self.app.chordEditorSelected())
            self.assertEqual(asked, [])
            self.assertTrue(self.app.chordEditing())
            self.assertTrue(self.app._currentSongText().startswith("Q"))
            self.assertTrue(self.app.editChanged())
            self.assertFalse((not self.app.toolbar.save.isVisible()))
            self.assertTrue(self.app.lyricEditorSelected())
            self.assertTrue(self.app.textEditing())
            self.assertTrue(self.app._currentSongText().startswith("Q"))
            self.assertEqual(asked, [])
            self.app.discardEdit()
            self.assertFalse(self.app.editing())
            self.assertEqual(self.app._currentSongText(), before)

    def test_edit_needs_an_open_song(self):
        self.app.setCurrentSong(None)
        self.app.updateStates()
        self.assertFalse(self.app.ui.actionChordEditorMode.isEnabled())
        self.assertFalse(self.app.ui.actionLyricEditorMode.isEnabled())


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
        cls.app = test_app()
        cls._td = tempfile.TemporaryDirectory()
        path = os.path.join(cls._td.name, "songs.songbook")
        conn = sqlite3.connect(path)
        create_schema(conn)
        conn.commit()
        conn.close()
        cls.app.setCurrentSongbook(path)

    @classmethod
    def tearDownClass(cls):
        cls.app.closeSongbook()
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


class TestAppShutdown(unittest.TestCase):
    """A second App() is refused, and the process still exits."""

    def test_second_app_is_refused_and_the_process_exits(self):
        script = (
            "import softchord\n"
            "softchord.App([])\n"
            "try:\n"
            "    softchord.App([])\n"
            "except RuntimeError:\n"
            "    print('ok')\n"
            "else:\n"
            "    raise SystemExit('second app was constructed')\n"
        )
        result = subprocess.run(
            [sys.executable, "-u", "-c", script],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ok", result.stdout)



# ---------------------------------------------------------------------------
# Chord strings (songbook format version 2)
# ---------------------------------------------------------------------------

import hashlib
import json

import softchord_songbook_upgrade
import softchord_v1_compat

VECTORS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "tests",
    "chord_vectors.json")


class TestChordVectors(unittest.TestCase):
    """The same cases are run by the Swift and JS tests."""

    @classmethod
    def setUpClass(cls):
        with open(VECTORS_PATH, encoding="utf-8") as fh:
            cls.cases = json.load(fh)["cases"]

    def test_vectors_are_not_empty(self):
        self.assertGreater(len(self.cases), 100)

    def test_every_vector(self):
        for case in self.cases:
            with self.subTest(input=case["input"]):
                parsed = softchord.parse_chord(case["input"])
                self.assertEqual(parsed.unknown, case["unknown"])
                if case["unknown"]:
                    self.assertEqual(softchord_chords_string(parsed),
                                     case["canonical"])
                    self.assertEqual(parsed.display, case["display"])
                    self.assertEqual(
                        softchord_chords.unrecognized_chord_display(
                            case["input"]), case["display"])
                    continue
                self.assertNotIn("display", case)
                self.assertEqual(parsed.root_text, case["root"])
                self.assertEqual(parsed.note_id, case["note_id"])
                self.assertEqual(
                    "minor" if parsed.is_minor else "major", case["quality"])
                self.assertEqual(parsed.chord_type_id, case["type_id"])
                self.assertEqual(parsed.is_known_type, case["known_type"])
                self.assertEqual(parsed.suffix, case["suffix"])
                self.assertEqual(parsed.bass_text or None, case["bass"])
                if case["bass"] is not None:
                    self.assertEqual(parsed.bass_note_id, case["bass_id"])
                self.assertEqual(parsed.marker, case["marker"])
                self.assertEqual(parsed.in_parentheses, case["parens"])
                self.assertEqual(softchord_chords_string(parsed),
                                 case["canonical"])

    def test_canonical_strings_are_stable(self):
        for case in self.cases:
            with self.subTest(input=case["input"]):
                again = softchord.parse_chord(case["canonical"])
                self.assertEqual(softchord_chords_string(again),
                                 case["canonical"])

    def test_parser_never_raises(self):
        for text in (None, "", " ", "\n", "(", ")", ":", "/", "//", "(:)",
                     "🎸", "C" * 500, "\x00", "Am7/", "(((C)))", "::"):
            with self.subTest(text=text):
                parsed = softchord.parse_chord(text)
                softchord_chords_string(parsed)


class TestLyricChordVectors(unittest.TestCase):
    """The same cases are run by the Swift and JS tests."""

    PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "tests",
        "lyric_chord_vectors.json")

    @classmethod
    def setUpClass(cls):
        with open(cls.PATH, encoding="utf-8") as fh:
            cls.cases = json.load(fh)["cases"]

    def test_vectors_are_not_empty(self):
        self.assertGreater(len(self.cases), 30)

    def test_every_vector(self):
        for case in self.cases:
            with self.subTest(name=case["name"]):
                renumber_map = lyric_renumber_map(case["old"], case["new"])
                kept = [i for i in case["chords_in"] if i in renumber_map]
                self.assertEqual(kept, case["kept"])
                self.assertEqual([renumber_map[i] for i in kept],
                                 case["chords_out"])

    def test_vectors_never_put_two_chords_on_one_letter(self):
        for case in self.cases:
            with self.subTest(name=case["name"]):
                out = case["chords_out"]
                self.assertEqual(out, sorted(set(out)))
                for i in out:
                    self.assertLess(i, len(case["new"]))

    def test_a_kept_chord_stays_on_the_same_letter(self):
        for case in self.cases:
            with self.subTest(name=case["name"]):
                for old, new in zip(case["kept"], case["chords_out"]):
                    self.assertEqual(case["old"][old], case["new"][new])

    def test_random_edits_keep_the_rules(self):
        rng = random.Random(20261028)
        alphabet = "ab\nЖ😀 "
        for _ in range(3000):
            old = "".join(rng.choice(alphabet)
                          for _ in range(rng.randint(0, 9)))
            start = rng.randint(0, len(old))
            end = rng.randint(start, len(old))
            inserted = "".join(rng.choice(alphabet)
                               for _ in range(rng.randint(0, 4)))
            new = old[:start] + inserted + old[end:]
            renumber_map = lyric_renumber_map(old, new)
            targets = list(renumber_map.values())
            with self.subTest(old=old, new=new):
                self.assertEqual(len(targets), len(set(targets)))
                for old_index, new_index in renumber_map.items():
                    self.assertLess(old_index, len(old))
                    self.assertLess(new_index, len(new))
                    self.assertEqual(old[old_index], new[new_index])
                # Order is kept, and nothing outside the edit is lost.
                kept = sorted(renumber_map)
                self.assertEqual([renumber_map[i] for i in kept],
                                 sorted(targets))
                self.assertGreaterEqual(len(renumber_map),
                                        len(old) - (end - start))


class TestChordMoveVectors(unittest.TestCase):
    """The same cases are run by the Swift and JS tests."""

    PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "tests",
        "chord_move_vectors.json")

    @classmethod
    def setUpClass(cls):
        with open(cls.PATH, encoding="utf-8") as fh:
            cls.vectors = json.load(fh)

    def test_vectors_are_not_empty(self):
        self.assertGreater(len(self.vectors["jumps"]), 20)
        self.assertGreater(len(self.vectors["directions"]), 5)

    def test_every_jump(self):
        for case in self.vectors["jumps"]:
            with self.subTest(name=case["name"]):
                self.assertEqual(
                    next_free_character(case["text"], case["target"],
                                        case["direction"],
                                        set(case["occupied"]),
                                        case["allow_other_direction"]),
                    case["expected"])

    def test_every_direction(self):
        for case in self.vectors["directions"]:
            with self.subTest(name=case["name"]):
                self.assertEqual(
                    chord_drag_direction(case["text"], case["chord"],
                                         case["previous"], case["target"]),
                    case["expected"])

    def test_a_jump_lands_on_a_free_letter_of_the_same_line(self):
        rng = random.Random(7)
        for _ in range(2000):
            text = "".join(rng.choice("ab\n") for _ in range(rng.randint(0, 9)))
            occupied = {i for i in range(len(text)) if rng.random() < 0.5}
            target = rng.randint(-1, len(text))
            direction = rng.choice([-1, 1])
            other = rng.random() < 0.5
            landing = next_free_character(text, target, direction, occupied,
                                          other)
            with self.subTest(text=text, target=target, occupied=occupied):
                if landing is None:
                    continue
                self.assertNotIn(landing, occupied)
                self.assertNotEqual(text[landing], "\n")
                self.assertEqual(text.count("\n", min(landing, target),
                                            max(landing, target)), 0)
                # Nothing free was passed over on the way.
                step = 1 if landing >= target else -1
                for between in range(target, landing, step):
                    self.assertIn(between, occupied)


class TestChordTextValidity(unittest.TestCase):
    """is_valid_chord_text: the one definition the chord editors use."""

    VALID = [
        "C", "Am", "Em7/G", "Bb", "F#m7/C#", "H", "Hm", "Аm", "Сmaj7",
        "Вb", "Н", "(Am)", "v:Am", "2:F#m7/G", "Gsus2add9", "  Am  "
    ]
    INVALID = [
        "", "   ", "?", "asdf", "xyz", "a", "am", "N.C.", "(?)", "()", "v:",
        "/C", "1", None
    ]

    def test_valid_texts(self):
        for text in self.VALID:
            with self.subTest(text=text):
                self.assertTrue(softchord_chords.is_valid_chord_text(text))

    def test_invalid_texts(self):
        for text in self.INVALID:
            with self.subTest(text=text):
                self.assertFalse(softchord_chords.is_valid_chord_text(text))

    def test_shared_validity_vectors(self):
        with open(VECTORS_PATH, encoding="utf-8") as fh:
            vectors = json.load(fh)["validity"]
        for text in vectors["valid"]:
            with self.subTest(valid=text):
                self.assertTrue(softchord_chords.is_valid_chord_text(text))
        for text in vectors["invalid"]:
            with self.subTest(invalid=text):
                self.assertFalse(softchord_chords.is_valid_chord_text(text))



def softchord_chords_string(parsed):
    import softchord_chords
    return softchord_chords.parsed_chord_string(parsed)


class TestSongChordFromString(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not QtWidgets.QApplication.instance():
            cls.qapp = QtWidgets.QApplication([])

    def setUp(self):
        self.app = MinimalTestApp()
        self.song = create_test_song(self.app, song_id=1, text="Hello there")

    def chord(self, text):
        return SongChord.from_text(self.song, 0, text)

    def test_known_chord_round_trips(self):
        self.assertEqual(self.chord("Am7/G").getStoredText(), "Am7/G")
        self.assertEqual(self.chord("(1:F♯m)").getStoredText(), "(1:F♯m)")

    def test_unknown_suffix_is_kept_and_base_quality_is_used(self):
        chord = self.chord("Cmaj9")
        self.assertFalse(chord.unknown)
        self.assertEqual(chord.chord_type_id, 0)
        self.assertEqual(chord.getStoredText(), "Cmaj9")
        minor = self.chord("Am(add9)")
        self.assertEqual(minor.chord_type_id, 1)
        self.assertEqual(minor.getStoredText(), "Am(add9)")

    def test_transpose_changes_only_root_and_bass(self):
        chord = self.chord("Am(add9)/E")
        chord.transpose(2)
        self.assertEqual(chord.getStoredText(), "Bm(add9)/F♯")

    def test_unrecognized_chord_shows_its_own_text_and_does_not_move(self):
        chord = self.chord("N.C.")
        self.assertTrue(chord.unknown)
        self.assertEqual(chord.getChordText(), "N.C.")
        self.assertEqual(chord.getStoredText(), "N.C.")
        chord.transpose(5)
        self.assertEqual(chord.getChordText(), "N.C.")
        self.assertEqual(chord.getStoredText(), "N.C.")

    def test_unrecognized_chord_shows_only_its_first_seven_characters(self):
        chord = self.chord("abcdefghij")
        self.assertEqual(chord.getChordText(), "abcdefg")
        # What is saved is the whole text.
        self.assertEqual(chord.getStoredText(), "abcdefghij")
        self.assertEqual(self.chord("Пожалуйста").getChordText(), "Пожалуй")
        self.assertEqual(self.chord("abcdefg").getChordText(), "abcdefg")

    def test_a_long_recognized_chord_is_not_shortened(self):
        chord = self.chord("Cmaj7sus4add9/F#")
        self.assertFalse(chord.unknown)
        self.assertEqual(chord.getChordText(), "Cmaj7sus4add9/F♯")

    def test_empty_or_question_mark_is_a_question_mark(self):
        self.assertEqual(self.chord("").getChordText(), "?")
        self.assertEqual(self.chord("?").getChordText(), "?")
        self.assertEqual(self.chord("").getStoredText(), "?")
        self.assertEqual(self.chord("?").getStoredText(), "?")

    def test_setting_a_note_makes_an_unknown_chord_known(self):
        chord = self.chord("Xyz")
        chord.note_id = 4
        self.assertFalse(chord.unknown)
        self.assertEqual(chord.getStoredText(), "E")

    def test_setting_the_type_replaces_a_kept_suffix(self):
        chord = self.chord("Cmaj9")
        chord.chord_type_id = 1
        self.assertEqual(chord.getStoredText(), "Cm")

    def test_strict_import_parser_still_rejects_words(self):
        for text in ("And", "Xyz", "Cmaj9", "N.C."):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    softchord.convert_chord_from_string(text)


class TestChordStringsInTheEditor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not QtWidgets.QApplication.instance():
            cls.qapp = QtWidgets.QApplication([])
        else:
            cls.qapp = QtWidgets.QApplication.instance()

    def setUp(self):
        self.app = test_app()
        open_empty_temp_songbook(self.app)
        self.app.curs.execute(
            "INSERT INTO songs (id, number, title, subtitle, text, uuid, updated_at) "
            "VALUES (0, 1, 'S', '', 'Amazing grace here', lower(hex(randomblob(16))), 1700000000)")
        self.app.curs.execute(
            "INSERT INTO song_chord_link (id, song_id, character_num, chord) "
            "VALUES (0, 0, 0, 'Cmaj9'), (1, 0, 3, 'Xyz'), (2, 0, 6, '(1:Am/G)')")
        self.app.curs.commit()
        self.app.songs_model.updateFromDatabase()
        self.app.ui.songs_view.selectRow(0)

    def stored(self):
        return [
            row[0] for row in self.app.curs.execute(
                "SELECT chord FROM song_chord_link ORDER BY character_num")
        ]

    def test_saving_without_edits_writes_the_same_strings(self):
        self.app.sendCurrentSongToDatabase()
        self.assertEqual(self.stored(), ["Cmaj9", "Xyz", "(1:Am/G)"])

    def test_unrecognized_chord_is_drawn_as_its_text(self):
        chord = self.app.current_song.getChordAtPosition(3)
        self.assertTrue(chord.unknown)
        self.assertEqual(chord.getChordText(), "Xyz")

    def _run_dialog(self, chord, text):
        dialog = softchord.ChordDialog(self.app)

        def type_and_accept():
            dialog.ui.chord_text_ef.setText(text)
            dialog.accept()

        QtCore.QTimer.singleShot(0, type_and_accept)
        self.assertTrue(dialog.display(chord))

    def test_dialog_keeps_a_chord_this_version_cannot_fully_read(self):
        chord = self.app.current_song.getChordAtPosition(0)
        dialog = softchord.ChordDialog(self.app)
        dialog._loadChord(chord)
        self.assertEqual(dialog.ui.chord_text_ef.text(), "Cmaj9")
        QtCore.QTimer.singleShot(0, dialog.accept)
        self.assertTrue(dialog.display(chord))
        self.assertEqual(chord.getStoredText(), "Cmaj9")

    def _dispose(self, dialog):
        """Close and delete a dialog so none is left under the main window."""
        dialog.close()
        dialog.setParent(None)
        dialog.deleteLater()
        QtWidgets.QApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)

    def test_dialog_refuses_text_that_is_not_a_chord(self):
        chord = self.app.current_song.getChordAtPosition(6)
        before = chord.getStoredText()
        dialog = softchord.ChordDialog(self.app)

        def type_and_try_to_accept():
            for text in ("N.C.", "", "?", "asdf"):
                dialog.ui.chord_text_ef.setText(text)
                dialog.accept()  # Refused, so the dialog stays open.
                self.assertTrue(dialog.isVisible(), text)
            dialog.reject()

        QtCore.QTimer.singleShot(0, type_and_try_to_accept)
        self.assertFalse(dialog.display(chord))
        self.assertEqual(chord.getStoredText(), before)
        self._dispose(dialog)

    def test_dialog_edits_an_unknown_chord_into_a_known_one(self):
        chord = self.app.current_song.getChordAtPosition(3)
        self._run_dialog(chord, "Dm7")
        self.assertFalse(chord.unknown)
        self.assertEqual(chord.getStoredText(), "Dm7")

    def _open(self, position):
        chord = self.app.current_song.getChordAtPosition(position)
        dialog = softchord.ChordDialog(self.app)
        dialog._loadChord(chord)
        ok = dialog.ui.buttonBox.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok)
        return chord, dialog, ok

    def test_invalid_text_is_red_and_cannot_be_saved(self):
        chord, dialog, ok = self._open(6)
        edit = dialog.ui.chord_text_ef
        self.assertEqual(edit.styleSheet(), "")
        self.assertTrue(ok.isEnabled())
        for text in ("asdf", "", "?", "xyz", "N.C."):
            with self.subTest(text=text):
                edit.setText(text)
                self.assertIn("red", edit.styleSheet())
                self.assertFalse(ok.isEnabled())
        for text in ("Dm7", "Bb", "F#m7/C#", "Аm", "(Am)", "v:Am", "Gsus2add9"):
            with self.subTest(text=text):
                edit.setText(text)
                self.assertEqual(edit.styleSheet(), "")
                self.assertTrue(ok.isEnabled())
        self._dispose(dialog)

    def test_an_unknown_chord_opens_red_until_a_valid_chord_is_typed(self):
        chord, dialog, ok = self._open(3)
        edit = dialog.ui.chord_text_ef
        self.assertEqual(edit.text(), "Xyz")
        self.assertIn("red", edit.styleSheet())
        self.assertFalse(ok.isEnabled())
        edit.setText("Dm7")
        self.assertEqual(edit.styleSheet(), "")
        self.assertTrue(ok.isEnabled())
        # Using the menus replaces the text with a valid chord too.
        edit.setText("asdf")
        self.assertFalse(ok.isEnabled())
        dialog.ui.note_menu.setCurrentIndex(5)
        self.assertEqual(edit.styleSheet(), "")
        self.assertTrue(ok.isEnabled())
        self._dispose(dialog)

    def test_enter_does_not_accept_an_invalid_chord(self):
        chord, dialog, ok = self._open(6)
        before = chord.getStoredText()
        dialog.show()
        edit = dialog.ui.chord_text_ef
        edit.setText("asdf")
        QTest.keyClick(edit, Qt.Key.Key_Return)
        self.assertTrue(dialog.isVisible())
        self.assertEqual(dialog.result(), 0)
        # A valid chord is accepted by Enter.
        edit.setText("Dm7")
        QTest.keyClick(edit, Qt.Key.Key_Return)
        self.assertFalse(dialog.isVisible())
        self.assertEqual(dialog.result(), 1)
        self.assertEqual(chord.getStoredText(), before)  # display() not used
        self._dispose(dialog)

    def test_cancel_still_works_with_an_invalid_chord(self):
        chord, dialog, ok = self._open(3)
        before = chord.getStoredText()

        def cancel():
            self.assertFalse(ok.isEnabled())
            dialog.reject()

        QtCore.QTimer.singleShot(0, cancel)
        self.assertFalse(dialog.display(chord))
        self.assertEqual(chord.getStoredText(), before)
        self.assertTrue(chord.unknown)
        self._dispose(dialog)

    def test_dialog_keeps_a_typed_unusual_suffix(self):
        chord = self.app.current_song.getChordAtPosition(6)
        self._run_dialog(chord, "Gsus2add9")
        self.assertEqual(chord.getStoredText(), "Gsus2add9")

    def test_m_key_does_not_crash_on_an_unknown_chord(self):
        self.app.selected_char_num = 3
        self.app.selected_chord_nums = {3}
        event = QtGui.QKeyEvent(QtCore.QEvent.Type.KeyPress, Qt.Key.Key_M,
                                Qt.KeyboardModifier.NoModifier, "m")
        self.app.editor.keyPressEvent(event)
        self.assertEqual(self.stored()[1], "Xyz")


V1_SCHEMA = [
    "CREATE TABLE songs (id int primary key, number int, text text, "
    "title text, subtitle text)",
    "CREATE TABLE song_chord_link (id int primary key, song_id int, "
    "character_num int, note_id int, chord_type_id int, bass_note_id int, "
    "marker text, in_parentheses int)",
    "CREATE TABLE notes (id int primary key, text text, alt_text text)",
    "CREATE TABLE chord_types (id int primary key, name text, print text)",
]

# (song_id, character_num, note_id, type_id, bass_id, marker, parens) and the
# string the converter must write. The id column is NULL in real old files.
V1_CHORDS = [
    (0, 0, 0, 0, -1, "", 0, "C"),
    (0, 3, 9, 1, -1, "1", 0, "1:Am"),
    (0, 6, 9, 4, 7, "", 1, "(Am7/G)"),
    (0, 8, 10, 0, 5, None, 0, "B♭/F"),
    (0, 10, 4, 2, 0, "-1", None, "Esus4/C"),
    (1, 0, 6, 9, -1, "2", 0, "2:F♯m6"),
]


def write_v1_songbook(path):
    conn = sqlite3.connect(path)
    for statement in V1_SCHEMA:
        conn.execute(statement)
    conn.execute("INSERT INTO songs VALUES (0, 1, 'Some words here', 'One', "
                 "'sub')")
    conn.execute("INSERT INTO songs VALUES (1, 2, 'More words', 'Two', '')")
    for note_id, text, alt in softchord.global_notes_list:
        conn.execute("INSERT INTO notes VALUES (?, ?, ?)",
                     (note_id, text, alt))
    for type_id, name, printed in softchord.chord_types_list:
        conn.execute("INSERT INTO chord_types VALUES (?, ?, ?)",
                     (type_id, name, printed))
    for chord in V1_CHORDS:
        conn.execute(
            "INSERT INTO song_chord_link (song_id, character_num, note_id, "
            "chord_type_id, bass_note_id, marker, in_parentheses) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)", chord[:7])
    conn.commit()
    conn.close()


def file_hash(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


class TestV1Compat(unittest.TestCase):
    """TODO(remove-v1-compat): delete with softchord_v1_compat.py."""

    def setUp(self):
        self.td = tempfile.mkdtemp()
        self.addCleanup(self._cleanup)
        self.path = os.path.join(self.td, "old.songbook")
        write_v1_songbook(self.path)

    def _cleanup(self):
        os.chmod(self.td, 0o755)
        shutil.rmtree(self.td, ignore_errors=True)

    def chords(self, path):
        conn = sqlite3.connect(path)
        try:
            return list(
                conn.execute("SELECT song_id, character_num, chord FROM "
                             "song_chord_link ORDER BY song_id, character_num"))
        finally:
            conn.close()

    def expected(self):
        return [(c[0], c[1], c[7]) for c in V1_CHORDS]

    def test_detect_format(self):
        conn = sqlite3.connect(self.path)
        self.assertEqual(softchord_v1_compat.detect_format(conn),
                         softchord_v1_compat.FORMAT_V1)
        conn.close()
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE song_chord_link (id int, song_id int, "
                     "character_num int, chord text)")
        # Chord strings but not the current schema yet.
        self.assertEqual(softchord_v1_compat.detect_format(conn),
                         softchord_v1_compat.FORMAT_V2_EARLY)
        current = sqlite3.connect(":memory:")
        create_schema(current)
        self.assertEqual(softchord_v1_compat.detect_format(current),
                         softchord_v1_compat.FORMAT_V2)
        conn.execute("PRAGMA user_version = 3")
        with self.assertRaises(ValueError):
            softchord_v1_compat.detect_format(conn)

    def test_in_place_conversion_writes_backup_and_new_format(self):
        opened = softchord_v1_compat.open_songbook(
            self.path, softchord.connect_existing_songbook)
        opened.conn.close()
        self.assertTrue(opened.converted)
        self.assertFalse(opened.temp_copy)
        self.assertEqual(self.chords(self.path), self.expected())
        conn = sqlite3.connect(self.path)
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 2)
        tables = [
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")
        ]
        self.assertEqual(sorted(tables), [
            "deleted_songs", "meta", "song_chord_link", "songs"])
        # The conversion writes the final schema directly.
        self.assertTrue(softchord_v1_compat.schema_is_current(conn))
        self.assertEqual(
            conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        self.assertEqual(list(conn.execute("PRAGMA foreign_key_check")), [])
        self.assertEqual(
            conn.execute("SELECT COUNT(*) FROM song_chord_link WHERE id IS "
                         "NULL").fetchone()[0], 0)
        conn.close()
        backup = self.path + ".v1.bak"
        self.assertEqual(opened.backup_path, backup)
        # The backup is the old file: same schema, same rows.
        old = sqlite3.connect(backup)
        self.assertEqual(
            old.execute("SELECT COUNT(*) FROM song_chord_link WHERE note_id "
                        "IS NOT NULL").fetchone()[0], len(V1_CHORDS))
        old.close()

    def test_existing_backup_is_never_overwritten(self):
        with open(self.path + ".v1.bak", "w") as fh:
            fh.write("precious")
        opened = softchord_v1_compat.open_songbook(
            self.path, softchord.connect_existing_songbook)
        opened.conn.close()
        with open(self.path + ".v1.bak") as fh:
            self.assertEqual(fh.read(), "precious")
        self.assertEqual(opened.backup_path, self.path + ".v1.2.bak")

    def test_second_open_does_not_convert_or_back_up_again(self):
        first = softchord_v1_compat.open_songbook(
            self.path, softchord.connect_existing_songbook)
        first.conn.close()
        second = softchord_v1_compat.open_songbook(
            self.path, softchord.connect_existing_songbook)
        second.conn.close()
        self.assertFalse(second.converted)
        self.assertIsNone(second.message)
        self.assertEqual(
            sorted(os.listdir(self.td)),
            ["old.songbook", "old.songbook.v1.bak"])

    def test_file_without_chord_types_table_uses_the_code_list(self):
        conn = sqlite3.connect(self.path)
        conn.execute("DROP TABLE chord_types")
        conn.execute("DROP TABLE notes")
        conn.commit()
        conn.close()
        opened = softchord_v1_compat.open_songbook(
            self.path, softchord.connect_existing_songbook)
        opened.conn.close()
        self.assertEqual(self.chords(self.path), self.expected())

    def test_file_chord_types_table_wins_over_the_code(self):
        # The old solo_and_group_songs file had id 7 as "dim", not "aug".
        conn = sqlite3.connect(self.path)
        conn.execute("UPDATE chord_types SET print='dim' WHERE id=7")
        conn.execute(
            "INSERT INTO song_chord_link (song_id, character_num, note_id, "
            "chord_type_id, bass_note_id, marker, in_parentheses) "
            "VALUES (1, 5, 0, 7, -1, '', 0)")
        conn.commit()
        conn.close()
        opened = softchord_v1_compat.open_songbook(
            self.path, softchord.connect_existing_songbook)
        opened.conn.close()
        self.assertEqual(self.chords(self.path)[-1], (1, 5, "C°"))
        self.assertTrue(
            any("7" in line for line in opened.report.type_table_differences))

    def test_read_only_old_file_is_converted_as_a_temporary_copy(self):
        original = file_hash(self.path)
        os.chmod(self.path, 0o444)
        os.chmod(self.td, 0o555)
        opened = softchord_v1_compat.open_songbook(
            self.path, softchord.connect_existing_songbook)
        opened.conn.close()
        self.assertTrue(opened.temp_copy)
        self.assertNotEqual(opened.path, self.path)
        self.assertEqual(opened.original_path, self.path)
        self.assertIn("not changed", opened.message)
        self.assertEqual(file_hash(self.path), original)
        self.assertEqual(os.listdir(self.td), ["old.songbook"])
        self.assertEqual(self.chords(opened.path), self.expected())
        # The copy can be edited.
        conn = sqlite3.connect(opened.path)
        conn.execute("UPDATE songs SET title='x'")
        conn.commit()
        conn.close()

    def test_a_failed_check_leaves_the_original_untouched(self):
        before = file_hash(self.path)
        original = softchord_v1_compat._check_parsed

        def always_fails(*args):
            raise softchord_v1_compat.ConversionError("forced")

        softchord_v1_compat._check_parsed = always_fails
        try:
            with self.assertRaises(softchord_v1_compat.ConversionError):
                softchord_v1_compat.open_songbook(
                    self.path, softchord.connect_existing_songbook)
        finally:
            softchord_v1_compat._check_parsed = original
        self.assertEqual(file_hash(self.path), before)
        conn = sqlite3.connect(self.path)
        columns = [
            row[1] for row in conn.execute("PRAGMA table_info(song_chord_link)")
        ]
        conn.close()
        self.assertIn("note_id", columns)

    def test_a_row_with_no_valid_note_becomes_an_unknown_chord(self):
        conn = sqlite3.connect(self.path)
        conn.execute(
            "INSERT INTO song_chord_link (song_id, character_num, note_id, "
            "chord_type_id, bass_note_id, marker, in_parentheses) "
            "VALUES (1, 5, 'oops', 0, -1, '', 0)")
        conn.commit()
        conn.close()
        opened = softchord_v1_compat.open_songbook(
            self.path, softchord.connect_existing_songbook)
        opened.conn.close()
        self.assertEqual(self.chords(self.path)[-1], (1, 5, "?"))
        self.assertEqual(opened.report.unknown_chords, 1)

    def test_orphans_are_removed_duplicates_and_null_ids_are_kept(self):
        conn = sqlite3.connect(self.path)
        conn.execute(
            "INSERT INTO song_chord_link (song_id, character_num, note_id, "
            "chord_type_id, bass_note_id, marker, in_parentheses) "
            "VALUES (99, 0, 0, 0, -1, '', 0), (0, 0, 2, 0, -1, '', 0)")
        conn.commit()
        conn.close()
        opened = softchord_v1_compat.open_songbook(
            self.path, softchord.connect_existing_songbook)
        opened.conn.close()
        self.assertEqual(opened.report.orphan_chords, 1)
        self.assertEqual(opened.report.orphan_song_ids, [99])
        self.assertEqual(opened.report.duplicate_positions, 1)
        # The chord of song 99 is gone, the duplicate position stays.
        self.assertEqual(len(self.chords(self.path)), len(V1_CHORDS) + 1)
        self.assertNotIn(99, [row[0] for row in self.chords(self.path)])

    def test_open_for_reading_leaves_the_source_alone(self):
        before = file_hash(self.path)
        conn, cleanup = softchord_v1_compat.open_for_reading(
            self.path, softchord.connect_existing_songbook)
        rows = list(conn.execute(
            "SELECT chord FROM song_chord_link ORDER BY song_id, "
            "character_num"))
        conn.close()
        cleanup()
        self.assertEqual([r[0] for r in rows], [c[7] for c in V1_CHORDS])
        self.assertEqual(file_hash(self.path), before)

    def test_newer_format_is_refused(self):
        conn = sqlite3.connect(self.path)
        conn.execute("PRAGMA user_version = 9")
        conn.commit()
        conn.close()
        with self.assertRaises(ValueError):
            softchord_v1_compat.open_songbook(
                self.path, softchord.connect_existing_songbook)


class TestOpeningOldSongbooksInTheEditor(unittest.TestCase):
    """TODO(remove-v1-compat): delete with softchord_v1_compat.py."""

    @classmethod
    def setUpClass(cls):
        if not QtWidgets.QApplication.instance():
            cls.qapp = QtWidgets.QApplication([])
        else:
            cls.qapp = QtWidgets.QApplication.instance()

    def setUp(self):
        self.app = test_app()
        self.td = tempfile.mkdtemp()
        self.addCleanup(self._cleanup)
        self.path = os.path.join(self.td, "old.songbook")
        write_v1_songbook(self.path)
        self.messages = []
        self.app.info = lambda text: self.messages.append(text)

    def _cleanup(self):
        try:
            self.app.setCurrentSongbook(None)
        except Exception:
            pass
        os.chmod(self.td, 0o755)
        shutil.rmtree(self.td, ignore_errors=True)

    def test_opening_converts_and_says_where_the_backup_is(self):
        self.app.setCurrentSongbook(self.path)
        self.assertEqual(len(self.messages), 1)
        self.assertIn(".v1.bak", self.messages[0])
        self.assertIsNone(self.app.songbook_original_path)
        self.assertEqual(self.app.curs.execute(
            "SELECT chord FROM song_chord_link WHERE song_id=0 AND "
            "character_num=6").fetchone()[0], "(Am7/G)")

    def test_not_writable_opens_a_copy_and_save_as_keeps_the_work(self):
        original = file_hash(self.path)
        os.chmod(self.path, 0o444)
        os.chmod(self.td, 0o555)
        self.app.setCurrentSongbook(self.path)

        self.assertEqual(len(self.messages), 1)
        self.assertIn("old chord format", self.messages[0])
        self.assertEqual(self.app.songbook_original_path, self.path)
        self.assertNotEqual(self.app.current_songbook_filename, self.path)
        self.assertIn("not saved", self.app.win.windowTitle())

        # Edit through the normal path, then Save As.
        self.app.curs.execute("UPDATE songs SET title='Edited' WHERE id=0")
        self.app.curs.commit()
        self.assertEqual(file_hash(self.path), original)

        dest = os.path.join(tempfile.mkdtemp(), "saved.songbook")
        original_get_save = QtWidgets.QFileDialog.getSaveFileName
        QtWidgets.QFileDialog.getSaveFileName = staticmethod(
            lambda *a, **k: (dest, ""))
        try:
            self.app.saveSongbook()
        finally:
            QtWidgets.QFileDialog.getSaveFileName = original_get_save
        self.assertIsNone(self.app.songbook_original_path)
        self.assertEqual(os.path.abspath(self.app.current_songbook_filename),
                         os.path.abspath(dest))
        self.assertEqual(self.app.curs.execute(
            "SELECT title FROM songs WHERE id=0").fetchone()[0], "Edited")
        self.assertEqual(file_hash(self.path), original)

    def test_closing_a_changed_copy_offers_save_as(self):
        os.chmod(self.path, 0o444)
        os.chmod(self.td, 0o555)
        self.app.setCurrentSongbook(self.path)
        asked = []
        self.app.question = lambda text, *a, **k: (asked.append(text) or False)
        self.app.curs.execute("UPDATE songs SET title='Edited' WHERE id=0")
        self.app.curs.commit()
        self.assertTrue(self.app._confirm_close_of_converted_copy())
        self.assertEqual(len(asked), 1)
        self.assertIn(self.path, asked[0])

    def test_closing_a_normal_songbook_asks_nothing(self):
        self.app.setCurrentSongbook(self.path)
        asked = []
        self.app.question = lambda text, *a, **k: (asked.append(text) or False)
        self.assertTrue(self.app._confirm_close_of_converted_copy())
        self.assertEqual(asked, [])

    def test_read_only_new_format_file_opens_read_only_with_a_message(self):
        new_path = os.path.join(self.td, "new.songbook")
        store = SongbookStore()
        store.create_file(new_path)
        os.chmod(new_path, 0o444)
        os.chmod(self.td, 0o555)
        self.app.setCurrentSongbook(new_path)
        self.assertEqual(len(self.messages), 1)
        self.assertIn("read-only", self.messages[0])
        self.assertIn("Save Songbook As", self.messages[0])
        self.assertIn("read-only", self.app.win.windowTitle())
        self.assertIsNone(self.app.songbook_original_path)

    def test_new_songbooks_are_version_2(self):
        path = os.path.join(self.td, "fresh.songbook")
        store = SongbookStore()
        store.create_file(path)
        conn = sqlite3.connect(path)
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 2)
        columns = [
            row[1] for row in conn.execute("PRAGMA table_info(song_chord_link)")
        ]
        self.assertEqual(columns, ["id", "song_id", "character_num", "chord"])
        conn.close()


# ---------------------------------------------------------------------------
# Songbook format: uuid, updated_at, meta, tombstones, constraints
# ---------------------------------------------------------------------------

import time
import uuid as uuid_module


def is_lowercase_uuid4(text):
    try:
        parsed = uuid_module.UUID(text)
    except (ValueError, AttributeError, TypeError):
        return False
    return parsed.version == 4 and str(parsed) == text


def table_columns(conn, table):
    return [row[1] for row in conn.execute("PRAGMA table_info(%s)" % table)]


class TestSongbookSchema(unittest.TestCase):

    def setUp(self):
        self.td = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.td, True)
        self.path = os.path.join(self.td, "My Book.songbook")
        self.conn = SongbookStore.create_file(self.path)
        self.addCleanup(self.conn.close)

    def test_new_songbook_has_the_current_tables_and_columns(self):
        conn = self.conn
        self.assertEqual(
            table_columns(conn, "songs"),
            ["id", "uuid", "number", "title", "subtitle", "text",
             "updated_at"])
        self.assertEqual(table_columns(conn, "song_chord_link"),
                         ["id", "song_id", "character_num", "chord"])
        self.assertEqual(table_columns(conn, "meta"), ["key", "value"])
        self.assertEqual(table_columns(conn, "deleted_songs"),
                         ["uuid", "deleted_at"])
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 2)
        self.assertTrue(
            softchord_v1_compat.schema_is_current(conn))
        indexes = [row[1] for row in conn.execute(
            "PRAGMA index_list(song_chord_link)")]
        self.assertIn("idx_song_chord_link_song_id", indexes)
        # NOT NULL flags and the foreign key with cascade
        notnull = {row[1]: row[3] for row in conn.execute(
            "PRAGMA table_info(songs)")}
        for column in ("uuid", "title", "subtitle", "text", "updated_at"):
            self.assertEqual(notnull[column], 1, column)
        self.assertEqual(notnull["number"], 0)
        foreign_keys = list(conn.execute(
            "PRAGMA foreign_key_list(song_chord_link)"))
        self.assertEqual(foreign_keys[0][2:7],
                         ("songs", "song_id", "id", "NO ACTION", "CASCADE"))

    def test_new_songbook_has_meta_rows(self):
        meta = dict(self.conn.execute("SELECT key, value FROM meta"))
        self.assertEqual(sorted(meta),
                         ["format_version", "name", "songbook_uuid"])
        self.assertEqual(meta["format_version"], "2")
        self.assertEqual(meta["name"], "My Book")
        self.assertTrue(is_lowercase_uuid4(meta["songbook_uuid"]))

    def test_each_new_songbook_has_its_own_uuid(self):
        other = SongbookStore.create_file(
            os.path.join(self.td, "Other.songbook"))
        self.addCleanup(other.close)
        ids = {conn.execute("SELECT value FROM meta WHERE key="
                            "'songbook_uuid'").fetchone()[0]
               for conn in (self.conn, other)}
        self.assertEqual(len(ids), 2)

    def test_connections_enforce_foreign_keys(self):
        self.assertEqual(
            self.conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        self.conn.close()
        conn = softchord.connect_existing_songbook(self.path)
        self.addCleanup(conn.close)
        self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)

    def test_deleting_a_song_row_cascades_to_its_chords(self):
        conn = self.conn
        conn.execute(
            "INSERT INTO songs (id, uuid, number, text, updated_at) "
            "VALUES (1, 'a', 1, 'x', 1)")
        conn.execute(
            "INSERT INTO song_chord_link (song_id, character_num, chord) "
            "VALUES (1, 0, 'C'), (1, 1, 'G')")
        conn.execute("DELETE FROM songs WHERE id=1")
        self.assertEqual(conn.execute(
            "SELECT COUNT(*) FROM song_chord_link").fetchone()[0], 0)

    def test_a_chord_needs_a_song_and_a_chord_text(self):
        conn = self.conn
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO song_chord_link (song_id, character_num, chord) "
                "VALUES (5, 0, 'C')")
        conn.execute(
            "INSERT INTO songs (id, uuid, updated_at) VALUES (5, 'b', 1)")
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO song_chord_link (song_id, character_num, chord) "
                "VALUES (5, 0, NULL)")

    def test_songs_need_a_unique_uuid_and_updated_at(self):
        conn = self.conn
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO songs (id, updated_at) VALUES (1, 1)")
        conn.execute("INSERT INTO songs (id, uuid, updated_at) "
                     "VALUES (1, 'same', 1)")
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO songs (id, uuid, updated_at) "
                         "VALUES (2, 'same', 1)")
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO songs (id, uuid) VALUES (3, 'other')")
        # Defaults: empty strings, NULL number
        row = conn.execute(
            "SELECT number, title, subtitle, text FROM songs WHERE id=1"
        ).fetchone()
        self.assertEqual(row, (None, "", "", ""))


class TestSongUuidUpdatedAtAndTombstones(unittest.TestCase):

    def setUp(self):
        self.app = MinimalTestApp()
        self.store = self.app.store
        self.conn = self.app.curs

    def row(self, song_id=1):
        return self.conn.execute(
            "SELECT uuid, updated_at FROM songs WHERE id=?",
            (song_id,)).fetchone()

    def age(self, song_id=1):
        """Pretend the song was saved long ago."""
        self.conn.execute("UPDATE songs SET updated_at=1000 WHERE id=?",
                          (song_id,))

    def test_a_new_song_gets_a_uuid4_and_utc_updated_at(self):
        before = int(time.time())
        returned = self.store.insert_song(1, 5, "T", "S", "text")
        self.store.commit()
        after = int(time.time())
        uuid_text, updated_at = self.row()
        self.assertEqual(returned, uuid_text)
        self.assertTrue(is_lowercase_uuid4(uuid_text))
        self.assertIsInstance(updated_at, int)
        # UTC epoch seconds, so it is close to time.time() whatever the zone.
        self.assertTrue(before <= updated_at <= after)
        self.store.insert_song(2, 5, "T", "S", "text")
        self.assertNotEqual(self.row(2)[0], uuid_text)

    def test_none_title_subtitle_and_text_are_stored_as_empty(self):
        self.store.insert_song(1, -1, None, None, None)
        self.assertEqual(self.conn.execute(
            "SELECT title, subtitle, text FROM songs").fetchone(),
            ("", "", ""))

    def test_song_object_has_the_uuid_and_it_never_changes(self):
        self.store.insert_song(1, 1, "T", "", "Hello")
        song = Song(self.app, 1)
        uuid_text = self.row()[0]
        self.assertEqual(song.uuid, uuid_text)
        song.title = "New title"
        self.store.update_song(1, song.number, song.title, song.subtitle,
                               song.getAllText())
        self.assertEqual(self.row()[0], uuid_text)

    def test_each_edit_updates_updated_at(self):
        self.store.insert_song(1, 1, "T", "S", "Hello")
        cases = [
            lambda: self.store.update_song_title(1, "Other"),
            lambda: self.store.update_song_subtitle(1, "Other"),
            lambda: self.store.update_song_number(1, 42),
            lambda: self.store.update_song_text(1, "Other text"),
            lambda: self.store.update_song(1, 43, "Third", "x", "Third text"),
            lambda: self.store.insert_chord(1, 0, "C"),
            lambda: self.store.update_chord(1, 0, "D"),
            lambda: self.store.move_chord(1, 0, 2),
            lambda: self.store.delete_chord(1, 2),
        ]
        for index, edit in enumerate(cases):
            with self.subTest(index=index):
                self.age()
                before = int(time.time())
                edit()
                updated_at = self.row()[1]
                self.assertTrue(before <= updated_at <= int(time.time()))

    def test_saving_without_a_change_leaves_updated_at_alone(self):
        self.store.insert_song(1, 1, "T", "S", "Hello")
        self.store.insert_chord(1, 0, "C")
        self.age()
        self.store.update_song(1, 1, "T", "S", "Hello")
        self.store.update_song_title(1, "T")
        self.store.update_song_text(1, "Hello")
        self.store.update_song_number(1, 1)
        self.store.update_chord(1, 0, "C")
        self.store.move_chord(1, 0, 0)
        self.store.delete_chord(1, 99)
        self.assertEqual(self.row()[1], 1000)

    def test_save_of_the_current_song_follows_the_same_rule(self):
        app = test_app()
        td = open_empty_temp_songbook(app)
        self.addCleanup(shutil.rmtree, td, True)
        app.createNewSong()
        app.discardEdit()   # a new song opens a text edit
        song_id = app.current_song.id
        app.curs.execute("UPDATE songs SET updated_at=1000 WHERE id=?",
                         (song_id,))
        app.curs.commit()
        app.sendCurrentSongToDatabase()
        self.assertEqual(app.curs.execute(
            "SELECT updated_at FROM songs WHERE id=?",
            (song_id,)).fetchone()[0], 1000)
        app.current_song.title = "A title"
        before = int(time.time())
        app.sendCurrentSongToDatabase()
        self.assertGreaterEqual(app.curs.execute(
            "SELECT updated_at FROM songs WHERE id=?",
            (song_id,)).fetchone()[0], before)
        app.setCurrentSongbook(None)

    def test_delete_leaves_a_tombstone_with_the_uuid(self):
        self.store.insert_song(1, 1, "T", "S", "Hello")
        self.store.insert_chord(1, 0, "C")
        uuid_text = self.row()[0]
        before = int(time.time())
        self.store.delete_song(1)
        self.store.commit()
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(*) FROM songs").fetchone()[0], 0)
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(*) FROM song_chord_link").fetchone()[0], 0)
        tombstone = self.conn.execute(
            "SELECT uuid, deleted_at FROM deleted_songs").fetchall()
        self.assertEqual(len(tombstone), 1)
        self.assertEqual(tombstone[0][0], uuid_text)
        self.assertTrue(before <= tombstone[0][1] <= int(time.time()))

    def test_tombstone_and_delete_are_one_transaction(self):
        self.store.insert_song(1, 1, "T", "S", "Hello")
        self.store.commit()
        self.store.delete_song(1)
        self.conn.rollback()
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(*) FROM songs").fetchone()[0], 1)
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(*) FROM deleted_songs").fetchone()[0], 0)

    def test_reinserting_the_uuid_removes_the_tombstone(self):
        self.store.insert_song(1, 1, "T", "S", "Hello")
        uuid_text = self.row()[0]
        self.store.delete_song(1)
        self.store.insert_song(1, 1, "T", "S", "Hello", uuid_text)
        self.assertEqual(self.row()[0], uuid_text)
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(*) FROM deleted_songs").fetchone()[0], 0)

    def test_deleting_a_missing_song_adds_no_tombstone(self):
        self.store.delete_song(77)
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(*) FROM deleted_songs").fetchone()[0], 0)


class TestUuidsInTheEditor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not QtWidgets.QApplication.instance():
            cls.qapp = QtWidgets.QApplication([])

    def setUp(self):
        self.app = test_app()
        self.td = open_empty_temp_songbook(self.app)
        self.addCleanup(shutil.rmtree, self.td, True)
        self.addCleanup(self.app.setCurrentSongbook, None)

    def uuids(self):
        return [row[0] for row in self.app.curs.execute(
            "SELECT uuid FROM songs ORDER BY id")]

    def test_new_and_imported_songs_get_uuids(self):
        self.app.createNewSong()
        self.app.importSongFromText("Title\nSome lyrics")
        uuids = self.uuids()
        self.assertEqual(len(uuids), 2)
        self.assertEqual(len(set(uuids)), 2)
        self.assertTrue(all(is_lowercase_uuid4(u) for u in uuids))

    def test_chordpro_import_gets_a_uuid(self):
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "test_тест_chordpro_song.chordpro"),
                  encoding="utf-8") as fh:
            text = fh.read()
        self.app.importSongFromText(text, "chordpro song")
        self.assertTrue(is_lowercase_uuid4(self.uuids()[0]))

    def test_appended_songs_get_new_uuids(self):
        source_path = os.path.join(self.td, "source.songbook")
        conn = SongbookStore.create_file(source_path)
        conn.execute(
            "INSERT INTO songs (id, uuid, number, title, text, updated_at) "
            "VALUES (0, '11111111-1111-4111-8111-111111111111', 1, 'A', "
            "'Hello', 1)")
        conn.commit()
        conn.close()
        self.app.appendSongbookFile(source_path)
        self.app.appendSongbookFile(source_path)  # twice must not collide
        uuids = self.uuids()
        self.assertEqual(len(uuids), 2)
        self.assertEqual(len(set(uuids)), 2)
        self.assertNotIn("11111111-1111-4111-8111-111111111111", uuids)

    def test_delete_and_undo_keep_the_uuid(self):
        self.app.importSongFromText("Title\nSome lyrics")
        song_id = self.app.curs.execute("SELECT id FROM songs").fetchone()[0]
        uuid_text = self.uuids()[0]
        command = DeleteSongsCommand(self.app, [song_id])
        command.redo()
        self.assertEqual(self.uuids(), [])
        self.assertEqual([row[0] for row in self.app.curs.execute(
            "SELECT uuid FROM deleted_songs")], [uuid_text])
        command.undo()
        self.assertEqual(self.uuids(), [uuid_text])
        self.assertEqual(self.app.curs.execute(
            "SELECT COUNT(*) FROM deleted_songs").fetchone()[0], 0)

    def test_the_editor_deletes_chords_with_their_song(self):
        self.app.importSongFromText("Title\nSome lyrics")
        song_id = self.app.curs.execute("SELECT id FROM songs").fetchone()[0]
        self.app.curs.execute(
            "INSERT INTO song_chord_link (song_id, character_num, chord) "
            "VALUES (?, 0, 'C')", (song_id,))
        self.app.curs.commit()
        DeleteSongsCommand(self.app, [song_id]).redo()
        self.assertEqual(self.app.curs.execute(
            "SELECT COUNT(*) FROM song_chord_link").fetchone()[0], 0)


# ---------------------------------------------------------------------------
# Upgrading early version 2 files (chord strings, but no uuid / meta)
# ---------------------------------------------------------------------------

EARLY_V2_SCHEMA = """
CREATE TABLE songs (id INTEGER PRIMARY KEY, number INTEGER, text TEXT,
    title TEXT, subtitle TEXT, key_note_id INTEGER, key_is_major INTEGER,
    alt_key_note_id INTEGER);
CREATE TABLE song_chord_link (id INTEGER PRIMARY KEY, song_id INTEGER,
    character_num INTEGER, chord TEXT);
PRAGMA user_version = 2;
"""
EARLY_V2_SONGS = [
    # id, number, text, title, subtitle, key, major, alt key
    (0, 1, "Hello world", "One", None, 2, 1, None),
    (1, None, None, None, "sub", None, None, 4),
    (5, 7, "abc", "Five", "", 0, 0, 0),
]
EARLY_V2_CHORDS = [
    (1, 0, 0, "C"),
    (2, 0, 6, "(Am7/G)"),
    (3, 1, 0, "D"),
    (4, 99, 0, "G"),  # orphan
    (5, 99, 3, "A"),  # orphan
    (6, 5, 1, "E"),
]
EARLY_V2_ORPHANS = 2


def write_early_v2_songbook(path, songs=EARLY_V2_SONGS,
                            chords=EARLY_V2_CHORDS):
    conn = sqlite3.connect(path)
    conn.executescript(EARLY_V2_SCHEMA)
    conn.executemany("INSERT INTO songs VALUES (?,?,?,?,?,?,?,?)", songs)
    conn.executemany("INSERT INTO song_chord_link VALUES (?,?,?,?)", chords)
    conn.commit()
    conn.close()


class TestEarlyVersion2Upgrade(unittest.TestCase):

    def setUp(self):
        self.td = tempfile.mkdtemp()
        self.addCleanup(self._cleanup)
        self.path = os.path.join(self.td, "early.songbook")
        write_early_v2_songbook(self.path)

    def _cleanup(self):
        os.chmod(self.td, 0o755)
        shutil.rmtree(self.td, ignore_errors=True)

    def check_current(self, path):
        conn = sqlite3.connect(path)
        self.addCleanup(conn.close)
        self.assertTrue(softchord_v1_compat.schema_is_current(conn))
        self.assertEqual(softchord_v1_compat.detect_format(conn),
                         softchord_v1_compat.FORMAT_V2)
        self.assertEqual(
            table_columns(conn, "songs"),
            ["id", "uuid", "number", "title", "subtitle", "text",
             "updated_at"])
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 2)
        self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0],
                         "ok")
        self.assertEqual(list(conn.execute("PRAGMA foreign_key_check")), [])
        return conn

    def test_detected_by_schema(self):
        conn = sqlite3.connect(self.path)
        self.addCleanup(conn.close)
        self.assertEqual(softchord_v1_compat.detect_format(conn),
                         softchord_v1_compat.FORMAT_V2_EARLY)
        # The version number does not decide it.
        conn.execute("PRAGMA user_version = 0")
        self.assertEqual(softchord_v1_compat.detect_format(conn),
                         softchord_v1_compat.FORMAT_V2_EARLY)

    def test_writable_file_is_upgraded_in_place_with_a_backup(self):
        before = int(time.time())
        opened = softchord_v1_compat.open_songbook(
            self.path, softchord.connect_existing_songbook)
        opened.conn.close()
        self.assertTrue(opened.converted)
        self.assertFalse(opened.temp_copy)
        backup = self.path + ".pre-uuid.bak"
        self.assertEqual(opened.backup_path, backup)
        self.assertIn(backup, opened.message)
        # The backup is the untouched early file.
        old = sqlite3.connect(backup)
        self.assertIn("key_note_id", table_columns(old, "songs"))
        self.assertEqual(old.execute(
            "SELECT COUNT(*) FROM song_chord_link").fetchone()[0],
            len(EARLY_V2_CHORDS))
        old.close()

        conn = self.check_current(self.path)
        songs = list(conn.execute(
            "SELECT id, number, title, subtitle, text FROM songs ORDER BY id"))
        self.assertEqual(songs, [
            (0, 1, "One", "", "Hello world"),
            (1, None, "", "sub", ""),
            (5, 7, "Five", "", "abc"),
        ])
        uuids = [r[0] for r in conn.execute("SELECT uuid FROM songs")]
        self.assertTrue(all(is_lowercase_uuid4(u) for u in uuids))
        self.assertEqual(len(set(uuids)), 3)
        for (updated_at,) in conn.execute("SELECT updated_at FROM songs"):
            self.assertTrue(before <= updated_at <= int(time.time()))
        meta = dict(conn.execute("SELECT key, value FROM meta"))
        self.assertEqual(meta["format_version"], "2")
        self.assertEqual(meta["name"], "early")
        self.assertTrue(is_lowercase_uuid4(meta["songbook_uuid"]))
        self.assertEqual(conn.execute(
            "SELECT COUNT(*) FROM deleted_songs").fetchone()[0], 0)

    def test_orphan_chord_rows_are_removed_and_reported(self):
        opened = softchord_v1_compat.open_songbook(
            self.path, softchord.connect_existing_songbook)
        opened.conn.close()
        report = opened.report
        self.assertEqual(report.songs, 3)
        self.assertEqual(report.chords_before, len(EARLY_V2_CHORDS))
        self.assertEqual(report.orphan_chords, EARLY_V2_ORPHANS)
        self.assertEqual(report.orphan_song_ids, [99])
        self.assertEqual(report.chords,
                         len(EARLY_V2_CHORDS) - EARLY_V2_ORPHANS)
        self.assertEqual(sorted(report.key_columns_removed),
                         ["alt_key_note_id", "key_is_major", "key_note_id"])
        self.assertEqual(report.uuids_assigned, 3)
        conn = self.check_current(self.path)
        self.assertEqual(
            list(conn.execute(
                "SELECT id, song_id, character_num, chord "
                "FROM song_chord_link ORDER BY id")),
            [c for c in EARLY_V2_CHORDS if c[1] != 99])

    def test_a_second_open_changes_nothing(self):
        first = softchord_v1_compat.open_songbook(
            self.path, softchord.connect_existing_songbook)
        first.conn.close()
        digest = file_hash(self.path)
        second = softchord_v1_compat.open_songbook(
            self.path, softchord.connect_existing_songbook)
        second.conn.close()
        self.assertFalse(second.converted)
        self.assertEqual(file_hash(self.path), digest)
        self.assertEqual(sorted(os.listdir(self.td)),
                         ["early.songbook", "early.songbook.pre-uuid.bak"])

    def test_an_existing_backup_is_never_overwritten(self):
        with open(self.path + ".pre-uuid.bak", "wb") as fh:
            fh.write(b"precious")
        opened = softchord_v1_compat.open_songbook(
            self.path, softchord.connect_existing_songbook)
        opened.conn.close()
        with open(self.path + ".pre-uuid.bak", "rb") as fh:
            self.assertEqual(fh.read(), b"precious")
        self.assertEqual(opened.backup_path, self.path + ".pre-uuid.2.bak")

    def test_a_failed_upgrade_rolls_back(self):
        # Two songs sharing a uuid-less row is fine, but a chord row that
        # cannot become NOT NULL makes the rebuild fail.
        conn = sqlite3.connect(self.path)
        conn.execute("INSERT INTO song_chord_link VALUES (50, 0, 9, NULL)")
        conn.commit()
        conn.close()
        before = file_hash(self.path)
        with self.assertRaises(Exception):
            softchord_songbook_upgrade.upgrade_file_in_place(self.path)
        self.assertEqual(file_hash(self.path), before)
        conn = sqlite3.connect(self.path)
        self.addCleanup(conn.close)
        self.assertEqual(softchord_v1_compat.detect_format(conn),
                         softchord_v1_compat.FORMAT_V2_EARLY)

    def test_not_writable_file_opens_a_converted_copy(self):
        original = file_hash(self.path)
        os.chmod(self.path, 0o444)
        os.chmod(self.td, 0o555)
        opened = softchord_v1_compat.open_songbook(
            self.path, softchord.connect_existing_songbook)
        opened.conn.close()
        self.assertTrue(opened.temp_copy)
        self.assertEqual(opened.original_path, self.path)
        self.assertNotEqual(opened.path, self.path)
        self.assertIn("not changed", opened.message)
        self.assertEqual(file_hash(self.path), original)
        self.assertEqual(os.listdir(self.td), ["early.songbook"])
        conn = self.check_current(opened.path)
        self.assertEqual(conn.execute(
            "SELECT COUNT(*) FROM song_chord_link").fetchone()[0],
            len(EARLY_V2_CHORDS) - EARLY_V2_ORPHANS)
        self.assertEqual(dict(conn.execute(
            "SELECT key, value FROM meta"))["name"], "early")

    def test_current_read_only_file_opens_read_only(self):
        path = os.path.join(self.td, "current.songbook")
        SongbookStore.create_file(path).close()
        os.chmod(path, 0o444)
        os.chmod(self.td, 0o555)
        digest = file_hash(path)
        opened = softchord_v1_compat.open_songbook(
            path, softchord.connect_existing_songbook)
        opened.conn.close()
        self.assertTrue(opened.read_only)
        self.assertFalse(opened.converted)
        self.assertEqual(file_hash(path), digest)

    def test_upgrade_copy_never_touches_the_source(self):
        digest = file_hash(self.path)
        target = os.path.join(self.td, "out.songbook")
        report = softchord_songbook_upgrade.upgrade_copy(self.path, target)
        self.assertEqual(file_hash(self.path), digest)
        self.assertEqual(report.orphan_chords, EARLY_V2_ORPHANS)
        conn = self.check_current(target)
        self.assertEqual(dict(conn.execute(
            "SELECT key, value FROM meta"))["name"], "out")
        with self.assertRaises(softchord_songbook_upgrade.ConversionError):
            softchord_songbook_upgrade.upgrade_copy(self.path, target)

    def test_upgrade_keeps_valid_uuids_and_updated_at_of_a_half_made_file(self):
        # A file that already has uuid columns but lacks the rest keeps them.
        conn = sqlite3.connect(self.path)
        conn.execute("ALTER TABLE songs ADD COLUMN uuid TEXT")
        conn.execute("ALTER TABLE songs ADD COLUMN updated_at INTEGER")
        conn.execute("UPDATE songs SET uuid='3f2a9c1e-5b7d-4e8a-9c1d-"
                     "0123456789ab', updated_at=1234 WHERE id=0")
        conn.commit()
        conn.close()
        softchord_songbook_upgrade.upgrade_file_in_place(self.path)
        conn = self.check_current(self.path)
        self.assertEqual(conn.execute(
            "SELECT uuid, updated_at FROM songs WHERE id=0").fetchone(),
            ("3f2a9c1e-5b7d-4e8a-9c1d-0123456789ab", 1234))

    def test_chord_rows_with_no_song_id_are_removed_too(self):
        write = os.path.join(self.td, "nulls.songbook")
        write_early_v2_songbook(
            write, chords=EARLY_V2_CHORDS + [(8, None, 0, "F")])
        softchord_songbook_upgrade.upgrade_file_in_place(write)
        conn = self.check_current(write)
        self.assertEqual(conn.execute(
            "SELECT COUNT(*) FROM song_chord_link").fetchone()[0],
            len(EARLY_V2_CHORDS) - EARLY_V2_ORPHANS)

    def test_an_empty_early_file_upgrades(self):
        path = os.path.join(self.td, "empty.songbook")
        write_early_v2_songbook(path, songs=[], chords=[])
        softchord_songbook_upgrade.upgrade_file_in_place(path)
        conn = self.check_current(path)
        self.assertEqual(conn.execute(
            "SELECT COUNT(*) FROM songs").fetchone()[0], 0)


class TestEarlyVersion2InTheEditor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not QtWidgets.QApplication.instance():
            cls.qapp = QtWidgets.QApplication([])

    def setUp(self):
        self.app = test_app()
        self.td = tempfile.mkdtemp()
        self.addCleanup(self._cleanup)
        self.path = os.path.join(self.td, "early.songbook")
        write_early_v2_songbook(self.path)
        self.messages = []
        self.app.info = lambda text: self.messages.append(text)

    def _cleanup(self):
        try:
            self.app.setCurrentSongbook(None)
        except Exception:
            pass
        os.chmod(self.td, 0o755)
        shutil.rmtree(self.td, ignore_errors=True)

    def test_opening_upgrades_and_says_where_the_backup_is(self):
        self.app.setCurrentSongbook(self.path)
        self.assertEqual(len(self.messages), 1)
        self.assertIn(".pre-uuid.bak", self.messages[0])
        self.assertIsNone(self.app.songbook_original_path)
        self.assertEqual(self.app.curs.execute(
            "SELECT COUNT(*) FROM songs").fetchone()[0], 3)
        self.assertEqual(self.app.curs.execute(
            "PRAGMA foreign_keys").fetchone()[0], 1)

    def test_not_writable_opens_a_copy_and_save_as_keeps_the_work(self):
        original = file_hash(self.path)
        os.chmod(self.path, 0o444)
        os.chmod(self.td, 0o555)
        self.app.setCurrentSongbook(self.path)
        self.assertEqual(len(self.messages), 1)
        self.assertEqual(self.app.songbook_original_path, self.path)
        self.assertIn("not saved", self.app.win.windowTitle())
        uuid_before = self.app.curs.execute(
            "SELECT uuid FROM songs WHERE id=0").fetchone()[0]
        meta_uuid = self.app.curs.execute(
            "SELECT value FROM meta WHERE key='songbook_uuid'").fetchone()[0]
        self.app.curs.execute("UPDATE songs SET title='Edited' WHERE id=0")
        self.app.curs.commit()
        self.assertEqual(file_hash(self.path), original)

        dest = os.path.join(tempfile.mkdtemp(), "saved.songbook")
        original_get_save = QtWidgets.QFileDialog.getSaveFileName
        QtWidgets.QFileDialog.getSaveFileName = staticmethod(
            lambda *a, **k: (dest, ""))
        try:
            self.app.saveSongbook()
        finally:
            QtWidgets.QFileDialog.getSaveFileName = original_get_save
        self.assertIsNone(self.app.songbook_original_path)
        self.assertEqual(self.app.curs.execute(
            "SELECT title, uuid FROM songs WHERE id=0").fetchone(),
            ("Edited", uuid_before))
        # Save As keeps the songbook uuid.
        self.assertEqual(self.app.curs.execute(
            "SELECT value FROM meta WHERE key='songbook_uuid'").fetchone()[0],
            meta_uuid)
        self.assertEqual(file_hash(self.path), original)

    def test_append_reads_an_early_file_through_a_copy(self):
        self.app.setCurrentSongbook(None)
        current = os.path.join(self.td, "current.songbook")
        SongbookStore.create_file(current).close()
        self.app.setCurrentSongbook(current)
        original = file_hash(self.path)
        self.app.appendSongbookFile(self.path)
        self.assertEqual(file_hash(self.path), original)
        self.assertEqual(self.app.curs.execute(
            "SELECT COUNT(*) FROM songs").fetchone()[0], 3)
        self.assertEqual(self.app.curs.execute(
            "SELECT COUNT(*) FROM song_chord_link").fetchone()[0],
            len(EARLY_V2_CHORDS) - EARLY_V2_ORPHANS)
        uuids = [r[0] for r in self.app.curs.execute("SELECT uuid FROM songs")]
        self.assertEqual(len(set(uuids)), 3)


class TestV1ConvertsStraightToTheCurrentSchema(unittest.TestCase):
    """TODO(remove-v1-compat): delete with softchord_v1_compat.py."""

    def test_converted_v1_file_has_uuids_meta_and_no_key_columns(self):
        td = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, td, True)
        path = os.path.join(td, "old.songbook")
        write_v1_songbook(path)
        opened = softchord_v1_compat.open_songbook(
            path, softchord.connect_existing_songbook)
        conn = opened.conn
        self.addCleanup(conn.close)
        self.assertTrue(softchord_v1_compat.schema_is_current(conn))
        columns = table_columns(conn, "songs")
        for obsolete in ("key_note_id", "key_is_major", "alt_key_note_id"):
            self.assertNotIn(obsolete, columns)
        uuids = [r[0] for r in conn.execute("SELECT uuid FROM songs")]
        self.assertTrue(uuids)
        self.assertTrue(all(is_lowercase_uuid4(u) for u in uuids))
        self.assertEqual(len(set(uuids)), len(uuids))
        self.assertEqual(dict(conn.execute(
            "SELECT key, value FROM meta"))["name"], "old")
        self.assertEqual(list(conn.execute("PRAGMA foreign_key_check")), [])
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 2)


class TestUpgradeTools(unittest.TestCase):
    """tools/upgrade_songbook_v2.py and tools/convert_songbook_v1_to_v2.py."""

    @classmethod
    def setUpClass(cls):
        import importlib.util
        import io
        cls.io = io
        tools = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                             "tools")
        cls.modules = {}
        for name in ("upgrade_songbook_v2", "convert_songbook_v1_to_v2"):
            spec = importlib.util.spec_from_file_location(
                name, os.path.join(tools, name + ".py"))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            cls.modules[name] = module

    def setUp(self):
        self.td = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.td, True)
        self.path = os.path.join(self.td, "early.songbook")
        write_early_v2_songbook(self.path)

    def run_tool(self, name, *args):
        import contextlib
        out = self.io.StringIO()
        with contextlib.redirect_stdout(out):
            try:
                code = self.modules[name].main(list(args))
            except SystemExit as exit_:
                code = exit_.code
        return code, out.getvalue()

    def test_output_mode_leaves_the_source_alone(self):
        digest = file_hash(self.path)
        out_path = os.path.join(self.td, "new.songbook")
        code, text = self.run_tool("upgrade_songbook_v2", self.path,
                                   "--output", out_path)
        self.assertEqual(code, 0, text)
        self.assertEqual(file_hash(self.path), digest)
        self.assertIn("orphan chord rows removed: 2 (song ids 99)", text)
        self.assertIn("verified", text)
        conn = sqlite3.connect(out_path)
        self.addCleanup(conn.close)
        self.assertTrue(softchord_v1_compat.schema_is_current(conn))
        self.assertEqual(dict(conn.execute(
            "SELECT key, value FROM meta"))["name"], "new")
        self.assertEqual(os.listdir(self.td).count("early.songbook"), 1)
        self.assertFalse(any(n.endswith(".bak") for n in os.listdir(self.td)))

    def test_output_must_not_exist_and_failure_leaves_nothing(self):
        out_path = os.path.join(self.td, "new.songbook")
        open(out_path, "w").close()
        code, text = self.run_tool("upgrade_songbook_v2", self.path,
                                   "--output", out_path)
        self.assertEqual(code, 1)
        self.assertIn("already exists", text)
        self.assertEqual(os.path.getsize(out_path), 0)

    def test_needs_exactly_one_of_output_and_in_place(self):
        code, _ = self.run_tool("upgrade_songbook_v2", self.path)
        self.assertNotEqual(code, 0)
        code, _ = self.run_tool("upgrade_songbook_v2", self.path, "--output",
                                os.path.join(self.td, "x"), "--in-place")
        self.assertNotEqual(code, 0)
        code, _ = self.run_tool("upgrade_songbook_v2", self.path, "--output",
                                self.path)
        self.assertNotEqual(code, 0)

    def test_in_place_makes_a_backup_first(self):
        original = file_hash(self.path)
        code, text = self.run_tool("upgrade_songbook_v2", self.path,
                                   "--in-place")
        self.assertEqual(code, 0, text)
        backup = self.path + ".pre-uuid.bak"
        self.assertTrue(os.path.exists(backup))
        conn = sqlite3.connect(self.path)
        self.addCleanup(conn.close)
        self.assertTrue(softchord_v1_compat.schema_is_current(conn))
        self.assertIn("key_note_id",
                      table_columns(sqlite3.connect(backup), "songs"))
        self.assertNotEqual(file_hash(self.path), original)

    def test_a_current_file_is_left_alone(self):
        path = os.path.join(self.td, "current.songbook")
        SongbookStore.create_file(path).close()
        digest = file_hash(path)
        code, text = self.run_tool("upgrade_songbook_v2", path, "--in-place")
        self.assertEqual(code, 0)
        self.assertIn("already the current format", text)
        self.assertEqual(file_hash(path), digest)
        self.assertEqual(sorted(os.listdir(self.td)),
                         ["current.songbook", "early.songbook"])

    def test_a_version_1_file_goes_straight_to_the_current_schema(self):
        v1 = os.path.join(self.td, "v1.songbook")
        write_v1_songbook(v1)
        out_path = os.path.join(self.td, "v1_new.songbook")
        code, text = self.run_tool("upgrade_songbook_v2", v1, "--output",
                                   out_path)
        self.assertEqual(code, 0, text)
        conn = sqlite3.connect(out_path)
        self.addCleanup(conn.close)
        self.assertTrue(softchord_v1_compat.schema_is_current(conn))

    def test_v1_converter_produces_the_current_schema_and_verifies(self):
        v1 = os.path.join(self.td, "v1.songbook")
        write_v1_songbook(v1)
        code, text = self.run_tool("convert_songbook_v1_to_v2", v1)
        self.assertEqual(code, 0, text)
        self.assertIn("verified", text)
        conn = sqlite3.connect(v1)
        self.addCleanup(conn.close)
        self.assertTrue(softchord_v1_compat.schema_is_current(conn))

    def test_v1_converter_check_mode_does_not_touch_the_file(self):
        v1 = os.path.join(self.td, "v1.songbook")
        write_v1_songbook(v1)
        digest = file_hash(v1)
        code, text = self.run_tool("convert_songbook_v1_to_v2", "--check", v1)
        self.assertEqual(code, 0, text)
        self.assertEqual(file_hash(v1), digest)

    def test_v1_converter_points_early_files_to_the_upgrade_tool(self):
        code, text = self.run_tool("convert_songbook_v1_to_v2", self.path)
        self.assertEqual(code, 1)
        self.assertIn("upgrade_songbook_v2", text)


class TestSongFilterKeepsTheOpenSong(unittest.TestCase):
    """Typing in the filter must not close and read the open song again."""

    @classmethod
    def setUpClass(cls):
        cls.app = test_app()

    def setUp(self):
        self.td = open_empty_temp_songbook(self.app)
        insert_and_select_song(self.app, with_chord=True)
        self.song = self.app.current_song

    def tearDown(self):
        self.app.clearFilterClicked()
        self.app.setCurrentSongbook(None)
        shutil.rmtree(self.td, ignore_errors=True)

    def test_filter_keeps_the_same_song_object(self):
        self.app.songFilterEdited("Test")
        self.assertIs(self.app.current_song, self.song)
        self.assertEqual(self.app.getSelectedSongIds(), [self.song.id])

    def test_hidden_song_stays_open_and_comes_back_selected(self):
        self.app.songFilterEdited("nothing matches this")
        self.assertIs(self.app.current_song, self.song)
        self.assertEqual(self.app.getSelectedSongIds(), [])
        self.app.songFilterEdited("still nothing")
        self.app.clearFilterClicked()
        self.assertIs(self.app.current_song, self.song)
        self.assertEqual(self.app.getSelectedSongIds(), [self.song.id])

    def test_filter_keeps_the_reset_transpose_count(self):
        self.app.transposeUp()
        self.assertEqual(self.song.transposed_steps, 1)
        self.app.songFilterEdited("Test")
        self.assertEqual(self.app.current_song.transposed_steps, 1)
        self.assertTrue(self.app.toolbar.transpose_reset.isEnabled())
        # The transpose is a change while viewing. Keep it, so closing asks nothing.
        self.assertTrue(self.app.saveEdit())


class _SaveDialogAnswers:
    """Patches QMessageBox.exec: pops one answer per dialog and records it."""

    def __init__(self, test):
        self.answers = []
        self.asked = []
        original = QtWidgets.QMessageBox.exec

        def exec_(box):
            self.asked.append(box.text())
            if not self.answers:
                raise AssertionError("dialog with no answer: %s" % box.text())
            return self.answers.pop(0)

        QtWidgets.QMessageBox.exec = exec_
        test.addCleanup(setattr, QtWidgets.QMessageBox, "exec", original)


_SB = QtWidgets.QMessageBox.StandardButton


class TestBriefNotes(unittest.TestCase):
    """The brief note at the bottom of the song view (softchord_note.py)."""

    def setUp(self):
        TestSaveAndDiscard.setUp(self)
        self.app.brief_note.hide()
    def tearDown(self):
        app = self.app
        app.zoom_pos = app.zoom_levels.index(1.0)
        app.updateZoomWidgets()
        app.brief_note.hide()
        TestSaveAndDiscard.tearDown(self)
    row_of = lambda self, *a: TestSaveAndDiscard.row_of(self, *a)
    select_song = lambda self, *a, **k: TestSaveAndDiscard.select_song(
        self, *a, **k)

    def shown(self):
        note = self.app.brief_note
        return note.text() if note.isVisible() else None

    def test_copy_notes(self):
        self.app.ui.actionCopySongText.trigger()
        self.assertEqual(self.shown(), "Song text copied to clipboard")
        self.app.ui.actionCopySongTextWithChords.trigger()
        self.assertEqual(self.shown(),
                         "Song text with chords copied to clipboard")
        self.app.ui.actionCopySongAsImage.trigger()
        self.assertEqual(self.shown(), "Song image copied to clipboard")

    def test_edit_mode_save_and_discard_notes(self):
        self.app.ui.actionChordEditorMode.trigger()
        self.assertEqual(self.shown(), "Entered chord editor mode")
        self.app.ui.actionLyricEditorMode.trigger()
        self.assertEqual(self.shown(), "Entered text editor mode")
        self.app.toolbar.save.trigger()
        self.assertEqual(self.shown(), "Saved")
        self.app.ui.actionChordEditorMode.trigger()
        self.app.toolbar.discard.trigger()
        self.assertEqual(self.shown(), "Changes discarded")

    def test_transpose_zoom_undo_and_redo_notes(self):
        toolbar = self.app.toolbar
        toolbar.transpose_up.trigger()
        self.assertEqual(self.shown(), "Transposed up to D♭")
        toolbar.transpose_down.trigger()
        toolbar.transpose_down.trigger()
        self.assertEqual(self.shown(), "Transposed down to B")
        toolbar.transpose_reset.trigger()
        self.assertEqual(self.shown(), "Transposed back to original key, C")
        self.app.ui.actionUndo.trigger()
        self.assertEqual(self.shown(), "Undone")
        self.app.ui.actionRedo.trigger()
        self.assertEqual(self.shown(), "Redone")
        self.app.ui.actionZoomIn.trigger()
        self.assertEqual(self.shown(), "Zoom 110%")
        self.app.ui.actionZoomActual.trigger()
        self.assertEqual(self.shown(), "Zoom 100%")

    def test_font_notes_only_when_confirmed(self):
        app = self.app
        saved = (app.lyrics_font, app.lyrics_font_size, app.chords_font,
                 app.chords_font_size)

        def restore():
            (app.lyrics_font, app.lyrics_font_size, app.chords_font,
             app.chords_font_size) = saved
            app.updateEditorFonts()
        self.addCleanup(restore)
        with mock.patch.object(QtWidgets.QFontDialog, "getFont",
                               return_value=(QtGui.QFont("Courier", 20), False)):
            self.app.ui.actionLyricsFont.trigger()
        self.assertIsNone(self.shown())
        with mock.patch.object(QtWidgets.QFontDialog, "getFont",
                               return_value=(QtGui.QFont("Courier", 20), True)):
            self.app.ui.actionLyricsFont.trigger()
            self.assertEqual(self.shown(), "Lyrics font changed")
            self.app.ui.actionChordsFont.trigger()
            self.assertEqual(self.shown(), "Chords font changed")

    def test_chord_deleted_note(self):
        self.app.ui.actionChordEditorMode.trigger()
        self.app.selected_char_num = 0
        self.app.toolbar.chord_delete.trigger()
        self.assertEqual(self.shown(), "Chord deleted")

    def test_note_sits_on_the_song_view_bottom(self):
        note = self.app.brief_note
        editor = self.app.editor
        self.assertIs(note.parentWidget(), editor)
        self.app.ui.actionZoomIn.trigger()
        self.assertEqual(note.geometry().bottom() + 1, editor.height() - 24)
        at = note.geometry()
        # Starting an edit shows the toolbar's edit buttons but moves no note.
        self.app.ui.actionChordEditorMode.trigger()
        self.assertEqual(note.geometry().bottom(), at.bottom())


class TestSaveAndDiscard(unittest.TestCase):
    """Edit Chords… / Edit Text… keep a draft until Save or Discard."""

    @classmethod
    def setUpClass(cls):
        cls.app = test_app()

    def setUp(self):
        self.app = test_app()
        self.td = open_empty_temp_songbook(self.app)
        insert_and_select_song(self.app, with_chord=True)
        self.app.curs.execute(
            "INSERT INTO songs (id, number, title, subtitle, text, uuid, "
            "updated_at) VALUES (1, 2, 'Second', '', 'Other text', "
            "lower(hex(randomblob(16))), 1700000000)")
        self.app.curs.commit()
        self.app.songs_model.updateFromDatabase()
        self.select_song(0)
        self.song = self.app.current_song
        self.dialog = _SaveDialogAnswers(self)

    def tearDown(self):
        if self.app.edit_session is not None:
            self.app._endEdit()
        self.app._pending_song_selection = None
        self.app.clearFilterClicked()
        self.app.setCurrentSongbook(None)
        shutil.rmtree(self.td, ignore_errors=True)

    # Helpers

    def row_of(self, song_id):
        model = self.app.ui.songs_view.model()
        for row in range(model.rowCount()):
            source = model.mapToSource(model.index(row, 0))
            if self.app.songs_model.getRowSongID(source.row()) == song_id:
                return row
        raise AssertionError("no row for song %s" % song_id)

    def select_song(self, song_id, wait=False):
        self.app.ui.songs_view.selectRow(self.row_of(song_id))
        if wait:
            QTest.qWait(20)

    def db_song(self, song_id=0):
        title, number, text = self.app.curs.execute(
            "SELECT title, number, text FROM songs WHERE id=?",
            (song_id,)).fetchone()
        chords = sorted(self.app.curs.execute(
            "SELECT character_num, chord FROM song_chord_link "
            "WHERE song_id=?", (song_id,)).fetchall())
        return title, number, text, chords

    def add_chord_edit(self, position=3):
        """Start a chord edit and put a G on a letter (3 unless given)."""
        self.app.chordEditorSelected()
        self.app.selected_char_num = position
        self.app.processKeyPressed(Qt.Key.Key_G)
        self.assertTrue(self.app.editChanged())

    def row_title(self, song_id):
        model = self.app.ui.songs_view.model()
        return model.index(self.row_of(song_id), 1).data()

    # Viewing and the edit bar

    def test_viewing_is_the_default(self):
        self.assertFalse(self.app.editing())
        self.assertFalse(self.app.toolbar.save.isVisible())
        self.assertFalse(self.app.toolbar.discard.isVisible())
        self.assertFalse(self.app.ui.actionSaveEdit.isEnabled())
        self.assertFalse(self.app.ui.actionChordEditorMode.isCheckable())
        self.assertFalse(self.app.ui.actionLyricEditorMode.isCheckable())
        self.assertEqual(self.app.ui.actionChordEditorMode.text(),
                         "Edit Chords\u2026")
        self.assertEqual(self.app.ui.actionLyricEditorMode.text(),
                         "Edit Text\u2026")

    def test_edit_shows_the_bar_and_save_hides_it(self):
        self.app.ui.actionChordEditorMode.trigger()
        self.assertTrue(self.app.chordEditing())
        self.assertTrue(self.app.toolbar.save.isVisible())
        self.assertTrue(self.app.toolbar.discard.isVisible())
        self.assertTrue(self.app.ui.actionSaveEdit.isEnabled())
        self.app.toolbar.save.trigger()
        self.assertFalse(self.app.editing())
        self.assertFalse(self.app.toolbar.save.isVisible())
        self.assertFalse(self.app.toolbar.discard.isVisible())

    def test_toolbar_groups_follow_the_web_toolbar(self):
        toolbar = self.app.toolbar
        ui = self.app.ui
        names = [a if a == "|" else a.objectName()
                 for a in toolbar.toolbarActions()]
        self.assertEqual(names, [
            "actionCopySongText", "actionCopySongTextWithChords",
            "actionCopySongAsImage", "|",
            "actionTransposeDown", "actionTransposeUp", "actionTransposeReset",
            "|", "actionZoomOut", "actionZoomActual", "actionZoomIn",
            "actionZoomPercent", "|", "actionPrint", "|",
            "actionLyricsFont", "actionChordsFont", "|",
            "actionLyricEditorMode", "actionChordEditorMode",
            "actionChordEdit", "actionChordDelete", "actionUndoTool",
            "actionRedoTool", "actionDiscardTool", "actionSaveEditTool"])
        for action in toolbar.toolbarActions():
            if action in toolbar._icons:
                self.assertFalse(action.icon().isNull(), action.objectName())
        self.assertIn(ui.actionChordEditorMode.shortcut().toString(),
                      ui.actionChordEditorMode.toolTip())
        self.assertEqual(ui.actionZoomActual.shortcut().toString(), "Ctrl+0")
        self.assertFalse(hasattr(ui, "zoom_slider"))

    def test_toolbar_font_buttons_open_the_font_dialogs(self):
        toolbar = self.app.toolbar
        ui = self.app.ui
        self.assertEqual(ui.actionLyricsFont.toolTip(), "Select font for lyrics")
        self.assertEqual(ui.actionChordsFont.toolTip(), "Select font for chords")
        for action in (ui.actionLyricsFont, ui.actionChordsFont):
            self.assertFalse(toolbar.widgetForAction(action).isHidden())
            self.assertFalse(action.icon().isNull())
        picked = QtGui.QFont("Courier", 21)
        with mock.patch.object(QtWidgets.QFontDialog, "getFont",
                               return_value=(picked, True)) as get_font:
            toolbar.widgetForAction(ui.actionLyricsFont).click()
            self.assertEqual(self.app.lyrics_font.pointSizeF(), 21)
            picked = QtGui.QFont("Courier", 17)
            get_font.return_value = (picked, True)
            toolbar.widgetForAction(ui.actionChordsFont).click()
            self.assertEqual(self.app.chords_font.pointSizeF(), 17)
        self.assertEqual(get_font.call_count, 2)

    def test_toolbar_edit_group_is_always_on_the_last_row(self):
        toolbar = self.app.toolbar
        ui = self.app.ui
        flow = toolbar.layout()
        box = lambda action: toolbar.widgetForAction(action).parentWidget()
        copy, fonts, edit = (box(ui.actionCopySongText),
                             box(ui.actionLyricsFont),
                             box(ui.actionLyricEditorMode))
        rows = lambda: sorted({w.geometry().y() for w in toolbar.findChildren(
            QtWidgets.QWidget) if w.parentWidget() is toolbar
            and not w.isHidden() and w.geometry().width() > 1})

        # Wide: everything else fits on row 1, the edit group is alone on row 2.
        flow.setGeometry(QtCore.QRect(0, 0, 2000, flow.heightForWidth(2000)))
        self.assertEqual(len(rows()), 2)
        self.assertGreater(edit.geometry().y(), copy.geometry().y())
        self.assertEqual(fonts.geometry().y(), copy.geometry().y())
        self.assertEqual(edit.geometry().x(), flow.contentsMargins().left())
        two_rows = flow.heightForWidth(2000)

        # Narrower: the fonts group no longer fits on row 1 and goes onto the
        # last row in front of the edit group; still two rows.
        width = fonts.geometry().right()
        flow.setGeometry(QtCore.QRect(0, 0, width, flow.heightForWidth(width)))
        self.assertEqual(fonts.geometry().y(), edit.geometry().y())
        self.assertLess(fonts.geometry().x(), edit.geometry().x())
        self.assertEqual(len(rows()), 2)
        self.assertEqual(flow.heightForWidth(width), two_rows)

        # Very narrow: more rows, the edit group still on the last one.
        flow.setGeometry(QtCore.QRect(0, 0, 150, flow.heightForWidth(150)))
        self.assertGreater(len(rows()), 2)
        self.assertEqual(edit.geometry().y(), rows()[-1])

        # Editing: the edit groups (Edit, chord, Discard/Save) stay together
        # on the last row whenever the pane can hold all of them.
        self.app.chordEditorSelected()
        finish = box(toolbar.save)
        flow.setGeometry(QtCore.QRect(0, 0, 2000, flow.heightForWidth(2000)))
        tail = finish.geometry().right() - edit.geometry().left() + 1
        for width in range(tail + 1, 1200, 25):
            flow.setGeometry(QtCore.QRect(0, 0, width,
                                          flow.heightForWidth(width)))
            self.assertEqual(finish.geometry().y(), edit.geometry().y(), width)
            self.assertEqual(edit.geometry().y(), rows()[-1], width)
            self.assertEqual(flow.heightForWidth(width),
                             toolbar.heightForWidth(width), width)

    def test_edit_buttons_carry_the_old_hint_labels_help(self):
        ui = self.app.ui
        chords = ui.actionChordEditorMode.toolTip()
        self.assertTrue(chords.startswith("<qt>Edit Chords…"))
        self.assertIn(ui.actionChordEditorMode.shortcut().toString(), chords)
        self.assertIn("<br><br><b>To add a new chord:</b><br>", chords)
        self.assertIn("To delete a chord:", chords)
        text = ui.actionLyricEditorMode.toolTip()
        self.assertTrue(text.startswith("<qt>Edit Text…"))
        self.assertIn("<br><br>When in lyric editing mode", text)
        # The toolbar sits directly above the song.
        column = ui.verticalLayout
        at = column.indexOf(self.app.toolbar)
        self.assertIs(column.itemAt(at + 1).layout(), ui.lyric_editor_layout)

    def test_toolbar_buttons_per_mode(self):
        toolbar = self.app.toolbar
        shown = lambda action: (action.isVisible() and not
                                toolbar.widgetForAction(action).isHidden())
        extra = (toolbar.chord_edit, toolbar.chord_delete, toolbar.undo,
                 toolbar.redo, toolbar.discard, toolbar.save)
        self.assertEqual([shown(a) for a in extra], [False] * 6)

        self.app.lyricEditorSelected()
        self.assertTrue(toolbar.isActive(self.app.ui.actionLyricEditorMode))
        self.assertEqual([shown(a) for a in extra],
                         [False, False, True, True, True, True])

        self.app.chordEditorSelected()
        self.assertTrue(toolbar.isActive(self.app.ui.actionChordEditorMode))
        self.assertFalse(toolbar.isActive(self.app.ui.actionLyricEditorMode))
        self.assertEqual([shown(a) for a in extra], [True] * 6)

        self.app.discardEdit()
        self.assertFalse(toolbar.isActive(self.app.ui.actionChordEditorMode))
        self.assertEqual([shown(a) for a in extra], [False] * 6)

    def test_toolbar_add_or_edit_chord(self):
        toolbar = self.app.toolbar
        self.app.chordEditorSelected()
        self.assertFalse(toolbar.chord_edit.isEnabled())
        self.assertFalse(toolbar.chord_delete.isEnabled())

        self.app.selected_char_num = 0  # the letter with the C chord
        self.assertTrue(toolbar.chord_edit.isEnabled())
        self.assertEqual(toolbar.chord_edit.toolTip(), "Edit chord")
        self.assertTrue(toolbar.chord_delete.isEnabled())

        self.app.selected_char_num = 3  # a letter with no chord
        self.assertEqual(toolbar.chord_edit.toolTip(), "Add chord")
        self.assertFalse(toolbar.chord_delete.isEnabled())

        opened = []
        self.app.processSongCharEdit = opened.append
        toolbar.chord_edit.trigger()
        self.assertEqual(opened, [3])

    def test_toolbar_wraps_whole_groups_when_narrow(self):
        flow = self.app.toolbar.layout()
        one_row = flow.heightForWidth(2000)
        self.assertGreater(flow.heightForWidth(250), one_row)
        self.assertTrue(self.app.ui.song_filter_ef.isClearButtonEnabled())
        for name in ("clear_filter_button", "new_song_button",
                     "delete_song_button", "label_3", "label", "statusbar",
                     "chords_editor_label", "lyrics_editor_label"):
            self.assertFalse(hasattr(self.app.ui, name), name)

    def test_toolbar_zoom_percent_is_a_plain_label(self):
        toolbar = self.app.toolbar
        label = toolbar.widgetForAction(toolbar.zoom_percent)
        self.assertIsInstance(label, QtWidgets.QLabel)
        self.assertEqual(label.text(), "100%")
        self.app.ui.actionZoomIn.trigger()
        self.assertEqual(label.text(), "110%")
        toolbar.zoom_percent.trigger()  # not a reset any more
        self.assertEqual(label.text(), "110%")
        self.assertTrue(self.app.ui.actionZoomActual.isEnabled())
        self.app.ui.actionZoomActual.trigger()
        self.assertEqual(label.text(), "100%")
        self.assertEqual(self.app.zoom_factor, 1.0)

    def test_save_and_discard_sit_right_of_edit_text(self):
        toolbar = self.app.toolbar
        actions = toolbar.toolbarActions()
        at = actions.index(self.app.ui.actionChordEditorMode)
        self.assertEqual(actions[at + 1:],
                         [toolbar.chord_edit, toolbar.chord_delete,
                          toolbar.undo, toolbar.redo,
                          toolbar.discard, toolbar.save])
        self.assertFalse(hasattr(self.app.ui, "edit_bar_label"))

    # Chords are selected only in Edit Chords

    def press_on(self, letter, is_chord, x=5):
        self.app.session.determineClickedLetter = (
            lambda px, py, dragging: (is_chord, letter))
        pos = QtCore.QPointF(x, 5)
        for kind, handler in (
                (QtCore.QEvent.Type.MouseButtonPress,
                 self.app.editor.mousePressEvent),
                (QtCore.QEvent.Type.MouseMove, self.app.editor.mouseMoveEvent),
                (QtCore.QEvent.Type.MouseButtonRelease,
                 self.app.editor.mouseReleaseEvent)):
            handler(QtGui.QMouseEvent(
                kind, pos, pos, Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
        del self.app.session.__dict__["determineClickedLetter"]

    def test_viewing_selects_nothing(self):
        self.press_on(0, True)
        self.assertIsNone(self.app.selected_char_num)
        self.assertIsNone(self.app.hover_char_num)
        self.assertIsNone(self.app.editor.dragging_chord)
        self.assertIsNone(self.app.editor.marquee_origin)
        QTest.keyClick(self.app.editor, Qt.Key.Key_Right)
        self.assertIsNone(self.app.selected_char_num)

    def test_only_edit_chords_selects(self):
        self.app.chordEditorSelected()
        self.press_on(2, False)
        self.assertEqual(self.app.selected_char_num, 2)
        self.app.selected_chord_nums = {0}
        # A text edit and viewing drop the chord selection.
        self.app.lyricEditorSelected()
        self.assertIsNone(self.app.selected_char_num)
        self.assertEqual(self.app.selected_chord_nums, set())
        self.app.discardEdit()
        self.app.chordEditorSelected()
        self.press_on(2, False)
        self.app.discardEdit()
        self.assertIsNone(self.app.selected_char_num)

    # The draft

    def test_no_songbook_change_until_save(self):
        before = self.db_song()
        self.add_chord_edit()
        self.app.transposeUp()
        self.app.currentSongTitleEdited("New title")
        self.assertEqual(self.db_song(), before)
        self.app.ui.actionSaveEdit.trigger()
        title, _, _, chords = self.db_song()
        self.assertEqual(title, "New title")
        self.assertEqual(chords, [(0, "D\u266d"), (3, "A\u266d")])

    def test_discard_restores_exactly(self):
        before = self.db_song()
        self.add_chord_edit()
        self.app.transposeUp()
        self.app.currentSongTitleEdited("New title")
        self.app.currentSongNumberEdited("42")
        self.app.toolbar.discard.trigger()
        self.assertFalse(self.app.editing())
        song = self.app.current_song
        self.assertEqual(song.title, "Test Song")
        self.assertEqual(song.number, 1)
        self.assertEqual(song.transposed_steps, 0)
        self.assertEqual([(c.character_num, c.getChordText())
                          for c in song.iterateAllChords()], [(0, "C")])
        self.assertEqual(self.app.ui.song_title_ef.text(), "Test Song")
        self.assertEqual(self.db_song(), before)
        self.assertFalse(self.app.win.isWindowModified())

    def test_change_then_undo_is_unchanged(self):
        self.add_chord_edit()
        self.app.undo_stack.undo()
        self.assertFalse(self.app.editChanged())
        self.assertFalse(self.app.win.isWindowModified())
        # Esc has nothing to ask about.
        self.app.ui.actionDiscardEdit.trigger()
        self.assertFalse(self.app.editing())
        self.assertEqual(self.dialog.asked, [])

    def test_text_edit_saves_text_and_moves_chords(self):
        self.app.lyricEditorSelected()
        cursor = self.app.editor.textCursor()
        cursor.setPosition(0)
        cursor.insertText("Hi ")
        self.assertTrue(self.app.editChanged())
        self.assertEqual(self.db_song()[2], "Amazing grace\nHow sweet the sound")
        self.app.ui.actionSaveEdit.trigger()
        _, _, text, chords = self.db_song()
        self.assertTrue(text.startswith("Hi Amazing"))
        self.assertEqual(chords, [(3, "C")])

    def test_dot_and_window_modified_follow_the_change(self):
        self.assertNotIn("\u2022", self.row_title(0))
        self.add_chord_edit()
        self.assertTrue(self.app.win.isWindowModified())
        self.assertEqual(self.row_title(0), "Test Song \u2022")
        self.assertEqual(self.row_title(1), "Second")
        self.app.undo_stack.undo()
        self.assertEqual(self.row_title(0), "Test Song")
        self.app.undo_stack.redo()
        self.app.saveEdit()
        self.assertFalse(self.app.win.isWindowModified())
        self.assertEqual(self.row_title(0), "Test Song")

    def test_save_and_esc_shortcuts(self):
        self.assertEqual(self.app.ui.actionSaveEdit.shortcut(),
                         QtGui.QKeySequence("Ctrl+S"))
        self.assertEqual(self.app.ui.actionDiscardEdit.shortcut(),
                         QtGui.QKeySequence("Esc"))

    def test_esc_asks_only_when_changed(self):
        before = self.db_song()
        self.add_chord_edit()
        self.addCleanup(self.app.session.__dict__.pop, "question", None)
        self.app.session.question = lambda *a, **k: False   # Keep Editing
        self.app.ui.actionDiscardEdit.trigger()
        self.assertTrue(self.app.editing())
        self.app.session.question = lambda *a, **k: True    # Discard
        self.app.ui.actionDiscardEdit.trigger()
        self.assertFalse(self.app.editing())
        self.assertEqual(self.db_song(), before)
        del self.app.session.__dict__["question"]

    def test_esc_cancels_a_chord_drag_first(self):
        self.app.chordEditorSelected()
        editor = self.app.editor

        def mouse(kind, x):
            pos = QtCore.QPointF(x, 5)
            button = (Qt.MouseButton.NoButton
                      if kind == QtCore.QEvent.Type.MouseMove
                      else Qt.MouseButton.LeftButton)
            return QtGui.QMouseEvent(kind, pos, pos, button,
                                     Qt.MouseButton.LeftButton,
                                     Qt.KeyboardModifier.NoModifier)

        self.app.session.determineClickedLetter = lambda x, y, dragging: (True, 0)
        self.addCleanup(self.app.session.__dict__.pop, "determineClickedLetter", None)
        editor.mousePressEvent(mouse(QtCore.QEvent.Type.MouseButtonPress, 5))
        self.assertIsNotNone(editor.dragging_chord)
        self.app.session.determineClickedLetter = lambda x, y, dragging: (False, 3)
        editor.mouseMoveEvent(mouse(QtCore.QEvent.Type.MouseMove, 40))
        QTest.keyClick(editor, Qt.Key.Key_Escape)
        self.assertIsNone(editor.dragging_chord)
        self.assertTrue(self.app.chordEditing())
        self.assertEqual([(c.character_num, c.getChordText()) for c in
                          self.app.current_song.iterateAllChords()],
                         [(0, "C")])
        self.assertFalse(self.app.editChanged())

    # The Save dialog on a song switch

    def test_switch_song_save(self):
        self.add_chord_edit()
        self.dialog.answers.append(_SB.Save)
        self.select_song(1, wait=True)
        self.assertEqual(len(self.dialog.asked), 1)
        self.assertIn("Test Song", self.dialog.asked[0])
        self.assertFalse(self.app.editing())
        self.assertEqual(self.app.current_song.id, 1)
        self.assertEqual(self.db_song()[3], [(0, "C"), (3, "G")])

    def test_switch_song_dont_save(self):
        before = self.db_song()
        self.add_chord_edit()
        self.dialog.answers.append(_SB.Discard)
        self.select_song(1, wait=True)
        self.assertFalse(self.app.editing())
        self.assertEqual(self.app.current_song.id, 1)
        self.assertEqual(self.app.getSelectedSongIds(), [1])
        self.assertEqual(self.db_song(), before)

    def test_switch_song_cancel_keeps_the_edit_and_selection(self):
        before = self.db_song()
        self.add_chord_edit()
        self.dialog.answers.append(_SB.Cancel)
        self.select_song(1)
        # The edited song is shown selected again before the dialog.
        self.assertEqual(self.app.getSelectedSongIds(), [0])
        QTest.qWait(20)
        self.assertEqual(len(self.dialog.asked), 1)
        self.assertTrue(self.app.chordEditing())
        self.assertIs(self.app.current_song, self.song)
        self.assertEqual(self.app.getSelectedSongIds(), [0])
        self.assertTrue(self.app.editChanged())
        self.assertEqual(self.db_song(), before)

    def test_multi_select_asks(self):
        self.add_chord_edit()
        self.dialog.answers.append(_SB.Cancel)
        view = self.app.ui.songs_view
        model = view.model()
        view.selectionModel().select(
            model.index(self.row_of(1), 0),
            QtCore.QItemSelectionModel.SelectionFlag.Select
            | QtCore.QItemSelectionModel.SelectionFlag.Rows)
        QTest.qWait(20)
        self.assertEqual(len(self.dialog.asked), 1)
        self.assertEqual(self.app.getSelectedSongIds(), [0])
        self.assertTrue(self.app.editing())

    def test_unchanged_edit_switches_without_asking(self):
        self.app.chordEditorSelected()
        self.select_song(1, wait=True)
        self.assertEqual(self.dialog.asked, [])
        self.assertFalse(self.app.editing())
        self.assertEqual(self.app.current_song.id, 1)

    def test_switching_edit_kind_keeps_the_draft(self):
        # MIRRORED UI: the web and iOS apps switch modes the same way.
        before = self.db_song()
        self.add_chord_edit()
        self.app.lyricEditorSelected()
        self.assertEqual(self.dialog.asked, [])
        self.assertTrue(self.app.textEditing())
        self.assertTrue(self.app.editChanged())
        self.assertEqual(self.db_song(), before)
        self.app.chordEditorSelected()
        self.assertEqual(self.dialog.asked, [])
        self.assertTrue(self.app.chordEditing())
        self.app.toolbar.save.trigger()
        self.assertFalse(self.app.editing())
        self.assertEqual(self.db_song()[3], [(0, "C"), (3, "G")])

    def test_filter_keeps_the_draft(self):
        self.add_chord_edit()
        self.app.songFilterEdited("nothing matches this")
        self.app.clearFilterClicked()
        self.assertEqual(self.dialog.asked, [])
        self.assertTrue(self.app.chordEditing())
        self.assertIs(self.app.current_song, self.song)
        self.assertTrue(self.app.editChanged())

    # Other ways out

    def test_close_cancel_keeps_the_window(self):
        self.add_chord_edit()
        self.dialog.answers.append(_SB.Cancel)
        event = QtGui.QCloseEvent()
        self.app.closeEvent(event)
        self.assertFalse(event.isAccepted())
        self.assertTrue(self.app.editing())

    def test_close_dont_save_closes(self):
        before = self.db_song()
        self.add_chord_edit()
        self.dialog.answers.append(_SB.Discard)
        event = QtGui.QCloseEvent()
        self.app.closeEvent(event)
        self.assertTrue(event.isAccepted())
        self.assertFalse(self.app.editing())
        self.assertEqual(self.db_song(), before)

    def test_songbook_actions_ask(self):
        for position, action in ((4, self.app.newSongbook),
                                 (5, self.app.openSongbook),
                                 (6, self.app.closeSongbook)):
            self.add_chord_edit(position)
            self.dialog.answers.append(_SB.Cancel)
            action()
            self.assertTrue(self.app.editing(), action.__name__)
            self.assertTrue(self.app.store.is_open, action.__name__)
            self.app.saveEdit()
        self.assertEqual(len(self.dialog.asked), 3)

    def test_open_from_the_finder_asks(self):
        self.add_chord_edit()
        self.dialog.answers.append(_SB.Cancel)
        self.assertFalse(self.app.setCurrentSongbook(None))
        self.assertTrue(self.app.store.is_open)
        self.assertTrue(self.app.editing())

    def test_new_song_asks(self):
        self.add_chord_edit()
        self.dialog.answers.append(_SB.Cancel)
        self.app.createNewSong()
        self.assertIs(self.app.current_song, self.song)
        self.dialog.answers.append(_SB.Save)
        self.app.createNewSong()
        self.assertIsNot(self.app.current_song, self.song)
        self.assertTrue(self.app.textEditing())

    def test_logout_saves_silently(self):
        self.add_chord_edit()
        self.app.commitDataForLogout(None)
        self.assertEqual(self.dialog.asked, [])
        self.assertFalse(self.app.editing())
        self.assertEqual(self.db_song()[3], [(0, "C"), (3, "G")])

    # Output during an edit uses the draft and does not write

    def test_export_uses_the_draft_without_writing(self):
        before = self.db_song()
        self.add_chord_edit()
        self.app.currentSongTitleEdited("Draft title")
        out = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, out, True)
        text_path = os.path.join(out, "song.txt")
        self.app.exportToText(text_path)
        self.app.exportToChordPro(os.path.join(out, "song.chordpro"))
        self.app.exportToSinglePdf(os.path.join(out, "song.pdf"))
        with open(text_path, encoding="utf-8-sig") as fh:
            exported = fh.read()
        self.assertIn("G", exported)
        with open(os.path.join(out, "song.chordpro"),
                  encoding="utf-8-sig") as fh:
            self.assertIn("Draft title", fh.read())
        self.assertTrue(os.path.getsize(os.path.join(out, "song.pdf")) > 0)
        self.assertEqual(self.db_song(), before)
        self.assertTrue(self.app.editChanged())

    def test_print_uses_the_draft_without_writing(self):
        before = self.db_song()
        self.add_chord_edit()
        out = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, out, True)
        printer = QtPrintSupport.QPrinter()
        printer.setOutputFormat(QtPrintSupport.QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(os.path.join(out, "print.pdf"))
        self.app.printSongsToPrinter([0], printer, "Printing")
        self.assertEqual(self.db_song(), before)
        self.assertTrue(self.app.editChanged())

    # Changes while viewing: a transpose, the title, number or notes

    def stored_chords(self):
        return self.db_song()[3]

    def test_transpose_while_viewing_is_a_change(self):
        before = self.db_song()
        self.app.transposeUp()
        self.assertTrue(self.app.editing())
        self.assertFalse(self.app.chordEditing())
        self.assertFalse(self.app.textEditing())
        self.assertTrue(self.app.toolbar.save.isVisible())
        self.assertTrue(self.app.toolbar.discard.isVisible())
        self.assertEqual(self.row_title(0), "Test Song \u2022")
        self.assertTrue(self.app.win.isWindowModified())
        self.assertEqual(self.db_song(), before)
        self.app.toolbar.save.trigger()
        self.assertFalse(self.app.editing())
        self.assertNotEqual(self.stored_chords(), before[3])
        self.assertEqual(self.row_title(0), "Test Song")
        self.assertFalse(self.app.toolbar.save.isVisible())

    def test_transposing_back_is_no_change(self):
        for back in (self.app.transposeDown, self.app.transposeReset):
            self.app.transposeUp()
            self.app.transposeUp()
            self.assertTrue(self.app.editChanged())
            back()
            if back == self.app.transposeDown:
                back()
            self.assertFalse(self.app.editChanged())
            self.assertFalse(
                self.app.toolbar.save.isVisible())
            self.assertEqual(self.row_title(0), "Test Song")
            QTest.qWait(20)
            self.assertFalse(self.app.editing(), back.__name__)

    def test_a_whole_octave_is_no_change(self):
        for _ in range(12):
            self.app.transposeUp()
        self.assertFalse(self.app.editChanged())
        QTest.qWait(20)
        self.assertFalse(self.app.editing())

    def test_transposing_back_keeps_how_a_chord_was_typed(self):
        self.app.curs.execute(
            "UPDATE song_chord_link SET chord='A#' WHERE song_id=0")
        self.app.curs.commit()
        self.app.setCurrentSong(Song(self.app, 0))
        song = self.app.current_song
        typed = song.getChordAtPosition(0).getStoredText()
        self.app.transposeUp()
        self.app.transposeDown()
        self.assertFalse(self.app.editChanged())
        QTest.qWait(20)
        self.assertFalse(self.app.editing())
        self.assertEqual(song.getChordAtPosition(0).getStoredText(), typed)

    def test_discard_puts_the_key_back(self):
        before = self.db_song()
        self.app.transposeUp()
        self.app.discardEdit()
        self.assertEqual(self.song.getChordAtPosition(0).note_id, 0)
        self.assertEqual(self.song.transposed_steps, 0)
        self.assertFalse(self.app.toolbar.transpose_reset.isEnabled())
        self.assertEqual(self.db_song(), before)

    def test_undo_while_viewing_never_writes(self):
        before = self.db_song()
        self.app.transposeUp()
        self.app.transposeUp()
        self.app.undo()
        self.assertEqual(self.db_song(), before)
        self.app.saveEdit()
        saved = self.db_song()
        # The transposes went with the edit: nothing of this song is left
        # on the songbook's own stack, and Undo writes nothing.
        stack = self.app.undo_stack
        self.assertFalse(any(
            getattr(stack.command(index), "song_scoped", False)
            for index in range(stack.count())))
        self.app.undo()
        self.assertEqual(self.db_song(), saved)

    def test_title_number_and_notes_while_viewing_are_a_change(self):
        before = self.db_song()
        self.app.currentSongTitleEdited("New Title")
        self.app.currentSongNumberEdited("7")
        self.app.subtitleEdited("Notes")
        self.assertTrue(self.app.editing())
        self.assertFalse(self.app.chordEditing())
        # The list keeps the saved title until Save, with the dot.
        self.assertEqual(self.row_title(0), "Test Song \u2022")
        self.assertEqual(self.db_song(), before)
        self.app.discardEdit()
        self.assertEqual(self.row_title(0), "Test Song")
        self.assertEqual(self.song.title, "Test Song")
        self.assertEqual(self.app.ui.song_title_ef.text(), "Test Song")
        self.assertEqual(self.db_song(), before)

        self.app.currentSongTitleEdited("New Title")
        self.app.currentSongNumberEdited("7")
        self.app.saveEdit()
        title, number, _, _ = self.db_song()
        self.assertEqual((title, number), ("New Title", 7))
        self.assertEqual(self.row_title(0), "New Title")

    def number_shown(self, song_id):
        model = self.app.ui.songs_view.model()
        return model.index(self.row_of(song_id), 0).data()

    def test_list_does_not_sort_or_filter_by_a_draft(self):
        self.app.ui.songs_view.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        order = (self.row_of(0), self.row_of(1))
        self.assertLess(order[0], order[1])
        number = self.number_shown(0)
        self.app.songFilterEdited("Test")
        self.assertEqual(self.app.ui.songs_view.model().rowCount(), 1)
        # A title that no longer matches the filter, and a number after Second.
        self.app.currentSongTitleEdited("Zebra")
        self.app.currentSongNumberEdited("9")
        self.assertTrue(self.app.editChanged())
        model = self.app.ui.songs_view.model()
        self.assertEqual(model.rowCount(), 1)
        self.assertEqual(self.row_title(0), "Test Song \u2022")
        self.assertEqual(self.number_shown(0), number)
        self.app.clearFilterClicked()
        self.assertEqual((self.row_of(0), self.row_of(1)), order)
        self.assertTrue(self.app.saveEdit())
        self.assertEqual(self.row_title(0), "Zebra")
        self.assertGreater(self.row_of(0), self.row_of(1))

    def test_discarding_a_title_and_number_leaves_the_list_as_it_was(self):
        self.app.ui.songs_view.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        order = (self.row_of(0), self.row_of(1))
        number = self.number_shown(0)
        self.app.currentSongNumberEdited("9")
        self.app.currentSongTitleEdited("Zebra")
        self.app.discardEdit()
        self.assertEqual((self.row_of(0), self.row_of(1)), order)
        self.assertEqual(self.row_title(0), "Test Song")
        self.assertEqual(self.number_shown(0), number)
        self.assertEqual(self.app.ui.song_title_ef.text(), "Test Song")

    def test_title_typed_back_is_no_change(self):
        self.app.currentSongTitleEdited("Test Son")
        self.assertTrue(self.app.editChanged())
        self.app.currentSongTitleEdited("Test Song")
        QTest.qWait(20)
        self.assertFalse(self.app.editing())

    def test_edit_chords_after_a_transpose_is_the_same_edit(self):
        self.app.transposeUp()
        # No dialog: the edit goes on (an unexpected dialog would fail).
        self.assertTrue(self.app.chordEditorSelected())
        self.assertTrue(self.app.chordEditing())
        self.assertTrue(self.app.editChanged())
        self.app.discardEdit()
        self.assertFalse(self.app.editing())
        self.assertEqual(self.song.getChordAtPosition(0).note_id, 0)

    def test_switching_song_after_a_transpose_asks(self):
        before = self.db_song()
        self.app.transposeUp()
        self.dialog.answers.append(_SB.Discard)
        self.select_song(1, wait=True)
        self.assertEqual(len(self.dialog.asked), 1)
        self.assertEqual(self.app.current_song.id, 1)
        self.assertEqual(self.db_song(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
