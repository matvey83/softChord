"""
Execute as:

python3 softchord_test.py
"""
import unittest
import os
import shutil
import sys
import tempfile

import softchord

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt


class SoftChordEditorTest(unittest.TestCase):
    """Integration tests that exercise the main App / main window / panels."""

    @classmethod
    def setUpClass(cls):
        cls.qapp = QtWidgets.QApplication(sys.argv)

        # Create the real App (this sets up the main window + UI)
        cls.app = softchord.App([])

        # === Mock dialog methods so tests don't block on message boxes ===
        # Using lambdas avoids binding/self issues when replacing methods on the instance.
        cls.app.info = lambda text: None          # was showing "scaled down" info dialog
        cls.app.warning = lambda text: None
        cls.app.error = lambda text: None
        cls.app.question = lambda *args, **kwargs: True   # auto-accept (for renumber etc.)

        # Copy the sample songbook so tests do not write the original file.
        src = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "zvuki_neba.songbook"))
        cls._td = tempfile.TemporaryDirectory()
        songbook_path = os.path.join(cls._td.name, "zvuki_neba.songbook")
        shutil.copyfile(src, songbook_path)
        cls.app.setCurrentSongbook(songbook_path)

    @classmethod
    def tearDownClass(cls):
        # Clean up the App
        if hasattr(cls, 'app'):
            cls.app.closeSongbook()
            cls.app.quit()
        if hasattr(cls, 'qapp'):
            cls.qapp.quit()
        if hasattr(cls, '_td'):
            cls._td.cleanup()

    def setUp(self):
        self.app = self.__class__.app
        self.prev_rows = self.app.songs_model.rowCount()

    def test_create_and_delete_song(self):
        """Basic create/delete through the App (main window buttons/panels)."""
        self.app.createNewSong()
        self.assertEqual(self.app.songs_model.rowCount(), self.prev_rows + 1)

        self.app.deleteSelectedSongs()
        self.assertEqual(self.app.songs_model.rowCount(), self.prev_rows)

    def _import_then_export(self, song_file, add_chords=()):
        """Import one text file, export it, delete it; return the exported text.

        add_chords: (character_num, note_id) chords added before the export.
        """
        rows = self.app.songs_model.rowCount()
        self.app.importTextFiles([song_file])
        self.assertEqual(self.app.songs_model.rowCount(), rows + 1)
        song = self.app.current_song
        for character_num, note_id in add_chords:
            song._addChord(softchord.SongChord(
                song, character_num, note_id, 0, -1, "", 0))
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            out_path = tmp.name
        try:
            self.app.exportToText(out_path)
            with open(out_path, encoding="utf-8", newline="") as fh:
                exported = fh.read()
        finally:
            os.remove(out_path)
        self.app.deleteSelectedSongs()
        self.assertEqual(self.app.songs_model.rowCount(), rows)
        return exported

    def _write_temp_text(self, text):
        with tempfile.NamedTemporaryFile(
                "w", suffix=".txt", delete=False, encoding="utf-8",
                newline="") as tmp:
            tmp.write(text)
        self.addCleanup(os.remove, tmp.name)
        return tmp.name

    def test_import_and_export_text_roundtrip(self):
        """Import a text file, export it, and import that export again.

        A chord name is written starting above its letter, which is where a
        text import reads it from, so export -> import -> export is the same.
        """
        song_file = "test_тест_song.txt"
        exported = self._import_then_export(song_file)
        with open(song_file, encoding="utf-8", newline="") as fh:
            original = fh.read().splitlines(keepends=True)
        # Not quite the file: a chord always sits on a letter, so the A over
        # the space before "This" and "Your" goes onto the T and the Y.
        changed = {
            0: "\ufeff A           D\r\n",
            2: " A           D\r\n",
            4: " A    E/G\u266f  F\u266fm\r\n",
        }
        expected = "".join(changed.get(i, line) for i, line in enumerate(original))
        self.assertEqual(exported, expected)
        again = self._import_then_export(self._write_temp_text(exported))
        self.assertEqual(again, exported)

    def test_text_with_chords_on_letters_comes_back_unchanged(self):
        """Multi-letter names, a name past the line end, and Cyrillic lyrics."""
        lyric = "Shine on me, Lord Jesus"
        chords = [(0, "Am7"), (6, "E/G\u266f"), (13, "F\u266fm"),
                  (len(lyric) - 1, "Dsus4")]
        row = ""
        for column, name in chords:
            row = row.ljust(column) + name
        text = ("\ufeff" + row + "\r\n" + lyric + "\r\n"
                + "G" + " " * 15 + "Em\r\n" + "Это русские слова\r\n")
        self.assertEqual(self._import_then_export(self._write_temp_text(text)),
                         text)

    def test_chords_on_neighbouring_letters_keep_a_space_between(self):
        """A name that would touch the one before it moves right, past a space.

        The text cannot hold both on neighbouring letters, so the import reads
        the moved name on the letter it is written over, and a second export
        is the same as the first.
        """
        text = "\ufeffAm7\r\nShine on me\r\n"
        # D on the "h" and E on the "i", right after Am7 on the "S".
        exported = self._import_then_export(
            self._write_temp_text(text), add_chords=[(1, 2), (2, 4)])
        self.assertEqual(exported, "\ufeffAm7 D E\r\nShine on me\r\n")
        again = self._import_then_export(self._write_temp_text(exported))
        self.assertEqual(again, exported)

    def test_export_to_single_pdf(self):
        """Basic PDF export through the App."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            out_path = tmp.name

        try:
            self.app.exportToSinglePdf(out_path)
            self.assertTrue(os.path.isfile(out_path))
            self.assertGreater(os.path.getsize(out_path), 1000)  # Sanity: not empty
        finally:
            if os.path.exists(out_path):
                os.remove(out_path)

    def test_transpose_up_and_down(self):
        """Test the App-level transpose buttons/panel actions."""
        # Import a song that has chords
        self.app.importTextFiles(["test_тест_song.txt"])
        self.assertEqual(self.app.songs_model.rowCount(), self.prev_rows + 1)

        # Select the newly imported song (last one)
        last_row = self.app.songs_model.rowCount() - 1
        self.app.ui.songs_view.selectRow(last_row)

        original_text = self.app.current_song.getAsText(include_chords=True)

        self.app.transposeUp()
        up_text = self.app.current_song.getAsText(include_chords=True)
        self.assertNotEqual(original_text, up_text)

        self.app.transposeDown()
        down_text = self.app.current_song.getAsText(include_chords=True)
        self.assertEqual(original_text, down_text)

        # Cleanup
        self.app.deleteSelectedSongs()

    def test_reset_transpose_button(self):
        """Reset transpose is dimmed until the song is moved, then restores the opened key."""
        self.app.importTextFiles(["test_тест_song.txt"])
        last_row = self.app.songs_model.rowCount() - 1
        self.app.ui.songs_view.selectRow(last_row)
        button = self.app.toolbar.transpose_reset

        original_text = self.app.current_song.getAsText(include_chords=True)
        self.assertFalse(button.isEnabled())

        self.app.transposeUp()
        self.app.transposeUp()
        self.assertTrue(button.isEnabled())
        self.app.transposeDown()
        self.app.transposeDown()
        self.assertFalse(button.isEnabled())

        self.app.transposeDown()
        self.app.transposeDown()
        self.app.transposeDown()
        self.assertTrue(button.isEnabled())
        button.trigger()
        self.assertEqual(self.app.current_song.getAsText(include_chords=True), original_text)
        self.assertFalse(button.isEnabled())

        # Cleanup
        self.app.deleteSelectedSongs()

    def test_export_to_chordpro(self):
        """Test exporting the current song to ChordPro format via the App."""
        self.app.importTextFiles(["test_тест_song.txt"])
        self.assertEqual(self.app.songs_model.rowCount(), self.prev_rows + 1)

        with tempfile.NamedTemporaryFile(suffix=".chordpro", delete=False) as tmp:
            out_path = tmp.name

        try:
            self.app.exportToChordPro(out_path)
            self.assertTrue(os.path.isfile(out_path))

            with open(out_path, encoding="utf-8") as fh:
                content = fh.read()

            # Basic sanity checks for ChordPro output
            self.assertIn("{title:", content)
            self.assertTrue("[" in content and "]" in content)  # chords in brackets
        finally:
            if os.path.exists(out_path):
                os.remove(out_path)

        self.app.deleteSelectedSongs()

    def test_song_filtering(self):
        """Test the filter panel / search functionality on the main window."""
        # Make sure we have songs loaded
        self.assertGreater(self.app.songs_model.rowCount(), 0)

        # Apply a filter that should match very few songs
        self.app.songFilterEdited("Amazing Grace")
        filtered_count = self.app.songs_proxy_model.rowCount()
        self.assertLess(filtered_count, self.app.songs_model.rowCount())

        # Clear the filter
        self.app.clearFilterClicked()
        self.app.songFilterEdited("")  # Explicit clear
        self.assertEqual(self.app.songs_proxy_model.rowCount(), self.app.songs_model.rowCount())

    # ------------------------------------------------------------------
    # Core keyboard input tests (processKeyPressed)
    # These exercise one of the most important user workflows: adding
    # and editing chords directly from the keyboard.
    # ------------------------------------------------------------------

    def test_keyboard_add_chord_with_letter_key(self):
        """Pressing C/D/E etc. on a selected character should add a chord."""
        # Make sure we have a current song selected
        if self.app.current_song is None:
            self.app.ui.songs_view.selectRow(0)

        self.app.selected_char_num = 5
        self.app.previous_song_text = self.app.current_song.getAllText()

        result = self.app.processKeyPressed(Qt.Key.Key_C)
        self.assertTrue(result)

        chord = self.app.current_song.getChordAtPosition(5)
        self.assertIsNotNone(chord)
        self.assertEqual(chord.note_id, 0)  # C

    def test_keyboard_toggle_major_minor_with_m(self):
        """M key should toggle the selected chord between major and minor."""
        if self.app.current_song is None:
            self.app.ui.songs_view.selectRow(0)

        self.app.selected_char_num = 5
        self.app.previous_song_text = self.app.current_song.getAllText()

        self.app.processKeyPressed(Qt.Key.Key_G)  # Add G major

        chord = self.app.current_song.getChordAtPosition(5)
        self.assertEqual(chord.chord_type_id, 0)

        # The flip is an undo step: the song gets a new chord object.
        self.app.processKeyPressed(Qt.Key.Key_M)
        chord = self.app.current_song.getChordAtPosition(5)
        self.assertEqual(chord.chord_type_id, 1)  # Minor

    def test_keyboard_move_chord_with_arrows(self):
        """Left/Right should move the selected chord position."""
        if self.app.current_song is None:
            self.app.ui.songs_view.selectRow(0)

        self.app.selected_char_num = 5
        self.app.previous_song_text = self.app.current_song.getAllText()

        self.app.processKeyPressed(Qt.Key.Key_C)
        chord = self.app.current_song.getChordAtPosition(5)

        # The move is an undo step: the song gets a new chord object.
        self.app.processKeyPressed(Qt.Key.Key_Right)
        self.assertIsNone(self.app.current_song.getChordAtPosition(5))
        moved = self.app.current_song.getChordAtPosition(6)
        self.assertIsNotNone(moved)
        self.assertEqual(moved.note_id, chord.note_id)

    def test_keyboard_up_does_not_transpose_selected_chord(self):
        """Up/Down arrows do not change the selected chord."""
        if self.app.current_song is None:
            self.app.ui.songs_view.selectRow(0)

        self.app.selected_char_num = 5
        self.app.previous_song_text = self.app.current_song.getAllText()

        self.app.processKeyPressed(Qt.Key.Key_D)
        chord = self.app.current_song.getChordAtPosition(5)
        original_note = chord.note_id

        self.assertFalse(self.app.processKeyPressed(Qt.Key.Key_Up))
        self.assertFalse(self.app.processKeyPressed(Qt.Key.Key_Down))
        self.assertEqual(self.app.current_song.getChordAtPosition(5).note_id, original_note)


if __name__ == "__main__":
    # Qt can crash while Python shuts down after the tests (seen on macOS
    # and Linux), so exit with the test result before that can happen.
    program = unittest.main(verbosity=2, exit=False)
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0 if program.result.wasSuccessful() else 1)
