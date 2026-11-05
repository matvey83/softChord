"""Menu bar wiring and window title for the SoftChord editor.

Keeps the QAction connections and the window-title text out of the large
session module so Phase 1 Account/File stubs can land here without mixing
them into the editor.
"""

import os


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

    # Edit Chords... and Edit Text... start an edit. They are actions,
    # not modes: the song is only viewed until one of them is chosen.
    ui.actionChordEditorMode.triggered.connect(session.chordEditorSelected)
    ui.actionLyricEditorMode.triggered.connect(session.lyricEditorSelected)
    ui.actionSaveEdit.triggered.connect(session.saveEdit)
    ui.actionDiscardEdit.triggered.connect(session.requestDiscardEdit)

    ui.actionZoomIn.triggered.connect(session.zoomIn)
    ui.actionZoomOut.triggered.connect(session.zoomOut)
    ui.actionZoomActual.triggered.connect(session.zoomActual)


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
    suffix = " (read-only)" if read_only else ""
    win.setWindowTitle("SoftChord - %s%s[*]" % (songbook_name, suffix))
