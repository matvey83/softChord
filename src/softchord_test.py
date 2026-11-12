"""
Execute as:

python3 softchord_test.py
"""
import unittest
import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time

import softchord

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt

# Fixtures live next to this file (the sample songbook is one directory up).
# Resolving them from __file__ lets the suite run from any working directory.
_HERE = os.path.dirname(os.path.abspath(__file__))
_TEXT_SONG = os.path.join(_HERE, "test_тест_song.txt")


class SoftChordEditorTest(unittest.TestCase):
    """Integration tests that exercise the main App / main window / panels."""

    @classmethod
    def setUpClass(cls):
        # Sign-in must not read a developer origin or a home-directory token.
        cls._saved_api_origin = os.environ.pop("SOFTCHORD_API_ORIGIN", None)
        cls._settings_dir = tempfile.mkdtemp(prefix="softchord-qsettings-")
        QtCore.QSettings.setPath(
            QtCore.QSettings.Format.IniFormat,
            QtCore.QSettings.Scope.UserScope,
            cls._settings_dir)
        cls.qapp = QtWidgets.QApplication(sys.argv)

        # Create the real App (this sets up the main window + UI)
        cls.app = softchord.App([])

        # === Mock dialog methods so tests don't block on message boxes ===
        # Using lambdas avoids binding/self issues when replacing methods on the instance.
        cls.app.info = lambda text: None          # was showing "scaled down" info dialog
        cls.app.warning = lambda text: None
        cls.app.error = lambda text: None
        cls.app.question = lambda *args, **kwargs: True   # auto-accept (for renumber etc.)
        # A song is already a draft. Leaving a dirty one must not block.
        cls.app._askSaveChanges = lambda: "discard"

        # Copy the sample songbook so tests do not write the original file.
        src = os.path.abspath(os.path.join(_HERE, "..", "zvuki_neba.songbook"))
        cls._td = tempfile.TemporaryDirectory()
        songbook_path = os.path.join(cls._td.name, "zvuki_neba.songbook")
        shutil.copyfile(src, songbook_path)
        cls.app.setCurrentSongbook(songbook_path)

    @classmethod
    def tearDownClass(cls):
        # Clean up the App
        if hasattr(cls, 'app'):
            cls.app.closeSongbook()
            cls.app.quit()
        if hasattr(cls, 'qapp'):
            cls.qapp.quit()
        if hasattr(cls, '_td'):
            cls._td.cleanup()
        saved = getattr(cls, "_saved_api_origin", None)
        if saved is not None:
            os.environ["SOFTCHORD_API_ORIGIN"] = saved
        settings_dir = getattr(cls, "_settings_dir", None)
        if settings_dir:
            shutil.rmtree(settings_dir, ignore_errors=True)

    def setUp(self):
        self.app = self.__class__.app
        self.prev_rows = self.app.songs_model.rowCount()
        # Ignore the process env unless a test passes its own mapping.
        self._saved_account_env = self.app.account.env
        self.app.account.env = {}

    def tearDown(self):
        self.app.account.env = self._saved_account_env
        self.app.account.show_signed_in(None)

    def test_create_and_delete_song(self):
        """Basic create/delete through the App (main window buttons/panels)."""
        self.app.createNewSong()
        self.assertEqual(self.app.songs_model.rowCount(), self.prev_rows + 1)

        self.app.deleteSelectedSongs()
        self.assertEqual(self.app.songs_model.rowCount(), self.prev_rows)

    def _import_then_export(self, song_file, add_chords=()):
        """Import one text file, export it, delete it; return the exported text.

        add_chords: (character_num, note_id) chords added before the export.
        """
        rows = self.app.songs_model.rowCount()
        self.app.importTextFiles([song_file])
        self.assertEqual(self.app.songs_model.rowCount(), rows + 1)
        song = self.app.current_song
        for character_num, note_id in add_chords:
            song._addChord(softchord.SongChord(
                song, character_num, note_id, 0, -1, "", 0))
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            out_path = tmp.name
        try:
            self.app.exportToText(out_path)
            with open(out_path, encoding="utf-8", newline="") as fh:
                exported = fh.read()
        finally:
            os.remove(out_path)
        self.app.deleteSelectedSongs()
        self.assertEqual(self.app.songs_model.rowCount(), rows)
        return exported

    def _write_temp_text(self, text):
        with tempfile.NamedTemporaryFile(
                "w", suffix=".txt", delete=False, encoding="utf-8",
                newline="") as tmp:
            tmp.write(text)
        self.addCleanup(os.remove, tmp.name)
        return tmp.name

    def test_import_and_export_text_roundtrip(self):
        """Import a text file, export it, and import that export again.

        A chord name is written starting above its letter, which is where a
        text import reads it from, so export -> import -> export is the same.
        """
        song_file = _TEXT_SONG
        exported = self._import_then_export(song_file)
        with open(song_file, encoding="utf-8", newline="") as fh:
            original = fh.read().splitlines(keepends=True)
        # Not quite the file: a chord always sits on a letter, so the A over
        # the space before "This" and "Your" goes onto the T and the Y.
        changed = {
            0: "\ufeff A           D\r\n",
            2: " A           D\r\n",
            4: " A    E/G\u266f  F\u266fm\r\n",
        }
        expected = "".join(changed.get(i, line) for i, line in enumerate(original))
        self.assertEqual(exported, expected)
        again = self._import_then_export(self._write_temp_text(exported))
        self.assertEqual(again, exported)

    def test_text_with_chords_on_letters_comes_back_unchanged(self):
        """Multi-letter names, a name past the line end, and Cyrillic lyrics."""
        lyric = "Shine on me, Lord Jesus"
        chords = [(0, "Am7"), (6, "E/G\u266f"), (13, "F\u266fm"),
                  (len(lyric) - 1, "Dsus4")]
        row = ""
        for column, name in chords:
            row = row.ljust(column) + name
        text = ("\ufeff" + row + "\r\n" + lyric + "\r\n"
                + "G" + " " * 15 + "Em\r\n" + "Это русские слова\r\n")
        self.assertEqual(self._import_then_export(self._write_temp_text(text)),
                         text)

    def test_chords_on_neighbouring_letters_keep_a_space_between(self):
        """A name that would touch the one before it moves right, past a space.

        The text cannot hold both on neighbouring letters, so the import reads
        the moved name on the letter it is written over, and a second export
        is the same as the first.
        """
        text = "\ufeffAm7\r\nShine on me\r\n"
        # D on the "h" and E on the "i", right after Am7 on the "S".
        exported = self._import_then_export(
            self._write_temp_text(text), add_chords=[(1, 2), (2, 4)])
        self.assertEqual(exported, "\ufeffAm7 D E\r\nShine on me\r\n")
        again = self._import_then_export(self._write_temp_text(exported))
        self.assertEqual(again, exported)

    def test_export_to_single_pdf(self):
        """Basic PDF export through the App."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            out_path = tmp.name

        try:
            self.app.exportToSinglePdf(out_path)
            self.assertTrue(os.path.isfile(out_path))
            self.assertGreater(os.path.getsize(out_path), 1000)  # Sanity: not empty
        finally:
            if os.path.exists(out_path):
                os.remove(out_path)

    def test_transpose_up_and_down(self):
        """Test the App-level transpose buttons/panel actions."""
        # Import a song that has chords
        self.app.importTextFiles([_TEXT_SONG])
        self.assertEqual(self.app.songs_model.rowCount(), self.prev_rows + 1)

        # Select the newly imported song (last one)
        last_row = self.app.songs_model.rowCount() - 1
        self.app.ui.songs_view.selectRow(last_row)

        original_text = self.app.current_song.getAsText(include_chords=True)

        self.app.transposeUp()
        up_text = self.app.current_song.getAsText(include_chords=True)
        self.assertNotEqual(original_text, up_text)

        self.app.transposeDown()
        down_text = self.app.current_song.getAsText(include_chords=True)
        self.assertEqual(original_text, down_text)

        # Cleanup
        self.app.deleteSelectedSongs()

    def test_reset_transpose_button(self):
        """Reset transpose is dimmed until the song is moved, then restores the opened key."""
        self.app.importTextFiles([_TEXT_SONG])
        last_row = self.app.songs_model.rowCount() - 1
        self.app.ui.songs_view.selectRow(last_row)
        button = self.app.toolbar.transpose_reset

        original_text = self.app.current_song.getAsText(include_chords=True)
        self.assertFalse(button.isEnabled())

        self.app.transposeUp()
        self.app.transposeUp()
        self.assertTrue(button.isEnabled())
        self.app.transposeDown()
        self.app.transposeDown()
        self.assertFalse(button.isEnabled())

        self.app.transposeDown()
        self.app.transposeDown()
        self.app.transposeDown()
        self.assertTrue(button.isEnabled())
        button.trigger()
        self.assertEqual(self.app.current_song.getAsText(include_chords=True), original_text)
        self.assertFalse(button.isEnabled())

        # Cleanup
        self.app.deleteSelectedSongs()

    def test_export_to_chordpro(self):
        """Test exporting the current song to ChordPro format via the App."""
        self.app.importTextFiles([_TEXT_SONG])
        self.assertEqual(self.app.songs_model.rowCount(), self.prev_rows + 1)

        with tempfile.NamedTemporaryFile(suffix=".chordpro", delete=False) as tmp:
            out_path = tmp.name

        try:
            self.app.exportToChordPro(out_path)
            self.assertTrue(os.path.isfile(out_path))

            with open(out_path, encoding="utf-8") as fh:
                content = fh.read()

            # Basic sanity checks for ChordPro output
            self.assertIn("{title:", content)
            self.assertTrue("[" in content and "]" in content)  # chords in brackets
        finally:
            if os.path.exists(out_path):
                os.remove(out_path)

        self.app.deleteSelectedSongs()

    def test_song_filtering(self):
        """Test the filter panel / search functionality on the main window."""
        # Make sure we have songs loaded
        self.assertGreater(self.app.songs_model.rowCount(), 0)

        # Apply a filter that should match very few songs
        self.app.songFilterEdited("Amazing Grace")
        filtered_count = self.app.songs_proxy_model.rowCount()
        self.assertLess(filtered_count, self.app.songs_model.rowCount())

        # Clear the filter
        self.app.clearFilterClicked()
        self.app.songFilterEdited("")  # Explicit clear
        self.assertEqual(self.app.songs_proxy_model.rowCount(), self.app.songs_model.rowCount())

    # ------------------------------------------------------------------
    # Core keyboard input tests (processKeyPressed)
    # These exercise one of the most important user workflows: adding
    # and editing chords directly from the keyboard.
    # ------------------------------------------------------------------

    def test_keyboard_add_chord_with_letter_key(self):
        """Pressing C/D/E etc. on a selected character should add a chord."""
        # Make sure we have a current song selected
        if self.app.current_song is None:
            self.app.ui.songs_view.selectRow(0)

        self.app.selected_char_num = 5
        self.app.previous_song_text = self.app.current_song.getAllText()

        result = self.app.processKeyPressed(Qt.Key.Key_C)
        self.assertTrue(result)

        chord = self.app.current_song.getChordAtPosition(5)
        self.assertIsNotNone(chord)
        self.assertEqual(chord.note_id, 0)  # C

    def test_keyboard_toggle_major_minor_with_m(self):
        """M key should toggle the selected chord between major and minor."""
        if self.app.current_song is None:
            self.app.ui.songs_view.selectRow(0)

        self.app.selected_char_num = 5
        self.app.previous_song_text = self.app.current_song.getAllText()

        self.app.processKeyPressed(Qt.Key.Key_G)  # Add G major

        chord = self.app.current_song.getChordAtPosition(5)
        self.assertEqual(chord.chord_type_id, 0)

        # The flip is an undo step: the song gets a new chord object.
        self.app.processKeyPressed(Qt.Key.Key_M)
        chord = self.app.current_song.getChordAtPosition(5)
        self.assertEqual(chord.chord_type_id, 1)  # Minor

    def test_keyboard_move_chord_with_arrows(self):
        """Left/Right should move the selected chord position."""
        if self.app.current_song is None:
            self.app.ui.songs_view.selectRow(0)

        self.app.selected_char_num = 5
        self.app.previous_song_text = self.app.current_song.getAllText()

        self.app.processKeyPressed(Qt.Key.Key_C)
        chord = self.app.current_song.getChordAtPosition(5)

        # The move is an undo step: the song gets a new chord object.
        self.app.processKeyPressed(Qt.Key.Key_Right)
        self.assertIsNone(self.app.current_song.getChordAtPosition(5))
        moved = self.app.current_song.getChordAtPosition(6)
        self.assertIsNotNone(moved)
        self.assertEqual(moved.note_id, chord.note_id)

    def test_dirty_leave_cancel_discard_and_save(self):
        """Save, Don't Save and Cancel while a song stays the one on screen."""
        app = self.app
        app.createNewSong()
        song_id = app.current_song.id
        self.addCleanup(self._delete_song, song_id)
        app.currentSongTitleEdited("Leave Me")
        self.assertTrue(app.editChanged())
        self.assertTrue(app.textEditing())

        app._askSaveChanges = lambda: "cancel"
        self.assertFalse(app.confirmLeaveEdit())
        self.assertTrue(app.editing())
        self.assertTrue(app.textEditing())
        self.assertEqual(app.current_song.title, "Leave Me")
        stored = app.curs.execute(
            "SELECT title FROM songs WHERE id=?", (song_id,)).fetchone()[0]
        self.assertEqual(stored, "")

        app._askSaveChanges = lambda: "discard"
        self.assertTrue(app.confirmLeaveEdit())
        self.assertFalse(app.editing())
        self.assertEqual(app.current_song.title, "")
        self.assertEqual(app.curs.execute(
            "SELECT title FROM songs WHERE id=?", (song_id,)).fetchone()[0], "")

        app.currentSongTitleEdited("Saved Title")
        self.assertTrue(app.editChanged())
        app._askSaveChanges = lambda: "save"
        self.assertTrue(app.confirmLeaveEdit())
        self.assertFalse(app.editing())
        self.assertEqual(app.current_song.title, "Saved Title")
        self.assertEqual(app.curs.execute(
            "SELECT title FROM songs WHERE id=?", (song_id,)).fetchone()[0],
            "Saved Title")

    def test_dirty_keep_open_cancel_discard_and_save(self):
        """Save, Don't Save and Cancel while the same song stays on screen.

        keep_open is the path used by a right-click, trim, or renumber: the
        song is not closed, and the same segment starts again.
        """
        app = self.app
        app.createNewSong()
        song_id = app.current_song.id
        self.addCleanup(self._delete_song, song_id)
        self.assertTrue(app.textEditing())
        app.currentSongTitleEdited("Keep Open")
        self.assertTrue(app.editChanged())

        app._askSaveChanges = lambda: "cancel"
        self.assertFalse(app.confirmLeaveEdit(keep_open=True))
        self.assertTrue(app.editing())
        self.assertTrue(app.textEditing())
        self.assertTrue(app.editChanged())
        self.assertEqual(app.current_song.id, song_id)
        self.assertEqual(app.current_song.title, "Keep Open")
        self.assertEqual(app.curs.execute(
            "SELECT title FROM songs WHERE id=?", (song_id,)).fetchone()[0],
            "")

        app._askSaveChanges = lambda: "discard"
        self.assertTrue(app.confirmLeaveEdit(keep_open=True))
        self.assertTrue(app.editing())
        self.assertTrue(app.textEditing())
        self.assertFalse(app.editChanged())
        self.assertEqual(app.current_song.id, song_id)
        self.assertEqual(app.current_song.title, "")
        self.assertEqual(app.curs.execute(
            "SELECT title FROM songs WHERE id=?", (song_id,)).fetchone()[0],
            "")

        app.currentSongTitleEdited("Kept Title")
        self.assertTrue(app.editChanged())
        app._askSaveChanges = lambda: "save"
        self.assertTrue(app.confirmLeaveEdit(keep_open=True))
        self.assertTrue(app.editing())
        self.assertTrue(app.textEditing())
        self.assertFalse(app.editChanged())
        self.assertEqual(app.current_song.id, song_id)
        self.assertEqual(app.current_song.title, "Kept Title")
        self.assertEqual(app.curs.execute(
            "SELECT title FROM songs WHERE id=?", (song_id,)).fetchone()[0],
            "Kept Title")

    def _delete_song(self, song_id):
        self.app._askSaveChanges = lambda: "discard"
        if (self.app.current_song is not None
                and self.app.current_song.id == song_id):
            self.app.deleteSelectedSongs()

    def test_keyboard_up_does_not_transpose_selected_chord(self):
        """Up/Down arrows do not change the selected chord."""
        if self.app.current_song is None:
            self.app.ui.songs_view.selectRow(0)

        self.app.selected_char_num = 5
        self.app.previous_song_text = self.app.current_song.getAllText()

        self.app.processKeyPressed(Qt.Key.Key_D)
        chord = self.app.current_song.getChordAtPosition(5)
        original_note = chord.note_id

        self.assertFalse(self.app.processKeyPressed(Qt.Key.Key_Up))
        self.assertFalse(self.app.processKeyPressed(Qt.Key.Key_Down))
        self.assertEqual(self.app.current_song.getChordAtPosition(5).note_id, original_note)

    def test_account_menu_and_file_items(self):
        """Account follows Settings. The four File items follow Save As."""
        ui = self.app.ui
        bar = [action.text() for action in ui.menubar.actions()]
        self.assertEqual(bar, ["File", "Edit", "Song", "Settings", "Account"])
        self.assertEqual(
            [action.objectName() for action in ui.menuAccount.actions()],
            ["actionSignedInEmail", "actionSignIn", "actionSignOut",
             "actionSignOutEverywhere", "actionAccountSettings"])
        self.assertFalse(ui.actionSignOutEverywhere.isVisible())
        self.assertEqual(
            [action.text() for action in ui.menuAccount.actions()
             if action.isVisible()],
            ["Sign In...", "Account Settings..."])
        self.assertTrue(ui.actionSignIn.isEnabled())
        self.assertTrue(ui.actionSignIn.isVisible())
        self.assertFalse(ui.actionSignOut.isVisible())
        self.assertFalse(ui.actionSignedInEmail.isVisible())
        self.assertFalse(ui.actionAccountSettings.isEnabled())

        labels = ["---" if action.isSeparator() else action.text()
                  for action in ui.menuFile.actions()]
        save_at = labels.index("Save Songbook As...")
        self.assertEqual(labels[save_at:save_at + 7], [
            "Save Songbook As...",
            "---",
            "Open From Account...",
            "Upload to Account...",
            "Share...",
            "Open Link...",
            "---",
        ])

    def _account_actions(self):
        ui = self.app.ui
        return (ui.actionSignIn, ui.actionOpenFromAccount,
                ui.actionUploadToAccount, ui.actionShare, ui.actionOpenLink)

    def test_not_available_dialogs(self):
        """Each account action shows its title and message, with one OK."""
        expected = [
            ("Not available yet", "Sign-in is coming in a later update."),
            ("Accounts aren't available yet",
             "This needs a softChord account, which is coming in a later update."),
            ("Accounts aren't available yet",
             "This needs a softChord account, which is coming in a later update."),
            ("Sharing isn't available yet",
             "Sharing needs a softChord account, which is coming in a later update."),
            ("Links aren't available yet",
             "Opening shared links is coming in a later update."),
        ]
        shown = []

        def exec_(box):
            shown.append((
                box.windowTitle(),
                box.text(),
                box.standardButtons(),
                len(box.buttons()),
                box.icon(),
            ))
            return QtWidgets.QMessageBox.StandardButton.Ok

        original = QtWidgets.QMessageBox.exec
        QtWidgets.QMessageBox.exec = exec_
        songbook = self.app.current_songbook_filename
        try:
            for action in self._account_actions():
                action.trigger()
            self.app.ui.actionAccountSettings.trigger()
        finally:
            QtWidgets.QMessageBox.exec = original

        ok = QtWidgets.QMessageBox.StandardButton.Ok
        info = QtWidgets.QMessageBox.Icon.Information
        self.assertEqual([(title, text) for title, text, _buttons, _count, _icon
                          in shown], expected)
        self.assertTrue(all(buttons == ok and count == 1 and icon == info
                            for _title, _text, buttons, count, icon in shown))
        self.assertEqual(self.app.current_songbook_filename, songbook)

    def test_new_actions_have_no_shortcuts(self):
        """Sign In, Sign Out, Sign Out Everywhere, Account Settings, and the four File items have no shortcut."""
        actions = self._account_actions() + (
            self.app.ui.actionAccountSettings, self.app.ui.actionSignOut,
            self.app.ui.actionSignOutEverywhere)
        for action in actions:
            self.assertTrue(action.shortcut().isEmpty(), action.text())

    def test_account_actions_use_no_network_module(self):
        """The menu stubs import no network module and open no connection."""
        import ast
        import inspect
        import socket
        import types
        import urllib.request

        from PyQt6 import QtNetwork

        import softchord_menus

        source = inspect.getsource(softchord_menus)
        tree = ast.parse(source)
        modules = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.extend(
                    alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                modules.append((node.module or "").split(".")[0])
        banned = ("socket", "ssl", "http", "urllib", "requests", "ftplib",
                  "smtplib")
        for name in banned:
            self.assertNotIn(name, modules)
        self.assertNotIn("http://", source)
        self.assertNotIn("https://", source)
        self.assertNotIn("QNetworkAccessManager", source)
        self.assertNotIn("QtNetwork", source)
        self.assertNotIn("requests", source)

        calls = []

        def refuse(kind):
            def wrapped(*args, **kwargs):
                calls.append(kind)
                raise AssertionError(kind)

            return wrapped

        real_socket = socket.socket
        real_create = socket.create_connection
        real_urlopen = urllib.request.urlopen
        real_qnam = QtNetwork.QNetworkAccessManager
        qnam_methods = ("get", "post", "put", "deleteResource",
                        "sendCustomRequest", "head")
        real_qnam_methods = {
            name: getattr(real_qnam, name) for name in qnam_methods}
        real_requests = sys.modules.get("requests")
        requests_stub = types.ModuleType("requests")
        for name in ("get", "post", "put", "patch", "delete", "head",
                     "request", "Session"):
            setattr(requests_stub, name, refuse("requests." + name))
        socket.socket = refuse("socket")
        socket.create_connection = refuse("create_connection")
        urllib.request.urlopen = refuse("urlopen")
        QtNetwork.QNetworkAccessManager = refuse("QNetworkAccessManager")
        for name in qnam_methods:
            setattr(real_qnam, name, refuse("QNetworkAccessManager." + name))
        sys.modules["requests"] = requests_stub
        before = set(sys.modules)
        original = QtWidgets.QMessageBox.exec
        QtWidgets.QMessageBox.exec = (
            lambda box: QtWidgets.QMessageBox.StandardButton.Ok)
        try:
            for action in self._account_actions():
                action.trigger()
        finally:
            QtWidgets.QMessageBox.exec = original
            socket.socket = real_socket
            socket.create_connection = real_create
            urllib.request.urlopen = real_urlopen
            QtNetwork.QNetworkAccessManager = real_qnam
            for name, method in real_qnam_methods.items():
                setattr(real_qnam, name, method)
            if real_requests is None:
                sys.modules.pop("requests", None)
            else:
                sys.modules["requests"] = real_requests
        added = [
            name for name in set(sys.modules) - before
            if name.split(".")[0] in banned
        ]
        self.assertEqual(calls, [])
        self.assertEqual(added, [])

    def test_window_title_local_read_only_and_converted_copy(self):
        from softchord_menus import update_window_title

        win = self.app.win
        self.assertEqual(
            win.windowTitle(), "SoftChord - zvuki_neba (Local)[*]")

        original = win.windowTitle()
        self.addCleanup(win.setWindowTitle, original)
        update_window_title(win, None)
        self.assertEqual(win.windowTitle(), "SoftChord[*]")
        update_window_title(win, os.path.join("books", "Mine.songbook"))
        self.assertEqual(win.windowTitle(), "SoftChord - Mine (Local)[*]")
        update_window_title(
            win, os.path.join("books", "Mine.songbook"), read_only=True)
        self.assertEqual(
            win.windowTitle(), "SoftChord - Mine (Read-only)[*]")
        update_window_title(
            win, os.path.join("tmp", "copy.songbook"),
            original_path=os.path.join("books", "Old Book.songbook"),
            read_only=True)
        self.assertEqual(
            win.windowTitle(),
            "SoftChord - Old Book (converted copy, not saved)[*]")

    def test_read_only_file_title_comes_from_the_open(self):
        """A songbook that cannot be written shows (Read-only)."""
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("chmod does not stop root from writing a songbook")
        app = self.app
        home = app.current_songbook_filename
        folder = tempfile.mkdtemp()
        path = os.path.join(folder, "locked.songbook")
        shutil.copyfile(home, path)
        os.chmod(path, 0o444)
        os.chmod(folder, 0o555)

        def restore():
            os.chmod(folder, 0o755)
            if os.path.exists(path):
                os.chmod(path, 0o644)
            app._askSaveChanges = lambda: "discard"
            app.setCurrentSongbook(home)
            shutil.rmtree(folder, ignore_errors=True)

        self.addCleanup(restore)
        app._askSaveChanges = lambda: "discard"
        app.setCurrentSongbook(path)
        self.assertEqual(
            app.win.windowTitle(), "SoftChord - locked (Read-only)[*]")

    def _empty_songbook(self, filename):
        """A new empty songbook. Cleanup reopens the book that is open now."""
        folder = tempfile.mkdtemp()
        path = os.path.join(folder, filename)
        softchord.SongbookStore.create_file(path).close()
        home = self.app.current_songbook_filename

        def restore():
            self.app._askSaveChanges = lambda: "discard"
            self.app.setCurrentSongbook(home)
            shutil.rmtree(folder, ignore_errors=True)

        self.addCleanup(restore)
        return path

    def _prepare_open_song(self):
        """A clean draft of a song that is already in the open songbook."""
        app = self.app
        app._askSaveChanges = lambda: "discard"
        if app.current_song is None:
            app.ui.songs_view.selectRow(0)
        self.assertIsNotNone(app.current_song)
        if app.editChanged():
            app.discardEdit()
        self.assertTrue(app.editing())
        self.assertFalse(app.editChanged())
        return app.current_song.id

    def test_open_asks_before_switching_and_cancel_aborts(self):
        """A dirty draft is asked about before Open. Cancel leaves it.

        Don't Save drops the draft and opens the chosen songbook.
        """
        app = self.app
        songbook = app.current_songbook_filename
        song_id = self._prepare_open_song()
        stored_before = app.curs.execute(
            "SELECT title FROM songs WHERE id=?", (song_id,)).fetchone()[0]
        app.currentSongTitleEdited("Not yet")
        self.assertTrue(app.editChanged())
        other = self._empty_songbook("other.songbook")

        asked = []
        opened = []

        def cancel():
            asked.append("cancel")
            return "cancel"

        def file_dialog(*args, **kwargs):
            opened.append(args)
            return (other, "")

        original_ask = app._askSaveChanges
        original_dialog = QtWidgets.QFileDialog.getOpenFileName
        app._askSaveChanges = cancel
        QtWidgets.QFileDialog.getOpenFileName = staticmethod(file_dialog)
        try:
            app.openSongbook()
            self.assertEqual(asked, ["cancel"])
            self.assertEqual(opened, [])
            self.assertEqual(app.current_songbook_filename, songbook)
            self.assertEqual(app.current_song.id, song_id)
            self.assertEqual(app.current_song.title, "Not yet")
            self.assertTrue(app.editChanged())

            def discard():
                asked.append("discard")
                return "discard"

            app._askSaveChanges = discard
            app.openSongbook()
            self.assertEqual(asked, ["cancel", "discard"])
            self.assertEqual(len(opened), 1)
            self.assertEqual(os.path.abspath(app.current_songbook_filename),
                             os.path.abspath(other))
            self.assertEqual(app.win.windowTitle(),
                             "SoftChord - other (Local)[*]")
            self.assertIsNone(app.current_song)
            self.assertFalse(app.editChanged())
            import sqlite3
            conn = sqlite3.connect(songbook)
            try:
                stored_after = conn.execute(
                    "SELECT title FROM songs WHERE id=?",
                    (song_id,)).fetchone()[0]
            finally:
                conn.close()
            self.assertEqual(stored_after, stored_before)
            self.assertNotEqual(stored_after, "Not yet")
        finally:
            QtWidgets.QFileDialog.getOpenFileName = original_dialog
            app._askSaveChanges = original_ask

    def test_clean_open_switches_without_asking(self):
        """A clean draft does not prompt. Open then switches songbooks."""
        app = self.app
        self._prepare_open_song()
        other = self._empty_songbook("clean.songbook")
        asked = []
        original_ask = app._askSaveChanges
        original_dialog = QtWidgets.QFileDialog.getOpenFileName
        app._askSaveChanges = lambda: asked.append("ask") or "cancel"
        QtWidgets.QFileDialog.getOpenFileName = staticmethod(
            lambda *args, **kwargs: (other, ""))
        try:
            app.openSongbook()
        finally:
            QtWidgets.QFileDialog.getOpenFileName = original_dialog
            app._askSaveChanges = original_ask
        self.assertEqual(asked, [])
        self.assertEqual(os.path.abspath(app.current_songbook_filename),
                         os.path.abspath(other))
        self.assertEqual(app.win.windowTitle(),
                         "SoftChord - clean (Local)[*]")
        self.assertIsNone(app.current_song)

    def _contract(self):
        path = os.path.join(_HERE, "fixtures", "api-contract.json")
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    def _swap_account(self, transport, origin=None, verifier=None,
                      setting_origin=None):
        """Point the live Account menu at a temp Ini file and a mock transport."""
        account = self.app.account
        previous = (
            account.settings, account.transport, account.env,
            account.verifier_factory, account.now)
        folder = tempfile.mkdtemp(prefix="softchord-auth-")
        settings = QtCore.QSettings(
            os.path.join(folder, "auth.ini"),
            QtCore.QSettings.Format.IniFormat)
        if setting_origin:
            settings.setValue("auth/apiOrigin", setting_origin)
            settings.sync()
        account.settings = settings
        account.transport = transport
        if origin is None:
            account.env = {}
        else:
            account.env = {"SOFTCHORD_API_ORIGIN": origin}
        if verifier is not None:
            account.verifier_factory = lambda: verifier

        def restore():
            (account.settings, account.transport, account.env,
             account.verifier_factory, account.now) = previous
            account.show_signed_in(None)
            shutil.rmtree(folder, ignore_errors=True)

        self.addCleanup(restore)
        return account

    def _settle(self, action):
        """Run action and wait until the account call finishes on the GUI thread."""
        account = self.app.account
        loop = QtCore.QEventLoop()
        fired = []

        def on_settled():
            fired.append(threading.get_ident())
            if loop.isRunning():
                loop.quit()

        account.settled.connect(on_settled)
        timer = QtCore.QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(loop.quit)
        try:
            action()
            if not fired:
                timer.start(3000)
                loop.exec()
        finally:
            timer.stop()
            try:
                account.settled.disconnect(on_settled)
            except TypeError:
                pass
        self.assertTrue(fired, "auth call did not finish")
        self.assertEqual(fired[-1], threading.get_ident())

    def test_sign_in_unconfigured_makes_no_request(self):
        """No origin: the menu says so, and the transport is not called."""
        from softchord_auth import NOT_CONFIGURED

        calls = []

        def boom(exchange):
            calls.append(exchange)
            raise AssertionError("network")

        self._swap_account(boom, origin=None, setting_origin=None)
        shown = []

        def exec_(box):
            shown.append((box.windowTitle(), box.text()))
            return QtWidgets.QMessageBox.StandardButton.Ok

        original = QtWidgets.QMessageBox.exec
        QtWidgets.QMessageBox.exec = exec_
        try:
            self.app.ui.actionSignIn.trigger()
        finally:
            QtWidgets.QMessageBox.exec = original
        self.assertEqual(calls, [])
        self.assertEqual(shown, [("Not available yet", NOT_CONFIGURED)])

    def test_json_post_mock_rejects_a_post_that_is_not_json(self):
        """The mock returns 400 unless the POST is exactly application/json."""
        from softchord_auth import HttpExchange, HttpResult, JsonEnforcingTransport

        ok = HttpResult(200, b'{"ok":true}')
        transport = JsonEnforcingTransport([ok])
        logout = "https://songs.example/api/auth/logout"
        rejected = [
            HttpExchange("POST", logout, {}, b"{}"),
            HttpExchange(
                "POST", logout,
                {"Content-Type": "application/json; charset=utf-8"}, b"{}"),
            HttpExchange(
                "POST", logout, {"Content-Type": "application/json"}, None),
            HttpExchange(
                "POST", logout, {"Content-Type": "application/json"}, b""),
            HttpExchange(
                "POST", logout, {"Content-Type": "application/json"}, b"null"),
            HttpExchange(
                "POST", logout, {"Content-Type": "text/plain"}, b"{}"),
        ]
        for exchange in rejected:
            result = transport(exchange)
            self.assertEqual(result.status, 400)
            self.assertEqual(
                json.loads(result.body.decode("utf-8"))["error"],
                "invalid_request")
        self.assertEqual(len(transport.responses), 1)
        accepted = HttpExchange(
            "POST", logout, {"Content-Type": "application/json"}, b"{}")
        self.assertEqual(transport(accepted).status, 200)
        self.assertEqual(transport.responses, [])
        self.assertEqual(len(transport.calls), len(rejected) + 1)

    def test_login_token_from_pasted_link(self):
        from softchord_auth import login_token_from_text, verifier_hash

        contract = self._contract()
        token = contract["wrongVerifier"]
        origin = contract["publicOrigin"]
        self.assertEqual(
            verifier_hash(contract["verifier"]["value"]),
            contract["verifier"]["sha256"])
        link = "%s/login?client=desktop&hint=s***%%40example.com#t=%s" % (
            origin, token)
        # The %% above is for the format string; the link must contain %40.
        self.assertIn("%40", link)
        self.assertEqual(login_token_from_text(link), token)
        self.assertEqual(
            login_token_from_text("softchord://login?token=%s" % token),
            token)
        self.assertEqual(login_token_from_text("  %s\n" % token), token)
        self.assertIsNone(login_token_from_text(
            "%s/login?client=desktop" % origin))
        self.assertIsNone(login_token_from_text(""))

    def test_contract_sha_is_the_pr9_head(self):
        path = os.path.join(_HERE, "fixtures", "api-contract.json")
        with open(path, "rb") as handle:
            raw = handle.read()
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(),
            "9f213067d7a0e262a998175848dd58c1021443dd04f3abc56881b19df1c990d5")
        self.assertIn(b"/api/auth/logout-all", raw)
        sha_path = os.path.join(_HERE, "fixtures", "api-contract.sha")
        with open(sha_path, encoding="utf-8") as handle:
            self.assertEqual(
                handle.read().strip(),
                "0775e8211158c57ff0869d1dbcf961c72ef167bd")

    def test_desktop_sign_in_verify_me_and_sign_out(self):
        """Request-link, verify, /api/me, and logout match the desktop case."""
        from softchord_auth import (
            DEVICE_LABEL, HttpResult, JsonEnforcingTransport, SignInDialog,
            verifier_hash)

        contract = self._contract()
        case = next(
            item for item in contract["cases"]
            if item["name"] == "native verify, me, and logout")
        steps = case["steps"]
        origin = contract["publicOrigin"]
        verifier = contract["verifier"]["value"]
        login_token = contract["wrongVerifier"]
        session_token = "desktopSessionToken0123456789abcdefABCD_xyz"
        email = steps[2]["response"]["json"]["email"]
        self.assertEqual(email, "singer@example.com")
        inner = JsonEnforcingTransport([
            HttpResult(200, b'{"ok":true}'),
            HttpResult(200, json.dumps({
                "email": "not-used@example.com",
                "token": session_token,
            }).encode("utf-8")),
            HttpResult(200, json.dumps({"email": email}).encode("utf-8")),
            HttpResult(200, b'{"ok":true}'),
        ])
        gui = threading.get_ident()
        idents = []

        def transport(exchange):
            idents.append(threading.get_ident())
            return inner(exchange)

        account = self._swap_account(transport, origin=origin, verifier=verifier)
        dialog = SignInDialog(account, self.app.win)
        edits = dialog.findChildren(QtWidgets.QLineEdit)
        self.assertEqual(
            [edit.objectName() for edit in edits],
            ["signInEmail", "signInLink"])
        for edit in edits:
            self.assertNotEqual(
                edit.echoMode(), QtWidgets.QLineEdit.EchoMode.Password)
        self.assertNotIn("password", dialog.windowTitle().lower())
        self.assertTrue(dialog.link_edit.isHidden())

        dialog.email_edit.setText("  Singer@Example.com ")
        self._settle(lambda: dialog.send_button.click())
        self.assertEqual(dialog.status_label.text(), "Check your email")
        self.assertFalse(dialog.link_edit.isHidden())

        sent = inner.calls[0]
        step = steps[0]["request"]
        self.assertEqual(sent.method, step["method"])
        self.assertEqual(sent.url, origin + step["path"])
        self.assertEqual(sent.headers, {"Content-Type": "application/json"})
        body = json.loads(sent.body.decode("utf-8"))
        self.assertEqual(body["email"], step["json"]["email"])
        self.assertEqual(body["client"], "desktop")
        self.assertEqual(body["verifier_hash"], contract["verifier"]["sha256"])
        self.assertEqual(body["verifier_hash"], verifier_hash(verifier))
        self.assertNotIn("verifier", body)

        # The verifier is kept, so a new dialog can finish after this one closes.
        again = SignInDialog(account, self.app.win)
        self.assertEqual(again.status_label.text(), "Check your email")
        self.assertFalse(again.link_edit.isHidden())
        again.link_edit.setText(
            "%s/login?client=desktop&hint=s***@example.com#t=%s" % (
                origin, login_token))
        self._settle(lambda: again.complete_button.click())
        self.assertEqual(
            again.result(), QtWidgets.QDialog.DialogCode.Accepted)

        verified = inner.calls[1]
        verify_step = steps[1]["request"]
        self.assertEqual(verified.method, verify_step["method"])
        self.assertEqual(verified.url, origin + verify_step["path"])
        self.assertEqual(
            verified.headers, {"Content-Type": "application/json"})
        verified_body = json.loads(verified.body.decode("utf-8"))
        self.assertEqual(set(verified_body), set(verify_step["json"]))
        self.assertEqual(verified_body["token"], login_token)
        self.assertEqual(verified_body["verifier"], verifier)
        self.assertEqual(verified_body["device_label"], DEVICE_LABEL)
        self.assertIn("device_label", verify_step["json"])

        me = inner.calls[2]
        me_step = steps[2]["request"]
        self.assertEqual(me.method, me_step["method"])
        self.assertEqual(me.url, origin + me_step["path"])
        self.assertEqual(
            me.headers, {"Authorization": "Bearer %s" % session_token})
        self.assertIsNone(me.body)
        self.assertEqual(self.app.ui.signedInEmailLabel.text(), email)
        self.assertTrue(self.app.ui.actionSignedInEmail.isVisible())
        self.assertTrue(self.app.ui.actionSignOut.isVisible())
        self.assertFalse(self.app.ui.actionSignIn.isVisible())
        self.assertEqual(account.session_token(), session_token)
        self.assertEqual(account.pending_verifier(), "")

        self.assertTrue(self.app.ui.actionSignOutEverywhere.isVisible())
        self._settle(lambda: self.app.ui.actionSignOut.trigger())
        logout = inner.calls[3]
        logout_step = steps[3]["request"]
        self.assertEqual(logout.method, logout_step["method"])
        self.assertEqual(logout.url, origin + logout_step["path"])
        self.assertEqual(logout.headers, {
            "Content-Type": "application/json",
            "Authorization": "Bearer %s" % session_token,
        })
        self.assertEqual(logout.body, b"{}")
        self.assertEqual(json.loads(logout.body.decode("utf-8")),
                         logout_step["json"])
        self.assertEqual(len(inner.calls), 4)
        self.assertTrue(all(ident != gui for ident in idents))
        self.assertEqual(account.session_token(), "")
        self.assertFalse(self.app.ui.actionSignOut.isVisible())
        self.assertFalse(self.app.ui.actionSignOutEverywhere.isVisible())
        self.assertTrue(self.app.ui.actionSignIn.isVisible())
        self.assertEqual(self.app.ui.signedInEmailLabel.text(), "")

    def test_api_origin_setting_is_used_when_the_env_is_unset(self):
        from softchord_auth import HttpResult, JsonEnforcingTransport, SignInDialog

        contract = self._contract()
        origin = contract["publicOrigin"]
        transport = JsonEnforcingTransport([
            HttpResult(200, b'{"ok":true}'),
        ])
        account = self._swap_account(
            transport, origin=None, verifier=contract["verifier"]["value"],
            setting_origin=origin + "/")
        dialog = SignInDialog(account, self.app.win)
        dialog.email_edit.setText("singer@example.com")
        self._settle(lambda: dialog.send_button.click())
        self.assertEqual(dialog.status_label.text(), "Check your email")
        self.assertEqual(
            transport.calls[0].url, origin + "/api/auth/request-link")

    def test_env_origin_wins_over_the_setting(self):
        from softchord_auth import HttpResult, JsonEnforcingTransport, SignInDialog

        contract = self._contract()
        origin = contract["publicOrigin"]
        transport = JsonEnforcingTransport([
            HttpResult(200, b'{"ok":true}'),
        ])
        account = self._swap_account(
            transport, origin=origin,
            verifier=contract["verifier"]["value"],
            setting_origin="https://wrong.example")
        dialog = SignInDialog(account, self.app.win)
        dialog.email_edit.setText("not-an-email")
        dialog.send_button.click()
        self.assertEqual(transport.calls, [])
        self.assertEqual(
            dialog.status_label.text(), "Enter a valid email address.")
        dialog.email_edit.setText("singer@example.com")
        self._settle(lambda: dialog.send_button.click())
        self.assertEqual(
            transport.calls[0].url, origin + "/api/auth/request-link")
        self.assertNotIn("wrong.example", transport.calls[0].url)

    def test_sign_out_without_an_origin_clears_the_token_and_does_not_connect(self):
        calls = []

        def boom(exchange):
            calls.append(exchange)
            raise AssertionError("network")

        account = self._swap_account(boom, origin=None)
        account.settings.setValue("auth/sessionToken", "kept-locally")
        account.settings.sync()
        account.show_signed_in("singer@example.com")
        self.app.ui.actionSignOut.trigger()
        self.assertEqual(calls, [])
        self.assertEqual(account.session_token(), "")
        self.assertTrue(self.app.ui.actionSignIn.isVisible())

    def test_me_unauthorized_clears_the_saved_session(self):
        from softchord_auth import HttpResult, JsonEnforcingTransport

        contract = self._contract()
        inner = JsonEnforcingTransport([
            HttpResult(401, b'{"error":"unauthorized"}'),
        ])
        gui = threading.get_ident()
        idents = []

        def transport(exchange):
            idents.append(threading.get_ident())
            return inner(exchange)

        account = self._swap_account(
            transport, origin=contract["publicOrigin"])
        account.settings.setValue("auth/sessionToken", "stale-token")
        account.settings.setValue("auth/pendingVerifier", "pending")
        self._settle(lambda: account.refresh())
        self.assertEqual(len(inner.calls), 1)
        self.assertNotEqual(idents[0], gui)
        me = inner.calls[0]
        self.assertEqual(me.method, "GET")
        self.assertEqual(me.url, contract["publicOrigin"] + "/api/me")
        self.assertEqual(me.headers, {"Authorization": "Bearer stale-token"})
        self.assertIsNone(me.body)
        self.assertEqual(account.session_token(), "")
        self.assertEqual(account.pending_verifier(), "")
        self.assertFalse(self.app.ui.actionSignOut.isVisible())

    def test_configured_sign_in_menu_opens_the_dialog_without_a_request(self):
        from softchord_auth import JsonEnforcingTransport, SignInDialog

        transport = JsonEnforcingTransport([])
        self._swap_account(
            transport, origin=self._contract()["publicOrigin"])
        opened = []

        def fake_exec(dialog):
            opened.append(dialog)
            return QtWidgets.QDialog.DialogCode.Rejected

        original = SignInDialog.exec
        SignInDialog.exec = fake_exec
        try:
            self.app.ui.actionSignIn.trigger()
        finally:
            SignInDialog.exec = original
        self.assertEqual(len(opened), 1)
        self.assertIsInstance(opened[0], SignInDialog)
        self.assertEqual(transport.calls, [])

    def test_http_origin_is_rejected_except_loopback(self):
        from softchord_auth import normalize_origin

        self.assertIsNone(normalize_origin("http://songs.example"))
        self.assertIsNone(normalize_origin("http://localhost.example"))
        self.assertIsNone(normalize_origin("http://127.0.0.1.example"))
        self.assertIsNone(normalize_origin("http://user:pass@localhost"))
        self.assertEqual(
            normalize_origin("https://songs.example"), "https://songs.example")
        self.assertEqual(
            normalize_origin("http://localhost:8787"), "http://localhost:8787")
        self.assertEqual(
            normalize_origin("http://127.0.0.1:8787"), "http://127.0.0.1:8787")
        self.assertEqual(
            normalize_origin("https://127.0.0.1"), "https://127.0.0.1")

        calls = []

        def boom(exchange):
            calls.append(exchange)
            raise AssertionError("network")

        account = self._swap_account(boom, setting_origin="http://songs.example")
        self.assertIsNone(account.origin())
        shown = []
        original = QtWidgets.QMessageBox.exec
        QtWidgets.QMessageBox.exec = (
            lambda box: shown.append(box.text())
            or QtWidgets.QMessageBox.StandardButton.Ok)
        try:
            self.app.ui.actionSignIn.trigger()
        finally:
            QtWidgets.QMessageBox.exec = original
        self.assertEqual(calls, [])
        self.assertEqual(shown, ["Sign-in is coming in a later update."])

    def test_transport_refuses_redirects_and_uses_a_15_second_timeout(self):
        import http.server
        import io
        from email.message import Message

        from softchord_auth import (
            HTTP_TIMEOUT_SECONDS, HttpExchange, TransportError, urllib_transport)

        self.assertEqual(HTTP_TIMEOUT_SECONDS, 15)
        seen = {}

        class Opener:
            def __init__(self, code):
                self.code = code

            def open(self, request, timeout=None):
                seen["timeout"] = timeout
                seen["authorization"] = request.get_header("Authorization")
                seen["codes"].append(self.code)
                raise urllib.error.HTTPError(
                    request.full_url, self.code, "Redirect", Message(),
                    io.BytesIO(b""))

        import urllib.error
        seen["codes"] = []
        exchange = HttpExchange(
            "GET", "https://songs.example/api/me",
            {"Authorization": "Bearer secret"}, None)
        for code in (302, 307, 308):
            with self.assertRaises(TransportError):
                urllib_transport(exchange, opener=Opener(code))
        self.assertEqual(seen["timeout"], 15)
        self.assertEqual(seen["authorization"], "Bearer secret")
        self.assertEqual(seen["codes"], [302, 307, 308])

        hits = []
        wanted = {"code": 302}

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_GET(self):
                self._hit()

            def do_POST(self):
                self._hit()

            def _hit(self):
                length = int(self.headers.get("Content-Length", "0") or "0")
                if length:
                    self.rfile.read(length)
                hits.append((self.path, self.headers.get("Authorization")))
                if self.path == "/api/auth/verify":
                    body = b'{"error":"unauthorized"}'
                    self.send_response(401)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                self.send_response(wanted["code"])
                self.send_header("Location", "/stolen")
                self.send_header("Content-Length", "0")
                self.send_header("Connection", "close")
                self.end_headers()

            def log_message(self, fmt, *args):
                return

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_address[1]
            base = "http://127.0.0.1:%d" % port
            for code in (302, 307, 308):
                wanted["code"] = code
                for method, path, body in (
                        ("GET", "/api/me", None),
                        ("POST", "/api/auth/logout", b"{}"),
                        ("POST", "/api/auth/logout-all", b"{}")):
                    hits.clear()
                    redirect = HttpExchange(
                        method, base + path,
                        {"Authorization": "Bearer secret-token",
                         "Content-Type": "application/json"},
                        body)
                    with self.assertRaises(TransportError):
                        urllib_transport(redirect)
                    self.assertEqual([item[0] for item in hits], [path])
                    self.assertEqual(hits[0][1], "Bearer secret-token")
            plain = HttpExchange(
                "POST", base + "/api/auth/verify",
                {"Content-Type": "application/json"}, b"{}")
            result = urllib_transport(plain)
            self.assertEqual(result.status, 401)
            self.assertNotIn("/stolen", [item[0] for item in hits])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_pending_verifier_expires_with_the_server_ttl(self):
        from softchord_auth import (
            VERIFIER_TTL_SECONDS, HttpResult, JsonEnforcingTransport,
            SignInDialog)

        self.assertEqual(VERIFIER_TTL_SECONDS, 15 * 60)
        contract = self._contract()
        verifier = contract["verifier"]["value"]
        issued = 1700000000
        transport = JsonEnforcingTransport([
            HttpResult(200, b'{"ok":true}'),
        ])
        account = self._swap_account(
            transport, origin=contract["publicOrigin"], verifier=verifier)
        account.now = lambda: issued
        dialog = SignInDialog(account, self.app.win)
        dialog.email_edit.setText("singer@example.com")
        self._settle(lambda: dialog.send_button.click())
        self.assertEqual(account.pending_verifier(), verifier)
        account.now = lambda: issued + VERIFIER_TTL_SECONDS - 1
        self.assertEqual(account.pending_verifier(), verifier)
        account.now = lambda: issued + VERIFIER_TTL_SECONDS
        self.assertEqual(account.pending_verifier(), "")
        before = len(transport.calls)
        again = SignInDialog(account, self.app.win)
        again.link_edit.setText(contract["wrongVerifier"])
        self._settle(lambda: again.complete())
        self.assertEqual(len(transport.calls), before)
        self.assertEqual(
            again.status_label.text(),
            "Open this link on the device where you requested it.")

    def test_auth_call_exception_does_not_escape_the_slot(self):
        from softchord_auth import SEND_FAILED, SignInDialog

        def boom(exchange):
            raise RuntimeError("boom")

        account = self._swap_account(
            boom, origin=self._contract()["publicOrigin"])
        dialog = SignInDialog(account, self.app.win)
        dialog.email_edit.setText("singer@example.com")
        self._settle(lambda: dialog.send_button.click())
        self.assertEqual(dialog.status_label.text(), SEND_FAILED)

    def test_sign_out_everywhere_posts_logout_all(self):
        """Logout-all matches the contract: bearer, JSON, and an empty object."""
        from softchord_auth import HttpResult, JsonEnforcingTransport

        contract = self._contract()
        case = next(
            item for item in contract["cases"]
            if item["name"] == "logout-all ends every session for the user")
        step = next(
            item["request"] for item in case["steps"]
            if item["request"]["path"] == "/api/auth/logout-all")
        origin = contract["publicOrigin"]
        session_token = "desktop-session-token"
        inner = JsonEnforcingTransport([
            HttpResult(200, b'{"ok":true}'),
        ])
        gui = threading.get_ident()
        idents = []

        def transport(exchange):
            idents.append(threading.get_ident())
            return inner(exchange)

        account = self._swap_account(transport, origin=origin)
        account.settings.setValue("auth/sessionToken", session_token)
        account.settings.setValue("auth/pendingVerifier", "still-pending")
        account.show_signed_in("singer@example.com")
        self.assertTrue(self.app.ui.actionSignOutEverywhere.isVisible())
        self._settle(
            lambda: self.app.ui.actionSignOutEverywhere.trigger())
        self.assertEqual(len(inner.calls), 1)
        self.assertNotEqual(idents[0], gui)
        sent = inner.calls[0]
        self.assertEqual(sent.method, step["method"])
        self.assertEqual(sent.url, origin + step["path"])
        self.assertEqual(sent.headers["Content-Type"], "application/json")
        self.assertEqual(
            sent.headers["Authorization"], "Bearer %s" % session_token)
        self.assertEqual(sent.body, b"{}")
        self.assertEqual(json.loads(sent.body.decode("utf-8")), step["json"])
        self.assertNotIn("origin", {name.lower() for name in sent.headers})
        self.assertEqual(account.session_token(), "")
        self.assertEqual(account.pending_verifier(), "")
        self.assertFalse(self.app.ui.actionSignOutEverywhere.isVisible())
        self.assertTrue(self.app.ui.actionSignIn.isVisible())

    def _session_token(self, prefix):
        token = (prefix + ("x" * 43))[:43]
        self.assertEqual(len(token), 43)
        return token

    def test_verify_token_must_match_the_token_pattern(self):
        """A verify token is stored and sent only when it matches _TOKEN."""
        from softchord_auth import (
            HttpResult, JsonEnforcingTransport, SignInDialog, _TOKEN)

        contract = self._contract()
        verifier = contract["verifier"]["value"]
        good = self._session_token("goodSession")
        self.assertIsNotNone(_TOKEN.fullmatch(good))
        rejected = [
            "short",
            "a" * 42,
            "a" * 129,
            " " + good,
            good + " ",
            good[:-1] + ".",
        ]
        script = []
        for bad in rejected:
            script.append(HttpResult(
                200, json.dumps({"token": bad, "email": "nope@example.com"}).encode()))
        script.append(HttpResult(
            200, json.dumps({"token": good, "email": "nope@example.com"}).encode()))
        script.append(HttpResult(
            200, json.dumps({"email": "singer@example.com"}).encode()))
        transport = JsonEnforcingTransport(script)
        account = self._swap_account(
            transport, origin=contract["publicOrigin"], verifier=verifier)
        account.settings.setValue("auth/pendingVerifier", verifier)
        account.settings.setValue("auth/pendingVerifierAt", int(time.time()))
        for bad in rejected:
            dialog = SignInDialog(account, self.app.win)
            dialog.link_edit.setText(contract["wrongVerifier"])
            self._settle(lambda: dialog.complete())
            self.assertEqual(account.session_token(), "")
            self.assertEqual(
                dialog.status_label.text(),
                "Open this link on the device where you requested it.")
            self.assertTrue(
                all(not call.url.endswith("/api/me") for call in transport.calls))
        dialog = SignInDialog(account, self.app.win)
        dialog.link_edit.setText(contract["wrongVerifier"])
        self._settle(lambda: dialog.complete())
        self.assertEqual(account.session_token(), good)
        me = transport.calls[-1]
        self.assertTrue(me.url.endswith("/api/me"))
        self.assertEqual(me.headers["Authorization"], "Bearer %s" % good)

    def test_logout_all_error_keeps_the_token(self):
        from softchord_auth import (
            HttpResult, JsonEnforcingTransport, SIGN_OUT_EVERYWHERE_FAILED)

        token = "desktop-session-token"
        transport = JsonEnforcingTransport([
            HttpResult(500, b'{"error":"unavailable"}'),
        ])
        account = self._swap_account(
            transport, origin=self._contract()["publicOrigin"])
        account.settings.setValue("auth/sessionToken", token)
        account.show_signed_in("singer@example.com")
        shown = []
        original = QtWidgets.QMessageBox.exec

        def exec_(box):
            shown.append((box.windowTitle(), box.text()))
            return QtWidgets.QMessageBox.StandardButton.Ok

        QtWidgets.QMessageBox.exec = exec_
        try:
            self._settle(
                lambda: self.app.ui.actionSignOutEverywhere.trigger())
        finally:
            QtWidgets.QMessageBox.exec = original
        self.assertEqual(shown, [
            ("Sign out everywhere", SIGN_OUT_EVERYWHERE_FAILED)])
        self.assertEqual(account.session_token(), token)
        self.assertEqual(
            self.app.ui.signedInEmailLabel.text(), "singer@example.com")
        self.assertTrue(self.app.ui.actionSignOutEverywhere.isVisible())
        self.assertEqual(len(transport.calls), 1)
        self.assertTrue(transport.calls[0].url.endswith("/api/auth/logout-all"))

    def test_logout_all_401_403_network_and_timeout(self):
        """401 clears the local session. 403, network, and timeout keep it."""
        from softchord_auth import HttpResult, SIGN_OUT_EVERYWHERE_FAILED

        origin = self._contract()["publicOrigin"]
        token = "desktop-session-token"

        def run(transport, clears):
            account = self._swap_account(transport, origin=origin)
            account.settings.setValue("auth/sessionToken", token)
            account.show_signed_in("singer@example.com")
            shown = []
            original = QtWidgets.QMessageBox.exec
            QtWidgets.QMessageBox.exec = (
                lambda box: shown.append(box.text())
                or QtWidgets.QMessageBox.StandardButton.Ok)
            try:
                self._settle(
                    lambda: self.app.ui.actionSignOutEverywhere.trigger())
            finally:
                QtWidgets.QMessageBox.exec = original
            if clears:
                self.assertEqual(account.session_token(), "")
                self.assertEqual(shown, [])
                self.assertTrue(self.app.ui.actionSignIn.isVisible())
            else:
                self.assertEqual(account.session_token(), token)
                self.assertEqual(shown, [SIGN_OUT_EVERYWHERE_FAILED])
                self.assertTrue(self.app.ui.actionSignOutEverywhere.isVisible())

        run(lambda exchange: HttpResult(401, b'{"error":"unauthorized"}'), True)
        run(lambda exchange: HttpResult(403, b'{"error":"forbidden"}'), False)

        def network(exchange):
            raise OSError("network down")

        def timed_out(exchange):
            raise TimeoutError("timed out")

        run(network, False)
        run(timed_out, False)

    def test_refresh_401_tells_the_open_dialog(self):
        """A startup 401 must not leave the in-flight dialog button disabled."""
        from softchord_auth import HttpResult, SIGN_IN_FAILED, SignInDialog

        contract = self._contract()
        verifier = contract["verifier"]["value"]
        old = "stale-session-token"
        new = self._session_token("newerSession")
        refresh_started = threading.Event()
        refresh_release = threading.Event()
        dialog_started = threading.Event()
        dialog_release = threading.Event()

        def transport(exchange):
            header = exchange.headers.get("Authorization", "")
            if exchange.method == "GET" and header == "Bearer %s" % old:
                refresh_started.set()
                if not refresh_release.wait(5):
                    raise TimeoutError("refresh was not released")
                return HttpResult(401, b'{"error":"unauthorized"}')
            dialog_started.set()
            if not dialog_release.wait(5):
                raise TimeoutError("dialog request was not released")
            if exchange.url.endswith("/api/auth/verify"):
                return HttpResult(200, json.dumps({
                    "token": new,
                    "email": "nope@example.com",
                }).encode())
            if exchange.method == "GET":
                return HttpResult(200, b'{"email":"singer@example.com"}')
            raise AssertionError(exchange.url)

        account = self._swap_account(transport, origin=contract["publicOrigin"])
        account.settings.setValue("auth/sessionToken", old)
        account.show_signed_in("old@example.com")
        try:
            account.refresh()
            self.assertTrue(refresh_started.wait(2))
            account.settings.setValue("auth/pendingVerifier", verifier)
            account.settings.setValue("auth/pendingVerifierAt", int(time.time()))
            dialog = SignInDialog(account, self.app.win)
            dialog.link_edit.setText(contract["wrongVerifier"])
            dialog.complete()
            self.assertTrue(dialog_started.wait(2))
            self.assertFalse(dialog.complete_button.isEnabled())
            self._settle(lambda: refresh_release.set())
            self.assertEqual(account.session_token(), "")
            self.assertFalse(dialog.complete_button.isEnabled())
            self._settle(lambda: dialog_release.set())
        finally:
            refresh_release.set()
            dialog_release.set()
        self.assertTrue(dialog.complete_button.isEnabled())
        self.assertEqual(dialog.status_label.text(), SIGN_IN_FAILED)
        self.assertEqual(account.session_token(), "")
        self.assertEqual(self.app.ui.signedInEmailLabel.text(), "")
        self.assertNotEqual(dialog.result(), QtWidgets.QDialog.DialogCode.Accepted)

    def test_auth_failure_does_not_print_the_bearer_token(self):
        secret = self._session_token("secretBearer")

        def boom(exchange):
            header = exchange.headers.get("Authorization", "")
            raise RuntimeError("request failed: %s" % header)

        account = self._swap_account(
            boom, origin=self._contract()["publicOrigin"])
        account.settings.setValue("auth/sessionToken", secret)
        account.show_signed_in("singer@example.com")
        captured = io.StringIO()
        with contextlib.redirect_stderr(captured):
            self._settle(lambda: account.refresh())
        text = captured.getvalue()
        self.assertNotIn(secret, text)
        self.assertNotIn("Bearer", text)
        self.assertNotIn("Authorization", text)
        self.assertIn("RuntimeError", text)
        self.assertEqual(account.session_token(), secret)

    def test_sign_in_does_not_stack_dialogs(self):
        from softchord_auth import SignInDialog

        account = self._swap_account(
            lambda exchange: (_ for _ in ()).throw(AssertionError("network")),
            origin=self._contract()["publicOrigin"])
        created = []
        original_init = SignInDialog.__init__
        original_exec = SignInDialog.exec

        def init(dialog, account, parent=None):
            created.append(dialog)
            original_init(dialog, account, parent)

        def exec_(dialog):
            account.sign_in()
            return QtWidgets.QDialog.DialogCode.Rejected

        SignInDialog.__init__ = init
        SignInDialog.exec = exec_
        try:
            account.sign_in()
        finally:
            SignInDialog.__init__ = original_init
            SignInDialog.exec = original_exec
        self.assertEqual(len(created), 1)
        self.assertIsNone(account._dialog)

    def test_reject_and_escape_drop_an_inflight_verify(self):
        """Esc and reject() finish a verify without saving the session."""
        from softchord_auth import HttpResult, SignInDialog

        contract = self._contract()
        verifier = contract["verifier"]["value"]
        saved = self._session_token("savedSession")
        origin = contract["publicOrigin"]

        def run_cancel(cancel):
            started = threading.Event()
            release = threading.Event()
            calls = []

            def transport(exchange):
                calls.append(exchange)
                started.set()
                if not release.wait(5):
                    raise TimeoutError("verify was not released")
                if exchange.url.endswith("/api/auth/verify"):
                    return HttpResult(
                        200, json.dumps({
                            "token": saved,
                            "email": "nope@example.com",
                        }).encode())
                if exchange.url.endswith("/api/me"):
                    return HttpResult(
                        200, b'{"email":"singer@example.com"}')
                raise AssertionError(exchange.url)

            account = self._swap_account(transport, origin=origin)
            account.settings.setValue("auth/pendingVerifier", verifier)
            account.settings.setValue("auth/pendingVerifierAt", int(time.time()))
            dialog = SignInDialog(account, self.app.win)
            dialog.link_edit.setText(contract["wrongVerifier"])
            dialog.show()
            dialog.complete()
            self.assertTrue(started.wait(2))
            began = time.monotonic()
            cancel(dialog)
            self.assertLess(time.monotonic() - began, 0.5)
            self.assertEqual(
                dialog.result(), QtWidgets.QDialog.DialogCode.Rejected)
            self._settle(lambda: release.set())
            self.assertEqual(account.session_token(), "")
            self.assertEqual(self.app.ui.signedInEmailLabel.text(), "")
            self.assertFalse(self.app.ui.actionSignOut.isVisible())
            self.assertTrue(any(
                call.url.endswith("/api/auth/verify") for call in calls))
            dialog.deleteLater()

        run_cancel(lambda dialog: dialog.reject())

        def escape(dialog):
            QtWidgets.QApplication.sendEvent(dialog, QtGui.QKeyEvent(
                QtCore.QEvent.Type.KeyPress,
                Qt.Key.Key_Escape,
                Qt.KeyboardModifier.NoModifier))

        run_cancel(escape)

    def test_stale_me_401_does_not_clear_a_newer_token(self):
        from softchord_auth import HttpResult, SignInDialog

        contract = self._contract()
        verifier = contract["verifier"]["value"]
        old = self._session_token("oldSession")
        new = self._session_token("newSession")
        started = threading.Event()
        release = threading.Event()
        calls = []

        def transport(exchange):
            calls.append(exchange)
            header = exchange.headers.get("Authorization", "")
            if exchange.method == "GET" and header == "Bearer %s" % old:
                started.set()
                if not release.wait(5):
                    raise TimeoutError("stale /api/me was not released")
                return HttpResult(401, b'{"error":"unauthorized"}')
            if exchange.url.endswith("/api/auth/verify"):
                return HttpResult(
                    200, json.dumps({"token": new, "email": "nope@example.com"}).encode())
            if exchange.method == "GET" and header == "Bearer %s" % new:
                return HttpResult(200, b'{"email":"singer@example.com"}')
            raise AssertionError(exchange.url)

        account = self._swap_account(transport, origin=contract["publicOrigin"])
        account.settings.setValue("auth/sessionToken", old)
        account.show_signed_in("old@example.com")
        account.refresh()
        self.assertTrue(started.wait(2))
        account.settings.setValue("auth/pendingVerifier", verifier)
        account.settings.setValue(
            "auth/pendingVerifierAt", int(time.time()))
        dialog = SignInDialog(account, self.app.win)
        dialog.link_edit.setText(contract["wrongVerifier"])
        self._settle(lambda: dialog.complete())
        self.assertEqual(account.session_token(), new)
        self.assertEqual(
            self.app.ui.signedInEmailLabel.text(), "singer@example.com")
        self._settle(lambda: release.set())
        self.assertEqual(account.session_token(), new)
        self.assertEqual(
            self.app.ui.signedInEmailLabel.text(), "singer@example.com")
        self.assertTrue(self.app.ui.actionSignOut.isVisible())
        self.assertTrue(any(
            call.headers.get("Authorization") == "Bearer %s" % old
            for call in calls))

    def test_stale_me_200_after_sign_out_does_not_show_the_email(self):
        from softchord_auth import HttpResult

        token = self._session_token("stillSession")
        started = threading.Event()
        release = threading.Event()

        def transport(exchange):
            if exchange.method == "GET":
                started.set()
                if not release.wait(5):
                    raise TimeoutError("stale /api/me was not released")
                return HttpResult(200, b'{"email":"late@example.com"}')
            if exchange.url.endswith("/api/auth/logout"):
                return HttpResult(200, b'{"ok":true}')
            raise AssertionError(exchange.url)

        account = self._swap_account(
            transport, origin=self._contract()["publicOrigin"])
        account.settings.setValue("auth/sessionToken", token)
        account.show_signed_in("singer@example.com")
        account.refresh()
        self.assertTrue(started.wait(2))
        self._settle(lambda: self.app.ui.actionSignOut.trigger())
        self.assertEqual(account.session_token(), "")
        self.assertEqual(self.app.ui.signedInEmailLabel.text(), "")
        self._settle(lambda: release.set())
        self.assertEqual(account.session_token(), "")
        self.assertEqual(self.app.ui.signedInEmailLabel.text(), "")
        self.assertFalse(self.app.ui.actionSignOut.isVisible())
        self.assertTrue(self.app.ui.actionSignIn.isVisible())

    def test_quit_does_not_wait_for_pending_requests(self):
        from softchord_auth import HttpResult, release_thread_pool

        token = self._session_token("quitSession")
        started = threading.Event()
        release = threading.Event()
        pool_started = threading.Event()
        pool_release = threading.Event()

        def transport(exchange):
            started.set()
            if not release.wait(5):
                raise TimeoutError("quit request was not released")
            return HttpResult(200, b'{"email":"late@example.com"}')

        class Blocker(QtCore.QRunnable):
            def run(self):
                pool_started.set()
                pool_release.wait(5)

        account = self._swap_account(
            transport, origin=self._contract()["publicOrigin"])
        self.app.aboutToQuit.disconnect(account.abandon_pending)
        self.app.aboutToQuit.connect(account.abandon_pending)
        account.settings.setValue("auth/sessionToken", token)
        account.show_signed_in(None)
        QtCore.QThreadPool.globalInstance().start(Blocker())
        try:
            self.assertTrue(pool_started.wait(2))
            began = time.monotonic()
            release_thread_pool()
            self.assertLess(time.monotonic() - began, 0.5)
            account.refresh()
            self.assertTrue(started.wait(2))
            began = time.monotonic()
            account.abandon_pending()
            self.assertLess(time.monotonic() - began, 0.5)
            release.set()
            QtWidgets.QApplication.processEvents()
        finally:
            release.set()
            pool_release.set()
        self.assertEqual(account.session_token(), token)
        self.assertEqual(self.app.ui.signedInEmailLabel.text(), "")
        self.assertFalse(self.app.ui.actionSignOut.isVisible())

    def test_quit_does_not_let_a_worker_emit_during_teardown(self):
        """A request still running at quit must not segfault Qt teardown."""
        script = """
import os, sys, time, threading
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.pop("SOFTCHORD_API_ORIGIN", None)
sys.path.insert(0, %r)
from PyQt6 import QtCore
import softchord
from softchord_auth import HttpResult

app = softchord.App([])
started = threading.Event()

def transport(exchange):
    started.set()
    time.sleep(0.4)
    return HttpResult(200, b'{"email":"late@example.com"}')

account = app.account
account.transport = transport
account.env = {"SOFTCHORD_API_ORIGIN": "https://songs.example"}
account.settings.setValue("auth/sessionToken", "quit-token")

def kick():
    account.refresh()
    QtCore.QTimer.singleShot(50, app.quit)

QtCore.QTimer.singleShot(0, kick)
app.exec()
time.sleep(0.6)
print("teardown-ok")
""" % _HERE
        proc = subprocess.run(
            [sys.executable, "-c", script],
            cwd=_HERE,
            capture_output=True,
            timeout=15)
        self.assertEqual(
            proc.returncode, 0,
            proc.stderr.decode("utf-8", "replace")[-800:])
        self.assertIn(b"teardown-ok", proc.stdout)


if __name__ == "__main__":
    # Qt can crash while Python shuts down after the tests (seen on macOS
    # and Linux), so exit with the test result before that can happen.
    program = unittest.main(verbosity=2, exit=False)
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0 if program.result.wasSuccessful() else 1)
