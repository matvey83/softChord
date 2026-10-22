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


class ChordGapDocumentLayout(QtGui.QAbstractTextDocumentLayout):
    """Line positions for one lyric document.

    The empty space above a chord line is added here. A block margin would
    leave the same space, and it would also be an undo step. The text
    editor would then undo the space before the letter a chord sits on.
    """

    def __init__(self, document):
        self._top = 0.0
        self._line_gap = 0.0
        self._left = 0.0
        self._chord_blocks = set()
        self._by_position = {}
        self._size = QtCore.QSizeF()
        self._in_relayout = False
        super().__init__(document)

    def set_chord_gap(self, top, line_gap, left, chord_block_numbers):
        """Space above the first line, and above later lines that have chords."""
        self._top = top
        self._line_gap = line_gap
        self._left = left
        self._chord_blocks = set(chord_block_numbers)
        self._relayout()

    def _relayout(self):
        if self._in_relayout:
            return
        self._in_relayout = True
        try:
            self._rebuild()
        finally:
            self._in_relayout = False
        self.update.emit(QtCore.QRectF(0.0, 0.0, self._size.width(),
                                       self._size.height()))
        self.documentSizeChanged.emit(self._size)

    def _rebuild(self):
        doc = self.document()
        margin = doc.documentMargin()
        option = doc.defaultTextOption()
        font = doc.defaultFont()
        y = self._top
        max_right = margin
        by_position = {}
        block = doc.begin()
        while block.isValid():
            # The first line's gap is the space above the whole song.
            # Qt ignores a top margin on that line, so this does too.
            if (block.blockNumber() != 0
                    and block.blockNumber() in self._chord_blocks):
                y += self._line_gap

            text_layout = block.layout()
            text_layout.clearLayout()
            text_layout.setFont(font)
            text_layout.setTextOption(option)
            text_layout.beginLayout()
            line_y = 0.0
            natural = 0.0
            while True:
                line = text_layout.createLine()
                if not line.isValid():
                    break
                line.setLineWidth(100000.0)
                line.setPosition(QtCore.QPointF(self._left, line_y))
                # Same line box Qt's own layout uses, so the caret stays put.
                line.setLeadingIncluded(True)
                natural = max(natural, self._left + line.naturalTextWidth())
                line_y += line.height()
            text_layout.endLayout()
            if line_y == 0.0:
                line_y = QtGui.QFontMetricsF(font).height()

            rect = QtCore.QRectF(margin, y, natural, line_y)
            text_layout.setPosition(rect.topLeft())
            by_position[block.position()] = rect
            max_right = max(max_right, margin + natural)
            y += line_y
            block = block.next()

        self._by_position = by_position
        self._size = QtCore.QSizeF(max_right + margin, y + margin)

    def documentChanged(self, position, charsRemoved, charsAdded):
        self._relayout()

    def draw(self, painter, context):
        doc = self.document()
        block = doc.begin()
        while block.isValid():
            rect = self.blockBoundingRect(block)
            clip = context.clip
            if clip.isValid() and not rect.intersects(clip):
                block = block.next()
                continue

            text_layout = block.layout()
            selections = []
            block_pos = block.position()
            block_length = block.length()
            for selection in context.selections:
                start = selection.cursor.selectionStart() - block_pos
                end = selection.cursor.selectionEnd() - block_pos
                if start >= block_length or end <= 0:
                    continue
                text_range = QtGui.QTextLayout.FormatRange()
                text_range.start = max(0, start)
                text_range.length = min(block_length, end) - text_range.start
                text_range.format = selection.format
                selections.append(text_range)

            # draw() adds the position already stored on the layout.
            text_layout.draw(painter, QtCore.QPointF(0.0, 0.0), selections, clip)
            cursor_pos = context.cursorPosition
            if block_pos <= cursor_pos < block_pos + block_length:
                text_layout.drawCursor(painter, QtCore.QPointF(0.0, 0.0),
                                       cursor_pos - block_pos)
            block = block.next()

    def hitTest(self, point, accuracy):
        doc = self.document()
        if not self._by_position:
            self._relayout()

        # The gap above a line belongs to that line. A click on the chord
        # sits in the gap, and the caret has to land on the lyric under it.
        chosen = None
        chosen_rect = None
        block = doc.begin()
        while block.isValid():
            rect = self._by_position.get(block.position())
            if rect is None:
                break
            chosen = block
            chosen_rect = rect
            if point.y() < rect.bottom():
                break
            block = block.next()
        if chosen is None:
            return -1

        text_layout = chosen.layout()
        if text_layout.lineCount() == 0:
            return chosen.position()
        relative_y = point.y() - chosen_rect.top()
        line = text_layout.lineAt(0)
        for index in range(text_layout.lineCount()):
            candidate = text_layout.lineAt(index)
            line = candidate
            if relative_y < candidate.y() + candidate.height():
                break
        x_on_line = point.x() - chosen_rect.left() - line.x()
        exact = accuracy == QtCore.Qt.HitTestAccuracy.ExactHit
        if exact and (x_on_line < 0.0 or x_on_line > line.naturalTextWidth()
                      or point.y() < chosen_rect.top()
                      or point.y() > chosen_rect.bottom()):
            return -1
        return chosen.position() + line.xToCursor(x_on_line)

    def pageCount(self):
        return 1

    def documentSize(self):
        return self._size

    def frameBoundingRect(self, frame):
        return QtCore.QRectF(QtCore.QPointF(0.0, 0.0), self._size)

    def blockBoundingRect(self, block):
        if block.position() not in self._by_position and not self._in_relayout:
            self._relayout()
        return self._by_position.get(block.position(), QtCore.QRectF())


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
        # Callers hold ignore_song_text_changed. Replacing the layout notifies
        # the editor, and that notification is not a lyric edit.

        if song.doc is None:
            return

        chords_by_char = {}
        for chord in song._chords:
            chords_by_char[chord.character_num] = True

        _chords_height, lyrics_height, line_height = session.getHeightsWithChords(
        )
        # A little air between a chord and the lyric line under it.
        chord_gap = (line_height - lyrics_height) * 1.03

        # The first line always gets the gap. That is usually true, and it
        # avoids a few layout problems when it is not.
        chord_blocks = set()
        block = song.doc.begin()
        line_start_char = 0
        while block.isValid():
            line_end_char = line_start_char + len(block.text())
            for chord_num in chords_by_char:
                if line_start_char <= chord_num <= line_end_char:
                    chord_blocks.add(block.blockNumber())
                    break
            line_start_char = line_end_char + 1
            block = block.next()

        layout = song.doc.documentLayout()
        if not isinstance(layout, ChordGapDocumentLayout):
            layout = ChordGapDocumentLayout(song.doc)
            song.doc.setDocumentLayout(layout)
        # The document owns the C++ layout. Keep the Python object too.
        song.doc._softchord_layout = layout
        layout.set_chord_gap(chord_gap + session.doc_editor_offset, chord_gap,
                             session.doc_editor_offset, chord_blocks)

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
