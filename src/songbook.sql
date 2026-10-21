-- Current songbook schema.
-- Old files may also have key_note_id, key_is_major, and alt_key_note_id
-- on songs. Readers ignore those columns.

CREATE TABLE songs (
    id INTEGER PRIMARY KEY,
    number INTEGER,
    text TEXT,
    title TEXT,
    subtitle TEXT
);

CREATE TABLE song_chord_link (
    id INTEGER PRIMARY KEY,
    song_id INTEGER,
    character_num INTEGER,
    note_id INTEGER,
    chord_type_id INTEGER,
    bass_note_id INTEGER,
    marker TEXT,
    in_parentheses INTEGER
);
