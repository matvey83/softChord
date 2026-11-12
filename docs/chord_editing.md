# Web: Edit chords

A song opens already on Chords, ready to edit. The toolbar's **Chords** and
**Lyrics** switch (Ctrl/Cmd+K and Ctrl/Cmd+L) chooses which part of the same
draft is edited. An empty new song starts on Lyrics. A pasted, imported or
existing song starts on Chords, including an existing song whose text is empty.
The web viewer has no new, paste or import button, so a song opened from the
list is the existing-song path (`segmentForOpen`).

The draft is for this page visit only. "Changes do not persist" is shown when
the draft differs from the last save, or when this page is holding a copy the
file does not have. A clean open shows no note. **Save** writes the draft into
this page's memory, stays in edit, and switches to Chords. **Discard** reloads
the last save and stays on the same segment. Neither asks. The songbook file is
never written. Copy, Print, Zoom, Undo and Redo stay shown. Transpose, and chord
Add and Delete, are shown on Chords and hidden on Lyrics. Discard and Save are
shown only when the draft is dirty. Undoing back to the last save hides them
and stays in edit. Transpose, like a text or chord edit, dirties that same
draft (a song opened at +2 is edited at +2; chords are stored untransposed, as
in [lyric_editing.md](lyric_editing.md)). Save keeps the key for this page
visit. Discard puts it back. Transposing back to the kept key, or a whole
octave away, is no change.

## Mouse and touch

- **Drag any chord** to move it. There is no select step: press on a chord and
  move more than 4px. The chord follows the pointer letter by letter, can go to
  another line, and uses the same jump rule as the desktop and iPhone editors when
  the letter under it already has a chord (see [lyric_editing.md](lyric_editing.md)).
  The chord keeps the spot where it was grabbed, so grabbing its right end does not
  make it jump. Near the top or bottom edge of the song area the area scrolls.
- Escape during a drag (or a cancelled touch) puts the chord back. One drag is one
  undo step.
- **Hover** (mouse and trackpad only, `@media (hover: hover)`): the chord under the
  pointer gets a light-blue pill with a thin outline and a grab cursor, and its
  letter a faint grey box. Touch screens show no hover.
- **Click** a chord or a letter to select it (a blue box on the letter). Double-click
  (or, on touch, tap the selected letter again) to type a chord.
- Chords that are not recognized (shown in red) can be selected, moved, edited and
  deleted like the others.
- Chords stick to whole letters: an accented letter, emoji or flag made of several
  code points takes a chord only on its first code point.

## Keyboard (the song area focused)

| Key | Does |
| --- | --- |
| A–G | Put that major chord on the selected letter (replaces a chord there) |
| m | Toggle minor of the selected chord |
| Left / Right | Move the chord along its line (jump rule), up to 10 letters past its end (see [Room right of a line](#room-right-of-a-line)); with no chord on the letter they do nothing |
| Delete / Backspace | Delete the chord |
| Enter / F2 | Type a chord (see below) |
| Ctrl/Cmd+Z, Shift+Ctrl/Cmd+Z (also Ctrl+Y) | Undo, Redo |
| Escape | Cancel a drag, else clear the selection. It never leaves the mode |

Up and Down do nothing in this mode (as in the desktop editor, where they no longer
transpose the selected chord), and neither do Left and Right on a letter with
no chord: the browser gets those keys and can scroll the page. The selection moves
only by click or tap. Letters with Ctrl, Cmd or Alt are left to the browser. The toolbar has the same
actions: Add/Edit chord, Delete chord, Undo, Redo. A screen reader hears what was
selected or changed through a polite live region.

## Typing a chord

One text field in a small panel by the letter (a bottom sheet on screens up to
760px; its font is 16px so iPhone Safari does not zoom). It starts with the chord as
shown, or "C" on an empty letter. While the text is not a chord the field is red,
OK is disabled and the note says "Not a chord. Start with a note from A to G.";
otherwise it says "Shown as X" with the chord as it will be drawn. Enter is OK,
Escape is Cancel. A chord typed in a transposed song is stored shifted back, so it
shows as typed. The chord parser is lenient (the same one as for songbooks): text
like "Hx" counts as a chord when it starts with a known note.

## Leaving with changes

Back, another song's address, or the browser's Back button with a dirty draft
ask "Do you want to save the changes you made to “title”?" with **Save** (the
default), **Don't Save** and **Cancel**. This is the same on Lyrics. Escape in
that dialog is Cancel. Escape anywhere else clears a lyric selection, or on
Chords cancels a drag else clears the chord selection. It never discards and
never leaves the song. Save keeps the edit for this page visit and then leaves;
the next song opens on Chords. Don't Save drops the unsaved draft (a Save
already stored for this visit stays) and leaves. Cancel stays. A draft undone
back to the last save does not ask. A page reload or closing the tab does not
ask yet (no `beforeunload`) and loses this page's edits. Because `hashchange`
comes after the address changed, the address is put back while the question is
open and set again on Don't Save or Save, which leaves one extra history entry.

## Not built (yet)

Selecting several chords (marquee or Shift-click), and Alt-drag to copy a chord.

## Checked and not checked

Tested in headless Chrome (`tests/edit_chords.browser.test.js`, mouse and emulated
touch, desktop width, 375px and 320px), and the pure rules in
`tests/chord_edit.test.js`. A 600-chord song moves a chord in under 1 ms a step
(median). Not tried: Safari, Firefox, a real iPhone or Android phone, IME input in
the chord field.

## Room right of a line

The same in all three apps (desktop `chord_room` and `tidy_chord_room` in
`softchord_text.py`, web `withRoom` and `tidied` in `softchord_chord_edit.js`,
iPhone `SongLyricChords.withRoom`, `tidied` and `movedWithRoom`):

- A chord can sit up to **10 letters right of the last letter of its line**
  (the last letter that is not a space). It sits there on real spaces: dragging
  a chord past the end, or moving it right with the arrow key, gives the line
  the spaces it needs, so a chord is always on a letter of its own line (never on
  the line break, never past the end of the text). The 11th Right does nothing.
- **Tidying.** After a move or a delete, each line the chord left or went to
  loses the spaces at its end past its last chord. A line keeps spaces only up
  to its last chord, so moving a chord back onto the words, or deleting it, takes
  its spaces away again. Lines the change did not touch keep their trailing
  spaces, and so do a line of only spaces and a tab. The text and the chords
  change together, so one Undo puts both back.
- Positions count Unicode code points, so Cyrillic and emoji lyrics pad and
  move the same way (an emoji like 🎵 is one letter).
- Hardware keyboard on iPhone/iPad: in Chords, Left and Right move the selected
  chord the same way, one undo step a press. With no chord on the selected letter
  they do nothing.
- Desktop, several chords selected (rectangle): Left and Right move them all,
  each with room right of its line, and Delete deletes them all. Both tidy the
  lines they touched and are one undo step. (The web and iPhone editors cannot
  select several chords.)
- **ChordPro.** Export writes a chord on a trailing space as `[G] ` before that
  space. Desktop import (the only app that imports ChordPro) takes the spaces off
  the end of each line, then gives a line back the spaces up to its last chord,
  so the chord comes back on the same space.
- **Remove Trailing Spaces** (desktop, Edit menu) is separate: it takes every
  trailing space off every line of the selected songs, and a chord that sat on
  one of those spaces is **deleted**, not moved (one songbook undo step brings it
  back).

## Desktop: Edit Chords…

A song opened in the desktop app is only viewed: nothing can be selected or
dragged, and the chord keys, double-click and paste do nothing. Chords can be
selected (click, rectangle, arrow keys) only in Edit Chords…. **Edit > Edit Chords…** (⌘K) or
the chords button starts an edit; **Edit Text…** (⌘L) is the same for the text
(see [lyric_editing.md](lyric_editing.md)). While editing, **Discard** and **Save**
buttons are shown right of the Edit Text button, and the Edit menu has Save Changes (⌘S) and
Discard Changes (Esc).

- The edit is a draft. The songbook is written only on Save. Title, number,
  subtitle and transpose (Reset too) are part of the draft and go back on Discard.
  The song list keeps showing the saved title and number (with the dot), and does
  not sort or filter by the draft, until Save.
- Changing one of those while viewing is a change as well: transposing, Reset
  transpose, or typing in the title, number or notes field starts a draft, and
  Save and Discard appear (the song stays in viewing, nothing becomes
  selectable). Edit Chords… or Edit Text… after it go on with the same draft.
  Transposing back to the key the song had (also a whole octave, or Reset), or
  typing the title back, is no change: Save and Discard go away and the draft
  ends. A chord typed as A# that came back as B♭ is shown as A# again.
- Undo and redo cover only the edit, and are dropped on Save or Discard. A change
  undone back to the start counts as no change. Nothing of a song is left on the
  songbook's own undo stack, so Undo while viewing never writes a song (only
  songbook steps such as delete, import, renumber and remove trailing spaces are
  undone there).
- With changes, the window shows it is modified and the song's row in the list
  has a • after the title.
- Esc during a chord drag puts the chord back. Otherwise it discards, asking
  first only if something changed. The Discard button does not ask.
- Print, export (PDF, text, ChordPro) and copy use the draft and do not save it.
- Choosing another song, the other kind of edit, closing the window, Quit, a new,
  opened, closed or saved-as songbook, opening one from the Finder, appending a
  songbook, a new, imported or pasted song, delete, renumber, remove trailing
  spaces and the song list's menu ask "Do you want to save the changes…?" with
  Save (the default), Don't Save and Cancel (Esc). On Cancel the edited song stays
  selected. An edit without changes ends without asking.
- Typing in the filter keeps the edit, even when the filter hides the song.
- At logout or shutdown, where no dialog can be shown, the edit is saved.

Tested offscreen (`TestSaveAndDiscard` in `src/test_song.py`, the dialog mocked).
Not tried by hand: a real ⌘Q, logout and shutdown, and the dialog as a sheet.

## iPhone: Chords and Lyrics

The song opens already editing, with a Chords or Lyrics switch in the toolbar.
There is no separate Edit Text… or Edit Chords… mode. Save and Discard show when
the draft is dirty (Discard first). Save keeps the edit for this run of the app
(the songbook file is never written) and stays in edit; Discard throws the
changes away and stays on the same segment. Back, with a dirty draft, asks Save,
Don't Save, or Cancel.

- A transpose is a change too. Discard and Save show when the draft is dirty
  (on Chords they sit with the transpose buttons; Lyrics hides transpose, so
  they are not next to it). Save keeps the key for this run, so the song opens
  in it again; Discard goes back to the kept key. Back at that key, or a whole
  octave away, is no change. Reset transpose goes to the songbook's key, so
  after Save it is a change.
- The note at the bottom says "Changes do not persist" while the draft is
  unsaved, after a saved edit, or when the song is shown in another key than
  the songbook's. The songbook file is never written.
- Copy, Copy as image, Print and Add to Photos use the song as it is shown,
  including an unsaved draft.
- Undo and Redo work in both Chords and Lyrics, and step through the text and
  chord changes of the draft: a move (one drag is one step), a typed chord, a
  delete, and lyric edits. They are dropped on Save and Discard. Undone back to
  the start is no change.
