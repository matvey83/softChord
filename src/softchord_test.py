"""
Execute as:

python3 softchord_test.py
"""
import unittest
import os
import shutil
import sys
import tempfile

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

    def setUp(self):
        self.app = self.__class__.app
        self.prev_rows = self.app.songs_model.rowCount()

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
            [action.text() for action in ui.menuAccount.actions()],
            ["Sign In...", "Account Settings..."])
        self.assertTrue(ui.actionSignIn.isEnabled())
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
            ("Sign-in isn't available yet",
             "softChord accounts are coming in a later update."),
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
        self.assertEqual([(title, text) for title, text, _buttons, _count
                          in shown], expected)
        self.assertTrue(all(buttons == ok and count == 1
                            for _title, _text, buttons, count in shown))
        self.assertEqual(self.app.current_songbook_filename, songbook)

    def test_account_actions_use_no_network_module(self):
        """The menu stubs import no network module and open no connection."""
        import ast
        import inspect
        import socket
        import urllib.request

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

        calls = []

        def refuse(kind):
            def wrapped(*args, **kwargs):
                calls.append(kind)
                raise AssertionError(kind)

            return wrapped

        real_socket = socket.socket
        real_create = socket.create_connection
        real_urlopen = urllib.request.urlopen
        socket.socket = refuse("socket")
        socket.create_connection = refuse("create_connection")
        urllib.request.urlopen = refuse("urlopen")
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

    def test_open_asks_before_switching_and_cancel_aborts(self):
        """A dirty draft is asked about before Open. Cancel leaves it."""
        app = self.app
        songbook = app.current_songbook_filename
        app.createNewSong()
        song_id = app.current_song.id
        self.addCleanup(self._delete_song, song_id)
        app.currentSongTitleEdited("Not yet")
        self.assertTrue(app.editChanged())

        asked = []
        opened = []

        def cancel():
            asked.append("cancel")
            return "cancel"

        def file_dialog(*args, **kwargs):
            opened.append(args)
            return ("", "")

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
            self.assertEqual(app.current_songbook_filename, songbook)
            self.assertEqual(app.current_song.id, song_id)
            self.assertEqual(app.current_song.title, "")
            self.assertFalse(app.editChanged())
        finally:
            QtWidgets.QFileDialog.getOpenFileName = original_dialog
            app._askSaveChanges = original_ask


if __name__ == "__main__":
    # Qt can crash while Python shuts down after the tests (seen on macOS
    # and Linux), so exit with the test result before that can happen.
    program = unittest.main(verbosity=2, exit=False)
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0 if program.result.wasSuccessful() else 1)
