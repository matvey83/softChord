#!/usr/bin/env python3
"""Upgrade a songbook to the current version 2 schema, outside the editor.

Usage:
    python3 tools/upgrade_songbook_v2.py FILE --output NEW_FILE [--name NAME]
    python3 tools/upgrade_songbook_v2.py FILE --in-place [--name NAME]

The current schema adds song uuids, updated_at, a meta table and a
deleted_songs table, drops the key columns, adds the foreign key from
song_chord_link to songs, and removes chord rows whose song does not exist.
See docs/songbook_format.md.

FILE is never changed unless --in-place is given. With --output the upgraded
copy is written to NEW_FILE (which must not exist yet). With --in-place a
backup FILE.pre-uuid.bak is made first (never overwriting an older backup),
then FILE is upgraded in one transaction.

A version 1 file (note_id columns) is converted straight to the current
schema too. A file that already has the current schema is left alone.

The result is checked against the original: same songs, same chords except the
orphan rows (which are reported with their song ids), unique uuids,
integrity_check ok, foreign_key_check empty. Exit status 1 if the upgrade
failed or did not verify.
"""

import argparse
import os
import sqlite3
import sys
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

import softchord_songbook_upgrade as upgrade  # noqa: E402
import softchord_v1_compat as compat  # noqa: E402


def _open_readonly(path):
    return sqlite3.connect("file:%s?mode=ro" % quote(os.path.abspath(path)),
                           uri=True)


def verify(original_path, new_path):
    """Compare an early version 2 file with its upgraded version. Returns a
    list of problems (empty when everything matches)."""
    problems = []
    old = _open_readonly(original_path)
    new = _open_readonly(new_path)
    try:
        old_songs = {}
        for row in old.execute(
                "SELECT id, number, title, subtitle, text FROM songs"):
            old_songs[row[0]] = (row[1], row[2] or "", row[3] or "",
                                 row[4] or "")
        new_songs = {}
        for row in new.execute(
                "SELECT id, number, title, subtitle, text FROM songs"):
            new_songs[row[0]] = (row[1], row[2], row[3], row[4])
        if len(old_songs) != len(new_songs):
            problems.append("songs: %i became %i" %
                            (len(old_songs), len(new_songs)))
        if old_songs != new_songs:
            problems.append("song ids, numbers, titles, subtitles or text "
                            "differ")

        old_chords = sorted(
            (r[0], r[1], r[2], r[3]) for r in old.execute(
                "SELECT song_id, character_num, chord, id "
                "FROM song_chord_link") if r[0] in old_songs)
        new_chords = sorted(
            (r[0], r[1], r[2], r[3]) for r in new.execute(
                "SELECT song_id, character_num, chord, id "
                "FROM song_chord_link"))
        if len(old_chords) != len(new_chords):
            problems.append("chords (without orphans): %i became %i" %
                            (len(old_chords), len(new_chords)))
        elif old_chords != new_chords:
            problems.append("chord rows differ")

        uuids = [r[0] for r in new.execute("SELECT uuid FROM songs")]
        if len(set(uuids)) != len(uuids):
            problems.append("song uuids are not unique")
        if new.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            problems.append("integrity_check failed")
        if list(new.execute("PRAGMA foreign_key_check")):
            problems.append("foreign_key_check found problems")
        if new.execute("PRAGMA user_version").fetchone()[0] != 2:
            problems.append("user_version is not 2")
        if not upgrade.schema_is_current(new):
            problems.append("schema is not the current one")
        tables = sorted(upgrade.table_names(new))
        if tables != ["deleted_songs", "meta", "song_chord_link", "songs"]:
            problems.append("tables are %r" % tables)
    finally:
        old.close()
        new.close()
    return problems


def _format_of(path):
    conn = _open_readonly(path)
    try:
        return compat.detect_format(conn)
    finally:
        conn.close()


def _report_lines(report):
    lines = ["  songs: %i" % report.songs,
             "  chords: %i before, %i after" %
             (getattr(report, "chords_before", None) or report.chords,
              getattr(report, "chords_after", None) or report.chords)]
    if report.orphan_chords:
        lines.append("  orphan chord rows removed: %i (song ids %s)" % (
            report.orphan_chords,
            ", ".join(str(i) for i in report.orphan_song_ids)))
    else:
        lines.append("  orphan chord rows removed: 0")
    if report.key_columns_removed:
        lines.append("  key columns removed: %s" %
                     ", ".join(report.key_columns_removed))
    lines.append("  uuids assigned: %i" % report.uuids_assigned)
    return lines


def run(path, output, in_place, name):
    print(path)
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        print("  missing or empty file, nothing to upgrade")
        return False
    file_format = _format_of(path)
    if file_format == compat.FORMAT_V2:
        print("  already the current format, nothing written")
        return True

    if in_place:
        report, backup = upgrade.upgrade_file_in_place(path, name)
        print("  backup: %s" % backup)
        original, result = backup, path
    else:
        if file_format == compat.FORMAT_V1:
            report = _convert_v1_copy(path, output, name)
        else:
            report = upgrade.upgrade_copy(path, output, name)
        original, result = path, output
        print("  written: %s" % output)
    for line in _report_lines(report):
        print(line)

    if file_format == compat.FORMAT_V1:
        print("  (version 1 source: chord conversion is checked by "
              "tools/convert_songbook_v1_to_v2.py)")
        problems = _verify_result_only(result)
    else:
        problems = verify(original, result)
    if problems:
        for problem in problems[:20]:
            print("  PROBLEM: " + problem)
        print("  %i problems" % len(problems))
        return False
    print("  verified: songs and chords match, integrity_check ok, "
          "foreign_key_check empty, uuids unique")
    return True


def _convert_v1_copy(path, output, name):
    if os.path.exists(output):
        raise upgrade.ConversionError("%s already exists." % output)
    source = _open_readonly(path)
    try:
        target = sqlite3.connect(output)
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()
    conn = sqlite3.connect(output)
    try:
        report = compat.convert_connection(conn)
        upgrade.finish_conversion(conn)
    finally:
        conn.close()
    return report


def _verify_result_only(path):
    problems = []
    new = _open_readonly(path)
    try:
        if not upgrade.schema_is_current(new):
            problems.append("schema is not the current one")
        if new.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            problems.append("integrity_check failed")
        if list(new.execute("PRAGMA foreign_key_check")):
            problems.append("foreign_key_check found problems")
        uuids = [r[0] for r in new.execute("SELECT uuid FROM songs")]
        if len(set(uuids)) != len(uuids):
            problems.append("song uuids are not unique")
    finally:
        new.close()
    return problems


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("file")
    parser.add_argument("--output", help="write the upgraded copy here")
    parser.add_argument("--in-place", action="store_true",
                        help="back up FILE and upgrade it")
    parser.add_argument("--name",
                        help="songbook name for the meta table (default: "
                        "the file name without extension)")
    args = parser.parse_args(argv)
    if bool(args.output) == bool(args.in_place):
        parser.error("give exactly one of --output or --in-place")
    if args.output and os.path.abspath(args.output) == os.path.abspath(
            args.file):
        parser.error("--output must be a different file; use --in-place")
    try:
        ok = run(args.file, args.output, args.in_place, args.name)
    except Exception as err:
        print("  FAILED: %s: %s" % (type(err).__name__, err))
        ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
