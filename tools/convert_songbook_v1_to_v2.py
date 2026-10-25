#!/usr/bin/env python3
"""One-off: convert old-format songbooks (version 1) to the new format.

TODO(remove-v1-compat): delete this script together with
src/softchord_v1_compat.py, which does the work.

Usage:
    python3 tools/convert_songbook_v1_to_v2.py [--check] FILE.songbook ...

Each file is backed up as FILE.songbook.v1.bak (never overwriting an existing
backup), converted in place in one transaction, then checked against its
backup: every chord must read back to the same note, type, bass, marker and
parentheses, every song must have the same number of chords, and the songs
table must be identical (NULL title, subtitle and text become ''). Chord rows
whose song does not exist are removed and reported. The result has the
current schema (song uuids, updated_at, meta, deleted_songs). Then
integrity_check, foreign_key_check and VACUUM run.

--check converts a temporary copy only, so the file is not touched.

A file that already has the current schema is skipped. A version 2 file
without uuids is upgraded by tools/upgrade_songbook_v2.py. Exit status 1 if any file
failed or did not verify.
"""

import argparse
from collections import Counter
import os
import shutil
import sqlite3
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

import softchord_v1_compat as compat  # noqa: E402
from softchord_chords import chord_types_list, parse_chord  # noqa: E402


def _rows(conn, sql):
    return list(conn.execute(sql))


def verify(old_path, new_path):
    """Compare a converted file with its original. Returns a list of problems
    (empty when everything matches)."""
    problems = []
    old = sqlite3.connect("file:%s?mode=ro" % old_path, uri=True)
    new = sqlite3.connect("file:%s?mode=ro" % new_path, uri=True)
    try:
        file_types = compat._file_chord_types(old)
        old_song_ids = {r[0] for r in old.execute("SELECT id FROM songs")}
        all_old_rows = _rows(
            old, "SELECT song_id, character_num, note_id, chord_type_id, "
            "bass_note_id, marker, in_parentheses, id FROM song_chord_link "
            "ORDER BY rowid")
        # Chords of songs that do not exist are removed on purpose.
        old_rows = [r[:7] for r in all_old_rows if r[0] in old_song_ids]
        new_rows = _rows(
            new, "SELECT song_id, character_num, chord FROM song_chord_link")
        if len(old_rows) != len(new_rows):
            problems.append("chord rows: %i became %i" %
                            (len(old_rows), len(new_rows)))

        # Compare as multisets: (song, position, note, suffix, bass, marker,
        # parentheses) from the old fields against the new strings parsed.
        want_counter = Counter()
        for o in old_rows:
            song_id, position, note_id, type_id, bass_id, marker, parens = o
            if not (isinstance(note_id, int) and 0 <= note_id <= 11):
                want_counter[(song_id, position, "unknown")] += 1
                continue
            if file_types is not None:
                want_suffix = file_types.get(type_id, "")
            elif isinstance(type_id, int) and 0 <= type_id < len(
                    chord_types_list):
                want_suffix = chord_types_list[type_id][2]
            else:
                want_suffix = ""
            type_index, known = compat.classify_suffix(want_suffix)
            if known:
                want_suffix = chord_types_list[type_index][2]
            want_bass = bass_id if isinstance(
                bass_id, int) and 0 <= bass_id <= 11 else -1
            want_counter[(song_id, position, note_id, want_suffix, want_bass,
                          compat._normalize_marker(marker)[0],
                          bool(parens))] += 1
        got_counter = Counter()
        for song_id, position, text in new_rows:
            parsed = parse_chord(text)
            if parsed.unknown:
                got_counter[(song_id, position, "unknown")] += 1
            else:
                got_counter[(song_id, position, parsed.note_id,
                             parsed.suffix, parsed.bass_note_id,
                             parsed.marker, parsed.in_parentheses)] += 1
        for key in (want_counter - got_counter):
            problems.append("missing after conversion: %r" % (key,))
        for key in (got_counter - want_counter):
            problems.append("unexpected after conversion: %r" % (key,))

        # Ids that were already unique are kept on the same chord.
        old_ids = [
            r for r in _rows(
                old, "SELECT id, song_id, character_num FROM song_chord_link "
                "WHERE id IS NOT NULL") if r[1] in old_song_ids]
        counts = Counter(r[0] for r in old_ids)
        new_by_id = {
            r[0]: (r[1], r[2]) for r in new.execute(
                "SELECT id, song_id, character_num FROM song_chord_link")
        }
        for chord_id, song_id, position in old_ids:
            if counts[chord_id] == 1 and new_by_id.get(chord_id) != (
                    song_id, position):
                problems.append("id %r moved" % (chord_id,))

        old_counts = [
            r for r in _rows(
                old, "SELECT song_id, COUNT(*) FROM song_chord_link "
                "GROUP BY song_id ORDER BY song_id") if r[0] in old_song_ids]
        new_counts = _rows(
            new, "SELECT song_id, COUNT(*) FROM song_chord_link "
            "GROUP BY song_id ORDER BY song_id")
        if old_counts != new_counts:
            problems.append("chords per song differ")

        columns = [r[1] for r in old.execute("PRAGMA table_info(songs)")]
        wanted = [c for c in ("id", "number", "title", "subtitle", "text")
                  if c in columns]
        query = "SELECT %s FROM songs ORDER BY id" % ", ".join(wanted)
        want_songs = [
            tuple("" if (value is None and name in ("title", "subtitle",
                                                    "text")) else value
                  for name, value in zip(wanted, row))
            for row in _rows(old, query)
        ]
        new_query = "SELECT %s FROM songs ORDER BY id" % ", ".join(wanted)
        if want_songs != _rows(new, new_query):
            problems.append("songs table differs")
        if "subtitle" not in columns and any(
                r[0] not in (None, "") for r in new.execute(
                    "SELECT subtitle FROM songs")):
            problems.append("subtitle added with data")

        if new.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            problems.append("integrity_check failed")
        if new.execute("PRAGMA user_version").fetchone()[0] != 2:
            problems.append("user_version is not 2")
        tables = sorted(r[0] for r in new.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"))
        if tables != ["deleted_songs", "meta", "song_chord_link", "songs"]:
            problems.append("tables are %r" % tables)
        if not compat.schema_is_current(new):
            problems.append("schema is not the current one")
        if _rows(new, "PRAGMA foreign_key_check"):
            problems.append("foreign_key_check found problems")
        uuids = [r[0] for r in new.execute("SELECT uuid FROM songs")]
        if len(set(uuids)) != len(uuids):
            problems.append("song uuids are not unique")
        if new.execute("SELECT COUNT(*) FROM song_chord_link WHERE id IS NULL"
                       ).fetchone()[0]:
            problems.append("chord rows without an id")
    finally:
        old.close()
        new.close()
    return problems


def describe(report):
    lines = ["  songs: %i, chords: %i before, %i after" %
             (report.songs, report.chords, report.chords_after)]
    if report.orphan_chords:
        lines.append("  orphan chord rows removed: %i (song ids %s)" % (
            report.orphan_chords,
            ", ".join(str(i) for i in report.orphan_song_ids)))
    for line in report.anomalies():
        lines.append("  anomaly - " + line)
    if report.used_file_chord_types:
        lines.append("  used the file's own chord_types table")
    return lines


def convert(path, check_only):
    """Convert one file. Returns True when it converted and verified."""
    print(path)
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        print("  skipped: missing or empty file, nothing to convert")
        return False
    conn = sqlite3.connect(path)
    try:
        file_format = compat.detect_format(conn)
    finally:
        conn.close()
    if file_format == compat.FORMAT_V2:
        print("  already the current format, skipped")
        return True
    if file_format == compat.FORMAT_V2_EARLY:
        print("  version 2 without uuids: use tools/upgrade_songbook_v2.py")
        return False

    if check_only:
        folder = tempfile.mkdtemp(prefix="softchord_check_")
        work = os.path.join(folder, os.path.basename(path))
        shutil.copyfile(path, work)
        original = work + ".orig"
        shutil.copyfile(path, original)
    else:
        folder = None
        work = path
        original = None
    try:
        report, backup = compat.convert_file_in_place(work)
        problems = verify(original or backup, work)
    finally:
        pass
    for line in describe(report):
        print(line)
    if not check_only:
        print("  backup: %s" % backup)
    if problems:
        for problem in problems[:20]:
            print("  PROBLEM: " + problem)
        print("  %i problems" % len(problems))
    else:
        print("  verified: every chord reads back to the same fields")
    if folder:
        shutil.rmtree(folder, ignore_errors=True)
    return not problems


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("files", nargs="+")
    parser.add_argument("--check", action="store_true",
                        help="convert a temporary copy only")
    args = parser.parse_args(argv)
    ok = True
    for path in args.files:
        try:
            ok = convert(path, args.check) and ok
        except Exception as err:
            print("  FAILED: %s: %s" % (type(err).__name__, err))
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
