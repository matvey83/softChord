// Edit text in the real viewer page, in headless Chrome: the textarea over the
// sheet, chords that follow the text, Undo/Redo, Save and Discard. Skipped when
// Chrome is not installed.
//
// Alignment is measured from pixels. The page is drawn twice, once with only the
// textarea's letters visible and once with only the sheet's letters, and the ink
// centre of every letter is compared. That is what a reader sees, so it catches
// a textarea that is a pixel off its sheet. Safari and Firefox are not tested.

const test = require("node:test");
const assert = require("node:assert/strict");
const helper = require("./browser_helper");
const SongTextEdit = require("../softchord_text_edit");

const skip = helper.skipUnlessBrowser();

const HELLO = {
  title: "Hello",
  text: "Hello world\nSecond line\nThird",
  chords: [[0, "C"], [6, "Am"], [12, "G"], [24, "F"]],
};
const RUSSIAN = {
  title: "Звуки неба",
  text: "Звуки неба, любовь моя\nи я иду домой",
  chords: [[0, "C"], [6, "Am"], [14, "G"], [23, "Em"]],
};

const {
  inEditor, click, startEditing, editorValue, select, disabled, chordsShown, sheetText,
  inkOffsets, assertAligned, setZoom,
} = require("./edit_helpers");


test("the Edit text button opens the editor over the sheet and locks what must wait", { skip: skip }, function () {
  return inEditor([HELLO], async function (page) {
    assert.equal(await page.eval("document.getElementById('edit-text').title"), "Edit Text…");
    assert.equal(await page.eval("document.getElementById('edit-text').getAttribute('aria-label')"), "Edit Text…");
    assert.equal(await page.eval("document.getElementById('sheet-editor').hidden"), true);
    assert.equal(await page.eval("document.getElementById('edit-actions').hidden"), true);
    await startEditing(page);
    assert.equal(await page.eval("document.getElementById('sheet-editor').hidden"), false);
    assert.equal(await editorValue(page), HELLO.text);
    assert.equal(await page.eval("document.getElementById('edit-actions').hidden"), false);
    for (var id of ["print", "copy-text", "copy-chords", "copy-image", "transpose-down", "transpose-up",
      "transpose-reset", "edit-text"]) {
      assert.equal(await disabled(page, id), true, id + " waits until Save or Discard");
    }
    // Zoom still works: the textarea is sized in em from the same variable as the sheet.
    for (id of ["zoom-in", "zoom-out"]) {
      assert.equal(await disabled(page, id), false, id + " stays on");
    }
    assert.equal(await page.eval("document.getElementById('edit-save').textContent"), "Save");
    assert.equal(await page.eval("document.getElementById('edit-discard').textContent"), "Discard");
    // Discard comes first, then Save, as in the desktop and iPhone apps.
    assert.equal(await page.eval("document.getElementById('edit-discard').nextElementSibling.id"), "edit-save");
    // Spelling help, and a visible caret.
    assert.equal(await page.eval("document.getElementById('sheet-editor').spellcheck"), false);
    assert.equal(await page.eval("document.getElementById('sheet-editor').wrap"), "off");
    assert.notEqual(await page.eval("getComputedStyle(document.getElementById('sheet-editor')).caretColor"),
      "rgba(0, 0, 0, 0)");
    // The textarea covers the sheet exactly, and its letters are see-through.
    assert.equal(await page.eval("getComputedStyle(document.getElementById('sheet-editor')).fontFamily === " +
      "getComputedStyle(document.getElementById('sheet')).fontFamily"), true);
    assert.equal(await page.eval("getComputedStyle(document.getElementById('sheet-editor')).fontSize === " +
      "getComputedStyle(document.getElementById('sheet')).fontSize"), true);
    await assertAligned(page, "just opened");
  });
});

for (var zoom of [100, 150]) {
  (function (percent) {
    test("typing moves the chords with their letters and the textarea stays on the sheet at " + percent + "%",
      { skip: skip }, function () {
        return inEditor([HELLO], async function (page) {
          await setZoom(page, percent);
          await startEditing(page);
          await assertAligned(page, "opened");

          // Type at the start: every chord moves one letter to the right.
          await page.insertText("X");
          assert.equal(await editorValue(page), "XHello world\nSecond line\nThird");
          assert.deepEqual(await chordsShown(page),
            [[1, "H", "C"], [7, "w", "Am"], [13, "S", "G"], [25, "T", "F"]]);
          assert.equal(await sheetText(page), "XHello world\nSecond line\nThird");
          await assertAligned(page, "typed at the start");

          // Replace a selection: the chord on a letter that went is dropped.
          await select(page, 1, 4);
          await page.insertText("J");
          assert.equal(await editorValue(page), "XJlo world\nSecond line\nThird");
          assert.deepEqual(await chordsShown(page),
            [[5, "w", "Am"], [11, "S", "G"], [23, "T", "F"]]);
          await assertAligned(page, "replaced a selection");

          // Paste several lines in the middle of a line.
          await select(page, 4, 4);
          await page.insertText("1\n22\n333 ");
          assert.equal(await editorValue(page), "XJlo1\n22\n333  world\nSecond line\nThird");
          assert.equal((await chordsShown(page)).length, 3);
          assert.deepEqual((await chordsShown(page)).map(function (c) { return c[1] + c[2]; }),
            ["wAm", "SG", "TF"]);
          await assertAligned(page, "pasted lines");

          // Enter at the start, in the middle and at the end of a line.
          await select(page, 0, 0);
          await page.key("Enter");
          assert.equal((await editorValue(page)).split("\n")[0], "");
          await assertAligned(page, "Enter at the start");
          var value = await editorValue(page);
          await select(page, value.indexOf("world"), value.indexOf("world"));
          await page.key("Enter");
          await assertAligned(page, "Enter in the middle");
          value = await editorValue(page);
          await select(page, value.indexOf("Second line") + 11, value.indexOf("Second line") + 11);
          await page.key("Enter");
          await assertAligned(page, "Enter at the end");
          assert.deepEqual((await chordsShown(page)).map(function (c) { return c[1] + c[2]; }),
            ["wAm", "SG", "TF"], "Enter moves chords with their letters");

          // Backspace joining two lines.
          value = await editorValue(page);
          var at = value.indexOf("world");
          await select(page, at, at);
          await page.key("Backspace");
          await assertAligned(page, "Backspace joined two lines");
          assert.deepEqual((await chordsShown(page)).map(function (c) { return c[1] + c[2]; }),
            ["wAm", "SG", "TF"]);
        });
      });
  })(zoom);
}

test("a Cyrillic song keeps its chords on its letters while it is edited", { skip: skip }, function () {
  return inEditor([RUSSIAN], async function (page) {
    await startEditing(page);
    await assertAligned(page, "opened");
    var before = (await chordsShown(page)).map(function (c) { return c[1] + c[2]; });
    await select(page, 0, 0);
    await page.insertText("Да, ");
    assert.deepEqual((await chordsShown(page)).map(function (c) { return c[1] + c[2]; }), before);
    await assertAligned(page, "typed Russian at the start");
    await select(page, 10, 10);
    await page.key("Enter");
    await assertAligned(page, "Enter in a Russian line");
    await select(page, 10, 11);
    await page.key("Backspace");
    await assertAligned(page, "Backspace in a Russian line");
    await setZoom(page, 150);
    await assertAligned(page, "Russian at 150%");
  });
});

test("Undo and Redo bring back the chords that were dropped with deleted letters", { skip: skip }, function () {
  return inEditor([HELLO], async function (page) {
    await startEditing(page);
    var chords = await chordsShown(page);
    assert.equal(chords.length, 4);
    // Delete "Hello w" (the chord on H and the one on w go with it).
    await select(page, 0, 7);
    await page.key("Delete");
    assert.equal(await editorValue(page), "orld\nSecond line\nThird");
    assert.deepEqual((await chordsShown(page)).map(function (c) { return c[1] + c[2]; }), ["SG", "TF"]);
    await page.undo();
    assert.equal(await editorValue(page), HELLO.text);
    assert.deepEqual(await chordsShown(page), chords, "both dropped chords are back");
    await assertAligned(page, "after Undo");
    await page.redo();
    assert.equal(await editorValue(page), "orld\nSecond line\nThird");
    assert.deepEqual((await chordsShown(page)).map(function (c) { return c[1] + c[2]; }), ["SG", "TF"]);
    await assertAligned(page, "after Redo");
    await page.undo();
    assert.deepEqual(await chordsShown(page), chords);

    // Typing, then deleting, then Undo twice.
    await select(page, 3, 3);
    await page.insertText("123");
    await page.key("Backspace");
    await page.undo();
    await page.undo();
    assert.equal(await editorValue(page), HELLO.text);
    assert.deepEqual(await chordsShown(page), chords);
  });
});

test("Save keeps the edited text and chords, shows the note, and later reads use them", { skip: skip }, function () {
  return inEditor([HELLO], async function (page) {
    await page.eval("window.__copied = []; Object.defineProperty(navigator, 'clipboard', " +
      "{ value: { writeText: function (t) { window.__copied.push(t); return Promise.resolve(); } } })");
    assert.equal(await page.eval("document.getElementById('persist-note').hidden"), true);
    await startEditing(page);
    await select(page, 5, 5);
    await page.insertText(" there");
    await click(page, "edit-save");
    assert.equal(await page.eval("document.getElementById('sheet-editor').hidden"), true);
    assert.equal(await page.eval("document.getElementById('edit-actions').hidden"), true);
    assert.equal(await sheetText(page), "Hello there world\nSecond line\nThird");
    assert.deepEqual((await chordsShown(page)).map(function (c) { return c[1] + c[2]; }),
      ["HC", "wAm", "SG", "TF"]);
    assert.equal(await page.eval("document.getElementById('persist-note').hidden"), false);
    assert.equal(await page.eval("document.getElementById('persist-note').textContent"), "Changes do not persist");
    // The buttons that waited are back (Reset transpose has nothing to reset).
    for (var id of ["print", "copy-text", "copy-chords", "copy-image", "transpose-down", "transpose-up",
      "edit-text"]) {
      assert.equal(await disabled(page, id), false, id);
    }
    assert.equal(await disabled(page, "transpose-reset"), true);
    await click(page, "copy-chords");
    await page.waitFor("window.__copied.length === 1", "the copy");
    var copied = await page.eval("window.__copied[0]");
    assert.ok(copied.includes("Hello there world"), copied);
    assert.ok(copied.split("\r\n")[0].startsWith("C"));
    // Edit again: the editor opens on the saved text.
    await startEditing(page);
    assert.equal(await editorValue(page), "Hello there world\nSecond line\nThird");
    await click(page, "edit-discard");
    // Saved text is still the shown text, and the note too.
    assert.equal(await sheetText(page), "Hello there world\nSecond line\nThird");
    assert.equal(await page.eval("document.getElementById('persist-note').hidden"), false);
  });
});

test("Save with nothing changed shows no note, and Discard throws the edit away", { skip: skip }, function () {
  return inEditor([HELLO], async function (page) {
    var original = await sheetText(page);
    await startEditing(page);
    await click(page, "edit-save");
    assert.equal(await page.eval("document.getElementById('persist-note').hidden"), true);
    assert.equal(await sheetText(page), original);

    await startEditing(page);
    await select(page, 0, 0);
    await page.insertText("ZZZ");
    assert.equal((await sheetText(page)).startsWith("ZZZHello"), true);
    await click(page, "edit-discard");
    assert.equal(await sheetText(page), original);
    assert.equal(await page.eval("document.getElementById('persist-note').hidden"), true);
    assert.equal(await page.eval("document.getElementById('sheet-editor').hidden"), true);
    await startEditing(page);
    assert.equal(await editorValue(page), HELLO.text, "the discarded text is gone");
  });
});

test("Escape does not leave the song while editing, and Back and other songs ask before they drop an edit", { skip: skip }, function () {
  return inEditor([HELLO, RUSSIAN], async function (page) {
    var asking = "document.getElementById('leave-confirm').open";
    await startEditing(page);
    await page.insertText("Q");
    await page.pressKey("Escape");
    assert.equal(await page.eval("location.hash"), "#/song/1");
    assert.equal(await page.eval("document.getElementById('sheet-editor').hidden"), false);
    assert.equal((await editorValue(page)).startsWith("Q"), true, "the edit is still there");
    // Back asks. Keep editing leaves everything as it was.
    await click(page, "back");
    assert.equal(await page.eval(asking), true, "Back asks before it drops an edit");
    assert.equal(await page.eval("document.getElementById('leave-confirm-title').textContent"), "Discard changes?");
    assert.equal(await page.eval("document.activeElement.id"), "leave-confirm-keep", "Keep editing is the default");
    await click(page, "leave-confirm-keep");
    assert.equal(await page.eval(asking), false);
    assert.equal(await page.eval("location.hash"), "#/song/1");
    assert.equal((await editorValue(page)).startsWith("Q"), true);
    // Escape in the dialog is Keep editing too.
    await click(page, "back");
    await page.pressKey("Escape");
    assert.equal(await page.eval(asking), false);
    assert.equal(await page.eval("document.getElementById('song-view').hidden"), false);
    // Discard goes back to the list and the edit is gone.
    await click(page, "back");
    await click(page, "leave-confirm-discard");
    await page.waitFor("document.getElementById('song-view').hidden", "the list");
    await page.eval("location.hash = '#/song/1'");
    await page.waitFor("!document.getElementById('song-view').hidden", "the song");
    assert.equal(await page.eval("document.getElementById('sheet-editor').hidden"), true);
    assert.equal(await sheetText(page), HELLO.text);
    // A saved edit is lost without asking (it was kept on purpose, with its note), and
    // so is it when another song opens.
    await startEditing(page);
    await page.insertText("Q");
    await click(page, "edit-save");
    assert.equal(await page.eval("document.getElementById('persist-note').hidden"), false);
    await page.eval("location.hash = '#/song/2'");
    await page.waitFor("document.getElementById('song-title').textContent === 'Звуки неба'", "song 2");
    assert.equal(await page.eval(asking), false);
    assert.equal(await page.eval("document.getElementById('persist-note').hidden"), true);
    // Another song with an edit in the draft: the address goes back and asks.
    await startEditing(page);
    await page.insertText("W");
    await page.eval("location.hash = '#/song/1'");
    await page.waitFor(asking, "the question");
    assert.equal(await page.eval("location.hash"), "#/song/2", "the address is put back while it asks");
    assert.equal(await page.eval("document.getElementById('song-title').textContent"), "Звуки неба");
    await click(page, "leave-confirm-keep");
    assert.equal((await editorValue(page)).startsWith("W"), true);
    await page.eval("location.hash = '#/song/1'");
    await page.waitFor(asking, "the question again");
    await click(page, "leave-confirm-discard");
    await page.waitFor("document.getElementById('song-title').textContent === 'Hello'", "song 1");
    assert.equal(await page.eval("location.hash"), "#/song/1");
    assert.equal(await page.eval("document.getElementById('sheet-editor').hidden"), true);
    assert.equal(await sheetText(page), HELLO.text);
    assert.equal(await page.eval("document.getElementById('persist-note').hidden"), true);
    // The same song's address in another form is not leaving.
    await startEditing(page);
    await page.insertText("E");
    await page.eval("location.hash = '#/song/01'");
    await new Promise(function (r) { setTimeout(r, 200); });
    assert.equal(await page.eval(asking), false);
    assert.equal((await editorValue(page)).startsWith("E"), true);
    await click(page, "edit-discard");
    // Escape with no edit still leaves the song, as before.
    await page.pressKey("Escape");
    await page.waitFor("document.getElementById('song-view').hidden", "leaving the song");
  });
});

test("Back and other songs do not ask when the edit changed nothing", { skip: skip }, function () {
  return inEditor([HELLO, RUSSIAN], async function (page) {
    await startEditing(page);
    await click(page, "back");
    assert.equal(await page.eval("document.getElementById('leave-confirm').open"), false);
    await page.waitFor("document.getElementById('song-view').hidden", "the list");
    await page.eval("location.hash = '#/song/1'");
    await page.waitFor("!document.getElementById('song-view').hidden", "the song");
    // A letter typed and taken away again is the same text: nothing to lose.
    await startEditing(page);
    await page.insertText("Q");
    await page.key("Backspace");
    await page.eval("location.hash = '#/song/2'");
    await page.waitFor("document.getElementById('song-title').textContent === 'Звуки неба'", "song 2");
    assert.equal(await page.eval("document.getElementById('leave-confirm').open"), false);
    // A chord edit counts: the text is the same but a chord moved.
    await startEditing(page);
    await page.eval("document.getElementById('sheet-editor').setSelectionRange(0, 0)");
    await page.insertText(" ");
    await click(page, "back");
    assert.equal(await page.eval("document.getElementById('leave-confirm').open"), true);
    await click(page, "leave-confirm-keep");
  });
});

test("a transposed song is edited in its own key and saved without changing the key", { skip: skip }, function () {
  return inEditor([HELLO], async function (page) {
    await click(page, "transpose-up");
    await click(page, "transpose-up");
    var shownChords = (await chordsShown(page)).map(function (c) { return c[2]; });
    assert.deepEqual(shownChords, ["D", "Bm", "A", "G"]);
    await startEditing(page);
    assert.deepEqual((await chordsShown(page)).map(function (c) { return c[2]; }), shownChords,
      "the editor shows the chords as they were shown");
    await page.insertText("Oh ");
    assert.deepEqual((await chordsShown(page)).map(function (c) { return c[2]; }), shownChords);
    await click(page, "edit-save");
    assert.deepEqual((await chordsShown(page)).map(function (c) { return c[2]; }), shownChords);
    assert.equal(await disabled(page, "transpose-reset"), false);
    // Reset goes back to the key the song had when it was opened, edit kept.
    await click(page, "transpose-reset");
    assert.deepEqual((await chordsShown(page)).map(function (c) { return c[2]; }), ["C", "Am", "G", "F"]);
    assert.equal((await sheetText(page)).startsWith("Oh Hello"), true);
  });
});

test("chords on a line break or past the end do not break editing", { skip: skip }, function () {
  var odd = { title: "Odd", text: "ab\ncd", chords: [[0, "C"], [2, "Am"], [5, "G"], [99, "F"], [3, "Em"]] };
  return inEditor([odd], async function (page) {
    assert.deepEqual((await chordsShown(page)).map(function (c) { return c[2]; }), ["C", "Em"]);
    await startEditing(page);
    assert.deepEqual((await chordsShown(page)).map(function (c) { return c[2]; }), ["C", "Em"]);
    await select(page, 5, 5);
    await page.insertText("e");
    await select(page, 0, 0);
    await page.insertText("x");
    await page.key("Enter");
    await assertAligned(page, "after typing with odd chords");
    await click(page, "edit-save");
    assert.equal(await sheetText(page), "x\nabcd".replace("abcd", "ab") + "\ncde");
  });
});

test("CRLF and CR in the song become LF, with the chords on the same letters", { skip: skip }, function () {
  var windows = { title: "Win", text: "ab\r\ncd\r\nef\rgh", chords: [[0, "C"], [4, "Am"], [8, "G"], [11, "F"]] };
  return inEditor([windows], async function (page) {
    await startEditing(page);
    assert.equal(await editorValue(page), "ab\ncd\nef\ngh");
    assert.deepEqual(await chordsShown(page), [[0, "a", "C"], [3, "c", "Am"], [6, "e", "G"], [9, "g", "F"]]);
    await select(page, 0, 0);
    await page.insertText("p\r\nq\rr");
    assert.equal((await editorValue(page)).includes("\r"), false, "a paste is normalised too");
    assert.equal(await editorValue(page), "p\nq\nrab\ncd\nef\ngh");
    assert.equal((await chordsShown(page)).length, 4);
    await assertAligned(page, "pasted CRLF text");
  });
});

test("tabs and spaces stay as typed", { skip: skip }, function () {
  return inEditor([HELLO], async function (page) {
    await startEditing(page);
    await select(page, 0, 0);
    await page.insertText("  ");
    await select(page, 2, 2);
    await page.insertText("\t");
    assert.equal((await editorValue(page)).slice(0, 4), "  \tH");
    await select(page, 9, 9);
    await page.insertText("   ");
    assert.equal(await sheetText(page), "  \tHello    world\nSecond line\nThird");
  });
});

test("a long line scrolls sideways, the textarea grows with it and the caret stays in view", { skip: skip }, function () {
  var long = { title: "Long", text: "word ".repeat(60).trim() + "\nshort", chords: [[0, "C"], [100, "G"]] };
  return inEditor([long], async function (page) {
    // The song opens shrunk to fit the window; Reset zoom shows it at the normal size.
    await page.eval("document.getElementById('zoom-reset').click()");
    await startEditing(page);
    var sizes = await page.eval("(function () { var e = document.getElementById('sheet-editor');" +
      "var s = document.getElementById('sheet-scroll'); return { editorW: e.offsetWidth, editorScrollW: e.scrollWidth," +
      "editorH: e.offsetHeight, editorScrollH: e.scrollHeight, boxW: s.clientWidth, boxScrollW: s.scrollWidth }; })()");
    assert.ok(sizes.boxScrollW > sizes.boxW, "the song area scrolls sideways");
    assert.ok(sizes.editorScrollW <= sizes.editorW, "the textarea holds its whole line");
    assert.ok(sizes.editorScrollH <= sizes.editorH, "the textarea holds all its lines");
    await assertAligned(page, "a long line");
    // Type at the end of the long line: the song area scrolls to show the caret.
    var end = (await editorValue(page)).indexOf("\n");
    await select(page, end, end);
    await page.insertText(" and some more words at the very end of the line");
    var visible = await page.eval("document.getElementById('sheet-scroll').scrollLeft");
    assert.ok(visible > 0, "the song area followed the caret (scrollLeft " + visible + ")");
    assert.equal(await page.eval("document.getElementById('sheet-editor').scrollLeft"), 0);
    // The sheet draws every letter as its own box and the textarea draws a run, so
    // they part by about 0.003px per letter (1px after 300 letters). Allow 2px here.
    await assertAligned(page, "after typing at the end of a long line", 2);
  });
});

test("zoom while editing keeps the textarea on the sheet at every step", { skip: skip }, function () {
  return inEditor([RUSSIAN], async function (page) {
    await startEditing(page);
    for (var percent of [50, 80, 110, 150, 200, 300]) {
      await setZoom(page, percent);
      await assertAligned(page, "zoom " + percent + "%");
    }
    await click(page, "zoom-reset");
    await page.insertText("z");
    await assertAligned(page, "zoom 100% after typing");
  });
});

test("an IME composition is shown while it is typed and the chords move when it ends", { skip: skip }, function () {
  return inEditor([HELLO], async function (page) {
    await startEditing(page);
    await select(page, 0, 0);
    await page.send("Input.imeSetComposition", { text: "に", selectionStart: 1, selectionEnd: 1 });
    // The letters being composed are in the sheet already.
    assert.equal((await sheetText(page)).startsWith("にHello"), true);
    await page.send("Input.imeSetComposition", { text: "にほ", selectionStart: 2, selectionEnd: 2 });
    assert.equal((await sheetText(page)).startsWith("にほHello"), true);
    await page.insertText("にほ");
    assert.equal(await editorValue(page), "にほHello world\nSecond line\nThird");
    assert.deepEqual((await chordsShown(page)).map(function (c) { return c[1] + c[2]; }),
      ["HC", "wAm", "SG", "TF"]);
    await assertAligned(page, "after composing");
    await page.undo();
    assert.equal(await editorValue(page), HELLO.text);
    assert.deepEqual((await chordsShown(page)).map(function (c) { return c[1] + c[2]; }),
      ["HC", "wAm", "SG", "TF"].map(function (t) { return t; }));
  });
});

// Types one letter at a time at the end of the song, so every letter is an Undo step of its own.
async function typeLetters(page, count) {
  var length = (await editorValue(page)).length;
  for (var i = 0; i < count; i++) {
    await select(page, length + i, length + i);
    await page.insertText("a");
  }
  return length;
}

test("Undo within the last snapshots brings chords back, and past them it goes on without them", { skip: skip }, function () {
  return inEditor([HELLO], async function (page) {
    await startEditing(page);
    var chords = await chordsShown(page);
    var tags = function (list) { return list.map(function (c) { return c[1] + c[2]; }); };
    // Delete "Hello w" (the chords on H and w go with it), then type a few letters.
    await select(page, 0, 7);
    await page.key("Delete");
    var length = await typeLetters(page, 20);
    for (var i = 0; i < 20; i++) {
      await page.undo();
    }
    await page.undo();
    assert.equal(await editorValue(page), HELLO.text, "all the way back");
    assert.deepEqual(await chordsShown(page), chords, "within the limit the dropped chords are back");

    // Redo it all, then type well past the number of snapshots that are kept.
    var extra = SongTextEdit.HISTORY_LIMIT + 20;
    await select(page, 0, 7);
    await page.key("Delete");
    await typeLetters(page, extra);
    var typed = await editorValue(page);
    assert.equal(typed.length, length + extra);
    var steps = 0;
    while ((await editorValue(page)) !== HELLO.text && steps < extra + 5) {
      await page.undo();
      steps++;
    }
    assert.equal(await editorValue(page), HELLO.text, "the text goes all the way back after " + steps + " Undos");
    // The snapshot of the first deletion was let go, so the chords on H and w are not
    // back, but the others are where they were and everything still lines up.
    assert.deepEqual(tags(await chordsShown(page)), ["SG", "TF"]);
    await assertAligned(page, "after Undo past the limit");
    // Redo keeps working too (here without snapshots), and nothing threw.
    await page.redo();
    assert.equal((await editorValue(page)).length < HELLO.text.length + 1, true);
    await assertAligned(page, "after Redo past the limit");
  });
});

test("painting only the lines that changed gives the same sheet as painting all of them", { skip: skip }, async function () {
  var song = {
    title: "Many lines", chords: [],
    text: Array.from({ length: 40 }, function (_, i) { return "Line " + i + " of the song"; }).join("\n"),
  };
  var at = 0;
  song.text.split("\n").forEach(function (line, i) {
    if (i % 3 === 0) {
      song.chords.push([at + 1, "C"], [at + 6, "Am"]);
    }
    at += line.length + 1;
  });
  var edited;
  await inEditor([song], async function (page) {
    await startEditing(page);
    // A letter in a middle line, a new line near the top, two lines removed in the
    // middle, the last line changed, then Undo, Undo and Redo.
    await select(page, 100, 100);
    await page.insertText("QQ");
    await select(page, 3, 3);
    await page.key("Enter");
    var value = await editorValue(page);
    var from = value.indexOf("Line 20");
    var to = value.indexOf("Line 22");
    await select(page, from, to);
    await page.key("Delete");
    await select(page, (await editorValue(page)).length, (await editorValue(page)).length);
    await page.insertText("!");
    await page.undo();
    await page.undo();
    await page.redo();
    await assertAligned(page, "after the edits");
    var shown = await page.eval("({ html: document.getElementById('sheet').innerHTML, text: document.getElementById('sheet-editor').value })");
    edited = { text: shown.text, html: shown.html, chords: await chordsShown(page) };
  });
  // The same song, as it is after those edits, painted from scratch.
  var fresh = {
    title: "Many lines", text: edited.text,
    chords: edited.chords.map(function (c) { return [c[0], c[2]]; }),
  };
  var page = await helper.openViewer([fresh]);
  try {
    await page.eval("location.hash = '#/song/1'");
    await page.waitFor("!document.getElementById('song-view').hidden", "the song page");
    await click(page, "edit-text");
    await page.waitFor("document.activeElement.id === 'sheet-editor'", "the editor");
    var again = await page.eval("document.getElementById('sheet').innerHTML");
    assert.equal(again, edited.html);
  } finally {
    await page.close();
  }
});
