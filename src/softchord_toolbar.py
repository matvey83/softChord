"""The song toolbar above the song pane of the desktop editor.

MIRRORED UI: this toolbar mirrors the web app's song toolbar
(softChord_web/index.html .toolbar, softChord_web/viewer.css) and the iOS
app's (softChord Viewer/softChord Viewer/SongToolbar.swift). The buttons,
their order and groups, the icons (the SVGs in softChord_web/icons/toolbar/,
the one copy, bundled by softchord.spec), the tooltips, and when each button
shows or is dimmed are the same in all three apps: change them in all three.

Intended desktop differences:
- It wraps like the web and iOS toolbars: whole groups move to the next row
  when the pane is too narrow, and a separator is dropped at a row's start or
  end. There is no 940 px rule: it wraps only when the groups do not fit.
- Desktop-only: Edit Text / Edit Chords and the edit groups after them are
  always on the last row, even when they would fit on the row above. When
  the pane narrows, the groups before them that no longer fit join that last
  row in front of them, and a new row starts only when they do not fit (the
  edit groups stay together on one row while the pane is wide enough).
  It sits below the Number/Title and Notes fields, above the song.
- No Back button and no title: the song list and the Title field are always
  there. No "Changes do not persist" banner and no brief notes: Save really
  saves to the songbook.
- Undo and Redo show in Edit Text too (the desktop has a text undo).
- Tooltips name the keyboard shortcut. The toolbar uses the menu bar's
  QActions where there is one, so both are dimmed together.
- The zoom percentage after the zoom buttons is plain text (not a button).
- Print opens the desktop print dialog for the selected songs.
- Desktop-only: a Fonts group after Print with "Select font for lyrics" and
  "Select font for chords" (the Settings menu's Lyrics Font and Chords Font
  dialogs). Their icons, font-lyrics.svg and font-chords.svg, sit with the
  others in softChord_web/icons/toolbar/ but are not drawn in index.html, so
  tools/export_toolbar_icons.js neither writes nor checks them.
- The icons take the palette's text colour (dark mode) and are drawn for
  1x, 2x and 3x screens.
"""

import os

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtSvg import QSvgRenderer

ICON_SIZE = 22

# The help that was the tooltip of the "Edit chords/lyrics of the selected
# song" hint labels, now under the Edit Chords and Edit Text tooltips.
CHORDS_HELP = (
    '<b>To add a new chord:</b><br>Press on a lyrics letter to select it, '
    'then press one of the following keys: A, B, C, D, E, F, or G. To '
    'assign a sharp or a flat, press the "Up" or "Down" key afterwards to '
    '"transpose" the chord. To create a minor chord, press the "M" key. To '
    'create advanced chords, double-click on the created chord (a dialog '
    'box will open).<br><br><b>To edit a chord:</b><br>Click on the chord '
    'to select it, then press "M" to toggle major/minor, press another '
    'letter to assign a different note, or press "Up" or "Down" keys to '
    'transpose it. Double-click on the chord for advanced '
    'modifications.<br><br><b>To move a chord:</b><br>Click on the chord to '
    'select it, and then use the "Left" or "Right" keys to move it relative '
    'to the lyrics below it. Alternatively you can simply drag it to the '
    'new place.<br><br><b>To duplicate a chord:</b><br>While holding the '
    '"Option" key, click and drag the chord. Alternatively you can use '
    'copy-and-paste.<br><br><b>To delete a chord:</b><br>Click on the chord '
    'to select it, and press the "Delete" key.'
)
LYRICS_HELP = (
    'When in lyric editing mode, you can modify the text (lyrics) of the '
    'song. As text is moved/added/removed, chords get moved automatically '
    'to follow their letters. Remember to go back into the chord editor '
    'mode when you need modify chords.'
)
BUTTON_SIZE = 28


def icon_dir():
    """The SVGs: next to this file in the PyInstaller build, else the web app's."""
    here = os.path.dirname(os.path.abspath(__file__))
    bundled = os.path.join(here, "icons", "toolbar")
    if os.path.isdir(bundled):
        return bundled
    return os.path.join(here, os.pardir, "softChord_web", "icons", "toolbar")


def tinted_icon(name, color):
    """The toolbar SVG `name` drawn in `color`, sharp at 1x, 2x and 3x."""
    path = os.path.join(icon_dir(), name + ".svg")
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return QtGui.QIcon()
    data = data.replace(b"#000000", color.name().encode("ascii"))
    renderer = QSvgRenderer(QtCore.QByteArray(data))
    icon = QtGui.QIcon()
    for scale in (1, 2, 3):
        side = ICON_SIZE * scale
        for mode, opacity in ((QtGui.QIcon.Mode.Normal, 1.0),
                              (QtGui.QIcon.Mode.Disabled, 0.35)):
            pixmap = QtGui.QPixmap(side, side)
            pixmap.fill(QtCore.Qt.GlobalColor.transparent)
            painter = QtGui.QPainter(pixmap)
            painter.setOpacity(opacity)
            renderer.render(painter)
            painter.end()
            icon.addPixmap(pixmap, mode)
    return icon


def _shortcut_text(action):
    keys = action.shortcut()
    if keys.isEmpty():
        return ""
    return " (%s)" % keys.toString(QtGui.QKeySequence.SequenceFormat.NativeText)


class _FlowLayout(QtWidgets.QLayout):
    """Left to right, onto the next row when an item does not fit.

    A separator item is shown only between two groups on the same row.
    The item with the "tailStart" property (the Edit Text / Edit Chords group)
    and everything after it are the tail, kept on the last row: the tail
    starts a new row unless the groups before it have already wrapped, in
    which case it joins their last (wrapped) row if all of it fits there.
    It wraps inside itself only when it is wider than the pane.
    """

    def __init__(self, parent=None, spacing=2, row_spacing=2):
        super().__init__(parent)
        self._items = []
        self._spacing = spacing
        self._row_spacing = row_spacing
        self.setContentsMargins(0, 2, 0, 2)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return QtCore.Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._layout(QtCore.QRect(0, 0, width, 0), False)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._layout(rect, True)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QtCore.QSize()
        for item in self._items:
            if not item.isEmpty():
                size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        return size + QtCore.QSize(margins.left() + margins.right(),
                                   margins.top() + margins.bottom())

    def _layout(self, rect, apply):
        margins = self.contentsMargins()
        area = rect.adjusted(margins.left(), margins.top(),
                             -margins.right(), -margins.bottom())
        items = [item for item in self._items if not item.isEmpty()]
        # The tail's width when on one row, to keep it together.
        tail_width, in_tail = 0, False
        for item in items:
            in_tail = in_tail or bool(item.widget().property("tailStart"))
            if in_tail:
                tail_width += item.sizeHint().width() + self._spacing
        tail_width -= self._spacing
        x, y, row_height = area.x(), area.y(), 0
        placed = []  # (item, rect) of the row being filled
        pending_sep = None
        rows = []
        for item in items:
            hint = item.sizeHint()
            if item.widget().property("separator"):
                if placed:
                    pending_sep = item
                continue
            sep_width = 0
            if pending_sep is not None:
                sep_width = pending_sep.sizeHint().width() + self._spacing
            width = hint.width()
            if item.widget().property("tailStart"):
                # Not on the first row; on a wrapped row only all of it.
                if not rows:
                    width = area.width() + 1
                else:
                    width = tail_width
            if placed and x + sep_width + width > area.right() + 1:
                rows.append((placed, row_height))
                if pending_sep is not None:
                    placed_sep = (pending_sep, None)
                    rows[-1][0].append(placed_sep)
                y += row_height + self._row_spacing
                x, row_height, placed, pending_sep = area.x(), 0, [], None
                sep_width = 0
            if pending_sep is not None:
                sep_hint = pending_sep.sizeHint()
                placed.append((pending_sep, QtCore.QRect(
                    QtCore.QPoint(x, y), sep_hint)))
                x += sep_width
                pending_sep = None
            placed.append((item, QtCore.QRect(QtCore.QPoint(x, y), hint)))
            x += hint.width() + self._spacing
            row_height = max(row_height, hint.height())
        if placed:
            rows.append((placed, row_height))
        if pending_sep is not None:
            rows[-1][0].append((pending_sep, None))
        if apply:
            for row, height in rows:
                for item, geometry in row:
                    if geometry is None:
                        # A separator at a row's end is not drawn.
                        item.setGeometry(QtCore.QRect(0, 0, 0, 0))
                        continue
                    geometry.moveTop(geometry.top()
                                     + (height - geometry.height()) // 2)
                    item.setGeometry(geometry)
        total = y + (rows[-1][1] if rows else 0) - area.y()
        return total + margins.top() + margins.bottom()


class SongToolbar(QtWidgets.QWidget):
    """Copy | Transpose | Zoom | Print | Fonts | Edit [Chord] [Discard Save]."""

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        ui = session.ui
        self.setObjectName("song_toolbar")
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,
                           QtWidgets.QSizePolicy.Policy.Preferred)
        self._icons = {}  # action -> SVG name, re-tinted on a palette change
        self._buttons = {}  # action -> its QToolButton
        self._order = []  # actions and "|" in toolbar order
        self._restyling = False
        self._flow = _FlowLayout(self, spacing=6)

        def new(name, text, slot, tip=None):
            action = QtGui.QAction(text, self)
            action.setObjectName(name)
            action.setToolTip(tip or text)
            action.triggered.connect(slot)
            return action

        def proxy(action, text, tip=None):
            """A toolbar-only twin of a menu action that can be hidden alone."""
            twin = new(action.objectName() + "Tool", text,
                       lambda checked=False: action.trigger(),
                       (tip or text) + _shortcut_text(action))
            twin.setEnabled(action.isEnabled())
            action.changed.connect(lambda: twin.setEnabled(action.isEnabled()))
            return twin

        # Actions the menus do not have.
        self.transpose_down = new("actionTransposeDown", "Transpose Down",
                                  session.transposeDown, "Transpose down")
        self.transpose_up = new("actionTransposeUp", "Transpose Up",
                                session.transposeUp, "Transpose up")
        self.transpose_reset = new("actionTransposeReset", "Reset Transpose",
                                   session.transposeReset, "Reset transpose")
        self.transpose_reset.setEnabled(False)
        # Only text: the zoom-reset button and Cmd+0 reset the zoom.
        self.zoom_percent = QtGui.QAction("100%", self)
        self.zoom_percent.setObjectName("actionZoomPercent")
        self.chord_edit = new("actionChordEdit", "Add Chord",
                              session.editChordFromToolbar, "Add chord")
        self.chord_delete = new("actionChordDelete", "Delete Chord",
                                session.deleteSelectedChord, "Delete chord")
        self.undo = proxy(ui.actionUndo, "Undo")
        self.redo = proxy(ui.actionRedo, "Redo")
        self.discard = new("actionDiscardTool", "Discard", session.discardEdit,
                           "Put the song back as it was before this edit"
                           + _shortcut_text(ui.actionDiscardEdit))
        self.save = proxy(ui.actionSaveEdit, "Save",
                          "Save this edit to the songbook")
        tips = (
            (ui.actionCopySongText, "Copy song text"),
            (ui.actionCopySongTextWithChords, "Copy song text (with chords)"),
            (ui.actionCopySongAsImage, "Copy song as image"),
            (ui.actionZoomOut, "Zoom out"),
            (ui.actionZoomActual, "Reset zoom (100%)"),
            (ui.actionZoomIn, "Zoom in"),
            (ui.actionPrint, "Print / Save as PDF…"),
            (ui.actionLyricEditorMode, "Edit Text…"),
            (ui.actionChordEditorMode, "Edit Chords…"),
        )
        for action, tip in tips:
            action.setToolTip(tip + _shortcut_text(action))
        for action, help_html in ((ui.actionLyricEditorMode, LYRICS_HELP),
                                  (ui.actionChordEditorMode, CHORDS_HELP)):
            tip = action.toolTip().replace("&", "&amp;").replace("<", "&lt;")
            action.setToolTip("<qt>%s<br><br>%s</qt>" % (tip, help_html))
        # Desktop-only, the tooltips exactly as asked (no shortcut).
        ui.actionLyricsFont.setToolTip("Select font for lyrics")
        ui.actionChordsFont.setToolTip("Select font for chords")

        groups = (
            ((ui.actionCopySongText, "copy-text"),
             (ui.actionCopySongTextWithChords, "copy-chords"),
             (ui.actionCopySongAsImage, "copy-image")),
            ((self.transpose_down, "transpose-down"),
             (self.transpose_up, "transpose-up"),
             (self.transpose_reset, "transpose-reset")),
            ((ui.actionZoomOut, "zoom-out"),
             (ui.actionZoomActual, "zoom-reset"),
             (ui.actionZoomIn, "zoom-in"),
             (self.zoom_percent, "label")),
            ((ui.actionPrint, "print"),),
            ((ui.actionLyricsFont, "font-lyrics"),
             (ui.actionChordsFont, "font-chords")),
            ((ui.actionLyricEditorMode, "edit-text"),
             (ui.actionChordEditorMode, "edit-chords")),
        )
        for num, group in enumerate(groups):
            # The edit group (the last) starts the tail kept on the last row.
            self._addGroup(group, separator=bool(num),
                           tail_start=num == len(groups) - 1)
        # Shown only while editing, without a separator, as on the web.
        self.chord_group = [self.chord_edit, self.chord_delete]
        self._addGroup(((self.chord_edit, "chord-edit"),
                        (self.chord_delete, "chord-delete"),
                        (self.undo, "chord-undo"),
                        (self.redo, "chord-redo")))
        self._addGroup(((self.discard, None), (self.save, None)))
        for action in (self.discard, self.save):
            self.widgetForAction(action).setProperty("textButton", True)
        for action in (self.discard, self.save):
            self.widgetForAction(action).setProperty("finishButton", True)
        self._restyle()
        self.applyMode(None, False)

    def _addGroup(self, group, separator=False, tail_start=False):
        if separator:
            line = QtWidgets.QFrame(self)
            line.setObjectName("song_toolbar_separator")
            line.setProperty("separator", True)
            line.setFixedSize(1, 20)
            self._flow.addWidget(line)
            self._order.append("|")
        box = QtWidgets.QWidget(self)
        box.setProperty("tailStart", tail_start)
        row = QtWidgets.QHBoxLayout(box)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(1)
        for action, icon in group:
            if icon == "label":
                # A plain label that follows the action's text.
                label = QtWidgets.QLabel(action.text(), box)
                label.setObjectName("song_toolbar_" + action.objectName())
                label.setContentsMargins(0, 0, 0, 0)
                action.changed.connect(
                    lambda label=label, action=action:
                    label.setText(action.text()))
                self._buttons[action] = label
                self._order.append(action)
                row.addWidget(label)
                continue
            button = QtWidgets.QToolButton(box)
            button.setDefaultAction(action)
            button.setAutoRaise(True)
            button.setIconSize(QtCore.QSize(ICON_SIZE, ICON_SIZE))
            button.setToolButtonStyle(
                QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly)
            button.setObjectName("song_toolbar_" + action.objectName())
            if icon:
                self._icons[action] = icon
                action.setIconVisibleInMenu(False)
            self._buttons[action] = button
            self._order.append(action)
            row.addWidget(button)
            action.changed.connect(
                lambda action=action: self._syncVisible(action))
        self._flow.addWidget(box)

    def _syncVisible(self, action):
        """A hidden action hides its button, and a group with none shown."""
        button = self._buttons[action]
        if button.isHidden() != action.isVisible():
            return
        button.setVisible(action.isVisible())
        box = button.parentWidget()
        shown = any(not child.isHidden()
                    for child in box.findChildren(QtWidgets.QToolButton))
        box.setVisible(shown)

    def widgetForAction(self, action):
        return self._buttons.get(action)

    def toolbarActions(self):
        """The actions in toolbar order, "|" for a separator."""
        return list(self._order)

    def _restyle(self):
        """Icons and the flat web look in the palette's colours."""
        if self._restyling:
            return
        self._restyling = True
        try:
            palette = self.palette()
            text = palette.color(QtGui.QPalette.ColorRole.WindowText)
            for action, name in self._icons.items():
                action.setIcon(tinted_icon(name, text))
            window = palette.color(QtGui.QPalette.ColorRole.Window)
            dark = window.lightness() < 128
            hover = window.lighter(130) if dark else window.darker(106)
            border = window.lighter(170) if dark else window.darker(118)
            accent = palette.color(QtGui.QPalette.ColorRole.Highlight)
            self.setStyleSheet("""
QFrame#song_toolbar_separator { background: %(border)s; border: 0; }
#song_toolbar QToolButton { border: 1px solid transparent;
    border-radius: 8px; min-width: %(size)dpx; min-height: %(size)dpx;
    padding: 0; }
#song_toolbar QToolButton[textButton="true"] { padding: 0 6px; }
#song_toolbar QToolButton[finishButton="true"] { font-size: 15px; }
#song_toolbar QToolButton:hover { background: %(hover)s;
    border-color: %(border)s; }
#song_toolbar QToolButton:pressed,
#song_toolbar QToolButton[active="true"] { background: %(border)s; }
#song_toolbar QToolButton:disabled { background: transparent;
    border-color: transparent; }
#song_toolbar QToolButton#song_toolbar_actionSaveEditTool { color: %(accent)s;
    font-weight: 600; }
""" % {"size": BUTTON_SIZE, "hover": hover.name(), "border": border.name(),
       "accent": accent.name()})
        finally:
            self._restyling = False

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QtCore.QEvent.Type.PaletteChange:
            self._restyle()

    def applyMode(self, mode, finish_shown):
        """Viewing (None), Edit Text ("text") or Edit Chords ("chords")."""
        ui = self.session.ui
        # Edit Text and Edit Chords are actions, not modes, in the menus, so
        # the button of the open edit is marked here and not checked.
        for action, name in ((ui.actionLyricEditorMode, "text"),
                             (ui.actionChordEditorMode, "chords")):
            button = self.widgetForAction(action)
            if button.property("active") != (mode == name):
                button.setProperty("active", mode == name)
                button.style().unpolish(button)
                button.style().polish(button)
        for action in self.chord_group:
            action.setVisible(mode == "chords")
        for action in (self.undo, self.redo):
            action.setVisible(mode in ("text", "chords"))
        self.discard.setVisible(finish_shown)
        self.save.setVisible(finish_shown)

    def isActive(self, action):
        return bool(self.widgetForAction(action).property("active"))

    def updateChordButtons(self, has_letter, has_chord, has_any_selected):
        self.chord_edit.setEnabled(has_letter)
        text = "Edit chord" if has_chord else "Add chord"
        self.chord_edit.setToolTip(text)
        self.chord_edit.setText(text.title())
        self.chord_delete.setEnabled(has_any_selected)

    def setZoomPercent(self, percent):
        self.zoom_percent.setText("%d%%" % percent)
