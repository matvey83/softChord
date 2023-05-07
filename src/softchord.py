"""

The main source file for softChord (previously softChord Editor)

Writen by: Matvey Adzhigirey
Development started in 10 December 2010

"""

# NOTE The sqlite3 is intentionally used instead of QtSql.

from PyQt6 import QtCore, QtGui, QtWidgets, uic
from PyQt6.QtCore import Qt
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtGui import QPageSize

PageSizeId = QPageSize.PageSizeId
import sys, os
import sqlite3
import codecs
import copy
import shutil
import platform
import traceback

# FIXME Make this an option? Or save into the songbook file?
PRINT_SONGBOOK = False

# For Zvuki Neba songbook:
if PRINT_SONGBOOK:
    LYRICS_SIZE = 11  # 14
    CHORDS_SIZE = 7  # 9
else:
    # For full-page printout:
    LYRICS_SIZE = 20  # 14
    CHORDS_SIZE = 12  # 9

CHORDS_COLOR = "BLACK"
CHORDS_COLOR = "BLUE"

PREFER_SHARPS, PREFER_FLATS, PREFER_NEITHER = range(3)

chord_types_list = [
    (0, "Major", u""),
    (1, "Minor", u"m"),
    (2, "Suspended 4th", u"sus4"),
    (3, "Major 7th", u"M7"),
    (4, "Minor 7th", u"m7"),
    (5, "Dominant 7th", u"7"),
    (6, "Add 9", u"9"),
    (7, "Augmented", u"aug"),
    (8, "Major 6th", u"6"),
    (9, "Minor 6th", u"m6"),
    (10, "11th", u"11"),
    (11, "Diminished", u"°"),
    (12, "Diminished 7th", u"°7"),
]

# Alternative text for chord types (for parsing text):
alternative_type_names = {
    "sus": "sus4",
    "s4": "sus4",
    "maj7": "M7",
    "2": "9",
    "(7)": "7",
    "dim": "°",
    "dim7": "°7",
}

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

# File extensions that can be used for the ChordPro file format:
chordpro_extensions = [".pro", ".chopro", ".chordpro", ".cpm"]

#print 'dir executable:', dir(sys.executable)
if not os.path.basename(sys.executable).lower().startswith("python"):
    exec_dir = os.path.dirname(sys.executable)
else:
    exec_dir = "."

# script_ui_file = os.path.join(exec_dir, "softchord_main_window.ui" )
# chord_dialog_ui_file = os.path.join(exec_dir, "softchord_chord_dialog.ui")
# pdf_dialog_ui_file = os.path.join(exec_dir, "softchord_pdf_dialog.ui")

import softchord_main_window_ui, softchord_chord_dialog_ui, softchord_pdf_dialog_ui

paper_sizes_list = [
    (PageSizeId.Letter, "Letter (8.5 x 11 inches, 216 x 279 mm)"),
    (PageSizeId.Legal, "Legal (8.5 x 14 inches, 216 x 356 mm)"),
    (PageSizeId.A0, "A0 (841 x 1189 mm)"),
    (PageSizeId.A1, "A1 (94 x 841 mm)"),
    (PageSizeId.A2, "A2 (420 x 594 mm)"),
    (PageSizeId.A3, "A3 (297 x 420 mm)"),
    (PageSizeId.A4, "A4 (210 x 297 mm, 8.26 x 11.69 inches)"),
    (PageSizeId.A5, "A5 (148 x 210 mm)"),
    (PageSizeId.A6, "A6 (105 x 148 mm)"),
    (PageSizeId.A7, "A7 (74 x 105 mm)"),
    (PageSizeId.A8, "A8 (52 x 74 mm)"),
    (PageSizeId.A9, "A9 (37 x 52 mm)"),
    (PageSizeId.B0, "B0 (1030 x 1456 mm)"),
    (PageSizeId.B1, "B1 (728 x 1030 mm)"),
    (PageSizeId.B2, "B2 (515 x 728 mm)"),
    (PageSizeId.B3, "B3 (364 x 515 mm)"),
    (PageSizeId.B4, "B4 (257 x 364 mm)"),
    (PageSizeId.B5, "B5 (182 x 257 mm, 7.17 x 10.13 inches)"),
    (PageSizeId.B6, "B6 (128 x 182 mm)"),
    (PageSizeId.B7, "B7 (91 x 128 mm)"),
    (PageSizeId.B8, "B8 (64 x 91 mm)"),
    (PageSizeId.B9, "B9 (45 x 64 mm)"),
    (PageSizeId.B10, "B10 (32 x 45 mm)"),
    (PageSizeId.C5E, "C5E (163 x 229 mm)"),
    (PageSizeId.Comm10E, "Comm10E (105 x 241 mm, U.S. Common 10 Envelope)"),
    (PageSizeId.DLE, "DLE (110 x 220 mm)"),
    (PageSizeId.Executive, "Executive (7.5 x 10 inches, 191 x 254 mm)"),
    (PageSizeId.Folio, "Folio (210 x 330 mm)"),
    (PageSizeId.Ledger, "Ledger (432 x 279 mm)"),
    (PageSizeId.Tabloid, "Tabloid (279 x 432 mm)"),
]


def replace_russian_characeters(text):
    modified_text = ""

    # FIXME Use the built-in replace method instead
    for char in text:
        if char == u'Е':  # Russian letter
            char = 'E'
        if char == u'С':  # Russian letter
            char = 'C'
        if char == u'В':  # Russian letter
            char = 'B'
        if char == u'А':  # Russian letter
            char = 'A'
        if char == 'H':  # European style (H instead of B)
            char = 'B'
        if char == 'Н':  # Russian letter "N" (H instead of B)
            char = 'B'
        modified_text += char

    return modified_text


class AddChordCommand(QtGui.QUndoCommand):

    def __init__(self, song, chord):
        QtGui.QUndoCommand.__init__(self)
        self.song = song
        self.chord = chord

    def undo(self):
        self.song._deleteChord(self.chord)

    def redo(self):
        self.song._addChord(self.chord)


class DeleteChordCommand(QtGui.QUndoCommand):

    def __init__(self, song, chord):
        QtGui.QUndoCommand.__init__(self)
        self.song = song
        self.chord = chord

    def undo(self):
        self.song._addChord(self.chord)

    def redo(self):
        self.song._deleteChord(self.chord)


class ReplaceChordCommand(QtGui.QUndoCommand):

    def __init__(self, song, prev_chord, new_chord):
        QtGui.QUndoCommand.__init__(self)
        self.song = song
        self.prev_chord = prev_chord
        self.new_chord = new_chord

    def undo(self):
        self.song._replaceChord(self.new_chord, self.prev_chord)

    def redo(self):
        self.song._replaceChord(self.prev_chord, self.new_chord)


class DeleteSongsCommand(QtGui.QUndoCommand):

    def __init__(self, app, song_ids):
        QtGui.QUndoCommand.__init__(self)

        self.app = app
        self.songs = []
        for song_id in song_ids:
            # Load the song from the database:
            song = Song(app, song_id)
            self.songs.append(song)

    def undo(self):
        """
        Re-add the deleted song to the database.
        """

        self.app.setWaitCursor()
        try:
            # Get the next available song_chord_link ID:
            row = self.app.curs.execute(
                "SELECT MAX(id) from song_chord_link").fetchone()
            if row[0] == None:
                chord_id = 0
            else:
                chord_id = row[0] + 1

            for song in self.songs:
                song_text = song.getAllText()
                self.app.curs.execute(
                    "INSERT INTO songs (id, number, title, subtitle, text) VALUES (?, ?, ?, ?, ?)",
                    (song.id, song.number, song.title, song.subtitle,
                     song_text))

                # Re-add all the chords:
                for chord in song.iterateAllChords():
                    self.app.curs.execute("INSERT INTO song_chord_link (song_id, character_num, note_id, chord_type_id, bass_note_id, marker, in_parentheses) " + \
                                "VALUES (?, ?, ?, ?, ?, ?, ?)", (chord.song_id, chord.character_num, chord.note_id, chord.chord_type_id, chord.bass_note_id, chord.marker, chord.in_parentheses))
                    chord_id += 1  # Increment the ID for the next chord.

            # Commit database changes:
            self.app.curs.commit()

            # Update the song table from database:
            self.app.songs_model.updateFromDatabase()

        finally:
            self.app.restoreCursor()

    def redo(self):
        """
        Delete the song form the database again
        """

        self.app.setWaitCursor()
        try:
            for song in self.songs:
                # Delete this song:
                self.app.curs.execute("DELETE FROM songs WHERE id=%i" % song.id)

                # Delete all associated chords:
                self.app.curs.execute(
                    "DELETE FROM song_chord_link WHERE song_id=%i" % song.id)

            # Commit database changes:
            self.app.curs.commit()

            # Update the song table from database:
            self.app.songs_model.updateFromDatabase()

            #print 'redo done'
        finally:
            self.app.restoreCursor()


"""
class SvgTextObject(QObject, public QTextObjectInterface
     {
              Q_OBJECT
                   Q_INTERFACES(QTextObjectInterface)

                    public:
                         QSizeF intrinsicSize(QTextDocument *doc, int posInDocument,
                                                   const QTextFormat &format);
                              void drawObject(QPainter *painter, const QRectF &rect, QTextDocument *doc,
                                                   int posInDocument, const QTextFormat &format);
                               };

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


class SongsTableRow:

    def __init__(self, id, number, title):
        self.id = id
        self.number = number
        self.title = title


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
        self.layoutAboutToBeChanged.emit()

        self._data = []
        if self.app.curs:
            # A songbook is currently open
            for row in self.app.curs.execute(
                    "SELECT id, number, title FROM songs ORDER BY id"):
                rowobj = SongsTableRow(row[0], row[1], row[2])
                self._data.append(rowobj)

        self.layoutChanged.emit()  # Forces the view to redraw

    def rowCount(self, parent=QtCore.QModelIndex()):
        """ Returns number of rows """
        return len(self._data)

    def columnCount(self, parent=QtCore.QModelIndex()):
        """ Returns number of columns """
        return len(self.header_list)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """
        Given a cell index, returns the data that should be displayed in that
        cell (text or check button state). Used by the view.
        """

        if role == Qt.ItemDataRole.DisplayRole:
            rowobj = self._data[index.row()]
            col = index.column()
            if col == 0:
                if rowobj.number == -1:  # Invalid song number
                    return QtCore.QVariant("")
                else:
                    return QtCore.QVariant(rowobj.number)

            elif col == 1:
                return QtCore.QVariant(rowobj.title)

        return QtCore.QVariant()

    def headerData(self, section, orientation, role):
        """
        Returns the string that should be displayed in the specified header
        cell. Used by the View.
        """
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self.header_list[section]
            else:
                return None  # Do not vertical header
                rowobj = self._data[section]
                return rowobj.id
        return None

    def getRow(self, row):
        return self._data[row]

    def setRow(self, rownum, rowobj):
        self._data[rownum] = rowobj

        self.dataChanged.emit(self.index(rownum, 0),
                              self.index(rownum,
                                         self.columnCount() - 1))

    def getRowSongID(self, row):
        """
        Returns the database ID of the selected song (by row number).
        """
        return self._data[row].id

    def getSongsRow(self, song):
        for i, row in enumerate(self._data):
            if row.id == song.id:
                return i
        raise ValueError("No such song in the model")

    def getTitleAndNumFromId(self, id):
        for rowobj in self._data:
            if rowobj.id == id:
                return rowobj.title, rowobj.number
        raise ValueError("No such Song ID in table")

    def getAllSongIds(self):
        return [song.id for song in self._data]


class SongsProxyModel(QtCore.QSortFilterProxyModel):
    """ 
    Proxy model that allows showing/hiding rows in the songs table.
    """

    def __init__(self, app):
        self.app = app
        super().__init__(app.win)

    def filterAcceptsRow(self, sourceRow, sourceParent):
        model = self.sourceModel()

        filter_string = self.app.filter_string

        if not filter_string:
            return True

        rowobj = model.getRow(sourceRow)

        if QtCore.QString(rowobj.title).contains(filter_string,
                                                 Qt.CaseInsensitive):
            return True

        if rowobj.number != -1:
            if QtCore.QString(str(rowobj.number)).contains(
                    filter_string, Qt.CaseInsensitive):
                return True

        return False

    def lessThan(self, left, right):
        leftData = self.sourceModel().data(left)
        rightData = self.sourceModel().data(right)
        return False  # FIXME
        # Convert strings to floats:
        leftDataFloat, leftOk = leftData.toFloat()
        rightDataFloat, rightOk = rightData.toFloat()
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

    def __init__(self, song, character_num, note_id, chord_type_id,
                 bass_note_id, marker, in_parentheses):
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

    def getChordText(self):
        """
        Returns string of the chord.
        For example, "Fm" or "Bbsus4"
        """
        note_text = self.song._getNoteString(self.note_id)

        chord_type_text = self.app.chord_type_prints[self.chord_type_id]

        # Convert the chord note and type to a text string:
        if self.marker:  # Not NULL
            # Add the chord prefix (example: "1:", "2:")

            chord_str = '%s:%s%s' % (self.marker, note_text, chord_type_text)
        else:
            chord_str = '%s%s' % (note_text, chord_type_text)

        # Add the bass note (if any):
        if self.bass_note_id != -1:  # Not NULL
            bass_note_text = self.song._getNoteString(self.bass_note_id)
            chord_str += "/%s" % bass_note_text

        # Add parentheses (if any):
        if self.in_parentheses:
            chord_str = "(%s)" % chord_str

        return chord_str


class SongChar:
    """
    This class holds the paint bounds information for this character and its chord (if any).
    """

    def __init__(self, text, song_char_num, chord, char_left, char_right,
                 chord_left, chord_right):
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
        self.prefer = PREFER_NEITHER
        self.key_note_id = -1  # Main key note
        self.key_is_major = -1  # Major or minor?
        self.alt_key_note_id = -1  # Alternative key note

        self.updateSongFromDatabase()
        self.updateSharpsOrFlats()

    def updateSongFromDatabase(self):
        """
        Read this song from the database, and populate the instnces properties.
        """

        # Read the song from the database:
        try:
            row = self.app.curs.execute(
                "SELECT number, title, subtitle, text, key_note_id, key_is_major, alt_key_note_id FROM songs WHERE id=%i"
                % self.id).fetchone()
        except sqlite3.OperationalError:
            # Old formatted songbook file
            row = self.app.curs.execute(
                "SELECT title, number, text, key_note_id, key_is_major FROM songs WHERE id=%i"
                % self.id).fetchone()
            # Create this prop
            self.app.curs.execute(
                "ALTER TABLE songs ADD alt_key_note_id INTEGER")
            self.app.curs.commit()
            print("Table songs: created alt_key_note_id and subtitle columns")
            # Re-try once the missing columns have been added:
            row = self.app.curs.execute(
                "SELECT number, title, subtitle, text, key_note_id, key_is_major, alt_key_note_id FROM songs WHERE id=%i"
                % self.id).fetchone()

        self.number = row[0]
        self.title = row[1]
        self.subtitle = row[2]
        if self.subtitle == None:
            self.subtitle = ""

        all_text = row[3]

        self.key_note_id = row[4]  # Can be None or -1
        if self.key_note_id == None:
            self.key_note_id = -1

        #print 'saved in database key_is_major:', row[5], 'type:', type(row[5])
        self.key_is_major = row[5]
        if self.key_is_major == None:
            self.key_is_major = -1

        self.alt_key_note_id = row[6]
        if self.alt_key_note_id == None:
            self.alt_key_note_id = -1

        # Read the chords for this song form the database:
        song_chords = []
        for row in self.app.curs.execute(
                "SELECT id, character_num, note_id, chord_type_id, bass_note_id, marker, in_parentheses FROM song_chord_link WHERE song_id=%i"
                % self.id):
            id = row[0]
            song_char_num = row[1]
            note_id = row[2]
            chord_type_id = row[3]
            bass_note_id = row[4]
            marker = row[5]
            in_parentheses = row[6]
            chord = SongChord(self, song_char_num, note_id, chord_type_id,
                              bass_note_id, marker, in_parentheses)
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

        chords_height, lyrics_height, line_height = self.app.getHeightsWithChords(
        )
        with_chords_top_margin = line_height - lyrics_height

        with_chords_top_margin *= 1.03  # Add some spacing between lines (that have chords

        # Set the margin for the first line (the top of the document):
        # NOTE: We are always setting the top margin for the first line with the assumption that
        # the first line always has chords on it. This assumption is often valid, and also
        # lets us avoid some issues.
        root_frame = self.doc.rootFrame()
        frame_format = root_frame.frameFormat()
        frame_format.setTopMargin(with_chords_top_margin +
                                  self.app.doc_editor_offset)
        root_frame.setFrameFormat(frame_format)

        block = self.doc.begin()

        with_chords_format = block.blockFormat()
        with_chords_format.setTopMargin(with_chords_top_margin)
        with_chords_format.setLeftMargin(self.app.doc_editor_offset)

        without_chords_format = block.blockFormat()
        without_chords_format.setTopMargin(0.0)
        without_chords_format.setLeftMargin(self.app.doc_editor_offset)

        linenum = -1
        line_start_char = 0
        for line_text in self.iterateLineTexts():
            linenum += 1
            line_end_char = line_start_char + len(line_text)

            # Figure out whether this line has chords, and need to be made taller:
            line_has_chords = False
            for chord_num in chords_by_char.keys():
                if chord_num >= line_start_char and chord_num <= line_end_char:
                    line_has_chords = True
                    break

            # Set the height of this line:
            cursor = QtGui.QTextCursor(block)

            if line_has_chords:
                cursor.setBlockFormat(with_chords_format)
            else:
                cursor.setBlockFormat(without_chords_format)

            if block == self.doc.end():
                break

            # block = next(iter(block))
            block = block.next()

            line_start_char += len(
                line_text) + 1  # Add the eof-of-line character

        self.app.ignore_song_text_changed = False

    def _getNoteString(self, note_id):
        """
        Returns the specified note as a string, using sharps vs flats
        as appropriate.
        """

        note_text, note_alt_text = self.app.notes_list[note_id]

        if self.prefer == PREFER_SHARPS:
            return note_text
        elif self.prefer == PREFER_FLATS:
            return note_alt_text
        else:
            if note_id in [1, 6]:
                # C#, F#
                return note_text
            else:
                # Bb, Eb, Ab
                return note_alt_text

    def addChord(self, chord):
        self.app.undo_stack.push(AddChordCommand(self, chord))

    def _addChord(self, chord):
        self._chords.append(chord)
        self.updateSharpsOrFlats()

        # This is important for undo/redo to move the selection:
        self.app.selected_char_num = chord.character_num

        # Update the margin of the document in case the chord was moved to a new line:
        self.setDocMargins()

        self.app.editor.viewport().update()

    def deleteChord(self, chord):
        self.app.undo_stack.push(DeleteChordCommand(self, chord))

    def _deleteChord(self, chord):
        self._chords.remove(chord)
        self.updateSharpsOrFlats()

        # FIXME If the chord is last in line, delete white space on the line, if any was added
        # just to align this chord. Happens often when importing songs from Text.

        # Update the margin of the document in case the chord was moved to a new line:
        self.setDocMargins()

        self.app.editor.viewport().update()

    def replaceChord(self, prev_chord, new_chord):
        command = ReplaceChordCommand(self, prev_chord, new_chord)
        self.app.undo_stack.push(command)

    def _replaceChord(self, prev_chord, new_chord):
        self._chords.remove(prev_chord)
        self._chords.append(new_chord)
        self.updateSharpsOrFlats()

        # This is important for undo/redo to move the selection:
        self.app.selected_char_num = new_chord.character_num

        # Update the margin of the document in case the chord was moved to a new line:
        self.setDocMargins()

        self.app.editor.viewport().update()

    def copyChord(self, chord, new_song_char_num):
        """
        Copy the specified chord to a new position.
        Wrapper for the addChord() method.
        """

        new_chord = copy.copy(chord)
        new_chord.character_num = new_song_char_num
        self.addChord(new_chord)
        return new_chord

    def getAllText(self):

        song_text = self.doc.toPlainText()
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

    def getLineHasChords(self, linenum):

        chords_present = False
        for chord in self._chords:
            chord_linenum, line_char_num = self.songCharToLineChar(
                chord.character_num)
            if chord_linenum == linenum:
                chords_present = True
                break

        return chords_present

    def getLineHeights(self, linenum):
        """
        Returns top & bottom y positions of the chords and lyrics texts
        for the specified line.
        """

        if self.getLineHasChords(linenum):
            return self.app.getHeightsWithChords()
        else:
            return self.app.getHeightsWithoutChords()

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
            if song_char_num < line_global_end - 1:
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
                out_char_num += len(
                    line_text) + 1  # Add one for the end-of-line character
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

        song_text = ''
        self.updateSharpsOrFlats()

        #for linenum, line_text in enumerate(self.iterateLineTexts()):

        lines = self.getAllText().split("\n")
        for linenum, line_text in enumerate(lines):

            if self.getLineHasChords(linenum):
                # Add the chords line above this line

                line_chord_text_list = [u' '] * len(
                    line_text)  # FIXME add a few to the end???

                # Figure out the lyric letter for the mouse location:
                song_char_num = -1
                for line_char_num in range(len(line_text)):
                    song_char_num = self.lineCharToSongChar(
                        linenum, line_char_num)

                    # Figure out if a chord is attached to this letter:
                    for chord in self.iterateAllChords():
                        chord_song_char_num = chord.character_num
                        chord_linenum, line_char_num = self.songCharToLineChar(
                            chord_song_char_num)

                        if chord_linenum != linenum:
                            continue

                        chord_text = chord.getChordText()

                        chord_len = len(chord_text)
                        chord_left = line_char_num - (chord_len // 2)
                        if not (chord_len % 2):  # Even number of characters:
                            # Offset the chord so that the chord-letter is closer to the middle of the chord text
                            chord_left += 1
                        chord_right = chord_left + chord_len

                        # Make sure that the chord does not go beyond the start-of-line:
                        while chord_left < 0:
                            chord_left += 1
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

    def getAsChordProText(self):
        """
        Return a ChordPro text string for this song.
        """

        self.updateSharpsOrFlats()

        all_text = self.getAllText()

        curr_char_num = 0
        converted_text = ''

        if self.title:
            converted_text += "{title:%s}\n" % self.title
        if self.number or self.subtitle:
            converted_text += "{subtitle:%i %s}\n" % (self.number,
                                                      self.subtitle)

        # Make a dict of chord strings (keyed by chord position in the song text:
        chord_texts_by_char_nums = {}
        for chord in self.iterateAllChords():
            chord_song_char_num = chord.character_num
            chord_text = chord.getChordText()

            # Replace "♯" with "#" and "♭" with "b":
            chord_text = chord_text.replace("♯", "#").replace("♭", "b")

            chord_texts_by_char_nums[chord_song_char_num] = chord_text

        for curr_char_num, char in enumerate(all_text):
            if curr_char_num in chord_texts_by_char_nums:
                converted_text += "[%s]" % chord_texts_by_char_nums[
                    curr_char_num]
            converted_text += char

        return converted_text

    def transpose(self, steps):
        for chord in self.iterateAllChords():
            chord.transpose(steps)

        if self.key_note_id != -1:
            self.key_note_id = transpose_note(self.key_note_id, steps)

        # NOTE: Do NOT transpose the alternative key (but perhaps change it?)
        #if self.alt_key_note_id != -1:
        #    self.alt_key_note_id = transpose_note(self.alt_key_note_id, steps)

        self.updateSharpsOrFlats()

    def sendToDatabase(self):
        """
        Save this song to the database.
        """

        self.app.setWaitCursor()
        try:
            chords_in_database = []
            for row in self.app.curs.execute(
                    "SELECT character_num FROM song_chord_link WHERE song_id=%i"
                    % self.id):
                chords_in_database.append(row[0])

            for chord in self.iterateAllChords():
                # Update existing chords
                if chord.character_num in chords_in_database:
                    self.app.curs.execute(
                        "UPDATE song_chord_link SET note_id=?, chord_type_id=?, bass_note_id=?, marker=?, in_parentheses=? WHERE song_id=? AND character_num=?",
                        (chord.note_id, chord.chord_type_id, chord.bass_note_id,
                         chord.marker, chord.in_parentheses, chord.song_id,
                         chord.character_num))
                    chords_in_database.remove(chord.character_num)

                else:
                    # Add new chords
                    self.app.curs.execute("INSERT INTO song_chord_link (song_id, character_num, note_id, chord_type_id, bass_note_id, marker, in_parentheses) " + \
                            "VALUES (?, ?, ?, ?, ?, ?, ?)", (chord.song_id, chord.character_num, chord.note_id, chord.chord_type_id, chord.bass_note_id, chord.marker, chord.in_parentheses))

            # Remove old chords
            for song_char_num in chords_in_database:
                self.app.curs.execute(
                    "DELETE FROM song_chord_link WHERE song_id=%i AND character_num=%i"
                    % (self.id, song_char_num))

            #print 'saving to database song_num:', self.number, 'key_is_major:', self.key_is_major
            self.app.curs.execute(
                "UPDATE songs SET number=?, title=?, subtitle=?, text=?, key_note_id=?, key_is_major=?, alt_key_note_id=? WHERE id=?",
                (self.number, self.title, self.subtitle, self.getAllText(),
                 self.key_note_id, self.key_is_major, self.alt_key_note_id,
                 self.id))
            self.app.curs.commit()
        finally:
            self.app.restoreCursor()

    def updateSharpsOrFlats(self):
        """
        Determines whether this song prefers notes to be displayed with flats
        or with sharps, and updates this song.
        """

        num_prefer_sharp = 0
        num_prefer_flat = 0
        for chord in self.iterateAllChords():
            if chord.note_id in [1, 6]:  # C# or F#
                num_prefer_sharp += 1
            elif chord.note_id in [3, 10]:  # Eb or Bb
                num_prefer_flat += 1

        if num_prefer_sharp > num_prefer_flat:
            self.prefer = PREFER_SHARPS
        elif num_prefer_sharp < num_prefer_flat:
            self.prefer = PREFER_FLATS
        else:
            self.prefer = PREFER_NEITHER

    def removeTrailingSpaces(self):
        """
        Remove trailing spaces from every line of the song.
        """

        original_text = self.getAllText()

        # Make a list of characters that have chords associtated with them, so that we don't delete them by accident:
        chars_used_for_chords = []
        for chord in self.iterateAllChords():
            chars_used_for_chords.append(chord.character_num)

        all_song_delete_positions = []

        # Make a list of characters that are to be deleted:
        wait_for_next_line = False
        char_num = len(original_text)
        for char in reversed(original_text):
            char_num -= 1
            if wait_for_next_line:
                if char == "\n":
                    wait_for_next_line = False
            elif char == "\n":
                # Another new line (or new line at end of song)
                continue
            else:
                if char == " " and not char_num in chars_used_for_chords:
                    all_song_delete_positions.append(char_num)
                else:
                    wait_for_next_line = True

        # Delete trailing spaces and Create a renumber map
        renumber_map = {}
        num_deleted_chars = 0
        modified_text = ""
        for char_num, char in enumerate(original_text):
            if char_num in all_song_delete_positions:
                num_deleted_chars += 1
            else:
                renumber_map[char_num] = char_num - num_deleted_chars
                modified_text += char

        # print "Number of characters deleted from this song:", len(all_song_delete_positions)
        # print "Number of characters in original_text:", len(original_text)

        # Renumber the chords based on the renumber_map:
        new_all_chords = []
        for chord in self.iterateAllChords():
            try:
                chord.new_character_num = renumber_map[chord.character_num]
            except KeyError:
                continue
            else:
                new_all_chords.append(chord)

        # Update the database:

        for chord in new_all_chords:
            self.app.curs.execute(
                "UPDATE song_chord_link SET character_num=? WHERE song_id=? AND character_num=?",
                (chord.new_character_num, chord.song_id, chord.character_num))

        self.app.curs.execute("UPDATE songs SET text=? WHERE id=?",
                              (modified_text, self.id))

        self.app.curs.commit()
        # print "Database updated"

        # self.setAllText(modified_text, new_all_chords)

        # FIXME THIS WILL NOT WORK ON THE SONG THAT IS CURRENTLY EDITED!


class CustomTextEdit(QtWidgets.QTextEdit):
    """
    """

    def __init__(self, app):
        super().__init__(app.win)
        self.app = app

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
            super().paintEvent(event)

            # Paint the chords:
            if self.app.current_song:
                painter = QtGui.QPainter()
                painter.begin(self.viewport())

                #scale_ratio = self.app.zoom_factor
                #scale_ratio = 1.0
                #painter.scale(scale_ratio, scale_ratio)

                #QTextDocument::drawContents ( QPainter * p, const QRectF & rect = QRectF() )
                #rect = QtCore.QRectF(0.0, 0.0, 1000.0, 1000.0)
                #self.document().drawContents(painter) #, rect)

                painter.setFont(self.app.chords_font)
                painter.setPen(self.app.chords_color)

                song = self.app.current_song

                cursor = self.textCursor()
                for chord in song.iterateAllChords():
                    # Obviously this line has chords:
                    chords_height, lyrics_height, line_height = self.app.getHeightsWithChords(
                    )

                    cursor.setPosition(
                        chord.character_num)  #, QtGui.QTextCursor.KeepAnchor)
                    left_rect = self.cursorRect(cursor)
                    cursor.setPosition(chord.character_num +
                                       1)  #, QtGui.QTextCursor.KeepAnchor)
                    right_rect = self.cursorRect(cursor)

                    chord_text = chord.getChordText()

                    chord_middle = (left_rect.left() + right_rect.right()
                                   ) // 2  # Average of left and right
                    #chord_width = self.app.chords_font_metrics.width(chord_text)
                    chord_width = self.app.getChordWidth(chord_text)
                    chord_left = chord_middle - (chord_width / 2.0)
                    chord_top = left_rect.bottom() - line_height

                    chord_rect = QtCore.QRectF(chord_left, chord_top,
                                               chord_width, chords_height)

                    self.app.drawChord(painter, chord_rect, chord_text)

                #painter.scale(1.0/scale_ratio, 1.0/scale_ratio)

                painter.end()

        else:
            painter = QtGui.QPainter()
            painter.begin(self.viewport())

            if self.app.current_song:
                width = 100000  # Unlimited
                height = 100000  # Unlimited

                paint_rect = QtCore.QRect(0, 0, width, height)
                self.app.drawSongToRect(self.app.current_song, painter,
                                        paint_rect)

            painter.end()

    def leaveEvent(self, event):
        """
        Called when the mouse LEAVES the song chords widget.
        """

        if self.lyric_editor_mode:
            super().leaveEvent(event)
        else:
            # Clear the hovering highlighting:
            self.app.hover_char_num = None
            self.viewport().update()

    def update(self):
        if not self.lyric_editor_mode:
            self.viewport().update()

    def undo(self):
        if self.lyric_editor_mode:
            super().undo()
        else:
            self.app.undo_stack.undo()

    def redo(self):
        if self.lyric_editor_mode:
            super().redo()
        else:
            self.app.undo_stack.redo()

    def optionKeyToggled(self, pressed):
        if self.dragging_chord == None:
            return

        if pressed:
            # Copy the dragging chord into the original location:
            self.original_chord = self.app.current_song.copyChord(
                self.dragging_chord, self.dragging_chord_orig_position)
        else:
            # Remove the original chord:
            self.app.current_song.deleteChord(self.original_chord)
            self.original_chord = None

        self.viewport().update()

    def mouseMoveEvent(self, event):
        """
        Called when mouse is DRAGGED or HOVERED in the song chords widget.
        """

        if self.lyric_editor_mode:
            super().mouseMoveEvent(event)
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
                    new_chord = copy.copy(self.dragging_chord)
                    new_chord.character_num = song_char_num
                    song.replaceChord(self.dragging_chord, new_chord)
                    self.dragging_chord = new_chord

                    # Show hover feedback on the new letter:
                    self.app.hover_char_num = song_char_num
                    self.app.selected_char_num = song_char_num
        else:
            # The mouse is NOT over a letter
            if not self.dragging_chord:
                self.app.hover_char_num = None

        self.app.editor.viewport().update()

    def mousePressEvent(self, event):
        """
        Called when mouse is CLICKED in the song chords widget.
        """

        if self.lyric_editor_mode:
            super().mousePressEvent(event)
            return

        if event.button() == Qt.MouseButton.LeftButton:
            localx = event.pos().x()
            localy = event.pos().y()
            letter_tuple = self.app.determineClickedLetter(
                localx, localy, False)

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
                        self.dragging_chord = self.app.current_song.getChord(
                            song_char_num)
                    except ValueError:
                        # User clicked on an empty chord space
                        pass
                    else:
                        self.dragging_chord_orig_position = song_char_num

                        self.app.undo_stack.beginMacro("chord dragged")

                        # If option is held, copy the chord:
                        key_modifiers = event.modifiers()
                        if bool(key_modifiers & Qt.KeyboardModifier.AltModifier):
                            self.original_chord = self.app.current_song.copyChord(
                                self.dragging_chord,
                                self.dragging_chord_orig_position)
                        else:
                            self.original_chord = None

            else:
                self.app.selected_char_num = None
                self.dragging_chord = None

            self.app.editor.viewport().update()

    def mouseReleaseEvent(self, event):
        if self.lyric_editor_mode:
            super().mouseReleaseEvent(event)
            return

        # Stop dragging of the chord (it's already in the correct position):
        if self.dragging_chord:
            if self.dragging_chord.character_num != self.dragging_chord_orig_position:

                # Delete the previous chord, if any:
                for other_chord in self.app.current_song.iterateAllChords():
                    if other_chord.character_num == self.dragging_chord.character_num and other_chord != self.dragging_chord:
                        self.app.current_song.deleteChord(other_chord)
                        break
                #self.current_song.sendToDatabase()
                self.app.editor.viewport().update()

            self.dragging_chord_orig_position = -1
            self.dragging_chord = None
            self.app.undo_stack.endMacro()

    def mouseDoubleClickEvent(self, event):
        """
        Called when mouse is DOUBLE-CLICKED in the song chords widget.
        """
        if self.lyric_editor_mode:
            super.mouseDoubleClickEvent(event)
            return

        if event.button() == Qt.MouseButton.LeftButton:
            localx = event.pos().x()
            localy = event.pos().y()
            letter_tuple = self.app.determineClickedLetter(
                localx, localy, False)
            if letter_tuple:
                # A valid chord/letter was double-clicked, edit it:
                (is_chord, song_char_num) = letter_tuple
                self.app.selected_char_num = song_char_num
                self.app.processSongCharEdit(song_char_num)
            else:
                # Invalid chord/letter was double clicked. Clear current selection:
                self.app.selected_char_num = None

            self.viewport().update()

    def keyPressEvent(self, event):

        if self.lyric_editor_mode:
            super().keyPressEvent(event)
            return

        key = event.key()
        if key == Qt.Key.Key_Alt:
            self.optionKeyToggled(True)

        if key == Qt.Key.Key_Delete or key == Qt.Key.Key_Backspace:
            self.app.deleteSelectedChord()
            return
        else:
            if not bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                # We are not invoking a shortcut (Control on Windows, Command on Mac)
                if self.app.processKeyPressed(key):
                    return

        # Let the main window handle this event (required for undo/redo shortcuts):
        self.app.win.keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if self.lyric_editor_mode:
            super().keyReleaseEvent(event)
            return

        key = event.key()
        if key == Qt.Key.Key_Alt:
            self.optionKeyToggled(False)


class ChordDialog(QtWidgets.QDialog):
    """
    Dialog for allowing the user to set the chord note & type.
    """

    def __init__(self, app):
        super().__init__(app.win)

        self.app = app
        # self.ui = uic.loadUi(chord_dialog_ui_file)
        self.ui = softchord_chord_dialog_ui.Ui_Dialog()
        self.ui.setupUi(self)

        notes_list = []
        for note_id in range(12):
            note_str = self.app.current_song._getNoteString(note_id)
            notes_list.append(note_str)
        self.ui.note_menu.addItems(notes_list)
        self.ui.note_menu.setMaxVisibleItems(12)  # Show all notes

        self.ui.chord_type_menu.addItems(self.app.chord_type_names)
        self.ui.chord_type_menu.setMaxVisibleItems(20)  # Show more types

        self.ui.bass_menu.addItems(["None"] + notes_list)
        self.ui.bass_menu.setMaxVisibleItems(12)  # Show all notes

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
            self.ui.bass_menu.setCurrentIndex(bass_note_id + 1)

        if marker == -1 or marker == "" or marker == "None":
            marker = ""
        self.ui.marker_ef.setText(marker)

        self.ui.in_parentheses_box.setChecked(in_parentheses)

        self.show()
        self.raise_()
        out = self.exec()
        if out:  # OK pressed:
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
        self.generate_table_of_contents = False
        self.print_song_num = True
        self.print_song_title = False
        self.print_song_key = True
        self.print_song_comment = True  # Usually "Pesn' Vozhrozhdeniya" number
        self.page_width = 8.5
        self.page_height = 11.0


class PdfDialog(QtWidgets.QDialog):
    """
    Dialog for allowing the user to set up printing and PDF export options.
    """

    def __init__(self, app):
        super().__init__(app.win)

        self.app = app
        # self.ui = uic.loadUi(pdf_dialog_ui_file)
        self.ui = softchord_pdf_dialog_ui.Ui_Dialog()
        self.ui.setupUi(self)

        self.ui.left_margin_ef.setValidator(
            QtGui.QDoubleValidator(0, 1000000000, 5, self))
        self.ui.right_margin_ef.setValidator(
            QtGui.QDoubleValidator(0, 1000000000, 5, self))
        self.ui.top_margin_ef.setValidator(
            QtGui.QDoubleValidator(0, 1000000000, 5, self))
        self.ui.bottom_margin_ef.setValidator(
            QtGui.QDoubleValidator(0, 1000000000, 5, self))
        self.ui.page_width_ef.setValidator(
            QtGui.QDoubleValidator(0, 1000000000, 5, self))
        self.ui.page_height_ef.setValidator(
            QtGui.QDoubleValidator(0, 1000000000, 5, self))

    def display(self, pdf_options, single_pdf_export):
        """
        Display a dialog that alters the PdfOptions if OK is pressed.
        Returns False if user pressed Cancel.
        """

        self.ui.left_margin_ef.setText(str(pdf_options.left_margin))
        self.ui.right_margin_ef.setText(str(pdf_options.right_margin))
        self.ui.top_margin_ef.setText(str(pdf_options.top_margin))
        self.ui.bottom_margin_ef.setText(str(pdf_options.bottom_margin))

        self.ui.page_width_ef.setText(str(pdf_options.page_width))
        self.ui.page_height_ef.setText(str(pdf_options.page_height))

        self.ui.alternate_margins_box.setChecked(pdf_options.alternate_margins)
        self.ui.print_4_per_page_box.setChecked(pdf_options.print_4_per_page)
        self.ui.generate_table_of_contents_box.setChecked(
            pdf_options.generate_table_of_contents)
        self.ui.print_song_num_box.setChecked(pdf_options.print_song_num)
        self.ui.print_song_title_box.setChecked(pdf_options.print_song_title)
        self.ui.print_song_key_box.setChecked(pdf_options.print_song_key)
        self.ui.print_song_comment_box.setChecked(
            pdf_options.print_song_comment)

        # Allow table of contents only when generating one PDF for multiple songs:
        if not single_pdf_export:
            self.ui.generate_table_of_contents_box.setChecked(False)
            self.ui.generate_table_of_contents_box.setVisible(False)

        self.show()
        self.raise_()
        out = self.exec()
        if out:  # OK pressed:
            # FIXME what if the user entered ""?
            pdf_options.left_margin = float(self.ui.left_margin_ef.text())
            pdf_options.right_margin = float(self.ui.right_margin_ef.text())
            pdf_options.top_margin = float(self.ui.top_margin_ef.text())
            pdf_options.bottom_margin = float(self.ui.bottom_margin_ef.text())
            pdf_options.page_width = float(self.ui.page_width_ef.text())
            pdf_options.page_height = float(self.ui.page_height_ef.text())
            pdf_options.alternate_margins = self.ui.alternate_margins_box.isChecked(
            )
            pdf_options.print_4_per_page = self.ui.print_4_per_page_box.isChecked(
            )
            pdf_options.generate_table_of_contents = self.ui.generate_table_of_contents_box.isChecked(
            )
            pdf_options.print_song_num = self.ui.print_song_num_box.isChecked()
            pdf_options.print_song_title = self.ui.print_song_title_box.isChecked(
            )
            pdf_options.print_song_key = self.ui.print_song_comment_box.isChecked(
            )
            pdf_options.print_song_comment = self.ui.print_song_comment_box.isChecked(
            )

            return True
        else:
            # Cancel pressed
            return False


class App(QtWidgets.QApplication):
    """
    The main application class.
    """

    def __init__(self, args):
        super().__init__(args)
        self.doc_editor_offset = 0  # FIXME

        # self.ui = uic.loadUi(script_ui_file)
        self.win = QtWidgets.QMainWindow()
        self.ui = softchord_main_window_ui.Ui_MainWindow()
        self.ui.setupUi(self.win)

        self.on_windows = platform.system() == "Windows"

        self.curs = None
        self.current_song = None
        self.empty_doc = QtGui.QTextDocument()

        self.pdf_options = PdfOptions()

        self.undo_stack = QtGui.QUndoStack()
        self.undo_stack.canUndoChanged.connect(self.updateEditMenu)
        self.undo_stack.canRedoChanged.connect(self.updateEditMenu)
        self.focusChanged.connect(self.updateEditMenu)

        # Make a list of all chord types:
        self.chord_type_names = []
        self.chord_type_prints = []
        for chord_type_id, name, print_text in chord_types_list:
            if print_text:
                name = "%s - %s" % (print_text, name)
            self.chord_type_names.append(name)
            self.chord_type_prints.append(print_text)

        # Key: chord type text, value: chord type ID
        self.chord_type_texts_dict = {}
        for id, print_text in enumerate(self.chord_type_prints):
            self.chord_type_texts_dict[print_text] = id
            for alternative_name, official_name in alternative_type_names.items(
            ):
                if print_text == official_name:
                    self.chord_type_texts_dict[alternative_name] = id

        # Make a list of all notes and keys:
        self.notes_list = []
        self.note_text_id_dict = {}
        for note_id, text, alt_text in global_notes_list:
            self.notes_list.append((text, alt_text))
            self.note_text_id_dict[text] = note_id
            self.note_text_id_dict[alt_text] = note_id

        # Allows the user to show only songs that match this text:
        self.filter_string = ""

        self.songs_model = SongsTableModel(self)
        self.songs_proxy_model = SongsProxyModel(self)
        self.songs_proxy_model.setSourceModel(self.songs_model)

        self.ui.songs_view.setModel(self.songs_proxy_model)
        self.ui.songs_view.setSortingEnabled(True)

        self.ui.songs_view.horizontalHeader().setStretchLastSection(True)
        self.ui.songs_view.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.ui.songs_view.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.ui.songs_view.selectionModel().selectionChanged.connect(
            self.songsSelectionChangedCallback)

        self.ui.song_filter_ef.textEdited.connect(self.songFilterEdited)
        self.ui.clear_filter_button.clicked.connect(self.clearFilterClicked)

        self.previous_song_text = None  # Song text before last user's edit operation

        self.editor = CustomTextEdit(self)
        self.editor.undoAvailable.connect(self.updateEditMenu)
        # self.print_editor = CustomTextEdit(self)
        #self.print_editor.setVisible(False)
        self.print_editor = self.editor  # FIXME

        self.ui.lyric_editor_layout.addWidget(self.editor)
        self.ui.lyric_editor_layout.removeWidget(self.ui.chord_scroll_area)
        self.ui.chord_scroll_area.hide()

        self.editor.setLineWrapMode(QtWidgets.QTextEdit.LineWrapMode.NoWrap)
        self.print_editor.setLineWrapMode(
            QtWidgets.QTextEdit.LineWrapMode.NoWrap)
        self.editor.textChanged.connect(self.lyricsTextChanged)

        self.ui.transpose_up_button.clicked.connect(self.transposeUp)
        self.ui.transpose_down_button.clicked.connect(self.transposeDown)
        self.ui.new_song_button.clicked.connect(self.createNewSong)
        self.ui.delete_song_button.clicked.connect(self.deleteSelectedSongs)

        self.ui.song_num_ef.textEdited.connect(self.currentSongNumberEdited)
        self.ui.song_title_ef.textEdited.connect(self.currentSongTitleEdited)
        self.ui.song_subtitle_ef.textEdited.connect(self.subtitleEdited)

        self.ui.song_num_ef.setValidator(
            QtGui.QIntValidator(0, 1000000000, self.win))
        self.ignore_song_key_changed = False
        self.ui.song_key_menu.currentIndexChanged.connect(
            self.currentSongKeyChanged)
        self.ui.song_alt_key_menu.currentIndexChanged.connect(
            self.currentSongAltKeyChanged)

        # Menu actions:
        self.ui.actionNewSongbook.triggered.connect(self.newSongbook)
        self.ui.actionOpenSongbook.triggered.connect(self.openSongbook)
        self.ui.actionCloseSongbook.triggered.connect(self.closeSongbook)
        self.ui.actionSaveSongbook.triggered.connect(self.saveSongbook)
        self.ui.actionAppendSongbook.triggered.connect(
            self.appendSongbookSelected)

        self.ui.actionPrint.triggered.connect(self.printSelectedSongs)
        self.ui.actionQuit.triggered.connect(self.win.close)
        self.ui.actionNewSong.triggered.connect(self.createNewSong)

        self.ui.actionDeleteSongs.triggered.connect(self.deleteSelectedSongs)
        self.ui.actionRemoveTrailingSpaces.triggered.connect(
            self.removeTrailingSpaces)
        self.ui.actionDeleteSong.triggered.connect(self.deleteSelectedSongs)
        self.ui.actionRenumberSongs.triggered.connect(self.renumberAllSongs)

        self.ui.actionSetID.triggered.connect(self.setSongDatabaseId)
        self.ui.actionExportSinglePdf.triggered.connect(self.exportToSinglePdf)
        self.ui.actionExportSongToPdf.triggered.connect(self.exportToSinglePdf)
        self.ui.actionExportMultiplePdfs.triggered.connect(
            self.exportToMultiplePdfs)
        self.ui.actionExportText.triggered.connect(self.exportToText)

        self.ui.actionExportChordPro.triggered.connect(self.exportToChordPro)
        self.ui.actionImportText.triggered.connect(self.browseForTextFile)
        self.ui.actionImportChordPro.triggered.connect(self.importFromChordPro)
        self.ui.actionLyricsFont.triggered.connect(self.changeLyricsFont)
        self.ui.actionChordsFont.triggered.connect(self.changeChordFont)

        self.ui.actionUndo.triggered.connect(self.undo_stack.undo)
        self.ui.actionRedo.triggered.connect(self.undo_stack.redo)
        self.ui.actionCut.triggered.connect(self.cutSelected)
        self.ui.actionCopy.triggered.connect(self.copySelected)
        self.ui.actionPaste.triggered.connect(self.pasteSelected)
        self.ui.actionCopySongText.triggered.connect(self.copySongText)
        self.ui.actionExportClipboard.triggered.connect(self.copySongText)

        # FIXME we need only one way to import a song from the clipboard. Remove one of these actions:
        self.ui.actionPasteAsNewSong.triggered.connect(self.pasteAsNewSong)
        self.ui.actionImportClipboard.triggered.connect(self.pasteAsNewSong)

        self.ui.actionChordEditorMode.triggered.connect(
            self.chordEditorSelected)
        self.ui.actionLyricEditorMode.triggered.connect(
            self.lyricEditorSelected)

        self.ui.actionZoomIn.triggered.connect(self.zoomIn)
        self.ui.actionZoomOut.triggered.connect(self.zoomOut)
        self.ui.actionZoomActual.triggered.connect(self.zoomActual)
        self.ui.zoom_in_button.clicked.connect(self.zoomIn)
        self.ui.zoom_out_button.clicked.connect(self.zoomOut)

        self.zoom_levels = [1.0]
        zoom1 = 1.0
        zoom2 = 1.0
        for i in range(10):
            zoom1 *= 1.1
            zoom2 /= 1.1
            self.zoom_levels += [zoom1, zoom2]
        self.zoom_levels.sort()

        self.ui.zoom_slider.setRange(0, len(self.zoom_levels) - 1)
        self.ui.zoom_slider.sliderMoved.connect(self.updateZoomWidgets)

        # Set zoom to 100%:
        self.zoom_factor = 1.0
        pos = self.zoom_levels.index(1.0)
        # FIXME
        # self.ui.zoom_slider.setTickPosition(pos)
        self.ui.zoom_slider.setSliderPosition(pos)

        self.clipboard = self.clipboard()
        self.clipboard.dataChanged.connect(self.clipboardChanged)

        self.ignore_song_text_changed = False

        # The letter/chord that is currently selected:
        self.selected_char_num = None
        # The letter/chord that is currently hover (mouse hoveing over it):
        self.hover_char_num = None

        # NOTE: For printing of small song books, font sizes of 14 / 11 are ideal.

        self.lyrics_font = QtGui.QFont("Times New Roman", LYRICS_SIZE)
        self.lyrics_font_size = float(LYRICS_SIZE)
        self.lyrics_color = QtGui.QColor("BLACK")
        self.lyrics_font_metrics = QtGui.QFontMetricsF(self.lyrics_font)

        # Font that will be used if no good fonts are found:
        self.chords_font_size = float(CHORDS_SIZE)
        self.chords_font = QtGui.QFont("Times New Roman", CHORDS_SIZE,
                                       QtGui.QFont.Weight.Bold)
        self.chords_font_metrics = QtGui.QFontMetricsF(self.chords_font)

        # NOTE: This may work only on a Mac:
        self.symbols_font = QtGui.QFont("Arial Unicode MS", CHORDS_SIZE,
                                        QtGui.QFont.Weight.Bold)
        self.symbols_font_metrics = QtGui.QFontMetricsF(self.symbols_font)

        # FIXME self.updateEditorFonts() ??

        # Search for a font that can display sharp and flat characters correctly:
        #for name in [
        #    'MS Reference Sans Serif'
        #    'Lucida Sans Unicode',
        #    'Arial Unicode MS',
        #        ]:
        #    font = QtGui.QFont(name, 14, QtGui.QFont.Weight.Bold)
        #    if font.exactMatch():
        #        self.chords_font = font
        #        break

        # BLUE is ideal for songbook printing:
        self.chords_color = QtGui.QColor(CHORDS_COLOR)
        self.white_color = QtGui.QColor("WHITE")
        self.editor.setFont(self.lyrics_font)
        self.print_editor.setFont(self.lyrics_font)

        self._orig_closeEvent = self.win.closeEvent
        self.win.closeEvent = self.closeEvent

        self.populateSongKeyMenu()
        self.setCurrentSongbook(None)

        self.songs_model.updateFromDatabase()

        self.ui.lyric_editor_button.clicked.connect(self.lyricEditorSelected)
        self.ui.chord_editor_button.clicked.connect(self.chordEditorSelected)

        self.chordEditorSelected()

        self.updateZoomWidgets()

        self.updateStates()

        self.win.show()
        self.win.raise_()

    def event(self, event):
        # if event.type() == Qt.QEvent.FileOpen:
        if event.type() == QtGui.QFileOpenEvent:
            # Cast as QFileOpenEvent!
            #self.openSongbook
            filename = event.file()
            if filename.endswith(".songbook"):
                self.setCurrentSongbook(filename)
            return True
        return super().event(event)

    def songFilterEdited(self, new_text):

        selection_model = self.ui.songs_view.selectionModel()

        # Save the selection:
        selected_source_rows = []
        for index in selection_model.selectedRows():
            index = self.songs_proxy_model.mapToSource(index)
            selected_source_rows.append(index.row())

        self.ui.songs_view.selectionModel().clear()

        self.songs_model.layoutAboutToBeChanged.emit()

        self.filter_string = new_text

        #self.songs_proxy_model.layoutChanged.emit() # Forces the view to redraw
        self.songs_model.layoutChanged.emit()  # Forces the view to redraw

        # FIXME re-select the subset of selected rows that is still visible
        for row in selected_source_rows:
            source_index = self.songs_model.index(row, 0)
            proxy_index = self.songs_proxy_model.mapFromSource(source_index)
            selection_model.select(
                proxy_index, QtGui.QItemSelectionModel.Select |
                QtGui.QItemSelectionModel.Rows)
            #self.ui.songs_view.selectRow(proxy_index.row())

    def clearFilterClicked(self):
        self.ui.song_filter_ef.setText("")
        self.songFilterEdited("")

    def lyricEditorSelected(self):

        self.ui.lyric_editor_button.setDown(True)
        self.ui.chord_editor_button.setDown(False)

        self.editor.viewport().setCursor(Qt.CursorShape.IBeamCursor)

        self.ui.chords_editor_label.hide()
        self.ui.lyrics_editor_label.show()
        self.editor.lyric_editor_mode = True
        self.editor.setUndoRedoEnabled(True)

        self.editor.viewport().update()

    def chordEditorSelected(self):

        self.editor.viewport().setCursor(Qt.CursorShape.ArrowCursor)

        self.ui.lyric_editor_button.setDown(False)
        self.ui.chord_editor_button.setDown(True)

        self.ui.lyrics_editor_label.hide()
        self.ui.chords_editor_label.show()
        self.editor.lyric_editor_mode = False
        self.editor.setUndoRedoEnabled(False)

        self.editor.viewport().update()
        self.updateEditMenu()

    def __del__(self):
        pass

    def populateSongKeyMenu(self):
        # Populate the song key pull-down menu:
        keys_list = ["None"]
        alt_keys_list = ["NA"]

        if self.current_song:
            for note_id, (text, alt_text) in enumerate(self.notes_list):
                if note_id in [3, 8, 10]:  # Eb, Ab, or Bb
                    combined_text = alt_text
                else:
                    combined_text = text

                keys_list.append(combined_text + u" minor")
                keys_list.append(combined_text + u" Major")
                alt_keys_list.append(combined_text)

        self.ignore_song_key_changed = True
        self.ui.song_key_menu.clear()
        self.ui.song_key_menu.addItems(keys_list)
        self.ui.song_key_menu.setMaxVisibleItems(
            25)  # Show all keys (including "None")

        self.ui.song_alt_key_menu.clear()
        self.ui.song_alt_key_menu.addItems(alt_keys_list)
        self.ui.song_alt_key_menu.setMaxVisibleItems(
            13)  # Show all keys (including "None")
        self.ignore_song_key_changed = False

        self.ui.song_key_menu.setEnabled(bool(self.current_song))
        self.ui.song_alt_key_menu.setEnabled(bool(self.current_song))

    def closeEvent(self, event):
        self.sendCurrentSongToDatabase()
        self._orig_closeEvent(event)

    def sendCurrentSongToDatabase(self):
        if self.current_song:
            # Update the current song in the database:
            self.current_song.sendToDatabase()

    def getSelectedChord(self):
        """
        Return the selected chord, or None, if no selection or the selected
        character has no chord assigned to it.
        """

        if self.selected_char_num != None and self.current_song:
            for chord in self.current_song.iterateAllChords():
                if chord.character_num == self.selected_char_num:
                    return chord
        return None

    def deleteSelectedChord(self):
        """
        Deletes the currently selected chord from the song.
        """

        chord = self.getSelectedChord()
        if chord:
            self.current_song.deleteChord(chord)

    def processKeyPressed(self, key):
        """
        Returns True if the key press was processed
        """

        if self.selected_char_num == None:
            return False

        if key in [Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down]:
            # Move or transpose the selected chord
            prev_chord = None
            for iter_chord in self.current_song.iterateAllChords():
                if iter_chord.character_num == self.selected_char_num:
                    prev_chord = iter_chord
                    break

            if prev_chord:
                # A chord is selected
                new_chord = copy.copy(prev_chord)
                if key == Qt.Key.Key_Left:
                    if new_chord.character_num > 0:
                        new_chord.character_num -= 1
                elif key == Qt.Key.Key_Right:
                    new_chord.character_num += 1
                elif key == Qt.Key.Key_Up:
                    new_chord.transpose(1)
                elif key == Qt.Key.Key_Down:
                    new_chord.transpose(-1)
                else:
                    raise ValueError("Invalid key pressed")

                # Make sure that the new chord is not off the line:
                try:
                    if self.previous_song_text[new_chord.character_num] == '\n':
                        # On a line break
                        return False
                except IndexError:
                    # Moved too far to the left or right
                    return False

                self.current_song.replaceChord(prev_chord, new_chord)
                return True

        # Determine if "m" key is pressed:
        if key == Qt.Key.Key_M:
            prev_chord = None
            for iter_chord in self.current_song.iterateAllChords():
                if iter_chord.character_num == self.selected_char_num:
                    prev_chord = iter_chord
                    break

            if prev_chord:
                # Chord already exists, flip major/minor
                new_chord = copy.copy(prev_chord)
                if new_chord.chord_type_id == 0:
                    new_chord.chord_type_id = 1
                else:
                    new_chord.chord_type_id = 0
                self.current_song.replaceChord(prev_chord, new_chord)
            return

        # Determine if a note key was pressed:
        key_note_dict = {
            Qt.Key.Key_C: 0,
            Qt.Key.Key_D: 2,
            Qt.Key.Key_E: 4,
            Qt.Key.Key_F: 5,
            Qt.Key.Key_G: 7,
            Qt.Key.Key_A: 9,
            Qt.Key.Key_B: 11,
        }
        note_id = key_note_dict.get(key)
        if note_id == None:
            return False

        # Check whether we are editing an existing chord or adding a new one:
        add_new = True
        prev_chord = None
        for iter_chord in self.current_song.iterateAllChords():
            if iter_chord.character_num == self.selected_char_num:
                add_new = False
                prev_chord = iter_chord
                break

        if add_new:
            chord_type_id = 0  # Major
            new_chord = SongChord(self.current_song, self.selected_char_num,
                                  note_id, chord_type_id, -1, "", False)
            self.current_song.addChord(new_chord)
        else:
            new_chord = copy.copy(prev_chord)

            # Change this chord to <note> major:
            new_chord.note_id = note_id
            new_chord.chord_type_id = 0
            new_chord.marker = ""
            new_chord.in_parentheses = False
            self.current_song.replaceChord(prev_chord, new_chord)

        return True

    def undo(self):
        self.undo_stack.undo()
        self.viewport().update()

    def redo(self):
        self.undo_stack.redo()
        self.viewport().update()

    def updateEditMenu(self, ignored1=None, ignored2=None):

        focus_widget = self.focusWidget()  # FIXME implement this properly

        enable_paste = not self.clipboard.text()

        try:
            if self.current_song:
                if self.editor.lyric_editor_mode:
                    # Currently editing the lyrics (QTextEdit)
                    # FIXME what if the lyrics editor can undo?
                    # FIXME We need to attach slots to QTextEdit.undoAvailable() and redoAvailable() signals
                    undo_possible = False
                    redo_possible = False
                else:
                    # In chord editor
                    undo_possible = self.undo_stack.canUndo()
                    redo_possible = self.undo_stack.canRedo()
                    # FIXME Enable paste only if CHORD text is selected:
            else:
                # Not currently editing a song:
                undo_possible = self.undo_stack.canUndo()
                redo_possible = self.undo_stack.canRedo()
                enable_paste = True  # FIXME enable based on the focus widget
        except RuntimeError:
            # C++ QUndoStack has been deleted
            return

        self.ui.actionUndo.setEnabled(undo_possible)
        self.ui.actionRedo.setEnabled(redo_possible)
        self.ui.actionPaste.setEnabled(enable_paste)

    def clearUndoStack(self):
        self.undo_stack.clear()

    def warning(self, text):
        QtWidgets.QMessageBox.warning(self.win, "Warning", text)

    def info(self, text):
        QtWidgets.QMessageBox.information(self.win, "Info", text)

    def error(self, text):
        QtWidgets.QMessageBox.warning(self.win, "Error", text)

    def setWaitCursor(self):
        """ Set the mouse cursor to the watch """
        self.win.setCursor(QtGui.QCursor(Qt.CursorShape.WaitCursor))

    def restoreCursor(self):
        """ Set the mouse cursor to the default arrow. """
        self.win.setCursor(Qt.CursorShape.ArrowCursor)

    def songsSelectionChangedCallback(self, selected=None, deselected=None):
        """
        Called when the song selection changes.
        """

        # Commit any changes in the current song:
        self.curs.commit()

        self.selected_char_num = None  # Remove the selection
        self.hover_char_num = None  # Remove the hover highlighting
        #self.updateCurrentSongFromDatabase()  FIXME REMOVE

        sel_indecies = self.ui.songs_view.selectedIndexes()
        num_selected = len(sel_indecies) / self.songs_model.columnCount()

        self.setWaitCursor()
        if num_selected == 1:
            index = sel_indecies[0]
            index = self.songs_proxy_model.mapToSource(index)
            song_id = self.songs_model.getRowSongID(index.row())
            song = Song(self, song_id)
            self.setCurrentSong(song)
        else:
            self.setCurrentSong(None)

        self.updateStates()
        self.restoreCursor()

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
        #### OBSOLETE FIXME REMOVE THIS METHOD

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

        # FIXME there is a faster way of doing this:
        num_selected = len(self.getSelectedSongIds())

        if self.current_song == None:
            self.ui.song_title_ef.setText("")
            self.ui.song_num_ef.setText("")
            self.ui.song_key_menu.setCurrentIndex(0)  # "None" item
            self.ui.song_alt_key_menu.setCurrentIndex(0)  # "None" item

        self.editor.setEnabled(self.current_song != None)
        self.ui.song_title_ef.setEnabled(self.current_song != None)
        self.ui.song_num_ef.setEnabled(self.current_song != None)
        self.ui.song_key_menu.setEnabled(self.current_song != None)
        self.ui.song_alt_key_menu.setEnabled(self.current_song != None)
        self.ui.transpose_up_button.setEnabled(self.current_song != None)
        self.ui.transpose_down_button.setEnabled(self.current_song != None)

        self.ui.delete_song_button.setEnabled(num_selected > 0)
        self.ui.actionDeleteSongs.setEnabled(num_selected > 0)
        self.ui.actionRemoveTrailingSpaces.setEnabled(num_selected > 0)
        self.ui.actionDeleteSong.setEnabled(num_selected == 1)
        self.ui.actionSetID.setEnabled(num_selected == 1)

        songs_present = self.songs_model.rowCount() > 0

        self.ui.actionExportSinglePdf.setEnabled(songs_present)
        self.ui.actionExportMultiplePdfs.setEnabled(songs_present and
                                                    num_selected != 1)

        self.ui.menuSong.setEnabled(num_selected == 1)  # not working?
        self.ui.actionExportText.setEnabled(num_selected == 1)
        self.ui.actionExportSongToPdf.setEnabled(num_selected == 1)
        self.ui.actionExportChordPro.setEnabled(num_selected == 1)
        self.ui.actionCopySongText.setEnabled(num_selected == 1)
        self.ui.actionExportClipboard.setEnabled(num_selected == 1)

        self.ui.actionPrint.setEnabled(songs_present)

        # FIXME instead link it to either the lyric editror select-all, or the songs table
        self.ui.actionSelectAll.setEnabled(False)

        # Whether there is an open songbook:
        songbook_open = (self.curs != None)
        self.ui.actionImportText.setEnabled(songbook_open)

        self.ui.new_song_button.setEnabled(songbook_open)
        self.ui.actionNewSong.setEnabled(songbook_open)

        self.ui.actionCloseSongbook.setEnabled(songbook_open)
        self.ui.actionSaveSongbook.setEnabled(songbook_open)
        self.ui.actionAppendSongbook.setEnabled(songbook_open)

        self.updateEditMenu()

    def setCurrentSong(self, song):
        """
        Sets the current song to the specified song.
        Reads all song info from the database.
        """

        if self.current_song == None and song == None:
            return

        #self.ignore_song_key_changed = True
        self.sendCurrentSongToDatabase()

        if self.current_song != None:
            # Update the current song in the database
            #self.current_song.sendToDatabase()

            # Clear the document of the QTextEdit before setting it to a new document.
            # This is needed to prevent a crash on Windows:
            prev_doc = self.editor.document()
            self.current_song.doc = prev_doc.clone()
            prev_doc.clear()

        if song == None:
            self.current_song = None
            self.previous_song_text = None
            self.ui.song_key_menu.setCurrentIndex(0)  # "None" item
            self.ui.song_alt_key_menu.setCurrentIndex(0)  # "None" item
            self.ui.song_num_ef.setText("")

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
                self.ui.song_key_menu.setCurrentIndex(0)
            else:
                self.ui.song_key_menu.setCurrentIndex(
                    self.current_song.key_note_id * 2 +
                    self.current_song.key_is_major + 1)

            if self.current_song.alt_key_note_id == -1:
                self.ui.song_alt_key_menu.setCurrentIndex(0)
            else:
                self.ui.song_alt_key_menu.setCurrentIndex(
                    self.current_song.alt_key_note_id + 1)

            self.ui.song_title_ef.setText(self.current_song.title)
            self.ui.song_subtitle_ef.setText(self.current_song.subtitle)

            if self.current_song.number == -1:
                self.ui.song_num_ef.setText("")
            else:
                self.ui.song_num_ef.setText(str(self.current_song.number))

            song.doc.setDefaultFont(self.lyrics_font)

            # NOTE: Messing with this stuff may cause the app to crash on Windows (compiled)
            self.editor.setDocument(song.doc)

            self.editor.verticalScrollBar().setValue(0)

        #self.ignore_song_key_changed = False

    def _transposeCurrentSong(self, steps):
        """
        Transpose the current song up by the specified number of steps.
        """

        self.setWaitCursor()
        try:
            self.current_song.transpose(steps)
            self.current_song.sendToDatabase()
            self.editor.viewport().update()
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

        song_text = self.editor.toPlainText()

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
                        renumber_map[len(self.previous_song_text) +
                                     i] = len(song_text) + i
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
                self.selected_char_num = renumber_map.get(
                    self.selected_char_num)
        else:
            # No previous text
            new_all_chords = self.current_song._chords

        self.current_song._chords = new_all_chords
        self.previous_song_text = song_text

        # DO NOT ENABLE! Deletes the chords   ???
        #self.sendCurrentSongToDatabase()

        #self.viewport().update()

        self.ignore_song_text_changed = False

    def zoomIn(self):
        pos = self.ui.zoom_slider.sliderPosition()
        self.ui.zoom_slider.setSliderPosition(pos + 1)
        self.updateZoomWidgets()

    def zoomOut(self):
        pos = self.ui.zoom_slider.sliderPosition()
        self.ui.zoom_slider.setSliderPosition(pos - 1)
        self.updateZoomWidgets()

    def zoomActual(self):
        """
        Set zoom level to 100%
        """
        pos = self.zoom_levels.index(1.0)
        self.ui.zoom_slider.setSliderPosition(pos)
        self.updateZoomWidgets()

    def updateZoomWidgets(self):

        pos = self.ui.zoom_slider.sliderPosition()
        self.zoom_factor = self.zoom_levels[pos]
        percent = int(self.zoom_factor * 100.0)
        percent_str = str(percent) + "%"
        self.ui.zoom_label.setText("Zoom: %s" % percent_str)
        self.updateEditorFonts()

        enable_zoom_in = (pos != len(self.zoom_levels) - 1)
        enable_zoom_out = (pos != 0)
        enable_zoom_actual = (self.zoom_levels[pos] != 1.0)

        self.ui.zoom_in_button.setEnabled(enable_zoom_in)
        self.ui.zoom_out_button.setEnabled(enable_zoom_out)
        self.ui.actionZoomIn.setEnabled(enable_zoom_in)
        self.ui.actionZoomOut.setEnabled(enable_zoom_out)
        self.ui.actionZoomActual.setEnabled(enable_zoom_actual)

    def getHeightsWithChords(self):

        cfm = self.chords_font_metrics
        lfm = self.lyrics_font_metrics

        lyrics_height = lfm.height()
        chords_height = cfm.height()

        line_height = (lyrics_height +
                       cfm.ascent()) - lfm.leading() - cfm.leading()

        return chords_height, lyrics_height, line_height

    def getHeightsWithoutChords(self):

        lyrics_height = self.lyrics_font_metrics.height()
        chords_height = 0.0
        line_height = lyrics_height

        return chords_height, lyrics_height, line_height

    def transposeUp(self):
        self._transposeCurrentSong(1)

    def transposeDown(self):
        self._transposeCurrentSong(-1)

    def changeChordFont(self):
        """
        Brings up a dialog to let the user modify the chords font.
        """

        # Make a copy:
        new_font = QtGui.QFont(self.chords_font)

        new_font, ok = QtGui.QFontDialog.getFont(new_font, self.win)
        if ok:
            self.chords_font_size = new_font.pointSizeF()
            self.chords_font = new_font
            self.updateEditorFonts()

    def changeLyricsFont(self):
        """
        Brings up a dialog to let the user modify the lyrics font.
        """

        # Make a copy:
        new_font = QtGui.QFont(self.lyrics_font)

        new_font, ok = QtGui.QFontDialog.getFont(new_font, self.win)
        if ok:
            self.lyrics_font_size = new_font.pointSizeF()
            self.lyrics_font = new_font
            self.updateEditorFonts()

    def updateEditorFonts(self):
        """
        Update the font metrics, because either the font(s) has changed, or the zoom
        level was changed.
        """

        # Update the lyrics font:
        self.lyrics_font.setPointSizeF(self.lyrics_font_size * self.zoom_factor)
        self.lyrics_font_metrics = QtGui.QFontMetricsF(self.lyrics_font)
        self.editor.setFont(self.lyrics_font)
        self.print_editor.setFont(self.lyrics_font)
        if self.current_song:
            self.current_song.setDocMargins()
        self.editor.viewport().update()

        # Update the chords fonts:
        self.chords_font.setPointSizeF(self.chords_font_size * self.zoom_factor)
        self.chords_font_metrics = QtGui.QFontMetricsF(self.chords_font)

        self.symbols_font.setPointSizeF(self.chords_font_size *
                                        self.zoom_factor)
        self.symbols_font_metrics = QtGui.QFontMetricsF(self.symbols_font)

        if self.current_song:
            self.current_song.setDocMargins()
        self.editor.viewport().update()

    def printSelectedSongs(self):
        """
        Bring up a print dialog box.
        """

        self.sendCurrentSongToDatabase()

        if not self.songs_model.rowCount():
            self.error("There are no songs to print")
            return

        printer = QPrinter()
        printer.setFullPage(True)
        printer.setPageSize(PageSizeId.Letter)
        printer.setPageOrientation(QtGui.QPageLayout.Orientation.Portrait)

        painter = QtGui.QPainter()

        print_dialog = QtGui.QPrintDialog(printer, self.win)
        if print_dialog.exec() == QtWidgets.QDialog.Accepted:
            ok = PdfDialog(self).display(self.pdf_options,
                                         single_pdf_export=True)
            if not ok:
                return

            song_ids = self.getSelectedSongIds()
            if not song_ids:
                # No selection, print the whole song book
                song_ids = self.songs_model.getAllSongIds()

            try:
                num_printed = self.printSongsToPrinter(song_ids, printer,
                                                       "Printing...")
                # In case of an IOError, num_printed will be 0.
            except Exception as err:
                self.error("Error printing:\n\n%s " % traceback.format_exc())

    def printSongsToPrinter(self, song_ids, printer, progress_message):
        """
        Paint the given songs to the specified QPriner instance.
        
        Will display an error dialog on error.
        """

        progress = QtWidgets.QProgressDialog(progress_message, "Abort", 0,
                                         len(song_ids), self.win)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        # Open the progress dialog right away:
        progress.setMinimumDuration(0)

        try:
            painter = QtGui.QPainter()
            if not painter.begin(printer):
                raise IOError("Failed to open the output file for writing")

            num_printed = 0
            page_num = 0

            num_table_of_contents_pages = 0
            if self.pdf_options.generate_table_of_contents:

                lyrics_height = self.lyrics_font_metrics.height()
                printable_height = self.getPrintableHeight(printer)

                max_songs_per_page = int(printable_height // lyrics_height)

                # FIXME use smaller font size for table of contents
                # FIXME Do not leave less than ~10 song titles per page.

                table_of_contents_lines = []
                for song_id in song_ids:
                    title, num = self.songs_model.getTitleAndNumFromId(song_id)
                    if num != -1:
                        table_of_contents_lines.append((title, num))

                # Sort by song name:
                # FIXME remove the leading "The", "A", etc:
                table_of_contents_lines.sort()

                # Split the table of contents into pages:
                table_of_contents_pages = []
                curr_page = []
                for curr_line in table_of_contents_lines:
                    curr_page.append(curr_line)
                    if len(curr_page) == max_songs_per_page:
                        table_of_contents_pages.append(curr_page)
                        curr_page = []
                if curr_page:
                    table_of_contents_pages.append(curr_page)

                #print 'num table of contents pages:', len(table_of_contents_pages)

                painter.setFont(self.lyrics_font)
                for lines in table_of_contents_pages:
                    page_num += 1
                    if page_num != 1:
                        if not printer.newPage():
                            raise IOError(
                                "Failed to flush page to disk, disk full?")
                    self.printTableOfConentsPage(lines, printer, painter,
                                                 page_num)

                num_table_of_contents_pages = len(table_of_contents_pages)

            if num_table_of_contents_pages % 2:
                # Odd number of table of contents pages. Inseart a blank line:
                page_num += 1
                if not printer.newPage():
                    raise IOError("Failed to flush page to disk, disk full?")

            min_scale_ratio = 1.0

            for song_id in song_ids:
                if progress.wasCanceled():
                    break

                page_num += 1
                if page_num != 1:
                    if not printer.newPage():
                        raise IOError(
                            "Failed to flush page to disk, disk full?")

                song = Song(self, song_id)

                # Set this song's document (will be reset later):
                self.print_editor.setDocument(song.doc)
                # NOTE: Messing with this stuff may cause the app to crash on Windows (compiled)

                scale_ratio = self.printSong(song, printer, painter, page_num)
                if scale_ratio < min_scale_ratio:
                    min_scale_ratio = scale_ratio

                num_printed += 1
                progress.setValue(num_printed)

            self.print_editor.setDocument(self.empty_doc)
            painter.end()

            self.reportScaleRatio(min_scale_ratio, len(song_ids))

        except IOError as err:
            self.error(str(err))
            return 0

        except Exception as err:
            raise

        progress.setValue(len(song_ids))

        return num_printed

    def printSong(self, song, printer, painter, page_num):
        # NOTE: The song's document should already be in the editor for this to work!

        # Figure out what the margins should be:
        # Convert to points (from inches):
        left_margin = self.pdf_options.left_margin * 72.0
        right_margin = self.pdf_options.right_margin * 72.0
        top_margin = self.pdf_options.top_margin * 72.0
        bottom_margin = self.pdf_options.bottom_margin * 72.0

        # orig_document = self.editor.document().clone()

        if self.pdf_options.alternate_margins and not page_num % 2:
            # If alternating margins and this is an even page:
            left_margin, right_margin = right_margin, left_margin

        width = printer.width()  #- 300
        height = printer.height()  #- 300

        if self.pdf_options.print_4_per_page:
            width = width // 2
            height = height // 2
            for (x, y) in ((0, 0), (0, 1), (1, 0), (1, 1)):
                song_width = width - left_margin - right_margin
                song_height = height - top_margin - bottom_margin

                song_top = top_margin + y * height
                song_left = left_margin + x * width

                # FIXME either use QRectF or use integers instead of floats
                paint_rect = QtCore.QRect(song_left, song_top, song_width,
                                          song_height)
                scale_ratio = self.drawSongToRect(song,
                                                  painter,
                                                  paint_rect,
                                                  exporting=True)
        else:
            song_width = width - left_margin - right_margin
            song_height = height - top_margin - bottom_margin
            song_top = top_margin
            song_left = left_margin
            # FIXME either use QRectF or use integers instead of floats
            paint_rect = QtCore.QRect(song_left, song_top, song_width,
                                      song_height)
            scale_ratio = self.drawSongToRect(song,
                                              painter,
                                              paint_rect,
                                              exporting=True)

        return scale_ratio

    # FIXME FIXME Re-factor out the common code from these two methods!

    def printTableOfConentsPage(self, lines, printer, painter, page_num):
        """
        Print the given table of contents pages to the given printer/painter.
        page_num is used to determine whether to use alternate margins.
        """

        # Figure out what the margins should be:
        # Convert to points (from inches):
        left_margin = self.pdf_options.left_margin * 72.0
        right_margin = self.pdf_options.right_margin * 72.0
        top_margin = self.pdf_options.top_margin * 72.0
        bottom_margin = self.pdf_options.bottom_margin * 72.0

        if self.pdf_options.alternate_margins and not page_num % 2:
            # If alternating margins and this is an even page:
            left_margin, right_margin = right_margin, left_margin

        width = printer.width()  #- 300
        height = printer.height()  #- 300

        if self.pdf_options.print_4_per_page:
            width = width // 2
            height = height // 2
            for (x, y) in ((0, 0), (0, 1), (1, 0), (1, 1)):
                song_width = width - left_margin - right_margin
                song_height = height - top_margin - bottom_margin

                song_top = top_margin + y * height
                song_left = left_margin + x * width

                paint_rect = QtCore.QRect(song_left, song_top, song_width,
                                          song_height)
                self.drawTableOfContentsPageToRect(lines, painter, paint_rect)
        else:
            song_width = width - left_margin - right_margin
            song_height = height - top_margin - bottom_margin
            song_top = top_margin
            song_left = left_margin
            paint_rect = QtCore.QRect(song_left, song_top, song_width,
                                      song_height)
            self.drawTableOfContentsPageToRect(lines, painter, paint_rect)

    # FIXME combine this code with the margin code aboce:

    def getPrintableHeight(self, printer):

        top_margin = self.pdf_options.top_margin * 72
        bottom_margin = self.pdf_options.bottom_margin * 72

        height = printer.height()  #- 300
        if self.pdf_options.print_4_per_page:
            height = height / 2.0

        return height - top_margin - bottom_margin

    def exportToSinglePdf(self, pdf_file=None):
        """
        Exports the selected songs to a PDF file.
        """

        self.sendCurrentSongToDatabase()

        song_ids = self.getSelectedSongIds()
        if not song_ids:
            # No selection, export all songs:
            song_ids = self.songs_model.getAllSongIds()

        if not pdf_file:
            ok = PdfDialog(self).display(self.pdf_options,
                                         single_pdf_export=True)
            if not ok:
                return

            if len(song_ids) == 1:
                suggested_path = os.path.join(QtCore.QDir.home().path(),
                                              self.current_song.title + ".pdf")
            else:
                suggested_path = QtCore.QDir.home().path()

            pdf_file = QtWidgets.QFileDialog.getSaveFileName(
                self.win,
                "Save PDF file as:",
                suggested_path,
                "PDF format (*.pdf)",
            )

            if not pdf_file:
                # User cancelled
                return

        self.setWaitCursor()
        # TODO factor out duplication
        try:
            printer = QPrinter()
            if self.pdf_options.print_4_per_page:
                page_size = QtCore.QSizeF(self.pdf_options.page_width * 2.0,
                                          self.pdf_options.page_height * 2.0)
            else:
                page_size = QtCore.QSizeF(self.pdf_options.page_width,
                                          self.pdf_options.page_height)
            page_size = QtGui.QPageSize(page_size, QtGui.QPageSize.Unit.Inch)
            printer.setPageSize(page_size)
            printer.setFullPage(
                True)  # considers whole page instead of only printable area.
            printer.setPageOrientation(QtGui.QPageLayout.Orientation.Portrait)
            printer.setOutputFileName(pdf_file)

            if sys.platform == 'win32':
                printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            elif sys.platform == 'darwin':
                # DON'T set it to NativeFormat, as that messes
                # page size on export
                printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)

            num_printed = self.printSongsToPrinter(song_ids, printer,
                                                   "Exporting to PDF...")
            # On IOError, num_printed will be 0.

        except Exception as err:
            self.restoreCursor()
            self.error("Error exporting:\n\n%s " % traceback.format_exc())
        else:
            self.restoreCursor()

    def exportToMultiplePdfs(self):
        """
        Exports the selected songs, each to its own PDF file.
        """

        self.sendCurrentSongToDatabase()

        song_ids = self.getSelectedSongIds()
        if len(song_ids) == 0:
            # No song is selected, export all.
            song_ids = self.songs_model.getAllSongIds()

        ok = PdfDialog(self).display(self.pdf_options, single_pdf_export=False)
        if not ok:
            return

        suggested_dir = QtCore.QDir.home().path()
        dir = QtWidgets.QFileDialog.getExistingDirectory(
            self.win,
            "Save PDF file in directory:",
            suggested_dir,
        )
        if not dir:
            # User cancelled
            return

        progress = QtWidgets.QProgressDialog("Exporting to PDFs...", "Abort", 0,
                                         len(song_ids), self.win)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        # Open the progress dialog right away:
        progress.setMinimumDuration(0)

        min_scale_ratio = 1.0
        for i, song_id in enumerate(song_ids):
            progress.setValue(i)

            if progress.wasCanceled():
                break

            song = Song(self, song_id)

            # Set this song's document (will be reset later):
            self.print_editor.setDocument(song.doc)
            # NOTE: Messing with this stuff may cause the app to crash on Windows (compiled)

            pdf_file = os.path.join(dir, song.title + ".pdf")

            # TODO factor out duplication
            try:
                printer = QPrinter()
                if self.pdf_options.print_4_per_page:
                    page_size = QtCore.QSizeF(
                        self.pdf_options.page_width * 2.0,
                        self.pdf_options.page_height * 2.0)
                else:
                    page_size = QtCore.QSizeF(self.pdf_options.page_width,
                                              self.pdf_options.page_height)
                page_size = QtGui.QPageSize(page_size, QtGui.QPageSize.Unit.Inch)
                printer.setPageSize(page_size)
                printer.setFullPage(
                    True
                )  # considers whole page instead of only printable area.
                printer.setPageOrientation(QtGui.QPageLayout.Orientation.Portrait)
                printer.setOutputFileName(pdf_file)

                # OLD: printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
                if sys.platform == 'win32':
                    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
                elif sys.platform == 'darwin':
                    printer.setOutputFormat(QPrinter.OutputFormat.NativeFormat)

                painter = QtGui.QPainter()
                if not painter.begin(printer):
                    raise IOError("Failed to open the output file for writing")

                # Always print the song as if to the first page, when exporting to multiple PDFs:
                scale_ratio = self.printSong(song, printer, painter, 1)
                if scale_ratio < min_scale_ratio:
                    min_scale_ratio = scale_ratio

                painter.end()

            except Exception as err:
                self.restoreCursor()
                self.error("Error generating PDF:\n%s" % str(err))
                raise

        progress.setValue(i + 1)  # Close the progress dialog
        self.print_editor.setDocument(self.empty_doc)

        self.reportScaleRatio(min_scale_ratio, len(song_ids))

    def reportScaleRatio(self, min_scale_ratio, num_songs):

        if min_scale_ratio != 1.0:
            scale_percent = min_scale_ratio * 100.0
            if num_songs > 1:
                self.info(
                    "Some songs were scaled down up to %.1f%% to fit the page."
                    % scale_percent)
            else:
                self.info(
                    "The song was scaled down to %.1f%% to fit the page." %
                    scale_percent)

    def cutSelected(self):
        """
        Cut the selected chord (if any) into the clipboard.
        """
        chord = self.getSelectedChord()
        if chord:
            chord_text = chord.getChordText()
            self.clipboard.setText(chord_text)
            self.current_song.deleteChord(chord)

    def copySelected(self):
        """
        Copy the selected chord (if any) into the clipboard.
        """
        chord = self.getSelectedChord()
        if chord:
            chord_text = chord.getChordText()
            self.clipboard.setText(chord_text)

    def pasteSelected(self):
        """
        Paste the chord of the clipboard (if any) onto the selected character (if any)
        """

        if self.editor.lyric_editor_mode:
            self.editor.paste()
            return

        if self.selected_char_num == None or not self.current_song:
            return

        text = self.clipboard.text()

        try:
            converted_chord = self.convertChordFromString(text)
        except ValueError as err:
            print("not a chord")
            return

        (marker, note_id, type_id, bass_id, in_parentheses) = converted_chord
        new_chord = SongChord(self.current_song, self.selected_char_num,
                              note_id, type_id, bass_id, marker, in_parentheses)

        prev_chord = None
        for chord in self.current_song.iterateAllChords():
            if chord.character_num == self.selected_char_num:
                prev_chord = chord
                break

        if prev_chord:
            # Replacing exising chord
            self.current_song.replaceChord(prev_chord, new_chord)
        else:
            # Adding a new chord
            self.current_song.addChord(new_chord)

    def copySongText(self):
        """
        Copy the selected song's text to the clipboard.
        The chords are included (as separate lines above the lyrics)
        """

        # self.sendCurrentSongToDatabase()

        if not self.current_song:
            self.warning("Please select a song first")
            return

        self.setWaitCursor()

        song_text = self.current_song.getAsText()

        # Fix the line endings that that they work on all OSes, including Windows NotePad:
        song_text = song_text.replace('\n', '\r\n')
        # FIXME is that needed?

        self.clipboard.setText(song_text)

        self.restoreCursor()

    def exportToText(self, text_file=None):
        """
        Exports the selected song (one) to a TEXT file.
        """

        self.sendCurrentSongToDatabase()

        self.setWaitCursor(
        )  # For some reason, without this line, the selection is not updated yet when running softchord_test.py
        if not self.getSelectedSongIds():
            self.error("No songs are selected")
            return
        elif len(self.getSelectedSongIds()) > 1:
            self.error("More than one song is selected.")
            return

        if not text_file:
            suggested_path = os.path.join(QtCore.QDir.home().path(),
                                          self.current_song.title + ".txt")

            text_file = QtWidgets.QFileDialog.getSaveFileName(
                self.win,
                "Save text file as:",
                suggested_path,
                "Text format (*.txt)",
            )
        if text_file:
            self.setWaitCursor()
            try:
                with codecs.open(text_file, 'w', encoding='utf_8_sig') as fh:
                    for song_index, song_id in enumerate(self.getSelectedSongIds()):
                        # NOTE for now there will always be only one song exported.
                        song = Song(self, song_id)

                        # Encode the unicode string as UTF-8 before writing to file:
                        song_text = song.getAsText()

                        # Fix the line endings that that they work on all OSes, including Windows NotePad:
                        song_text = song_text.replace('\n', '\r\n')

                        fh.write(song_text)
            finally:
                self.restoreCursor()

    def exportToChordPro(self, filename=None):
        """
        Exports the selected song (one) to a ChordPro format.
        """

        self.sendCurrentSongToDatabase()

        self.setWaitCursor(
        )  # For some reason, without this line, the selection is not updated yet when running softchord_test.py
        if not self.getSelectedSongIds():
            self.error("No songs are selected")
            return
        elif len(self.getSelectedSongIds()) > 1:
            self.error("More than one song is selected.")
            return

        if not filename:
            suggested_path = os.path.join(QtCore.QDir.home().path(),
                                          self.current_song.title + ".chordpro")

            filename = QtWidgetrs.QFileDialog.getSaveFileName(
                self.win,
                "Save text file as:",
                suggested_path,
                "ChordPro format (*.chordpro)",
            )
        if filename:
            self.setWaitCursor()
            try:
                with codecs.open(filename, 'w', encoding='utf_8_sig') as fh:
                    for song_index, song_id in enumerate(self.getSelectedSongIds()):
                        # NOTE for now there will always be only one song exported.
                        song = Song(self, song_id)

                        song_text = song.getAsChordProText()

                        # Fix the line endings that that they work on all OSes, including Windows NotePad:
                        song_text = song_text.replace('\n', '\r\n')

                        fh.write(song_text)
            finally:
                self.restoreCursor()

    def currentSongTitleEdited(self, new_title):
        """
        Called when the user modifies the selected song's title.
        """
        if self.current_song:
            new_title = new_title.strip()  # Remove any EOL characters, etc.
            self.current_song.title = new_title
            self.setWaitCursor()
            try:
                self.curs.execute('UPDATE songs SET title=? WHERE id=?',
                                  (new_title, self.current_song.id))
                self.curs.commit()

                row_num = self.songs_model.getSongsRow(self.current_song)
                rowobj = self.songs_model.getRow(row_num)

                rowobj.title = new_title

                self.songs_model.setRow(row_num, rowobj)

            finally:
                self.restoreCursor()

    def subtitleEdited(self, new_note_str):
        """
        User has specified a new song note (comment).
        """

        if not self.current_song:
            raise ValueError("No current song")

        self.current_song.subtitle = new_note_str
        self.setWaitCursor()
        try:
            self.curs.execute('UPDATE songs SET subtitle=? WHERE id=?',
                              (new_note_str, self.current_song.id))
            self.curs.commit()

            row_num = self.songs_model.getSongsRow(self.current_song)
            rowobj = self.songs_model.getRow(row_num)
            rowobj.subtitle = new_note_str
        finally:
            self.restoreCursor()

    def currentSongNumberEdited(self, new_num_str):
        """
        Called when the user modifies the selected song's number.
        """
        if self.current_song:
            if new_num_str == "":
                new_num_str = -1  # NULL
            try:
                new_num = int(new_num_str)
            except:
                self.error("Invalid song number")
            else:
                self.current_song.number = new_num
                self.curs.execute('UPDATE songs SET number=%i WHERE id=%i' %
                                  (new_num, self.current_song.id))
                self.curs.commit()

                # Save the selection:
                selected_row_num = self.songs_model.getSongsRow(
                    self.current_song)

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
            is_major = -1
        else:
            note_id = (new_key_index - 1) // 2
            is_major = (new_key_index - 1) % 2

        if note_id != self.current_song.key_note_id or is_major != self.current_song.key_is_major:
            self.current_song.key_note_id = note_id
            self.current_song.key_is_major = is_major

            self.sendCurrentSongToDatabase()
            self.editor.viewport().update()

    def currentSongAltKeyChanged(self, new_alt_key_index):
        """
        Called when the user modifies the selected song's key.
        """

        if self.ignore_song_key_changed:
            return

        if self.current_song == None:
            return

        song_id = self.current_song.id

        if new_alt_key_index == 0:  # "None" menu item
            alt_key_note_id = -1
        else:
            alt_key_note_id = (new_alt_key_index - 1)

        if alt_key_note_id != self.current_song.alt_key_note_id:
            self.current_song.alt_key_note_id = alt_key_note_id

            self.sendCurrentSongToDatabase()
            self.editor.viewport().update()

    def createNewSong(self):
        """
        Add a new song to the database and the songs table, and select it.
        """

        row = self.curs.execute("SELECT MAX(id) from songs").fetchone()
        if row[0] == None:
            song_id = 0
        else:
            song_id = row[0] + 1

        out = self.curs.execute(
            "INSERT INTO songs (id, number, title, subtitle, text) VALUES (?, ?, ?, ?, ?)",
            (song_id, -1, "", "", ""))
        self.curs.commit()

        # Update the song table from database:
        self.songs_model.updateFromDatabase()

        # Select the newly added song:
        source_index = self.songs_model.index(self.songs_model.rowCount() - 1,
                                              0)
        proxy_index = self.songs_proxy_model.mapFromSource(source_index)
        self.ui.songs_view.selectRow(proxy_index.row())

        song = Song(self, song_id)
        self.setCurrentSong(song)

        ####self.updateCurrentSongFromDatabase() # FIXME REMOVE
        self.lyricEditorSelected()

    def deleteSelectedSongs(self):
        """
        Deletes the selected song(s).
        """
        selected_song_ids = self.getSelectedSongIds()

        # Will set the current song to None:
        self.ui.songs_view.selectionModel().clearSelection()
        #self.setCurrentSong(None)

        self.undo_stack.push(DeleteSongsCommand(self, selected_song_ids))

        #self.updateStates()
        self.updateEditMenu()

    def removeTrailingSpaces(self):

        # FIXME Save the current song to database?

        for song_index, song_id in enumerate(self.getSelectedSongIds()):
            song = Song(self, song_id)
            song.removeTrailingSpaces()

        # FIXME Update the current song from database

    def renumberAllSongs(self):
        """
        Re-number all songs in the database (song number, not IDs).
        """

        if not self.question(
                "All songs in the songbook will be renumbered consecutively starting with 1. Continue?"
        ):
            return

        all_song_ids = self.songs_model.getAllSongIds()

        for song_num, song_id in enumerate(all_song_ids, start=1):
            self.curs.execute('UPDATE songs SET number=? WHERE id=?',
                              (song_num, song_id))
        self.curs.commit()

        # Update the song table from database:
        self.songs_model.updateFromDatabase()

    def question(self,
                 msg,
                 button1="OK",
                 button2="Cancel",
                 title="softChord - Question"):
        """ 
        Display a prompt dialog window with specified text.
        Returns True if first button (default OK) is pressed, False otherwise.
        """
        mbox = QtWidgets.QMessageBox(self.win)
        mbox.setText(msg)
        mbox.setWindowTitle(title)
        mbox.setIcon(QtWidgets.QMessageBox.Question)
        b1 = mbox.addButton(button1, QtWidgets.QMessageBox.ActionRole)
        b2 = mbox.addButton(button2, QtWidgets.QMessageBox.RejectRole)
        mbox.exec()
        return (mbox.clickedButton() == b1)

    def setSongDatabaseId(self):
        """
        Give the selected song a new song ID in the database.
        """

        curr_id = self.current_song.id
        next_id = None

        all_song_ids = self.songs_model.getAllSongIds()

        new_id, ok = QtGui.QInputDialog.getInteger(
            self.win, "softChord", "Enter a new ID for this song:", curr_id, 1)
        if not ok or new_id == curr_id:
            # User cancelled or selected same ID
            return

        if new_id in all_song_ids:
            song = Song(self, new_id)
            self.error("The ID %i is already used by song #%s (%s)" %
                       (new_id, song.number, song.title))
            return

        self.curs.execute('UPDATE songs SET id=? WHERE id=?', (new_id, curr_id))
        self.curs.execute(
            "UPDATE song_chord_link SET song_id=? WHERE song_id=?",
            (new_id, curr_id))
        self.curs.commit()

        # Update the song table from database:
        self.songs_model.updateFromDatabase()

    def getCharRects(self, editor, song_char_num, chord=None):
        cursor = editor.textCursor()

        if chord != None:
            has_chord = True
        else:
            has_chord = False
            for chord in self.current_song._chords:
                if chord.character_num == song_char_num:
                    has_chord = True
                    break

        if has_chord:
            chords_height, lyrics_height, line_height = self.getHeightsWithChords(
            )
        else:
            chords_height, lyrics_height, line_height = self.getHeightsWithoutChords(
            )

        # Find the bounding rect for this character:
        cursor.setPosition(song_char_num)
        left_rect = editor.cursorRect(cursor)
        cursor.setPosition(song_char_num + 1)
        right_rect = editor.cursorRect(cursor)

        char_left = left_rect.left()
        char_right = right_rect.right()

        char_top = left_rect.top()
        char_bottom = left_rect.bottom()

        char_width = right_rect.right() - left_rect.left()
        char_height = left_rect.bottom() - left_rect.top()
        char_rect = QtCore.QRectF(left_rect.left(), left_rect.top(), char_width,
                                  char_height)

        if has_chord:
            chord_top = left_rect.bottom() - line_height
            chord_text = chord.getChordText()
            chord_middle = (char_left +
                            char_right) // 2  # Average of left and right
            chord_width = self.chords_font_metrics.horizontalAdvance(chord_text)

            chord_width = self.getChordWidth(chord_text)
            chord_left = chord_middle - (chord_width / 2.0)
            chord_rect = QtCore.QRectF(chord_left, chord_top, chord_width,
                                       chords_height)
        else:
            chord_rect = None

        return char_rect, chord_rect

    def getChordWidth(self, chord_text):

        width = 0.0
        for letter in chord_text:
            if letter in ["♯", "♭"]:
                width += self.symbols_font_metrics.horizontalAdvance(letter)
            else:
                width += self.chords_font_metrics.horizontalAdvance(letter)
        return width

    def drawChord(self, painter, chord_rect, chord_text):
        """
        Draw the given chord to the given rect of the painter.
        Draws the special symbols in the <symbol> font, which ensures that
        the spacing is correct.
        """

        r = chord_rect.right()

        normal_height = self.chords_font_metrics.height()
        normal_baseline = chord_rect.bottom() - (0.2 * normal_height
                                                )  # FIXME hack

        chord_left = chord_rect.left()

        chord_width = chord_rect.width()
        chord_center = (chord_rect.right() - chord_rect.left()) / 2.0

        letter_left = chord_rect.left()

        curr_left = chord_rect.left()
        orig_top = chord_rect.top()
        raise_distance = chord_rect.height(
        ) / 10.0  # Distance to raise the flat/sharp signs by
        raised_top = chord_rect.top() - raise_distance
        raised_baseline = normal_baseline - raise_distance

        for letter in chord_text:
            #letter_rect = QtCore.QRect(letter_left, chord_rect.top(), 1000.0, 1000.0)
            if letter in ["♯", "♭"]:
                # FIXME: On Windows, the flat is drawn a little off
                #letter_rect.setTop(raised_top)
                painter.setFont(self.symbols_font)
                let_width = self.symbols_font_metrics.horizontalAdvance(letter)
                baseline = raised_baseline
            else:
                #letter_rect.setTop(orig_top)
                painter.setFont(self.chords_font)
                let_width = self.chords_font_metrics.horizontalAdvance(letter)
                baseline = normal_baseline

            #bound_rect = painter.drawText(letter_rect, QtCore.Qt.AlignLeft, letter)

            pos = QtCore.QPointF(letter_left, baseline)
            painter.drawText(pos, letter)

            #letter_left = bound_rect.right()
            letter_left += let_width

        # FIXME restore chord_rect and font?

    def _drawSongToPainter(self, song, painter, header_list, exporting=False):
        """
        Draw the given song to the given painter.
        Always draws the main text and chords.
        When not exporting, draws selection rects as well.
        When exporting, optionally draws song num and/or title.
        """

        # NOTE: Everything here is unscaled (original font sizes, etc)

        if exporting:
            editor = self.print_editor
        else:
            editor = self.editor

        if not exporting:
            # On Windows, don't use the default dark blue, as it will not work correctly
            # With default chord and text colors (blue and black):
            if self.on_windows:
                selection_brush = QtGui.QColor("light blue")
            else:
                selection_brush = QtGui.QPalette().highlight()
            hover_brush = QtGui.QColor("light grey")

            # Draw any selection rects:
            if self.hover_char_num != None:
                char_rect, chord_rect = self.getCharRects(
                    editor, self.hover_char_num)

                # Mouse is currently hovering over this letter:
                # Draw a hover rectangle:
                painter.fillRect(char_rect, hover_brush)
                if chord_rect:
                    painter.fillRect(chord_rect, hover_brush)

            if self.selected_char_num != None:
                char_rect, chord_rect = self.getCharRects(
                    editor, self.selected_char_num)

                # Draw a selection rectangle:
                painter.fillRect(char_rect, selection_brush)
                if chord_rect:
                    painter.fillRect(chord_rect, selection_brush)

        for chord in song._chords:
            char_rect, chord_rect = self.getCharRects(editor,
                                                      chord.character_num,
                                                      chord)

            chord_text = chord.getChordText()
            painter.setFont(self.chords_font)

            # On Windows, selected text is drawn in white:
            #if chord.character_num == self.selected_char_num and self.on_windows:
            #    painter.setPen(self.white_color)
            #else:
            painter.setPen(self.chords_color)

            if chord_rect:
                self.drawChord(painter, chord_rect, chord_text)
            else:
                print('no chord rect!')

        # Draw the lyrics document:

        painter.setFont(self.lyrics_font)
        painter.setPen(self.lyrics_color)

        doc = editor.document()

        # When drawing to screen, we need to offset the current scroll bar values:
        # (this will basically raise the document to (0,0) position temporarily)
        if not exporting:
            scroll_x = editor.horizontalScrollBar().value()
            scroll_y = editor.verticalScrollBar().value()
            painter.translate(-scroll_x, -scroll_y)

        doc.drawContents(painter, QtCore.QRectF(0.0, 0.0, 10000.0, 10000.0))

        if not exporting:
            # Revert the scroll offset translation:
            painter.translate(scroll_x, scroll_y)

    def drawSongToRect(self, song, output_painter, rect, exporting=False):
        """
        Draws the current song text to the specified rect.

        exporting - whether we are drawing to a PDF/Print instead of the screen.
        
        When "exporting", the selection/inert cursor are not drawn, and the song number
        IS drawn.
        """

        # FIXME will not account for chord text:
        tf = song.doc.rootFrame()
        layout_bounding_rect = song.doc.documentLayout().frameBoundingRect(tf)

        pic_right = layout_bounding_rect.right()
        pic_bottom = layout_bounding_rect.bottom()
        # FIXME this does not account for the header line and the first chords line

        # Figure out what the scaling factor should be:
        #print "exporting:", exporting, "zoom_factor:", self.zoom_factor
        if not exporting:
            # Painting to screen, zoom factor is already applied to font size
            scale_ratio = 1.0
            actual_scale_ratio = None
        else:
            # Exporting, make sure the song fits into the specified <rect>:
            # Adjust according to the view zoom factor:
            pic_right /= self.zoom_factor
            pic_bottom /= self.zoom_factor

            width_ratio = pic_right / rect.width()
            height_ratio = pic_bottom / rect.height()
            scale_ratio = max(width_ratio, height_ratio)

            if scale_ratio > 1.0:
                scale_ratio = 1.0 / scale_ratio
            else:
                # Do not make songs any bigger
                scale_ratio = 1.0  # / self.zoom_factor # Adjust by the view zoom factor

            # When exporting to PDF, undo the zoom scaling:
            actual_scale_ratio = scale_ratio
            scale_ratio /= self.zoom_factor

        # Height of the header line:
        lyrics_height = self.lyrics_font_metrics.height()

        # Print song number and/or title to the header (first) line:
        header_list = []

        if exporting:
            if self.pdf_options.print_song_num and song.number != -1:
                header_list.append(str(song.number))

            if self.pdf_options.print_song_comment and song.subtitle:
                header_list.append(song.subtitle)

            if self.pdf_options.print_song_key and song.key_note_id != -1:
                #print 'song num:', song.number, 'key_note_id:', song.key_note_id, 'is_major:', song.key_is_major
                song_key_str = "Key: %s" % song._getNoteString(song.key_note_id)
                if not song.key_is_major:
                    song_key_str += "m"

                if song.alt_key_note_id != -1:
                    alt_song_key_str = song._getNoteString(song.alt_key_note_id)
                    if not song.key_is_major:
                        alt_song_key_str += "m"
                    song_key_str += " (%s)" % alt_song_key_str

                header_list.append(song_key_str)

            if self.pdf_options.print_song_title and song.title:
                header_list.append(song.title)

        # Go to songs's reference frame:
        output_painter.translate(rect.left(), rect.top())
        output_painter.scale(scale_ratio, scale_ratio)

        # Offset the editor margins when exporting:
        if exporting:
            output_painter.translate(-self.doc_editor_offset,
                                     -self.doc_editor_offset)

        if header_list:
            # Combine the song number string, song key, song subtitle, and/or song title string:
            header_str = "  ".join(header_list)
            output_painter.setFont(self.lyrics_font)

            x = 5.0  # For some reason needed for alignment
            y = 0.0

            # FIXME what if the title is too long?
            header_rect = QtCore.QRect(x, y, 1000.0, lyrics_height)
            output_painter.drawText(header_rect, QtCore.Qt.AlignLeft,
                                    header_str)

            output_painter.translate(0.0, lyrics_height)

        # Draw the song lyrics and chirds:
        self._drawSongToPainter(song, output_painter, header_list, exporting)
        # output_painter.drawText(100, 100, "TEST")

        if header_list:
            output_painter.translate(0.0, -lyrics_height)

        # Revert the editor margins when exporting:
        if exporting:
            output_painter.translate(self.doc_editor_offset,
                                     self.doc_editor_offset)

        # Redo the effect of scaling:
        output_painter.scale(1.0 / scale_ratio, 1.0 / scale_ratio)

        # Go to the original reference frame:
        output_painter.translate(-rect.left(), -rect.top())

        return actual_scale_ratio

    # FIXME FIXME factor-out the common code between these two methods!

    def drawTableOfContentsPageToRect(self, lines, painter, rect):
        """
        Draws the given table of contents page to the specified rect.
        <lines> is a list of (song_name, song_num) tuples for this page.
        """

        # Go to songs's reference frame:
        painter.translate(rect.left(), rect.top())

        max_width = rect.width()
        max_height = rect.height()
        max_name_width = max_width - self.lyrics_font_metrics.width(".999")

        lyrics_height = self.lyrics_font_metrics.height()
        dot_char_width = self.lyrics_font_metrics.width(".")

        curr_height = 0.0
        for song_name, song_num in lines:
            # Keep removing the last word of the song title until it fits into a line:
            while self.lyrics_font_metrics.width(song_name) > max_name_width:
                # Remove the last word:
                s = song_name.split()
                if len(s) == 1:
                    # Only left with one word
                    break
                # If there IS something to remove
                remove_chars = len(s[-1]) + 1
                song_name = song_name[:-remove_chars]

            name_bounds_rect = painter.drawText(0, curr_height, max_width,
                                                lyrics_height, Qt.AlignLeft,
                                                song_name)
            num_bounds_rect = painter.drawText(0, curr_height, max_width,
                                               lyrics_height, Qt.AlignRight,
                                               str(song_num))

            dots_left = name_bounds_rect.right()
            dots_right = num_bounds_rect.left()
            dots_width = dots_right - dots_left

            num_dots = int(dots_width // dot_char_width)

            if num_dots >= 3:
                dots_str = '.' * (num_dots - 2)
                dots_str = ' ' + dots_str + ' '

                # FIXME display dots a bit higher
                painter.drawText(dots_left, curr_height, dots_width,
                                 lyrics_height, Qt.AlignLeft, dots_str)

            curr_height += lyrics_height

        # Go to the original reference frame:
        painter.translate(-rect.left(), -rect.top())

    def determineClickedLetter(self, x, y, dragging):
        """
        Determine where the specified (local) mouse coordinates position.
        That is, which lyric or chord letter was the mouse above when this
        event happened.
        """

        if not self.current_song:
            return None

        # Scale:
        #x = float(x) / self.zoom_factor
        #y = float(y) / self.zoom_factor

        for chord in self.current_song._chords:
            song_char_num = chord.character_num
            char_rect, chord_rect = self.getCharRects(self.editor,
                                                      chord.character_num,
                                                      chord)

            if y > chord_rect.top() and y < chord_rect.bottom():
                if y < chord_rect.bottom() and not dragging:
                    # Mouse is over the chord height:
                    if chord_rect and x > chord_rect.left(
                    ) and x < chord_rect.right():
                        is_chord = True
                        return (is_chord, chord.character_num)
                else:
                    # Mouse is over the lyrics height OR we are dragging
                    if x > chord_rect.left() and x < chord_rect.right():
                        is_chord = False
                        return (is_chord, chord.character_num)

        # Not over a chord, check the letter:
        offset_x = x - 5.0

        if self.editor.dragging_chord:
            # Make sure drag obove (not over) a letter would be cought:
            chord = self.editor.dragging_chord
            char_rect, chord_rect = self.getCharRects(self.editor,
                                                      chord.character_num,
                                                      chord)
            if y > chord_rect.top() and y < char_rect.top():
                y = char_rect.top() + 1

        cursor = self.editor.cursorForPosition(QtCore.QPoint(offset_x, y))

        # If at the start or end of line, make sure the cursor is actually over a character:
        at_start = cursor.atBlockStart()
        at_end = cursor.atBlockEnd()
        if at_start or at_end:
            r = self.editor.cursorRect(cursor)
            if at_start and x < r.left():
                return None
            if at_end and x >= r.right():
                return None

        pos = cursor.position()
        return (False, pos)

    def processSongCharEdit(self, song_char_num):
        """
        Bring up a dialog that will allow the user to add/modify the chord at
        the specified position.
        """

        add_new = True
        orig_chord = None
        for iter_chord in self.current_song.iterateAllChords():
            if iter_chord.character_num == song_char_num:
                add_new = False
                orig_chord = iter_chord
                break

        if add_new:
            new_chord = SongChord(self.current_song, song_char_num, 0, 0, -1,
                                  "", False)
        else:
            new_chord = copy.copy(orig_chord)

        ok = ChordDialog(self).display(new_chord)
        if ok:
            # Ok pressed
            if add_new:
                self.current_song.addChord(new_chord)
            else:
                self.current_song.replaceChord(orig_chord, new_chord)

            #self.sendCurrentSongToDatabase()

            self.editor.viewport().update()

    def importFromChordPro(self, filename=None):
        """
        Lets the user select a ChordPro file to import.
        """
        if not filename:
            filter_string = "ChordPro format (%s)" % ' '.join(
                ['*' + ext for ext in chordpro_extensions])
            chordpro_files = QtWidgets.QFileDialog.getOpenFileNames(
                self.win,
                "Select a ChordPro file to import",
                QtCore.QDir.home().path(),  # initial dir
                filter_string,
            )
        else:
            chordpro_files = [filename]

        if chordpro_files:
            self.setWaitCursor()
            try:
                for filename in chordpro_files:
                    # "rU" makes sure that the line endings are handled properly:
                    # file_text = codecs.open(filename.encode('utf-8'), 'rU', encoding='utf_8_sig').read()
                    with codecs.open(filename, 'rU', encoding='utf_8_sig') as fh:
                        file_text = fh.read()
                    self.importSongFromChordProText(file_text)
            finally:
                self.restoreCursor()

    def clipboardChanged(self):
        """
        Enable/disable the "Paset As New Song" menu item.
        """

        text = self.clipboard.text()
        self.ui.actionPasteAsNewSong.setEnabled(not text.isEmpty())
        self.updateEditMenu()

    def pasteAsNewSong(self):
        """
        Paste text from clipboard as a new song.
        """

        if self.current_songbook_filename == None:
            self.warning("Please open/create a song book first")
            return

        self.setWaitCursor()
        text = self.clipboard.text()
        try:
            self.importSongFromText(text)
        except Exception as err:
            self.restoreCursor()
            self.error("Error parsing the text:\n\n%s " %
                       traceback.format_exc())
        else:
            self.restoreCursor()

    def browseForTextFile(self):
        """
        Lets the user select a text file to import.
        """
        text_files = QtWidgets.QFileDialog.getOpenFileNames(
            self.win,
            "Select a text file to import",
            QtCore.QDir.home().path(),  # initial dir
            "Text format (*.txt *.text)",  ###### *.textClipping)", # *.textClipping is used on MacOSX
        )
        if text_files:
            self.importTextFiles(text_files)

    def importTextFiles(self, text_files):
        self.setWaitCursor()
        try:
            for filename in text_files:
                song_title = os.path.splitext(os.path.basename(filename))[0]

                # "rU" makes sure that the line endings are handled properly:
                with open(filename, 'rU', encoding='utf_8_sig') as fh:
                    text = fh.read()
                    try:
                        self.importSongFromText(text, song_title)
                    except Exception as err:
                        self.restoreCursor()
                        self.error("Error parsing the text:\n\n%s " %
                               traceback.format_exc())
                        break
        finally:
            self.restoreCursor()

    def importSongFromText(self, input_text, song_title=None):
        """
        Adds the song specified with the given text to the database.
        input_text should contain all lines, decoded, in Unicode.
        
        If the title is not specified, then the first line of the lyrics
        becomes the title.
        
        Will raise an exception if an error in the text was found.
        """

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

        song_lines = []  # each item is a tuple of line text and chord list.

        prev_chords = {}
        for line in song_text:
            #line = line[:-1]

            # Attempt to convert the line to chords:
            num_chords = 0
            num_non_chords = 0

            tmp_chords = {}  # Key: line_char_num, value: converted chord
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
                        words.append((current_word, current_word_start, i - 1))
                        current_word = None

            if current_word:
                words.append((current_word, current_word_start, i))

            # Try to break up words that contain multiple chords:
            NOTES = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
            modified_words = []
            for word, word_start, word_end in words:
                word = replace_russian_characeters(word)

                num_notes = 0
                for char in word:
                    if char in NOTES:
                        num_notes += 1
                    elif char == '/':
                        num_notes -= 1

                if num_notes > 1:
                    # Try to break up the word:
                    chord_starts = [word_start]

                    char_pos = word_start
                    for char in word[1:]:
                        char_pos += 1  # Start with second char
                        if char in NOTES:
                            chord_starts.append(char_pos)

                    # FIXME This will not handle parenthesis and markers properly

                    for i, chord_start in enumerate(chord_starts):
                        try:
                            chord_end = chord_starts[i + 1] - 1
                        except IndexError:
                            chord_end = word_end

                        chord_text = word[chord_start - word_start:chord_end -
                                          word_start + 1]

                        modified_words.append(
                            (chord_text, chord_start, chord_end))

                else:
                    modified_words.append((word, word_start, word_end))

            for word, word_start, word_end in modified_words:
                if word == u'/':
                    num_chords += 1
                    converted_chord = None
                else:
                    try:
                        converted_chord = self.convertChordFromString(word)
                    except ValueError as err:
                        tmp_warnings.append('  WARNING: %s; chord: "%s"' %
                                            (str(err), word))
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
                    print(warning_str)
            else:
                # This is a lyrics line
                if prev_chords:
                    # Strip the EOF character (not always present):
                    line = line.rstrip()

                    # Add spaces to the end of <line> if necessary:
                    for line_char_num in prev_chords.keys():
                        if line_char_num >= len(line):
                            line += ' ' * (line_char_num - len(line) + 1)
                    song_lines.append((line, prev_chords))
                else:
                    # The line before was NOT a chords line - no chords for this lyrics line
                    song_lines.append((line, {}))
                prev_chords = []

        # If the title is not specified, set it to the first line of lyrics:
        if song_title == None and song_lines:
            # Also remove leading and trailing spaces:
            song_title = song_lines[0][0].strip()
            # Strip "1." (if present):
            for find_str in [
                    "1", "Пр.", "Припев"
                    "Chorus", "Куплет", ".", ":", ")"
            ]:
                if song_title.startswith(find_str):
                    song_title = song_title[len(find_str):].strip()
            # Remove any trailing punctuation marks:
            if song_title and song_title[-1] in [",", ".", ";", ":"
                                                ]:  # NOTE: question mark is ok
                song_title = song_title[:-1]
            if not song_title:
                # In case all of the title got stripped
                song_title = "Unknown"

        # Make a global-reference text and chords dict:
        global_song_text = ""
        global_song_chords = {}  # key: position in the global_song_text
        line_start_char_num = 0
        for lyrics, chords_dict in song_lines:
            global_song_text += lyrics + '\n'
            for line_char_num, chord in chords_dict.items():
                song_char_num = line_char_num + line_start_char_num
                global_song_chords[song_char_num] = chord

            line_start_char_num += len(lyrics) + 1  # 1 for the EOL character

        self._importSongFromLyricsAndChords(song_num, song_title, "",
                                            global_song_text,
                                            global_song_chords)

    def _importSong(self, song_num, song_title, song_subtitle, song_text,
                    key_note_id, key_is_major, alt_key_note_id):
        """
        Import the given song (except chords).
        Returns the ID assigned to the new song.
        NOTE: curs.commit() MUST be called afterwards.
        """

        row = self.curs.execute("SELECT MAX(id) from songs").fetchone()
        if row[0] == None:
            song_id = 0
        else:
            song_id = row[0] + 1

        self.curs.execute(
            "INSERT INTO songs (id, number, title, subtitle, text, key_note_id, key_is_major, alt_key_note_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (song_id, song_num, song_title, song_subtitle, song_text,
             key_note_id, key_is_major, alt_key_note_id))

        return song_id

    def _importChord(self,
                     song_id,
                     song_char_num,
                     note_id,
                     type_id,
                     bass_id,
                     marker,
                     in_parentheses,
                     chord_id=None):
        """
        Import the given chord to the database.
        Returns the ID assigned to the new chord entry (if ID was not given).
        NOTE: curs.commit() MUST be called afterwards.
        """

        if chord_id == None:
            # Get the next available ID:
            row = self.curs.execute(
                "SELECT MAX(id) from song_chord_link").fetchone()
            if row[0] == None:
                chord_id = 0
            else:
                chord_id = row[0] + 1

        if not marker:
            marker = ""
        in_parentheses = int(in_parentheses)
        self.curs.execute('INSERT INTO song_chord_link (id, song_id, character_num, note_id, chord_type_id, bass_note_id, marker, in_parentheses) ' + \
                    'VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (chord_id, song_id, song_char_num, note_id, type_id, bass_id, marker, in_parentheses))

        return chord_id

    def _importSongFromLyricsAndChords(self,
                                       song_num=-1,
                                       song_title="",
                                       song_subtitle="",
                                       song_text="",
                                       song_chords=None):
        """
        Import the given song to the database.
        song_chords (optional) should be a dict: key=song_char_num, values: (marker, note_id, type_id, bass_id, in_parentheses)
        """

        song_id = self._importSong(song_num,
                                   song_title,
                                   song_subtitle,
                                   song_text,
                                   key_note_id=-1,
                                   key_is_major=-1,
                                   alt_key_note_id=-1)

        # Add song's chords (if any):
        chord_id = None  # So that _importChord() assigned a new ID to the new chord
        if song_chords:
            for song_char_num, chord in song_chords.items():
                (marker, note_id, type_id, bass_id, in_parentheses) = chord

                chord_id = self._importChord(song_id, song_char_num, note_id,
                                             type_id, bass_id, marker,
                                             in_parentheses, chord_id)
                chord_id += 1  # Increment the ID for the next chord.

        self.curs.commit()

        # Update the song table from database:
        self.songs_model.updateFromDatabase()

        # FIXME #index = self.songs_proxy_model.mapToSource(index)
        self.ui.songs_view.selectRow(self.songs_model.rowCount() - 1)

    def importSongFromChordProText(self, song_text):

        song_title = ""
        song_num = -1  # NULL
        song_subtitle = ""

        tmp_warnings = []
        song_lines = []

        for line in song_text.split('\n'):
            line = line.rstrip()  # Remove the EOL character(s)

            if line.startswith('#'):
                # Comment
                continue

            if line.startswith('{') and line.endswith('}'):
                custom_string = line[1:-1]
                if custom_string.startswith('title:'):
                    song_title = custom_string[6:]
                    continue
                elif custom_string.startswith('t:'):
                    song_title = custom_string[2:]
                    continue
                if custom_string.startswith('subtitle:'):
                    # If the subtitle is a number, treat it as a song number:
                    tmp_subtitle = custom_string[9:]
                    try:
                        song_num = int(tmp_subtitle)
                    except:
                        song_subtitle = tmp_subtitle
                    else:
                        continue

                tmp_warnings.append('WARNING: line ignored: "%s"' % line)
                continue

            line_lyrics = ""
            line_chords = []
            curr_chord = None
            curr_adjusted_char_num = 0

            for line_char_num, char in enumerate(line):
                if char == '[':
                    curr_chord = ""
                    continue

                if curr_chord != None:
                    if char == ']':
                        line_chords.append((curr_adjusted_char_num, curr_chord))
                        curr_chord = None
                    else:
                        curr_chord += char
                    continue

                line_lyrics += char
                curr_adjusted_char_num += 1

            chords_dict = {}
            for char_num, chord_text in line_chords:
                try:
                    converted_chord = self.convertChordFromString(chord_text)
                except ValueError as err:
                    tmp_warnings.append('WARNING: %s CHORD "%s"' %
                                        (str(err), word))
                else:
                    chords_dict[char_num] = converted_chord

            song_lines.append((line_lyrics, chords_dict))

        for warning_str in tmp_warnings:
            print('  ', warning_str)

        # Combine all lines together:
        global_song_text = ""
        global_song_chords = {}  # key: position in the global_song_text
        line_start_char_num = 0
        for lyrics, chords_dict in song_lines:
            global_song_text += lyrics + '\n'
            for line_char_num, chord in chords_dict.items():
                song_char_num = line_char_num + line_start_char_num
                global_song_chords[song_char_num] = chord

            line_start_char_num += len(lyrics) + 1  # 1 for the EOL character

        # Attempt to derive the song number from the title:
        # (if it wasn't already set from the subtitle)
        if song_num == -1:
            try:
                song_num = int(song_title)
            except:
                pass

        self._importSongFromLyricsAndChords(song_num, song_title, "",
                                            global_song_text,
                                            global_song_chords)

    def convertChordFromString(self, chord_str):
        """
        Convert the specified chord string to a note_id, chord_type_id, and a bass_note_id.
        """

        chord_str = replace_russian_characeters(chord_str)

        input_chord_str = chord_str[:]

        in_parentheses = chord_str.startswith('(') and chord_str.endswith(')')
        if in_parentheses:
            chord_str = chord_str[1:-1]

        marker = None

        colon = chord_str.find(':')
        if colon != -1:
            if colon == len(chord_str) - 1:
                raise ValueError("Not a chord (nothing after a colon")

            marker = chord_str[:colon]
            chord_str = chord_str[colon + 1:]

        slash = chord_str.find('/')
        if slash != -1:
            bass_str = chord_str[slash + 1:]
            chord_str = chord_str[:slash]
            if len(chord_str) == 0:
                raise ValueError("No characters present before the bass slash")
            if len(bass_str) == 0:
                raise ValueError("No character present after the bass slash")
        else:
            bass_str = None

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

        # Nothing to undo; new database
        self.clearUndoStack()

        self.current_songbook_filename = filename

        if filename is None:
            self.curs = None
            self.win.setWindowTitle("softChord")
        else:
            #self.info('Database: %s; exists: %s' % (songbook_file, os.path.isfile(filename)))
            self.curs = sqlite3.connect(filename)
            songbook_name = os.path.splitext(os.path.basename(filename))[0]
            self.win.setWindowTitle("softChord - %s" % songbook_name)

        self.songs_model.updateFromDatabase()
        self.updateStates()

    def appendSongbookFile(self, filename):
        """
        Append the given songbook to the currently open songbook.
        """

        self.setWaitCursor()
        try:
            # This step can't be undoed:
            self.clearUndoStack()

            self.ui.songs_view.selectionModel().clearSelection()

            curs2 = sqlite3.connect(filename)

            chord_id = None  # So that _importChord() assigned a new ID to the new chord

            for row in curs2.execute(
                    "SELECT number, title, subtitle, text, key_note_id, key_is_major, alt_key_note_id FROM songs ORDER BY id"
            ):
                (song_num, song_title, song_subtitle, song_text, key_note_id,
                 key_is_major, alt_key_note_id) = row
                song_id = self._importSong(song_num, song_title, song_subtitle,
                                           song_text, key_note_id, key_is_major,
                                           alt_key_note_id)

                for row in curs2.execute(
                        "SELECT id, character_num, note_id, chord_type_id, bass_note_id, marker, in_parentheses FROM song_chord_link WHERE song_id=%i"
                        % song_id):
                    (id, song_char_num, note_id, chord_type_id, bass_note_id,
                     marker, in_parentheses) = row

                    chord_id = self._importChord(song_id, song_char_num,
                                                 note_id, chord_type_id,
                                                 bass_note_id, marker,
                                                 id_parentheses, chord_id)
                    chord_id += 1  # Increment the ID for the next chord.

            self.curs.commit()

            self.songs_model.updateFromDatabase()
            self.updateStates()
        finally:
            self.restoreCursor()

    def newSongbook(self):
        songbook_file = QtWidgets.QFileDialog.getSaveFileName(
            self.win,
            "Save songbook as:",
            QtCore.QDir.home().path(),  # initial dir
            "Songbook format (*.songbook)",
        )
        if songbook_file:
            # Overwrite a previous songbook (if any):
            if os.path.isfile(songbook_file):
                os.remove(songbook_file)

            # Open an empty satabase:
            self.curs = sqlite3.connect(songbook_file)

            self.curs.execute(
                "CREATE TABLE song_chord_link(id INTEGER PRIMARY KEY, song_id INTEGER, character_num INTEGER, note_id INTEGER, chord_type_id INTEGER, bass_note_id INTEGER, marker TEXT, in_parentheses INTEGER)"
            )
            self.curs.execute(
                "CREATE TABLE songs (id INTEGER PRIMARY KEY, number INTEGER, text TEXT, title TEXT, subtitle TEXT, key_note_id INTEGER, key_is_major INTEGER, alt_key_note_id INTEGER)"
            )
            self.setCurrentSongbook(songbook_file)

    def openSongbook(self):
        songbook_file, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.win,
            "Select a songbook to open",
            # QtCore.QDir.home().path(), # initial dir
            "Songbook format (*.songbook)",
        )
        if songbook_file:
            self.setCurrentSongbook(songbook_file)

    def closeSongbook(self):
        if self.current_song:
            # Send the current song to the database:
            self.setCurrentSong(None)
        self.setCurrentSongbook(None)

    def saveSongbook(self):

        if self.current_song:
            # Send the current song to the database:
            self.setCurrentSong(None)

        if self.current_songbook_filename == None:
            suggested_path = os.path.join(QtCore.QDir.home().path(),
                                          "My Songbook.songbook")
        else:
            suggested_path = self.current_songbook_filename

        new_songbook_file = None
        while True:
            new_songbook_file = QtWidgets.QFileDialog.getSaveFileName(
                self.win,
                "Save songbook as:",
                suggested_path,
                "Songbook foramt (*.songbook)",
            )
            if not new_songbook_file:
                break
            if os.path.abspath(new_songbook_file) == os.path.abspath(
                    self.current_songbook_filename):
                self.warning(
                    "Please select a new location for the new songbook")
            else:
                break

        if new_songbook_file:
            # User did not cancel

            try:
                shutil.copyfile(self.current_songbook_filename,
                                new_songbook_file)
            except Exception as err:
                self.error(
                    "Could save the songbook to a new location.\n\nException: %s"
                    % err)

            self.setCurrentSongbook(new_songbook_file)

            # FIXME re-open the current song

    def appendSongbookSelected(self):
        """
        Append a user-selected songbook to the currently opened songbook.
        """

        songbook_file = QtWidgets.QFileDialog.getOpenFileName(
            self.win,
            "Select a songbook to append",
            QtCore.QDir.home().path(),  # initial dir
            "Songbook format (*.songbook)",
        )
        if songbook_file:
            self.appendSongbookFile(songbook_file)


def main():
    """
    The main event loop. This function is also run by the Windows executable.
    """

    app = App(sys.argv)
    #print 'applicationDirPath():', app.applicationDirPath()
    #print 'applicationFilePath():', app.applicationFilePath()
    #print 'arguments:', map(unicode, app.arguments())
    #print 'libraryPaths():', map(unicode, app.libraryPaths())
    app.setOverrideCursor(QtGui.QCursor(Qt.CursorShape.WaitCursor))

    input_files = [filename for filename in sys.argv[1:]]

    if input_files:
        if input_files[0].endswith(".songbook"):
            app.setCurrentSongbook(input_files[0])
        else:
            for filename in input_files:
                ext = os.path.splitext(filename)[1]
                if ext == '.txt':
                    app.importTextFiles([filename])
                elif ext in chordpro_extensions:
                    app.importFromChordPro(filename)
                else:
                    print('WARNING: invalid file type:', filename)

    app.restoreOverrideCursor()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

#EOF
