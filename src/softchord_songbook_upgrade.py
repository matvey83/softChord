"""Bring a songbook to the current schema (no Qt).

The current schema is src/songbook.sql, described in docs/songbook_format.md.
Early version 2 files had chord strings but not the rest:

  * songs had key_note_id, key_is_major and alt_key_note_id columns (the key
    is always detected now), no uuid and no updated_at, and title, subtitle
    and text could be NULL.
  * song_chord_link had no constraints and no index, and could hold chords
    of songs that do not exist (orphans).
  * there was no meta table and no deleted_songs table.

The file is recognised by its schema, not by user_version, which stays 2.

rebuild_to_current() does the upgrade inside a transaction the caller opened.
The editor (softchord_v1_compat.open_songbook) and tools/upgrade_songbook_v2.py
call it with the same safety rules as the version 1 conversion: a one-time
backup made with the SQLite backup API, an in-place transaction when the file
is writable, and otherwise a temporary copy.
"""

import os
import sqlite3
from urllib.parse import quote

from softchord_store import (
    SONGBOOK_FORMAT_VERSION,
    SONG_CHORD_LINK_INDEX_NAME,
    SONG_CHORD_LINK_TABLE_SQL,
    SONGS_TABLE_SQL,
    DELETED_SONGS_TABLE_SQL,
    META_TABLE_SQL,
    new_uuid,
    songbook_name_for_path,
    utc_now,
)

# Backup file tag for an upgrade of an early version 2 file.
PRE_UUID_TAG = "pre-uuid"

CURRENT_SONG_COLUMNS = ("id", "uuid", "number", "title", "subtitle", "text",
                        "updated_at")
OBSOLETE_SONG_COLUMNS = ("key_note_id", "key_is_major", "alt_key_note_id")


class ConversionError(Exception):
    """The songbook could not be converted. Nothing was changed."""


def table_names(conn):
    return [
        row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")
    ]


def table_columns(conn, table):
    return [row[1] for row in conn.execute("PRAGMA table_info(%s)" % table)]


def schema_is_current(conn):
    """True when the file has exactly the tables and columns of songbook.sql.

    The checks are on the schema because the early version 2 files have the
    same user_version.
    """
    tables = table_names(conn)
    for table in ("songs", "song_chord_link", "meta", "deleted_songs"):
        if table not in tables:
            return False
    info = {row[1]: row for row in conn.execute("PRAGMA table_info(songs)")}
    if set(info) != set(CURRENT_SONG_COLUMNS):
        return False
    # (name, notnull) flags: title, subtitle, text, uuid, updated_at
    for column in ("uuid", "title", "subtitle", "text", "updated_at"):
        if not info[column][3]:
            return False
    chord_columns = table_columns(conn, "song_chord_link")
    if sorted(chord_columns) != ["character_num", "chord", "id", "song_id"]:
        return False
    if not list(conn.execute("PRAGMA foreign_key_list(song_chord_link)")):
        return False
    indexes = [row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' "
        "AND tbl_name='song_chord_link'")]
    return SONG_CHORD_LINK_INDEX_NAME in indexes


class UpgradeReport:
    """What an upgrade did."""

    def __init__(self):
        self.songs = 0
        self.chords_before = 0
        self.chords = 0  # after the orphans were removed
        self.orphan_chords = 0
        self.orphan_song_ids = []  # song_id values that have no song
        self.key_columns_removed = []
        self.uuids_assigned = 0
        self.backup_path = None

    def lines(self):
        lines = ["songs: %i" % self.songs,
                 "chords: %i before, %i after" %
                 (self.chords_before, self.chords)]
        if self.orphan_chords:
            lines.append("orphan chord rows removed: %i (song ids %s)" % (
                self.orphan_chords,
                ", ".join(str(i) for i in self.orphan_song_ids)))
        if self.key_columns_removed:
            lines.append("key columns removed: %s" %
                         ", ".join(self.key_columns_removed))
        lines.append("uuids assigned: %i" % self.uuids_assigned)
        return lines


def database_file_name(conn):
    """The base name (no extension) of the connection's file, or None."""
    for _seq, _name, path in conn.execute("PRAGMA database_list"):
        if path:
            return songbook_name_for_path(path)
    return None


def _valid_uuid(value):
    import uuid
    if not isinstance(value, str):
        return False
    try:
        return str(uuid.UUID(value)) == value
    except ValueError:
        return False


def rebuild_to_current(conn, name=None, chord_rows=None, report=None):
    """Rebuild songs and song_chord_link to the current schema.

    Call inside a transaction (BEGIN IMMEDIATE) with foreign_keys off. The
    caller commits or rolls back. Does not commit.

    chord_rows are (id, song_id, character_num, chord) tuples to use instead
    of the table's rows (the version 1 conversion passes its converted rows).
    The song_chord_link table is dropped and made again, so it must not be
    referenced by anything else.

    * songs: key columns are dropped, NULL title, subtitle and text become
      '', valid unique uuids are kept and every other song gets a new one,
      updated_at is kept when it is an integer and is now (UTC) otherwise.
    * chords of songs that do not exist are removed.
    * meta gets the missing rows. Existing songbook_uuid and name are kept.
    * deleted_songs is created if it is missing.
    """
    report = report or UpgradeReport()
    name = name or database_file_name(conn) or "songbook"
    now = utc_now()
    tables = table_names(conn)

    if chord_rows is None:
        if "song_chord_link" in tables:
            chord_rows = list(conn.execute(
                "SELECT id, song_id, character_num, chord FROM "
                "song_chord_link ORDER BY rowid"))
        else:
            chord_rows = []
    chord_rows = list(chord_rows)
    report.chords_before = len(chord_rows)

    old_columns = table_columns(conn, "songs")
    report.key_columns_removed = [
        c for c in OBSOLETE_SONG_COLUMNS if c in old_columns
    ]
    selected = [c for c in ("id", "uuid", "number", "title", "subtitle",
                            "text", "updated_at") if c in old_columns]
    old_songs = list(conn.execute(
        "SELECT %s FROM songs ORDER BY id" % ", ".join(selected)))
    index = {column: i for i, column in enumerate(selected)}

    seen = set()
    new_songs = []
    for row in old_songs:
        song_uuid = row[index["uuid"]] if "uuid" in index else None
        if not _valid_uuid(song_uuid) or song_uuid in seen:
            song_uuid = new_uuid()
            report.uuids_assigned += 1
        seen.add(song_uuid)
        updated_at = row[index["updated_at"]] if "updated_at" in index else None
        if not isinstance(updated_at, int):
            updated_at = now
        new_songs.append((
            row[index["id"]], song_uuid,
            row[index["number"]] if "number" in index else None,
            (row[index["title"]] if "title" in index else None) or "",
            (row[index["subtitle"]] if "subtitle" in index else None) or "",
            (row[index["text"]] if "text" in index else None) or "",
            updated_at))
    report.songs = len(new_songs)

    song_ids = {row[0] for row in new_songs}
    kept = []
    orphan_ids = set()
    for row in chord_rows:
        if row[1] in song_ids:
            kept.append(row)
        else:
            orphan_ids.add(row[1])
    report.orphan_chords = len(chord_rows) - len(kept)
    report.orphan_song_ids = sorted(
        orphan_ids, key=lambda value: (value is None, value))
    report.chords = len(kept)

    # Rebuild. Nothing references songs yet because the chord table goes first.
    conn.execute("DROP TABLE IF EXISTS song_chord_link")
    conn.execute("ALTER TABLE songs RENAME TO songs_before_upgrade")
    conn.execute(SONGS_TABLE_SQL)
    conn.executemany(
        "INSERT INTO songs (id, uuid, number, title, subtitle, text, "
        "updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)", new_songs)
    conn.execute("DROP TABLE songs_before_upgrade")
    conn.execute(SONG_CHORD_LINK_TABLE_SQL)
    conn.executemany(
        "INSERT INTO song_chord_link (id, song_id, character_num, chord) "
        "VALUES (?, ?, ?, ?)", kept)
    conn.execute(
        "CREATE INDEX %s ON song_chord_link(song_id)" %
        SONG_CHORD_LINK_INDEX_NAME)

    tables = table_names(conn)
    if "meta" not in tables:
        conn.execute(META_TABLE_SQL)
    conn.executemany(
        "INSERT OR IGNORE INTO meta (key, value) VALUES (?, ?)",
        [("songbook_uuid", new_uuid()), ("name", name)])
    conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES ('format_version', ?)",
        (str(SONGBOOK_FORMAT_VERSION),))
    if "deleted_songs" not in tables:
        conn.execute(DELETED_SONGS_TABLE_SQL)
    conn.execute("PRAGMA user_version = %i" % SONGBOOK_FORMAT_VERSION)

    # Check before the caller commits.
    stored_songs = conn.execute("SELECT COUNT(*) FROM songs").fetchone()[0]
    stored_chords = conn.execute(
        "SELECT COUNT(*) FROM song_chord_link").fetchone()[0]
    if stored_songs != len(old_songs) or stored_chords != len(kept):
        raise ConversionError(
            "Row counts changed: %i songs and %i chords became %i and %i." %
            (len(old_songs), len(kept), stored_songs, stored_chords))
    if list(conn.execute("PRAGMA foreign_key_check")):
        raise ConversionError("Chords without a song remain after upgrade.")
    return report


def upgrade_connection(conn, name=None):
    """Upgrade an early version 2 connection in one transaction.

    On any error the transaction is rolled back and the file is unchanged.
    The caller runs finish_conversion() afterwards.
    """
    previous_isolation = conn.isolation_level
    conn.isolation_level = None  # explicit BEGIN / COMMIT
    try:
        conn.execute("BEGIN IMMEDIATE")
        report = rebuild_to_current(conn, name)
        conn.execute("COMMIT")
    except BaseException:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise
    finally:
        conn.isolation_level = previous_isolation
    return report


def finish_conversion(conn):
    """integrity_check and VACUUM after a committed conversion."""
    result = conn.execute("PRAGMA integrity_check").fetchone()[0]
    if result != "ok":
        raise ConversionError("integrity_check failed: %s" % result)
    previous = conn.isolation_level
    conn.isolation_level = None
    try:
        conn.execute("VACUUM")
    finally:
        conn.isolation_level = previous


def backup_path_for(path, tag="v1"):
    """<name>.songbook.<tag>.bak, or the first free numbered variant."""
    candidate = "%s.%s.bak" % (path, tag)
    number = 2
    while os.path.exists(candidate):
        candidate = "%s.%s.%i.bak" % (path, tag, number)
        number += 1
    return candidate


def _uri_path(path):
    return quote(os.path.abspath(path))


def make_backup(path, tag="v1"):
    """Copy the file with the SQLite backup API. Never overwrites a file."""
    backup = backup_path_for(path, tag)
    source = sqlite3.connect("file:%s?mode=ro" % _uri_path(path), uri=True)
    try:
        target = sqlite3.connect(backup)
        try:
            source.backup(target)
        finally:
            target.close()
    except BaseException:
        if os.path.exists(backup):
            os.remove(backup)
        raise
    finally:
        source.close()
    return backup


def upgrade_file_in_place(path, name=None):
    """Back up and upgrade a file. Returns (UpgradeReport, backup_path)."""
    backup = make_backup(path, PRE_UUID_TAG)
    conn = sqlite3.connect(path)
    try:
        report = upgrade_connection(conn, name)
        finish_conversion(conn)
    finally:
        conn.close()
    report.backup_path = backup
    return report, backup


def upgrade_copy(source_path, target_path, name=None):
    """Upgrade a copy of source_path made at target_path (a new file). The
    source is only read. Returns an UpgradeReport."""
    if os.path.exists(target_path):
        raise ConversionError("%s already exists." % target_path)
    try:
        source = sqlite3.connect("file:%s?mode=ro" % _uri_path(source_path),
                                 uri=True)
        try:
            target = sqlite3.connect(target_path)
            try:
                source.backup(target)
            finally:
                target.close()
        finally:
            source.close()
        conn = sqlite3.connect(target_path)
        try:
            report = upgrade_connection(
                conn, name or songbook_name_for_path(target_path))
            finish_conversion(conn)
        finally:
            conn.close()
    except BaseException:
        # Do not leave a half-made file behind.
        if os.path.exists(target_path):
            os.remove(target_path)
        raise
    return report
