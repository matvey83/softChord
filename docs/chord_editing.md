# Web: Edit chords

The button next to the pencil (title "Edit Chords…") opens the chord editor of
the web viewer. It is a second editing mode beside Edit text: only one of them is
open at a time, and the other one's button is disabled until Save or Discard.

Like Edit text it edits a draft of the song for this page visit only. "Changes do
not persist" is shown as soon as the mode opens. **Save** keeps the draft as the
song's chords (Viewer, Copy and Print use them afterwards), **Discard** throws it
away. The songbook is never written. While the mode is open Print, the Copy buttons,
Transpose down/up, Reset transpose and Edit text are disabled, so the key cannot
change under the draft (a song opened at +2 is edited at +2; chords are stored
untransposed, as in [lyric_editing.md](lyric_editing.md)). A transpose made
before the mode opened is part of the edit: Save keeps it, Discard puts it back (a
transpose while viewing shows Save and Discard as well, see lyric_editing.md).

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
| Left / Right | Move the chord along its line (jump rule); with no chord on the letter they do nothing |
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

Back, another song's address, or the browser's Back button with a draft that differs
from the song as opened ask "Discard changes?" (Keep editing is the default, Escape
keeps editing). This is the same for Edit text. A draft that was changed and undone
back to the start does not ask. A page reload or closing the tab does not ask yet
(no `beforeunload`). Because `hashchange` comes after the address changed, the
address is put back while the question is open and set again on Discard, which
leaves one extra history entry.

## Not built (yet)

Selecting several chords (marquee or Shift-click), and Alt-drag to copy a chord.

## Checked and not checked

Tested in headless Chrome (`tests/edit_chords.browser.test.js`, mouse and emulated
touch, desktop width, 375px and 320px), and the pure rules in
`tests/chord_edit.test.js`. A 600-chord song moves a chord in under 1 ms a step
(median). Not tried: Safari, Firefox, a real iPhone or Android phone, IME input in
the chord field.

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

## iPhone: Edit Text… and Edit Chords…

The song page's ⋯ menu has Edit Text… and Edit Chords…. While editing, Discard and
Save show under the transpose buttons (Discard first). Save keeps the edit for this
run of the app (the songbook file is never written); Discard throws it away. Back
does not ask.

- A transpose while viewing is a change too: Discard and Save show next to the
  transpose buttons. Save keeps the key for this run, so the song opens in it again;
  Discard goes back to the kept key. Back at that key, or a whole octave away, is no
  change. Reset transpose goes to the songbook's key, so after Save it is a change.
- An edit opened after a transpose takes it in: Save keeps both, Discard puts both
  back.
- The note at the bottom says "Changes do not persist" while something is not
  saved, and "Not written to the songbook" for a saved edit or transpose (with
  "Transpose does not persist." when a saved edit is shown in a key not saved).
- Copy, Copy as image and Add to Photos copy the song as it is shown.
- In Edit Chords…, Undo and Redo (under Edit chord and Delete chord) step through
  the chord changes of the edit: a move (one drag is one step), a typed chord, a
  delete. They are dropped on Save and Discard. Undone back to the start is no
  change.
