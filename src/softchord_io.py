"""Songbook files and song import/export."""

import os
import shutil
import sqlite3
import traceback

from PyQt6 import QtCore, QtWidgets

from softchord_chords import convert_chord_from_string, replace_russian_characeters
from softchord_song import Song

# File extensions that can be used for the ChordPro file format:
chordpro_extensions = [".pro", ".chopro", ".chordpro", ".cpm"]

SQLITE_HEADER = b"SQLite format 3\x00"

# New songbooks do not store a user-selected key; old files may still have
# key_note_id / key_is_major columns, which are ignored.
SONGS_TABLE_SQL = (
    "CREATE TABLE songs (id INTEGER PRIMARY KEY, number INTEGER, text TEXT, "
    "title TEXT, subtitle TEXT)"
)
SONG_CHORD_LINK_TABLE_SQL = (
    "CREATE TABLE song_chord_link(id INTEGER PRIMARY KEY, song_id INTEGER, "
    "character_num INTEGER, note_id INTEGER, chord_type_id INTEGER, "
    "bass_note_id INTEGER, marker TEXT, in_parentheses INTEGER)"
)


def _normalize_local_path(path):
    """Turn a file: URL from macOS/Qt into a filesystem path."""
    if not path:
        return path
    path = str(path)
    if path.startswith("file:"):
        local = QtCore.QUrl(path).toLocalFile()
        if local:
            return local
    return path


def read_import_text_file(filename):
    """Read a lyrics/ChordPro file as Unicode.

    Prefer UTF-8 (with optional BOM). Fall back to common 8-bit encodings so
    files saved on Windows in a local code page still import. Latin-1 is last
    because it never fails.
    """
    with open(filename, "rb") as fh:
        raw = fh.read()
    for encoding in ("utf-8-sig", "cp1250", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def connect_existing_songbook(filename):
    """Open an existing songbook. Never create a new/empty database."""
    filename = os.path.abspath(_normalize_local_path(filename))
    if not os.path.isfile(filename):
        raise FileNotFoundError("Songbook file not found:\n%s" % filename)
    if os.path.getsize(filename) == 0:
        raise ValueError(
            "This file is empty and is not a valid songbook:\n%s" % filename)

    with open(filename, "rb") as fh:
        header = fh.read(16)
    if header != SQLITE_HEADER:
        raise ValueError(
            "This file is not a valid softChord songbook:\n%s" % filename)

    conn = sqlite3.connect(filename)
    try:
        tables = [
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")
        ]
    except Exception:
        conn.close()
        raise
    if "songs" not in tables:
        conn.close()
        raise ValueError(
            "This file is not a valid softChord songbook (missing songs table):\n%s"
            % filename)
    return conn


def _chord_tokens(line):
    """Words on a chord line, with glued chord names split apart.

    Returns (text, start, end) with end inclusive. Text has look-alike
    Cyrillic letters normalized the same way as chord parsing.
    """
    words = []
    current_word = ""
    current_word_start = None
    for i, char in enumerate(line):
        if not current_word:
            if char.isspace():
                continue
            current_word = char
            current_word_start = i
        elif not char.isspace():
            current_word += char
        else:
            words.append((current_word, current_word_start, i - 1))
            current_word = ""
            current_word_start = None
    if current_word:
        words.append((current_word, current_word_start, len(line) - 1))

    notes = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
    tokens = []
    for word, word_start, word_end in words:
        word = replace_russian_characeters(word)
        num_notes = 0
        for char in word:
            if char in notes:
                num_notes += 1
            elif char == '/':
                num_notes -= 1
        if num_notes <= 1:
            tokens.append((word, word_start, word_end))
            continue
        # "AmC" and similar were typed without a separating space.
        chord_starts = [word_start]
        char_pos = word_start
        for char in word[1:]:
            char_pos += 1
            if char in notes:
                chord_starts.append(char_pos)
        for i, chord_start in enumerate(chord_starts):
            try:
                chord_end = chord_starts[i + 1] - 1
            except IndexError:
                chord_end = word_end
            chord_text = word[chord_start - word_start:chord_end - word_start +
                              1]
            tokens.append((chord_text, chord_start, chord_end))
    return tokens


def _classify_chord_line(line, convert_chord):
    """Return (is_chord_line, entries, warnings).

    entries are (text, start, end, converted_chord) for tokens that parse
    as chords. A line is a chord line when more tokens are chords than not.
    """
    num_chords = 0
    num_non_chords = 0
    entries = []
    warnings = []
    for word, start, end in _chord_tokens(line):
        if word == '/':
            num_chords += 1
            continue
        try:
            converted = convert_chord(word)
        except ValueError as err:
            warnings.append('  WARNING: %s; chord: "%s"' % (err, word))
            num_non_chords += 1
        else:
            num_chords += 1
            entries.append((word, start, end, converted))
    return (num_chords > num_non_chords), entries, warnings


def _median(values):
    values = sorted(values)
    mid = len(values) // 2
    if len(values) % 2:
        return values[mid]
    return (values[mid - 1] + values[mid]) / 2.0


def text_is_proportionally_spaced(pairs, metrics):
    """Whether chord lines were aligned visually in a proportional font.

    Monospaced sheets use about one column per lyric character, so the
    chord line is not much longer than the lyric. Proportionally spaced
    sheets insert extra spaces (spaces are narrower than letters) and the
    two lines end up a similar width in the lyrics font.
    pairs are (chord_line, lyric_line).
    """
    length_ratios = []
    width_ratios = []
    for chord_line, lyric_line in pairs:
        chord = chord_line.rstrip()
        lyric = lyric_line.rstrip()
        if not chord or not lyric:
            continue
        lyric_width = metrics.horizontalAdvance(lyric)
        if lyric_width <= 0:
            continue
        length_ratios.append(len(chord) / float(len(lyric)))
        width_ratios.append(metrics.horizontalAdvance(chord) / lyric_width)
    if not length_ratios:
        return False
    return (_median(length_ratios) > 1.2 and
            0.8 <= _median(width_ratios) <= 1.2)


def _char_x_center(text, index, metrics):
    left = metrics.horizontalAdvance(text[:index])
    right = metrics.horizontalAdvance(text[:index + 1])
    return (left + right) / 2.0


def _nearest_nonspace(text, index):
    indices = [i for i, char in enumerate(text) if not char.isspace()]
    if not indices:
        return None
    if index < 0:
        index = 0
    elif index >= len(text):
        index = len(text) - 1
    # Equal distance prefers the character to the right.
    return min(indices, key=lambda i: (abs(i - index), 0 if i >= index else 1))


def _next_free_nonspace(text, index, used):
    indices = [
        i for i, char in enumerate(text)
        if not char.isspace() and i not in used
    ]
    right = [i for i in indices if i > index]
    if right:
        return min(right)
    left = [i for i in indices if i < index]
    if left:
        return max(left)
    return None


def assign_chord_anchors(chord_line, lyric_line, tokens, metrics,
                         proportional):
    """Map chord tokens onto lyric character indexes.

    tokens are (start, end, payload) with end inclusive. In a proportional
    sheet the anchor is the visual center of the chord name. In a monospaced
    sheet it is the first letter. Indexes always fall on a non-space
    character, and two chords never share one. The lyric is not extended.
    """
    nonspace = [i for i, char in enumerate(lyric_line) if not char.isspace()]
    if not nonspace:
        return []
    if proportional:
        centers = [
            _char_x_center(lyric_line, i, metrics) for i in range(len(lyric_line))
        ]
    used = set()
    placed = []
    for start, end, payload in tokens:
        if proportional:
            left = metrics.horizontalAdvance(chord_line[:start])
            right = metrics.horizontalAdvance(chord_line[:end + 1])
            center = (left + right) / 2.0
            index = min(nonspace, key=lambda i: (abs(centers[i] - center), -i))
        else:
            index = _nearest_nonspace(lyric_line, start)
        if index in used:
            index = _next_free_nonspace(lyric_line, index, used)
        if index is None:
            continue
        used.add(index)
        placed.append((index, payload))
    return placed


def parse_chord_over_lyrics(lines, convert_chord, metrics):
    """Pair chord lines with the lyric line under them and place the chords.

    Returns (song_lines, proportional). song_lines items are
    (lyric_text, {character_index: converted_chord}). Lyric text is the
    source line, without spaces added to make room for a chord.
    """
    pending_line = None
    pending_entries = None
    raw_pairs = []
    for line in lines:
        is_chord, entries, warnings = _classify_chord_line(line, convert_chord)
        if is_chord:
            for warning in warnings:
                print(warning)
            pending_line = line
            pending_entries = entries
        else:
            if pending_entries:
                raw_pairs.append((pending_line, line.rstrip(), pending_entries))
            else:
                raw_pairs.append((None, line, []))
            pending_line = None
            pending_entries = None

    # A chord line at the end of the file has no lyrics under it.
    # Keep it as its own line so the chords are not dropped.
    if pending_entries:
        raw_pairs.append(
            (pending_line, pending_line.rstrip(), pending_entries))
    elif pending_line is not None:
        raw_pairs.append((None, pending_line, []))

    proportional = text_is_proportionally_spaced(
        [(chord_line, lyric) for chord_line, lyric, entries in raw_pairs
         if entries], metrics)

    song_lines = []
    for chord_line, lyric, entries in raw_pairs:
        if not entries:
            song_lines.append((lyric, {}))
            continue
        tokens = [(start, end, converted)
                  for _text, start, end, converted in entries]
        placed = assign_chord_anchors(chord_line, lyric, tokens, metrics,
                                      proportional)
        song_lines.append((lyric, {index: chord for index, chord in placed}))
    return song_lines, proportional


class SongbookIO:
    """Mixin: songbook open/save and song import/export."""

    def exportToText(self, text_file=None):
        """
        Exports the selected song (one) to a TEXT file.
        """

        self.sendCurrentSongToDatabase()

        self.setWaitCursor(
        )  # For some reason, without this line, the selection is not updated yet when running softchord_test.py
        try:
            if not self.getSelectedSongIds():
                self.error("No songs are selected")
                return
            elif len(self.getSelectedSongIds()) > 1:
                self.error("More than one song is selected.")
                return
        finally:
            self.restoreCursor()

        if not text_file:
            suggested_path = os.path.join(QtCore.QDir.home().path(),
                                          self.current_song.title + ".txt")

            text_file, _ = QtWidgets.QFileDialog.getSaveFileName(
                self.win,
                "Save text file as:",
                suggested_path,
                "Text format (*.txt)",
            )
        if text_file:
            self.setWaitCursor()
            try:
                with open(text_file, 'w', encoding='utf-8-sig') as fh:
                    for song_id in self.getSelectedSongIds():
                        # NOTE for now there will always be only one song exported.
                        song = Song(self, song_id)
                        song_text = song.getAsText()
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
        try:
            if not self.getSelectedSongIds():
                self.error("No songs are selected")
                return
            elif len(self.getSelectedSongIds()) > 1:
                self.error("More than one song is selected.")
                return
        finally:
            self.restoreCursor()

        if not filename:
            suggested_path = os.path.join(QtCore.QDir.home().path(),
                                          self.current_song.title + ".chordpro")

            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                self.win,
                "Save text file as:",
                suggested_path,
                "ChordPro format (*.chordpro)",
            )
        if filename:
            self.setWaitCursor()
            try:
                with open(filename, 'w', encoding='utf-8-sig') as fh:
                    for song_id in self.getSelectedSongIds():
                        # NOTE for now there will always be only one song exported.
                        song = Song(self, song_id)

                        song_text = song.getAsChordProText()

                        # Fix the line endings that that they work on all OSes, including Windows NotePad:
                        song_text = song_text.replace('\n', '\r\n')

                        fh.write(song_text)
            finally:
                self.restoreCursor()

    def importFromChordPro(self, filename=None):
        """
        Lets the user select a ChordPro file to import.
        """
        if not filename:
            filter_string = "ChordPro format (%s)" % ' '.join(
                ['*' + ext for ext in chordpro_extensions])
            chordpro_files, _ = QtWidgets.QFileDialog.getOpenFileNames(
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
                    try:
                        file_text = read_import_text_file(filename)
                        self.importSongFromChordProText(file_text)
                    except Exception:
                        self.error("Error importing %s:\n\n%s" %
                                   (filename, traceback.format_exc()))
                        break
            finally:
                self.restoreCursor()

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
        except sqlite3.OperationalError as err:
            self.restoreCursor()
            if "readonly" in str(err).lower():
                self.error(
                    "Cannot paste as a new song because this songbook is read-only.\n\n"
                    "Use File → Save Songbook As... to save a writable copy, then paste again."
                )
            else:
                self.error("Error parsing the text:\n\n%s " %
                           traceback.format_exc())
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
        text_files, _ = QtWidgets.QFileDialog.getOpenFileNames(
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
                try:
                    text = read_import_text_file(filename)
                    self.importSongFromText(text, song_title)
                except Exception:
                    self.error("Error importing %s:\n\n%s" %
                               (filename, traceback.format_exc()))
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

        song_lines, _proportional = parse_chord_over_lyrics(
            song_text, self.convertChordFromString, self.lyrics_font_metrics)

        # If the title is not specified, set it to the first line of lyrics:
        if song_title == None and song_lines:
            # Also remove leading and trailing spaces:
            song_title = song_lines[0][0].strip()
            # Strip "1." (if present):
            for find_str in [
                    "1", "Припев", "Пр.", "Chorus", "Куплет", ".", ":", ")"
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

    def _importSong(self, song_num, song_title, song_subtitle, song_text):
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
            "INSERT INTO songs (id, number, title, subtitle, text) VALUES (?, ?, ?, ?, ?)",
            (song_id, song_num, song_title, song_subtitle, song_text))

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

        song_id = self._importSong(song_num, song_title, song_subtitle,
                                   song_text)

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
                                        (str(err), chord_text))
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

        self._importSongFromLyricsAndChords(song_num, song_title, song_subtitle,
                                            global_song_text,
                                            global_song_chords)

    def convertChordFromString(self, chord_str):
        """
        Convert the specified chord string to a note_id, chord_type_id, and a bass_note_id.
        """
        return convert_chord_from_string(chord_str, self.note_text_id_dict,
                                         self.chord_type_texts_dict)

    def setCurrentSongbook(self, filename, conn=None):
        if filename is not None:
            filename = _normalize_local_path(filename)
            if conn is None:
                conn = connect_existing_songbook(filename)
        else:
            conn = None

        self.ui.songs_view.selectionModel().clearSelection()
        # Send the current song to database:
        self.setCurrentSong(None)

        # Nothing to undo; new database
        self.clearUndoStack()

        previous_curs = self.curs
        self.curs = conn
        self.current_songbook_filename = filename
        if filename is None:
            self.win.setWindowTitle("softChord")
        else:
            songbook_name = os.path.splitext(os.path.basename(filename))[0]
            self.win.setWindowTitle("softChord - %s" % songbook_name)

        self.songs_model.updateFromDatabase()
        self.updateStates()
        if previous_curs is not None and previous_curs is not self.curs:
            try:
                previous_curs.close()
            except Exception:
                pass

    def appendSongbookFile(self, filename):
        """
        Append the given songbook to the currently open songbook.
        """

        self.setWaitCursor()
        try:
            # This step can't be undoed:
            self.clearUndoStack()

            self.ui.songs_view.selectionModel().clearSelection()

            curs2 = connect_existing_songbook(filename)

            chord_id = None  # So that _importChord() assigned a new ID to the new chord

            # Materialize the source songs first: nested executes on the same
            # sqlite3 cursor reset the outer iterator.
            source_songs = list(
                curs2.execute(
                    "SELECT id, number, title, subtitle, text FROM songs ORDER BY id"
                ))
            for (src_song_id, song_num, song_title, song_subtitle,
                 song_text) in source_songs:
                dest_song_id = self._importSong(song_num, song_title,
                                                song_subtitle, song_text)

                source_chords = list(
                    curs2.execute(
                        "SELECT character_num, note_id, chord_type_id, "
                        "bass_note_id, marker, in_parentheses "
                        "FROM song_chord_link WHERE song_id=?",
                        (src_song_id,)))
                for (song_char_num, note_id, chord_type_id, bass_note_id,
                     marker, in_parentheses) in source_chords:
                    chord_id = self._importChord(dest_song_id, song_char_num,
                                                 note_id, chord_type_id,
                                                 bass_note_id, marker,
                                                 in_parentheses, chord_id)
                    chord_id += 1  # Increment the ID for the next chord.

            self.curs.commit()

            self.songs_model.updateFromDatabase()
            self.updateStates()
        finally:
            self.restoreCursor()
            try:
                curs2.close()
            except Exception:
                pass

    def newSongbook(self):
        songbook_file, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.win,
            "Save songbook as:",
            QtCore.QDir.home().path(),  # initial dir
            "Songbook format (*.songbook)",
        )
        if songbook_file:
            # Overwrite a previous songbook (if any):
            if os.path.isfile(songbook_file):
                os.remove(songbook_file)

            # Open an empty database once, then reuse that connection.
            conn = sqlite3.connect(songbook_file)
            conn.execute(SONG_CHORD_LINK_TABLE_SQL)
            conn.execute(SONGS_TABLE_SQL)
            conn.commit()
            self.setCurrentSongbook(songbook_file, conn=conn)

    def openSongbook(self):
        initial_dir = QtCore.QDir.home().path()
        songbook_file, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.win,
            "Select a songbook to open",
            initial_dir,
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
            new_songbook_file, _ = QtWidgets.QFileDialog.getSaveFileName(
                self.win,
                "Save songbook as:",
                suggested_path,
                "Songbook format (*.songbook)",
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
                    "Could not save the songbook to a new location.\n\nException: %s"
                    % err)
                return

            self.setCurrentSongbook(new_songbook_file)

    def appendSongbookSelected(self):
        """
        Append a user-selected songbook to the currently opened songbook.
        """

        songbook_file, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.win,
            "Select a songbook to append",
            QtCore.QDir.home().path(),  # initial dir
            "Songbook format (*.songbook)",
        )
        if songbook_file:
            self.appendSongbookFile(songbook_file)

