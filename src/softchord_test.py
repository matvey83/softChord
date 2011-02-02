# -*- coding: utf-8 -*-

# Use Unicode for all strings:
from __future__ import unicode_literals

import unittest
import os, sys

import softchord_main

from PyQt4 import QtCore, QtGui


class SoftChordEditorTest(unittest.TestCase):

    def testMain(self):
        """
        Test for softChord Editor
        """
        
        qapp = QtGui.QApplication(sys.argv)
        app = softchord_main.App()
        
        
        prev_rows = app.songs_model.rowCount()


        app.createNewSong()
        self.assertEqual( app.songs_model.rowCount(), prev_rows + 1 )
        
        # Delete the song that we just added (it's selected):
        app.deleteSelectedSongs()
        
        self.assertEqual( app.songs_model.rowCount(), prev_rows )
        
        # Import the test song:
        song_file = "test_тест_song.txt"
        app.importFromText(song_file)
        

        self.assertEqual( app.songs_model.rowCount(), prev_rows+1 )
        
        
        # Export back to text:
        out_song_file = "out_song.txt"
        if os.path.isfile(out_song_file):
            os.remove(out_song_file)
        app.exportToText(out_song_file)
        
        lines = open(out_song_file).readlines()
        
        
        # Compare the lines:
        orig_lines = open(song_file).readlines()
        self.assertEqual(lines, orig_lines)
        os.remove(out_song_file)
        
        
        # Test export to PDF:
        out_pdf_file = "out.pdf"
        if os.path.isfile(out_pdf_file):
            os.remove(out_pdf_file)
        
        app.exportToSinglePdf(out_pdf_file)
        
        self.assert_( os.path.isfile(out_pdf_file) )
        
        os.remove(out_pdf_file)
        
        # Remove the imported song:
        app.deleteSelectedSongs()
        
        self.assertEqual( app.songs_model.rowCount(), prev_rows )
        
        

if __name__ == "__main__":
    unittest.TextTestRunner(verbosity=2)
    unittest.main()

