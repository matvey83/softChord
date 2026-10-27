# Songbook file format (version 2)

A `.songbook` file is a SQLite database with `PRAGMA user_version = 2`.
`src/songbook.sql` is the schema the editor creates new files from. The
chord string grammar is in [chord_format.md](chord_format.md).

## Tables

```
songs(id INTEGER PRIMARY KEY,
      uuid TEXT NOT NULL UNIQUE,
      number INTEGER,
      title TEXT NOT NULL DEFAULT '',
      subtitle TEXT NOT NULL DEFAULT '',
      text TEXT NOT NULL DEFAULT '',
      updated_at INTEGER NOT NULL)

song_chord_link(id INTEGER PRIMARY KEY,
                song_id INTEGER NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
                character_num INTEGER NOT NULL,
                chord TEXT NOT NULL)
  + INDEX idx_song_chord_link_song_id ON song_chord_link(song_id)

meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)

deleted_songs(uuid TEXT PRIMARY KEY, deleted_at INTEGER NOT NULL)
```

### songs

- `id` is local to the file. It can differ between copies of a song.
- `uuid` identifies the song across files and devices. It is a lowercase
  hyphenated UUID version 4, generated once when the song is created or
  imported, and never changed. Deleting a song and undoing the delete keeps it.
  Appending another songbook to this one gives the appended songs new uuids.
- `number` is the song number shown in the list. It is nullable and not unique.
- `updated_at` is Unix epoch seconds in UTC. It is set when the song is created
  and whenever a save changes the title, subtitle, number, text or chords. A
  save that changes nothing leaves it alone.
- There is no stored key. The key is not part of the format.

### song_chord_link

One row per chord. `character_num` is the position of the lyric character the
chord sits on, `chord` is the chord string. Text that is not a chord is kept
as it is and shown in red, cut to its first 7 characters (see
[chord_format.md](chord_format.md)). Rows are removed with their song
(`ON DELETE CASCADE`). The editor turns on `PRAGMA foreign_keys` and also
deletes the rows itself.

### meta

Key/value rows written when the editor creates a songbook:

| key | value |
| --- | --- |
| `format_version` | `'2'` |
| `songbook_uuid` | a UUID version 4, created once, never changed |
| `name` | the file name without the extension |

Viewers ignore `meta`. Save As keeps `songbook_uuid`.

### deleted_songs

Tombstones for songs deleted in the editor: the song `uuid` and the UTC epoch
seconds of the delete. The tombstone is written in the same transaction as the
delete and removed again if a song with that uuid is inserted (undo). Viewers
ignore the table.

## Older files

The editor opens older files and upgrades them (`src/softchord_v1_compat.py`,
`src/softchord_songbook_upgrade.py`). It detects the old layouts by their
schema, not by `user_version`.

- Version 1 (`user_version` 0): separate note, chord type, bass, marker and
  parentheses columns, plus `notes` and `chord_types` tables. Converted
  straight to the schema above. Backup: `<name>.songbook.v1.bak`.
- Early version 2: chord strings, but no `uuid`, `updated_at`, `meta` or
  `deleted_songs`, and `songs` still had `key_note_id`, `key_is_major` and
  `alt_key_note_id`. The upgrade drops the key columns, replaces NULL title,
  subtitle and text with `''`, assigns a uuid to every song, sets `updated_at`
  to the upgrade time, deletes chord rows whose song does not exist, adds the
  foreign key and index, and creates `meta` and `deleted_songs`. Backup:
  `<name>.songbook.pre-uuid.bak`.

Both backups are made with the SQLite backup API before anything changes and
are never overwritten (a numbered name is used instead). If the file cannot be
written, the editor opens an upgraded temporary copy titled
"(converted copy, not saved)" and offers Save As. A read-only file that is
already current opens read-only.

To upgrade a file without the editor:
`python3 tools/upgrade_songbook_v2.py FILE --output NEW_FILE`.

The iPhone app and the web viewer read the current schema only and ignore
`meta` and `deleted_songs`.
