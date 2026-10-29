# Editing lyrics and what happens to the chords

A chord belongs to one letter of the song text (its character number). When
the text changes, every chord has to follow its letter. All three apps use the
same rule, and run the same cases from `tests/lyric_chord_vectors.json`.

| Platform | Code | Tests |
| --- | --- | --- |
| Desktop (Python) | `lyric_renumber_map` in `src/softchord_text.py` | `src/test_song.py` |
| iOS | `SongLyricChords.renumberMap` | `softChord ViewerTests` |
| Web | `moveChords` in `softChord_web/softchord_text_edit.js` | `softChord_web/tests/text_edit.test.js` |

## The rule

1. Find the longest unchanged beginning (prefix) of the old and new text, and
   the longest unchanged ending (suffix). The suffix is capped so that it never
   overlaps the prefix: `suffix <= min(old length, new length) - prefix`. Without
   the cap, `Hello` to `Helo` counted the second `l` twice and put two chords on
   one letter.
2. A chord in the prefix stays where it is. A chord in the suffix moves by the
   difference in length.
3. A chord on a letter that was deleted or replaced is dropped. Undo brings it
   back (web, see below).
4. Positions are counted in code points, not UTF-16 units, so emoji and other
   characters outside the first plane count as one letter.

A chord on a line break, past the end of the text, or below zero has no letter.
It is not drawn and not copied (all three platforms). Edits treat it by the rule
above like any other chord: a chord on a line break is kept (it is in the unchanged
beginning or ending, unless the edit replaced that line break), but a chord past
the end of the text or below zero is in neither, so **the first edit drops it**.
Such chords only come from a damaged songbook. One consequence on the web: with a
chord past the end, typing a letter and deleting it again after Save still shows
"Changes do not persist", because the first edit already dropped that chord, so
the text is the same but the chords are not.

## Moving a chord by hand

When a chord is dragged or moved with the arrow keys onto a letter that already
has a chord, it jumps over it to the next free letter on the same line, in the
direction it is moving. It never lands on a line break, so two chords never share a
letter.

- Arrow keys: if there is no free letter in that direction, the chord stays.
- Dragging: the direction is where the pointer is going (the letter it was last
  over, to the letter it is over now). If there is no free letter that way, it
  tries the other way; if the line is full it stays.

## Web: Edit text

The pencil button above the song (title "Edit song text") makes the whole song text
editable over the sheet. It works best on a large screen (laptop or desktop). On a
phone the toolbar wraps onto more rows (Save and Discard stay on screen at 320px and
up), and the textarea is never under 16px (see below), but it has been tried only in
a desktop browser with a phone-sized window, not on a real phone.

- The sheet is drawn as always. A see-through textarea lies exactly over it, with
  the same font, size and line height. Only its caret and selection show, so the
  chords stay visible and move while you type.
- While editing, every line keeps room for chords, so lines do not jump when a
  chord appears or goes. This makes the lines a little further apart than in the
  viewer.
- The song is edited as one text. Line endings are normalised to `\n` when the
  text is loaded or pasted (`\r\n` and `\r` become `\n`). Spaces and tabs are kept
  as they are.
- A tab is as wide in the sheet as in the textarea: the next tab stop, a whole
  number of 8 spaces from the start of the line. The sheet draws every letter as a
  box of its own, so the tab's box is given that width (in em, so it follows zoom
  and print size; `fitTabs` in `viewer.js`). The text still holds the tab, and
  chords are numbered as before.
- A letter made of several code points (an accent on its letter, an emoji with a skin
  tone or joiners, a flag, a heart with its variation selector) is one box in the
  sheet, like one letter in the textarea. Chords are still numbered by code point,
  so a chord stored on the accent or on a joiner is drawn over the whole letter.
  This needs `Intl.Segmenter`; without it every code point is a box, as before.
- Opening or leaving the editor keeps the song line that was at the top of the
  screen where it was, and the caret starts on that line, so a long song does not
  jump back to the first line. (Lines get room for chords while editing, so their
  heights change.) After Save or Discard the keyboard focus goes to the Edit button.
- Opening the address of the song that is being edited again does nothing to the
  edit. The sheet and the textarea always show the same draft.
- A screen reader would read the song twice (the sheet and the textarea under it),
  so while editing the sheet has `aria-hidden="true"` and the textarea is labelled
  "Song text".
- Typing stays fast on a long song (about 13 ms a keystroke at 24 000 letters, 316 ms
  before): a chord finds its line by search, the key detection that spells the
  chords is remembered while the chords' roots and types do not change, and only the
  lines that changed are painted again.
- Undo and Redo (Ctrl/Cmd+Z, Ctrl/Cmd+Shift+Z) are the browser's. The editor also
  keeps a list of `{text, chords}` snapshots next to the browser's history. After
  an Undo or Redo, the chords of the snapshot with the same text are put back,
  including chords that were dropped by a deletion. If there is none, the chords
  are moved by the rule above. At most 200 snapshots are kept (each one holds all the
  chords), so after more than 200 edits the oldest are let go: Undo still goes on
  with the browser's text, and the chords then follow their letters, but chords that
  were dropped by those old edits do not come back. While an IME composition is going
  on, the snapshot is taken when it ends.
- **Dragging selected text** inside the textarea (drop it somewhere else) is an
  edit like a cut and a paste: the chords on the moved letters are dropped at the old
  place and are not brought along to the new one. This is the same in the desktop and
  iPhone editors, because the rule only compares the text before and after. Move the
  chords again by hand afterwards if they should go with the letters.
- "Changes do not persist" is shown as soon as the editor opens, before anything is
  typed. When the editor closes it goes again, unless something is kept (see Save)
  or the song is transposed. So Discard, and Save with nothing changed, show no note.
- **Save** keeps the edited text and chords as the song's text for this page
  visit. Viewer, Copy and Print use them afterwards, and "Changes do not
  persist" stays shown. The songbook is never written. **Discard** throws the edit
  away without asking. The edit is also lost when the page goes back to the list,
  opens another song, or is reloaded.
- While editing, Print, the three Copy buttons, Transpose down/up, Reset
  transpose and Edit text are disabled. Zoom stays on, because the textarea and the
  sheet take their size from the same variable.
- The textarea's font is never smaller than 16px. iPhone Safari zooms the whole
  page when a text field under 16px gets focus. The sheet is under 16px below 80%
  zoom (50%, 60%, 70%), so there the textarea is laid out with a 16px font and
  every length of it multiplied by the same ratio, then scaled down (`--boost` in
  `viewer.css`) to cover the sheet. At 80% and up nothing is scaled. Because the
  browser rounds ascent and line height to whole pixels for each font size on its
  own, below 80% a letter of the textarea can sit up to about 1.2px above or below
  the sheet's (it is within 0.33px at 80% and up). Not tried on a real iPhone.
- Escape does nothing while editing (it would otherwise leave the song and lose the
  text). Use Save, Discard or Back.
- Transposition: the text does not depend on the key. The chords of the draft are
  kept as they are stored (not transposed) and shown shifted by the current
  transposition, as on iOS. So a song opened at +2 is edited at +2, and Save
  does not change the key.

### What was and was not checked

The textarea and the sheet are separate elements that have to line up to a
fraction of a pixel. In Chrome this is measured by the browser tests
(`tests/edit_text.browser.test.js`): after each edit, at 100% and 150% zoom, every
letter of the textarea is within 1px of the sheet's letter, and manual sweeps from 50%
to 300% were within about 0.33px across and 0.5px down. Over a very long line the
two drift apart by about 0.003px per letter.

Not tested, and possible to be a little off: Safari and Firefox (different line
box and kerning rules), IME composition beyond a basic check, and a real phone.
Tabs, accented letters, emoji, flags and joiners are tested in Chrome the same
way (at 60%, 100% and 150% zoom for tabs). Kerning and ligatures are switched off in
both layers to keep them equal.

The browser tests need Chrome. Without it they are skipped with a loud warning,
and `SOFTCHORD_REQUIRE_BROWSER=1` makes a missing Chrome a failure (see the README).
