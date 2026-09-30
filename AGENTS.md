# softChord

## Songbooks

Repository `.songbook` files are production song libraries. Do not open, write, import into, or commit them during development.

- Tests use `open_empty_temp_songbook`, or a copy under a temp directory, as `src/softchord_test.py` does. Never pass a repository `.songbook` path to `setCurrentSongbook`.
- To run the app by hand, copy a songbook to a temp file first. Do not launch `start_softChord.py` or `src/softchord.py` on a repository songbook.
- Do not `git add` a `.songbook`, and do not revert songbook changes, unless asked. A dirty songbook may be real edits.
