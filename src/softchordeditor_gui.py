# -*- coding: utf-8 -*-
"""

The main source file for softChord Editor

Writen by: Matvey Adzhigirey
Development started in 10 December 2010

"""

# NOTE The sqlite3 is intentionally used instead of QtSql.

# These are imported for Python 3 compatability:
# Use Unicode for all strings:
from __future__ import unicode_literals

from __future__ import division


from PyQt4 import QtCore, QtGui, uic
from PyQt4.QtCore import Qt
import sys, os
import sqlite3
import codecs
import copy



chord_types_list = [
  (0, u"Major", u""),
  (1, u"Minor", u"m"),
  (2, u"Suspended 4th", u"sus4"),
  (3, u"Major 7th", u"M7"),
  (4, u"Minor 7th", u"m7"),
  (5, u"Dominant 7th", u"7"),
  (6, u"Add 9", u"9"),
  (7, u"Diminished", u"dim"),
  (8, u"Major 6th", u"6"),
  (9, u"Minor 6th", u"m6"),
  (10, u"11th", u"11"),
  (11, u"Diminished", u"°"),
  (12, u"Diminished 7th", u"°7"),
]

global_notes_list = [
  (0, u"C", u"C"),
  (1, u"C♯", u"D♭"),
  (2, u"D", u"D"),
  (3, u"D♯", u"E♭"),
  (4, u"E", u"E"),
  (5, u"F", u"F"),
  (6, u"F♯", u"G♭"),
  (7, u"G", u"G"),
  (8, u"G♯", u"A♭"),
  (9, u"A", u"A"),
  (10, u"A♯", u"B♭"),
  (11, u"B", u"B"), 
]


#print 'dir executable:', dir(sys.executable)
if not os.path.basename(sys.executable).lower().startswith("python"):
    exec_dir = os.path.dirname(sys.executable)
else:
    exec_dir = "."

script_ui_file = os.path.join(exec_dir, "softchordeditor.ui" )
chord_dialog_ui_file = os.path.join(exec_dir, "softchordeditor_chord_dialog.ui")
pdf_dialog_ui_file = os.path.join(exec_dir, "softchordeditor_pdf_dialog.ui")

#print 'script_ui_file:', script_ui_file
#print 'exists:', os.path.isfile(script_ui_file)





paper_sizes_list = [
        (QtGui.QPrinter.Letter, "Letter (8.5 x 11 inches, 216 x 279 mm)"),
        (QtGui.QPrinter.Legal, "Legal (8.5 x 14 inches, 216 x 356 mm)"),
        (QtGui.QPrinter.A0, "A0 (841 x 1189 mm)"),
        (QtGui.QPrinter.A1, "A1 (94 x 841 mm)"),
        (QtGui.QPrinter.A2, "A2 (420 x 594 mm)"),
        (QtGui.QPrinter.A3, "A3 (297 x 420 mm)"),
        (QtGui.QPrinter.A4, "A4 (210 x 297 mm, 8.26 x 11.69 inches)"),
        (QtGui.QPrinter.A5, "A5 (148 x 210 mm)"),
        (QtGui.QPrinter.A6, "A6 (105 x 148 mm)"),
        (QtGui.QPrinter.A7, "A7 (74 x 105 mm)"),
        (QtGui.QPrinter.A8, "A8 (52 x 74 mm)"),
        (QtGui.QPrinter.A9, "A9 (37 x 52 mm)"),
        (QtGui.QPrinter.B0, "B0 (1030 x 1456 mm)"),
        (QtGui.QPrinter.B1, "B1 (728 x 1030 mm)"),
        (QtGui.QPrinter.B2, "B2 (515 x 728 mm)"),
        (QtGui.QPrinter.B3, "B3 (364 x 515 mm)"),
        (QtGui.QPrinter.B4, "B4 (257 x 364 mm)"),
        (QtGui.QPrinter.B5, "B5 (182 x 257 mm, 7.17 x 10.13 inches)"),
        (QtGui.QPrinter.B6, "B6 (128 x 182 mm)"),
        (QtGui.QPrinter.B7, "B7 (91 x 128 mm)"),
        (QtGui.QPrinter.B8, "B8 (64 x 91 mm)"),
        (QtGui.QPrinter.B9, "B9 (45 x 64 mm)"),
        (QtGui.QPrinter.B10, "B10 (32 x 45 mm)"),
        (QtGui.QPrinter.C5E, "C5E (163 x 229 mm)"),
        (QtGui.QPrinter.Comm10E, "Comm10E (105 x 241 mm, U.S. Common 10 Envelope)"),
        (QtGui.QPrinter.DLE, "DLE (110 x 220 mm)"),
        (QtGui.QPrinter.Executive, "Executive (7.5 x 10 inches, 191 x 254 mm)"),
        (QtGui.QPrinter.Folio, "Folio (210 x 330 mm)"),
        (QtGui.QPrinter.Ledger, "Ledger (432 x 279 mm)"),
        (QtGui.QPrinter.Tabloid, "Tabloid (279 x 432 mm)"),
]



"""
class AddCommand( QtGui.QUndoCommand ):
    def __init__(self, item, position):
        self.parent = 0
    
    def undo(self):
        
    
    def redo(self):


"""






def tr(text):
    """
    Returns translated GUI text. Not implemented yet.
    """
    return text


def transpose_note(note_id, steps):
    """
    Transpose the given note ID up by <steps>.
    Returns the transposed note ID.
    """
    note_id += steps

    if note_id < 0:
        note_id += 12
    elif note_id > 11:
        note_id -= 12

    return note_id


class SongsTableModel(QtCore.QAbstractTableModel):
    """
    Class for storing table information.
    """
    def __init__(self, app):
        QtCore.QAbstractTableModel.__init__(self)
        self.app = app
        self._data = []
        self.header_list = ["Number", "Title"]
        self.updateFromDatabase()

    def updateFromDatabase(self):
        """
        Updates the table model from the latest data in the database.
        """
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        self._data = []
        if self.app.curs:
            # A songbook is currently open
            for row in self.app.curs.execute("SELECT id, number, title FROM songs"):
                self._data.append(row)
        self.emit(QtCore.SIGNAL("layoutChanged()")) # Forces the view to redraw
    
    def rowCount(self, parent=QtCore.QModelIndex()):
        """ Returns number of rows """
        return len(self._data)
    
    def columnCount(self, parent=QtCore.QModelIndex()):
        """ Returns number of columns """
        return len(self.header_list)
    
    def data(self, index, role=Qt.DisplayRole):
        """
        Given a cell index, returns the data that should be displayed in that
        cell (text or check button state). Used by the view.
        """
        
        if role == Qt.DisplayRole:
            row_data = self._data[index.row()]
            row_data = row_data[1:] # Remove the ID column
            value = row_data[index.column()]
            if value == -1: # Invalid song number
                value = ""
            return QtCore.QVariant(value)
        return QtCore.QVariant()
    
    def headerData(self, section, orientation, role):
        """
        Returns the string that should be displayed in the specified header
        cell. Used by the View.
        """
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return QtCore.QVariant(self.header_list[section])
            else:
                return QtCore.QVariant(section+1)
        return QtCore.QVariant()        
    
    def getRowSongID(self, row):
        """
        Returns the database ID of the selected song (by row number).
        """
        return self._data[row][0]

    def getSongsRow(self, song):
        for i, row in enumerate(self._data):
            if row[0] == song.id:
                return i
        raise ValueError("No such song in the model")
        

class SongsProxyModel(QtGui.QSortFilterProxyModel):
    """ 
    Proxy model that allows showing/hiding rows in the residues table.
    """

    def __init__(self, parent):
        self.parent = parent
        QtGui.QSortFilterProxyModel.__init__(self, parent)

    def filterAcceptsRow(self, sourceRow, sourceParent):
        model = self.sourceModel()
        
        return True
    
    def lessThan(self, left, right):
        leftData = self.sourceModel().data(left)
        rightData = self.sourceModel().data(right)
        
        # Convert strings to floats:
        leftDataFloat, leftOk = leftData.toDouble()
        rightDataFloat, rightOk = rightData.toDouble()
        if leftOk and rightOk:
            return leftDataFloat < rightDataFloat
        else:
            # Non-number value ("NA", for example):
            return leftData.toString() < rightData.toString()
        


class SongChord:
    """
    Class that stores specific chord information. This chord is for a
    specific letter in a specific song.
    """
    
    def __init__(self, song, character_num, note_id, chord_type_id, bass_note_id, marker, in_parentheses):
        self.app = song.app
        self.song = song
        self.song_id = song.id
        self.character_num = character_num
        self.note_id = note_id
        self.chord_type_id = chord_type_id
        self.bass_note_id = bass_note_id

        if marker == u"-1" or marker == None or marker == "None":
            # FIXME the database should have only one of these in it
            marker = ""
        self.marker = marker

        if in_parentheses == None:
            in_parentheses = 0
        self.in_parentheses = in_parentheses
    


    def transpose(self, steps):
        """
        Transpose this chord the specified number of steps up.
        <steps> can be negative.
        """
        self.note_id = transpose_note(self.note_id, steps)
        if self.bass_note_id != -1:
            self.bass_note_id = transpose_note(self.bass_note_id, steps)
    

    def _getNoteString(self, note_id):
        """
        Returns the specified note as a string, using sharps vs flats
        as appropriate.
        """
        
        note_text, note_alt_text = self.app.notes_list[note_id]

        if self.song.prefer_sharps:
            return note_text
        else:
            return note_alt_text
        

    def getChordText(self):
        """
        Returns string of the chord.
        For example, "Fm" or "Bbsus4"
        """
        note_text = self._getNoteString(self.note_id)
        
        chord_type_text = self.app.chord_type_prints[self.chord_type_id]
        
        # Convert the chord note and type to a text string:
        if self.marker: # Not NULL
            # Add the chord prefix (example: "1:", "2:")
        
            chord_str = '%s:%s%s' % (self.marker, note_text, chord_type_text)
        else:
            chord_str = '%s%s' % (note_text, chord_type_text)
        
        # Add the bass note (if any):
        if self.bass_note_id != -1: # Not NULL
            bass_note_text = self._getNoteString(self.bass_note_id)
            chord_str += "/%s" % bass_note_text
        
        # Add parentheses (if any):
        if self.in_parentheses:
            chord_str = "(%s)" % chord_str
        
        return chord_str




class SongChar:
    """
    This class holds the paint bounds information for this character and its chord (if any).
    """
    def __init__(self, text, song_char_num, chord, char_left, char_right, chord_left, chord_right):
        self.text = text
        self.song_char_num = song_char_num
        self.chord = chord
        self.char_left = char_left
        self.char_right = char_right
        self.has_chord = bool(chord_right)
        self.chord_left = chord_left
        self.chord_right = chord_right



class Song:
    """
    Stores information for a particular song.
    """
    
    def __init__(self, app, song_id):
        self.app = app
        self.id = song_id
        self._chords = []
        self.number = -1
        self.title = ""
        self.prefer_sharps = True
        self.key_note_id = -1
        self.key_is_major = 0

        self.updateSongFromDatabase()
        self.updateSharpsOrFlats()
    
    
    def updateSongFromDatabase(self):
        
        for row in self.app.curs.execute("SELECT title, number, text, key_note_id, key_is_major FROM songs WHERE id=%i" % self.id):
            self.title = row[0]
            self.number = row[1]
            all_text = unicode(row[2])
            self.key_note_id = row[3] # Can be None or -1
            if self.key_note_id == None:
                self.key_note_id = -1
            self.key_is_major = row[4]
            if self.key_is_major == None:
                self.key_is_major = 0
            break
        
        song_chords = []
        for row in self.app.curs.execute("SELECT id, character_num, note_id, chord_type_id, bass_note_id, marker, in_parentheses FROM song_chord_link WHERE song_id=%i" % self.id):
            id = row[0]
            song_char_num = row[1]
            note_id = row[2]
            chord_type_id = row[3]
            bass_note_id = row[4]
            marker = row[5]
            in_parentheses = row[6]
            chord = SongChord(self, song_char_num, note_id, chord_type_id, bass_note_id, marker, in_parentheses)
            song_chords.append(chord)
        
        self.doc = QtGui.QTextDocument()
        self.doc.setDefaultFont(self.app.lyrics_font)
        
        self.setAllText(all_text, song_chords)
        
        self.updateSharpsOrFlats()
    
    

    def iterateAllChords(self):
        for chord in self._chords:
            yield chord
    

    def setAllText(self, all_text, all_chords):
        """
        Populates the QTextDocument and self._chords lists based on the specified
        data.
        """
        
        self.doc.setPlainText(all_text)
        self._chords = all_chords
        self.setDocMargins()
        
        self.updateSharpsOrFlats()
    
    

    def setDocMargins(self):
        
        # Required to avoid circular calls:
        self.app.ignore_song_text_changed = True        
        
        # Determine which chars have chords:
        chords_by_char = {}
        for chord in self._chords:
            chords_by_char[chord.character_num] = True
        
        
        chords_height, lyrics_height, line_height = self.getHeightsWithChords()
        with_chords_top_margin = line_height - lyrics_height
        
        
        # Set the margin for the first line (the top of the document):
        # NOTE: We are always setting the top margin for the first line with the assumption that
        # the first line always has chords on it. This assumption is often valid, and also
        # lets us avoid some issues.
        root_frame = self.doc.rootFrame()
        frame_format = root_frame.frameFormat()
        frame_format.setTopMargin(with_chords_top_margin)
        root_frame.setFrameFormat(frame_format)
        
        
        block = self.doc.begin()
        
        with_chords_format = block.blockFormat()
        with_chords_format.setTopMargin(with_chords_top_margin)
        with_chords_format.setLeftMargin(10)
        
        without_chords_format = block.blockFormat()
        without_chords_format.setTopMargin(0.0)
        without_chords_format.setLeftMargin(10)
        
        
        linenum = -1
        line_start_char = 0
        for line_text in self.iterateLineTexts():
            linenum += 1
            
            line_end_char = line_start_char + len(line_text)
            
            line_has_chords = False
            for chord_num in chords_by_char.keys():
                if chord_num >= line_start_char and chord_num <= line_end_char:
                    line_has_chords = True
                    break
            
            cursor = QtGui.QTextCursor(block)
            
            if line_has_chords:
                cursor.setBlockFormat(with_chords_format)
            else:
                cursor.setBlockFormat(without_chords_format)
            
            if block == self.doc.end():
                break
            
            block = block.next()

            line_start_char += len(line_text) + 1 # Add the eof-of-line character
        
        self.app.ignore_song_text_changed = False

    
    def addChord(self, chord):
        self._chords.append(chord)
        self.updateSharpsOrFlats()
        
    
    def deleteChord(self, chord):
        self._chords.remove(chord)
        self.updateSharpsOrFlats()
    

    def moveChord(self, chord, new_song_char_num):
        chord.character_num = new_song_char_num
    
    def getAllText(self):
        
        song_text = unicode(self.doc.toPlainText())
        return song_text
        

    def iterateLineTexts(self):
        """
        Iterate over each the lines in this song.
        """
        all_text = self.getAllText()
        for text in all_text.split("\n"):
            yield text
    

    def iterateTextChars(self):
        all_text = self.getAllText()
        for char in all_text:
            yield char



    def iterateCharDrawPositions(self):
        
        te = self.app.editor
        
        cursor = te.textCursor()
        
        # Make a dict of chords:
        char_num_chord_dict = {}
        for chord in self._chords:
            char_num_chord_dict[chord.character_num] = chord
        
        
        all_chars = []
        
        linenum = -1
        line_start_char = 0
        for line_text in self.iterateLineTexts():
            linenum += 1
            
            line_end_char = line_start_char + len(line_text)
            
            line_has_chords = False
            for chord_num in char_num_chord_dict.keys():
                if chord_num >= line_start_char and chord_num <= line_end_char:
                    line_has_chords = True
                    break
            
            if line_has_chords:
                chords_height, lyrics_height, line_height = self.getHeightsWithChords()
            else:
                chords_height, lyrics_height, line_height = self.getHeightsWithoutChords()
            
            
            for line_char_num, char_text in enumerate(line_text):
                song_char_num = line_start_char + line_char_num
                
                # Find the bounding rect for this character:
                chord = char_num_chord_dict.get(song_char_num)
                
                cursor.setPosition(song_char_num)
                left_rect = te.cursorRect(cursor)
                cursor.setPosition(song_char_num+1)
                right_rect = te.cursorRect(cursor)
                
                char_left = left_rect.left()
                char_right = right_rect.right()
                
                chord_top = left_rect.bottom() - line_height
                chord_bottom = chord_top + chords_height

                char_top = left_rect.top()
                char_bottom = left_rect.bottom()
                
                
                # Find the bounding rect for this chord (if any):
                if chord:
                    chord_text = chord.getChordText()
                    chord_middle = (char_left + char_right) // 2 # Average of left and right
                    chord_width = self.app.chords_font_metrics.width(chord_text)
                    chord_left = chord_middle - (chord_width/2.0)
                    chord_right = chord_middle + (chord_width/2.0)
                else:
                    chord_left = chord_right = None
                
                char = SongChar(char_text, song_char_num, chord, char_left, char_right, chord_left, chord_right)
                if char.has_chord:
                    char.chord_text = chord_text
                
                char.chord_bottom = chord_bottom
                char.chord_top = chord_top
                char.char_bottom = char_bottom
                char.char_top = char_top
                
                all_chars.append(char)
            
            line_start_char += len(line_text) + 1 # Add the eof-of-line character
        
        return all_chars



    def getLineHasChords(self, linenum):

        chords_present = False
        for chord in self._chords:
            chord_linenum, line_char_num = self.songCharToLineChar(chord.character_num)
            if chord_linenum == linenum:
                chords_present = True
                break

        return chords_present
    

    def getHeightsWithChords(self):
        
        cfm = self.app.chords_font_metrics
        lfm = self.app.lyrics_font_metrics

        lyrics_height = lfm.height()
        chords_height = cfm.height()
        
        line_height = (lyrics_height + cfm.ascent()) - lfm.leading() - cfm.leading()
        
        return chords_height, lyrics_height, line_height
        

    def getHeightsWithoutChords(self):

        lyrics_height = self.app.lyrics_font_metrics.height()
        chords_height = 0.0
        line_height = lyrics_height
        
        return chords_height, lyrics_height, line_height
    
    
    def getLineHeights(self, linenum):
        """
        Returns top & bottom y positions of the chords and lyrics texts
        for the specified line.
        """

        if self.getLineHasChords(linenum):
            return self.getHeightsWithChords()
        else:
            return self.getHeightsWithoutChords()

    
    def songCharToLineChar(self, song_char_num):
        """
        Given a character's global position in the song, return the
        character's line and line position.

        Returns a tuple of (linenum, char_num)
        """
        
        line_global_start = 0
        line_global_end = 0
        linenum = -1
        for line_text in self.iterateLineTexts():
            linenum += 1
            line_global_end += len(line_text) + 1
            if song_char_num < line_global_end-1:
                # This character is in this line
                line_char_num = song_char_num - line_global_start
                return (linenum, line_char_num)
            line_global_start += len(line_text) + 1
        
        raise RuntimeError()


    def lineCharToSongChar(self, char_linenum, char_num):
        """
        Given the character position in the line, return its global
        position in the song.
        """
        
        out_char_num = 0
        linenum = -1
        for line_text in self.iterateLineTexts():
            linenum += 1
            if linenum == char_linenum:
                return out_char_num + char_num
            else:
                out_char_num += len(line_text) + 1 # Add one for the end-of-line character
        raise RuntimeError()
    

    def getChord(self, song_char_num):
        for chord in self.iterateAllChords():
            chord_song_char_num = chord.character_num
            if chord_song_char_num == song_char_num:
                return chord
        raise ValueError("There is no chord for character %i" % song_char_num)
                
    
    def getAsText(self):
        """
        Return a text string for this song. This text will have proper
        formatting only if displayed with a mono-spaced (fixed-width) font.
        """
        
        song_text = unicode()
        self.updateSharpsOrFlats()
        
        for linenum, line_text in enumerate(self.iterateLineTexts()):
            
            if self.getLineHasChords(linenum):
                # Add the chords line above this line
                
                line_chord_text_list =  [u' '] * len(line_text) # FIXME add a few to the end???
                
                # Figure out the lyric letter for the mouse location:
                song_char_num = -1
                for line_char_num in range(len(line_text)):
                    song_char_num = self.lineCharToSongChar(linenum, line_char_num)
                    
                    
                    # Figure out if a chord is attached to this letter:
                    for chord in self.iterateAllChords():
                        chord_song_char_num = chord.character_num
                        chord_linenum, line_char_num = self.songCharToLineChar(chord_song_char_num)

                        if chord_linenum != linenum:
                            continue
                        
                        chord_text = chord.getChordText()
                        
                        chord_len = len(chord_text)
                        chord_left = line_char_num - (chord_len//2)
                        if not (chord_len % 2): # Even number of characters:
                            # Offset the chord so that the chord-letter is closer to the middle of the chord text
                            chord_left += 1
                        chord_right = chord_left + chord_len
                        
                        # Make sure that the chord does not go beyond the start-of-line:
                        while chord_left < 0:
                            chord_left +=1
                            chord_right += 1
                        
                        # Make sure that the chord does not go beyond the end-of-line:
                        while chord_right >= len(line_chord_text_list):
                            chord_right -= 1
                            chord_left -= 1
                        
                        # For each letter in the chord text:
                        for i in range(len(chord_text)):
                            pos = i + chord_left
                            line_chord_text_list[pos] = chord_text[i]


            
                line_chord_text = u''.join(line_chord_text_list).rstrip()
                song_text += line_chord_text + u"\n"
            
            song_text += line_text + u"\n"
        

        # Remove the last end-of-line:
        if song_text[-1] == "\n":
            song_text = song_text[:-1]
        
        return song_text
        
    
    def transpose(self, steps):
        for chord in self.iterateAllChords():
            chord.transpose(steps)
        
        if self.key_note_id != -1:
            self.key_note_id = transpose_note(self.key_note_id, steps)
        
        self.updateSharpsOrFlats()
        
        self.changed()
        self.app.editor.repaint()
    

    def changed(self):
        self.setDocMargins()
        self.app.enableUndo()
    
    def sendToDatabase(self):
        """
        Save this song to the database.
        """
        
        self.app.setWaitCursor()
        try:
            chords_in_database = []
            for row in self.app.curs.execute("SELECT character_num FROM song_chord_link WHERE song_id=%i" % self.id):
                chords_in_database.append(row[0])
            
            for chord in self.iterateAllChords():
                # Update existing chords
                if chord.character_num in chords_in_database:
                    self.app.curs.execute('UPDATE song_chord_link SET note_id=%i, chord_type_id=%i, bass_note_id=%i, marker="%s", in_parentheses=%i WHERE song_id=%i AND character_num=%i' 
                        % (chord.note_id, chord.chord_type_id, chord.bass_note_id, chord.marker, chord.in_parentheses, chord.song_id, chord.character_num))
                    chords_in_database.remove(chord.character_num)
            
                else:
                    # Add new chords
                    self.app.curs.execute('INSERT INTO song_chord_link (song_id, character_num, note_id, chord_type_id, bass_note_id, marker, in_parentheses) ' + \
                            'VALUES (%i, %i, %i, %i, %i, "%s", %i)' % (chord.song_id, chord.character_num, chord.note_id, chord.chord_type_id, chord.bass_note_id, chord.marker, chord.in_parentheses))

            # Remove old chords
            for song_char_num in chords_in_database:
                self.app.curs.execute("DELETE FROM song_chord_link WHERE song_id=%i AND character_num=%i" % (self.id, song_char_num))
            
            self.app.curs.execute('UPDATE songs SET number=%i, title="%s", text="%s", key_note_id=%i, key_is_major=%i WHERE id=%i' % 
                (self.number, self.title, self.getAllText(), self.key_note_id, self.key_is_major, self.id))
            self.app.curs.commit()
        finally:
            self.app.restoreCursor()
        
        self.app.disableUndo()
    

    def copyChord(self, chord, new_song_char_num):
        """
        Copy the specified chord to a new position.
        """
        
        new_chord = copy.copy(chord)
        new_chord.character_num = new_song_char_num
        self.addChord(new_chord)
        return new_chord
       
            
    def updateSharpsOrFlats(self):
        """
        Determines whether this song prefers notes to be displayed with flats
        or with sharps, and updates this song.
        """
        
        num_prefer_sharp = 0
        num_prefer_flat = 0
        for chord in self.iterateAllChords():
            if chord.note_id in [1, 6]: # C# or F#
                num_prefer_sharp += 1
            elif chord.note_id in [3, 10]: # Eb or Bb
                num_prefer_flat += 1
        
        self.prefer_sharps = (num_prefer_sharp >= num_prefer_flat)
    





class CustomTextEdit(QtGui.QTextEdit):
    """
    """
    def __init__(self, app):
        QtGui.QWidget.__init__(self, app.ui)
        self.app = app
        
        
        #self.setViewportMargins(self.app.left_margin, self.app.top_margin, 5, 5)

        self.dragging_chord_orig_position = -1
        self.dragging_chord = None
        self.original_chord = None

        # So that hover mouse move events are generated:
        self.setMouseTracking(True)
        
        self.lyric_editor_mode = False
        

    def paintEvent(self, event):
        """
        Called when the widget needs to draw the current song.
        """
        
        if self.lyric_editor_mode:
            
            # Paint the lyrics text, selection rect, and cursor:
            QtGui.QTextEdit.paintEvent(self, event)
            

            # Paint the chords:
            if self.app.current_song:
                painter = QtGui.QPainter()
                painter.begin(self.viewport())
                
                
                # Draw background into the whole widget:
                #rect = self.viewport().rect()
                #rect = QtCore.QRect(0, 0, 100, 100)
                #bgbrush = QtGui.QBrush(QtGui.QColor("white"))
                #painter.fillRect(rect, bgbrush)
                
                
                painter.setFont(self.app.chords_font)
                painter.setPen(self.app.chords_color)

                song = self.app.current_song
                
                cursor = self.textCursor()
                for chord in song.iterateAllChords():
                    # Obviously this line has chords:
                    chords_height, lyrics_height, line_height = song.getHeightsWithChords()
                    
                    cursor.setPosition(chord.character_num)
                    left_rect = self.cursorRect(cursor)
                    cursor.setPosition(chord.character_num+1)
                    right_rect = self.cursorRect(cursor)
                    
                    chord_text = chord.getChordText()
                    
                    chord_middle = (left_rect.left() + right_rect.right()) // 2 # Average of left and right
                    chord_width = self.app.chords_font_metrics.width(chord_text)
                    chord_left = chord_middle - (chord_width/2.0)
                    chord_right = chord_middle + (chord_width/2.0)
                    
                    chord_top = left_rect.bottom() - line_height
                    chord_bottom = chord_top + chords_height
                    
                    painter.drawText(chord_left, chord_top, chord_right-chord_left, chord_bottom-chord_top, QtCore.Qt.AlignHCenter, chord_text)
                    
                painter.end()
            
                
        else:
            
            painter = QtGui.QPainter()
            painter.begin(self.viewport())
            
            # Draw into the whole widget:
            rect = self.rect()
            #bgbrush = QtGui.QBrush(QtGui.QColor("white"))
            #painter.fillRect(rect, bgbrush)
            
            if self.app.current_song:
                width = 100000 # Unlimited
                height = 100000 # Unlimited
                
                paint_rect = QtCore.QRect(0, 0, width, height)
                self.app.drawSongToRect(self.app.current_song, painter, paint_rect)
            
            painter.end()
    

    def leaveEvent(self, event):
        """
        Called when the mouse LEAVES the song chords widget.
        """
        
        if self.lyric_editor_mode:
            QtGui.QTextEdit.leaveEvent(self, event)
        else:
            # Clear the hovering highlighting:
            self.hover_char_num = None
            self.repaint()
    
    
    def optionKeyToggled(self, pressed):
        if self.dragging_chord == None:
            return
        
        if pressed:
            # Copy the dragging chord into the original location:
            self.original_chord = self.app.current_song.copyChord(self.dragging_chord, self.dragging_chord_orig_position)
        else:
            # Remove the original chord:
            self.app.current_song.deleteChord(self.original_chord)
            self.original_chord = None

        self.repaint()
    
    
    def mouseMoveEvent(self, event):
        """
        Called when mouse is DRAGGED or HOVERED in the song chords widget.
        """
        
        if self.lyric_editor_mode:
            QtGui.QTextEdit.mouseMoveEvent(self, event)
            return
        
        localx = event.pos().x()
        localy = event.pos().y()
        dragging = (self.dragging_chord != None)
        letter_tuple = self.app.determineClickedLetter(localx, localy, dragging)
        
        if letter_tuple != None:
            (is_chord, song_char_num) = letter_tuple
            # Mouse is over a vlid chord/letter
            
            if not self.dragging_chord:
                # Hovering, highlight the new chord/letter
                self.app.hover_char_num = song_char_num
                
                # No chord is being currently dragged. Clear previous selection:
                # WHEN? self.app.selected_char_num = song_char_num
                # self.app.selected_char_num = None
                
            else:
                # Dragging - A chord is being dragged
                song = self.app.current_song

                if song_char_num != self.dragging_chord.character_num:
                    # The dragged chord was moved to a new position
                    
                    #prev_chord_linenum, prev_line_char_num = song.songCharToLineChar(self.dragging_chord.character_num)
                    
                    song.moveChord(self.dragging_chord, song_char_num)
                    
                    # Update the margin of the document in case the chord was moved to a new line:
                    song.setDocMargins()
                    
                    # Show hover feedback on the new letter:
                    self.app.hover_char_num = song_char_num
                    self.app.selected_char_num = song_char_num
        else:
            # The mouse is NOT over a letter
            if not self.dragging_chord:
                self.app.hover_char_num = None
        self.app.editor.repaint()



    def mousePressEvent(self, event):
        """
        Called when mouse is CLICKED in the song chords widget.
        """
        
        if self.lyric_editor_mode:
            QtGui.QTextEdit.mousePressEvent(self, event)
            return
        
        if event.button() == Qt.LeftButton:
            localx = event.pos().x()
            localy = event.pos().y()
            letter_tuple = self.app.determineClickedLetter(localx, localy, False)
            if letter_tuple:
                # A valid letter/chord was clicked, select it:
                (is_chord, song_char_num) = letter_tuple
                
                if self.app.selected_char_num != song_char_num:
                    # User clicked on an un-selected letter. Select it:
                    self.app.selected_char_num = song_char_num
               
                #if self.app.selected_char_num == song_char_num and is_chord:
                if is_chord:
                    # User clicked on the selected chord, initiate drag:
                    try:
                        self.dragging_chord = self.app.current_song.getChord(song_char_num)
                    except ValueError:
                        # User clicked on an empty chord space
                        pass
                    else:
                        self.dragging_chord_orig_position = song_char_num
                        
                        # If option is held, copy the chord:
                        key_modifiers = event.modifiers() 
                        if bool(key_modifiers & Qt.AltModifier):
                            self.original_chord = self.app.current_song.copyChord(self.dragging_chord, self.dragging_chord_orig_position)
                        else:
                            self.original_chord = None

            else:
                self.app.selected_char_num = None
                self.dragging_chord = None
            
            print 'repainting'
            self.app.editor.repaint()
    

    def mouseReleaseEvent(self, event):
        if self.lyric_editor_mode:
            QtGui.QTextEdit.mouseReleaseEvent(self, event)
            return

        # Stop dragging of the chord (it's already in the correct position):
        if self.dragging_chord:
            if self.dragging_chord.character_num != self.dragging_chord_orig_position:
                
                # Delete the previous chord, if any:
                for other_chord in self.app.current_song.iterateAllChords():
                    if other_chord.character_num == self.dragging_chord.character_num and other_chord != self.dragging_chord:
                        self.app.current_song.deleteChord(other_chord)
                        break
                self.app.current_song.changed()
                self.app.editor.repaint()

            self.dragging_chord_orig_position = -1
            self.dragging_chord = None
    

    def mouseDoubleClickEvent(self, event):
        """
        Called when mouse is DOUBLE-CLICKED in the song chords widget.
        """
        if self.lyric_editor_mode:
            QtGui.QTextEdit.mouseDoubleClickedEvent(self, event)
            return
        
        if event.button() == Qt.LeftButton:
            localx = event.pos().x()
            localy = event.pos().y()
            letter_tuple = self.app.determineClickedLetter(localx, localy, False)
            if letter_tuple:
                # A valid chord/letter was double-clicked, edit it:
                (is_chord, song_char_num) = letter_tuple
                self.app.selected_char_num = song_char_num
                self.app.processSongCharEdit(song_char_num)
            else:
                # Invalid chord/letter was double clicked. Clear current selection:
                self.app.selected_char_num = None

            self.app.editor.repaint()

    

    


class ChordDialog:
    """
    Dialog for allowing the user to set the chord note & type.
    """

    def c(self, widget, signal_str, slot):
        self.ui.connect(widget, QtCore.SIGNAL(signal_str), slot)
    def __init__(self, app):
        self.app = app
        self.ui = uic.loadUi(chord_dialog_ui_file)
        
        notes_list = []

        for (note_text, note_alt_text) in self.app.notes_list:
            if note_text == note_alt_text:
                combined_text = note_text
            else:
                combined_text = "%s/%s" % (note_text, note_alt_text)
            notes_list.append(combined_text)
        self.ui.note_menu.addItems(notes_list)
        self.ui.note_menu.setMaxVisibleItems(12) # Show all notes


        self.ui.chord_type_menu.addItems(self.app.chord_type_names)
        self.ui.chord_type_menu.setMaxVisibleItems(20) # Show more types

        self.ui.bass_menu.addItems(["None"] + notes_list)
        self.ui.bass_menu.setMaxVisibleItems(12) # Show all notes
    

    def display(self, chord):
        """
        Display the chord-editing dialog box.
        Modify the passed chord if OK is pressed.
        Returns False if user pressed Cancel.
        """
        
        note_id = chord.note_id
        chord_type_id = chord.chord_type_id
        bass_note_id = chord.bass_note_id
        marker = chord.marker
        in_parentheses = chord.in_parentheses
        
        if note_id != None:
            self.ui.note_menu.setCurrentIndex(note_id)
        if chord_type_id != None:
            self.ui.chord_type_menu.setCurrentIndex(chord_type_id)
        if bass_note_id != None:
            # -1 becomes 0, etc:
            self.ui.bass_menu.setCurrentIndex(bass_note_id+1)
        
        if marker == -1 or marker == "" or marker == "None":
            marker = ""
        self.ui.marker_ef.setText(marker)

        self.ui.in_parentheses_box.setChecked(in_parentheses)
        
        self.ui.show()
        self.ui.raise_()
        out = self.ui.exec_()
        if out: # OK pressed:
            chord.note_id = self.ui.note_menu.currentIndex()
            chord.chord_type_id = self.ui.chord_type_menu.currentIndex()
            # 0 (first item) will become -1 (invalid):
            chord.bass_note_id = self.ui.bass_menu.currentIndex() - 1
            chord.marker = self.ui.marker_ef.text()
            chord.in_parentheses = self.ui.in_parentheses_box.isChecked()
            
            return True
        else:
            # Cancel pressed
            return False



class PdfOptions:
    def __init__(self):
        self.left_margin = 0.5
        self.right_margin = 0.5
        self.top_margin = 0.5
        self.bottom_margin = 0.5
        self.alternate_margins = False
        self.print_4_per_page = False



class PdfDialog:
    """
    Dialog for allowing the user to set up printing and PDF export options.
    """

    def c(self, widget, signal_str, slot):
        self.ui.connect(widget, QtCore.SIGNAL(signal_str), slot)
    def __init__(self, app):
        self.app = app
        self.ui = uic.loadUi(pdf_dialog_ui_file)
        self.ui.left_margin_ef.setValidator( QtGui.QDoubleValidator(0, 1000000000, 5, self.ui) )
        self.ui.right_margin_ef.setValidator( QtGui.QDoubleValidator(0, 1000000000, 5, self.ui) )
        self.ui.top_margin_ef.setValidator( QtGui.QDoubleValidator(0, 1000000000, 5, self.ui) )
        self.ui.bottom_margin_ef.setValidator( QtGui.QDoubleValidator(0, 1000000000, 5, self.ui) )
    
    
    
    def display(self, pdf_options):
        """
        Display a dialog that alters the PdfOptions if OK is pressed.
        Returns False if user pressed Cancel.
        """
        
        self.ui.left_margin_ef.setText( str(pdf_options.left_margin) )
        self.ui.right_margin_ef.setText( str(pdf_options.right_margin) )
        self.ui.top_margin_ef.setText( str(pdf_options.top_margin) )
        self.ui.bottom_margin_ef.setText( str(pdf_options.bottom_margin) )
        
        self.ui.alternate_margins_box.setChecked(pdf_options.alternate_margins)
        self.ui.print_4_per_page_box.setChecked(pdf_options.print_4_per_page)
        
        self.ui.show()
        self.ui.raise_()
        out = self.ui.exec_()
        if out: # OK pressed:
            # FIXME what if the user entered ""?
            pdf_options.left_margin = float(self.ui.left_margin_ef.text())
            pdf_options.right_margin = float(self.ui.right_margin_ef.text())
            pdf_options.top_margin = float(self.ui.top_margin_ef.text())
            pdf_options.bottom_margin = float(self.ui.bottom_margin_ef.text())
            pdf_options.alternate_margins = self.ui.alternate_margins_box.isChecked()
            pdf_options.print_4_per_page = self.ui.print_4_per_page_box.isChecked()
            return True
        else:
            # Cancel pressed
            return False

            


class App:
    """
    The main application class.
    """
    def c(self, widget, signal_str, slot):
        self.ui.connect(widget, QtCore.SIGNAL(signal_str), slot)
        
        self.left_margin = 21
        self.top_margin = 10

    
    def __init__(self):
        self.ui = uic.loadUi(script_ui_file)

        #self.curs = sqlite3.connect(db_file)
        self.curs = None
        self.current_song = None
        
        self.pdf_options = PdfOptions()
        
        self.undo_stack = QtGui.QUndoStack()
        self.undo_stack.canUndoChanged.connect(self.ui.actionUndo.setEnabled)
        self.undo_stack.canRedoChanged.connect(self.ui.actionRedo.setEnabled)
        

        # Make a list of all chord types:
        self.chord_type_names = []
        self.chord_type_prints = []
        for chord_type_id, name, print_text in chord_types_list:
            self.chord_type_names.append(name)
            self.chord_type_prints.append(print_text)
        
        
        # Make a list of all notes and keys:
        self.notes_list = []
        self.note_text_id_dict = {}
        for note_id, text, alt_text in global_notes_list:
            self.notes_list.append( (text, alt_text) )
            self.note_text_id_dict[text] = note_id
            self.note_text_id_dict[alt_text] = note_id
        
        self.songs_model = SongsTableModel(self)
        self.songs_proxy_model = SongsProxyModel(self.ui)
        self.songs_proxy_model.setSourceModel(self.songs_model)
        
        self.ui.songs_view.setModel(self.songs_proxy_model)
        self.ui.songs_view.setSortingEnabled(True)

        self.ui.songs_view.horizontalHeader().setStretchLastSection(True)
        self.ui.songs_view.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.ui.songs_view.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.c( self.ui.songs_view.selectionModel(), "selectionChanged(QItemSelection, QItemSelection)",
            self.songsSelectionChangedCallback )
        
        self.previous_song_text = None # Song text before last user's edit operation

        self.editor = CustomTextEdit(self)
        
        self.ui.lyric_editor_layout.addWidget(self.editor)
        self.ui.lyric_editor_layout.removeWidget(self.ui.chord_scroll_area)
        self.ui.chord_scroll_area.hide()

        self.editor.setLineWrapMode(int(QtGui.QTextEdit.NoWrap))
        self.c( self.editor, "textChanged()", self.lyricsTextChanged )
        
        self.c( self.ui.transpose_up_button, "clicked()", self.transposeUp )
        self.c( self.ui.transpose_down_button, "clicked()", self.transposeDown )
        self.c( self.ui.new_song_button, "clicked()", self.createNewSong )
        self.c( self.ui.delete_song_button, "clicked()", self.deleteSelectedSongs )
        
        self.c( self.ui.song_title_ef, "textEdited(QString)", self.currentSongTitleEdited )
        self.c( self.ui.song_num_ef, "textEdited(QString)", self.currentSongNumberEdited )
        self.ui.song_num_ef.setValidator( QtGui.QIntValidator(0, 1000000000, self.ui) )
        self.ignore_song_key_changed = False
        self.c( self.ui.song_key_menu, "currentIndexChanged(int)", self.currentSongKeyChanged )
        
        # Menu actions:
        self.ui.actionNewSongbook.triggered.connect(self.newSongbook)
        self.ui.actionOpenSongbook.triggered.connect(self.openSongbook)
        self.ui.actionCloseSongbook.triggered.connect(self.closeSongbook)
        
        self.c( self.ui.actionPrint, "triggered()", self.printSelectedSongs )
        self.c( self.ui.actionQuit, "triggered()", self.ui.close )
        self.c( self.ui.actionNewSong, "triggered()", self.createNewSong )
        self.c( self.ui.actionDeleteSongs, "triggered()", self.deleteSelectedSongs )
        self.c( self.ui.actionExportPdf, "triggered()", self.exportToPdf )
        self.c( self.ui.actionExportText, "triggered()", self.exportToText )
        self.c( self.ui.actionImportText, "triggered()", self.importFromText )
        self.c( self.ui.actionLyricsFont, "triggered()", self.changeLyricsFont )
        self.c( self.ui.actionChordsFont, "triggered()", self.changeChordFont )

        self.ui.actionUndo.triggered.connect(self.undo_stack.undo)
        self.ui.actionRedo.triggered.connect(self.undo_stack.redo)
        
        
        zoom_items = ["150%", "125%", "100%", "80%", "75%", "50%"]
        self.ui.zoom_combo_box.addItems(zoom_items)
        self.c( self.ui.zoom_combo_box, "currentIndexChanged(QString)", self.comboTextSizeChanged)
        self.ui.zoom_combo_box.setCurrentIndex(3) # 80%
        self.ui.zoom_combo_box.setCurrentIndex(2) # 100%
        self.ui.zoom_combo_box.setVisible(False)
        
        self.ignore_song_text_changed = False
        
        
        # The letter/chord that is currently selected:
        self.selected_char_num = None
        # The letter/chord that is currently hover (mouse hoveing over it):
        self.hover_char_num = None
        
        self.lyrics_font = QtGui.QFont("Times New Roman", 18)
        self.lyrics_color = QtGui.QColor("BLACK")
        self.lyrics_font_metrics = QtGui.QFontMetricsF(self.lyrics_font)


        # Font that will be used if no good fonts are found:
        self.chords_font = QtGui.QFont("Times New Roman", 14, QtGui.QFont.Bold)
        
        # Search for a font that can display sharp and flat characters correctly:
        #for name in [
        #    'MS Reference Sans Serif'
        #    'Lucida Sans Unicode', 
        #    'Arial Unicode MS', 
        #        ]:
        #    font = QtGui.QFont(name, 14, QtGui.QFont.Bold)
        #    if font.exactMatch():
        #        self.chords_font = font
        #        break

        self.chords_font_metrics = QtGui.QFontMetricsF(self.chords_font)
        self.chords_color = QtGui.QColor("DARK BLUE")
        self.editor.setFont(self.lyrics_font)
        
        self._orig_keyPressEvent = self.ui.keyPressEvent
        self.ui.keyPressEvent = self.keyPressEvent
        
        self._orig_keyReleaseEvent = self.ui.keyReleaseEvent
        self.ui.keyReleaseEvent = self.keyReleaseEvent

        self._orig_closeEvent = self.ui.closeEvent
        self.ui.closeEvent = self.closeEvent

        #the scale font at first is 1, no change
        self.zoom_factor = 1.0
        
        self.populateSongKeyMenu()
        
        default_db_file1 = os.path.join( exec_dir, "zvuki_neba.songbook" )
        default_db_file2 = os.path.join( exec_dir, "solo_and_group_songs.songbook")
        
        if os.path.isfile(default_db_file1):
            self.setCurrentSongbook(default_db_file1)
        elif os.path.isfile(default_db_file2):
            self.setCurrentSongbook(default_db_file2)
        else:
            self.setCurrentSongbook(None)
        
        self.songs_model.updateFromDatabase()
        
        self.ui.lyric_editor_button.clicked.connect( self.lyricEditorSelected )
        self.ui.chord_editor_button.clicked.connect( self.chordEditorSelected )
        
        self.chordEditorSelected()

        self.updateStates()
    	


    def lyricEditorSelected(self):
        
        self.ui.lyric_editor_button.setDown(True)
        self.ui.chord_editor_button.setDown(False)
        
        if self.current_song:
            self.current_song.setDocMargins()
        
        self.editor.viewport().setCursor( QtCore.Qt.IBeamCursor)

        self.ui.lyrics_editor_label.show()
        self.ui.chords_editor_label.hide()
        self.editor.lyric_editor_mode = True
        self.editor.repaint()
    

    def chordEditorSelected(self):
        
        self.editor.viewport().setCursor( QtGui.QCursor(QtCore.Qt.ArrowCursor) )
        
        self.ui.lyric_editor_button.setDown(False)
        self.ui.chord_editor_button.setDown(True)

        self.ui.lyrics_editor_label.hide()
        self.ui.chords_editor_label.show()
        self.editor.lyric_editor_mode = False
        
        if self.current_song:
            self.current_song.setDocMargins()
        self.editor.repaint()
    
    

    def __del__(self):
        pass
    

    
    def populateSongKeyMenu(self):
        # Populate the song key pull-down menu:
        keys_list = ["None"]

        if self.current_song:
            for note_id, (text, alt_text) in enumerate(self.notes_list):
                if note_id in [3, 8, 10]: # Eb, Ab, or Bb
                    combined_text = alt_text
                else:
                    combined_text = text
                
                keys_list.append(combined_text + u" Major")
                keys_list.append(combined_text + u" Minor")
        
        self.ignore_song_key_changed = True
        self.ui.song_key_menu.clear()
        self.ui.song_key_menu.addItems(keys_list)
        self.ui.song_key_menu.setMaxVisibleItems(25) # Show all keys (including "None")
        self.ignore_song_key_changed = False
        
        self.ui.song_key_menu.setEnabled( bool(self.current_song) )
        
    
    
    def keyPressEvent(self, event):
        """
        Will get called when a key is pressed
        """
        key = event.key()
        if key == Qt.Key_Alt:
            self.editor.optionKeyToggled(True)
             
        if key == Qt.Key_Delete or key == Qt.Key_Backspace:
            self.deleteSelectedChord()
        else:
            if not self.processKeyPressed(key):
                self._orig_keyPressEvent(event)
    
    def keyReleaseEvent(self, event):
        key = event.key()
        if key == Qt.Key_Alt:
            self.editor.optionKeyToggled(False)
        
        self._orig_keyReleaseEvent(event)


    def closeEvent(self, event):
        if self.current_song:
            # Update the current song in the database:
            self.current_song.sendToDatabase()
        self._orig_closeEvent(event)
    
    def deleteSelectedChord(self):
        """
        Deletes the currently selected chord from the song.
        """
        
        if self.selected_char_num != None and self.current_song:
            for chord in self.current_song.iterateAllChords():
                if chord.character_num == self.selected_char_num:
                    self.current_song.deleteChord(chord)
                    break
            
            self.current_song.sendToDatabase()
            self.editor.repaint()
    
    def processKeyPressed(self, key):
        """
        """
        
        if self.selected_char_num == None:
            return False
        
        key_note_dict = {
            Qt.Key_C : 0,
            Qt.Key_D : 2,
            Qt.Key_E : 4,
            Qt.Key_F : 5,
            Qt.Key_G : 7,
            Qt.Key_A : 9,
            Qt.Key_B : 11,
        }
        note_id = key_note_dict.get(key)
        if note_id == None:
            return False        
        
        # Check whether we are editing an existing chord or adding a new one:
        add_new = True
        chord = None
        for iter_chord in self.current_song.iterateAllChords():
            if iter_chord.character_num == self.selected_char_num:
                add_new = False
                chord = iter_chord
                break
        
        if add_new:
            chord_type_id = 0 # Major
            chord = SongChord(self.current_song, self.selected_char_num, note_id, chord_type_id, -1, "", False)
            self.current_song.addChord(chord)
        else:
            if chord.note_id == note_id:
                # Key of the current chord note was pressed, reverse Major/minor:
                if chord.chord_type_id == 0:
                    chord.chord_type_id = 1
                else:
                    chord.chord_type_id = 0
            else:
                # A different note, change to <note> major:
                chord.note_id = note_id
                chord.chord_type_id = 0
                chord.marker = ""
                chord.in_parentheses = False
            #chord.updateChordString()
        
        self.current_song.changed()
        
        self.editor.repaint()
        return True
        
    
    def undo(self):
        self.updateUndoRedo()
        self.editor.repaint()
    
    def redo(self):
        self.updateUndoRedo()
        self.editor.repaint()
    
    def updateUndoRedo(self):
        if self.current_song == None:
            self.undo_possible = False
            self.redo_possible = False
        self.ui.actionUndo.setEnabled(self.undo_possible)
        self.ui.actionRedo.setEnabled(self.redo_possible)
    
    def enableUndo(self):
        pass
    
    def disableUndo(self):
        self.undo_stack.clear()
    
    
    def warning(self, text):
        """ Display a warning dialog box with the given text """
        QtGui.QMessageBox.warning(self.ui, "Warning", text)

    def info(self, text):
        """ Display an information dialog box with the given text """
        QtGui.QMessageBox.information(self.ui, "Information", text)
    
    def error(self, text):
        """ Display an error dialog box with the given text """
        QtGui.QMessageBox.warning(self.ui, "Error", text)

    def setWaitCursor(self):
        """ Set the mouse cursor to the watch """
        self.ui.setCursor( QtGui.QCursor(QtCore.Qt.WaitCursor) )

    def restoreCursor(self):
        """ Set the mouse cursor to the default arrow. """
        self.ui.setCursor( QtGui.QCursor(QtCore.Qt.ArrowCursor) )


    def songsSelectionChangedCallback(self, selected=None, deselected=None):
        """
        Called when the song selection changes.
        """
        
        # Commit any changes in the current song:
        self.curs.commit()
        
        self.selected_char_num = None # Remove the selection
        self.hover_char_num = None # Remove the hover highlighting
        self.updateCurrentSongFromDatabase()
        
        # Sroll the chords table to the top (and left):
        #self.ui.chord_scroll_area.horizontalScrollBar().setValue(0)
        #self.ui.chord_scroll_area.verticalScrollBar().setValue(0)
        
        self.chordEditorSelected()
    
    
    def getSelectedSongIds(self):
        """
        Returns a list of selected songs (their song_ids)
        """

        selected_song_ids = []
        for index in self.ui.songs_view.selectionModel().selectedRows():
            index = self.songs_proxy_model.mapToSource(index)
            song_id = self.songs_model.getRowSongID(index.row())
            selected_song_ids.append(song_id)
        return selected_song_ids
    

    def updateCurrentSongFromDatabase(self):
        """
        Re-reads the current song from the database.
        """
        
        self.setWaitCursor()
        selected_song_ids = self.getSelectedSongIds()
        
        if len(selected_song_ids) == 1:
            song_id = selected_song_ids[0]
            song = Song(self, song_id)
            self.setCurrentSong(song)
        else:
            self.setCurrentSong(None)
        
        self.updateStates()
        self.restoreCursor()
        
    
    def updateStates(self):
        """
        Enable / disable buttons and other widgets as needed.
        """

        selected_song_ids = self.getSelectedSongIds()
        
        if self.current_song == None:
            self.ui.song_title_ef.setText("")
            self.ui.song_num_ef.setText("")
            self.ui.song_key_menu.setCurrentIndex(0) # None
        
        num_selected = len(selected_song_ids)        
        
        self.editor.setEnabled( self.current_song != None )
        self.ui.song_title_ef.setEnabled( self.current_song != None )
        self.ui.song_num_ef.setEnabled( self.current_song != None )
        self.ui.song_key_menu.setEnabled( self.current_song != None )
        self.ui.transpose_up_button.setEnabled( self.current_song != None )
        self.ui.transpose_down_button.setEnabled( self.current_song != None )
        
        self.ui.delete_song_button.setEnabled( num_selected > 0 )
        self.ui.actionDeleteSongs.setEnabled( num_selected > 0 )        
        
        self.ui.actionExportPdf.setEnabled( num_selected > 0 )
        
        self.ui.actionExportText.setEnabled( num_selected == 1 )
        
        self.ui.actionPrint.setEnabled( num_selected > 0 )

        # Whether there is an open songbook:
        songbook_open = (self.curs != None)
        self.ui.actionImportText.setEnabled(songbook_open)
        
        self.ui.new_song_button.setEnabled(songbook_open)
        self.ui.actionNewSong.setEnabled(songbook_open)
        
        self.ui.actionCloseSongbook.setEnabled(songbook_open)
        
        self.updateUndoRedo()
            
    
    def setCurrentSong(self, song):
        """
        Sets the current song to the specified song.
        Reads all song info from the database.
        """
        
        if self.current_song != None:
            # Update the current song in the database
            self.current_song.sendToDatabase()
        
        if song == None:
            self.current_song = None
            self.previous_song_text = None
            self.ui.song_key_menu.setCurrentIndex( 0 )
            self.ui.song_num_ef.setText("")
            
            # Need to save a reference to the doc to prevent a crash on Windows:
            self.empty_doc = QtGui.QTextDocument()
            self.editor.setDocument(self.empty_doc)
            self.editor.verticalScrollBar().setValue(0)
        
        else:
            self.current_song = song
            self.populateSongKeyMenu()
            
            if not self.ignore_song_text_changed:
                song_text = self.current_song.getAllText()
                self.ignore_song_text_changed = False
                self.previous_song_text = song_text

            if self.current_song.key_note_id == -1:
                self.ui.song_key_menu.setCurrentIndex( 0 )
            else:
                self.ui.song_key_menu.setCurrentIndex( self.current_song.key_note_id*2 + self.current_song.key_is_major + 1)
            
            self.ui.song_title_ef.setText(self.current_song.title)
            if self.current_song.number == -1:
                self.ui.song_num_ef.setText("")
            else:
                self.ui.song_num_ef.setText( str(self.current_song.number) )
            
            #song.doc.setDefaultFont(self.lyrics_font)
            self.editor.setDocument(song.doc)
            self.editor.verticalScrollBar().setValue(0)
        
        self.disableUndo()
        
        self.editor.repaint()


    def _transposeCurrentSong(self, steps):
        """
        Transpose the current song up by the specified number of steps.
        """
        
        self.setWaitCursor()
        try:
            self.current_song.transpose(steps)
            self.current_song.changed()
            self.editor.repaint()
        finally:
            self.restoreCursor()
    



    def lyricsTextChanged(self):
        """
        Called when the song lyric text is modified by the user.
        """
        
        if self.ignore_song_text_changed:
            return
        
        if not self.current_song:
            return
        
        self.ignore_song_text_changed = True
        
        song_text = unicode(self.editor.toPlainText())
        
        # Compare the new text to the previous text:
        
        if self.previous_song_text and self.previous_song_text != song_text:
            
            # For each character: key: old position, value: new position
            renumber_map = {}
            
            i = -1
            while True:
                i += 1
                try:
                    if song_text[i] != self.previous_song_text[i]:
                        break
                    else:
                        renumber_map[i] = i
                except IndexError:
                    # Reached end-of-line of either string
                    break
            num_preserved_begin_chars = i
            
            i = 0
            while True:
                i -= 1
                try:
                    if song_text[i] != self.previous_song_text[i]:
                        break
                    else:
                        renumber_map[ len(self.previous_song_text)+i ] = len(song_text)+i
                except IndexError:
                    # Reached end-of-line of either string
                    break
            num_preserved_end_chars = i
            
            
            new_all_chords = []
            for chord in self.current_song.iterateAllChords():
                try:
                    chord.character_num = renumber_map[chord.character_num]
                except KeyError:
                    continue
                else:
                    new_all_chords.append(chord)
            
            # Renumber the selection:
            if self.selected_char_num != None:
                self.selected_char_num = renumber_map.get(self.selected_char_num)
        else:
            # No previous text
            new_all_chords = self.current_song._chords
        
        self.current_song._chords = new_all_chords
        self.previous_song_text = song_text
        
        self.current_song.changed()
        
        self.editor.repaint()
        
        self.ignore_song_text_changed = False
    

    def comboTextSizeChanged(self, new_text):

        self.zoom_factor = int(new_text[:-1]) / 100.0
        if self.current_song:
            self.editor.repaint()
        

    
    def transposeUp(self):
        self._transposeCurrentSong(1)

    def transposeDown(self):
        self._transposeCurrentSong(-1)
    
    def changeChordFont(self):
        """
        Brings up a dialog to let the user modify the chords font.
        """
        new_font, ok = QtGui.QFontDialog.getFont(self.chords_font, self.ui)
        if ok:
            self.chords_font = new_font
            self.chords_font_metrics = QtGui.QFontMetricsF(self.chords_font)
            if self.current_song:
                self.current_song.setDocMargins()
            self.editor.repaint()

    def changeLyricsFont(self):
        """
        Brings up a dialog to let the user modify the lyrics font.
        """
        new_font, ok = QtGui.QFontDialog.getFont(self.lyrics_font, self.ui)
        if ok:
            self.lyrics_font = new_font
            self.lyrics_font_metrics = QtGui.QFontMetricsF(self.lyrics_font)
            self.editor.setFont(self.lyrics_font)
            if self.current_song:
                self.current_song.setDocMargins()
            self.editor.repaint()
        
    
    def printSelectedSongs(self):
        """
        Bring up a print dialog box.
        """
        
        if not self.getSelectedSongIds():
            self.error("No songs are selected")
            return
        
        
        printer = QtGui.QPrinter()
        printer.setFullPage(True)
        printer.setPageSize(QtGui.QPrinter.Letter)
        printer.setOrientation(QtGui.QPrinter.Portrait)
        
        painter = QtGui.QPainter()
        
        print_dialog = QtGui.QPrintDialog(printer, self.ui)
        if print_dialog.exec_() == QtGui.QDialog.Accepted:
            ok = PdfDialog(self).display(self.pdf_options)
            if not ok:
                return
            num_printed = self._paintToPrinter(printer)


    
    def _paintToPrinter(self, printer):
        """
        Paint current songs to the specified QPriner instance.
        """
        
        #print 'from page:', printer.fromPage()
        #print 'page order:', printer.pageOrder()
        #print 'print range:', printer.printRange()

        
        painter = QtGui.QPainter()
        if not painter.begin(printer):
            raise IOError("Failed to open the output file for writing")
        
        # Figure out what the margins should be:
        # Convert to points (from inches):
        left_margin = self.pdf_options.left_margin * 72
        right_margin = self.pdf_options.right_margin * 72
        top_margin = self.pdf_options.top_margin * 72
        bottom_margin = self.pdf_options.bottom_margin * 72
        
        orig_document = self.editor.document()
        
        num_printed = 0
        page_num = 0
        for song_id in self.getSelectedSongIds():
            page_num += 1
            #print 'exporting song_id:', song_id
            if page_num != 1:
                if not printer.newPage():
                    raise IOError("Failed to flush page to disk, disk full?")
            
            song = Song(self, song_id)
            
            
            if self.pdf_options.alternate_margins and page_num != 1:
                left_margin, right_margin = right_margin, left_margin
            
            width = printer.width() #- 300
            height = printer.height() #- 300
            
            self.editor.setDocument(song.doc)
            
            if self.pdf_options.print_4_per_page:
                width  = width // 2
                height = height // 2
                for (x, y) in ( (0,0), (0,1), (1,0), (1,1) ):
                    song_width = width - left_margin - right_margin
                    song_height = height - top_margin - bottom_margin
                    
                    song_top = top_margin + y*height
                    song_left = left_margin + x*width
                    
                    paint_rect = QtCore.QRect(song_left, song_top, song_width, song_height)
                    self.drawSongToRect(song, painter, paint_rect, exporting=True)
            else:
                song_width = width - left_margin - right_margin
                song_height = height - top_margin - bottom_margin
                song_top = top_margin
                song_left = left_margin
                paint_rect = QtCore.QRect(song_left, song_top, song_width, song_height)
                self.drawSongToRect(song, painter, paint_rect, exporting=True)
            num_printed += 1
        
        self.editor.setDocument(orig_document)
        
        painter.end()
        print "Done drawing"
        return num_printed


    def exportToPdf(self, pdf_file=None):
        """
        Exports the selected songs to a PDF file.
        """
        
        #self.setWaitCursor() # For some reason, without this line, the selection is not updated yet when running softchordeditor_test.py
        #if not self.getSelectedSongIds():
        #    self.error("No songs are selected")
        #    return
        
        if not pdf_file:
            ok = PdfDialog(self).display(self.pdf_options)
            if not ok:
                return
            
            if len(self.getSelectedSongIds()) == 1:
                suggested_path = os.path.join( unicode(QtCore.QDir.home().path()), unicode(self.current_song.title) + ".pdf" )
            else:
                suggested_path = QtCore.QDir.home().path()
            
            pdf_file = QtGui.QFileDialog.getSaveFileName(self.ui,
                        "Save PDF file as:",
                        suggested_path,
                        "PDF format (*.pdf)",
            )
        
        if pdf_file: 
            num_exported = 0
            self.setWaitCursor()
            try:
                printer = QtGui.QPrinter()
                printer.setFullPage(True) # considers whole page instead of only printable area.
                printer.setPageSize(QtGui.QPrinter.Letter)
                printer.setOrientation(QtGui.QPrinter.Portrait)
                printer.setOutputFileName(pdf_file)
                printer.setOutputFormat(QtGui.QPrinter.PdfFormat)
                
                num_exported = self._paintToPrinter(printer)
            except Exception, err:
                self.restoreCursor()
                self.error("Error generating PDF:\n%s" % str(err))
                raise
            else:
                if num_exported == 1:
                    num_str = "1 song"
                else:
                    num_str = "%i songs" % num_exported
                self.restoreCursor()
    
    
    
    def exportToText(self, text_file=None):
        """
        Exports the selected song (one) to a TEXT file.
        """
        
        self.setWaitCursor() # For some reason, without this line, the selection is not updated yet when running softchordeditor_test.py
        if not self.getSelectedSongIds():
            self.error("No songs are selected")
            return
        elif len(self.getSelectedSongIds()) > 1:
            self.error("More than one song is selected.")
            return
        
        if not text_file:
            suggested_path = os.path.join( unicode(QtCore.QDir.home().path()), unicode(self.current_song.title) + ".txt" )
            
            text_file = QtGui.QFileDialog.getSaveFileName(self.ui,
                    "Save text file as:",
                    suggested_path,
                    "Text format (*.txt)",
            )
        if text_file:
            self.setWaitCursor()
            try:
                fh = codecs.open( unicode(text_file).encode('utf-8'), 'w', encoding='utf_8_sig') #encoding='utf-8')
                
                #fh = open( unicode(text_file).encode('utf-8'), 'w' )
                
                for song_index, song_id in enumerate(self.getSelectedSongIds()):
                    # NOTE for now there will always be only one song exported.
                    song = Song(self, song_id)
                    
                    # Encode the unicode string as UTF-8 before writing to file:
                    song_text = song.getAsText()

                    # Fix the line endings that that they work on all OSes, including Windows NotePad:
                    song_text = song_text.replace('\n', '\r\n')
                    
                    #song_text = song.getAsText().encode('utf_8_sig')
                    fh.write(song_text)
                
                fh.close()
            finally:
                self.restoreCursor()

    
    def currentSongTitleEdited(self, new_title):
        """
        Called when the user modifies the selected song's title.
        """
        if self.current_song:
            self.current_song.title = unicode(new_title).strip() # Remove any EOL characters, etc.
            self.setWaitCursor()
            try:
                self.curs.execute('UPDATE songs SET title="%s" WHERE id=%i' % (new_title, self.current_song.id))
                self.curs.commit()
                
                selected_row_num = self.songs_model.getSongsRow(self.current_song)
                
                # Update the song table from database:
                self.songs_model.updateFromDatabase()
                
                # Re-select this song:
                source_index = self.songs_model.index(selected_row_num, 0)
                proxy_index = self.songs_proxy_model.mapFromSource(source_index)
                self.ui.songs_view.selectRow(proxy_index.row())
            finally:
                self.restoreCursor()
        
    
    def currentSongNumberEdited(self, new_num_str):
        """
        Called when the user modifies the selected song's number.
        """
        if self.current_song:
            if new_num_str == "":
                new_num_str = -1 # NULL
            try:
                new_num = int(new_num_str)
            except:
                self.error("Invalid song number")
            else:
                self.current_song.number = new_num
                self.curs.execute('UPDATE songs SET number=%i WHERE id=%i' % (new_num, self.current_song.id))
                self.curs.commit()
                
                # Save the selection:
                selected_row_num = self.songs_model.getSongsRow(self.current_song)
                
                # Update the song table from database:
                self.songs_model.updateFromDatabase()
                
                # Re-select this song:
                source_index = self.songs_model.index(selected_row_num, 0)
                proxy_index = self.songs_proxy_model.mapFromSource(source_index)
                self.ui.songs_view.selectRow(proxy_index.row())
            finally:
                self.restoreCursor()
        
    
    def currentSongKeyChanged(self, new_key_index):
        """
        Called when the user modifies the selected song's key.
        """
        
        if self.ignore_song_key_changed:
            return
        
        if self.current_song == None:
            return
        
        song_id = self.current_song.id
        
        if new_key_index == 0:
            note_id = -1
            is_major = 1
        else:
            note_id = (new_key_index-1) // 2
            is_major = (new_key_index-1) % 2
        
        if note_id != self.current_song.key_note_id or is_major != self.current_song.key_is_major:
            self.current_song.key_note_id = note_id
            self.current_song.key_is_major = is_major

            # Do not run this code if the value of the menu is first initialized
            self.current_song.changed()
            self.editor.repaint()

    
    def createNewSong(self):
        """
        Add a new song to the database and the songs table, and select it.
        """
        song_text = ""
        song_number = -1 # NULL
        song_title = ""
        
        row = self.curs.execute("SELECT MAX(id) from songs").fetchone()
        if row[0] == None:
            id = 0
        else:
            id = row[0] + 1
        
        out = self.curs.execute("INSERT INTO songs (id, number, text, title) " + \
                        'VALUES (%i, %i, "%s", "%s")' % (id, song_number, song_text, song_title))
        self.curs.commit()
        
        # Update the song table from database:
        self.songs_model.updateFromDatabase()
        
        # Select the newly added song:
        source_index = self.songs_model.index(self.songs_model.rowCount() - 1, 0)
        proxy_index = self.songs_proxy_model.mapFromSource(source_index)
        self.ui.songs_view.selectRow(proxy_index.row())
        self.updateCurrentSongFromDatabase()
        
        self.lyricEditorSelected()
    
    
    def _deleteSong(self, song_id):
        
        # Delete this song:
        self.curs.execute("DELETE FROM songs WHERE id=%i" % song_id)
        
        # Delete all associated chords:   
        self.curs.execute("DELETE FROM song_chord_link WHERE song_id=%i" % song_id)
        self.curs.commit()


    def deleteSelectedSongs(self):
        """
        Deletes the selected song(s).
        """
        self.setWaitCursor()
        try:
            selected_song_ids = self.getSelectedSongIds()
            
            # Will set the current song to None:
            self.ui.songs_view.selectionModel().clearSelection()
            #self.setCurrentSong(None)
            
            for song_id in selected_song_ids:
                self._deleteSong(song_id)
            
            # Update the song table from database:
            self.songs_model.updateFromDatabase()
        finally:
            self.restoreCursor()
    
    
    
    
    def _drawSongToPainter(self, song, painter, exporting=False):
        """
        """
        
        selection_brush = QtGui.QPalette().highlight()
        hover_brush = QtGui.QColor("light grey")
        
        chars = song.iterateCharDrawPositions()
        
        for char in chars:
            if not exporting:
                if self.hover_char_num == char.song_char_num:
                    # Mouse is currently hovering over this letter:
                    # Draw a hover rectangle:
                    painter.fillRect(char.char_left, char.char_top, char.char_right-char.char_left, char.char_bottom-char.char_top, hover_brush)
                    if char.has_chord:
                        painter.fillRect(char.chord_left, char.chord_top, char.chord_right-char.chord_left, char.chord_bottom-char.chord_top, hover_brush)
                
                if self.selected_char_num == char.song_char_num:
                    # Draw a selection rectangle:
                    painter.fillRect(char.char_left, char.char_top, char.char_right-char.char_left, char.char_bottom-char.char_top, selection_brush)
                    if char.has_chord:
                        painter.fillRect(char.chord_left, char.chord_top, char.chord_right-char.chord_left, char.chord_bottom-char.chord_top, selection_brush)
            

        for char in chars:
            if char.has_chord:
                #chord_text = char.chord.getChordText()
                chord_text = char.chord_text
                painter.setFont(self.chords_font)
                painter.setPen(self.chords_color)

                # FIXME fix this bug:
                #chord_text = chord_text.replace('♭', 'b')
                painter.drawText(char.chord_left, char.chord_top, char.chord_right-char.chord_left, char.chord_bottom-char.chord_top, QtCore.Qt.AlignHCenter, chord_text)
        
        
        painter.setFont(self.lyrics_font)
        painter.setPen(self.lyrics_color)
        
        # Draw the lyrics document:
        doc = self.editor.document()

        
        x = self.editor.horizontalScrollBar().value()
        y = self.editor.verticalScrollBar().value()
        
        painter.translate(-x, -y)

        # Even though we are drawing at 0,0, the text will be drawn with an offset:
        x = -self.left_margin
        y = -self.top_margin
        doc.drawContents( painter, QtCore.QRectF(x, y, 10000.0, 10000.0) )

        painter.translate(x, y)

    


    def drawSongToRect(self, song, output_painter, rect, exporting=False):
        """
        Draws the current song text to the specified rect.

        exporting - whether we are drawing to a PDF/Print instead of the screen.
        """
        
        
        
        # FIXME will not account for chord text:
        te = self.editor
        tf = song.doc.rootFrame()
        layout_bounding_rect = song.doc.documentLayout().frameBoundingRect(tf)

        pic_right = layout_bounding_rect.right()
        pic_bottom = layout_bounding_rect.bottom()
        
        
        # Figure out what the scaling factor should be:
        if not exporting:
            #scale_ratio = self.zoom_factor
            scale_ratio = 1.0 
        else:
            # Exporting, make sure the song fits into the specified <rect>:
            width_ratio = pic_right / rect.width()
            height_ratio = pic_bottom / rect.height()
            scale_ratio = max(width_ratio, height_ratio)
            
            if scale_ratio > 1.0:
                scale_ratio = 1.0 / scale_ratio
            else:
                # Do not make songs any bigger
                scale_ratio = 1.0
        
        
        # Go to songs's reference frame:
        output_painter.translate(rect.left(), rect.top())
        output_painter.scale(scale_ratio, scale_ratio)
        
        self._drawSongToPainter(song, output_painter, exporting)
        
        # Redo the effect of scaling:
        output_painter.scale(1.0/scale_ratio, 1.0/scale_ratio)
        
        # Go to the original reference frame:
        output_painter.translate(-rect.left(), -rect.top())
        
        
    
    def determineClickedLetter(self, x, y, dragging):
        """
        Determine where the specified (local) mouse coordinates position.
        That is, which lyric or chord letter was the mouse above when this
        event happened.
        """
        
        if not self.current_song:
            return None
        
        # Place the coordinates into the songs frame of reference:
        #x -= 20
        #y -= 10
        
        #x -= self.left_margin
        #y -= self.top_margin

        # Scale:
        #x = float(x) / self.zoom_factor
        #y = float(y) / self.zoom_factor
        
        
        for char in self.current_song.iterateCharDrawPositions():
            if y < char.chord_top or y > char.char_bottom:
                continue # Not this line
            
            if y < char.chord_bottom and not dragging:
                # Mouse is over the chord height:
                if char.has_chord and x > char.chord_left and x < char.chord_right:
                    is_chord = True
                    return (is_chord, char.song_char_num)
            else:
                # Mouse is over the lyrics height OR we are dragging
                if x > char.char_left and x < char.char_right:
                    is_chord = False
                    return (is_chord, char.song_char_num)
        
        # Location is NOT on an existing chord or lyric
        
        return None





    
    def processSongCharEdit(self, song_char_num):
        """
        Bring up a dialog that will allow the user to add/modify the chord at
        the specified position.
        """
        
        add_new = True
        chord = None
        for iter_chord in self.current_song.iterateAllChords():
            if iter_chord.character_num == song_char_num:
                add_new = False
                chord = iter_chord
                break
        
        if add_new:
            chord = SongChord(self.current_song, song_char_num, 0, 0, -1, "", False)
        
        ok = ChordDialog(self).display(chord)
        if ok:
            # Ok pressed
            if add_new:
                self.current_song.addChord(chord)
            
            self.current_song.changed()
            
            self.editor.repaint()
                



    


    def importFromText(self, text_file=None):
        """
        Lets the user select a text file to import.
        """
        if not text_file:
            text_files = QtGui.QFileDialog.getOpenFileNames(self.ui,
                    "Select a text file to import",
                    QtCore.QDir.home().path(), # initial dir
                    "Text format (*.txt)",
            )
        else:
            text_files = [text_file]
        
        if text_files:
            self.setWaitCursor()
            try:
                for filename in text_files:
                    # Convert QString to a Python string:
                    filename = unicode(filename)

                    song_title = os.path.splitext(os.path.basename(filename))[0]
                    """
                    try:
                        song_title = song_title.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                           # Try Cyrillic 1251:
                           song_title = song_title.decode('cp1251')
                        except UnicodeDecodeError:
                           song_title = ""
                           print "WARNING File name could not be decoded"
                    """
                    
                    #filename = filename.decode('utf-8')
                    
                    # "rU" makes sure that the line endings are handled properly:
                    
                    text = codecs.open( unicode(filename).encode('utf-8'), 'rU', encoding='utf_8_sig').read()
                    
                    self.importSongFromText(text, song_title)
            finally:
                self.restoreCursor()
    

    def importSongFromText(self, input_text, song_title):
        """
        Adds the song specified with the given text to the database.
        input_text should contain all lines, decoded, in Unicode.
        """
        
        alternative_type_names = {
           "sus" : "sus4",
           "s4" : "sus4",
           "maj7" : "M7",
           "2" : "9",
           "(7)" : "7",
           "dim" : "°",
           "dim7" : "°7",
        }

        # Key: chord type text, value: chord type ID
        self.chord_type_texts_dict = {}
        for id, print_text in enumerate(self.chord_type_prints):
            self.chord_type_texts_dict[print_text] = id
            for alternative_name, official_name in alternative_type_names.iteritems():
                if print_text == official_name:
                    self.chord_type_texts_dict[alternative_name] = id
        
        song_text = input_text.split('\n')
        # Remove the 2 last empty lines:
        if song_text[-1] == "":
            song_text.pop(-1)
        
        # Attempt to derive the song number from the title:
        song_num = -1
        try:
            song_num = int(song_title)
        except:
            pass
        
        song_lines = [] # each item is a tuple of line text and chord list.
        
        
        prev_chords = {}
        for line in song_text:
            #line = line[:-1]
            
            # Attempt to convert the line to chords:
            num_chords = 0
            num_non_chords = 0
            
            tmp_chords = {} # Key: line_char_num, value: converted chord
            tmp_warnings = []
            
            char_num = 0
            
            # Make a list of words:
            words = []
            current_word = ""
            current_word_start = None
            for i, char in enumerate(line):
                if not current_word:
                    # Previous char was a white space
                    if char.isspace():
                        continue
                    else:
                        # Found a word:
                        current_word = char
                        current_word_start = i
                        on_break = False
                else:
                    # Previous char was part of a word
                    if not char.isspace():
                        # Still on the same word
                        current_word += char
                    else:
                        on_break = True
                        words.append( (current_word, current_word_start, i-1) )
                        current_word = None

            if current_word:
                words.append( (current_word, current_word_start, i) )
            
            for word, word_start, word_end in words:
                if word == u'/':
                    num_chords += 1
                    converted_chord = None
                else:
                    try:
                        converted_chord = self.convertChordFromString(word)
                    except ValueError, err:
                        tmp_warnings.append( 'WARNING: %s; chord: "%s"' % (str(err), word) ) #word.encode('utf-8')) )
                        num_non_chords += 1
                    else:
                        chord_middle_char = (word_start + word_end) // 2
                        num_chords += 1
                        tmp_chords[chord_middle_char] = converted_chord
                        char_num += 6
                

            if num_chords > num_non_chords:
                # This is a chords line
                prev_chords = tmp_chords
                for warning_str in tmp_warnings:
                    print '  ', warning_str
            else:
                # This is a lyrics line
                if prev_chords:
                    # Strip the EOF character (not always present):
                    line = line.rstrip()
                    
                    # Add spaces to the end of <line> if necessary:
                    for line_char_num in prev_chords.keys():
                        if line_char_num >= len(line):
                            #print 'Extending line from %i to %i' % (len(line), line_char_num+1)
                            line += ' ' * (line_char_num - len(line) + 1)
                    song_lines.append( (line, prev_chords) )
                else:
                    # The line before was NOT a chords line - no chords for this lyrics line
                    song_lines.append( (line, {}) )
                prev_chords = []
        
        
        # Make a global-reference text and chords dict:
        global_song_text = ""
        global_song_chords = {} # key: position in the global_song_text
        line_start_char_num = 0
        for lyrics, chords_dict in song_lines:
            
            global_song_text += lyrics + '\n'
            for line_char_num, chord in chords_dict.iteritems():
                song_char_num = line_char_num + line_start_char_num
                global_song_chords[song_char_num] = chord
            
            line_start_char_num += len(lyrics) + 1 # 1 for the EOL character
        
        
        
        row = self.curs.execute("SELECT MAX(id) from songs").fetchone()
        if row[0] == None:
            song_id = 0
        else:
            song_id = row[0]+1
        
        # Replace all double quotes with single quotes:
        global_song_text = global_song_text.replace('"', "'")

        self.curs.execute("INSERT INTO songs (id, number, text, title) " + \
            'VALUES (%i, %i, "%s", "%s")' % (song_id, song_num, global_song_text, song_title))
        
        # Get the next available ID:
        row = self.curs.execute("SELECT MAX(id) from song_chord_link").fetchone()
        if row[0] == None:
            chord_id = 0
        else:
            chord_id = row[0]+1
        #chord_id = row[0]+1 if row[0] != None else 0
        
        for song_char_num, chord in global_song_chords.iteritems():
            (marker, note_id, type_id, bass_id, in_parentheses) = chord
            if not marker:
                marker = ""
            
            in_parentheses = int(in_parentheses)
            
            self.curs.execute('INSERT INTO song_chord_link (id, song_id, character_num, note_id, chord_type_id, bass_note_id, marker, in_parentheses) ' + \
                        'VALUES (%i, %i, %i, %i, %i, %i, "%s", %i)' % (chord_id, song_id, song_char_num, note_id, type_id, bass_id, marker, in_parentheses))
            chord_id += 1 # Increment the ID for the next chord.
        self.curs.commit()
        
        # Update the song table from database:
        self.songs_model.updateFromDatabase()
        
        # FIXME #index = self.songs_proxy_model.mapToSource(index)
        self.ui.songs_view.selectRow( self.songs_model.rowCount()-1 )


    def convertChordFromString(self, chord_str):
        """
        Convert the specified chord string to a note_id, chord_type_id, and a bass_note_id.
        """
        
        input_chord_str = chord_str[:]
        
        in_parentheses = chord_str.startswith('(') and chord_str.endswith(')')
        if in_parentheses:
            chord_str = chord_str[1:-1]
        
        marker = None
        
        colon = chord_str.find(':')
        if colon != -1:
            if colon == len(chord_str)-1:
                raise ValueError("Not a chord (nothing after a colon")
            
            marker = chord_str[:colon]
            chord_str = chord_str[colon+1:]
        
        slash = chord_str.find('/')
        if slash != -1:
            bass_str = chord_str[slash+1:]
            chord_str = chord_str[:slash]
            if len(chord_str) == 0:
                raise ValueError("No characters present before the bass slash")
            if len(bass_str) == 0:
                raise ValueError("No character present after the bass slash")
        else:
            bass_str = None
        
        if chord_str[0] == u'Е': # Russian letter
            chord_str = 'E' + chord_str[1:]
        if chord_str[0] == u'С': # Russian letter
            chord_str = 'C' + chord_str[1:]
        if chord_str[0] == u'В': # Russian letter
            chord_str = 'B' + chord_str[1:]
        if chord_str[0] == u'А': # Russian letter
            chord_str = 'A' + chord_str[1:]
        if chord_str[0] == 'H': # European style (H instead of B)
            chord_str = 'B' + chord_str[1:]
        
        if chord_str[0] in [u'A', u'B', u'C', u'D', u'E', u'F', u'G']:
            if len(chord_str) > 1 and chord_str[1] in [u'#', u'b', u'♭', u'♯']:
                note = chord_str[:2]
                type = chord_str[2:]
            else:
                note = chord_str[0]
                type = chord_str[1:]
        else:
            raise ValueError("First chord letter is not a note")
        
        if len(note) > 1:
            if note[1] == u'#':
                note = note[0] + u'♯'
            elif note[1] == u'b':
                note = note[0] + u'♭'
        if bass_str and len(bass_str) > 1:
            if bass_str[1] == u'#':
                bass_str = bass_str[0] + u'♯'
            elif bass_str[1] == u'b':
                bass_str = bass_str[0] + u'♭'
        
        note_id = self.note_text_id_dict[note]
        if bass_str != None:
            try:
                bass_id = self.note_text_id_dict[bass_str]
            except KeyError:
                raise ValueError("Unrecognized bass note string")
        else:
            bass_id = -1
        
        try:
            type_id = self.chord_type_texts_dict[type]
        except KeyError:
            raise ValueError("Unkown chord type")
        
        return (marker, note_id, type_id, bass_id, in_parentheses)

    
    def setCurrentSongbook(self, filename):
        self.ui.songs_view.selectionModel().clearSelection()
        # Send the current song to database:
        self.setCurrentSong(None)
        
        if filename == None:
            self.curs = None
        else:
            #self.info('Database: %s; exists: %s' % (db_file, os.path.isfile(filename)))
            self.curs = sqlite3.connect(filename)
        
        self.songs_model.updateFromDatabase()
        self.updateStates()
        
        
    def newSongbook(self):
        db_file = QtGui.QFileDialog.getSaveFileName(self.ui,
                    "Save songbook as:",
                    QtCore.QDir.home().path(), # initial dir
                    "Songbook format (*.songbook)",
        )
        if db_file:
            # Overwrite a previous songbook (if any):
            if os.path.isfile(db_file):
                os.remove(db_file)

            # Open an empty satabase:
            self.curs = sqlite3.connect(unicode(db_file))

            self.curs.execute("CREATE TABLE song_chord_link(id INTEGER PRIMARY KEY, song_id INTEGER, character_num INTEGER, note_id INTEGER, chord_type_id INTEGER, bass_note_id INTEGER, marker TEXT, in_parentheses INTEGER)")
            self.curs.execute("CREATE TABLE songs (id INTEGER PRIMARY KEY, number INTEGER, text TEXT, title TEXT, key_note_id INTEGER, key_is_major INTEGER)")
            self.setCurrentSongbook( unicode(db_file) )
        
    
    def openSongbook(self):
        db_file = QtGui.QFileDialog.getOpenFileName(self.ui,
                "Select a songbook to open",
                QtCore.QDir.home().path(), # initial dir
                "Songbook format (*.songbook)",
        )
        if db_file:
            self.setCurrentSongbook( unicode(db_file) )
    
    def closeSongbook(self):
        if self.current_song:
            # Send the current song to the database:
            self.setCurrentSong(None)
        self.setCurrentSongbook(None)



def main():
    """
    The main event loop. This function is also run by the Windows executable.
    """

    qapp = QtGui.QApplication(sys.argv)
    app = App()
    app.ui.show()
    app.ui.raise_()
    if len(sys.argv) > 1:
        if sys.argv[1].endswith(".songbook"):
            app.setCurrentSongbook(sys.argv[1])
        else:
            for filename in sys.argv[1:]:
               app.importFromText(filename)
    sys.exit(qapp.exec_())


if __name__ == "__main__":
    main()


#EOF
