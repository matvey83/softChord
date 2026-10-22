"""Chord rectangles shared by the editor and by print.

QtDocumentLayout is the Qt document adapter. A new lyric renderer
replaces that class. SongLayout centers each chord on the anchor
character it reports. On-screen painting and PDF/print both use that.

Paired with softChord Viewer/softChord Viewer/softchord_layout.swift.
"""

from PyQt6 import QtCore, QtGui


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
    def place(layout, chords, heights_with_chords, chord_width_of,
              chord_text_of):
        """Place every chord using the layout's lyric positions.

        heights_with_chords() returns (chords_height, lyrics_height, line_height).
        chord_width_of(text) and chord_text_of(chord) describe one chord.
        """
        chords_height, _lyrics_height, line_height = heights_with_chords()
        placed = []
        for chord in chords:
            text = chord_text_of(chord)
            char_rect, chord_rect = layout.character_and_chord_boxes(
                chord.character_num, text, chords_height, line_height,
                chord_width_of(text))
            placed.append(
                PlacedChord(chord.character_num, text, char_rect, chord_rect))
        return SongLayout(placed)


class QtDocumentLayout:
    """Lyric positions and painting that go through a QTextDocument.

    TODO: The web sheet should copy SongSheetLayout's measurements. This
    Qt adapter stays until a new lyric renderer replaces it.

    This is the only place that asks Qt for cursor rectangles, hit
    testing, document drawing, and the document's bounding size.
    """

    def __init__(self, editor):
        self.editor = editor

    @staticmethod
    def content_size(document):
        """Width and height of the laid-out text, in document units."""
        rect = document.documentLayout().frameBoundingRect(document.rootFrame())
        return rect.right(), rect.bottom()

    def character_and_chord_boxes(self, song_char_num, chord_text,
                                  chords_height, line_height, chord_width):
        """Lyric character box, and the chord box centered on it.

        chord_text is None when the character has no chord. Cursor positions
        come from the editor so the boxes match the text Qt is drawing.

        Mirror: softchord_layout.swift SongSheetLayout.drawing, which centers
        each chord on the same anchor with Core Text advances.
        """
        cursor = self.editor.textCursor()
        cursor.setPosition(song_char_num)
        left_rect = self.editor.cursorRect(cursor)
        cursor.setPosition(song_char_num + 1)
        right_rect = self.editor.cursorRect(cursor)

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

    def draw_lyrics(self, painter, apply_scroll):
        """Draw the editor's lyric document.

        On screen, shift by the scroll bars so the lyrics line up with the
        chord boxes, which are already in viewport coordinates. Exporting
        paints at the document origin.
        """
        editor = self.editor
        if apply_scroll:
            scroll_x = editor.horizontalScrollBar().value()
            scroll_y = editor.verticalScrollBar().value()
            painter.translate(-scroll_x, -scroll_y)

        editor.document().drawContents(painter,
                                      QtCore.QRectF(0.0, 0.0, 10000.0, 10000.0))

        if apply_scroll:
            painter.translate(scroll_x, scroll_y)

    def caret_at(self, x, y):
        """Character position under a point, and the caret rectangle there."""
        cursor = self.editor.cursorForPosition(QtCore.QPoint(int(x), int(y)))
        rect = self.editor.cursorRect(cursor)
        return (cursor.position(), cursor.atBlockStart(), cursor.atBlockEnd(),
                rect)

    @staticmethod
    def fill(song, session):
        """Make song.doc show song.text, with space above chord lines."""
        if song.doc is None:
            song.doc = QtGui.QTextDocument()
        song.doc.setDefaultFont(session.lyrics_font)
        ignoring = session.ignore_song_text_changed
        session.ignore_song_text_changed = True
        try:
            if song.doc.toPlainText() != song.text:
                song.doc.setPlainText(song.text)
            QtDocumentLayout._apply_margins(song, session)
        finally:
            session.ignore_song_text_changed = ignoring

    @staticmethod
    def apply_margins(song, session):
        """Space lines that have chords. The lyric text is left as it is."""
        ignoring = session.ignore_song_text_changed
        session.ignore_song_text_changed = True
        try:
            QtDocumentLayout._apply_margins(song, session)
        finally:
            session.ignore_song_text_changed = ignoring

    @staticmethod
    def _apply_margins(song, session):
        # Block format changes notify the editor. Callers hold
        # ignore_song_text_changed so that is not treated as a lyric edit.

        chords_by_char = {}
        for chord in song._chords:
            chords_by_char[chord.character_num] = True

        chords_height, lyrics_height, line_height = session.getHeightsWithChords(
        )
        with_chords_top_margin = line_height - lyrics_height

        with_chords_top_margin *= 1.03  # Add some spacing between lines (that have chords

        # The first line is always given the chord gap. That is usually true,
        # and it avoids a few layout problems when it is not.
        root_frame = song.doc.rootFrame()
        frame_format = root_frame.frameFormat()
        frame_format.setTopMargin(with_chords_top_margin +
                                  session.doc_editor_offset)
        root_frame.setFrameFormat(frame_format)

        block = song.doc.begin()

        with_chords_format = block.blockFormat()
        with_chords_format.setTopMargin(with_chords_top_margin)
        with_chords_format.setLeftMargin(session.doc_editor_offset)

        without_chords_format = block.blockFormat()
        without_chords_format.setTopMargin(0.0)
        without_chords_format.setLeftMargin(session.doc_editor_offset)

        line_start_char = 0
        for line_text in song.doc.toPlainText().split("\n"):
            line_end_char = line_start_char + len(line_text)

            line_has_chords = False
            for chord_num in chords_by_char.keys():
                if chord_num >= line_start_char and chord_num <= line_end_char:
                    line_has_chords = True
                    break

            cursor = QtGui.QTextCursor(block)
            if line_has_chords:
                cursor.setBlockFormat(with_chords_format)
            else:
                cursor.setBlockFormat(without_chords_format)

            if block == song.doc.end():
                break

            block = block.next()
            line_start_char += len(line_text) + 1  # end-of-line character

    @staticmethod
    def release_editor_document(editor, song):
        """Keep a copy of the editor's document on the song, then clear it.

        The editor and the song share that document. Setting another
        document without clearing this one crashes on Windows.
        """
        prev_doc = editor.document()
        song.doc = prev_doc.clone()
        prev_doc.clear()

    @staticmethod
    def show_document(editor, document):
        """Show this document in the editor."""
        editor.setDocument(document)
