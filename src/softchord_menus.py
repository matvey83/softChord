"""Menu bar wiring and window title for the SoftChord editor.

Keeps the QAction connections and the window-title text out of the large
session module so Phase 1 Account/File stubs can land here without mixing
them into the editor.
"""

import os

from PyQt6 import QtGui, QtWidgets


# Phase 1 copy, shown with one OK button. These actions do not open a
# songbook and do not use the network.
_SIGN_IN = (
    "Sign-in isn't available yet",
    "softChord accounts are coming in a later update.",
)
_SHARE = (
    "Sharing isn't available yet",
    "Sharing needs a softChord account, which is coming in a later update.",
)
_ACCOUNT_SONGBOOK = (
    "Accounts aren't available yet",
    "This needs a softChord account, which is coming in a later update.",
)
_OPEN_LINK = (
    "Links aren't available yet",
    "Opening shared links is coming in a later update.",
)


def show_not_available(parent, title, message):
    """Explain that an account or link action is not in this update."""
    box = QtWidgets.QMessageBox(parent)
    box.setIcon(QtWidgets.QMessageBox.Icon.Information)
    box.setWindowTitle(title)
    box.setText(message)
    box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
    box.exec()


def _on_not_available(parent, title, message):
    def handler(checked=False):
        show_not_available(parent, title, message)

    return handler


def _action(parent, name, text):
    action = QtGui.QAction(parent)
    action.setObjectName(name)
    action.setText(text)
    return action


def _add_file_account_actions(session):
    """After Save Songbook As: Open From Account, Upload, Share, Open Link."""
    ui = session.ui
    menu = ui.menuFile
    ui.actionOpenFromAccount = _action(
        menu, "actionOpenFromAccount", "Open From Account...")
    ui.actionUploadToAccount = _action(
        menu, "actionUploadToAccount", "Upload to Account...")
    ui.actionShare = _action(menu, "actionShare", "Share...")
    ui.actionOpenLink = _action(menu, "actionOpenLink", "Open Link...")

    items = (
        (ui.actionOpenFromAccount, _ACCOUNT_SONGBOOK),
        (ui.actionUploadToAccount, _ACCOUNT_SONGBOOK),
        (ui.actionShare, _SHARE),
        (ui.actionOpenLink, _OPEN_LINK),
    )
    for action, (title, message) in items:
        action.triggered.connect(
            _on_not_available(session.win, title, message))

    # Save Songbook As is already followed by a separator. The four items
    # sit under that separator, and another separator keeps Import separate.
    actions = menu.actions()
    save_at = actions.index(ui.actionSaveSongbook)
    insert_before = actions[save_at + 2]
    for action, _copy in items:
        menu.insertAction(insert_before, action)
    menu.insertSeparator(insert_before)


def _add_account_menu(session):
    """Account, after Settings. Sign In explains itself; Settings is dimmed."""
    ui = session.ui
    menu = QtWidgets.QMenu(ui.menubar)
    menu.setObjectName("menuAccount")
    menu.setTitle("Account")
    ui.menuAccount = menu
    ui.actionSignIn = _action(menu, "actionSignIn", "Sign In...")
    ui.actionAccountSettings = _action(
        menu, "actionAccountSettings", "Account Settings...")
    ui.actionAccountSettings.setEnabled(False)
    title, message = _SIGN_IN
    ui.actionSignIn.triggered.connect(
        _on_not_available(session.win, title, message))
    menu.addAction(ui.actionSignIn)
    menu.addAction(ui.actionAccountSettings)
    ui.menubar.addMenu(menu)


def wire_menus(session):
    """Connect the main window menu actions to the session."""
    ui = session.ui

    ui.actionNewSongbook.triggered.connect(session.newSongbook)
    ui.actionOpenSongbook.triggered.connect(session.openSongbook)
    ui.actionCloseSongbook.triggered.connect(session.closeSongbook)
    ui.actionSaveSongbook.triggered.connect(session.saveSongbook)
    ui.actionAppendSongbook.triggered.connect(session.appendSongbookSelected)

    ui.actionPrint.triggered.connect(session.printSelectedSongs)
    ui.actionQuit.triggered.connect(session.win.close)
    ui.actionNewSong.triggered.connect(session.createNewSong)

    ui.actionDeleteSongs.triggered.connect(session.deleteSelectedSongs)
    ui.actionRemoveTrailingSpaces.triggered.connect(
        session.removeTrailingSpaces)
    ui.actionDeleteSong.triggered.connect(session.deleteSelectedSongs)
    ui.actionRenumberSongs.triggered.connect(session.renumberAllSongs)

    ui.actionExportSinglePdf.triggered.connect(session.exportToSinglePdf)
    ui.actionExportSongToPdf.triggered.connect(session.exportToSinglePdf)
    ui.actionExportMultiplePdfs.triggered.connect(session.exportToMultiplePdfs)
    ui.actionExportText.triggered.connect(session.exportToText)

    ui.actionExportChordPro.triggered.connect(session.exportToChordPro)
    ui.actionImportText.triggered.connect(session.browseForTextFile)
    ui.actionImportChordPro.triggered.connect(session.importFromChordPro)
    ui.actionLyricsFont.triggered.connect(session.changeLyricsFont)
    ui.actionChordsFont.triggered.connect(session.changeChordFont)

    ui.actionUndo.triggered.connect(session.undo)
    ui.actionRedo.triggered.connect(session.redo)
    ui.actionCut.triggered.connect(session.cutSelected)
    ui.actionCopy.triggered.connect(session.copySelected)
    ui.actionPaste.triggered.connect(session.pasteSelected)
    ui.actionCopySongText.triggered.connect(session.copySongText)
    ui.actionCopySongTextWithChords.triggered.connect(
        session.copySongTextWithChords)
    ui.actionCopySongAsImage.triggered.connect(session.copySongAsImage)
    ui.actionExportClipboard.triggered.connect(session.copySongText)

    # FIXME we need only one way to import a song from the clipboard. Remove one of these actions:
    ui.actionPasteAsNewSong.triggered.connect(session.pasteAsNewSong)
    ui.actionImportClipboard.triggered.connect(session.pasteAsNewSong)

    # Chords and Lyrics select the segment of the open draft. A song is
    # already editing when it opens.
    ui.actionChordEditorMode.triggered.connect(session.chordEditorSelected)
    ui.actionLyricEditorMode.triggered.connect(session.lyricEditorSelected)
    ui.actionSaveEdit.triggered.connect(session.saveEdit)
    ui.actionDiscardEdit.triggered.connect(session.discardEdit)

    ui.actionZoomIn.triggered.connect(session.zoomIn)
    ui.actionZoomOut.triggered.connect(session.zoomOut)
    ui.actionZoomActual.triggered.connect(session.zoomActual)

    _add_file_account_actions(session)
    _add_account_menu(session)


def update_window_title(win, filename, original_path=None, read_only=False):
    """Set the main window title for the open songbook (or none)."""
    if filename is None:
        win.setWindowTitle("SoftChord[*]")
        return
    if original_path is not None:
        songbook_name = os.path.splitext(os.path.basename(original_path))[0]
        win.setWindowTitle(
            "SoftChord - %s (converted copy, not saved)[*]" % songbook_name)
        return
    songbook_name = os.path.splitext(os.path.basename(filename))[0]
    # A converted copy returned above. A file opened here is local, or
    # read-only when it cannot be written.
    suffix = " (Read-only)" if read_only else " (Local)"
    win.setWindowTitle("SoftChord - %s%s[*]" % (songbook_name, suffix))
