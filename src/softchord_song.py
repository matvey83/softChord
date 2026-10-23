"""Song model, table models, and undo commands."""

import copy

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
from softchord_layout import QtDocumentLayout
from softchord_text import format_song_text, place_chord_on_line

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
        self.song.session.updateChordLineSpacing(self.song)

    def redo(self):
        self.song._addChord(self.chord)
        self.song.session.updateChordLineSpacing(self.song)


class DeleteChordCommand(QtGui.QUndoCommand):

    def __init__(self, song, chord):
        QtGui.QUndoCommand.__init__(self)
        self.song = song
        self.chord = chord

    def undo(self):
        self.song._addChord(self.chord)
        self.song.session.updateChordLineSpacing(self.song)

    def redo(self):
        self.song._deleteChord(self.chord)
        self.song.session.updateChordLineSpacing(self.song)


class ReplaceChordCommand(QtGui.QUndoCommand):

    def __init__(self, song, prev_chord, new_chord):
        QtGui.QUndoCommand.__init__(self)
        self.song = song
        self.prev_chord = prev_chord
        self.new_chord = new_chord

    def undo(self):
        self.song._replaceChord(self.new_chord, self.prev_chord)
        self.song.session.updateChordLineSpacing(self.song)

    def redo(self):
        self.song._replaceChord(self.prev_chord, self.new_chord)
        self.song.session.updateChordLineSpacing(self.song)


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
            for song in self.songs:
                song_text = song.getAllText()
                self.session.store.insert_song(song.id, song.number, song.title,
                                               song.subtitle, song_text)

                # Re-add all the chords:
                for chord in song.iterateAllChords():
                    self.session.store.insert_chord(
                        chord.song_id, chord.character_num, chord.note_id,
                        chord.chord_type_id, chord.bass_note_id, chord.marker,
                        chord.in_parentheses)

            self.session.store.commit()

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
                self.session.store.delete_song(song.id)

            self.session.store.commit()

            # Update the song table from database:
            self.session.songs_model.updateFromDatabase()

        finally:
            self.session.restoreCursor()


def text_has_trailing_spaces(text):
    """True when a line ends with a space Remove Trailing Spaces would delete."""
    if not text:
        return False
    return any(line.endswith(" ") for line in text.split("\n"))


class SongTextSnapshot:
    """Lyric text and chords for one song, kept so an edit can be undone."""

    def __init__(self, song_id, text, chords):
        self.song_id = song_id
        self.text = text
        self.chords = chords

    @staticmethod
    def capture(session, song_id):
        record = session.store.load_song(song_id)
        chords = tuple(
            (link.character_num, link.note_id, link.chord_type_id,
             link.bass_note_id, link.marker or "",
             int(link.in_parentheses or 0)) for link in record.chords)
        return SongTextSnapshot(song_id, record.text or "", chords)

    def restore(self, session):
        """Put this text and these chords back into the songbook."""

        def write():
            session.store.update_song_text(self.song_id, self.text)
            for position in session.store.chord_positions(self.song_id):
                session.store.delete_chord(self.song_id, position)
            for (character_num, note_id, chord_type_id, bass_note_id, marker,
                 in_parentheses) in self.chords:
                session.store.insert_chord(self.song_id, character_num,
                                           note_id, chord_type_id,
                                           bass_note_id, marker,
                                           in_parentheses)

        session._run_songbook_write(write)


class TransposeSongCommand(QtGui.QUndoCommand):
    """One transpose of every chord in the song."""

    def __init__(self, song, steps):
        QtGui.QUndoCommand.__init__(self)
        self.setText("transpose")
        self.song = song
        self.steps = steps
        self._notes = [(chord, chord.note_id, chord.bass_note_id)
                       for chord in song.iterateAllChords()]

    def redo(self):
        self.song.transpose(self.steps)
        self._save()

    def undo(self):
        for chord, note_id, bass_note_id in self._notes:
            chord.note_id = note_id
            chord.bass_note_id = bass_note_id
        self.song.updateSharpsOrFlats()
        self._save()

    def _save(self):
        session = self.song.session
        session.setWaitCursor()
        try:
            session.sendCurrentSongToDatabase()
            session.editor.viewport().update()
        finally:
            session.restoreCursor()


class RemoveTrailingSpacesCommand(QtGui.QUndoCommand):
    """Trim trailing spaces on the given songs, as one undo step."""

    def __init__(self, owner, snapshots):
        QtGui.QUndoCommand.__init__(self)
        self.setText("remove trailing spaces")
        self.session = document_owner(owner)
        self.snapshots = list(snapshots)

    def redo(self):
        song_ids = []
        for snapshot in self.snapshots:
            song = Song(self.session, snapshot.song_id)
            song.removeTrailingSpaces()
            song_ids.append(snapshot.song_id)
        self.session._reloadOpenSong(song_ids)

    def undo(self):
        for snapshot in self.snapshots:
            snapshot.restore(self.session)
        self.session._reloadOpenSong(
            [snapshot.song_id for snapshot in self.snapshots])


class RenumberSongsCommand(QtGui.QUndoCommand):
    """Number the songs 1, 2, 3 in their current order."""

    def __init__(self, owner, previous):
        QtGui.QUndoCommand.__init__(self)
        self.setText("renumber songs")
        self.session = document_owner(owner)
        # (song id, number before this command), in songbook order.
        self.previous = list(previous)

    def redo(self):
        numbered = [(song_id, index) for index, (song_id, _number) in enumerate(
            self.previous, start=1)]
        self.session._writeSongNumbers(numbered)

    def undo(self):
        self.session._writeSongNumbers(self.previous)


class ImportSongsCommand(QtGui.QUndoCommand):
    """Songs added by one import or paste. Undo removes just those songs."""

    def __init__(self, owner, song_ids):
        QtGui.QUndoCommand.__init__(self)
        self.setText("import songs")
        self.session = document_owner(owner)
        self.songs = [Song(self.session, song_id) for song_id in song_ids]
        # push() runs redo, and these songs are already in the songbook.
        self._already_imported = True

    def redo(self):
        if self._already_imported:
            self._already_imported = False
            return
        self._insert()
        self.session.songs_model.updateFromDatabase()
        self.session._selectSongId(self.songs[-1].id)

    def undo(self):
        ids = {song.id for song in self.songs}
        current = self.session.current_song
        if current is not None and current.id in ids:
            self.session.ui.songs_view.selectionModel().clearSelection()
        self.session.setWaitCursor()
        try:
            for song in self.songs:
                self.session.store.delete_song(song.id)
            self.session.store.commit()
            self.session.songs_model.updateFromDatabase()
        finally:
            self.session.restoreCursor()

    def _insert(self):
        self.session.setWaitCursor()
        try:
            for song in self.songs:
                self.session.store.insert_song(song.id, song.number, song.title,
                                               song.subtitle, song.getAllText())
                for chord in song.iterateAllChords():
                    self.session.store.insert_chord(
                        chord.song_id, chord.character_num, chord.note_id,
                        chord.chord_type_id, chord.bass_note_id, chord.marker,
                        chord.in_parentheses)
            self.session.store.commit()
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
        if self.session.store.is_open:
            for song_id, number, title in self.session.store.list_song_rows():
                self._data.append(SongsTableRow(song_id, number, title))

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
        """Move this chord up by the given number of half steps.

        steps can be negative. Mirror: softchord_chords.swift transposeNote,
        which SongTranspose.shifted calls for every chord.
        """
        self.note_id = transpose_note(self.note_id, steps)
        if self.bass_note_id != -1:
            self.bass_note_id = transpose_note(self.bass_note_id, steps)

    def getChordText(self):
        """Return this chord as text, for example "Fm" or "Bbsus4".

        Mirror: softchord_chords.swift SoftchordChords.chordText.
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
        self.text = ""
        self.doc = None

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

        # Legacy key_note_id / key_is_major columns are left unread.
        record = self.session.store.load_song(self.id)

        self.number = record.number
        self.title = record.title
        self.subtitle = record.subtitle
        if self.subtitle == None:
            self.subtitle = ""

        song_chords = []
        for link in record.chords:
            song_chords.append(
                SongChord(self, link.character_num, link.note_id,
                          link.chord_type_id, link.bass_note_id, link.marker,
                          link.in_parentheses))

        self.setAllText(record.text, song_chords)

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
        Store the lyric text and chords, and refresh the display document.
        """

        self.text = all_text or ""
        self._chords = all_chords
        QtDocumentLayout.fill(self, self.session)

        self.updateSharpsOrFlats()

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

    def deleteChord(self, chord):
        self.session.undo_stack.push(DeleteChordCommand(self, chord))

    def _deleteChord(self, chord):
        self._chords.remove(chord)
        self.updateSharpsOrFlats()

        # FIXME If the chord is last in line, delete white space on the line, if any was added
        # just to align this chord. Happens often when importing songs from Text.

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

        # A marquee move keeps every selected character selected, including
        # through undo. One chord still follows the single selection.
        nums = getattr(self.session, "selected_chord_nums", None)
        if nums and prev_chord.character_num in nums:
            nums.discard(prev_chord.character_num)
            nums.add(new_chord.character_num)
            self.session.selected_char_num = None
        else:
            self.session.selected_char_num = new_chord.character_num

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
        return self.text

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
        """Return (line number, column) for a character in the song.

        Mirror: softchord_text.swift SongText.lineAndColumn.
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
        """Return this song as clipboard text.

        Chord lines line up in a monospace font. Mirror: softchord_text.swift
        SongText.render.
        """
        self.updateSharpsOrFlats()
        lines = self.getAllText().split("\n")

        def chords_on_line(linenum):
            found = []
            for chord in self.iterateAllChords():
                chord_linenum, anchor = self.songCharToLineChar(
                    chord.character_num)
                if chord_linenum == linenum:
                    found.append((anchor, chord.getChordText()))
            return found

        return format_song_text(
            lines, include_chords, self.getLineHasChords, chords_on_line)

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
        """Move every chord up by the given number of half steps.

        steps can be negative. The new chords are saved with the song.
        Mirror: softchord_chords.swift SongTranspose.shifted, which keeps
        the shifted chords in memory only.
        """
        for chord in self.iterateAllChords():
            chord.transpose(steps)

        self.updateSharpsOrFlats()

    def updateSharpsOrFlats(self):
        """Infer key regions and the accidental style of each.

        Mirror: softchord_text.swift SongText.regions.
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
                self.session.store.delete_chord(self.id, old_char_num)
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
            self.session.store.move_chord(self.id, old_char_num, new_char_num)

        self.session.store.update_song_text(self.id, modified_text)
        self.session.store.commit()

        self.setAllText(modified_text, new_all_chords)
