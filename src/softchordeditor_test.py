
import unittest
import os, sys

import softchordeditor_gui

from PyQt4 import QtCore, QtGui


class SoftChordEditorTest(unittest.TestCase):

    def testMain(self):
        """
        Test for softChord Editor
        """
        
        qapp = QtGui.QApplication(sys.argv)
        app = softchordeditor_gui.App()
        
        
        prev_rows = app.songs_model.rowCount()


        app.createNewSong()
        self.assertEqual( app.songs_model.rowCount(), prev_rows + 1 )

        # Delete the song that we just added (it's selected):
        app.deleteSelectedSong()

        self.assertEqual( app.songs_model.rowCount(), prev_rows )
        
        # Import the test song:
        song_file = "test_song.txt"
        app.importFromText(song_file)
        
        self.assertEqual( app.songs_model.rowCount(), prev_rows+1 )
        
        # Export back to text:
        out_song_file = "out_song.txt"
        if os.path.isfile(out_song_file):
            os.remove(out_song_file)
        app.exportToText(out_song_file)
        
        lines = open(out_song_file).readlines()
        
        # Remove the imported song:
        app.deleteSelectedSong()

        self.assertEqual( app.songs_model.rowCount(), prev_rows )
        
        # Compare the lines:
        orig_lines = open(song_file).readlines()
        self.assertEqual(lines, orig_lines)
        os.remove(out_song_file)


if __name__ == "__main__":
    unittest.TextTestRunner(verbosity=2)
    unittest.main()

