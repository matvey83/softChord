"""The brief note at the bottom of the song view ("Saved", "Zoom 110%").

MIRRORED UI: the web app's showToast (softChord_web/viewer.js, #toast in
viewer.css) and the iOS app's showToast (SongPage.swift): 14 px white text on a
dark rounded box 24 px above the bottom, centred, at most 2 lines, gone after
2.2 s; a new note replaces the one shown. Desktop: it sits on the song view
(the editor), so it does not move when the toolbar wraps or an edit starts.
"""

from PyQt6 import QtCore, QtWidgets

DURATION_MS = 2200
BOTTOM = 24
SIDE = 16


class BriefNote(QtWidgets.QLabel):

    def __init__(self, view):
        super().__init__(view)
        self.setObjectName("brief_note")
        self.setWordWrap(True)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setAttribute(
            QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setStyleSheet(
            "#brief_note { background: rgba(28, 28, 30, 235); color: #fff;"
            " font-size: 14px; padding: 10px 16px; border-radius: 10px; }")
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)
        view.installEventFilter(self)
        self.hide()

    def showNote(self, text):
        self.setText(text)
        self._place()
        self.show()
        self.raise_()
        self._timer.start(DURATION_MS)

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Type.Resize and self.isVisible():
            self._place()
        return False

    def _place(self):
        view = self.parentWidget()
        room = max(60, view.width() - 2 * SIDE)
        width = min(room, self.fontMetrics().horizontalAdvance(self.text()) + 34)
        lines = 1 if width < room else 2
        self.setFixedWidth(width)
        height = self.heightForWidth(width) if lines > 1 else self.sizeHint().height()
        self.setFixedHeight(height)
        self.move((view.width() - width) // 2, view.height() - BOTTOM - height)
