# Known issues

- Desktop: Undo cannot cross a Save. Save drops the draft's undo steps (by design).

- iOS: there is no New, Paste, or Import song UI. `SongEditSegment.forOpen` opens an empty new song on Lyrics and everything else on Chords, and that helper is unit-tested, but the app only opens existing songs, so they always start on Chords.
- iOS: title, number, and notes are not editable, so they cannot dirty the draft the way they do on desktop.
- iOS: the song toolbar wraps onto another row instead of putting overflow items in a "..." menu. `SongShareMenu` can include Chords and Lyrics, but the song page does not present that menu, so the segment can only be changed from the toolbar.
- iOS: on Lyrics, the zoom buttons scale the lyric font, but a pinch does not zoom, and the sheet does not fit-to-width. Those both work on Chords.

- iOS: swipe-back on a dirty draft needs a device check. The nav bar is hidden, which should disable swipe-back, but that has not been verified on a device. If swipe-back still works, a dirty draft is lost silently.
- iOS: every keystroke is its own undo step.
- iOS: `lyricDraftChanged` treats retyping back to a history entry as undo or redo.
- iOS: tapping Lyrics is ignored while a switch waits for the keyboard.
- iOS: `commitEdit` can save `steps:0` and lose the key.
- iOS: Lyrics now zooms with the toolbar buttons, fit-to-width applies on Chords, and Copy and Print use the unsaved draft.
