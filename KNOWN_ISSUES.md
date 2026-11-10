# Known issues

- Desktop: Undo cannot cross a Save. Save drops the draft's undo steps (by design).

- iOS: there is no New, Paste, or Import song UI. `SongEditSegment.forOpen` opens an empty new song on Lyrics and everything else on Chords, and that helper is unit-tested, but the app only opens existing songs, so they always start on Chords.
- iOS: title, number, and notes are not editable, so they cannot dirty the draft the way they do on desktop.
- iOS: the song toolbar wraps onto another row instead of putting overflow items in a "..." menu. `SongShareMenu` can include Chords and Lyrics, but the song page does not present that menu, so the segment can only be changed from the toolbar.
- iOS: on Lyrics, the zoom buttons scale the lyric font, but a pinch does not zoom, and the sheet does not fit-to-width. Those both work on Chords.
