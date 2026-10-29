"""

The main source file for softChord (previously softChord Editor)

Writen by: Matvey Adzhigirey
Development started in 10 December 2010
Ported to Qt6 in May-June 2023.
"""

# NOTE The sqlite3 is intentionally used instead of QtSql.

from PyQt6 import QtCore, QtGui, QtWidgets
import sys, os
import sqlite3
import traceback
import threading

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
    chord_string,
    UNKNOWN_CHORD_TEXT,
)
from softchord_song import (
    AddChordCommand,
    DeleteChordCommand,
    ReplaceChordCommand,
    DeleteSongsCommand,
    SongsTableRow,
    SongsTableModel,
    SongsProxyModel,
    SongChord,
    SongChar,
    Song,
)
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
    SongbookStore,
)
from softchord_session import (
    ChordDialog,
    CustomTextEdit,
    PdfDialog,
    PdfOptions,
    SongbookSession,
)


class _SessionAttr:
    """Read and write one SongbookSession attribute through the process shell."""

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            for cls in (SongbookSession, SongbookIO):
                if self.name in cls.__dict__:
                    return cls.__dict__[self.name]
            return self
        return getattr(object.__getattribute__(obj, "session"), self.name)

    def __set__(self, obj, value):
        setattr(object.__getattribute__(obj, "session"), self.name, value)


# Instance state assigned in SongbookSession.__init__ / songbook open.
# Methods are added from the session classes below. clipboard is included
# because QApplication.clipboard is a method and would hide the session's.
_SESSION_FIELDS = (
    "doc_editor_offset",
    "win",
    "ui",
    "on_windows",
    "curs",
    "current_song",
    "current_songbook_filename",
    "empty_doc",
    "pdf_options",
    "undo_stack",
    "chord_type_names",
    "chord_type_prints",
    "chord_type_texts_dict",
    "notes_list",
    "note_text_id_dict",
    "filter_string",
    "songs_model",
    "songs_proxy_model",
    "previous_song_text",
    "editor",
    "editor_mode_action_group",
    "zoom_levels",
    "zoom_factor",
    "clipboard",
    "ignore_song_text_changed",
    "selected_char_num",
    "selected_chord_nums",
    "hover_char_num",
    "lyrics_font",
    "lyrics_font_size",
    "lyrics_color",
    "lyrics_font_metrics",
    "chords_font",
    "chords_font_size",
    "chords_font_metrics",
    "symbols_font",
    "symbols_font_metrics",
    "chords_color",
    "unrecognized_chords_color",
    "white_color",
)




class App(QtWidgets.QApplication):
    """
    Process shell. The open songbook, current song, and editor commands live
    on SongbookSession. Attribute access is forwarded so callers can keep
    using the application object.
    """
    # Destroying a QApplication while its widgets still exist crashes Qt, and a
    # later test often constructs another App before the previous one is collectable.
    # Keep the shell alive until process exit. A second App() raises, because
    # two QApplications crash while the process is exiting.
    _singleton = None

    def __init__(self, args):
        if App._singleton is not None:
            raise RuntimeError("softChord is already running")
        super().__init__(args)
        self.session = SongbookSession()
        self.focusChanged.connect(self.session.updateEditMenu)
        # Logout or shutdown: no dialog can be shown, so an edit is saved.
        self.commitDataRequest.connect(self.session.commitDataForLogout)
        self.aboutToQuit.connect(self.session.commitDataForLogout)
        # On the class, so a later App() sees it and this shell is not collected.
        App._singleton = self

    def event(self, event):
        if event.type() == QtGui.QFileOpenEvent:
            filename = event.file()
            if not filename:
                url = event.url()
                if url is not None and url.isLocalFile():
                    filename = url.toLocalFile()
            if filename and str(filename).endswith(".songbook"):
                self.session.setCurrentSongbook(_normalize_local_path(filename))
            return True
        return super().event(event)

    def __getattr__(self, name):
        try:
            session = object.__getattribute__(self, "session")
        except AttributeError:
            raise AttributeError(name)
        try:
            return getattr(session, name)
        except AttributeError:
            raise AttributeError(name)


def _install_session_attrs():
    names = set(_SESSION_FIELDS)
    for cls in (SongbookSession, SongbookIO):
        for name in cls.__dict__:
            if not name.startswith("__"):
                names.add(name)
    for name in names:
        if name in App.__dict__:
            continue
        setattr(App, name, _SessionAttr(name))


_install_session_attrs()


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


# Prevent PyQt6 from abort()ing the process when a slot raises.
# A custom sys.excepthook takes precedence over Qt's qFatal() path.
_exception_dialog_open = False


def _handle_unhandled_exception(exc_type, exc, tb):
    """Log an exception and show a dialog. Do not re-raise (that aborts in PyQt6)."""
    global _exception_dialog_open
    if exc_type is None:
        return
    if issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
        sys.__excepthook__(exc_type, exc, tb)
        return

    traceback.print_exception(exc_type, exc, tb)

    app = QtWidgets.QApplication.instance()
    if app is None or _exception_dialog_open:
        return

    if isinstance(exc, (ValueError, FileNotFoundError, sqlite3.Error)):
        message = str(exc)
    else:
        message = "An unexpected error occurred:\n\n%s: %s" % (
            exc_type.__name__, exc)

    _exception_dialog_open = True
    try:
        parent = None
        if isinstance(app, App) and getattr(app, "win", None) is not None:
            parent = app.win
        QtWidgets.QMessageBox.critical(parent, "softChord error", message)
    except Exception:
        pass
    finally:
        _exception_dialog_open = False


def _install_exception_hooks():
    """Install process-wide hooks so Qt slots/events don't terminate the app."""
    sys.excepthook = _handle_unhandled_exception

    def _thread_hook(args):
        _handle_unhandled_exception(args.exc_type, args.exc_value,
                                    args.exc_traceback)

    threading.excepthook = _thread_hook

    def _unraisable_hook(unraisable):
        _handle_unhandled_exception(unraisable.exc_type, unraisable.exc_value,
                                    unraisable.exc_traceback)

    sys.unraisablehook = _unraisable_hook


def _configure_frozen_stdio():
    """Windowed frozen apps start with stdout/stderr set to None.

    Any print() in a Qt slot then raises AttributeError, and PyQt6 aborts the
    process. Attach them to a log file (or devnull) before creating the GUI.
    """
    if not _is_frozen():
        return
    if sys.stdout is not None and sys.stderr is not None:
        return
    log_fp = None
    try:
        if sys.platform == "darwin":
            log_dir = os.path.join(os.path.expanduser("~"), "Library", "Logs")
        elif sys.platform == "win32":
            log_dir = os.path.join(
                os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                "softChord")
        else:
            log_dir = os.path.expanduser("~")
        os.makedirs(log_dir, exist_ok=True)
        log_fp = open(os.path.join(log_dir, "softChord.log"),
                      "a",
                      encoding="utf-8",
                      errors="replace",
                      buffering=1)
    except Exception:
        log_fp = open(os.devnull, "w")
    if sys.stdout is None:
        sys.stdout = log_fp
    if sys.stderr is None:
        sys.stderr = log_fp


def register_songbook_file_association():
    """Register *.songbook -> this executable in the current-user registry.

    macOS associations come from the app bundle Info.plist. On Windows the
    standalone exe has no installer, so we claim the extension at launch
    (HKCU, no admin required) whenever the stored command path is stale.
    """
    if sys.platform != "win32" or not _is_frozen():
        return

    import winreg
    import ctypes

    exe = os.path.abspath(sys.executable)
    command = '"%s" "%%1"' % exe
    prog_id = "softChord.songbook"
    open_key = r"Software\Classes\%s\shell\open\command" % prog_id

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, open_key) as key:
            current, _ = winreg.QueryValueEx(key, None)
        if current == command:
            return
    except OSError:
        pass

    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                              r"Software\Classes\.songbook") as key:
            winreg.SetValueEx(key, None, 0, winreg.REG_SZ, prog_id)
            winreg.SetValueEx(key, "Content Type", 0, winreg.REG_SZ,
                              "application/x-softchord-songbook")

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                              r"Software\Classes\%s" % prog_id) as key:
            winreg.SetValueEx(key, None, 0, winreg.REG_SZ,
                              "softChord songbook")

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                              r"Software\Classes\%s\DefaultIcon" %
                              prog_id) as key:
            winreg.SetValueEx(key, None, 0, winreg.REG_SZ, "%s,0" % exe)

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, open_key) as key:
            winreg.SetValueEx(key, None, 0, winreg.REG_SZ, command)

        SHCNE_ASSOCCHANGED = 0x08000000
        SHCNF_FLUSH = 0x1000
        ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_FLUSH,
                                             None, None)
    except OSError:
        # Association is convenience; never block the app from starting.
        pass


def _set_app_icon(app):
    """
    The window and Dock icon. The PyInstaller build puts the icons folder next
    to this file too (see softchord.spec).
    """
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons",
                        "softchord.png")
    if os.path.exists(path):
        app.setWindowIcon(QtGui.QIcon(path))


def main():
    """
    The main event loop. This function is also run by the Windows executable.
    """

    _configure_frozen_stdio()
    _install_exception_hooks()
    register_songbook_file_association()

    app = App(sys.argv)
    _set_app_icon(app)
    app.setOverrideCursor(QtGui.QCursor(QtCore.Qt.CursorShape.WaitCursor))

    input_files = [filename for filename in sys.argv[1:]]

    if input_files:
        if input_files[0].endswith(".songbook"):
            app.setCurrentSongbook(input_files[0])
        else:
            for filename in input_files:
                ext = os.path.splitext(filename)[1]
                if ext == '.txt':
                    app.importTextFiles([filename])
                elif ext in chordpro_extensions:
                    app.importFromChordPro(filename)
                else:
                    print('WARNING: invalid file type:', filename)

    app.restoreOverrideCursor()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

#EOF
