# Chord format (songbook format version 2)

A songbook is a SQLite file with `PRAGMA user_version = 2`. The whole file
format is in [songbook_format.md](songbook_format.md). The chord table is:

```
song_chord_link(id, song_id, character_num, chord TEXT)
```

`song_chord_link.chord` is one string per chord. `character_num` is the
position of the lyric character the chord sits on. `notes` and `chord_types`
tables are gone: note names and chord types come from the code.

Version 1 (`user_version` 0) had `note_id`, `chord_type_id`, `bass_note_id`,
`marker` and `in_parentheses` columns instead of `chord`. The desktop editor
converts those files when it opens them (`src/softchord_v1_compat.py`). The
iPhone app and the web viewer read version 2 only.

## Grammar

```
chord   = [ "(" ] [ marker ":" ] root suffix [ "/" bass ] [ ")" ]
root    = A-G [ "♯" | "♭" ]
bass    = A-G [ "♯" | "♭" ]
suffix  = any text without a valid bass note after its last "/"
unknown = "?"
```

* Outer parentheses wrap everything: `(1:Am7/G)`.
* `marker` is the text before the first colon. Existing data only has `1` and `2`.
* The editor writes `♯` and `♭`. `#` and `b` are read as the same notes.
* Suffix examples: empty (major), `m`, `sus4`, `M7`, `m7`, `7`, `9`, `11`,
  `6`, `m6`, `°`, `°7`, `aug`. Alternative names (`sus`, `s4`, `maj7`, `2`,
  `(7)`, `dim`, `dim7`) are read and written as the printed type.
* An unknown chord (no usable root) is written as `?`, or as its original text.

## Tolerant parser

Every reader parses with the same layers and never fails. The shared test
file `tests/chord_vectors.json` is run by the Python, Swift and JS tests.

1. Trim whitespace. Strip outer parentheses. Strip the marker (text before the
   first colon). Split off a bass: the text after the last `/` counts only if
   it is exactly a note name, otherwise the slash stays in the suffix.
2. The root must be `A` to `G` with an optional `#`, `b`, `♯` or `♭`. Look-alike
   Russian letters (`А В С Е Н`) and German `H` are read as `A B C E B`. This
   applies to the root and the bass only, not to the suffix.
3. A suffix that exactly matches a known type (or alternative name) is that
   type. Any other suffix is still a chord. Its base quality is minor if it
   starts with `m`, `min`, `mi` or `-` (but not `ma`/`maj`), else major.
   **The original suffix text is kept and written back unchanged**, so
   `Cmaj9` opened in an older version is still `Cmaj9` when saved.
4. No valid root means an unknown chord. It is drawn as `?` and keeps its
   original text, which is written back unchanged. `?` is written only when
   the user entered nothing parseable, or typed `?`.

Transposing changes only the root and bass. The suffix is kept as it is. The
base quality is used for key detection and colouring.

The editor keeps the spelling it read (`B♭` or `A♯`). When a chord is moved
to another note, the song's key picks sharps or flats again.
