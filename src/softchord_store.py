"""SQLite songbook: open, load, and save songs and chord links.

Song, undo, and import talk to this store. They do not run SQL themselves.
New tables come from songbook.sql, which the iOS tests use as well.
Each chord is one text string in song_chord_link.chord (format version 2,
docs/chord_format.md). Version 1 files are converted before the store sees
them, by softchord_v1_compat.py.
"""

import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _schema_statements():
    """The statements in songbook.sql, without comments."""
    text = Path(__file__).with_name("songbook.sql").read_text(encoding="utf-8")
    lines = [line for line in text.splitlines()
             if not line.lstrip().startswith("--")]
    return [part.strip() for part in "\n".join(lines).split(";")
            if part.strip()]


def _create_statement(table_name):
    """The CREATE TABLE statement for table_name from songbook.sql."""
    prefix = "CREATE TABLE %s " % table_name
    for statement in _schema_statements():
        if statement.startswith(prefix) or statement.startswith(
                "CREATE TABLE %s(" % table_name):
            return statement
    raise RuntimeError("songbook.sql has no CREATE TABLE for %s" % table_name)


# Written to PRAGMA user_version by new songbooks. Version 1 (the separate
# note, type, bass, marker and parentheses columns) shows as user_version 0.
SONGBOOK_FORMAT_VERSION = 2

SONGS_TABLE_SQL = _create_statement("songs")
SONG_CHORD_LINK_TABLE_SQL = _create_statement("song_chord_link")
META_TABLE_SQL = _create_statement("meta")
DELETED_SONGS_TABLE_SQL = _create_statement("deleted_songs")
# Every CREATE statement of the current schema, in the order to run them.
SCHEMA_STATEMENTS = [
    statement for statement in _schema_statements()
    if statement.startswith("CREATE ")
]
SONG_CHORD_LINK_INDEX_NAME = "idx_song_chord_link_song_id"


def new_uuid():
    """A new song or songbook id: lowercase, hyphenated uuid4 text."""
    return str(uuid.uuid4())


def utc_now():
    """Now as Unix epoch seconds in UTC, for updated_at and deleted_at."""
    return int(datetime.now(timezone.utc).timestamp())


def songbook_name_for_path(path):
    """The default display name: the file name without its extension."""
    name = os.path.splitext(os.path.basename(path or ""))[0]
    return name or "songbook"


def create_schema(conn, name=None):
    """Create every table, the index and the meta rows in an empty database."""
    for statement in SCHEMA_STATEMENTS:
        conn.execute(statement)
    conn.executemany(
        "INSERT INTO meta (key, value) VALUES (?, ?)",
        [("format_version", str(SONGBOOK_FORMAT_VERSION)),
         ("songbook_uuid", new_uuid()),
         ("name", name or "songbook")])
    conn.execute("PRAGMA user_version = %i" % SONGBOOK_FORMAT_VERSION)


def enable_foreign_keys(conn):
    """Make this connection enforce song_chord_link.song_id (cascade delete)."""
    conn.execute("PRAGMA foreign_keys=ON")


def readonly_database_error(err):
    """SQLite refused a write because this connection cannot modify the file."""
    return (isinstance(err, sqlite3.OperationalError)
            and "readonly" in str(err).lower())


def database_file_was_replaced(err):
    """The open connection's file was moved or replaced, so it can no longer write."""
    return getattr(err, "sqlite_errorname", None) == "SQLITE_READONLY_DBMOVED"


class ChordLink:
    """One chord row, without the database id. chord is the chord string."""

    def __init__(self, character_num, chord):
        self.character_num = character_num
        self.chord = chord


class SongRecord:
    """Song columns and chord links loaded from the songbook."""

    def __init__(self, number, title, subtitle, text, chords, uuid=None,
                 updated_at=None):
        self.uuid = uuid
        self.updated_at = updated_at
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
    def create_file(path, name=None):
        """Create an empty songbook file and return its connection.

        Does not replace the store's current connection. The caller adopts
        the returned connection after closing the previous songbook. name is
        the display name stored in meta (default: the file name).
        """
        conn = sqlite3.connect(path)
        create_schema(conn, name or songbook_name_for_path(path))
        conn.commit()
        enable_foreign_keys(conn)
        return conn

    def list_song_rows(self):
        """(id, number, title) in id order. Empty when no songbook is open."""
        if not self.is_open:
            return []
        return list(
            self.connection.execute(
                "SELECT id, number, title FROM songs ORDER BY id"))

    def load_song(self, song_id):
        """Load one song and its chord strings."""
        conn = self._conn()
        row = conn.execute(
            "SELECT number, title, subtitle, text, uuid, updated_at "
            "FROM songs WHERE id=?", (song_id,)).fetchone()

        chords = []
        for chord_row in conn.execute(
                "SELECT id, character_num, chord FROM song_chord_link "
                "WHERE song_id=?", (song_id,)):
            chords.append(ChordLink(chord_row[1], chord_row[2]))
        return SongRecord(row[0], row[1], row[2], row[3], chords, row[4],
                          row[5])

    def next_song_id(self):
        """Next song id. The first song in an empty songbook is 0."""
        row = self._conn().execute("SELECT MAX(id) from songs").fetchone()
        if row[0] is None:
            return 0
        return row[0] + 1

    def _touch_song(self, song_id):
        """Set updated_at (UTC epoch seconds) after a change to the song."""
        self._execute("UPDATE songs SET updated_at=? WHERE id=?",
                      (utc_now(), song_id))

    def insert_song(self, song_id, number, title, subtitle, text, uuid=None):
        """Add a song. A new song gets a uuid4 unless one is given (undo of a
        delete gives the old one back). A tombstone for that uuid is removed.
        Returns the song's uuid."""
        uuid = uuid or new_uuid()
        self._execute(
            "INSERT INTO songs (id, uuid, number, title, subtitle, text, "
            "updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (song_id, uuid, number, title or "", subtitle or "", text or "",
             utc_now()))
        self._execute("DELETE FROM deleted_songs WHERE uuid=?", (uuid,))
        return uuid

    def _update_song_column(self, song_id, column, value):
        # updated_at only moves when the value really changes.
        self._execute(
            "UPDATE songs SET %s=?, updated_at=? WHERE id=? AND %s IS NOT ?" %
            (column, column), (value, utc_now(), song_id, value))

    def update_song_title(self, song_id, title):
        self._update_song_column(song_id, "title", title or "")

    def update_song_subtitle(self, song_id, subtitle):
        self._update_song_column(song_id, "subtitle", subtitle or "")

    def update_song_number(self, song_id, number):
        self._update_song_column(song_id, "number", number)

    def update_song_text(self, song_id, text):
        self._update_song_column(song_id, "text", text or "")

    def update_song(self, song_id, number, title, subtitle, text):
        """Save the song's columns. updated_at moves only if one changed."""
        title, subtitle, text = title or "", subtitle or "", text or ""
        self._execute(
            "UPDATE songs SET number=?, title=?, subtitle=?, text=?, "
            "updated_at=? WHERE id=? AND (number IS NOT ? OR title IS NOT ? "
            "OR subtitle IS NOT ? OR text IS NOT ?)",
            (number, title, subtitle, text, utc_now(), song_id, number, title,
             subtitle, text))

    def delete_song(self, song_id):
        """Delete a song and its chords, and leave a tombstone (its uuid and
        the UTC time) for sync. All in the caller's transaction."""
        row = self._execute("SELECT uuid FROM songs WHERE id=?",
                            (song_id,)).fetchone()
        self._execute("DELETE FROM song_chord_link WHERE song_id=?",
                      (song_id,))
        self._execute("DELETE FROM songs WHERE id=?", (song_id,))
        if row is not None:
            self._execute(
                "INSERT OR REPLACE INTO deleted_songs (uuid, deleted_at) "
                "VALUES (?, ?)", (row[0], utc_now()))

    def next_chord_id(self):
        """Next chord-link id. The first chord in an empty songbook is 0."""
        row = self._conn().execute(
            "SELECT MAX(id) from song_chord_link").fetchone()
        if row[0] is None:
            return 0
        return row[0] + 1

    def insert_chord(self, song_id, character_num, chord, chord_id=None):
        """Insert a chord link. Omit chord_id to let SQLite assign the row id."""
        if chord_id is None:
            self._execute(
                "INSERT INTO song_chord_link (song_id, character_num, chord) "
                "VALUES (?, ?, ?)", (song_id, character_num, chord))
            self._touch_song(song_id)
            return None
        self._execute(
            "INSERT INTO song_chord_link (id, song_id, character_num, chord) "
            "VALUES (?, ?, ?, ?)", (chord_id, song_id, character_num, chord))
        self._touch_song(song_id)
        return chord_id

    def chord_positions(self, song_id):
        return [
            row[0] for row in self._conn().execute(
                "SELECT character_num FROM song_chord_link WHERE song_id=?",
                (song_id,))
        ]

    def update_chord(self, song_id, character_num, chord):
        cursor = self._execute(
            "UPDATE song_chord_link SET chord=? "
            "WHERE song_id=? AND character_num=? AND chord IS NOT ?",
            (chord, song_id, character_num, chord))
        if cursor.rowcount > 0:
            self._touch_song(song_id)

    def delete_chord(self, song_id, character_num):
        cursor = self._execute(
            "DELETE FROM song_chord_link WHERE song_id=? AND character_num=?",
            (song_id, character_num))
        if cursor.rowcount > 0:
            self._touch_song(song_id)

    def move_chord(self, song_id, old_character_num, new_character_num):
        cursor = self._execute(
            "UPDATE song_chord_link SET character_num=? "
            "WHERE song_id=? AND character_num=? AND character_num IS NOT ?",
            (new_character_num, song_id, old_character_num,
             new_character_num))
        if cursor.rowcount > 0:
            self._touch_song(song_id)

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
                    "SELECT character_num, chord "
                    "FROM song_chord_link WHERE song_id=?", (song[0],)))
            loaded.append((song, chords))
        return loaded
