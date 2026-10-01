"""SQLite songbook: open, migrate, load, and save songs and chord links.

Song, undo, and import talk to this store. They do not run SQL themselves.
"""

import sqlite3


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


def readonly_database_error(err):
    """SQLite refused a write because this connection cannot modify the file."""
    return (isinstance(err, sqlite3.OperationalError)
            and "readonly" in str(err).lower())


def database_file_was_replaced(err):
    """The open connection's file was moved or replaced, so it can no longer write."""
    return getattr(err, "sqlite_errorname", None) == "SQLITE_READONLY_DBMOVED"


class ChordLink:
    """One chord row, without the database id."""

    def __init__(self, character_num, note_id, chord_type_id, bass_note_id,
                 marker, in_parentheses):
        self.character_num = character_num
        self.note_id = note_id
        self.chord_type_id = chord_type_id
        self.bass_note_id = bass_note_id
        self.marker = marker
        self.in_parentheses = in_parentheses


class SongRecord:
    """Song columns and chord links loaded from the songbook."""

    def __init__(self, number, title, subtitle, text, chords):
        self.number = number
        self.title = title
        self.subtitle = subtitle
        self.text = text
        self.chords = chords


class SongbookStore:
    """The open songbook connection and the queries that use it."""

    def __init__(self, connection=None):
        self.connection = connection
        self.path = None
        self._connect = None

    @property
    def is_open(self):
        return self.connection is not None

    def use(self, connection):
        """Adopt an already-open connection, or None when the songbook closes."""
        self.connection = connection

    def _conn(self):
        if self.connection is None:
            raise RuntimeError("No songbook is open")
        return self.connection

    def reopen(self):
        """Open the same path again.

        SQLite keeps the original file handle. If that file is replaced, later
        writes fail with "readonly" even though the file now on disk is writable.
        """
        if not self.path or self._connect is None:
            return False
        try:
            conn = self._connect(self.path)
        except (OSError, ValueError, sqlite3.Error):
            return False
        previous = self.connection
        self.connection = conn
        if previous is not None and previous is not conn:
            try:
                previous.rollback()
            except sqlite3.Error:
                pass
            try:
                previous.close()
            except sqlite3.Error:
                pass
        return True

    def _execute(self, sql, params=()):
        try:
            return self._conn().execute(sql, params)
        except sqlite3.OperationalError as err:
            if not database_file_was_replaced(err) or not self.reopen():
                raise
            return self._conn().execute(sql, params)

    def commit(self):
        self._conn().commit()

    @staticmethod
    def create_file(path):
        """Create an empty songbook file and return its connection.

        Does not replace the store's current connection. The caller adopts
        the returned connection after closing the previous songbook.
        """
        conn = sqlite3.connect(path)
        conn.execute(SONG_CHORD_LINK_TABLE_SQL)
        conn.execute(SONGS_TABLE_SQL)
        conn.commit()
        return conn

    def list_song_rows(self):
        """(id, number, title) in id order. Empty when no songbook is open."""
        if not self.is_open:
            return []
        return list(
            self.connection.execute(
                "SELECT id, number, title FROM songs ORDER BY id"))

    def load_song(self, song_id):
        """Load one song. Add a missing subtitle column on old songbooks."""
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT number, title, subtitle, text FROM songs WHERE id=%i" %
                song_id).fetchone()
        except sqlite3.OperationalError:
            # Old formatted songbook file
            row = conn.execute(
                "SELECT title, number, text FROM songs WHERE id=%i" %
                song_id).fetchone()
            self._execute("ALTER TABLE songs ADD subtitle TEXT")
            self.commit()
            print("Table songs: added 'subtitle' column")
            row = conn.execute(
                "SELECT number, title, subtitle, text FROM songs WHERE id=%i" %
                song_id).fetchone()

        chords = []
        for chord_row in conn.execute(
                "SELECT id, character_num, note_id, chord_type_id, "
                "bass_note_id, marker, in_parentheses FROM song_chord_link "
                "WHERE song_id=%i" % song_id):
            chords.append(
                ChordLink(chord_row[1], chord_row[2], chord_row[3],
                          chord_row[4], chord_row[5], chord_row[6]))
        return SongRecord(row[0], row[1], row[2], row[3], chords)

    def next_song_id(self):
        """Next song id. The first song in an empty songbook is 0."""
        row = self._conn().execute("SELECT MAX(id) from songs").fetchone()
        if row[0] is None:
            return 0
        return row[0] + 1

    def insert_song(self, song_id, number, title, subtitle, text):
        self._execute(
            "INSERT INTO songs (id, number, title, subtitle, text) "
            "VALUES (?, ?, ?, ?, ?)",
            (song_id, number, title, subtitle, text))

    def update_song_title(self, song_id, title):
        self._execute("UPDATE songs SET title=? WHERE id=?",
                             (title, song_id))

    def update_song_subtitle(self, song_id, subtitle):
        self._execute("UPDATE songs SET subtitle=? WHERE id=?",
                             (subtitle, song_id))

    def update_song_number(self, song_id, number):
        self._execute("UPDATE songs SET number=? WHERE id=?",
                             (number, song_id))

    def update_song_text(self, song_id, text):
        self._execute("UPDATE songs SET text=? WHERE id=?",
                             (text, song_id))

    def update_song(self, song_id, number, title, subtitle, text):
        self._execute(
            "UPDATE songs SET number=?, title=?, subtitle=?, text=? WHERE id=?",
            (number, title, subtitle, text, song_id))

    def delete_song(self, song_id):
        self._execute("DELETE FROM songs WHERE id=%i" % song_id)
        self._execute("DELETE FROM song_chord_link WHERE song_id=%i" % song_id)

    def next_chord_id(self):
        """Next chord-link id. The first chord in an empty songbook is 0."""
        row = self._conn().execute(
            "SELECT MAX(id) from song_chord_link").fetchone()
        if row[0] is None:
            return 0
        return row[0] + 1

    def insert_chord(self,
                     song_id,
                     character_num,
                     note_id,
                     chord_type_id,
                     bass_note_id,
                     marker,
                     in_parentheses,
                     chord_id=None):
        """Insert a chord link. Omit chord_id to let SQLite assign the row id."""
        if chord_id is None:
            self._execute(
                "INSERT INTO song_chord_link (song_id, character_num, note_id, "
                "chord_type_id, bass_note_id, marker, in_parentheses) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (song_id, character_num, note_id, chord_type_id, bass_note_id,
                 marker, in_parentheses))
            return None
        self._execute(
            "INSERT INTO song_chord_link (id, song_id, character_num, note_id, "
            "chord_type_id, bass_note_id, marker, in_parentheses) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (chord_id, song_id, character_num, note_id, chord_type_id,
             bass_note_id, marker, in_parentheses))
        return chord_id

    def chord_positions(self, song_id):
        return [
            row[0] for row in self._conn().execute(
                "SELECT character_num FROM song_chord_link WHERE song_id=%i" %
                song_id)
        ]

    def update_chord(self, song_id, character_num, note_id, chord_type_id,
                     bass_note_id, marker, in_parentheses):
        self._execute(
            "UPDATE song_chord_link SET note_id=?, chord_type_id=?, "
            "bass_note_id=?, marker=?, in_parentheses=? "
            "WHERE song_id=? AND character_num=?",
            (note_id, chord_type_id, bass_note_id, marker, in_parentheses,
             song_id, character_num))

    def delete_chord(self, song_id, character_num):
        self._execute(
            "DELETE FROM song_chord_link WHERE song_id=? AND character_num=?",
            (song_id, character_num))

    def move_chord(self, song_id, old_character_num, new_character_num):
        self._execute(
            "UPDATE song_chord_link SET character_num=? "
            "WHERE song_id=? AND character_num=?",
            (new_character_num, song_id, old_character_num))

    @staticmethod
    def read_songs(connection):
        """Songs and their chord rows from another open songbook.

        Materializes each query. Nested executes on one sqlite3 cursor would
        reset the outer iterator. Does not migrate or commit the source.
        """
        songs = list(
            connection.execute(
                "SELECT id, number, title, subtitle, text FROM songs ORDER BY id"
            ))
        loaded = []
        for song in songs:
            chords = list(
                connection.execute(
                    "SELECT character_num, note_id, chord_type_id, "
                    "bass_note_id, marker, in_parentheses "
                    "FROM song_chord_link WHERE song_id=?", (song[0],)))
            loaded.append((song, chords))
        return loaded
