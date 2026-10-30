"""Songbook session: the open songbook, current song, and editor commands.

Not a QApplication. softchord.App is the process shell and forwards here.
"""

from PyQt6 import QtCore, QtGui, QtWidgets, sip
from PyQt6.QtCore import Qt
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from PyQt6.QtGui import QPageSize
from PyQt6.QtSvg import QSvgGenerator

PageSizeId = QPageSize.PageSizeId
import sys, os
import copy
import math
import platform
import sqlite3
import traceback

from softchord_chords import (
    PREFER_SHARPS,
    PREFER_FLATS,
    PREFER_NEITHER,
    chord_types_list,
    alternative_type_names,
    global_notes_list,
    DetectedKey,
    prefer_from_major_tonic,
    score_key,
    family_score,
    key_label,
    best_detected_key,
    detect_region_start_indices,
    auto_detected_key_labels,
    format_auto_detected_key_text,
    replace_russian_characeters,
    transpose_note,
    convert_chord_from_string,
    parse_chord,
    is_valid_chord_text,
)
from softchord_song import (
    AddChordCommand,
    DeleteChordCommand,
    ReplaceChordCommand,
    DeleteSongsCommand,
    ImportSongsCommand,
    RemoveTrailingSpacesCommand,
    RenumberSongsCommand,
    SongTextSnapshot,
    SongsTableRow,
    SongsTableModel,
    SongsProxyModel,
    SongChord,
    SongChar,
    Song,
    TransposeSongCommand,
    text_has_trailing_spaces,
)
from softchord_store import (
    SongbookStore,
    database_file_was_replaced,
    readonly_database_error,
)
from softchord_layout import QtDocumentLayout, SongLayout
from softchord_text import (chord_room, tidy_chord_room, tidy_moved,
                             line_letter_range, chord_drag_direction, lyric_renumber_map,
                            next_free_character)
from softchord_io import (
    SQLITE_HEADER,
    SONGS_TABLE_SQL,
    SONG_CHORD_LINK_TABLE_SQL,
    chordpro_extensions,
    _normalize_local_path,
    read_import_text_file,
    connect_existing_songbook,
    parse_chord_over_lyrics,
    assign_chord_anchors,
    SongbookIO,
)

# FIXME Make this an option? Or save into the songbook file?
PRINT_SONGBOOK = False

# For Zvuki Neba songbook:
if PRINT_SONGBOOK:
    LYRICS_SIZE = 11  # 14
    CHORDS_SIZE = 7  # 9
else:
    # For full-page printout:
    LYRICS_SIZE = 20  # 14
    CHORDS_SIZE = 12  # 9

CHORDS_COLOR = "BLACK"
CHORDS_COLOR = "BLUE"
# Text in a chord position that is not a chord (the editor will not save it,
# but a songbook made elsewhere can hold it).
UNRECOGNIZED_CHORDS_COLOR = "RED"
# The selection on screen, the same colours as the web app's (#007aff).
SELECTED_LETTER_COLOR = QtGui.QColor(0, 122, 255, 51)  # 20%
SELECTED_CHORD_HALO_COLOR = QtGui.QColor(0, 122, 255, 64)  # 25%
SELECTED_CHORD_LINE_COLOR = QtGui.QColor(0, 122, 255)

if not os.path.basename(sys.executable).lower().startswith("python"):
    exec_dir = os.path.dirname(sys.executable)
else:
    exec_dir = "."

# script_ui_file = os.path.join(exec_dir, "softchord_main_window.ui" )
# chord_dialog_ui_file = os.path.join(exec_dir, "softchord_chord_dialog.ui")
# pdf_dialog_ui_file = os.path.join(exec_dir, "softchord_pdf_dialog.ui")

import softchord_main_window_ui, softchord_chord_dialog_ui, softchord_pdf_dialog_ui
from softchord_toolbar import SongToolbar
from softchord_note import BriefNote

paper_sizes_list = [
    (PageSizeId.Letter, "Letter (8.5 x 11 inches, 216 x 279 mm)"),
    (PageSizeId.Legal, "Legal (8.5 x 14 inches, 216 x 356 mm)"),
    (PageSizeId.A0, "A0 (841 x 1189 mm)"),
    (PageSizeId.A1, "A1 (94 x 841 mm)"),
    (PageSizeId.A2, "A2 (420 x 594 mm)"),
    (PageSizeId.A3, "A3 (297 x 420 mm)"),
    (PageSizeId.A4, "A4 (210 x 297 mm, 8.26 x 11.69 inches)"),
    (PageSizeId.A5, "A5 (148 x 210 mm)"),
    (PageSizeId.A6, "A6 (105 x 148 mm)"),
    (PageSizeId.A7, "A7 (74 x 105 mm)"),
    (PageSizeId.A8, "A8 (52 x 74 mm)"),
    (PageSizeId.A9, "A9 (37 x 52 mm)"),
    (PageSizeId.B0, "B0 (1030 x 1456 mm)"),
    (PageSizeId.B1, "B1 (728 x 1030 mm)"),
    (PageSizeId.B2, "B2 (515 x 728 mm)"),
    (PageSizeId.B3, "B3 (364 x 515 mm)"),
    (PageSizeId.B4, "B4 (257 x 364 mm)"),
    (PageSizeId.B5, "B5 (182 x 257 mm, 7.17 x 10.13 inches)"),
    (PageSizeId.B6, "B6 (128 x 182 mm)"),
    (PageSizeId.B7, "B7 (91 x 128 mm)"),
    (PageSizeId.B8, "B8 (64 x 91 mm)"),
    (PageSizeId.B9, "B9 (45 x 64 mm)"),
    (PageSizeId.B10, "B10 (32 x 45 mm)"),
    (PageSizeId.C5E, "C5E (163 x 229 mm)"),
    (PageSizeId.Comm10E, "Comm10E (105 x 241 mm, U.S. Common 10 Envelope)"),
    (PageSizeId.DLE, "DLE (110 x 220 mm)"),
    (PageSizeId.Executive, "Executive (7.5 x 10 inches, 191 x 254 mm)"),
    (PageSizeId.Folio, "Folio (210 x 330 mm)"),
    (PageSizeId.Ledger, "Ledger (432 x 279 mm)"),
    (PageSizeId.Tabloid, "Tabloid (279 x 432 mm)"),
]


class SongDraft:
    """The parts of a song an edit can change, as they were at one moment.

    Title, number and subtitle are in it, and so is the transposition: during
    an edit those are held back until Save as well.
    """

    def __init__(self, text, chords, title, number, subtitle,
                 transposed_steps, key):
        self.text = text
        # Copies, so later edits and transposes do not change them.
        self.chords = chords
        self.title = title
        self.number = number
        self.subtitle = subtitle
        self.transposed_steps = transposed_steps
        # What "changed" compares: text, stored chord strings, metadata.
        self.key = key

    @staticmethod
    def key_of(text, chords, title, number, subtitle):
        stored = sorted(
            (chord.character_num, chord.getStoredText()) for chord in chords)
        return (text or "", tuple(stored), title or "", number,
                subtitle or "")

    def respelledKey(self, session, song):
        """key, with the chords spelled as the song's key spells them.

        A transpose forgets how a chord was typed (A# or Bb). Taken away and
        back, the song has the same notes and this key.
        """
        chords = []
        for chord in self.chords:
            chord = copy.copy(chord)
            if not chord.unknown:
                chord.note_id = chord.note_id
                if chord.bass_note_id != -1:
                    chord.bass_note_id = chord.bass_note_id
            chords.append(chord)
        return self.key_of(self.text, chords, self.title, self.number,
                           self.subtitle)

    @classmethod
    def capture(cls, session, song):
        text = session._currentSongText()
        chords = list(song.iterateAllChords())
        return cls(text, [copy.copy(chord) for chord in chords], song.title,
                   song.number, song.subtitle, song.transposed_steps,
                   cls.key_of(text, chords, song.title, song.number,
                              song.subtitle))


class EditSession:
    """One edit of the open song, until Save or Discard.

    Edit Chords and Edit Text are edits, and so is a change made while
    viewing (VIEW): a transpose, or a new title, number or notes. Nothing is
    written to the songbook while it lasts. Its undo steps are on their own
    stack, which goes away with the edit.
    """

    CHORDS = "chords"
    TEXT = "text"
    # A change made while viewing. Save and Discard show only while it
    # changes the song; going back (transposing to the key it had) ends it.
    # Edit Chords or Edit Text go on with it as the same edit.
    VIEW = "view"

    def __init__(self, mode, song, start, main_undo_stack):
        self.mode = mode
        self.song = song
        self.start = start
        # The songbook's undo stack, put back when the edit ends.
        self.main_undo_stack = main_undo_stack


class CustomTextEdit(QtWidgets.QTextEdit):
    """
    """

    def __init__(self, app):
        super().__init__(app.win)
        self.app = app

        self.dragging_chord_orig_position = -1
        self.dragging_chord = None
        # The letter the mouse was over at its last move while dragging.
        self.dragging_mouse_char = -1
        self.original_chord = None
        # Press point while a selection rectangle may be dragged.
        self.marquee_origin = None
        self.marquee_current = None

        # So that hover mouse move events are generated:
        self.setMouseTracking(True)

        self.lyric_editor_mode = False

    def cancelChordMarquee(self):
        self.marquee_origin = None
        self.marquee_current = None

    def _marquee_is_drag(self):
        """A short movement is still a click."""
        if self.marquee_origin is None or self.marquee_current is None:
            return False
        delta = self.marquee_current - self.marquee_origin
        distance = QtWidgets.QApplication.startDragDistance()
        return delta.manhattanLength() >= distance

    def _chord_nums_in_rect(self, rect):
        song = self.app.current_song
        if song is None:
            return set()
        selected = set()
        editor = self.app.editor
        for chord in song.iterateAllChords():
            _char_rect, chord_rect = self.app.getCharRects(
                editor, chord.character_num, chord)
            if chord_rect is not None and rect.intersects(
                    QtCore.QRectF(chord_rect)):
                selected.add(chord.character_num)
        return selected

    def _finish_marquee(self):
        if not self._marquee_is_drag():
            return
        rect = QtCore.QRectF(QtCore.QPointF(self.marquee_origin),
                             QtCore.QPointF(self.marquee_current)).normalized()
        self.app.selected_chord_nums = self._chord_nums_in_rect(rect)
        # The drag is the rectangle, even when it misses every chord.
        self.app.selected_char_num = None

    def _draw_marquee(self, painter):
        if not self._marquee_is_drag():
            return
        band = QtCore.QRect(self.marquee_origin,
                            self.marquee_current).normalized()
        color = self.app.chords_color
        painter.setPen(QtGui.QPen(color))
        painter.setBrush(QtGui.QColor(color.red(), color.green(), color.blue(),
                                      40))
        painter.drawRect(band)

    def paintEvent(self, event):
        """
        Called when the widget needs to draw the current song.
        """

        if self.lyric_editor_mode:

            # Paint the lyrics text, selection rect, and cursor:
            super().paintEvent(event)

            # Paint the chords:
            if self.app.current_song:
                painter = QtGui.QPainter()
                painter.begin(self.viewport())
                self.paintChordLayer(painter)
                painter.end()

        else:
            painter = QtGui.QPainter()
            painter.begin(self.viewport())

            if self.app.current_song:
                width = 100000  # Unlimited
                height = 100000  # Unlimited

                paint_rect = QtCore.QRect(0, 0, width, height)
                editor = self.app.editor
                self.app.drawSongToRect(self.app.current_song, painter, editor,
                                        paint_rect)

            self._draw_marquee(painter)
            painter.end()

    def paintChordLayer(self, painter):
        """Draw chords for the current song using the shared song layout."""
        painter.setFont(self.app.chords_font)
        layout = SongLayout.place(
            QtDocumentLayout(self), self.app.current_song.chordsOnLetters(),
            self.app.getHeightsWithChords, self.app.getChordWidth,
            lambda chord: chord.getChordText())
        for placed in layout.placed:
            painter.setPen(self.app.chordColorFor(placed))
            self.app.drawChord(painter, placed.chord_rect, placed.chord_text)

    def leaveEvent(self, event):
        """
        Called when the mouse LEAVES the song chords widget.
        """

        if self.lyric_editor_mode:
            super().leaveEvent(event)
        else:
            # Clear the hovering highlighting:
            self.app.hover_char_num = None
            self.viewport().update()

    def update(self):
        if not self.lyric_editor_mode:
            self.viewport().update()

    def undo(self):
        if self.lyric_editor_mode:
            super().undo()
        else:
            self.app.undo_stack.undo()

    def redo(self):
        if self.lyric_editor_mode:
            super().redo()
        else:
            self.app.undo_stack.redo()

    def optionKeyToggled(self, pressed):
        if self.dragging_chord == None:
            return

        if pressed:
            # Copy the dragging chord into the original location:
            self.original_chord = self.app.current_song.copyChord(
                self.dragging_chord, self.dragging_chord_orig_position)
        else:
            # Remove the original chord:
            self.app.current_song.deleteChord(self.original_chord)
            self.original_chord = None

        self.viewport().update()

    def mouseMoveEvent(self, event):
        """
        Called when mouse is DRAGGED or HOVERED in the song chords widget.
        """

        if self.lyric_editor_mode:
            super().mouseMoveEvent(event)
            return
        if not self.app.chordEditing():
            # Viewing: no hover highlight, nothing to select.
            return

        if self.dragging_chord is None and self.marquee_origin is not None:
            self.marquee_current = event.pos()
            if self._marquee_is_drag():
                self.app.hover_char_num = None
                self.viewport().update()
                return

        localx = event.pos().x()
        localy = event.pos().y()
        dragging = (self.dragging_chord != None)
        letter_tuple = self.app.determineClickedLetter(localx, localy, dragging)

        if letter_tuple != None:
            (is_chord, song_char_num) = letter_tuple
            # Mouse is over a vlid chord/letter

            if not self.dragging_chord:
                # Hovering, highlight the new chord/letter
                self.app.hover_char_num = song_char_num
            else:
                # Dragging - A chord is being dragged
                song = self.app.current_song

                if song_char_num != self.dragging_mouse_char:
                    # The mouse is over a new letter. A chord that was moved
                    # onto a letter with a chord jumps over that letter, so
                    # the mouse still being over it moves nothing.
                    song = self.app.current_song
                    text = song.getAllText()
                    chord = self.dragging_chord
                    direction = chord_drag_direction(
                        text, chord.character_num, self.dragging_mouse_char,
                        song_char_num)
                    self.dragging_mouse_char = song_char_num
                    landing = self.app.freeCharacterForChord(
                        chord, song_char_num, direction, True)

                    if landing is not None and landing != chord.character_num:
                        # The spaces the chord leaves at the end of a line go.
                        moved, where = self.app.placeChord(chord, landing)
                        self.dragging_chord = moved
                        self.dragging_mouse_char = where(song_char_num)
                        self._followReplaced(where)

                        # Show hover feedback on the new letter:
                        self.app.hover_char_num = moved.character_num
                        self.app.selected_char_num = moved.character_num
        else:
            # The mouse is NOT over a letter
            if not self.dragging_chord:
                self.app.hover_char_num = None
            elif self.app.drag_past_line_end is not None:
                # Right of the last letter of a line: the line gets spaces.
                self.app.dragChordPastLineEnd(self, *self.app.drag_past_line_end)

        self.app.editor.viewport().update()

    def _followReplaced(self, where):
        """The copy of an Option drag stays the chord it is when it moved."""
        if self.original_chord is None:
            return
        position = where(self.original_chord.character_num)
        for chord in self.app.current_song.iterateAllChords():
            if chord.character_num == position and chord is not self.dragging_chord:
                self.original_chord = chord
                return

    def mousePressEvent(self, event):
        """
        Called when mouse is CLICKED in the song chords widget.
        """

        if self.lyric_editor_mode:
            super().mousePressEvent(event)
            return

        if not self.app.chordEditing():
            # Viewing: nothing can be selected or dragged.
            return

        if event.button() == Qt.MouseButton.LeftButton:
            # A click drops the rectangle selection. The press then selects
            # one letter, or starts dragging the chord under the pointer.
            self.app.selected_chord_nums = set()
            self.cancelChordMarquee()

            localx = event.pos().x()
            localy = event.pos().y()
            letter_tuple = self.app.determineClickedLetter(
                localx, localy, False)

            if letter_tuple:
                # A valid letter/chord was clicked, select it:
                (is_chord, song_char_num) = letter_tuple

                if self.app.selected_char_num != song_char_num:
                    # User clicked on an un-selected letter. Select it:
                    self.app.selected_char_num = song_char_num

                #if self.app.selected_char_num == song_char_num and is_chord:
                if is_chord:
                    # User clicked on the selected chord, initiate drag:
                    try:
                        self.dragging_chord = self.app.current_song.getChord(
                            song_char_num)
                    except ValueError:
                        # User clicked on an empty chord space
                        pass
                    else:
                        self.dragging_chord_orig_position = song_char_num
                        self.dragging_mouse_char = song_char_num

                        self.app.undo_stack.beginMacro("chord dragged")

                        # If option is held, copy the chord:
                        key_modifiers = event.modifiers()
                        if bool(key_modifiers &
                                Qt.KeyboardModifier.AltModifier):
                            self.original_chord = self.app.current_song.copyChord(
                                self.dragging_chord,
                                self.dragging_chord_orig_position)
                        else:
                            self.original_chord = None

            else:
                self.app.selected_char_num = None
                self.dragging_chord = None

            # A press that is not on a chord glyph can drag a selection rectangle.
            if self.dragging_chord is None:
                self.marquee_origin = event.pos()
                self.marquee_current = event.pos()

            self.app.editor.viewport().update()

    def mouseReleaseEvent(self, event):
        if self.lyric_editor_mode:
            super().mouseReleaseEvent(event)
            return

        # Stop dragging of the chord (it's already in the correct position,
        # and no other chord was on that letter):
        if self.dragging_chord:
            self.dragging_chord_orig_position = -1
            self.dragging_mouse_char = -1
            self.dragging_chord = None
            self.app.undo_stack.endMacro()
        else:
            self._finish_marquee()

        self.cancelChordMarquee()
        self.viewport().update()

    def mouseDoubleClickEvent(self, event):
        """
        Called when mouse is DOUBLE-CLICKED in the song chords widget.
        """
        if self.lyric_editor_mode:
            super().mouseDoubleClickEvent(event)
            return
        if not self.app.chordEditing():
            return

        if event.button() == Qt.MouseButton.LeftButton:
            localx = event.pos().x()
            localy = event.pos().y()
            letter_tuple = self.app.determineClickedLetter(
                localx, localy, False)
            if letter_tuple:
                # A valid chord/letter was double-clicked, edit it:
                (is_chord, song_char_num) = letter_tuple
                self.app.selected_char_num = song_char_num
                self.app.processSongCharEdit(song_char_num)
            else:
                # Invalid chord/letter was double clicked. Clear current selection:
                self.app.selected_char_num = None

            self.viewport().update()

    def cancelChordDrag(self):
        """Esc while dragging: the chord goes back where it was."""
        if self.dragging_chord is None:
            return False
        self.dragging_chord = None
        self.dragging_chord_orig_position = -1
        self.dragging_mouse_char = -1
        self.original_chord = None
        self.app.undo_stack.endMacro()
        self.app.undo_stack.undo()
        self.app.selected_char_num = None
        self.viewport().update()
        return True

    def event(self, event):
        # Esc during a chord drag cancels the drag. Without a drag it is the
        # Discard Changes shortcut.
        if (event.type() == QtCore.QEvent.Type.ShortcutOverride
                and self.dragging_chord is not None
                and event.key() == Qt.Key.Key_Escape):
            event.accept()
            return True
        # QTextEdit handles Undo and Redo before keyPressEvent, and accepts
        # the shortcut so the Edit menu action does not run. While chords are
        # edited, those keys belong to the chord undo stack.
        if not self.lyric_editor_mode and event.type() in (
                QtCore.QEvent.Type.ShortcutOverride,
                QtCore.QEvent.Type.KeyPress):
            redo = event.matches(QtGui.QKeySequence.StandardKey.Redo)
            undo = event.matches(QtGui.QKeySequence.StandardKey.Undo)
            if undo or redo:
                if event.type() == QtCore.QEvent.Type.KeyPress:
                    if redo:
                        self.app.ui.actionRedo.trigger()
                    else:
                        self.app.ui.actionUndo.trigger()
                event.accept()
                return True
        return super().event(event)

    def keyPressEvent(self, event):

        if self.lyric_editor_mode:
            super().keyPressEvent(event)
            return

        key = event.key()
        if key == Qt.Key.Key_Escape and self.cancelChordDrag():
            return

        if not self.app.chordEditing():
            # Viewing: Copy works, keys that would change the song do not.
            if (key == Qt.Key.Key_C and bool(
                    event.modifiers() & Qt.KeyboardModifier.ControlModifier)):
                self.app.ui.actionCopy.trigger()
                return
            self.app.win.keyPressEvent(event)
            return

        if key == Qt.Key.Key_Alt:
            self.optionKeyToggled(True)

        if key == Qt.Key.Key_Delete or key == Qt.Key.Key_Backspace:
            self.app.deleteSelectedChord()
            return
        else:
            if not bool(event.modifiers() &
                        Qt.KeyboardModifier.ControlModifier):
                # We are not invoking a shortcut (Control on Windows, Command on Mac)
                if self.app.processKeyPressed(key):
                    return
            else:
                # TODO instead of passing these to the UI (parent) perhaps there
                # is a better way?
                if key == Qt.Key.Key_C:
                    self.app.ui.actionCopy.trigger()
                    return
                elif key == Qt.Key.Key_X:
                    self.app.ui.actionCut.trigger()
                    return
                elif key == Qt.Key.Key_V:
                    self.app.ui.actionPaste.trigger()
                    return

        # Unused keys are left for the window. Undo and redo are handled above.
        self.app.win.keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if self.lyric_editor_mode:
            super().keyReleaseEvent(event)
            return

        key = event.key()
        if key == Qt.Key.Key_Alt:
            self.optionKeyToggled(False)


class ChordDialog(QtWidgets.QDialog):
    """
    Dialog for allowing the user to set the chord note & type.

    The chord text must be a valid chord (is_valid_chord_text, the same test
    as the parser and transposer use). While it is not, the field is red and
    OK is disabled, and Enter does not accept.
    """

    # Native macOS line edits ignore a background color unless a border is set.
    _INVALID_CHORD_STYLE = "QLineEdit { background-color: red; border: 1px solid red; }"

    def __init__(self, app):
        super().__init__(app.win)

        self.app = app
        self.ui = softchord_chord_dialog_ui.Ui_Dialog()
        self.ui.setupUi(self)
        self._edited_chord = None
        self._kept_type_id = 0
        self._kept_suffix = None
        self._initial_text = ""
        # Set while copying one side onto the other, so the two stay in step
        # without rewriting the text the user is still typing.
        self._updating_chord = False

        notes_list = []
        char_num = getattr(self.app, "selected_char_num", None)
        for note_id in range(12):
            note_str = self.app.current_song._getNoteString(note_id, char_num)
            notes_list.append(note_str)
        self.ui.note_menu.addItems(notes_list)
        self.ui.note_menu.setMaxVisibleItems(12)  # Show all notes

        self.ui.chord_type_menu.addItems(self.app.chord_type_names)
        self.ui.chord_type_menu.setMaxVisibleItems(20)  # Show more types

        self.ui.bass_menu.addItems(["None"] + notes_list)
        self.ui.bass_menu.setMaxVisibleItems(12)  # Show all notes

        # Chord text sits to the right of "Chord for selected letter:".
        chord_text = QtWidgets.QLineEdit(self)
        chord_text.setObjectName("chord_text_ef")
        header = QtWidgets.QHBoxLayout()
        self.ui.verticalLayout.removeWidget(self.ui.label)
        header.addWidget(self.ui.label)
        header.addWidget(chord_text, 1)
        self.ui.verticalLayout.insertLayout(0, header)
        self.ui.chord_text_ef = chord_text
        self.setTabOrder(chord_text, self.ui.note_menu)

        self.ui.note_menu.currentIndexChanged.connect(self._onChordEdited)
        self.ui.chord_type_menu.currentIndexChanged.connect(self._onChordEdited)
        self.ui.bass_menu.currentIndexChanged.connect(self._onChordEdited)
        self.ui.marker_ef.textChanged.connect(self._onChordEdited)
        self.ui.in_parentheses_box.toggled.connect(self._onChordEdited)
        chord_text.textChanged.connect(self._onChordTextChanged)
        chord_text.textChanged.connect(self._refreshChordValidity)

    def _onChordEdited(self, *args):
        if self._updating_chord:
            return
        self._updateChordText()

    def _onChordTextChanged(self, text):
        if self._updating_chord or self._edited_chord is None:
            return
        parsed = parse_chord(text)
        if parsed.unknown:
            # Not a chord: red, and OK is off. The controls stay as they are.
            return

        # Hold the menus still so this edit is not immediately replaced
        # with the normalized spelling.
        self._updating_chord = True
        try:
            self._setControls(parsed.note_id, parsed.chord_type_id,
                              parsed.bass_note_id, parsed.marker,
                              parsed.in_parentheses)
            # A suffix that is not a known type is kept as typed.
            self._kept_type_id = parsed.chord_type_id
            self._kept_suffix = (None if parsed.is_known_type else
                                 parsed.suffix)
        finally:
            self._updating_chord = False

    def _setControls(self, note_id, type_id, bass_note_id, marker,
                     in_parentheses):
        self.ui.note_menu.setCurrentIndex(note_id)
        self.ui.chord_type_menu.setCurrentIndex(type_id)
        # -1 becomes 0, etc:
        self.ui.bass_menu.setCurrentIndex(bass_note_id + 1)
        self.ui.marker_ef.setText(marker or "")
        self.ui.in_parentheses_box.setChecked(bool(in_parentheses))

    def _setChordTextInvalid(self, invalid):
        style = self._INVALID_CHORD_STYLE if invalid else ""
        self.ui.chord_text_ef.setStyleSheet(style)

    def _chordTextIsValid(self):
        return is_valid_chord_text(self.ui.chord_text_ef.text())

    def _refreshChordValidity(self, *args):
        """Red field and no OK while the chord text is not a valid chord."""
        valid = self._chordTextIsValid()
        self._setChordTextInvalid(not valid)
        ok = self.ui.buttonBox.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok)
        if ok is not None:
            ok.setEnabled(valid)

    def accept(self):
        # Backstop for any path other than the (disabled) OK button.
        if not self._chordTextIsValid():
            return
        super().accept()

    def _updateChordText(self):
        if self._edited_chord is None:
            return
        # Changing a control replaces whatever was typed.
        text = self._chordTextFromControls()
        edit = self.ui.chord_text_ef
        self._updating_chord = True
        try:
            if edit.text() != text:
                edit.setText(text)
        finally:
            self._updating_chord = False

    def _suffixFromControls(self):
        """Kept suffix text while the type menu still shows its base type."""
        if self.ui.chord_type_menu.currentIndex() == self._kept_type_id:
            return self._kept_suffix
        return None

    def _chordTextFromControls(self):
        """
        Chord text for the current controls, spelled the same way as the song.
        """
        chord = self._edited_chord
        preview = SongChord(chord.song, chord.character_num,
                            self.ui.note_menu.currentIndex(),
                            self.ui.chord_type_menu.currentIndex(),
                            self.ui.bass_menu.currentIndex() - 1,
                            self.ui.marker_ef.text(),
                            self.ui.in_parentheses_box.isChecked(),
                            suffix=self._suffixFromControls())
        return preview.getChordText()

    def _loadChord(self, chord):
        """
        Fill the controls from this chord and show its chord text.
        """
        self._edited_chord = chord
        self._kept_type_id = chord.chord_type_id
        self._kept_suffix = chord._suffix
        self._initial_text = chord.getStoredText()

        self._updating_chord = True
        try:
            if not chord.unknown:
                self._setControls(chord.note_id, chord.chord_type_id,
                                  chord.bass_note_id, chord.marker,
                                  chord.in_parentheses)
            else:
                self._setControls(0, 0, -1, "", False)
            # Show the chord as stored, so a chord this version cannot read
            # fully (or at all) is not changed by opening the dialog.
            self.ui.chord_text_ef.setText(self._initial_text)
        finally:
            self._updating_chord = False
        # Text that is not a chord shows red until a valid chord is typed.
        self._refreshChordValidity()

    def display(self, chord):
        """
        Display the chord-editing dialog box.
        Modify the passed chord if OK is pressed.
        Returns False if user pressed Cancel.
        """

        self._loadChord(chord)

        # Focus the chord text and select it so typing replaces the chord.
        edit = self.ui.chord_text_ef
        edit.setFocus()
        edit.selectAll()

        self.show()
        self.raise_()
        out = self.exec()
        if out:  # OK pressed:
            if edit.text() == self._initial_text:
                # Untouched. Keep the chord exactly as it was read.
                return True
            chord.note_id = self.ui.note_menu.currentIndex()
            chord.chord_type_id = self.ui.chord_type_menu.currentIndex()
            suffix = self._suffixFromControls()
            if suffix is not None:
                chord._suffix = suffix
            # 0 (first item) will become -1 (invalid):
            chord.bass_note_id = self.ui.bass_menu.currentIndex() - 1
            chord.marker = self.ui.marker_ef.text()
            chord.in_parentheses = self.ui.in_parentheses_box.isChecked()

            return True
        else:
            # Cancel pressed
            return False



class PdfOptions:

    def __init__(self):
        self.left_margin = 0.5
        self.right_margin = 0.5
        self.top_margin = 0.5
        self.bottom_margin = 0.5
        self.alternate_margins = False
        self.print_4_per_page = False
        self.generate_table_of_contents = False
        self.print_song_num = True
        self.print_song_title = False
        self.print_song_key = True
        self.print_song_comment = True  # Usually "Pesn' Vozhrozhdeniya" number
        self.page_width = 8.5
        self.page_height = 11.0


def fit_scale_ratio(content_width, content_height, target_width, target_height,
                    zoom_factor):
    """How much to shrink the song so it fits the page. 1.0 means it already fits.

    The content size is the on-screen document, which already includes zoom.
    The returned number is the one shown in the export dialog. Painting
    divides it by the zoom again. The header line is not part of this size.
    """
    content_width /= zoom_factor
    content_height /= zoom_factor
    ratio = max(content_width / target_width, content_height / target_height)
    if ratio > 1.0:
        return 1.0 / ratio
    return 1.0


def song_target_size(page_width, page_height, left, right, top, bottom,
                     four_per_page):
    """Width and height of the area one copy of the song is painted into."""
    if four_per_page:
        page_width = page_width // 2
        page_height = page_height // 2
        return (int(page_width - left - right), int(page_height - top - bottom))
    return (page_width - left - right, page_height - top - bottom)


def song_document_size(song):
    """Width and height of the song text, in document units."""
    return QtDocumentLayout.content_size(song.doc)


def single_song_fit_scale(song, page_width, page_height, left_in, right_in,
                          top_in, bottom_in, four_per_page, zoom_factor):
    """Fit scale for one song, or None when the printable area is empty."""
    target_width, target_height = song_target_size(
        page_width, page_height, left_in * 72.0, right_in * 72.0,
        top_in * 72.0, bottom_in * 72.0, four_per_page)
    if target_width <= 0 or target_height <= 0:
        return None
    content_width, content_height = song_document_size(song)
    return fit_scale_ratio(content_width, content_height, target_width,
                           target_height, zoom_factor)


def scale_message(scale_ratio):
    """Label text for one song's fit scale. None means the page area is empty."""
    if scale_ratio is None:
        return "The page is too small to fit this song."
    percent = scale_ratio * 100.0
    if percent >= 99.95:
        return "The song fits the page at 100%."
    return "The song will be scaled to %.1f%% to fit the page." % percent


def export_printer(page_width_in, page_height_in, four_per_page,
                   output_file=None, native_on_mac=False):
    """A printer set up the way PDF export paints a page.

    Four copies use a sheet twice as wide and twice as tall, and each copy
    is then painted into one quarter. On macOS, one-file export uses PDF
    output. One-file-per-song export uses the native format.
    """
    printer = QPrinter()
    if four_per_page:
        size = QtCore.QSizeF(page_width_in * 2.0, page_height_in * 2.0)
    else:
        size = QtCore.QSizeF(page_width_in, page_height_in)
    printer.setPageSize(QtGui.QPageSize(size, QtGui.QPageSize.Unit.Inch))
    printer.setFullPage(True)
    printer.setPageOrientation(QtGui.QPageLayout.Orientation.Portrait)
    if output_file:
        printer.setOutputFileName(output_file)
    if sys.platform == "win32":
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    elif sys.platform == "darwin":
        if native_on_mac:
            printer.setOutputFormat(QPrinter.OutputFormat.NativeFormat)
        else:
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    return printer


class PdfDialog(QtWidgets.QDialog):
    """
    Dialog for allowing the user to set up printing and PDF export options.
    """

    def __init__(self, app):
        super().__init__(app.win)

        self.app = app
        self.ui = softchord_pdf_dialog_ui.Ui_Dialog()
        self.ui.setupUi(self)

        self.ui.left_margin_ef.setValidator(
            QtGui.QDoubleValidator(0, 1000000000, 5, self))
        self.ui.right_margin_ef.setValidator(
            QtGui.QDoubleValidator(0, 1000000000, 5, self))
        self.ui.top_margin_ef.setValidator(
            QtGui.QDoubleValidator(0, 1000000000, 5, self))
        self.ui.bottom_margin_ef.setValidator(
            QtGui.QDoubleValidator(0, 1000000000, 5, self))
        self.ui.page_width_ef.setValidator(
            QtGui.QDoubleValidator(0, 1000000000, 5, self))
        self.ui.page_height_ef.setValidator(
            QtGui.QDoubleValidator(0, 1000000000, 5, self))

        self._scale_song = None
        self._scale_printer = None
        self._native_on_mac = False
        self._scale_inputs_connected = False

    def display(self, pdf_options, single_pdf_export, song=None, printer=None,
                native_on_mac=False):
        """
        Display a dialog that alters the PdfOptions if OK is pressed.
        Returns False if user pressed Cancel.

        song is set for a one-song print or PDF export. The dialog then
        shows the fit scale and updates it as the page settings change.
        printer is the printer chosen in the system print dialog. PDF
        export leaves it empty and uses the page size fields instead.
        """

        self.ui.left_margin_ef.setText(str(pdf_options.left_margin))
        self.ui.right_margin_ef.setText(str(pdf_options.right_margin))
        self.ui.top_margin_ef.setText(str(pdf_options.top_margin))
        self.ui.bottom_margin_ef.setText(str(pdf_options.bottom_margin))

        self.ui.page_width_ef.setText(str(pdf_options.page_width))
        self.ui.page_height_ef.setText(str(pdf_options.page_height))

        self.ui.alternate_margins_box.setChecked(pdf_options.alternate_margins)
        self.ui.print_4_per_page_box.setChecked(pdf_options.print_4_per_page)
        self.ui.generate_table_of_contents_box.setChecked(
            pdf_options.generate_table_of_contents)
        self.ui.print_song_num_box.setChecked(pdf_options.print_song_num)
        self.ui.print_song_title_box.setChecked(pdf_options.print_song_title)
        self.ui.print_song_key_box.setChecked(pdf_options.print_song_key)
        self.ui.print_song_comment_box.setChecked(
            pdf_options.print_song_comment)

        # Allow table of contents only when generating one PDF for multiple songs:
        if not single_pdf_export:
            self.ui.generate_table_of_contents_box.setChecked(False)
            self.ui.generate_table_of_contents_box.setVisible(False)

        if song is not None:
            self.showSongScale(song, printer, native_on_mac)
        else:
            self.ui.scale_label.hide()

        self.show()
        self.raise_()
        out = self.exec()
        if out:  # OK pressed:
            # FIXME what if the user entered ""?
            pdf_options.left_margin = float(self.ui.left_margin_ef.text())
            pdf_options.right_margin = float(self.ui.right_margin_ef.text())
            pdf_options.top_margin = float(self.ui.top_margin_ef.text())
            pdf_options.bottom_margin = float(self.ui.bottom_margin_ef.text())
            pdf_options.page_width = float(self.ui.page_width_ef.text())
            pdf_options.page_height = float(self.ui.page_height_ef.text())
            pdf_options.alternate_margins = self.ui.alternate_margins_box.isChecked(
            )
            pdf_options.print_4_per_page = self.ui.print_4_per_page_box.isChecked(
            )
            pdf_options.generate_table_of_contents = self.ui.generate_table_of_contents_box.isChecked(
            )
            pdf_options.print_song_num = self.ui.print_song_num_box.isChecked()
            pdf_options.print_song_title = self.ui.print_song_title_box.isChecked(
            )
            pdf_options.print_song_key = self.ui.print_song_key_box.isChecked()
            pdf_options.print_song_comment = self.ui.print_song_comment_box.isChecked(
            )

            return True
        else:
            # Cancel pressed
            return False

    def showSongScale(self, song, printer=None, native_on_mac=False):
        """Show the fit scale for one song and keep it current."""
        self._scale_song = song
        self._scale_printer = printer
        self._native_on_mac = native_on_mac
        was_hidden = self.ui.scale_label.isHidden()
        self.ui.scale_label.show()
        self.updateScaleLabel()
        if was_hidden:
            extra = self.ui.scale_label.sizeHint().height() + 8
            self.resize(self.width(), self.height() + extra)
        if self._scale_inputs_connected:
            return
        for edit in (self.ui.left_margin_ef, self.ui.right_margin_ef,
                     self.ui.top_margin_ef, self.ui.bottom_margin_ef,
                     self.ui.page_width_ef, self.ui.page_height_ef):
            edit.textChanged.connect(self.onScaleInputsChanged)
        self.ui.print_4_per_page_box.toggled.connect(self.onScaleInputsChanged)
        self._scale_inputs_connected = True

    def onScaleInputsChanged(self, _value=None):
        self.updateScaleLabel()

    def updateScaleLabel(self):
        """Refresh the fit-scale label from the fields currently on screen."""
        if self._scale_song is None:
            return
        margins = self._read_inches()
        if margins is None:
            self.ui.scale_label.setText("Enter the page size to see the scale.")
            return
        left, right, top, bottom, page_width, page_height = margins
        four_per_page = self.ui.print_4_per_page_box.isChecked()
        if self._scale_printer is not None:
            # The system print dialog already chose the paper.
            page_px_width = self._scale_printer.width()
            page_px_height = self._scale_printer.height()
        else:
            printer = export_printer(page_width, page_height, four_per_page,
                                     native_on_mac=self._native_on_mac)
            page_px_width = printer.width()
            page_px_height = printer.height()
        scale = single_song_fit_scale(
            self._scale_song, page_px_width, page_px_height, left, right, top,
            bottom, four_per_page, self.app.zoom_factor)
        self.ui.scale_label.setText(scale_message(scale))

    def _read_inches(self):
        """Page size and margins from the fields, or None if one is not a number."""
        try:
            return (
                float(self.ui.left_margin_ef.text()),
                float(self.ui.right_margin_ef.text()),
                float(self.ui.top_margin_ef.text()),
                float(self.ui.bottom_margin_ef.text()),
                float(self.ui.page_width_ef.text()),
                float(self.ui.page_height_ef.text()),
            )
        except ValueError:
            return None


def _png_bytes(image):
    """PNG bytes for the clipboard. A QImage there becomes a TIFF on macOS."""

    buffer = QtCore.QBuffer()
    buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    data = buffer.data()
    buffer.close()
    return data


class _SongSheetClipboardTypes(QtGui.QUtiMimeConverter):
    """Mac names for a copied song sheet.

    Qt's own image copy is a TIFF. Other apps paste a PNG or an SVG.
    """

    _types = (
        ("image/png", "public.png"),
        ("image/svg+xml", "public.svg-image"),
    )

    def utiForMime(self, mime):
        for name, uti in self._types:
            if mime == name:
                return uti
        return ""

    def mimeForUti(self, uti):
        for name, mapped in self._types:
            if uti == mapped:
                return name
        return ""

    def convertFromMime(self, mime, data, uti):
        if self.mimeForUti(uti) != mime:
            return []
        if isinstance(data, QtCore.QByteArray):
            return [data]
        try:
            return [QtCore.QByteArray(bytes(data))]
        except TypeError:
            return []

    def convertToMime(self, mime, data, uti):
        if self.mimeForUti(uti) != mime or not data:
            return QtCore.QByteArray()
        return data[0]


class SongbookSession(SongbookIO, QtCore.QObject):
    """
    Open songbook, current song, undo stack, and editor commands.

    Not a QApplication. App creates this, owns the process, and forwards
    attribute access so existing callers can keep using the shell.
    """

    @property
    def curs(self):
        """Open connection. Callers that still inspect the file use this.

        Songs, undo, and import go through the store instead of executing SQL.
        """
        return self.store.connection

    @curs.setter
    def curs(self, connection):
        self.store.use(connection)

    def __init__(self):
        super().__init__()
        self._readonly_songbook_reported = False
        # TODO(remove-v1-compat): path of an old-format songbook that could
        # not be converted in place, while a converted temporary copy is open.
        self.songbook_original_path = None
        self.doc_editor_offset = 0  # FIXME

        self.win = QtWidgets.QMainWindow()
        self.ui = softchord_main_window_ui.Ui_MainWindow()
        self.ui.setupUi(self.win)

        self.on_windows = platform.system() == "Windows"

        self.store = SongbookStore()
        self.current_song = None
        self.empty_doc = QtGui.QTextDocument()

        self.pdf_options = PdfOptions()

        self.undo_stack = QtGui.QUndoStack()
        self.undo_stack.canUndoChanged.connect(self.updateEditMenu)
        self.undo_stack.canRedoChanged.connect(self.updateEditMenu)

        # Make a list of all chord types:
        self.chord_type_names = []
        self.chord_type_prints = []
        for _, name, print_text in chord_types_list:
            if print_text:
                name = "%s - %s" % (print_text, name)
            self.chord_type_names.append(name)
            self.chord_type_prints.append(print_text)

        # Key: chord type text, value: chord type ID
        self.chord_type_texts_dict = {}
        for id, print_text in enumerate(self.chord_type_prints):
            self.chord_type_texts_dict[print_text] = id
            for alternative_name, official_name in alternative_type_names.items(
            ):
                if print_text == official_name:
                    self.chord_type_texts_dict[alternative_name] = id

        # Make a list of all notes and keys:
        self.notes_list = []
        self.note_text_id_dict = {}
        for note_id, text, alt_text in global_notes_list:
            self.notes_list.append((text, alt_text))
            self.note_text_id_dict[text] = note_id
            self.note_text_id_dict[alt_text] = note_id

        # Allows the user to show only songs that match this text:
        self.filter_string = ""
        # True while the song list selection is put back by code. The open
        # song does not change then.
        self._holding_song_selection = False
        # The edit in progress (Edit Chords or Edit Text), or None: viewing.
        self.edit_session = None
        # Whether that edit differs from the song as it was when it started.
        self._edit_changed = False
        # A song picked in the list during a changed edit. The list shows the
        # edited song again, and the Save dialog runs right after.
        self._pending_song_selection = None

        self.songs_model = SongsTableModel(self)
        self.songs_proxy_model = SongsProxyModel(self)
        self.songs_proxy_model.setSourceModel(self.songs_model)

        self.ui.songs_view.setModel(self.songs_proxy_model)
        self.ui.songs_view.setSortingEnabled(True)

        self.ui.songs_view.horizontalHeader().setStretchLastSection(True)
        self.ui.songs_view.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.ui.songs_view.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.ui.songs_view.selectionModel().selectionChanged.connect(
            self.songsSelectionChangedCallback)
        # Policy goes on the view: Qt forwards viewport context-menu events
        # here, with positions still in viewport coordinates.
        self.ui.songs_view.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu)
        self.ui.songs_view.customContextMenuRequested.connect(
            self.showSongsContextMenu)

        self.ui.song_filter_ef.textEdited.connect(self.songFilterEdited)
        self.ui.song_filter_ef.setClearButtonEnabled(True)

        self.previous_song_text = None  # Song text before last user's edit operation

        self.editor = CustomTextEdit(self)
        self.brief_note = BriefNote(self.editor)
        self.editor.undoAvailable.connect(self.updateEditMenu)
        self.editor.redoAvailable.connect(self.updateEditMenu)

        self.ui.lyric_editor_layout.addWidget(self.editor)
        self.ui.lyric_editor_layout.removeWidget(self.ui.chord_scroll_area)
        self.ui.chord_scroll_area.hide()

        self.editor.setLineWrapMode(QtWidgets.QTextEdit.LineWrapMode.NoWrap)
        self.editor.textChanged.connect(self.lyricsTextChanged)


        self.ui.song_num_ef.textEdited.connect(self.currentSongNumberEdited)
        self.ui.song_title_ef.textEdited.connect(self.currentSongTitleEdited)
        self.ui.song_subtitle_ef.textEdited.connect(self.subtitleEdited)

        self.ui.song_num_ef.setValidator(
            QtGui.QIntValidator(0, 1000000000, self.win))

        # Menu actions:
        self.ui.actionNewSongbook.triggered.connect(self.newSongbook)
        self.ui.actionOpenSongbook.triggered.connect(self.openSongbook)
        self.ui.actionCloseSongbook.triggered.connect(self.closeSongbook)
        self.ui.actionSaveSongbook.triggered.connect(self.saveSongbook)
        self.ui.actionAppendSongbook.triggered.connect(
            self.appendSongbookSelected)

        self.ui.actionPrint.triggered.connect(self.printSelectedSongs)
        self.ui.actionQuit.triggered.connect(self.win.close)
        self.ui.actionNewSong.triggered.connect(self.createNewSong)

        self.ui.actionDeleteSongs.triggered.connect(self.deleteSelectedSongs)
        self.ui.actionRemoveTrailingSpaces.triggered.connect(
            self.removeTrailingSpaces)
        self.ui.actionDeleteSong.triggered.connect(self.deleteSelectedSongs)
        self.ui.actionRenumberSongs.triggered.connect(self.renumberAllSongs)

        self.ui.actionExportSinglePdf.triggered.connect(self.exportToSinglePdf)
        self.ui.actionExportSongToPdf.triggered.connect(self.exportToSinglePdf)
        self.ui.actionExportMultiplePdfs.triggered.connect(
            self.exportToMultiplePdfs)
        self.ui.actionExportText.triggered.connect(self.exportToText)

        self.ui.actionExportChordPro.triggered.connect(self.exportToChordPro)
        self.ui.actionImportText.triggered.connect(self.browseForTextFile)
        self.ui.actionImportChordPro.triggered.connect(self.importFromChordPro)
        self.ui.actionLyricsFont.triggered.connect(self.changeLyricsFont)
        self.ui.actionChordsFont.triggered.connect(self.changeChordFont)

        self.ui.actionUndo.triggered.connect(self.undo)
        self.ui.actionRedo.triggered.connect(self.redo)
        self.ui.actionCut.triggered.connect(self.cutSelected)
        self.ui.actionCopy.triggered.connect(self.copySelected)
        self.ui.actionPaste.triggered.connect(self.pasteSelected)
        self.ui.actionCopySongText.triggered.connect(self.copySongText)
        self.ui.actionCopySongTextWithChords.triggered.connect(self.copySongTextWithChords)
        self.ui.actionCopySongAsImage.triggered.connect(self.copySongAsImage)
        self.ui.actionExportClipboard.triggered.connect(self.copySongText)

        # FIXME we need only one way to import a song from the clipboard. Remove one of these actions:
        self.ui.actionPasteAsNewSong.triggered.connect(self.pasteAsNewSong)
        self.ui.actionImportClipboard.triggered.connect(self.pasteAsNewSong)

        # Edit Chords... and Edit Text... start an edit. They are actions,
        # not modes: the song is only viewed until one of them is chosen.
        self.ui.actionChordEditorMode.triggered.connect(
            self.chordEditorSelected)
        self.ui.actionLyricEditorMode.triggered.connect(
            self.lyricEditorSelected)
        self.ui.actionSaveEdit.triggered.connect(self.saveEdit)
        self.ui.actionDiscardEdit.triggered.connect(self.requestDiscardEdit)

        self.ui.actionZoomIn.triggered.connect(self.zoomIn)
        self.ui.actionZoomOut.triggered.connect(self.zoomOut)
        self.ui.actionZoomActual.triggered.connect(self.zoomActual)

        self.zoom_levels = [1.0]
        zoom1 = 1.0
        zoom2 = 1.0
        for i in range(10):
            zoom1 *= 1.1
            zoom2 /= 1.1
            self.zoom_levels += [zoom1, zoom2]
        self.zoom_levels.sort()


        # Set zoom to 100%:
        self.zoom_factor = 1.0
        self.zoom_pos = self.zoom_levels.index(1.0)

        # The song toolbar above the song pane (see softchord_toolbar.py).
        self.toolbar = SongToolbar(self, self.ui.layoutWidget)
        # Below the Notes row, directly above the song.
        column = self.ui.verticalLayout
        song_at = next(i for i in range(column.count())
                       if column.itemAt(i).layout() is self.ui.lyric_editor_layout)
        column.insertWidget(song_at, self.toolbar)
        self.undo_stack.indexChanged.connect(self._updateChordButtons)

        self.clipboard = QtWidgets.QApplication.clipboard()
        self.clipboard.dataChanged.connect(self.clipboardChanged)
        # Kept alive for the session. Dropping it removes the PNG and SVG
        # names from the Mac clipboard.
        if sys.platform == "darwin":
            self._song_sheet_clipboard_types = _SongSheetClipboardTypes()

        self.ignore_song_text_changed = False
        # Chords that belong with the lyrics at each text-editor undo step.
        # The editor can put a deleted character back, but the chord on it
        # is not part of that text and would otherwise stay gone.
        self._lyric_undo_doc = None
        self._lyric_new_command = False
        self._lyric_undo_steps = 0
        self._lyric_chord_snapshots = {}

        # The letter/chord that is currently selected:
        self.selected_char_num = None
        # Character indexes chosen by a drag rectangle in Edit chords.
        self.selected_chord_nums = set()
        # The letter/chord that is currently hover (mouse hoveing over it):
        self.hover_char_num = None
        self.drag_past_line_end = None

        # NOTE: For printing of small song books, font sizes of 14 / 11 are ideal.

        self.lyrics_font = QtGui.QFont("Times New Roman", LYRICS_SIZE)
        self.lyrics_font_size = float(LYRICS_SIZE)
        self.lyrics_color = QtGui.QColor("BLACK")
        self.lyrics_font_metrics = QtGui.QFontMetricsF(self.lyrics_font)

        # Font that will be used if no good fonts are found:
        self.chords_font_size = float(CHORDS_SIZE)
        self.chords_font = QtGui.QFont("Times New Roman", CHORDS_SIZE,
                                       QtGui.QFont.Weight.Bold)
        self.chords_font_metrics = QtGui.QFontMetricsF(self.chords_font)

        # NOTE: This may work only on a Mac:
        self.symbols_font = QtGui.QFont("Arial Unicode MS", CHORDS_SIZE,
                                        QtGui.QFont.Weight.Bold)
        self.symbols_font_metrics = QtGui.QFontMetricsF(self.symbols_font)


        # BLUE is ideal for songbook printing:
        self.chords_color = QtGui.QColor(CHORDS_COLOR)
        self.unrecognized_chords_color = QtGui.QColor(UNRECOGNIZED_CHORDS_COLOR)
        self.white_color = QtGui.QColor("WHITE")
        self.editor.setFont(self.lyrics_font)

        self._orig_closeEvent = self.win.closeEvent
        self.win.closeEvent = self.closeEvent

        self._updateAutoDetectedKeyLabel()
        self.setCurrentSongbook(None)

        self.songs_model.updateFromDatabase()

        # The song is viewed until Edit Chords or Edit Text is chosen.
        self._applyEditorMode(None)

        self.updateZoomWidgets()

        self.updateStates()

        self.win.show()
        self.win.raise_()

    def songFilterEdited(self, new_text):
        """Show only the songs that match the filter text.

        Showing and hiding rows does not change which song is open. The
        selection is put back while the selection callback is held off, so
        the open song is not saved, closed and read again. (That dropped its
        undo steps, the Reset transpose count, and the scroll position.) A
        song the filter hides stays open, and is selected again when the
        filter shows it.
        """
        selected_ids = self.getSelectedSongIds()
        if not selected_ids and self.current_song is not None:
            selected_ids = [self.current_song.id]

        self._holding_song_selection = True
        try:
            self.ui.songs_view.selectionModel().clear()

            self.songs_model.layoutAboutToBeChanged.emit()
            self.filter_string = new_text
            self.songs_model.layoutChanged.emit()  # Forces the view to redraw

            self._selectSongIds(selected_ids)
        finally:
            self._holding_song_selection = False

        visible = self.getSelectedSongIds()
        song = self.current_song
        keeps_open_song = song is not None and visible in ([], [song.id])
        if not keeps_open_song and (song is not None or len(visible) == 1):
            # Several songs were selected and one is left: open it.
            self.songsSelectionChangedCallback()
        else:
            self.updateStates()

    def _selectSongIds(self, song_ids):
        """Select the rows of these songs that the filter shows."""
        selection_model = self.ui.songs_view.selectionModel()
        ids = self.songs_model.getAllSongIds()
        first = None
        for song_id in song_ids:
            if song_id not in ids:
                continue
            source_index = self.songs_model.index(ids.index(song_id), 0)
            proxy_index = self.songs_proxy_model.mapFromSource(source_index)
            if not proxy_index.isValid():
                continue
            if first is None:
                first = proxy_index
            selection_model.select(
                proxy_index, QtCore.QItemSelectionModel.SelectionFlag.Select |
                QtCore.QItemSelectionModel.SelectionFlag.Rows)
        if first is not None:
            selection_model.setCurrentIndex(
                first, QtCore.QItemSelectionModel.SelectionFlag.NoUpdate)

    def clearFilterClicked(self):
        self.ui.song_filter_ef.setText("")
        self.songFilterEdited("")

    def note(self, text):
        """A brief note at the bottom of the song view (softchord_note.py)."""
        self.brief_note.showNote(text)

    def _editModeIs(self, mode):
        return self.edit_session is not None and self.edit_session.mode == mode

    def lyricEditorSelected(self):
        """Edit Text...: start editing the lyrics of the open song."""
        was = self._editModeIs(EditSession.TEXT)
        started = self.startEdit(EditSession.TEXT)
        if started and not was and self._editModeIs(EditSession.TEXT):
            self.note("Entered text editor mode")
        return started

    def chordEditorSelected(self):
        """Edit Chords...: start editing the chords of the open song."""
        was = self._editModeIs(EditSession.CHORDS)
        started = self.startEdit(EditSession.CHORDS)
        if started and not was and self._editModeIs(EditSession.CHORDS):
            self.note("Entered chord editor mode")
        return started

    # -- Edit sessions -------------------------------------------------------

    def editing(self):
        """True between Edit Chords/Edit Text and Save or Discard."""
        return self.edit_session is not None

    def chordEditing(self):
        session = self.edit_session
        return session is not None and session.mode == EditSession.CHORDS

    def textEditing(self):
        session = self.edit_session
        return session is not None and session.mode == EditSession.TEXT

    def _currentSongText(self):
        song = self.current_song
        if song is None:
            return ""
        # Lyric edits can sit in the editor before the song has them.
        if self.editor.document() is song.doc:
            return self.editor.toPlainText()
        return song.getAllText()

    def editChanged(self):
        """True when the edit differs from the song as it was at its start.

        A change that was undone again does not count.
        """
        session = self.edit_session
        if session is None or session.song is not self.current_song:
            return False
        song = session.song
        key = SongDraft.key_of(self._currentSongText(),
                               song.iterateAllChords(), song.title,
                               song.number, song.subtitle)
        if key == session.start.key:
            return False
        if (session.mode == EditSession.VIEW
                and song.transposed_steps == session.start.transposed_steps):
            # Transposed away and back: the same notes, though a chord typed
            # as A# may now read Bb. That is the key it had, so no change.
            return key != session.start.respelledKey(self, song)
        return True

    def startEdit(self, mode):
        """Start an edit of the open song. False when it did not start."""
        song = self.current_song
        if song is None:
            self._applyEditorMode(None)
            return False
        session = self.edit_session
        if session is not None:
            if session.mode == mode or mode == EditSession.VIEW:
                # A change while viewing joins the edit that is open.
                self._applyEditorMode(session.mode)
                return True
            if session.mode == EditSession.VIEW:
                # Edit Chords or Edit Text after a transpose (or a new
                # title): the same edit goes on, one Save or Discard for all.
                session.mode = mode
                self._applyEditorMode(mode)
                self._updateEditChanged()
                self.updateStates()
                return True
            # MIRRORED UI: the web app (viewer.js switchEditing) and the iOS
            # app (SongPage.swift switchEditing) switch the same way.
            # The other kind of edit: the same edit goes on in that mode,
            # without asking. One Save or Discard keeps or drops all of it.
            # The text's own undo starts over (see _applyEditorMode); the
            # edit's undo stack goes on.
            session.mode = mode
            self._applyEditorMode(mode)
            self._updateEditChanged()
            self.updateStates()
            return True

        # Steps for another Song object must not be undone in this edit.
        self._dropSongEditSteps()

        stack = QtGui.QUndoStack(self)
        stack.canUndoChanged.connect(self.updateEditMenu)
        stack.canRedoChanged.connect(self.updateEditMenu)
        stack.indexChanged.connect(self._updateEditChanged)
        self.edit_session = EditSession(mode, song,
                                        SongDraft.capture(self, song),
                                        self.undo_stack)
        self.undo_stack = stack
        self._applyEditorMode(mode)
        self._updateEditChanged()
        self.updateStates()
        return True

    def saveEdit(self, checked=False, report=True):
        """Save: write the edit to the songbook and go back to viewing.

        False when the songbook could not be written. The edit then goes on.
        """
        session = self.edit_session
        if session is None:
            return True
        if session.song is self.current_song and self.editChanged():
            if not self._writeCurrentSong(report=report):
                return False
            self._refreshSongList()
        self._endEdit()
        if report:
            self.note("Saved")
        return True

    def discardEdit(self, checked=False):
        """Discard: put the song back as it was and go back to viewing."""
        session = self.edit_session
        if session is None:
            return
        song = session.song
        if song is self.current_song and self.editChanged():
            self._restoreSongDraft(song, session.start)
        self._endEdit()
        self.note("Changes discarded")

    def requestDiscardEdit(self, checked=False):
        """Esc: discard the edit, asking first only when something changed."""
        if self.edit_session is None:
            return
        if self.editChanged() and not self.question(
                "Discard the changes to this song?",
                button1="Discard",
                button2="Keep Editing"):
            return
        self.discardEdit()

    def confirmLeaveEdit(self):
        """Ask before anything that leaves the edit. True to go on.

        Save, Don't Save or Cancel. An edit with no changes just ends.
        """
        if self.edit_session is None:
            return True
        if not self.editChanged():
            self._endEdit()
            return True
        answer = self._askSaveChanges()
        if answer == "save":
            return self.saveEdit()
        if answer == "discard":
            self.discardEdit()
            return True
        return False

    def _leaveEditMessageBox(self):
        """The Save / Don't Save / Cancel dialog (a sheet on macOS)."""
        song = self.edit_session.song if self.edit_session else None
        title = (song.title if song is not None else "") or "Untitled"
        box = QtWidgets.QMessageBox(self.win)
        box.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        box.setWindowTitle("softChord")
        box.setText("Do you want to save the changes you made to \u201c%s\u201d?"
                    % title)
        box.setInformativeText(
            "Your changes will be lost if you don\u2019t save them.")
        buttons = QtWidgets.QMessageBox.StandardButton
        box.setStandardButtons(buttons.Save | buttons.Discard | buttons.Cancel)
        box.button(buttons.Discard).setText("Don\u2019t Save")
        box.setDefaultButton(buttons.Save)
        box.setEscapeButton(buttons.Cancel)
        box.setWindowModality(Qt.WindowModality.WindowModal)
        return box

    def _askSaveChanges(self):
        """"save", "discard" or "cancel"."""
        box = self._leaveEditMessageBox()
        result = box.exec()
        buttons = QtWidgets.QMessageBox.StandardButton
        try:
            result = buttons(result)
        except (TypeError, ValueError):
            return "cancel"
        if result == buttons.Save:
            return "save"
        if result == buttons.Discard:
            return "discard"
        return "cancel"

    def commitDataForLogout(self, manager=None):
        """Logout or shutdown: no dialog can be shown, so the edit is saved."""
        self._leaveEditSilently()

    def _leaveEditSilently(self):
        """End the edit without asking: save it, or drop it if it can't be.

        For a logout or shutdown, where no dialog can be shown, and as the
        safety net when another song is shown without asking.
        """
        if self.edit_session is None:
            return
        if not self.saveEdit(report=False):
            self._endEdit()

    def _viewDraft(self):
        """Make a change while viewing part of an edit. True when it is."""
        if self.edit_session is not None:
            return True
        return self.startEdit(EditSession.VIEW)

    def _endUnchangedViewDraft(self):
        """A change while viewing that was taken back ends by itself."""
        session = self.edit_session
        if (session is None or session.mode != EditSession.VIEW
                or self.editChanged()):
            return
        song = session.song
        if song is self.current_song:
            key = SongDraft.key_of(self._currentSongText(),
                                   song.iterateAllChords(), song.title,
                                   song.number, song.subtitle)
            if key != session.start.key:
                # Only spelled another way (A# came back as Bb): show it
                # as it was.
                self._restoreSongDraft(song, session.start)
        self._endEdit()

    def _endEdit(self):
        session = self.edit_session
        if session is None:
            return
        self.edit_session = None
        old_stack = self.undo_stack
        self.undo_stack = session.main_undo_stack
        # The edit's history goes with it. Quiet, so that deleting it does
        # not update a menu that may be gone already.
        old_stack.blockSignals(True)
        old_stack.clear()
        old_stack.deleteLater()
        self.selected_chord_nums = set()
        self.editor.cancelChordMarquee()
        self._applyEditorMode(None)
        self._updateEditChanged()
        self.updateStates()

    def _restoreSongDraft(self, song, start):
        song.title = start.title
        song.number = start.number
        song.subtitle = start.subtitle
        song.transposed_steps = start.transposed_steps
        self.ignore_song_text_changed = True
        try:
            song.setAllText(start.text,
                            [copy.copy(chord) for chord in start.chords])
            QtDocumentLayout.show_document(self.editor, song.doc)
            self.previous_song_text = song.getAllText()
        finally:
            self.ignore_song_text_changed = False
        self.selected_char_num = None
        self.selected_chord_nums = set()
        self._showSongFields(song)
        self._updateAutoDetectedKeyLabel()
        self.updateTransposeResetButton()
        self.editor.viewport().update()

    def _showSongFields(self, song):
        self.ui.song_title_ef.setText(song.title or "")
        self.ui.song_subtitle_ef.setText(song.subtitle or "")
        if song.number == -1:
            self.ui.song_num_ef.setText("")
        else:
            self.ui.song_num_ef.setText(str(song.number))

    def _refreshSongList(self):
        """Read the list again after a save. The same songs stay selected."""
        selected = self.getSelectedSongIds()
        self._holding_song_selection = True
        try:
            self.songs_model.updateFromDatabase()
            self.ui.songs_view.selectionModel().clear()
            self._selectSongIds(selected)
        finally:
            self._holding_song_selection = False

    def _updateEditChanged(self, ignored=None):
        """Mark the window and the song's row while the edit is not saved."""
        changed = self.editChanged()
        was = self._edit_changed
        self._edit_changed = changed
        self.win.setWindowModified(changed)
        session = self.edit_session
        if session is not None and session.mode == EditSession.VIEW:
            self._showSaveAndDiscard(session.mode)
            if not changed:
                # Not now: this may run inside the edit's own undo stack.
                QtCore.QTimer.singleShot(0, self._endUnchangedViewDraft)
        song = session.song if session is not None else self.current_song
        if changed != was and song is not None:
            try:
                row_num = self.songs_model.getSongsRow(song)
            except ValueError:
                pass
            else:
                self.songs_model.dataChanged.emit(
                    self.songs_model.index(row_num, 1),
                    self.songs_model.index(row_num, 1))

    def _showSaveAndDiscard(self, mode):
        """While editing. A change made while viewing shows them once it
        changes something."""
        shown = mode is not None and (
            mode != EditSession.VIEW or self.editChanged())
        mode_name = None if mode == EditSession.VIEW else mode
        self.toolbar.applyMode(mode_name, shown)

    def songHasUnsavedEdit(self, song_id):
        """The song list shows a dot on this song's row."""
        session = self.edit_session
        return (session is not None and self._edit_changed
                and session.song.id == song_id)

    def _applyEditorMode(self, mode):
        """Show viewing (mode None), Edit Chords or Edit Text."""
        lyric = mode == EditSession.TEXT
        entering_lyric = lyric and not self.editor.lyric_editor_mode

        self.editor.viewport().setCursor(
            Qt.CursorShape.IBeamCursor if lyric else Qt.CursorShape.ArrowCursor)
        self._showSaveAndDiscard(mode)
        if mode != EditSession.CHORDS:
            # Chords can be selected only in Edit Chords.
            self.selected_char_num = None
            self.selected_chord_nums = set()
            self.hover_char_num = None
            self.editor.cancelChordMarquee()

        self.editor.lyric_editor_mode = lyric
        self.editor.setUndoRedoEnabled(lyric)
        # The text undo history starts over with the chords the song has now.
        if entering_lyric or not lyric:
            self._reset_lyric_chord_history()

        self.ui.actionSaveEdit.setEnabled(mode is not None)
        self.ui.actionDiscardEdit.setEnabled(mode is not None)
        self.editor.viewport().update()
        self.updateEditMenu()
        self._updateChordButtons()

    # The selected letter or chords of Edit Chords. Setting them updates the
    # toolbar's Add/Edit chord and Delete chord buttons.
    @property
    def selected_char_num(self):
        return self.__dict__.get("_selected_char_num")

    @selected_char_num.setter
    def selected_char_num(self, value):
        self.__dict__["_selected_char_num"] = value
        self._updateChordButtons()

    @property
    def selected_chord_nums(self):
        return self.__dict__.get("_selected_chord_nums", set())

    @selected_chord_nums.setter
    def selected_chord_nums(self, value):
        self.__dict__["_selected_chord_nums"] = value
        self._updateChordButtons()

    def _updateChordButtons(self, *args):
        toolbar = self.__dict__.get("toolbar")
        if toolbar is None or sip.isdeleted(toolbar):
            return
        letter = self.selected_char_num is not None and self.chordEditing()
        chord = letter and self.getSelectedChord() is not None
        toolbar.updateChordButtons(
            letter, chord, chord or bool(self.selected_chord_nums))

    def editChordFromToolbar(self, checked=False):
        """Add/Edit chord: the selected chord, else a new one at the letter."""
        if not self.chordEditing() or self.selected_char_num is None:
            return
        self.processSongCharEdit(self.selected_char_num)
        self._updateChordButtons()

    def __del__(self):
        pass

    def _updateAutoDetectedKeyLabel(self):
        label = getattr(self.ui, "auto_detected_key_label", None)
        if label is None:
            return
        if self.current_song is None:
            text = "Auto-detected key:"
        else:
            text = format_auto_detected_key_text(self.current_song._regions)
        label.setText(text)
        label.setToolTip(text)
        # Notes field is expanding; keep the full "Am, Bm" string visible.
        label.setMinimumWidth(label.fontMetrics().horizontalAdvance(text) + 12)

    def closeEvent(self, event):
        # Quit, Command-Q and the close button all come here.
        if not self.confirmLeaveEdit():
            event.ignore()
            return
        self._flushCurrentSong()
        if not self._confirm_close_of_converted_copy():
            event.ignore()
            return
        self._orig_closeEvent(event)

    def _confirm_close_of_converted_copy(self):
        """True when the window may close.

        TODO(remove-v1-compat): an old-format songbook that could not be
        converted in place was opened as a temporary copy. Closing would lose
        the edits made to it, so offer Save As first.
        """
        if self.songbook_original_path is None:
            return True
        conn = self.store.connection
        if conn is None or conn.total_changes == 0:
            return True
        if not self.question(
                "Your changes are in a temporary converted copy. The original "
                "songbook was not changed:\n%s\n\nSave the copy now?" %
                self.songbook_original_path,
                button1="Save As...",
                button2="Close Without Saving"):
            return True
        self.saveSongbook()
        # Still the copy when the user cancelled the Save As dialog.
        return self.songbook_original_path is None

    def _rollback_songbook(self):
        conn = self.store.connection
        if conn is None:
            return
        try:
            conn.rollback()
        except sqlite3.Error:
            pass

    def _reopen_songbook_connection(self):
        """Open the same path again. A replaced file leaves the old connection stale."""
        return self.store.reopen()

    def _report_readonly_songbook(self):
        if self._readonly_songbook_reported:
            return
        self._readonly_songbook_reported = True
        self.error(
            "Cannot modify this songbook because it is read-only.\n\n"
            "Use File → Save Songbook As... to save a writable copy.")

    def _run_songbook_write(self, write, report=True):
        """Run write() and commit. Return False when the file cannot be modified.

        Switching songs still calls this to flush. That failure is not reported:
        viewing a read-only songbook must not raise, and the edit that was just
        refused already explains why.
        """
        for attempt in (1, 2):
            try:
                write()
                self.store.commit()
                return True
            except sqlite3.OperationalError as err:
                self._rollback_songbook()
                if (database_file_was_replaced(err) and attempt == 1
                        and self._reopen_songbook_connection()):
                    continue
                if readonly_database_error(err):
                    if report:
                        self._report_readonly_songbook()
                    return False
                raise
        return False

    def _flushCurrentSong(self):
        """Write the open song before a switch, print or export.

        Not during an edit: the edit is written only by Save.
        """
        if self.edit_session is not None:
            return
        self.sendCurrentSongToDatabase()

    def sendCurrentSongToDatabase(self):
        """
        Save the current song to the database.
        """
        self._writeCurrentSong(report=False)

    def _writeCurrentSong(self, report=False):
        """Write the open song. False when the songbook was not written."""
        if not self.current_song:
            return True
        song = self.current_song
        # Lyric edits can sit in the editor until this save. Copy them into
        # the song first so getAllText() is the text about to be written.
        if self.editor.document() is song.doc:
            song.text = self.editor.toPlainText()

        def write():
            chords_in_database = self.store.chord_positions(song.id)

            for chord in song.iterateAllChords():
                # Update existing chords
                if chord.character_num in chords_in_database:
                    self.store.update_chord(chord.song_id, chord.character_num,
                                            chord.getStoredText())
                    chords_in_database.remove(chord.character_num)

                else:
                    # Add new chords
                    self.store.insert_chord(chord.song_id, chord.character_num,
                                            chord.getStoredText())

            # Remove old chords
            for song_char_num in chords_in_database:
                self.store.delete_chord(song.id, song_char_num)

            self.store.update_song(song.id, song.number, song.title,
                                   song.subtitle, song.getAllText())

        self.setWaitCursor()
        try:
            # Song switches flush even when nothing changed, and a read-only
            # file must stay browsable, so only Save reports a failure.
            return self._run_songbook_write(write, report=report)
        finally:
            self.restoreCursor()

    def getSelectedChord(self):
        """
        Return the selected chord, or None, if no selection or the selected
        character has no chord assigned to it.
        """

        if self.selected_char_num != None and self.current_song:
            for chord in self.current_song.iterateAllChords():
                if chord.character_num == self.selected_char_num:
                    return chord
        return None

    def deleteSelectedChord(self):
        """
        Deletes the currently selected chord from the song.
        """

        count = self._deleteSelectedChords()
        if count:
            self.note("Chords deleted" if count > 1 else "Chord deleted")
            return

        chord = self.getSelectedChord()
        if chord:
            # The spaces only this chord needed at the end of its line go too.
            song = self.current_song
            others = [other for other in song.iterateAllChords()
                      if other is not chord]
            text, gaps = tidy_chord_room(
                song.getAllText(), [other.character_num for other in others],
                (chord.character_num, ))
            self.note("Chord deleted")
            if not gaps:
                song.deleteChord(chord)
                return
            song.setTextAndChords(
                text, self._chordsAt(
                    [(other, tidy_moved(gaps, other.character_num))
                     for other in others])[0],
                tidy_moved(gaps, chord.character_num))

    def _deleteSelectedChords(self):
        """Delete every marquee-selected chord as one undo step."""
        if not self.selected_chord_nums or self.current_song is None:
            return False
        chords = [
            chord for chord in self.current_song.iterateAllChords()
            if chord.character_num in self.selected_chord_nums
        ]
        if not chords:
            return False
        self.undo_stack.beginMacro("delete chords")
        for chord in chords:
            self.current_song.deleteChord(chord)
        self.undo_stack.endMacro()
        self.selected_chord_nums = set()
        self.selected_char_num = None
        self.editor.viewport().update()
        return len(chords)

    @staticmethod
    def _chordsAt(moves):
        """(chords, copies): the chords at their new positions, a copy for each
        one that moves; copies maps an old chord to its copy."""
        chords = []
        copies = {}
        for chord, position in moves:
            if position != chord.character_num:
                moved = copy.copy(chord)
                moved.character_num = position
                copies[id(chord)] = moved
                chord = moved
            chords.append(chord)
        return chords, copies

    def placeChord(self, chord, landing, room=None):
        """Move chord onto landing, as one undo step: (moved chord, where).

        landing is a letter of room's text (softchord_text.chord_room, by
        default the song's text as it is). The lines the chord left and went
        to lose the spaces at their end that no chord needs, so the text can
        change with the chords. where(position) is where a position of room's
        text is now.

        MIRRORED: softchord_chord_mode.js nudge and dragTo, SongPage.swift
        moveChord (both with SongChordEdit / SongLyricChords withRoom, tidied).
        """
        song = self.current_song
        text = song.getAllText()
        room_text, at, count = room or (text, len(text), 0)

        def shifted(position):
            return position + count if position >= at else position

        moves = [(other, landing if other is chord
                  else shifted(other.character_num))
                 for other in song.iterateAllChords()]
        new_text, gaps = tidy_chord_room(
            room_text, [position for _, position in moves],
            (shifted(chord.character_num), landing))

        def where(position):
            return tidy_moved(gaps, position)

        final = where(landing)
        if new_text == text:
            moved = copy.copy(chord)
            moved.character_num = final
            song.replaceChord(chord, moved)
            return moved, where
        chords, copies = self._chordsAt(
            [(other, where(position)) for other, position in moves])
        song.setTextAndChords(new_text, chords, final)
        return copies.get(id(chord), chord), where

    def dragChordPastLineEnd(self, editor, line_end, distance):
        """The dragged chord, with the pointer distance pixels right of the
        line that ends at line_end: the line gets spaces for it, up to
        CHORD_ROOM past its last letter."""
        song = self.current_song
        chord = editor.dragging_chord
        text = song.getAllText()
        last = line_end - 1
        if chord is None or last < 0 or text[last] == "\n":
            return
        room = chord_room(text, last)
        room_text, at, count = room
        span = line_letter_range(room_text, last)
        width = max(1.0, QtGui.QFontMetricsF(
            song.doc.defaultFont()).horizontalAdvance(" "))
        target = min(span[1], last + max(1, math.ceil(distance / width)))
        if target == editor.dragging_mouse_char:
            return
        occupied = {
            other.character_num + (count if other.character_num >= at else 0)
            for other in song.iterateAllChords() if other is not chord
        }
        landing = next_free_character(room_text, target, 1, occupied, True)
        current = chord.character_num + (count if chord.character_num >= at else 0)
        if landing is None or landing == current:
            return
        moved, where = self.placeChord(chord, landing, room)
        editor.dragging_chord = moved
        editor.dragging_mouse_char = where(target)
        editor._followReplaced(where)
        self.hover_char_num = moved.character_num
        self.selected_char_num = moved.character_num

    def freeCharacterForChord(self, chord, target, direction,
                              allow_other_direction):
        """The letter chord lands on when it is moved onto target.

        A letter that has another chord is jumped over, so a chord is never
        lost and a letter never has two. None means the chord stays.
        """
        occupied = {
            other.character_num
            for other in self.current_song.iterateAllChords()
            if other is not chord
        }
        return next_free_character(self.current_song.getAllText(), target,
                                   direction, occupied, allow_other_direction)

    def _nudgeSelectedChords(self, delta):
        """Move every selected chord by one letter, as one undo step.

        The chord furthest along the move goes first, so two neighbors do
        not land on each other. A chord that would leave its line stays put.
        A letter that has a chord (selected or not) is jumped over, to the
        next free letter on the line in the same direction.
        """
        song = self.current_song
        if song is None:
            return
        chords = [
            chord for chord in song.iterateAllChords()
            if chord.character_num in self.selected_chord_nums
        ]
        if not chords:
            return
        text = song.getAllText()
        occupied = {chord.character_num for chord in song.iterateAllChords()}
        chords.sort(key=lambda chord: chord.character_num, reverse=delta > 0)
        moves = []
        for chord in chords:
            occupied.discard(chord.character_num)
            new_num = next_free_character(text, chord.character_num + delta,
                                          delta, occupied)
            if new_num is None:
                occupied.add(chord.character_num)
                continue
            occupied.add(new_num)
            moves.append((chord, new_num))
        if not moves:
            return
        self.undo_stack.beginMacro("move chords")
        for chord, new_num in moves:
            new_chord = copy.copy(chord)
            new_chord.character_num = new_num
            song.replaceChord(chord, new_chord)
        self.undo_stack.endMacro()
        self.selected_char_num = None

    def processKeyPressed(self, key):
        """
        Returns True if the key press was processed
        """

        if self.selected_chord_nums and key in (Qt.Key.Key_Left,
                                                Qt.Key.Key_Right):
            delta = -1 if key == Qt.Key.Key_Left else 1
            self._nudgeSelectedChords(delta)
            return True

        if self.selected_char_num == None:
            return False

        if key in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            # Move the selected chord. A chord that is moved onto a letter
            # that has a chord jumps over it, so a letter never has two
            # chords. (Old songs may still have two. The one created last is
            # the one that moves.) Up and Down do nothing.
            prev_chord = self.current_song.getChordAtPosition(self.selected_char_num)

            if prev_chord:
                # A letter that has a chord is jumped over. No free letter on
                # the line that way (or a line break) means the chord stays.
                # Right of the last letter there is room (chord_room).
                direction = -1 if key == Qt.Key.Key_Left else 1
                song = self.current_song
                room = chord_room(song.getAllText(), prev_chord.character_num)
                room_text, at, count = room
                occupied = {
                    other.character_num + (count if other.character_num >= at else 0)
                    for other in song.iterateAllChords()
                    if other is not prev_chord
                }
                landing = next_free_character(
                    room_text, prev_chord.character_num + direction,
                    direction, occupied, False)
                if landing is None:
                    return False
                self.placeChord(prev_chord, landing, room)
                return True

        # Determine if "m" key is pressed:
        if key == Qt.Key.Key_M:
            prev_chord = None
            for iter_chord in self.current_song.iterateAllChords():
                if iter_chord.character_num == self.selected_char_num:
                    prev_chord = iter_chord
                    break

            if prev_chord and not prev_chord.unknown:
                # Chord already exists, flip major/minor
                new_chord = copy.copy(prev_chord)
                if new_chord.chord_type_id == 0:
                    new_chord.chord_type_id = 1
                else:
                    new_chord.chord_type_id = 0
                self.current_song.replaceChord(prev_chord, new_chord)
                return True
            return False

        # Determine if a note key was pressed:
        key_note_dict = {
            Qt.Key.Key_C: 0,
            Qt.Key.Key_D: 2,
            Qt.Key.Key_E: 4,
            Qt.Key.Key_F: 5,
            Qt.Key.Key_G: 7,
            Qt.Key.Key_A: 9,
            Qt.Key.Key_B: 11,
        }
        note_id = key_note_dict.get(key)
        if note_id == None:
            return False

        # Check whether we are editing an existing chord or adding a new one:
        add_new = True
        prev_chord = None
        for iter_chord in self.current_song.iterateAllChords():
            if iter_chord.character_num == self.selected_char_num:
                add_new = False
                prev_chord = iter_chord
                break

        if add_new:
            chord_type_id = 0  # Major
            new_chord = SongChord(self.current_song, self.selected_char_num,
                                  note_id, chord_type_id, -1, "", False)
            self.current_song.addChord(new_chord)
        else:
            new_chord = copy.copy(prev_chord)

            # Change this chord to <note> major:
            new_chord.note_id = note_id
            new_chord.chord_type_id = 0
            new_chord.marker = ""
            new_chord.in_parentheses = False
            self.current_song.replaceChord(prev_chord, new_chord)

        return True

    def _using_lyric_undo(self):
        """Text mode undoes letters. Chord mode undoes the chord stack."""
        return self.current_song is not None and self.editor.lyric_editor_mode

    def undo(self):
        if self._using_lyric_undo():
            can = self.editor.document().isUndoAvailable()
            self.editor.undo()
        else:
            can = self.undo_stack.canUndo()
            self.undo_stack.undo()
        self.editor.viewport().update()
        if can:
            self.note("Undone")

    def redo(self):
        if self._using_lyric_undo():
            can = self.editor.document().isRedoAvailable()
            self.editor.redo()
        else:
            can = self.undo_stack.canRedo()
            self.undo_stack.redo()
        self.editor.viewport().update()
        if can:
            self.note("Redone")

    def updateEditMenu(self, ignored1=None, ignored2=None):
        # An edit's undo history can outlive the window at exit.
        if sip.isdeleted(self.ui.actionUndo):
            return

        focus_widget = QtWidgets.QApplication.focusWidget()  # FIXME implement this properly

        enable_paste = False
        try:
            text = self.clipboard.text()
        except RuntimeError:
            # The application clipboard is already destroyed.
            return

        try:
            if self.current_song:
                if self.editor.lyric_editor_mode:
                    # The Edit menu follows the letter undo, same as Command-Z
                    # in the lyric editor. Chord edits stay on the other stack.
                    document = self.editor.document()
                    undo_possible = document.isUndoAvailable()
                    redo_possible = document.isRedoAvailable()
                    enable_paste = bool(text)
                elif not self.chordEditing():
                    undo_possible = self.undo_stack.canUndo()
                    redo_possible = self.undo_stack.canRedo()
                else:
                    # In chord editor
                    undo_possible = self.undo_stack.canUndo()
                    redo_possible = self.undo_stack.canRedo()
                    # FIXME Enable paste only if CHORD text is selected:
                    try:
                        self.convertChordFromString(text)
                    except ValueError:
                        pass
                    else:
                        enable_paste = True
            else:
                # Not currently editing a song:
                undo_possible = self.undo_stack.canUndo()
                redo_possible = self.undo_stack.canRedo()
        except RuntimeError:
            # C++ QUndoStack has been deleted
            return

        self.ui.actionUndo.setEnabled(undo_possible)
        self.ui.actionRedo.setEnabled(redo_possible)
        self.ui.actionPaste.setEnabled(enable_paste)

    def clearUndoStack(self):
        self.undo_stack.clear()

    def _dropSongEditSteps(self):
        """Forget the chord and transpose steps when another song is shown.

        Those steps edit one Song object. Undo after a switch would change that
        old object and then save the song on screen. Steps for the whole songbook
        (delete, import, renumber, trailing spaces) stay as long as no song step
        is on the stack with them.
        """
        stack = self.undo_stack

        def song_step(command):
            if getattr(command, "song_scoped", False):
                return True
            return any(song_step(command.child(index))
                       for index in range(command.childCount()))

        if self.current_song is not None and any(
                song_step(stack.command(index)) for index in range(stack.count())):
            stack.clear()

    def updateChordLineSpacing(self, song):
        """Give chord lines their extra space and repaint.

        Chord commands call this. A drag is one undo step made of many
        commands, and each of those has to update the spacing immediately.
        """
        if self.current_song is not song:
            return
        QtDocumentLayout.apply_margins(song, self)
        self.editor.viewport().update()

    def warning(self, text):
        QtWidgets.QMessageBox.warning(self.win, "Warning", text)

    def info(self, text):
        QtWidgets.QMessageBox.information(self.win, "Info", text)

    def error(self, text):
        QtWidgets.QMessageBox.warning(self.win, "Error", text)

    def setWaitCursor(self):
        """ Set the mouse cursor to the watch """
        self.win.setCursor(QtGui.QCursor(Qt.CursorShape.WaitCursor))

    def restoreCursor(self):
        """ Set the mouse cursor to the default arrow. """
        self.win.setCursor(Qt.CursorShape.ArrowCursor)

    def songsSelectionChangedCallback(self, selected=None, deselected=None):
        """
        Called when the song selection changes.
        """
        if self._holding_song_selection:
            return
        session = self.edit_session
        if session is not None:
            target = self.getSelectedSongIds()
            if target == [session.song.id]:
                return
            if self.editChanged():
                # Show the edited song selected again, then ask. Asking after
                # this click or key press is done keeps the list's own
                # handling of it out of the dialog.
                self._putSongSelectionBack()
                first = self._pending_song_selection is None
                self._pending_song_selection = target
                if first:
                    QtCore.QTimer.singleShot(
                        0, self._resolvePendingSongSelection)
                return
            self._endEdit()

        # Commit any changes in the current song:
        if self.store.is_open:
            self.store.commit()

        self.selected_char_num = None  # Remove the selection
        self.selected_chord_nums = set()
        self.hover_char_num = None  # Remove the hover highlighting
        editor = getattr(self, "editor", None)
        if editor is not None:
            editor.cancelChordMarquee()

        sel_indecies = self.ui.songs_view.selectedIndexes()
        num_selected = len(sel_indecies) / self.songs_model.columnCount()

        self.setWaitCursor()
        if num_selected == 1:
            index = sel_indecies[0]
            index = self.songs_proxy_model.mapToSource(index)
            song_id = self.songs_model.getRowSongID(index.row())
            song = Song(self, song_id)
            self.setCurrentSong(song)
        else:
            self.setCurrentSong(None)

        self.updateStates()
        self.restoreCursor()

    def _putSongSelectionBack(self):
        song = self.edit_session.song if self.edit_session else self.current_song
        self._holding_song_selection = True
        try:
            self.ui.songs_view.selectionModel().clear()
            if song is not None:
                self._selectSongIds([song.id])
        finally:
            self._holding_song_selection = False
        self.ui.songs_view.viewport().update()

    def _resolvePendingSongSelection(self):
        """Ask about the edit, then select what was picked (unless Cancel)."""
        target = self._pending_song_selection
        self._pending_song_selection = None
        if target is None:
            return
        if not self.confirmLeaveEdit():
            return
        self._holding_song_selection = True
        try:
            self.ui.songs_view.selectionModel().clear()
            self._selectSongIds(target)
        finally:
            self._holding_song_selection = False
        self.songsSelectionChangedCallback()

    def getSelectedSongIds(self):
        """
        Returns a list of selected songs (their song_ids)
        """

        selected_song_ids = []
        for index in self.ui.songs_view.selectionModel().selectedRows():
            index = self.songs_proxy_model.mapToSource(index)
            song_id = self.songs_model.getRowSongID(index.row())
            selected_song_ids.append(song_id)
        return selected_song_ids

    def _songForOutput(self, song_id):
        """A song to print or export, as it is on screen.

        During an edit the open song is the unsaved edit. Output uses it, and
        the songbook is not written.
        """
        song = Song(self, song_id)
        current = self.current_song
        if (self.edit_session is not None and current is not None
                and current.id == song_id):
            song.title = current.title
            song.number = current.number
            song.subtitle = current.subtitle
            song.transposed_steps = current.transposed_steps
            chords = [
                SongChord.from_text(song, chord.character_num,
                                    chord.getStoredText())
                for chord in current.iterateAllChords()
            ]
            song.setAllText(self._currentSongText(), chords)
        return song

    def singleExportSong(self, song_ids):
        """The song being printed or exported, when there is exactly one."""
        if len(song_ids) != 1:
            return None
        song_id = song_ids[0]
        if self.current_song is not None and self.current_song.id == song_id:
            return self.current_song
        return Song(self, song_id)

    def updateStates(self):
        """
        Enable / disable buttons and other widgets as needed.
        """

        # FIXME there is a faster way of doing this:
        num_selected = len(self.getSelectedSongIds())

        if self.current_song == None:
            self.ui.song_title_ef.setText("")
            self.ui.song_num_ef.setText("")

        self.editor.setEnabled(self.current_song != None)
        self.ui.song_title_ef.setEnabled(self.current_song != None)
        self.ui.song_num_ef.setEnabled(self.current_song != None)
        self._updateAutoDetectedKeyLabel()
        self.toolbar.transpose_up.setEnabled(self.current_song != None)
        self.toolbar.transpose_down.setEnabled(self.current_song != None)
        self.updateTransposeResetButton()
        self.ui.actionChordEditorMode.setEnabled(self.current_song != None)
        self.ui.actionLyricEditorMode.setEnabled(self.current_song != None)

        self.ui.actionDeleteSongs.setEnabled(num_selected > 0)
        self.ui.actionRemoveTrailingSpaces.setEnabled(num_selected > 0)
        self.ui.actionDeleteSong.setEnabled(num_selected == 1)

        songs_present = self.songs_model.rowCount() > 0

        self.ui.actionExportSinglePdf.setEnabled(songs_present)
        self.ui.actionExportMultiplePdfs.setEnabled(songs_present and
                                                    num_selected != 1)

        self.ui.menuSong.setEnabled(num_selected == 1)  # not working?
        self.ui.actionExportText.setEnabled(num_selected == 1)
        self.ui.actionExportSongToPdf.setEnabled(num_selected == 1)
        self.ui.actionExportChordPro.setEnabled(num_selected == 1)
        self.ui.actionCopySongText.setEnabled(num_selected == 1)
        self.ui.actionCopySongTextWithChords.setEnabled(num_selected == 1)
        self.ui.actionCopySongAsImage.setEnabled(num_selected == 1)
        self.ui.actionExportClipboard.setEnabled(num_selected == 1)

        self.ui.actionPrint.setEnabled(songs_present)

        # FIXME instead link it to either the lyric editror select-all, or the songs table
        self.ui.actionSelectAll.setEnabled(False)

        # Whether there is an open songbook:
        songbook_open = self.store.is_open
        self.ui.actionImportText.setEnabled(songbook_open)

        self.ui.actionNewSong.setEnabled(songbook_open)

        self.ui.actionCloseSongbook.setEnabled(songbook_open)
        self.ui.actionSaveSongbook.setEnabled(songbook_open)
        self.ui.actionAppendSongbook.setEnabled(songbook_open)

        self.updateEditMenu()

    def setCurrentSong(self, song):
        """
        Sets the current song to the specified song.
        Reads all song info from the database.
        """

        if self.current_song == None and song == None:
            return

        # Callers ask about an unsaved edit first. Never lose one here.
        self._leaveEditSilently()
        self._dropSongEditSteps()
        self._flushCurrentSong()

        if self.current_song != None:
            # Clearing the shared document notifies the editor. That is not
            # a lyric edit, and it has to happen before the new song is current.
            self.ignore_song_text_changed = True
            try:
                QtDocumentLayout.release_editor_document(
                    self.editor, self.current_song)
            finally:
                self.ignore_song_text_changed = False

        if song == None:
            self.current_song = None
            self.previous_song_text = None
            self.ui.song_num_ef.setText("")
            self.updateTransposeResetButton()

            # NOTE: Messing with this stuff may cause the app to crash on Windows (compiled)
            QtDocumentLayout.show_document(self.editor, self.empty_doc)
            self.editor.verticalScrollBar().setValue(0)
            self._updateAutoDetectedKeyLabel()

        else:
            self.current_song = song
            self._updateAutoDetectedKeyLabel()
            self.updateTransposeResetButton()

            if not self.ignore_song_text_changed:
                song_text = self.current_song.getAllText()
                self.ignore_song_text_changed = False
                self.previous_song_text = song_text

            self.ui.song_title_ef.setText(self.current_song.title)
            self.ui.song_subtitle_ef.setText(self.current_song.subtitle)

            if self.current_song.number == -1:
                self.ui.song_num_ef.setText("")
            else:
                self.ui.song_num_ef.setText(str(self.current_song.number))

            song.doc.setDefaultFont(self.lyrics_font)
            # Line spacing lives in the layout. The copy kept after leaving
            # this song does not have that layout yet.
            QtDocumentLayout.apply_margins(song, self)

            # NOTE: Messing with this stuff may cause the app to crash on Windows (compiled)
            QtDocumentLayout.show_document(self.editor, song.doc)

            self.editor.verticalScrollBar().setValue(0)

        # The text undo stack belongs to the document just shown.
        self._reset_lyric_chord_history()

    def _transposeCurrentSong(self, steps):
        """
        Transpose the current song up by the specified number of steps.
        """

        song = self.current_song
        if song is None or not song.has_transposable_chords():
            return
        # While viewing, a transpose is a change to Save or Discard.
        if not self._viewDraft():
            return
        self.undo_stack.push(TransposeSongCommand(song, steps))
        self.note(self._transposedNote(
            "Transposed up" if steps > 0 else "Transposed down", " to "))

    def _transposedNote(self, text, joiner):
        """iOS SongPage.transposedNote: with the key the chords are now in."""
        song = self.current_song
        chords = [c for c in song.iterateAllChords() if not c.unknown]
        key = best_detected_key(chords) if chords else None
        if key is None or key.score <= 0:
            return text
        return text + joiner + key.label

    def updateTransposeResetButton(self):
        """Reset is on only when the open song is not in the key it was loaded in."""
        song = self.current_song
        self.toolbar.transpose_reset.setEnabled(
            song is not None and song.transposed_steps != 0)

    def transposeReset(self):
        """Transpose the open song back to the key it had when it was loaded.

        "Loaded" is when the song was last selected in the list (each selection reads
        the song from the songbook). The song counts its net steps since then, so
        this is one transpose by the opposite number of steps. It is one undo step.
        Chords that were added or retyped after transposing are moved with the rest,
        and chord edits do not change the count, so Reset always means "the whole
        song as many half steps back as it was moved", and never throws edits away.
        """
        song = self.current_song
        if song is None or song.transposed_steps == 0:
            return
        if not self._viewDraft():
            return
        self.undo_stack.push(
            TransposeSongCommand(song, -song.transposed_steps, "reset transpose"))
        self.note(self._transposedNote("Transposed back to original key", ", "))

    def _onLyricUndoCommandAdded(self):
        # Undo and redo do not emit this. A document that is no longer shown
        # must not mark the edit either.
        if self.sender() is self.editor.document():
            self._lyric_new_command = True

    def _watch_lyric_undo_document(self):
        doc = self.editor.document()
        if doc is None or doc is self._lyric_undo_doc:
            return
        # Leave the previous document connected. Switching songs can delete
        # it, and a signal from it is ignored above.
        self._lyric_undo_doc = doc
        doc.undoCommandAdded.connect(self._onLyricUndoCommandAdded)

    def _lyric_undo_index(self):
        doc = self.editor.document()
        if doc is None or not doc.isUndoRedoEnabled():
            return 0
        return doc.availableUndoSteps()

    def _capture_lyric_chords(self):
        # The number is kept beside the chord. Later edits move the same
        # object, and this number has to stay as it was at this undo step.
        return [(chord, chord.character_num)
                for chord in self.current_song._chords]

    def _restore_lyric_chords(self, captured):
        restored = []
        for chord, character_num in captured:
            chord.character_num = character_num
            restored.append(chord)
        self.current_song._chords = restored

    def _reset_lyric_chord_history(self):
        """The chords on the song now match the lyrics in the editor."""
        self._lyric_new_command = False
        self._lyric_chord_snapshots = {}
        self._watch_lyric_undo_document()
        steps = self._lyric_undo_index()
        self._lyric_undo_steps = steps
        if self.current_song is not None:
            self._lyric_chord_snapshots[steps] = self._capture_lyric_chords()

    def _lyric_renumber_map(self, song_text):
        # For each character: key: old position, value: new position
        return lyric_renumber_map(self.previous_song_text, song_text)

    def _remap_lyric_selection(self, renumber_map):
        if self.selected_char_num != None:
            self.selected_char_num = renumber_map.get(self.selected_char_num)
        if self.selected_chord_nums:
            self.selected_chord_nums = {
                renumber_map[num]
                for num in self.selected_chord_nums if num in renumber_map
            }

    def _renumber_lyric_chords(self, renumber_map):
        kept = []
        for chord in self.current_song.iterateAllChords():
            try:
                chord.character_num = renumber_map[chord.character_num]
            except KeyError:
                continue
            kept.append(chord)
        self.current_song._chords = kept

    def _sync_lyric_chords(self, new_command, song_text):
        """Move chords with the text editor's undo stack.

        song_text is None when this notification is not a lyric edit.
        """
        steps = self._lyric_undo_index()
        previous = self._lyric_undo_steps
        snaps = self._lyric_chord_snapshots

        if self.current_song is None:
            self._lyric_chord_snapshots = {}
            self._lyric_undo_steps = steps
            return

        text_changed = (song_text is not None
                        and self.previous_song_text is not None
                        and song_text != self.previous_song_text)
        if previous not in snaps:
            snaps[previous] = self._capture_lyric_chords()

        # One step back is undo, a step forward without a new edit is redo.
        if text_changed and not new_command and (steps == previous - 1
                                                  or steps > previous):
            saved = snaps.get(steps)
            if saved is not None:
                self._remap_lyric_selection(
                    self._lyric_renumber_map(song_text))
                self._restore_lyric_chords(saved)
                self._lyric_undo_steps = steps
                return

        if text_changed:
            if not new_command and steps < previous:
                # The undo stack was cleared (the text was replaced wholesale).
                snaps = {}
                self._lyric_chord_snapshots = snaps
            renumber_map = self._lyric_renumber_map(song_text)
            self._remap_lyric_selection(renumber_map)
            self._renumber_lyric_chords(renumber_map)

        if new_command:
            for key in list(snaps):
                if key > steps:
                    del snaps[key]

        if text_changed or new_command:
            snaps[steps] = self._capture_lyric_chords()
        self._lyric_undo_steps = steps

    def lyricsTextChanged(self):
        """
        Called when the song lyric text is modified by the user.
        Removes all chords that were associated with any text that was deleted,
        and adjusts positions of all chords that were affected by the change.
        Undoing that edit puts those chords back on the restored characters.
        """

        new_command = self._lyric_new_command
        self._lyric_new_command = False

        if self.ignore_song_text_changed or not self.current_song:
            self._sync_lyric_chords(new_command, None)
            return

        if self.editor.document() is not self._lyric_undo_doc:
            self._reset_lyric_chord_history()
            new_command = False

        self.ignore_song_text_changed = True
        try:
            song_text = self.editor.toPlainText()
            previous_text = self.previous_song_text
            self._sync_lyric_chords(new_command, song_text)
            self.current_song.text = song_text
            self.previous_song_text = song_text
            # The lines that have chords may be other lines now (Enter, or
            # joining two lines), and so the space above them has to move.
            if song_text != previous_text:
                QtDocumentLayout.apply_margins(self.current_song, self)
        finally:
            self.ignore_song_text_changed = False
        if self.edit_session is not None:
            self._updateEditChanged()

    def zoomIn(self, checked=False):
        self.zoom_pos = min(self.zoom_pos + 1, len(self.zoom_levels) - 1)
        self.updateZoomWidgets()
        self._zoomNote()

    def zoomOut(self, checked=False):
        self.zoom_pos = max(self.zoom_pos - 1, 0)
        self.updateZoomWidgets()
        self._zoomNote()

    def zoomActual(self, checked=False):
        """
        Set zoom level to 100%
        """
        self.zoom_pos = self.zoom_levels.index(1.0)
        self.updateZoomWidgets()
        self._zoomNote()

    def _zoomNote(self):
        self.note("Zoom %d%%" % round(self.zoom_factor * 100.0))

    def updateZoomWidgets(self):

        pos = self.zoom_pos
        self.zoom_factor = self.zoom_levels[pos]
        self.toolbar.setZoomPercent(round(self.zoom_factor * 100.0))
        self.updateEditorFonts()

        enable_zoom_in = (pos != len(self.zoom_levels) - 1)
        enable_zoom_out = (pos != 0)
        enable_zoom_actual = (self.zoom_levels[pos] != 1.0)

        self.ui.actionZoomIn.setEnabled(enable_zoom_in)
        self.ui.actionZoomOut.setEnabled(enable_zoom_out)
        self.ui.actionZoomActual.setEnabled(enable_zoom_actual)

    def getHeightsWithChords(self):

        cfm = self.chords_font_metrics
        lfm = self.lyrics_font_metrics

        lyrics_height = lfm.height()
        chords_height = cfm.height()

        line_height = (lyrics_height +
                       cfm.ascent()) - lfm.leading() - cfm.leading()

        return chords_height, lyrics_height, line_height

    def getHeightsWithoutChords(self):

        lyrics_height = self.lyrics_font_metrics.height()
        chords_height = 0.0
        line_height = lyrics_height

        return chords_height, lyrics_height, line_height

    def transposeUp(self):
        self._transposeCurrentSong(1)

    def transposeDown(self):
        self._transposeCurrentSong(-1)

    def changeChordFont(self):
        """
        Brings up a dialog to let the user modify the chords font.
        """

        # Make a copy:
        new_font = QtGui.QFont(self.chords_font)

        new_font, ok = QtWidgets.QFontDialog.getFont(new_font, self.win)
        if ok:
            self.chords_font_size = new_font.pointSizeF()
            self.chords_font = new_font
            self.updateEditorFonts()
            self.note("Chords font changed")

    def changeLyricsFont(self):
        """
        Brings up a dialog to let the user modify the lyrics font.
        """

        # Make a copy:
        new_font = QtGui.QFont(self.lyrics_font)

        new_font, ok = QtWidgets.QFontDialog.getFont(new_font, self.win)
        if ok:
            self.lyrics_font_size = new_font.pointSizeF()
            self.lyrics_font = new_font
            self.updateEditorFonts()
            self.note("Lyrics font changed")

    def updateEditorFonts(self):
        """
        Update the font metrics, because either the font(s) has changed, or the zoom
        level was changed.
        """

        # Update the lyrics font:
        self.lyrics_font.setPointSizeF(self.lyrics_font_size * self.zoom_factor)
        self.lyrics_font_metrics = QtGui.QFontMetricsF(self.lyrics_font)
        self.editor.setFont(self.lyrics_font)

        if self.current_song:
            QtDocumentLayout.apply_margins(self.current_song, self)
        self.editor.viewport().update()

        # Update the chords fonts:
        self.chords_font.setPointSizeF(self.chords_font_size * self.zoom_factor)
        self.chords_font_metrics = QtGui.QFontMetricsF(self.chords_font)

        self.symbols_font.setPointSizeF(self.chords_font_size *
                                        self.zoom_factor)
        self.symbols_font_metrics = QtGui.QFontMetricsF(self.symbols_font)

        if self.current_song:
            QtDocumentLayout.apply_margins(self.current_song, self)
        self.editor.viewport().update()

    def printSelectedSongs(self):
        """
        Bring up a print dialog box.
        """

        self._flushCurrentSong()

        if not self.songs_model.rowCount():
            self.error("There are no songs to print")
            return

        printer = QPrinter()
        printer.setFullPage(True)
        #printer.setPageSize(QPageSize.Letter)
        printer.setPageOrientation(QtGui.QPageLayout.Orientation.Portrait)

        print_dialog = QPrintDialog(printer, self.win)
        if print_dialog.exec():  # accepted
            song_ids = self.getSelectedSongIds()
            if not song_ids:
                # No selection, print the whole song book
                song_ids = self.songs_model.getAllSongIds()

            ok = PdfDialog(self).display(
                self.pdf_options,
                single_pdf_export=True,
                song=self.singleExportSong(song_ids),
                printer=printer)
            if not ok:
                return

            try:
                self.printSongsToPrinter(song_ids, printer,
                                                       "Printing...")
                self.note("Sent to printer")
            except Exception as err:
                self.error("Error printing:\n\n%s " % traceback.format_exc())

    def printSongsToPrinter(self, song_ids, printer, progress_message):
        """
        Paint the given songs to the specified QPriner instance.
        
        Will display an error dialog on error.
        """
        # TODO factor out duplication with exportToMultiplePdfs()

        print_editor = self.createPrintEditor()
        progress = QtWidgets.QProgressDialog(progress_message, "Abort", 0,
                                             len(song_ids), self.win)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        # Open the progress dialog right away:
        progress.setMinimumDuration(0)

        try:
            painter = QtGui.QPainter()
            if not painter.begin(printer):
                raise IOError("Failed to open the output file for writing")

            num_printed = 0
            page_num = 0

            num_table_of_contents_pages = 0
            if self.pdf_options.generate_table_of_contents:

                lyrics_height = self.lyrics_font_metrics.height()
                printable_height = self.getPrintableHeight(printer)

                max_songs_per_page = int(printable_height // lyrics_height)

                # FIXME use smaller font size for table of contents
                # FIXME Do not leave less than ~10 song titles per page.

                table_of_contents_lines = []
                for song_id in song_ids:
                    title, num = self.songs_model.getTitleAndNumFromId(song_id)
                    if num != -1:
                        table_of_contents_lines.append((title, num))

                # Sort by song name:
                # FIXME remove the leading "The", "A", etc:
                table_of_contents_lines.sort()

                # Split the table of contents into pages:
                table_of_contents_pages = []
                curr_page = []
                for curr_line in table_of_contents_lines:
                    curr_page.append(curr_line)
                    if len(curr_page) == max_songs_per_page:
                        table_of_contents_pages.append(curr_page)
                        curr_page = []
                if curr_page:
                    table_of_contents_pages.append(curr_page)

                painter.setFont(self.lyrics_font)
                for lines in table_of_contents_pages:
                    page_num += 1
                    if page_num != 1:
                        if not printer.newPage():
                            raise IOError(
                                "Failed to flush page to disk, disk full?")
                    self.printTableOfConentsPage(lines, printer, painter,
                                                 page_num)

                num_table_of_contents_pages = len(table_of_contents_pages)

            if num_table_of_contents_pages % 2:
                # Odd number of table of contents pages. Inseart a blank line:
                page_num += 1
                if not printer.newPage():
                    raise IOError("Failed to flush page to disk, disk full?")

            min_scale_ratio = 1.0

            for song_id in song_ids:
                if progress.wasCanceled():
                    break

                page_num += 1
                if page_num != 1:
                    if not printer.newPage():
                        raise IOError(
                            "Failed to flush page to disk, disk full?")

                song = self._songForOutput(song_id)

                # Set this song's document (will be reset later):
                # NOTE: Messing with this stuff may cause the app to crash on Windows (compiled)
                QtDocumentLayout.show_document(print_editor, song.doc)

                scale_ratio = self.printSong(song, printer, painter, print_editor, page_num)
                if scale_ratio < min_scale_ratio:
                    min_scale_ratio = scale_ratio

                num_printed += 1
                progress.setValue(num_printed)

            painter.end()

            self.reportScaleRatio(min_scale_ratio, len(song_ids))

        except IOError as err:
            self.error(str(err))
            return 0

        except Exception as err:
            raise

        progress.setValue(len(song_ids))

        return num_printed

    def printSong(self, song, printer, painter, editor, page_num):
        # NOTE: The song's document should already be in the editor for this to work!

        # Figure out what the margins should be:
        # Convert to points (from inches):
        left_margin = self.pdf_options.left_margin * 72.0
        right_margin = self.pdf_options.right_margin * 72.0
        top_margin = self.pdf_options.top_margin * 72.0
        bottom_margin = self.pdf_options.bottom_margin * 72.0

        # orig_document = self.editor.document().clone()

        if self.pdf_options.alternate_margins and not page_num % 2:
            # If alternating margins and this is an even page:
            left_margin, right_margin = right_margin, left_margin

        page_width = printer.width()  #- 300
        page_height = printer.height()  #- 300
        song_width, song_height = song_target_size(
            page_width, page_height, left_margin, right_margin, top_margin,
            bottom_margin, self.pdf_options.print_4_per_page)

        if self.pdf_options.print_4_per_page:
            page_width = page_width // 2
            page_height = page_height // 2
            for (x, y) in ((0, 0), (0, 1), (1, 0), (1, 1)):
                song_top = top_margin + y * page_height
                song_left = left_margin + x * page_width

                # FIXME either use QRectF or use integers instead of floats
                paint_rect = QtCore.QRect(int(song_left), int(song_top),
                                          song_width, song_height)
                scale_ratio = self.drawSongToRect(song,
                                                  painter,
                                                  editor,
                                                  paint_rect,
                                                  exporting=True)
        else:
            paint_rect = QtCore.QRectF(left_margin, top_margin, song_width,
                                      song_height)
            scale_ratio = self.drawSongToRect(song,
                                              painter,
                                              editor, 
                                              paint_rect,
                                              exporting=True)

        return scale_ratio

    # FIXME FIXME Re-factor out the common code from these two methods!

    def printTableOfConentsPage(self, lines, printer, painter, page_num):
        """
        Print the given table of contents pages to the given printer/painter.
        page_num is used to determine whether to use alternate margins.
        """

        # Figure out what the margins should be:
        # Convert to points (from inches):
        left_margin = self.pdf_options.left_margin * 72.0
        right_margin = self.pdf_options.right_margin * 72.0
        top_margin = self.pdf_options.top_margin * 72.0
        bottom_margin = self.pdf_options.bottom_margin * 72.0

        if self.pdf_options.alternate_margins and not page_num % 2:
            # If alternating margins and this is an even page:
            left_margin, right_margin = right_margin, left_margin

        width = printer.width()  #- 300
        height = printer.height()  #- 300

        if self.pdf_options.print_4_per_page:
            width = width // 2
            height = height // 2
            for (x, y) in ((0, 0), (0, 1), (1, 0), (1, 1)):
                song_width = width - left_margin - right_margin
                song_height = height - top_margin - bottom_margin

                song_top = top_margin + y * height
                song_left = left_margin + x * width

                paint_rect = QtCore.QRect(int(song_left), int(song_top), int(song_width),
                                          int(song_height))
                self.drawTableOfContentsPageToRect(lines, painter, paint_rect)
        else:
            song_width = width - left_margin - right_margin
            song_height = height - top_margin - bottom_margin
            song_top = top_margin
            song_left = left_margin
            paint_rect = QtCore.QRect(song_left, song_top, song_width,
                                      song_height)
            self.drawTableOfContentsPageToRect(lines, painter, paint_rect)

    # FIXME combine this code with the margin code aboce:

    def getPrintableHeight(self, printer):

        top_margin = self.pdf_options.top_margin * 72
        bottom_margin = self.pdf_options.bottom_margin * 72

        height = printer.height()  #- 300
        if self.pdf_options.print_4_per_page:
            height = height / 2.0

        return height - top_margin - bottom_margin

    def exportToSinglePdf(self, pdf_file=None):
        """
        Exports the selected songs to a PDF file.
        """

        self._flushCurrentSong()

        song_ids = self.getSelectedSongIds()
        if not song_ids:
            # No selection, export all songs:
            song_ids = self.songs_model.getAllSongIds()

        if not pdf_file:
            ok = PdfDialog(self).display(
                self.pdf_options,
                single_pdf_export=True,
                song=self.singleExportSong(song_ids))
            if not ok:
                return

            if len(song_ids) == 1:
                suggested_path = os.path.join(QtCore.QDir.home().path(),
                                              self.current_song.title + ".pdf")
            else:
                suggested_path = QtCore.QDir.home().path()

            pdf_file, _ = QtWidgets.QFileDialog.getSaveFileName(
                self.win,
                "Save PDF file as:",
                suggested_path,
                "PDF format (*.pdf)",
            )

            if not pdf_file:
                # User cancelled
                return

        self.setWaitCursor()
        try:
            printer = export_printer(self.pdf_options.page_width,
                                     self.pdf_options.page_height,
                                     self.pdf_options.print_4_per_page,
                                     output_file=pdf_file)
            self.printSongsToPrinter(song_ids, printer,
                                                   "Exporting to PDF...")

        except Exception as err:
            self.restoreCursor()
            self.error("Error exporting:\n\n%s " % traceback.format_exc())
        else:
            self.restoreCursor()

    def exportToMultiplePdfs(self):
        """
        Exports the selected songs, each to its own PDF file.
        """
        # TODO factor out duplication with printSongsToPrinter()

        self._flushCurrentSong()

        song_ids = self.getSelectedSongIds()
        if len(song_ids) == 0:
            # No song is selected, export all.
            song_ids = self.songs_model.getAllSongIds()

        ok = PdfDialog(self).display(
            self.pdf_options,
            single_pdf_export=False,
            song=self.singleExportSong(song_ids),
            native_on_mac=True)
        if not ok:
            return

        suggested_dir = QtCore.QDir.home().path()
        dir = QtWidgets.QFileDialog.getExistingDirectory(
            self.win,
            "Save PDF file in directory:",
            suggested_dir,
        )
        if not dir:
            # User cancelled
            return
        
        print_editor = self.createPrintEditor()

        progress = QtWidgets.QProgressDialog("Exporting to PDFs...", "Abort", 0,
                                             len(song_ids), self.win)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        # Open the progress dialog right away:
        progress.setMinimumDuration(0)

        min_scale_ratio = 1.0
        for i, song_id in enumerate(song_ids):
            progress.setValue(i)

            if progress.wasCanceled():
                break

            song = self._songForOutput(song_id)

            # Set this song's document (will be reset later):
            # NOTE: Messing with this stuff may cause the app to crash on Windows (compiled)
            QtDocumentLayout.show_document(print_editor, song.doc)

            pdf_file = os.path.join(dir, song.title + ".pdf")

            try:
                printer = export_printer(self.pdf_options.page_width,
                                         self.pdf_options.page_height,
                                         self.pdf_options.print_4_per_page,
                                         output_file=pdf_file,
                                         native_on_mac=True)

                painter = QtGui.QPainter()
                if not painter.begin(printer):
                    raise IOError("Failed to open the output file for writing")

                # Always print the song as if to the first page, when exporting to multiple PDFs:
                scale_ratio = self.printSong(song, printer, painter, print_editor, 1)
                if scale_ratio < min_scale_ratio:
                    min_scale_ratio = scale_ratio

                painter.end()

            except Exception as err:
                self.restoreCursor()
                self.error("Error generating PDF:\n%s" % str(err))
                raise

        progress.setValue(i + 1)  # Close the progress dialog

        self.reportScaleRatio(min_scale_ratio, len(song_ids))


    def reportScaleRatio(self, min_scale_ratio, num_songs):
        """Tell the user when a multi-song export had to shrink a song.

        One song shows its scale in the export settings before export.
        """
        if num_songs <= 1 or min_scale_ratio == 1.0:
            return
        scale_percent = min_scale_ratio * 100.0
        self.info(
            "Some songs were scaled down up to %.1f%% to fit the page."
            % scale_percent)

    def cutSelected(self):
        """
        Cut the selected chord (if any) into the clipboard.
        """
        if self.textEditing():
            self.editor.cut()
            return
        if not self.chordEditing():
            return
        chord = self.getSelectedChord()
        if chord:
            chord_text = chord.getChordText()
            self.clipboard.setText(chord_text)
            self.current_song.deleteChord(chord)

    def copySelected(self):
        """
        Copy the selected chord (if any) into the clipboard.
        """
        chord = self.getSelectedChord()
        if chord:
            chord_text = chord.getChordText()
            self.clipboard.setText(chord_text)

    def pasteSelected(self):
        """
        Paste the chord of the clipboard (if any) onto the selected character (if any)
        """

        if self.editor.lyric_editor_mode:
            self.editor.paste()
            return
        if not self.chordEditing():
            return

        if self.selected_char_num == None or not self.current_song:
            return

        text = self.clipboard.text()

        try:
            converted_chord = self.convertChordFromString(text)
        except ValueError as err:
            print("not a chord")
            return

        (marker, note_id, type_id, bass_id, in_parentheses) = converted_chord
        new_chord = SongChord(self.current_song, self.selected_char_num,
                              note_id, type_id, bass_id, marker, in_parentheses)

        prev_chord = None
        for chord in self.current_song.iterateAllChords():
            if chord.character_num == self.selected_char_num:
                prev_chord = chord
                break

        if prev_chord:
            # Replacing exising chord
            self.current_song.replaceChord(prev_chord, new_chord)
        else:
            # Adding a new chord
            self.current_song.addChord(new_chord)

    def copySongText(self):
        """
        Copy the selected song's text to the clipboard. Chords are not included.
        """

        assert self.current_song is not None

        self.setWaitCursor()
        try:
            song_text = self.current_song.getAsText(include_chords=False)
            self.clipboard.setText(song_text)
        finally:
            self.restoreCursor()
        self.note("Song text copied to clipboard")

    def copySongTextWithChords(self):
        """
        Copy the selected song's text to the clipboard.
        The chords are included (as separate lines above the lyrics)
        """

        assert self.current_song is not None

        self.setWaitCursor()
        try:
            song_text = self.current_song.getAsText()
            self.clipboard.setText(song_text)
        finally:
            self.restoreCursor()
        self.note("Song text with chords copied to clipboard")

    def copySongAsImage(self):
        """
        Copy the selected song's sheet to the clipboard as PNG and SVG.
        """

        assert self.current_song is not None

        self.setWaitCursor()
        try:
            song = self.current_song
            editor = self.editor
            mime = QtCore.QMimeData()
            mime.setData("image/png",
                         _png_bytes(self._renderSongSheetImage(song, editor)))
            mime.setData("image/svg+xml",
                         self._renderSongSheetSvg(song, editor))
            # setImage() is a TIFF on macOS. These two types are the sheet.
            self.clipboard.setMimeData(mime)
        finally:
            self.restoreCursor()
        self.note("Song image copied to clipboard")

    def _paddedSongSheetBounds(self, song, editor):
        """Lyric frame and chords, with room for a chord past the letters."""

        # A chord is centered on its letter, so it can hang past the lyrics.
        pad = 16.0
        return self._songSheetBounds(song, editor).adjusted(-pad, -pad, pad,
                                                            pad)

    def _renderSongSheetImage(self, song, editor):
        """White song sheet at four times the screen resolution."""

        scale = 4
        bounds = self._paddedSongSheetBounds(song, editor)
        width = max(1, math.ceil(bounds.width() * scale))
        height = max(1, math.ceil(bounds.height() * scale))
        image = QtGui.QImage(width, height, QtGui.QImage.Format.Format_ARGB32)
        image.fill(QtCore.Qt.GlobalColor.white)
        painter = QtGui.QPainter(image)
        try:
            painter.scale(scale, scale)
            painter.translate(-bounds.left(), -bounds.top())
            self._drawSongToPainter(song, painter, editor, exporting=True)
        finally:
            painter.end()
        return image

    def _renderSongSheetSvg(self, song, editor):
        """The same white sheet, as vectors."""

        bounds = self._paddedSongSheetBounds(song, editor)
        width = max(1, math.ceil(bounds.width()))
        height = max(1, math.ceil(bounds.height()))
        generator = QSvgGenerator()
        buffer = QtCore.QBuffer()
        buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
        generator.setOutputDevice(buffer)
        generator.setResolution(96)
        generator.setSize(QtCore.QSize(width, height))
        generator.setViewBox(QtCore.QRectF(0, 0, width, height))
        painter = QtGui.QPainter(generator)
        try:
            painter.fillRect(QtCore.QRectF(0, 0, width, height),
                             QtCore.Qt.GlobalColor.white)
            painter.translate(-bounds.left(), -bounds.top())
            self._drawSongToPainter(song, painter, editor, exporting=True)
        finally:
            painter.end()
        svg = buffer.data()
        buffer.close()
        return svg

    def _songSheetBounds(self, song, editor):
        """Lyric frame, plus any chord that extends outside it."""

        right, bottom = song_document_size(song)
        bounds = QtCore.QRectF(0.0, 0.0, right, bottom)
        scroll_x = editor.horizontalScrollBar().value()
        scroll_y = editor.verticalScrollBar().value()
        layout = SongLayout.place(QtDocumentLayout(editor),
                                  song.chordsOnLetters(),
                                  self.getHeightsWithChords, self.getChordWidth,
                                  lambda chord: chord.getChordText())
        for placed in layout.placed:
            if placed.chord_rect is not None:
                bounds = bounds.united(
                    placed.chord_rect.translated(scroll_x, scroll_y))
        return bounds

    def currentSongTitleEdited(self, new_title):
        """
        Called when the user modifies the selected song's title.

        Part of an edit (one is started while viewing): saved by Save, put
        back by Discard. The song list keeps the saved title and number (and
        its sort and filter) until Save.
        """
        if self.current_song and self._viewDraft():
            self.current_song.title = new_title.strip()
            self._updateEditChanged()

    def subtitleEdited(self, new_note_str):
        """
        User has specified a new song note (comment).

        Part of an edit, like the title.
        """

        if not self.current_song:
            raise ValueError("No current song")

        if self._viewDraft():
            self.current_song.subtitle = new_note_str
            self._updateEditChanged()

    def currentSongNumberEdited(self, new_num_str):
        """
        Called when the user modifies the selected song's number.

        Part of an edit, like the title.
        """
        if self.current_song:
            if new_num_str == "":
                new_num_str = -1  # NULL
            try:
                new_num = int(new_num_str)
            except:
                self.error("Invalid song number")
            else:
                if self._viewDraft():
                    self.current_song.number = new_num
                    self._updateEditChanged()

    def createNewSong(self):
        """
        Add a new song to the database and the songs table, and select it.
        """
        if not self.confirmLeaveEdit():
            return

        song_id = self.store.next_song_id()
        if not self._run_songbook_write(lambda: self.store.insert_song(
                song_id, -1, "", "", "")):
            return

        # Update the song table from database:
        self.songs_model.updateFromDatabase()

        # Select the newly added song:
        source_index = self.songs_model.index(self.songs_model.rowCount() - 1,
                                              0)
        proxy_index = self.songs_proxy_model.mapFromSource(source_index)
        self.ui.songs_view.selectRow(proxy_index.row())

        song = Song(self, song_id)
        self.setCurrentSong(song)

        self.lyricEditorSelected()

    def showSongsContextMenu(self, pos):
        """
        Show the songs table context menu at a viewport position.
        """
        view = self.ui.songs_view
        # The menu selects the clicked song first, and Delete acts on it.
        if not self.confirmLeaveEdit():
            return
        menu = self.buildSongsContextMenu(view.indexAt(pos))
        if menu is None:
            return
        if menu.exec(view.viewport().mapToGlobal(pos)) is not None:
            self.deleteSongsFromContextMenu()

    def buildSongsContextMenu(self, index):
        """
        Build the songs table context menu for a view row.

        When the clicked song is not already selected, select it first
        (this covers a right-click with nothing selected). One selected
        song is labeled "Delete"; several are labeled "Delete...".
        Returns None if index is not a song row.
        """
        if not index.isValid():
            return None

        view = self.ui.songs_view
        selected_rows = {
            row_index.row()
            for row_index in view.selectionModel().selectedRows()
        }
        if index.row() not in selected_rows:
            view.selectRow(index.row())

        num_selected = len(view.selectionModel().selectedRows())
        if num_selected < 1:
            return None

        menu = QtWidgets.QMenu(view)
        if num_selected == 1:
            menu.addAction("Delete")
        else:
            menu.addAction("Delete...")
        return menu

    def deleteSongsFromContextMenu(self):
        """
        Delete the songs targeted by the songs table context menu.

        A single song is deleted immediately. Several songs require
        confirmation ("Delete N songs?").
        """
        num_selected = len(self.getSelectedSongIds())
        if num_selected > 1:
            if not self.question(
                    "Delete %d songs?" % num_selected, button1="Delete"):
                return
        if num_selected > 0:
            self.deleteSelectedSongs()

    def deleteSelectedSongs(self):
        """
        Deletes the selected song(s).
        """
        if not self.confirmLeaveEdit():
            return
        selected_song_ids = self.getSelectedSongIds()

        # Will set the current song to None:
        self.ui.songs_view.selectionModel().clearSelection()

        self.undo_stack.push(DeleteSongsCommand(self, selected_song_ids))

        self.updateEditMenu()

    def removeTrailingSpaces(self):
        if not self.confirmLeaveEdit():
            return

        self._flushCurrentSong()

        snapshots = []
        for song_id in self.getSelectedSongIds():
            snapshot = SongTextSnapshot.capture(self, song_id)
            if text_has_trailing_spaces(snapshot.text):
                snapshots.append(snapshot)
        if not snapshots:
            return
        self.undo_stack.push(RemoveTrailingSpacesCommand(self, snapshots))

    def _reloadOpenSong(self, song_ids):
        """Read an open song back after its text was rewritten in the songbook."""
        if self.current_song is None or self.current_song.id not in song_ids:
            return
        # The new text replaced the document, so the letter undo no longer matches.
        self.ignore_song_text_changed = True
        try:
            self.current_song.updateSongFromDatabase()
            QtDocumentLayout.show_document(self.editor, self.current_song.doc)
            self.previous_song_text = self.current_song.getAllText()
        finally:
            self.ignore_song_text_changed = False
        self._reset_lyric_chord_history()
        self._updateAutoDetectedKeyLabel()

    def _writeSongNumbers(self, pairs):
        """Save these song numbers. A later save of the open song must keep them."""

        def write():
            for song_id, number in pairs:
                self.store.update_song_number(song_id, number)

        if not self._run_songbook_write(write):
            return

        # Refreshing the song list can save the open song. Give it the new
        # number first, or that save would put the old number back.
        by_id = dict(pairs)
        song = self.current_song
        if song is not None and song.id in by_id:
            song.number = by_id[song.id]
            if song.number == -1:
                self.ui.song_num_ef.setText("")
            else:
                self.ui.song_num_ef.setText(str(song.number))
        self.songs_model.updateFromDatabase()

    def _selectSongId(self, song_id):
        ids = self.songs_model.getAllSongIds()
        if song_id not in ids:
            return
        source_index = self.songs_model.index(ids.index(song_id), 0)
        proxy_index = self.songs_proxy_model.mapFromSource(source_index)
        if proxy_index.isValid():
            self.ui.songs_view.selectRow(proxy_index.row())

    def _rememberImportedSongs(self, song_ids):
        """One undo step removes every song this import or paste added."""
        song_ids = [song_id for song_id in song_ids if song_id is not None]
        if song_ids:
            self.undo_stack.push(ImportSongsCommand(self, song_ids))

    def renumberAllSongs(self):
        """
        Re-number all songs in the database (song number, not IDs).
        """
        if not self.confirmLeaveEdit():
            return

        if not self.question(
                "All songs in the songbook will be renumbered consecutively starting with 1. Continue?"
        ):
            return

        previous = []
        for song_id in self.songs_model.getAllSongIds():
            _title, number = self.songs_model.getTitleAndNumFromId(song_id)
            previous.append((song_id, number))
        if not previous:
            return
        if all(number == index
               for index, (_song_id, number) in enumerate(previous, start=1)):
            return

        self.undo_stack.push(RenumberSongsCommand(self, previous))

    def question(self,
                 msg,
                 button1="OK",
                 button2="Cancel",
                 title="softChord - Question"):
        """ 
        Display a prompt dialog window with specified text.
        Returns True if first button (default OK) is pressed, False otherwise.
        """
        mbox = QtWidgets.QMessageBox(self.win)
        mbox.setText(msg)
        mbox.setWindowTitle(title)
        mbox.setIcon(QtWidgets.QMessageBox.Icon.Question)
        b1 = mbox.addButton(button1, QtWidgets.QMessageBox.ButtonRole.ActionRole)
        b2 = mbox.addButton(button2, QtWidgets.QMessageBox.ButtonRole.RejectRole)
        mbox.exec()
        return (mbox.clickedButton() == b1)

    def getCharRects(self, editor, song_char_num, chord=None):
        if chord != None:
            has_chord = True
        else:
            has_chord = False
            for chord in self.current_song._chords:
                if chord.character_num == song_char_num:
                    has_chord = True
                    break

        if has_chord:
            chords_height, _lyrics_height, line_height = self.getHeightsWithChords(
            )
            chord_text = chord.getChordText()
            chord_width = self.getChordWidth(chord_text)
        else:
            chords_height, _lyrics_height, line_height = self.getHeightsWithoutChords(
            )
            chord_text = None
            chord_width = 0

        return QtDocumentLayout(editor).character_and_chord_boxes(
            song_char_num, chord_text, chords_height, line_height, chord_width)

    def chordColorFor(self, placed):
        """Blue for a chord, red for text that is not a chord."""
        if placed.unrecognized:
            return self.unrecognized_chords_color
        return self.chords_color

    def getChordWidth(self, chord_text):

        width = 0.0
        for letter in chord_text:
            if letter in ["♯", "♭"]:
                width += self.symbols_font_metrics.horizontalAdvance(letter)
            else:
                width += self.chords_font_metrics.horizontalAdvance(letter)
        return width

    def drawSelection(self, painter, char_rect, chord_rect):
        """
        The selection on screen (never in a PDF, a print or an image), the
        same as the web app's: the letter gets a light blue box (#007aff at
        20%, corners of 3px). Its chord gets a halo: #007aff at 25% reaching
        2px past the chord, with a 1px #007aff line around it and rounded
        corners.
        """
        painter.save()
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(SELECTED_LETTER_COLOR)
        painter.drawRoundedRect(QtCore.QRectF(char_rect), 3.0, 3.0)
        if chord_rect:
            halo = QtCore.QRectF(chord_rect).adjusted(-2.0, -2.0, 2.0, 2.0)
            painter.setBrush(SELECTED_CHORD_HALO_COLOR)
            painter.drawRoundedRect(halo, 4.0, 4.0)
            pen = QtGui.QPen(SELECTED_CHORD_LINE_COLOR)
            pen.setWidthF(1.0)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(halo.adjusted(-0.5, -0.5, 0.5, 0.5), 4.5, 4.5)
        painter.restore()

    def drawChord(self, painter, chord_rect, chord_text):
        """
        Draw the given chord to the given rect of the painter.
        Draws the special symbols in the <symbol> font, which ensures that
        the spacing is correct.
        """

        normal_height = self.chords_font_metrics.height()
        normal_baseline = chord_rect.bottom() - (0.2 * normal_height
                                                )  # FIXME hack

        letter_left = chord_rect.left()

        # Distance to raise the flat/sharp signs by
        raise_distance = chord_rect.height() / 10.0
        raised_baseline = normal_baseline - raise_distance

        for letter in chord_text:
            if letter in ["♯", "♭"]:
                # FIXME: On Windows, the flat is drawn a little off
                painter.setFont(self.symbols_font)
                let_width = self.symbols_font_metrics.horizontalAdvance(letter)
                baseline = raised_baseline
            else:
                painter.setFont(self.chords_font)
                let_width = self.chords_font_metrics.horizontalAdvance(letter)
                baseline = normal_baseline

            pos = QtCore.QPointF(letter_left, baseline)
            painter.drawText(pos, letter)

            letter_left += let_width

        # FIXME restore chord_rect and font?
    
    def createPrintEditor(self):
        print_editor = CustomTextEdit(self)
        print_editor.setLineWrapMode(
            QtWidgets.QTextEdit.LineWrapMode.NoWrap)
        print_editor.setFont(self.lyrics_font)
        return print_editor

    def _drawSongToPainter(self, song, painter, editor, exporting=False):
        """
        Draw the given song to the given painter.
        Always draws the main text and chords.
        When not exporting, draws selection rects as well.
        When exporting, optionally draws song num and/or title.
        """

        # NOTE: Everything here is unscaled (original font sizes, etc)

        if not exporting:
            hover_brush = QtGui.QColor("light grey")

            # Draw any selection rects:
            if self.hover_char_num != None:
                char_rect, chord_rect = self.getCharRects(
                    editor, self.hover_char_num)

                # Mouse is currently hovering over this letter:
                # Draw a hover rectangle:
                painter.fillRect(char_rect, hover_brush)
                if chord_rect:
                    painter.fillRect(chord_rect, hover_brush)

            selected_nums = set(self.selected_chord_nums)
            if self.selected_char_num != None:
                selected_nums.add(self.selected_char_num)
            for char_num in selected_nums:
                char_rect, chord_rect = self.getCharRects(editor, char_num)

                # The selected letter and its chord, as in the web app.
                self.drawSelection(painter, char_rect, chord_rect)

        # Chord boxes come from the editor viewport. Export draws the lyrics
        # at the document origin, so shift the boxes by the scroll offset.
        # A painter translate here would move the lyrics too: an SVG does not
        # put that translate back the way a bitmap painter does.
        scroll_x = 0.0
        scroll_y = 0.0
        if exporting:
            scroll_x = editor.horizontalScrollBar().value()
            scroll_y = editor.verticalScrollBar().value()

        doc_layout = QtDocumentLayout(editor)
        layout = SongLayout.place(doc_layout, song.chordsOnLetters(),
                                  self.getHeightsWithChords, self.getChordWidth,
                                  lambda chord: chord.getChordText())
        for placed in layout.placed:
            painter.setFont(self.chords_font)

            # On Windows, selected text is drawn in white:
            #if chord.character_num == self.selected_char_num and self.on_windows:
            #    painter.setPen(self.white_color)
            #else:
            painter.setPen(self.chordColorFor(placed))

            if placed.chord_rect:
                self.drawChord(
                    painter, placed.chord_rect.translated(scroll_x, scroll_y),
                    placed.chord_text)
            else:
                print('no chord rect!')

        # Draw the lyrics document:

        painter.setFont(self.lyrics_font)
        painter.setPen(self.lyrics_color)
        doc_layout.draw_lyrics(painter, apply_scroll=not exporting)

    def drawSongToRect(self, song, output_painter, editor, rect, exporting=False):
        """
        Draws the current song text to the specified rect.

        exporting - whether we are drawing to a PDF/Print instead of the screen.
        
        When "exporting", the selection/inert cursor are not drawn, and the song number
        IS drawn.
        """

        # FIXME will not account for chord text:
        pic_right, pic_bottom = song_document_size(song)
        # FIXME this does not account for the header line and the first chords line

        # Figure out what the scaling factor should be:
        if not exporting:
            # Painting to screen, zoom factor is already applied to font size
            scale_ratio = 1.0
            actual_scale_ratio = None
        else:
            # Exporting, make sure the song fits into the specified <rect>.
            # Do not make songs any bigger. Painting then undoes the zoom.
            actual_scale_ratio = fit_scale_ratio(
                pic_right, pic_bottom, rect.width(), rect.height(),
                self.zoom_factor)
            scale_ratio = actual_scale_ratio / self.zoom_factor

        # Height of the header line:
        lyrics_height = self.lyrics_font_metrics.height()

        # Print song number and/or title to the header (first) line:
        header_list = []

        if exporting:
            if self.pdf_options.print_song_num and song.number != -1:
                header_list.append(str(song.number))

            if self.pdf_options.print_song_comment and song.subtitle:
                header_list.append(song.subtitle)

            if self.pdf_options.print_song_key:
                labels = auto_detected_key_labels(song._regions)
                if labels:
                    header_list.append("Key: " + ", ".join(labels))

            if self.pdf_options.print_song_title and song.title:
                header_list.append(song.title)

        # Go to songs's reference frame:
        output_painter.translate(rect.left(), rect.top())
        output_painter.scale(scale_ratio, scale_ratio)

        # Offset the editor margins when exporting:
        if exporting:
            output_painter.translate(-self.doc_editor_offset,
                                     -self.doc_editor_offset)

        if header_list:
            # Combine the song number string, song key, song subtitle, and/or song title string:
            header_str = "  ".join(header_list)
            output_painter.setFont(self.lyrics_font)

            x = 5.0  # For some reason needed for alignment
            y = 0.0

            # FIXME what if the title is too long?
            header_rect = QtCore.QRectF(x, y, 1000.0, lyrics_height)
            output_painter.drawText(header_rect, Qt.AlignmentFlag.AlignLeft, header_str)

            output_painter.translate(0.0, lyrics_height)

        # Draw the song lyrics and chirds:
        self._drawSongToPainter(song, output_painter, editor, exporting)

        if header_list:
            output_painter.translate(0.0, -lyrics_height)

        # Revert the editor margins when exporting:
        if exporting:
            output_painter.translate(self.doc_editor_offset,
                                     self.doc_editor_offset)

        # Redo the effect of scaling:
        output_painter.scale(1.0 / scale_ratio, 1.0 / scale_ratio)

        # Go to the original reference frame:
        output_painter.translate(-rect.left(), -rect.top())

        return actual_scale_ratio

    # FIXME FIXME factor-out the common code between these two methods!

    def drawTableOfContentsPageToRect(self, lines, painter, rect):
        """
        Draws the given table of contents page to the specified rect.
        <lines> is a list of (song_name, song_num) tuples for this page.
        """

        # Go to songs's reference frame:
        painter.translate(rect.left(), rect.top())

        max_width = rect.width()
        max_height = rect.height()
        max_name_width = max_width - self.lyrics_font_metrics.boundingRect(".999").width()

        lyrics_height = self.lyrics_font_metrics.height()
        dot_char_width = self.lyrics_font_metrics.boundingRect(".").width()

        curr_height = 0.0
        for song_name, song_num in lines:
            # Keep removing the last word of the song title until it fits into a line:
            while self.lyrics_font_metrics.boundingRect(song_name).width() > max_name_width:
                # Remove the last word:
                s = song_name.split()
                if len(s) == 1:
                    # Only left with one word
                    break
                # If there IS something to remove
                remove_chars = len(s[-1]) + 1
                song_name = song_name[:-remove_chars]

            rect = QtCore.QRect(0, int(curr_height), int(max_width), int(lyrics_height))
            name_bounds_rect = painter.drawText(rect, Qt.AlignmentFlag.AlignLeft,
                                                song_name)
            num_bounds_rect = painter.drawText(rect, Qt.AlignmentFlag.AlignRight,
                                               str(song_num))

            dots_left = name_bounds_rect.right()
            dots_right = num_bounds_rect.left()
            dots_width = dots_right - dots_left

            num_dots = int(dots_width // dot_char_width)

            if num_dots >= 3:
                dots_str = '.' * (num_dots - 2)
                dots_str = ' ' + dots_str + ' '

                # FIXME display dots a bit higher
                rect = QtCore.QRect(int(dots_left), int(curr_height), int(dots_width), int(lyrics_height))
                painter.drawText(rect, Qt.AlignmentFlag.AlignLeft, dots_str)

            curr_height += lyrics_height

        # Go to the original reference frame:
        painter.translate(-rect.left(), -rect.top())

    def determineClickedLetter(self, x, y, dragging):
        """
        Determine where the specified (local) mouse coordinates position.
        That is, which lyric or chord letter was the mouse above when this
        event happened.
        """

        self.drag_past_line_end = None
        if not self.current_song:
            return None

        for chord in self.current_song._chords:
            char_rect, chord_rect = self.getCharRects(self.editor,
                                                      chord.character_num,
                                                      chord)

            if y > chord_rect.top() and y < chord_rect.bottom():
                if y < chord_rect.bottom() and not dragging:
                    # Mouse is over the chord height:
                    if chord_rect and x > chord_rect.left(
                    ) and x < chord_rect.right():
                        is_chord = True
                        return (is_chord, chord.character_num)
                else:
                    # Mouse is over the lyrics height OR we are dragging
                    if x > chord_rect.left() and x < chord_rect.right():
                        is_chord = False
                        return (is_chord, chord.character_num)

        # Not over a chord, check the letter:
        offset_x = x - 5.0

        if self.editor.dragging_chord:
            # Make sure drag obove (not over) a letter would be cought:
            chord = self.editor.dragging_chord
            char_rect, chord_rect = self.getCharRects(self.editor,
                                                      chord.character_num,
                                                      chord)
            if y > chord_rect.top() and y < char_rect.top():
                y = char_rect.top() + 1

        pos, at_start, at_end, rect = QtDocumentLayout(
            self.editor).caret_at(offset_x, y)

        # If at the start or end of line, make sure the cursor is actually over a character:
        if at_start or at_end:
            if at_end and x >= rect.right() and dragging:
                # A chord dragged right of its line: see dragChordPastLineEnd.
                self.drag_past_line_end = (pos, x - rect.right())
            if at_start and x < rect.left():
                return None
            if at_end and x >= rect.right():
                return None

        return (False, pos)

    def processSongCharEdit(self, song_char_num):
        """
        Bring up a dialog that will allow the user to add/modify the chord at
        the specified position.
        """

        add_new = True
        orig_chord = None
        for iter_chord in self.current_song.iterateAllChords():
            if iter_chord.character_num == song_char_num:
                add_new = False
                orig_chord = iter_chord
                break

        if add_new:
            new_chord = SongChord(self.current_song, song_char_num, 0, 0, -1,
                                  "", False)
        else:
            new_chord = copy.copy(orig_chord)

        ok = ChordDialog(self).display(new_chord)
        if ok:
            # Ok pressed
            if add_new:
                self.current_song.addChord(new_chord)
                self.note("Chord added")
            else:
                self.current_song.replaceChord(orig_chord, new_chord)
                self.note("Chord changed")

            self.editor.viewport().update()

    def clipboardChanged(self):
        """
        Enable/disable the "Paset As New Song" menu item.
        """

        text = self.clipboard.text()
        self.ui.actionPasteAsNewSong.setEnabled(bool(text))
        self.updateEditMenu()


