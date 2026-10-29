"""Song model, table models, and undo commands."""

import copy

from PyQt6 import QtCore, QtGui
from PyQt6.QtCore import Qt

from softchord_chords import (
    PREFER_FLATS,
    PREFER_NEITHER,
    PREFER_SHARPS,
    UNKNOWN_CHORD_TEXT,
    unrecognized_chord_display,
    chord_string,
    classify_suffix,
    key_regions,
    note_text,
    parse_chord,
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
    # Edits one Song object. The session drops these when another song is shown.
    song_scoped = True

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
    # Edits one Song object. The session drops these when another song is shown.
    song_scoped = True

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
    # Edits one Song object. The session drops these when another song is shown.
    song_scoped = True

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
                # The song comes back with its own uuid (and loses its tombstone).
                self.session.store.insert_song(song.id, song.number, song.title,
                                               song.subtitle, song_text,
                                               song.uuid)

                # Re-add all the chords:
                for chord in song.iterateAllChords():
                    self.session.store.insert_chord(
                        chord.song_id, chord.character_num,
                        chord.getStoredText())

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
        chords = tuple((link.character_num, link.chord)
                       for link in record.chords)
        return SongTextSnapshot(song_id, record.text or "", chords)

    def restore(self, session):
        """Put this text and these chords back into the songbook."""

        def write():
            session.store.update_song_text(self.song_id, self.text)
            for position in session.store.chord_positions(self.song_id):
                session.store.delete_chord(self.song_id, position)
            for character_num, chord in self.chords:
                session.store.insert_chord(self.song_id, character_num, chord)

        session._run_songbook_write(write)


class TransposeSongCommand(QtGui.QUndoCommand):
    """One transpose of every chord in the song."""
    # Edits one Song object. The session drops these when another song is shown.
    song_scoped = True

    def __init__(self, song, steps, text="transpose"):
        QtGui.QUndoCommand.__init__(self)
        self.setText(text)
        self.song = song
        self.steps = steps
        self._counted = True
        self._notes = [(chord, chord.note_id, chord.bass_note_id,
                        chord._root_text, chord._bass_text)
                       for chord in song.iterateAllChords()]

    def redo(self):
        self._counted = self.song.transpose(self.steps)
        self._save()

    def undo(self):
        for chord, note_id, bass_note_id, root_text, bass_text in self._notes:
            chord.note_id = note_id
            chord.bass_note_id = bass_note_id
            chord._root_text = root_text
            chord._bass_text = bass_text
        self.song.updateSharpsOrFlats()
        # The notes are back as they were, so the count of steps since the song
        # was loaded goes back too. (Song.transpose adds the steps on redo,
        # unless the song had only unrecognized chords.)
        if self._counted:
            self.song.add_transposed_steps(-self.steps)
        self._save()

    def _save(self):
        session = self.song.session
        session.setWaitCursor()
        try:
            session.sendCurrentSongToDatabase()
            session.editor.viewport().update()
        finally:
            session.restoreCursor()
        # Reset is on only while the song is away from the key it was loaded in.
        session.updateTransposeResetButton()


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
                                               song.subtitle, song.getAllText(),
                                               song.uuid)
                for chord in song.iterateAllChords():
                    self.session.store.insert_chord(
                        chord.song_id, chord.character_num,
                        chord.getStoredText())
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

    The songbook stores one string per chord (docs/chord_format.md).
    note_id, chord_type_id and bass_note_id are the parsed fields.

    A chord whose suffix is not a known type (for example "maj9") keeps that
    text in the suffix, so it is written back unchanged. chord_type_id is then
    only its base quality (0 major, 1 minor). Setting chord_type_id replaces
    the suffix with the type's own text.

    An unknown (unrecognized) chord has no root. It is drawn in red as its first
    7 characters, and written back as raw.

    Setting note_id or bass_note_id drops the spelling read from the file, and
    the song's key picks sharps or flats again.

    Mirror: softchord_chords.swift SongChord.
    """

    def __init__(self, song, character_num, note_id, chord_type_id,
                 bass_note_id, marker, in_parentheses, suffix=None,
                 root_text=None, bass_text=None):
        self.app = song.app
        self.song = song
        self.song_id = song.id
        self.character_num = character_num
        self.unknown = False
        self.raw = UNKNOWN_CHORD_TEXT
        self._suffix = suffix
        self._root_text = root_text
        self._bass_text = bass_text
        self._note_id = note_id
        self._chord_type_id = chord_type_id
        self._bass_note_id = bass_note_id

        if marker == "-1" or marker == None or marker == "None":
            # FIXME the database should have only one of these in it
            marker = ""
        self.marker = marker

        if in_parentheses == None:
            in_parentheses = 0
        self.in_parentheses = in_parentheses

    @classmethod
    def unknown_chord(cls, song, character_num, raw=UNKNOWN_CHORD_TEXT):
        """A chord with no usable root. raw is written back unchanged."""
        chord = cls(song, character_num, -1, 0, -1, "", 0)
        chord.set_unknown(raw)
        return chord

    @classmethod
    def from_text(cls, song, character_num, text):
        """Read a chord string with the tolerant parser. Never raises."""
        parsed = parse_chord(text)
        if parsed.unknown:
            return cls.unknown_chord(song, character_num, parsed.raw)
        return cls(song, character_num, parsed.note_id, parsed.chord_type_id,
                   parsed.bass_note_id, parsed.marker, parsed.in_parentheses,
                   suffix=None if parsed.is_known_type else parsed.suffix,
                   root_text=parsed.root_text,
                   bass_text=parsed.bass_text or None)

    def set_unknown(self, raw):
        """Make this an unknown chord that is written back as raw."""
        raw = (raw or "").strip()
        self.unknown = True
        self.raw = raw if raw else UNKNOWN_CHORD_TEXT
        self._note_id = -1
        self._chord_type_id = 0
        self._bass_note_id = -1
        self._suffix = None
        self._root_text = None
        self._bass_text = None
        self.marker = ""
        self.in_parentheses = 0

    @property
    def note_id(self):
        return self._note_id

    @note_id.setter
    def note_id(self, value):
        self._note_id = value
        self._root_text = None
        if value is not None and value >= 0:
            self.unknown = False

    @property
    def chord_type_id(self):
        return self._chord_type_id

    @chord_type_id.setter
    def chord_type_id(self, value):
        self._chord_type_id = value
        self._suffix = None

    @property
    def bass_note_id(self):
        return self._bass_note_id

    @bass_note_id.setter
    def bass_note_id(self, value):
        self._bass_note_id = value
        self._bass_text = None

    @property
    def suffix(self):
        """Text after the root: the type's own text, or the kept original."""
        if self._suffix is not None:
            return self._suffix
        return self.app.chord_type_prints[self._chord_type_id]

    @suffix.setter
    def suffix(self, value):
        """Set the suffix text. A known type text selects that type."""
        type_id, known = classify_suffix(value)
        self._chord_type_id = type_id
        self._suffix = None if known else value

    def transpose(self, steps):
        """Move this chord up by the given number of half steps.

        steps can be negative. Only the root and bass change. The suffix is
        kept as it is. Mirror: softchord_chords.swift transposeNote, which
        SongTranspose.shifted calls for every chord.
        """
        if self.unknown:
            return
        self.note_id = transpose_note(self.note_id, steps)
        if self.bass_note_id != -1:
            self.bass_note_id = transpose_note(self.bass_note_id, steps)

    def getChordText(self):
        """Return this chord as text, for example "Fm" or "Bbsus4".

        An unrecognized chord is its first 7 characters (or "?" when empty).
        Mirror: softchord_chords.swift SoftchordChords.chordText.
        """
        if self.unknown:
            return unrecognized_chord_display(self.raw)

        note_str = self._root_text or self.song._getNoteString(
            self.note_id, self.character_num)

        bass_str = ""
        if self.bass_note_id != -1:  # Not NULL
            bass_str = self._bass_text or self.song._getNoteString(
                self.bass_note_id, self.character_num)

        return chord_string(self.marker, note_str, self.suffix, bass_str,
                            self.in_parentheses)

    def getStoredText(self):
        """The string written to the songbook for this chord."""
        if self.unknown:
            return self.raw
        return self.getChordText()


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
        self.uuid = None  # set from the songbook; never changes
        self._chords = []
        self.number = -1
        self.title = ""
        self.prefer = PREFER_NEITHER
        self._regions = []  # (start_char, prefer, key_label)
        self.text = ""
        self.doc = None
        # Half steps this song has been transposed by since this Song was loaded
        # from the songbook (what Reset transpose undoes), folded into -5..6.
        # Up then Down is 0 again, and so is a whole octave (12 steps), which gives
        # the same chords. Chord edits do not change it, so a chord typed after
        # transposing is moved back with the rest. Reloading the text from the
        # songbook keeps it, because the stored chords are still the transposed ones.
        self.transposed_steps = 0

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

        record = self.session.store.load_song(self.id)

        self.uuid = record.uuid
        self.number = record.number
        self.title = record.title
        self.subtitle = record.subtitle
        if self.subtitle == None:
            self.subtitle = ""

        # A songbook can hold the same chord twice on one letter (older imports
        # did). The song keeps one of them, in memory only: the file is not
        # rewritten until the song is. Different chords on a letter both stay.
        song_chords = []
        seen = set()
        for link in record.chords:
            if (link.character_num, link.chord) in seen:
                continue
            seen.add((link.character_num, link.chord))
            song_chords.append(
                SongChord.from_text(self, link.character_num, link.chord))

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

        if char_num is None:
            prefer = self.prefer
        else:
            prefer = self._prefer_for_char(char_num)

        return note_text(note_id, prefer)

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
            found = self.letterLineAndColumn(chord.character_num)
            if found is not None and found[0] == linenum:
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

    def letterLineAndColumn(self, song_char_num):
        """Like songCharToLineChar, but None when there is no letter there.

        A chord can be stored on a line break or past the end of the text.
        It has no letter to sit on, so it is not drawn or copied, and it
        must not stop the rest of the song from being shown.
        """
        try:
            return self.songCharToLineChar(song_char_num)
        except RuntimeError:
            return None

    def chordsOnLetters(self):
        """The chords that have a letter to sit on, in their order.

        A chord on a line break, past the end of the text, or below zero has
        no letter (letterLineAndColumn is None for it). Painting, the line
        spacing and Copy text leave such a chord out, so they all agree.
        The text is split once, not once per chord.
        """
        text = self.getAllText()
        return [chord for chord in self._chords
                if 0 <= chord.character_num < len(text)
                and text[chord.character_num] != "\n"]

    def songCharToLineChar(self, song_char_num):
        """Return (line number, column) for a letter in the song.

        Raises RuntimeError for a line break, a negative number, and a
        number past the end of the text.

        Mirror: softchord_text.swift SongText.lineAndColumn.
        """

        if song_char_num < 0:
            raise RuntimeError()

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
            if song_char_num == line_global_end - 1:
                # The line break at the end of this line has no letter.
                raise RuntimeError()
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
                where = self.letterLineAndColumn(chord.character_num)
                if where is not None and where[0] == linenum:
                    found.append((where[1], chord.getChordText()))
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
            # An unknown chord keeps its own text (for example "N.C.").
            chord_text = chord.getStoredText()

            # Replace "♯" with "#" and "♭" with "b":
            chord_text = chord_text.replace("♯", "#").replace("♭", "b")

            chord_texts_by_char_nums[chord_song_char_num] = chord_text

        for curr_char_num, char in enumerate(all_text):
            if curr_char_num in chord_texts_by_char_nums:
                converted_text += "[%s]" % chord_texts_by_char_nums[
                    curr_char_num]
            converted_text += char

        return converted_text

    def add_transposed_steps(self, steps):
        """Count a transpose (or an undone one), folded so 12 steps is 0."""
        folded = (self.transposed_steps + steps) % 12
        self.transposed_steps = folded - 12 if folded > 6 else folded

    def transpose(self, steps):
        """Move every chord up by the given number of half steps.

        steps can be negative. The new chords are saved with the song.
        Mirror: softchord_chords.swift SongTranspose.shifted, which keeps
        the shifted chords in memory only.
        """
        counted = self.has_transposable_chords()
        for chord in self.iterateAllChords():
            chord.transpose(steps)

        # Unrecognized chords do not move, so a song of only those has not
        # changed key and Reset has nothing to undo.
        if counted:
            self.add_transposed_steps(steps)
        self.updateSharpsOrFlats()
        return counted

    def has_transposable_chords(self):
        """True when at least one chord has a root, so transposing changes it."""
        return any(not chord.unknown for chord in self.iterateAllChords())

    def updateSharpsOrFlats(self):
        """Infer key regions and the accidental style of each.

        Mirror: softchord_text.swift SongText.regions.
        """
        # An unknown chord has no root, so it says nothing about the key.
        chords = [c for c in self.iterateAllChords() if not c.unknown]
        self._regions = key_regions(chords)
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
