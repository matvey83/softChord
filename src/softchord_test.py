"""
Execute as:

python3 softchord_test.py
"""
import unittest
import os, sys

import softchord

from PyQt6 import QtCore, QtGui, QtWidgets


class SoftChordEditorTest(unittest.TestCase):

    def testMain(self):
        """
        Test for softChord Editor
        """

        qapp = QtWidgets.QApplication(sys.argv)
        app = softchord.App([])

        app.setCurrentSongbook('zvuki_neba.songbook')

        prev_rows = app.songs_model.rowCount()

        app.createNewSong()
        self.assertEqual(app.songs_model.rowCount(), prev_rows + 1)

        # Delete the song that we just added (it's selected):
        app.deleteSelectedSongs()

        self.assertEqual(app.songs_model.rowCount(), prev_rows)

        # Import the test song:
        song_file = "test_тест_song.txt"
        app.importTextFiles([song_file])

        self.assertEqual(app.songs_model.rowCount(), prev_rows + 1)

        # Export back to text:
        out_song_file = "out_song.txt"
        if os.path.isfile(out_song_file):
            os.remove(out_song_file)
        app.exportToText(out_song_file)

        with open(out_song_file) as fh:
            lines = fh.readlines()

        # Compare the lines:
        with open(song_file) as fh:
            orig_lines = fh.readlines()
        self.assertEqual(lines, orig_lines)
        os.remove(out_song_file)

        # Test export to PDF:
        out_pdf_file = "out.pdf"
        if os.path.isfile(out_pdf_file):
            os.remove(out_pdf_file)

        app.exportToSinglePdf(out_pdf_file)

        assert os.path.isfile(out_pdf_file)

        os.remove(out_pdf_file)

        # Remove the imported song:
        app.deleteSelectedSongs()

        self.assertEqual(app.songs_model.rowCount(), prev_rows)


if __name__ == "__main__":
    unittest.TextTestRunner(verbosity=2)
    unittest.main()
