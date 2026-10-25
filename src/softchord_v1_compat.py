"""Open songbooks in the old format (version 1) by converting them (no Qt).

TODO(remove-v1-compat): This whole module exists only so the editor can read
songbooks from before chords became one string. Once every songbook has been
opened once, delete this file and every line that mentions
TODO(remove-v1-compat) (softchord_io.py, softchord_session.py, test_song.py).
tools/convert_songbook_v1_to_v2.py uses it too, so delete that as well.

Version 1 stored each chord as note_id, chord_type_id, bass_note_id, marker
and in_parentheses in song_chord_link, with user_version 0. Some files also
had notes and chord_types tables. Version 2 (docs/chord_format.md) has one
chord string per row and user_version 2.

The conversion produces the current schema directly (src/songbook.sql, see
docs/songbook_format.md): song uuids, updated_at, meta, deleted_songs, no key
columns, and no chords of songs that do not exist. A version 2 file from before
those additions is upgraded the same way (softchord_songbook_upgrade.py), with
a backup named <name>.songbook.pre-uuid.bak. That part is not temporary.

The editor never writes the old format. open_songbook() converts an old file:

  * in place, when the file and its folder are writable. A backup of the
    original is written first, next to the file, as <name>.songbook.v1.bak
    (an existing backup is never overwritten). The conversion runs in one
    transaction and is checked before it is committed.
  * otherwise (read-only file or folder, or any failure), the original is not
    touched. A converted copy in a temporary folder is opened instead, and
    the result says so, so that the editor can ask for Save As.
"""

import os
import shutil
import sqlite3
import tempfile

from softchord_chords import (
    ChordFields,
    UNKNOWN_CHORD_TEXT,
    chord_types_list,
    classify_suffix,
    global_notes_list,
    parse_chord,
    spelled_chord_strings,
)
from softchord_store import SONGBOOK_FORMAT_VERSION
from softchord_songbook_upgrade import (  # noqa: F401 (re-exported)
    ConversionError,
    PRE_UUID_TAG,
    UpgradeReport,
    backup_path_for,
    finish_conversion,
    make_backup,
    rebuild_to_current,
    schema_is_current,
    table_columns,
    table_names,
    upgrade_connection,
    upgrade_file_in_place,
    _uri_path,
)

OLD_CHORD_COLUMNS = ("note_id", "chord_type_id", "bass_note_id", "marker",
                     "in_parentheses")

FORMAT_V1 = 1  # one note, type, bass, marker and parentheses per chord
FORMAT_V2 = 2  # the current schema (user_version 2 in the file)
FORMAT_V2_EARLY = 3  # chord strings, but not the current schema yet


_columns = table_columns
_tables = table_names


def detect_format(conn):
    """FORMAT_V1, FORMAT_V2_EARLY or FORMAT_V2 for an open songbook connection.

    The schema decides. user_version only has to be 2 or less. Raises
    ValueError for a songbook saved by a newer softChord.
    """
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version > SONGBOOK_FORMAT_VERSION:
        raise ValueError(
            "This songbook was saved by a newer version of softChord "
            "(songbook format %i). Please update softChord." % version)
    if "song_chord_link" in _tables(conn):
        columns = _columns(conn, "song_chord_link")
        if "chord" not in columns:
            if "note_id" in columns:
                return FORMAT_V1
            raise ValueError("This songbook has an unrecognized chord table.")
    if schema_is_current(conn):
        return FORMAT_V2
    return FORMAT_V2_EARLY


# ---------------------------------------------------------------------------
# Row conversion
# ---------------------------------------------------------------------------


class ConversionReport:
    """What a conversion did, and what looked odd in the old data."""

    def __init__(self):
        self.songs = 0
        self.chords = 0
        self.unknown_chords = 0  # rows that became "?"
        self.marker_normalized = 0  # marker was NULL, "-1", "None" or -1
        self.parentheses_null = 0
        self.bass_none = 0  # NULL, -1 or out of range
        self.bass_out_of_range = 0
        self.type_missing = 0  # type id not in the table in use
        self.orphan_chords = 0  # song_id has no song (removed)
        self.orphan_song_ids = []
        self.key_columns_removed = []
        self.uuids_assigned = 0
        self.chords_after = 0  # chords left once the orphans are removed
        self.duplicate_positions = 0  # same song and character (kept)
        self.ids_assigned = 0  # NULL or repeated chord ids got a new id
        self.type_table_differences = []
        self.notes_table_differences = []
        self.used_file_chord_types = False
        self.backup_path = None

    def anomalies(self):
        lines = []
        for name in ("unknown_chords", "marker_normalized",
                     "parentheses_null", "bass_out_of_range", "type_missing",
                     "orphan_chords", "duplicate_positions", "ids_assigned"):
            if getattr(self, name):
                lines.append("%s: %i" % (name, getattr(self, name)))
        lines.extend(self.type_table_differences)
        lines.extend(self.notes_table_differences)
        return lines


def _normalize_marker(marker):
    if marker is None or marker == -1 or marker in ("-1", "None"):
        return "", True
    return str(marker), False


def _file_chord_types(conn):
    """{id: printed text} from the file's own chord_types table, or None."""
    if "chord_types" not in _tables(conn):
        return None
    try:
        return {row[0]: row[1] for row in conn.execute(
            "SELECT id, print FROM chord_types")}
    except sqlite3.Error:
        return None


def _compare_tables(conn, report):
    """Note differences between the file's own tables and the code's lists."""
    file_types = _file_chord_types(conn)
    if file_types is not None:
        report.used_file_chord_types = True
        for type_id, _name, print_text in chord_types_list:
            if type_id in file_types and file_types[type_id] != print_text:
                report.type_table_differences.append(
                    "chord_types id %i: file prints %r, code prints %r (the "
                    "file's text was used for this file)" %
                    (type_id, file_types[type_id], print_text))
        for type_id in file_types:
            if type_id >= len(chord_types_list):
                report.type_table_differences.append(
                    "chord_types id %i is not in the code's list" % type_id)
    if "notes" in _tables(conn):
        try:
            file_notes = {row[0]: (row[1], row[2]) for row in conn.execute(
                "SELECT id, text, alt_text FROM notes")}
        except sqlite3.Error:
            file_notes = {}
        for note_id, text, alt_text in global_notes_list:
            if file_notes.get(note_id) != (text, alt_text):
                report.notes_table_differences.append(
                    "notes id %i: file has %r, code has %r" %
                    (note_id, file_notes.get(note_id), (text, alt_text)))
    return file_types


def old_row_to_fields(row, file_types, report):
    """ChordFields from one (character_num, note_id, chord_type_id,
    bass_note_id, marker, in_parentheses) row of an old songbook.
    Also returns the expected parse of the result, for checking.
    """
    (character_num, note_id, type_id, bass_id, marker, parens) = row
    marker, changed = _normalize_marker(marker)
    if changed:
        report.marker_normalized += 1
    if parens is None:
        report.parentheses_null += 1
    parens = bool(parens)

    if not isinstance(note_id, int) or not 0 <= note_id <= 11:
        report.unknown_chords += 1
        return ChordFields(character_num, -1, 0, -1, "", 0,
                           unknown_raw=UNKNOWN_CHORD_TEXT), None

    if bass_id is None or bass_id == -1:
        bass_id = -1
    elif not isinstance(bass_id, int) or not 0 <= bass_id <= 11:
        report.bass_out_of_range += 1
        bass_id = -1
    if bass_id == -1:
        report.bass_none += 1

    if file_types is not None:
        print_text = file_types.get(type_id)
    elif isinstance(type_id, int) and 0 <= type_id < len(chord_types_list):
        print_text = chord_types_list[type_id][2]
    else:
        print_text = None
    if print_text is None:
        # No such type: keep the root and call it major.
        report.type_missing += 1
        print_text = ""
    new_type_id, known = classify_suffix(print_text)
    fields = ChordFields(character_num, note_id, new_type_id, bass_id,
                         marker, parens,
                         suffix=None if known else print_text)
    expected = (note_id, new_type_id, bass_id, marker, parens,
                chord_types_list[new_type_id][2] if known else print_text)
    return fields, expected


def _check_parsed(chord, expected, where):
    """The new string must parse back to the old fields."""
    parsed = parse_chord(chord)
    if expected is None:
        ok = parsed.unknown and parsed.raw == chord
    else:
        note_id, type_id, bass_id, marker, parens, suffix = expected
        ok = ((not parsed.unknown) and parsed.note_id == note_id
              and parsed.chord_type_id == type_id
              and parsed.bass_note_id == bass_id
              and parsed.marker == marker
              and parsed.in_parentheses == parens
              and parsed.suffix == suffix)
    if not ok:
        raise ConversionError("Chord %r does not read back as the old chord "
                              "(%s)." % (chord, where))


def convert_connection(conn):
    """Convert an open version 1 connection to version 2 in one transaction.

    Verifies the result before it commits. Produces the current schema
    (softchord_songbook_upgrade.rebuild_to_current). Returns a
    ConversionReport. On any error the transaction is rolled back and the
    file is unchanged. The caller runs integrity_check and VACUUM afterwards
    (finish_conversion).
    """
    report = ConversionReport()
    previous_isolation = conn.isolation_level
    conn.isolation_level = None  # explicit BEGIN / COMMIT
    try:
        conn.execute("BEGIN IMMEDIATE")
        file_types = _compare_tables(conn, report)

        old_rows = list(
            conn.execute(
                "SELECT id, song_id, character_num, note_id, chord_type_id, "
                "bass_note_id, marker, in_parentheses FROM song_chord_link "
                "ORDER BY rowid"))
        # The old id column was "int primary key", which allows NULL (and
        # SQLite does not number such rows). Give those rows fresh ids.
        used_ids = set()
        next_id = max([row[0] for row in old_rows if row[0] is not None] +
                      [-1]) + 1
        fixed_rows = []
        for row in old_rows:
            if row[0] is None or row[0] in used_ids:
                row = (next_id,) + tuple(row[1:])
                next_id += 1
                report.ids_assigned += 1
            used_ids.add(row[0])
            fixed_rows.append(row)
        old_rows = fixed_rows
        song_ids = {row[0] for row in conn.execute("SELECT id FROM songs")}
        report.songs = len(song_ids)
        report.chords = len(old_rows)

        by_song = {}
        for index, row in enumerate(old_rows):
            by_song.setdefault(row[1], []).append((index, row))

        converted_by_index = {}
        for song_id, indexed_rows in by_song.items():
            rows = [row for _index, row in indexed_rows]
            if song_id not in song_ids:
                report.orphan_chords += len(rows)
            positions = {}
            for row in rows:
                positions[row[2]] = positions.get(row[2], 0) + 1
            report.duplicate_positions += sum(
                1 for count in positions.values() if count > 1)

            converted = [
                old_row_to_fields(row[2:], file_types, report) for row in rows
            ]
            strings = spelled_chord_strings([c[0] for c in converted])
            for (index, row), (_fields, expected), chord in zip(
                    indexed_rows, converted, strings):
                _check_parsed(chord, expected, "chord id %s" % row[0])
                converted_by_index[index] = (row[0], row[1], row[2], chord)
        # Keep the rows in their old order.
        new_rows = [converted_by_index[i] for i in range(len(old_rows))]

        # Types and notes come from the code now.
        conn.execute("DROP TABLE IF EXISTS chord_types")
        conn.execute("DROP TABLE IF EXISTS notes")
        # Build the current schema: song uuids, updated_at, meta and
        # deleted_songs, no key columns, and no orphan chords. This replaces
        # song_chord_link with the converted rows.
        upgraded = rebuild_to_current(conn, chord_rows=new_rows)
        report.orphan_song_ids = upgraded.orphan_song_ids
        report.key_columns_removed = upgraded.key_columns_removed
        report.uuids_assigned = upgraded.uuids_assigned
        report.chords_after = upgraded.chords
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


def convert_file_in_place(path):
    """Back up and convert a file. Returns (ConversionReport, backup_path)."""
    backup = make_backup(path)
    conn = sqlite3.connect(path)
    try:
        report = convert_connection(conn)
        finish_conversion(conn)
    finally:
        conn.close()
    report.backup_path = backup
    return report, backup


def _can_write_in_place(path):
    directory = os.path.dirname(os.path.abspath(path))
    return os.access(path, os.W_OK) and os.access(directory, os.W_OK)


class OpenedSongbook:
    """The result of open_songbook()."""

    def __init__(self, conn, path, original_path):
        self.conn = conn
        # The file the connection is on. Differs from original_path for a copy.
        self.path = path
        self.original_path = original_path
        self.converted = False  # an old file was converted (in place or copy)
        self.temp_copy = False  # path is a temporary copy of original_path
        self.read_only = False  # a version 2 file that cannot be modified
        self.backup_path = None
        self.message = None  # shown to the user once, when not None
        self.report = None


def open_songbook(path, connect):
    """Open a songbook file, converting it first when it is the old format.

    connect(path) opens and checks a file (connect_existing_songbook).
    Never changes the original unless the conversion in place succeeded.
    """
    conn = connect(path)
    try:
        file_format = detect_format(conn)
    except BaseException:
        conn.close()
        raise

    opened = OpenedSongbook(conn, path, path)
    if file_format == FORMAT_V2:
        if not _can_write_in_place(path):
            opened.read_only = True
            opened.message = (
                "This songbook is read-only, so changes cannot be saved to "
                "it.\n\n%s\n\nUse File → Save Songbook As... to save a "
                "writable copy." % path)
        elif conn.execute("PRAGMA user_version").fetchone()[0] != \
                SONGBOOK_FORMAT_VERSION:
            # Made by an editor that did not set the version. Mark it.
            try:
                conn.execute("PRAGMA user_version = %i" %
                             SONGBOOK_FORMAT_VERSION)
                conn.commit()
            except sqlite3.Error:
                pass
        return opened

    # Not the current schema: convert (version 1) or upgrade (early version 2)
    # before use. TODO(remove-v1-compat): the version 1 part.
    conn.close()
    is_v1 = file_format == FORMAT_V1
    if is_v1:
        in_place = convert_file_in_place
        convert = convert_connection
        what = "the old chord format"
        done = "converted to the new format"
    else:
        in_place = upgrade_file_in_place
        convert = upgrade_connection
        what = ("an earlier version of the songbook format (no song ids "
                "yet)")
        done = "upgraded to the current format"
    failure = None
    if _can_write_in_place(path):
        try:
            report, backup = in_place(path)
        except Exception as err:  # the original is unchanged (rolled back)
            failure = "%s: %s" % (type(err).__name__, err)
        else:
            opened = OpenedSongbook(connect(path), path, path)
            opened.converted = True
            opened.report = report
            opened.backup_path = backup
            opened.message = (
                "This songbook used %s. It was %s.\n\nA backup of the "
                "original is saved as:\n%s" % (what, done, backup))
            return opened

    reason = failure or (
        "the file or its folder is read-only")
    folder = tempfile.mkdtemp(prefix="softchord_v1_")
    copy_path = os.path.join(folder, os.path.basename(path))
    try:
        shutil.copyfile(path, copy_path)
        os.chmod(copy_path, 0o600)
        copy_conn = sqlite3.connect(copy_path)
        try:
            report = convert(copy_conn)
        finally:
            copy_conn.close()
        copy_conn = sqlite3.connect(copy_path)
        try:
            finish_conversion(copy_conn)
        finally:
            copy_conn.close()
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise
    opened = OpenedSongbook(connect(copy_path), copy_path, path)
    opened.converted = True
    opened.temp_copy = True
    opened.report = report
    opened.message = (
        "This songbook uses %s, and it cannot be %s in place (%s).\n\n"
        "The original was not changed:\n%s\n\n"
        "You are working on a converted temporary copy. Use File → Save "
        "Songbook As... to keep your changes." %
        (what, "converted" if is_v1 else "upgraded", reason, path))
    return opened


def open_for_reading(path, connect):
    """Open a songbook only to read songs from it (for Append Songbook).

    Returns (connection, cleanup). An old-format file is read through a
    converted temporary copy, so the source is never changed. Call cleanup()
    after the connection is closed.
    """
    conn = connect(path)
    try:
        file_format = detect_format(conn)
    except BaseException:
        conn.close()
        raise
    if file_format != FORMAT_V1:
        # The songs and chord_link columns that are read are the same in an
        # early version 2 file, so it is read as it is.
        return conn, lambda: None
    conn.close()
    folder = tempfile.mkdtemp(prefix="softchord_v1_")
    copy_path = os.path.join(folder, os.path.basename(path))
    try:
        shutil.copyfile(path, copy_path)
        copy_conn = sqlite3.connect(copy_path)
        try:
            convert_connection(copy_conn)
        finally:
            copy_conn.close()
        return connect(copy_path), lambda: shutil.rmtree(folder,
                                                         ignore_errors=True)
    except BaseException:
        shutil.rmtree(folder, ignore_errors=True)
        raise
