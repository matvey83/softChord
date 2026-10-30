// Layout of the Edit text mode in the real viewer page (headless Chrome): tabs,
// combining characters and emoji, the toolbar on phones, the scroll position when
// the editor opens, focus, and what is announced. Skipped when Chrome is not
// installed. The shared helpers measure the textarea against the sheet in pixels.

const test = require("node:test");
const assert = require("node:assert/strict");
const helper = require("./browser_helper");
const {
  inEditor, click, startEditing, assertAligned, setZoom, sheetText, editorValue, chordsShown,
} = require("./edit_helpers");

const skip = helper.skipUnlessBrowser();

const HELLO_LAYOUT = {
  title: "Hello",
  text: "Hello world\nSecond line\nThird",
  chords: [[0, "C"], [6, "Am"], [12, "G"], [24, "F"]],
};

// Real songs have tabs between the chord rows and the words, and ` \tD  Am` is a
// chord row that starts after a space and a tab.
const TABS = {
  title: "Tabs",
  text: "abc\tdef\n \tD  Am\n\tstart\na\tb\tc\td\nplain line",
  chords: [[0, "C"], [4, "Am"], [8, "G"], [14, "F"]],
};

// The left edge of the letter at a UTF-16 offset in the textarea, and the left edge
// of the sheet's letter with that song index, both in page pixels.
function letterLefts(page, offset, songChar) {
  return page.eval("(function () {" +
    "var ed = document.getElementById('sheet-editor');" +
    "var mirror = document.createElement('div');" +
    "var cs = getComputedStyle(ed);" +
    "['fontFamily','fontSize','lineHeight','tabSize','whiteSpace','fontKerning','fontVariantLigatures'," +
    "'paddingLeft','paddingTop','letterSpacing'].forEach(function (p) { mirror.style[p] = cs[p]; });" +
    "mirror.style.position = 'absolute'; mirror.style.visibility = 'hidden';" +
    "mirror.style.left = ed.getBoundingClientRect().left + 'px'; mirror.style.top = '0px';" +
    "mirror.style.whiteSpace = 'pre';" +
    "mirror.style.paddingLeft = cs.paddingLeft;" +
    "var before = ed.value.slice(0, " + offset + ").split('\\n').pop();" +
    "mirror.textContent = before;" +
    "var probe = document.createElement('span'); probe.textContent = '|'; mirror.appendChild(probe);" +
    "document.body.appendChild(mirror);" +
    "var textarea = probe.getBoundingClientRect().left;" +
    "mirror.remove();" +
    "var span = document.querySelector('#sheet .char[data-song-char=\"" + songChar + "\"]');" +
    "return { textarea: textarea, sheet: span.getBoundingClientRect().left };" +
    "})()");
}

test("a tab is as wide in the sheet as in the textarea, so the letters after it line up", { skip: skip }, function () {
  return inEditor([TABS], async function (page) {
    await startEditing(page);
    // abc<TAB>def: the textarea moves d to the next 8-column stop.
    var d = await letterLefts(page, 4, 4);
    assert.ok(Math.abs(d.textarea - d.sheet) <= 1,
      "d is at " + d.sheet.toFixed(1) + " in the sheet and " + d.textarea.toFixed(1) + " in the textarea");
    await assertAligned(page, "tabs at 100%");
    await setZoom(page, 150);
    await assertAligned(page, "tabs at 150%");
    await setZoom(page, 60);
    await assertAligned(page, "tabs at 60%");
  });
});

test("tabs stay in the song text and are not turned into spaces by editing", { skip: skip }, function () {
  return inEditor([TABS], async function (page) {
    await startEditing(page);
    assert.equal(await page.eval("document.getElementById('sheet-editor').value"), TABS.text);
    await page.eval("document.getElementById('sheet-editor').setSelectionRange(0, 0)");
    await page.insertText("X");
    await assertAligned(page, "typed before a tab");
    await click(page, "edit-save");
    await click(page, "edit-text");
    await page.waitFor("document.activeElement.id === 'sheet-editor'", "the editor");
    assert.equal(await page.eval("document.getElementById('sheet-editor').value"), "X" + TABS.text);
  });
});

// Every button of the toolbar is inside the window, with and without editing.
async function buttonsOutside(page, width) {
  return page.eval("(function () {" +
    "var out = []; var width = " + width + ";" +
    "document.querySelectorAll('.toolbar button').forEach(function (b) {" +
    "if (b.offsetParent === null) { return; }" +
    "var r = b.getBoundingClientRect();" +
    "if (r.left < -0.5 || r.right > width + 0.5) { out.push(b.id + ' ' + r.left.toFixed(0) + '..' + r.right.toFixed(0)); } });" +
    "if (document.documentElement.scrollWidth > width) { out.push('page scrolls sideways: ' + document.documentElement.scrollWidth); }" +
    "var t = document.querySelector('.toolbar'); if (t.scrollWidth > t.clientWidth + 0.5) { out.push('toolbar overflows: ' + t.scrollWidth); }" +
    "return out; })()");
}

for (var phone of [320, 375, 640, 700, 760, 800, 940, 941, 1000]) {
  (function (width) {
    test("the toolbar fits in a " + width + "px window, also while editing", { skip: skip }, async function () {
      var page = await helper.openViewer([TABS], { viewport: { width: width, height: 700 } });
      try {
        await page.eval("location.hash = '#/song/1'");
        await page.waitFor("!document.getElementById('song-view').hidden", "the song page");
        assert.deepEqual(await buttonsOutside(page, width), [], "not editing");
        await click(page, "edit-text");
        await page.waitFor("!document.getElementById('sheet-editor').hidden", "the editor");
        assert.deepEqual(await buttonsOutside(page, width), [], "editing");
        // Save and Discard can be reached, and are not hidden behind another button.
        for (var id of ["edit-save", "edit-discard"]) {
          var onTop = await page.eval("(function () { var r = document.getElementById('" + id +
            "').getBoundingClientRect(); var hit = document.elementFromPoint((r.left + r.right) / 2, (r.top + r.bottom) / 2);" +
            "return hit && hit.id; })()");
          assert.equal(onTop, id, id + " is on top at its own centre");
        }
        // Edit Chords adds four buttons: still inside the window.
        await click(page, "edit-discard");
        await click(page, "edit-chords");
        await page.waitFor("!document.getElementById('chord-actions').hidden", "the chord buttons");
        assert.deepEqual(await buttonsOutside(page, width), [], "editing chords");
        assert.deepEqual(page.errors, []);
      } finally {
        await page.close();
      }
    });
  })(phone);
}

// The rows of the toolbar (layoutToolbar): the widest mode (viewing with Save
// and Discard) decides, so the rows are the same in every mode. Wide: Back, the
// title and the buttons on one row. Narrower: the buttons below Back and the
// title, on one row while they fit, else the Edit group starts the next row.
async function toolbarRows(page) {
  return page.eval("(function () {" +
    "var t = document.querySelector('#song-view .toolbar');" +
    "var top = function (id) { return Math.round(document.getElementById(id).getBoundingClientRect().top); };" +
    "var zoom = document.getElementById('zoom-in').closest('.tool-group');" +
    "var edit = document.getElementById('edit-group');" +
    "return { narrow: t.classList.contains('narrow'), back: top('back'), zoom: Math.round(zoom.getBoundingClientRect().top)," +
    " edit: top('edit-group'), editLeft: Math.round(edit.getBoundingClientRect().left)," +
    " chords: document.getElementById('chord-actions').hidden ? null : top('chord-actions') }; })()");
}

for (var rowCase of [[1200, "one"], [700, "buttons"], [500, "edit"], [375, "edit"]]) {
  (function (width, expected) {
    test("at " + width + "px the toolbar rows are the same in every mode (" + expected + ")", { skip: skip }, async function () {
      var page = await helper.openViewer([TABS], { viewport: { width: width, height: 700 } });
      try {
        await page.eval("location.hash = '#/song/1'");
        await page.waitFor("!document.getElementById('song-view').hidden", "the song page");
        var modes = [["viewing", null], ["text", "edit-text"], ["chords", "edit-chords"]];
        for (var mode of modes) {
          if (mode[1]) {
            if (mode[0] === "chords") { await click(page, "edit-discard"); }
            await click(page, mode[1]);
            await page.waitFor("!document.getElementById('edit-actions').hidden", "editing");
          }
          var rows = await toolbarRows(page);
          if (expected === "one") {
            assert.equal(rows.narrow, false, mode[0]);
            assert.ok(Math.abs(rows.edit - rows.back) < 6, mode[0] + " one row: " + JSON.stringify(rows));
          } else {
            assert.equal(rows.narrow, true, mode[0]);
            assert.ok(rows.zoom > rows.back, mode[0] + " buttons below the title");
            if (expected === "buttons") {
              assert.equal(rows.edit, rows.zoom, mode[0] + " buttons on one row");
            } else {
              assert.ok(rows.edit > rows.zoom, mode[0] + " Edit starts a row: " + JSON.stringify(rows));
              assert.ok(rows.editLeft <= 8, mode[0] + " Edit at the left: " + rows.editLeft);
            }
          }
          if (rows.chords !== null) {
            assert.equal(rows.chords, rows.edit, mode[0] + " chord buttons follow Edit");
          }
        }
        assert.deepEqual(page.errors, []);
      } finally {
        await page.close();
      }
    });
  })(rowCase[0], rowCase[1]);
}

// A long song, scrolled to the middle. Line n is "Line n" with a chord on every third.
function longSong() {
  var lines = [];
  var chords = [];
  var at = 0;
  for (var i = 0; i < 90; i++) {
    var text = "Line " + i + " of the long song";
    lines.push(text);
    if (i % 3 === 0) {
      chords.push([at + 2, "Am"]);
    }
    at += text.length + 1;
  }
  return { title: "Long", text: lines.join("\n"), chords: chords };
}

// The song line at the top of the song area and its distance from the top edge.
function topLine(page) {
  return page.eval("(function () {" +
    "var base = document.getElementById('sheet-scroll').getBoundingClientRect().top;" +
    "var rows = document.querySelectorAll('#sheet .line');" +
    "for (var i = 0; i < rows.length; i++) { var r = rows[i].getBoundingClientRect();" +
    "if (r.bottom > base + 0.5) { return { index: i, offset: r.top - base }; } }" +
    "return null; })()");
}

test("opening and leaving the editor keeps the same song line at the top of the screen", { skip: skip }, async function () {
  var page = await helper.openViewer([longSong()], { viewport: { width: 1000, height: 500 } });
  try {
    await page.eval("location.hash = '#/song/1'");
    await page.waitFor("!document.getElementById('song-view').hidden", "the song page");
    for (var spot of [1500, 2000]) {
      await page.eval("document.getElementById('sheet-scroll').scrollTop = " + spot);
      var before = await topLine(page);
      assert.ok(before.index > 20, "scrolled into the middle (line " + before.index + ")");
      await click(page, "edit-text");
      await page.waitFor("document.activeElement.id === 'sheet-editor'", "the editor");
      var inEdit = await topLine(page);
      assert.equal(inEdit.index, before.index, "same line at the top while editing");
      assert.ok(Math.abs(inEdit.offset - before.offset) <= 2,
        "line did not move: " + before.offset.toFixed(1) + " -> " + inEdit.offset.toFixed(1));
      // The caret is on that first visible line.
      var caretLine = await page.eval("(function () { var e = document.getElementById('sheet-editor');" +
        "return { line: e.value.slice(0, e.selectionStart).split('\\n').length - 1," +
        "column: e.selectionStart - e.value.lastIndexOf('\\n', e.selectionStart - 1) - 1," +
        "collapsed: e.selectionStart === e.selectionEnd }; })()");
      assert.equal(caretLine.line, before.index, "caret is on the first visible line");
      assert.equal(caretLine.collapsed, true);
      await click(page, "edit-discard");
      var after = await topLine(page);
      assert.equal(after.index, before.index, "same line at the top after leaving");
      assert.ok(Math.abs(after.offset - before.offset) <= 2,
        "line did not move: " + before.offset.toFixed(1) + " -> " + after.offset.toFixed(1));
    }
    assert.deepEqual(page.errors, []);
  } finally {
    await page.close();
  }
});

test("focus goes to the Edit button after Save and after Discard", { skip: skip }, function () {
  return inEditor([TABS], async function (page) {
    for (var finish of ["edit-save", "edit-discard"]) {
      await startEditing(page);
      await click(page, finish);
      assert.equal(await page.eval("document.activeElement.id"), "edit-text", "after " + finish);
    }
  });
});
test("opening the same song again by its address while editing does not break the editor", { skip: skip }, function () {
  return inEditor([TABS], async function (page) {
    await startEditing(page);
    await page.insertText("X");
    // #/song/01 is song 1 again. It fires a hashchange, but it is the open song.
    await page.eval("location.hash = '#/song/01'");
    await new Promise(function (r) { setTimeout(r, 300); });
    assert.equal(await page.eval("document.getElementById('sheet-editor').hidden"), false, "still editing");
    assert.equal(await sheetText(page), await editorValue(page), "the sheet still shows the draft");
    await page.insertText("Y");
    assert.equal(await sheetText(page), await editorValue(page), "and follows later typing");
    assert.ok((await editorValue(page)).startsWith("XY"));
    await assertAligned(page, "after the same address again");
  });
});

// Letters made of several code points: e + accent, an emoji, a family (ZWJ),
// a flag, a heart with a variation selector, and Cyrillic й written as и + breve.
// Chord numbers count code points, so a chord can sit on any of them.
const CLUSTERS = {
  title: "Clusters",
  text: "e\u0301 \u2026 \u{1F600} \u{1F468}\u200D\u{1F469}\u200D\u{1F467} \u{1F1F7}\u{1F1FA} \u2764\uFE0F end\n" +
    "Мои\u0306 друг, и\u0306 тут",
  chords: [
    [0, "C"],    // on e
    [1, "D"],    // on the accent: the same letter as e
    [6, "Am"],   // on the family's first code point
    [15, "G"],   // on a flag's first code point
    [18, "F"],   // on the heart
    [19, "Em"],  // on its variation selector: the heart again
  ],
};

test("a letter made of several code points is one box in the sheet and lines up with the textarea", { skip: skip }, function () {
  return inEditor([CLUSTERS], async function (page) {
    await startEditing(page);
    await assertAligned(page, "clusters at 100%");
    await setZoom(page, 150);
    await assertAligned(page, "clusters at 150%");
    // One box per user-perceived letter.
    var boxes = await page.eval("Array.from(document.querySelectorAll('#sheet .line')[0].querySelectorAll('.char'))" +
      ".map(function (c) { return c.firstChild.textContent; })");
    assert.deepEqual(boxes.slice(0, 7), ["e\u0301", " ", "\u2026", " ", "\u{1F600}", " ",
      "\u{1F468}\u200D\u{1F469}\u200D\u{1F467}"]);
    // Editing still counts code points: a letter typed first moves every chord by
    // one code point, and the chords stay on their letters.
    await page.eval("document.getElementById('sheet-editor').setSelectionRange(0, 0)");
    await page.insertText("X");
    var shown = await chordsShown(page);
    assert.deepEqual(shown[0], [1, "e\u0301", "C"]);
    assert.equal(shown.length, 5, "every letter that had a chord still has one");
    await assertAligned(page, "clusters after typing");
  });
});

function noteShown(page) {
  return page.eval("!document.getElementById('persist-note').hidden");
}

test("Changes do not persist is shown as soon as the editor opens and goes with it", { skip: skip }, function () {
  return inEditor([TABS], async function (page) {
    assert.equal(await noteShown(page), false, "not shown before editing");
    await startEditing(page);
    assert.equal(await noteShown(page), true, "shown while editing, before any change");
    // Discard: nothing was kept, so the note goes again.
    await click(page, "edit-discard");
    assert.equal(await noteShown(page), false, "gone after Discard");
    // Save with nothing changed: still nothing that would not persist.
    await startEditing(page);
    await click(page, "edit-save");
    assert.equal(await noteShown(page), false, "gone after a Save with no change");
    // Save with a change keeps it, and Discard of a later edit leaves it.
    await startEditing(page);
    await page.insertText("X");
    assert.equal(await noteShown(page), true);
    await click(page, "edit-save");
    assert.equal(await noteShown(page), true, "kept after Save with a change");
    await startEditing(page);
    await click(page, "edit-discard");
    assert.equal(await noteShown(page), true, "the earlier saved edit still does not persist");
  });
});

// iPhone Safari zooms the whole page when a text field with a font under 16px is
// focused. The textarea is therefore never set smaller than 16px: below 80% zoom
// it is laid out larger and scaled down again, so it still covers the sheet.
for (var small of [50, 60, 70, 80, 100]) {
  (function (percent) {
    test("the textarea font is at least 16px and still lines up with the sheet at " + percent + "%", { skip: skip }, function () {
      return inEditor([HELLO_LAYOUT], async function (page) {
        await setZoom(page, percent);
        await startEditing(page);
        var size = await page.eval("parseFloat(getComputedStyle(document.getElementById('sheet-editor')).fontSize)");
        assert.ok(size >= 16, "textarea font is " + size + "px at " + percent + "%");
        // Below 80% the textarea is scaled down from a 16px font, and the browser
        // rounds its lines to whole pixels differently, so up to 1.2px is allowed.
        var tolerance = percent < 80 ? 1.2 : 1;
        await assertAligned(page, "opened at " + percent + "%", tolerance);
        await page.insertText("XY");
        await assertAligned(page, "typed at " + percent + "%", tolerance);
        // It covers the whole song area, whatever its font.
        var box = await page.eval("(function () {" +
          "var e = document.getElementById('sheet-editor').getBoundingClientRect();" +
          "var s = document.getElementById('sheet').getBoundingClientRect();" +
          "return [e.left - s.left, e.top - s.top, e.width - s.width, e.height - s.height]; })()");
        assert.ok(Math.abs(box[0]) <= 1 && Math.abs(box[1]) <= 1, "same corner " + box);
        assert.ok(box[2] >= -1 && box[3] >= -1, "at least as big as the sheet " + box);
      });
    });
  })(small);
}

test("only the textarea is left for a screen reader while editing, not the sheet under it", { skip: skip }, function () {
  return inEditor([HELLO_LAYOUT], async function (page) {
    var state = function () {
      return page.eval("({ sheet: document.getElementById('sheet').getAttribute('aria-hidden')," +
        "label: document.getElementById('sheet-editor').getAttribute('aria-label')," +
        "editorHidden: document.getElementById('sheet-editor').hidden })");
    };
    assert.equal((await state()).sheet, null, "the sheet is read while viewing");
    await startEditing(page);
    var editing = await state();
    assert.equal(editing.sheet, "true");
    assert.equal(editing.label, "Song text");
    assert.equal(editing.editorHidden, false);
    await click(page, "edit-discard");
    assert.equal((await state()).sheet, null, "after Discard");
    await startEditing(page);
    assert.equal((await state()).sheet, "true", "editing again");
    await click(page, "edit-save");
    assert.equal((await state()).sheet, null, "after Save");
  });
});
