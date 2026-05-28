"""
Execute as:

python3 softchord_test.py
"""
import unittest
import os
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

        # Open the real songbook from the project root
        songbook_path = os.path.join(os.path.dirname(__file__), "..", "zvuki_neba.songbook")
        songbook_path = os.path.abspath(songbook_path)
        cls.app.setCurrentSongbook(songbook_path)

    @classmethod
    def tearDownClass(cls):
        # Clean up the App
        if hasattr(cls, 'app'):
            cls.app.quit()
        if hasattr(cls, 'qapp'):
            cls.qapp.quit()

    def setUp(self):
        self.app = self.__class__.app
        self.prev_rows = self.app.songs_model.rowCount()

    def test_create_and_delete_song(self):
        """Basic create/delete through the App (main window buttons/panels)."""
        self.app.createNewSong()
        self.assertEqual(self.app.songs_model.rowCount(), self.prev_rows + 1)

        self.app.deleteSelectedSongs()
        self.assertEqual(self.app.songs_model.rowCount(), self.prev_rows)

    def test_import_and_export_text_roundtrip(self):
        """Import text file and export it back (exercises App import/export paths)."""
        song_file = "test_тест_song.txt"
        self.app.importTextFiles([song_file])

        self.assertEqual(self.app.songs_model.rowCount(), self.prev_rows + 1)

        # Export back to text
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            out_path = tmp.name

        try:
            self.app.exportToText(out_path)

            with open(out_path, encoding="utf-8") as fh:
                exported = fh.readlines()

            with open(song_file, encoding="utf-8") as fh:
                original = fh.readlines()

            self.assertEqual(exported, original)
        finally:
            if os.path.exists(out_path):
                os.remove(out_path)

        # Cleanup the imported song
        self.app.deleteSelectedSongs()
        self.assertEqual(self.app.songs_model.rowCount(), self.prev_rows)

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

        self.app.processKeyPressed(Qt.Key.Key_M)
        self.assertEqual(chord.chord_type_id, 1)  # Minor

    def test_keyboard_move_chord_with_arrows(self):
        """Left/Right should move the selected chord position."""
        if self.app.current_song is None:
            self.app.ui.songs_view.selectRow(0)

        self.app.selected_char_num = 5
        self.app.previous_song_text = self.app.current_song.getAllText()

        self.app.processKeyPressed(Qt.Key.Key_C)
        chord = self.app.current_song.getChordAtPosition(5)

        self.app.processKeyPressed(Qt.Key.Key_Right)
        self.assertEqual(chord.character_num, 6)

    def test_keyboard_transpose_selected_chord(self):
        """Up/Down arrows should transpose the selected chord."""
        if self.app.current_song is None:
            self.app.ui.songs_view.selectRow(0)

        self.app.selected_char_num = 5
        self.app.previous_song_text = self.app.current_song.getAllText()

        self.app.processKeyPressed(Qt.Key.Key_D)
        chord = self.app.current_song.getChordAtPosition(5)
        original_note = chord.note_id

        self.app.processKeyPressed(Qt.Key.Key_Up)
        self.assertEqual(chord.note_id, (original_note + 1) % 12)


if __name__ == "__main__":
    unittest.main(verbosity=2)
