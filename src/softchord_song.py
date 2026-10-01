"""Song model, table models, and undo commands."""

import copy
import sqlite3

from PyQt6 import QtCore, QtGui
from PyQt6.QtCore import Qt

from softchord_chords import (
    PREFER_FLATS,
    PREFER_NEITHER,
    PREFER_SHARPS,
    best_detected_key,
    detect_region_start_indices,
    transpose_note,
)


def document_owner(owner):
    """Return the songbook session when given the QApplication shell.

    A stand-in used by tests has no session and is returned unchanged.
    """
    session = getattr(owner, "session", None)
    if session is not None and session is not owner and hasattr(session, "curs"):
        return session
    return owner


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

    def __init__(self, owner, song_ids):
        QtGui.QUndoCommand.__init__(self)

        self.session = document_owner(owner)
        self.songs = []
        for song_id in song_ids:
            # Load the song from the database:
            song = Song(self.session, song_id)
            self.songs.append(song)

    def undo(self):
        """
        Re-add the deleted song to the database.
        """

        self.session.setWaitCursor()
        try:
            # Get the next available song_chord_link ID:
            row = self.session.curs.execute(
                "SELECT MAX(id) from song_chord_link").fetchone()
            if row[0] == None:
                chord_id = 0
            else:
                chord_id = row[0] + 1

            for song in self.songs:
                song_text = song.getAllText()
                self.session.curs.execute(
                    "INSERT INTO songs (id, number, title, subtitle, text) VALUES (?, ?, ?, ?, ?)",
                    (song.id, song.number, song.title, song.subtitle,
                     song_text))

                # Re-add all the chords:
                for chord in song.iterateAllChords():
                    self.session.curs.execute("INSERT INTO song_chord_link (song_id, character_num, note_id, chord_type_id, bass_note_id, marker, in_parentheses) " + \
                                "VALUES (?, ?, ?, ?, ?, ?, ?)", (chord.song_id, chord.character_num, chord.note_id, chord.chord_type_id, chord.bass_note_id, chord.marker, chord.in_parentheses))
                    chord_id += 1  # Increment the ID for the next chord.

            # Commit database changes:
            self.session.curs.commit()

            # Update the song table from database:
            self.session.songs_model.updateFromDatabase()

        finally:
            self.session.restoreCursor()

    def redo(self):
        """
        Delete the song form the database again
        """

        self.session.setWaitCursor()
        try:
            for song in self.songs:
                # Delete this song:
                self.session.curs.execute("DELETE FROM songs WHERE id=%i" % song.id)

                # Delete all associated chords:
                self.session.curs.execute(
                    "DELETE FROM song_chord_link WHERE song_id=%i" % song.id)

            # Commit database changes:
            self.session.curs.commit()

            # Update the song table from database:
            self.session.songs_model.updateFromDatabase()

        finally:
            self.session.restoreCursor()



class SongsTableRow:

    def __init__(self, id, number, title):
        self.id = id
        self.number = number
        self.title = title


class SongsTableModel(QtCore.QAbstractTableModel):
    """
    Class for storing table information.
    """

    def __init__(self, owner):
        QtCore.QAbstractTableModel.__init__(self)
        self.session = document_owner(owner)
        self._data = []
        self.header_list = ["Number", "Title"]
        self.updateFromDatabase()

    def updateFromDatabase(self):
        """
        Updates the table model from the latest data in the database.
        """
        self.layoutAboutToBeChanged.emit()

        self._data = []
        if self.session.curs:
            # A songbook is currently open
            for row in self.session.curs.execute(
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
                    return None
                else:
                    return rowobj.number

            elif col == 1:
                return rowobj.title

        return None

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

    def __init__(self, owner):
        self.session = document_owner(owner)
        super().__init__(self.session.win)

    def filterAcceptsRow(self, sourceRow, sourceParent):
        model = self.sourceModel()

        filter_string = self.session.filter_string

        if not filter_string:
            return True

        rowobj = model.getRow(sourceRow)

        # TODO also strip out punctuation (e.g. commas)
        lower_filter_str = filter_string.casefold()
        if lower_filter_str in rowobj.title.casefold():
            return True

        if rowobj.number != -1:
            if lower_filter_str in str(rowobj.number):
                return True

        return False

    def lessThan(self, left, right):
        leftData = self.sourceModel().data(left)
        rightData = self.sourceModel().data(right)
        if leftData is not None and rightData is not None:
            return leftData < rightData
        return False


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

        if marker == "-1" or marker == None or marker == "None":
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
        note_text = self.song._getNoteString(self.note_id, self.character_num)

        chord_type_text = self.app.chord_type_prints[self.chord_type_id]

        # Convert the chord note and type to a text string:
        if self.marker:  # Not NULL
            # Add the chord prefix (example: "1:", "2:")
            chord_str = '%s:%s%s' % (self.marker, note_text, chord_type_text)
        else:
            chord_str = '%s%s' % (note_text, chord_type_text)

        # Add the bass note (if any):
        if self.bass_note_id != -1:  # Not NULL
            bass_note_text = self.song._getNoteString(self.bass_note_id,
                                                      self.character_num)
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

    def __init__(self, owner, song_id):
        self.session = document_owner(owner)
        self.id = song_id
        self._chords = []
        self.number = -1
        self.title = ""
        self.prefer = PREFER_NEITHER
        self._regions = []  # (start_char, prefer, key_label)

        self.updateSongFromDatabase()
        self.updateSharpsOrFlats()

    @property
    def app(self):
        """Owner used by chord text. This is the session, not QApplication."""
        return self.session

    def updateSongFromDatabase(self):
        """
        Read this song from the database, and populate the instnces properties.
        """

        # Read the song from the database. Legacy key_note_id / key_is_major
        # columns are left unread (old songbooks still open).
        try:
            row = self.session.curs.execute(
                "SELECT number, title, subtitle, text FROM songs WHERE id=%i"
                % self.id).fetchone()
        except sqlite3.OperationalError:
            # Old formatted songbook file
            row = self.session.curs.execute(
                "SELECT title, number, text FROM songs WHERE id=%i"
                % self.id).fetchone()
            # Create this prop
            self.session.curs.execute(
                "ALTER TABLE songs ADD subtitle TEXT")
            self.session.curs.commit()
            print("Table songs: added 'subtitle' column")
            # Re-try once the missing columns have been added:
            row = self.session.curs.execute(
                "SELECT number, title, subtitle, text FROM songs WHERE id=%i"
                % self.id).fetchone()

        self.number = row[0]
        self.title = row[1]
        self.subtitle = row[2]
        if self.subtitle == None:
            self.subtitle = ""

        all_text = row[3]

        # Read the chords for this song form the database:
        song_chords = []
        for row in self.session.curs.execute(
                "SELECT id, character_num, note_id, chord_type_id, bass_note_id, marker, in_parentheses FROM song_chord_link WHERE song_id=%i"
                % self.id):
            # id = row[0]
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
        self.doc.setDefaultFont(self.session.lyrics_font)

        self.setAllText(all_text, song_chords)

        self.updateSharpsOrFlats()

    def iterateAllChords(self):
        for chord in self._chords:
            yield chord

    def getChordAtPosition(self, char_num):
        # Go in reverse order to make sure the most recently added or moved chord
        # is given priority:
        for chord in reversed(self._chords):
            if chord.character_num == char_num:
                return chord
        return None

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
        self.session.ignore_song_text_changed = True

        # Determine which chars have chords:
        chords_by_char = {}
        for chord in self._chords:
            chords_by_char[chord.character_num] = True

        chords_height, lyrics_height, line_height = self.session.getHeightsWithChords(
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
                                  self.session.doc_editor_offset)
        root_frame.setFrameFormat(frame_format)

        block = self.doc.begin()

        with_chords_format = block.blockFormat()
        with_chords_format.setTopMargin(with_chords_top_margin)
        with_chords_format.setLeftMargin(self.session.doc_editor_offset)

        without_chords_format = block.blockFormat()
        without_chords_format.setTopMargin(0.0)
        without_chords_format.setLeftMargin(self.session.doc_editor_offset)

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

            block = block.next()

            line_start_char += len(
                line_text) + 1  # Add the eof-of-line character

        self.session.ignore_song_text_changed = False

    def _prefer_for_char(self, char_num):
        prefer = self.prefer
        for start_char, region_prefer, _label in self._regions:
            if char_num >= start_char:
                prefer = region_prefer
            else:
                break
        return prefer

    def _getNoteString(self, note_id, char_num=None):
        """
        Returns the specified note as a string, using sharps vs flats
        as appropriate for the local key region.
        """

        note_text, note_alt_text = self.session.notes_list[note_id]
        if char_num is None:
            prefer = self.prefer
        else:
            prefer = self._prefer_for_char(char_num)

        if prefer == PREFER_SHARPS:
            return note_text
        elif prefer == PREFER_FLATS:
            return note_alt_text
        else:
            if note_id in [1, 6]:
                # C#, F#
                return note_text
            else:
                # Bb, Eb, Ab
                return note_alt_text

    def addChord(self, chord):
        self.session.undo_stack.push(AddChordCommand(self, chord))

    def _addChord(self, chord):
        self._chords.append(chord)
        self.updateSharpsOrFlats()

        # This is important for undo/redo to move the selection:
        self.session.selected_char_num = chord.character_num

        # Update the margin of the document in case the chord was moved to a new line:
        self.setDocMargins()

        self.session.editor.viewport().update()

    def deleteChord(self, chord):
        self.session.undo_stack.push(DeleteChordCommand(self, chord))

    def _deleteChord(self, chord):
        self._chords.remove(chord)
        self.updateSharpsOrFlats()

        # FIXME If the chord is last in line, delete white space on the line, if any was added
        # just to align this chord. Happens often when importing songs from Text.

        # Update the margin of the document in case the chord was moved to a new line:
        self.setDocMargins()

        self.session.editor.viewport().update()

    def replaceChord(self, prev_chord, new_chord):
        command = ReplaceChordCommand(self, prev_chord, new_chord)
        self.session.undo_stack.push(command)

    def _replaceChord(self, prev_chord, new_chord):
        try:
            self._chords.remove(prev_chord)
        except Exception as err:
            print('ERROR: _replaceChord() chord not found:', prev_chord)
            print(err)

        self._chords.append(new_chord)
        self.updateSharpsOrFlats()

        # This is important for undo/redo to move the selection:
        self.session.selected_char_num = new_chord.character_num

        # Update the margin of the document in case the chord was moved to a new line:
        self.setDocMargins()

        self.session.editor.viewport().update()

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
            return self.session.getHeightsWithChords()
        else:
            return self.session.getHeightsWithoutChords()

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

    def getAsText(self, include_chords=True):
        """
        Return a text string for this song. This text will have proper
        formatting only if displayed with a mono-spaced (fixed-width) font
        (important if include_chords is set to True).
        """

        song_text = ''
        self.updateSharpsOrFlats()

        lines = self.getAllText().split("\n")
        for linenum, line_text in enumerate(lines):

            if include_chords and self.getLineHasChords(linenum):
                # Add the chords line above this line

                line_chord_text_list = [' '] * len(line_text)

                # Figure out the lyric letter for the mouse location:
                for line_char_num in range(len(line_text)):
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

                line_chord_text = ''.join(line_chord_text_list).rstrip()
                song_text += line_chord_text + "\n"

            if not include_chords:
                line_text = line_text.rstrip()
            song_text += line_text + "\n"

        # Remove the last end-of-line:
        if song_text[-1] == "\n":
            song_text = song_text[:-1]

        # Fix the line endings that that they work on all OSes, including Windows NotePad:
        song_text = song_text.replace('\n', '\r\n')

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

        self.updateSharpsOrFlats()

    def updateSharpsOrFlats(self):
        """
        Infer key regions from chord structure and the accidental style of each.
        """
        chords = list(self.iterateAllChords())
        chords.sort(key=lambda c: c.character_num)
        starts = detect_region_start_indices(chords)
        self._regions = []
        for k, idx in enumerate(starts):
            end = starts[k + 1] if k + 1 < len(starts) else len(chords)
            group = chords[idx:end]
            detected = best_detected_key(group)
            start_char = group[0].character_num if group else 0
            if detected is None:
                prefer, label = PREFER_NEITHER, ""
            else:
                prefer, label = detected.prefer, detected.label
            self._regions.append((start_char, prefer, label))
        if self._regions:
            self.prefer = self._regions[0][1]
        else:
            self.prefer = PREFER_NEITHER
        if getattr(self.session, "current_song", None) is self:
            updater = getattr(self.session, "_updateAutoDetectedKeyLabel", None)
            if updater:
                updater()

    def removeTrailingSpaces(self):
        """
        Remove trailing spaces from every line of the song.
        """

        original_text = self.getAllText()

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
                if char == " ":
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

        # Renumber surviving chords; drop any that sat on trimmed spaces.
        new_all_chords = []
        updates = []
        for chord in self.iterateAllChords():
            old_char_num = chord.character_num
            try:
                new_char_num = renumber_map[old_char_num]
            except KeyError:
                self.session.curs.execute(
                    "DELETE FROM song_chord_link WHERE song_id=? AND character_num=?",
                    (self.id, old_char_num))
                continue
            if new_char_num != old_char_num:
                updates.append((new_char_num, old_char_num))
            chord.character_num = new_char_num
            new_all_chords.append(chord)

        # Update from right to left so new positions do not collide with
        # chords that have not been moved yet.
        for new_char_num, old_char_num in sorted(updates,
                                                key=lambda item: item[1],
                                                reverse=True):
            self.session.curs.execute(
                "UPDATE song_chord_link SET character_num=? WHERE song_id=? AND character_num=?",
                (new_char_num, self.id, old_char_num))

        self.session.curs.execute("UPDATE songs SET text=? WHERE id=?",
                              (modified_text, self.id))

        self.session.curs.commit()

        self.setAllText(modified_text, new_all_chords)
