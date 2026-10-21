"""Chord rectangles shared by the editor and by print.

Qt lays out the lyric characters. This module centers each chord on its
anchor character. On-screen painting and PDF/print both use that result.

Paired with softChord Viewer/softChord Viewer/softchord_layout.swift.
"""

from PyQt6 import QtCore


class PlacedChord:
    """One chord and the lyric character it sits on, in editor coordinates."""

    def __init__(self, character_num, chord_text, char_rect, chord_rect):
        self.character_num = character_num
        self.chord_text = chord_text
        self.char_rect = char_rect
        self.chord_rect = chord_rect


class SongLayout:
    """Chord boxes for one painting of a song."""

    def __init__(self, placed):
        self.placed = placed

    @staticmethod
    def place(editor, chords, heights_with_chords, chord_width_of,
              chord_text_of):
        """Place every chord on the editor's current lyric layout.

        heights_with_chords() returns (chords_height, lyrics_height, line_height).
        chord_width_of(text) and chord_text_of(chord) describe one chord.
        """
        chords_height, _lyrics_height, line_height = heights_with_chords()
        placed = []
        for chord in chords:
            text = chord_text_of(chord)
            char_rect, chord_rect = character_and_chord_boxes(
                editor, chord.character_num, text, chords_height, line_height,
                chord_width_of(text))
            placed.append(
                PlacedChord(chord.character_num, text, char_rect, chord_rect))
        return SongLayout(placed)


def character_and_chord_boxes(editor, song_char_num, chord_text, chords_height,
                              line_height, chord_width):
    """Lyric character box, and the chord box centered on it.

    chord_text is None when the character has no chord. Cursor positions
    come from the editor so the boxes match the text Qt is drawing.

    Mirror: softchord_layout.swift SongSheetLayout.drawing, which centers
    each chord on the same anchor with Core Text advances.
    """
    cursor = editor.textCursor()
    cursor.setPosition(song_char_num)
    left_rect = editor.cursorRect(cursor)
    cursor.setPosition(song_char_num + 1)
    right_rect = editor.cursorRect(cursor)

    char_left = left_rect.left()
    char_right = right_rect.right()
    char_width = right_rect.right() - left_rect.left()
    char_height = left_rect.bottom() - left_rect.top()
    char_rect = QtCore.QRectF(left_rect.left(), left_rect.top(), char_width,
                              char_height)

    if chord_text is None:
        return char_rect, None

    chord_top = left_rect.bottom() - line_height
    # Average of the character's left and right edges.
    chord_middle = (char_left + char_right) // 2
    chord_left = chord_middle - (chord_width / 2.0)
    chord_rect = QtCore.QRectF(chord_left, chord_top, chord_width,
                               chords_height)
    return char_rect, chord_rect
