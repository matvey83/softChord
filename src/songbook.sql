-- Current songbook schema, format version 2 (PRAGMA user_version = 2).
-- The whole file format is described in docs/songbook_format.md. Each chord is
-- one text string, described in docs/chord_format.md.
-- Version 1 files (user_version 0) had note_id, chord_type_id, bass_note_id,
-- marker and in_parentheses columns, plus notes and chord_types tables.
-- Early version 2 files had no uuid, updated_at, meta or deleted_songs, and
-- songs still had key_note_id, key_is_major and alt_key_note_id columns.
-- The editor upgrades both when it opens them. Viewers read version 2 only.
-- The editor adds the meta rows when it creates a songbook.

CREATE TABLE songs (
    id INTEGER PRIMARY KEY,
    uuid TEXT NOT NULL UNIQUE,
    number INTEGER,
    title TEXT NOT NULL DEFAULT '',
    subtitle TEXT NOT NULL DEFAULT '',
    text TEXT NOT NULL DEFAULT '',
    updated_at INTEGER NOT NULL
);

CREATE TABLE song_chord_link (
    id INTEGER PRIMARY KEY,
    song_id INTEGER NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
    character_num INTEGER NOT NULL,
    chord TEXT NOT NULL
);

CREATE INDEX idx_song_chord_link_song_id ON song_chord_link(song_id);

CREATE TABLE meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE deleted_songs (
    uuid TEXT PRIMARY KEY,
    deleted_at INTEGER NOT NULL
);

PRAGMA user_version = 2;
