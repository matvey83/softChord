// Edit chords in the real viewer page, in headless Chrome: the mode itself, the
// selection, the pointer and the keyboard. Skipped when Chrome is not installed.
// Safari, Firefox and a real phone are not tested.

const test = require("node:test");
const assert = require("node:assert/strict");
const helper = require("./browser_helper");

const skip = helper.skipUnlessBrowser();

const HELLO = {
  title: "Hello",
  text: "Hello world\nSecond line\nThird",
  chords: [[0, "C"], [6, "Am"], [12, "G"], [24, "F"]],
};

const { inEditor, click, disabled, chordsShown, point, selectedLetter, setZoom } = require("./edit_helpers");

async function startChords(page) {
  await click(page, "edit-chords");
  await page.waitFor("document.getElementById('sheet-wrap').classList.contains('chord-mode')", "chord mode");
}

test("the Edit chords button opens the mode next to the pencil and locks what must wait", { skip: skip }, function () {
  return inEditor([HELLO], async function (page) {
    assert.equal(await page.eval("document.getElementById('edit-chords').title"), "Edit Chords…");
    assert.equal(await page.eval("document.getElementById('edit-chords').getAttribute('aria-label')"), "Edit Chords…");
    assert.equal(await page.eval("document.getElementById('edit-chords').previousElementSibling.id"), "edit-text");
    assert.equal(await page.eval("document.getElementById('chord-actions').hidden"), true);
    assert.equal(await page.eval("document.getElementById('persist-note').hidden"), true);
    await startChords(page);
    // The banner is there from the first moment, and Save and Discard with it.
    assert.equal(await page.eval("document.getElementById('persist-note').hidden"), false);
    assert.equal(await page.eval("document.getElementById('persist-note').textContent"), "Changes do not persist");
    assert.equal(await page.eval("document.getElementById('edit-actions').hidden"), false);
    assert.equal(await page.eval("document.getElementById('chord-actions').hidden"), false);
    // No textarea: the sheet itself is edited, and the keyboard can reach it.
    assert.equal(await page.eval("document.getElementById('sheet-editor').hidden"), true);
    assert.equal(await page.eval("document.getElementById('sheet').tabIndex"), 0);
    assert.equal(await page.eval("document.getElementById('sheet').getAttribute('aria-hidden')"), null);
    assert.equal(await page.eval("document.activeElement.id"), "sheet");
    // The song transpose and what reads the song wait. Zoom stays, and Edit text
    // switches this edit to the text.
    for (var id of ["print", "copy-text", "copy-chords", "copy-image", "transpose-down", "transpose-up",
      "transpose-reset", "edit-chords"]) {
      assert.equal(await disabled(page, id), true, id + " waits until Save or Discard");
    }
    assert.equal(await disabled(page, "edit-text"), false, "edit-text switches modes");
    for (id of ["zoom-in", "zoom-out"]) {
      assert.equal(await disabled(page, id), false, id + " stays on");
    }
    // Nothing is selected yet, so there is no chord to edit or delete, and nothing to undo.
    for (id of ["chord-edit", "chord-delete", "chord-undo", "chord-redo"]) {
      assert.equal(await disabled(page, id), true, id + " has nothing to do yet");
    }
    // Every line has room for its chords, also the ones that have none.
    assert.ok(await page.eval("parseFloat(getComputedStyle(document.querySelectorAll('#sheet .line')[2]).marginTop) > 10"));
    assert.deepEqual(await chordsShown(page), [[0, "H", "C"], [6, "w", "Am"], [12, "S", "G"], [24, "T", "F"]]);
  });
});

test("while editing, the other one of Edit text and Edit chords stays on (it switches modes)", { skip: skip }, function () {
  return inEditor([HELLO], async function (page) {
    await click(page, "edit-text");
    await page.waitFor("document.activeElement.id === 'sheet-editor'", "the editor");
    assert.equal(await disabled(page, "edit-chords"), false);
    assert.equal(await disabled(page, "edit-text"), true);
    assert.equal(await page.eval("document.getElementById('chord-actions').hidden"), true);
    assert.equal(await page.eval("document.getElementById('sheet').getAttribute('aria-hidden')"), "true");
    assert.equal(await page.eval("document.getElementById('sheet').hasAttribute('tabindex')"), false);
    await click(page, "edit-discard");
    assert.equal(await disabled(page, "edit-chords"), false);
    await startChords(page);
    assert.equal(await disabled(page, "edit-text"), false);
    assert.equal(await disabled(page, "edit-chords"), true);
    await click(page, "edit-discard");
    assert.equal(await page.eval("document.getElementById('sheet-wrap').classList.contains('chord-mode')"), false);
    assert.equal(await page.eval("document.getElementById('sheet-wrap').classList.contains('editing')"), false);
    assert.equal(await page.eval("document.getElementById('chord-actions').hidden"), true);
    assert.equal(await page.eval("document.getElementById('edit-actions').hidden"), true);
    assert.equal(await page.eval("document.getElementById('sheet').hasAttribute('tabindex')"), false);
    assert.equal(await page.eval("document.getElementById('sheet').hasAttribute('role')"), false);
    for (var id of ["print", "copy-text", "transpose-down", "edit-text", "edit-chords"]) {
      assert.equal(await disabled(page, id), false, id + " is back");
    }
    // The button that began the edit has the keyboard again.
    assert.equal(await page.eval("document.activeElement.id"), "edit-chords");
    assert.equal(await page.eval("document.getElementById('persist-note').hidden"), true);
  });
});

test("Save with no chord changed keeps nothing, like Edit text", { skip: skip }, function () {
  return inEditor([HELLO], async function (page) {
    await startChords(page);
    await click(page, "edit-save");
    assert.equal(await page.eval("document.getElementById('persist-note').hidden"), true);
    assert.deepEqual(await chordsShown(page), [[0, "H", "C"], [6, "w", "Am"], [12, "S", "G"], [24, "T", "F"]]);
    assert.equal(await page.eval("document.activeElement.id"), "edit-chords");
  });
});

test("a press selects the letter or the chord under the pointer, and a press on nothing clears it", { skip: skip }, function () {
  return inEditor([HELLO], async function (page) {
    await startChords(page);
    // A letter with no chord: selected, Add chord on, Delete chord off.
    var p = await point(page, 1);
    await page.mouse.click(p.x, p.y);
    assert.equal(await selectedLetter(page), 1);
    assert.equal(await disabled(page, "chord-edit"), false);
    assert.equal(await page.eval("document.getElementById('chord-edit').title"), "Add chord");
    assert.equal(await disabled(page, "chord-delete"), true);
    assert.equal(await page.eval("document.getElementById('chord-live').textContent"), "Line 1, letter e, no chord");
    // A chord: its letter is selected, Edit chord and Delete chord are on.
    p = await point(page, 6, "chord");
    await page.mouse.click(p.x, p.y);
    assert.equal(await selectedLetter(page), 6);
    assert.equal(await page.eval("document.getElementById('chord-edit').title"), "Edit chord");
    assert.equal(await disabled(page, "chord-delete"), false);
    assert.equal(await page.eval("document.getElementById('chord-live').textContent"), "Line 1, letter w, chord Am");
    // The room above a letter (where the chord would be) is on that letter.
    p = await point(page, 15);
    var above = await page.eval("document.querySelector('#sheet .char[data-song-char=\"15\"]').getBoundingClientRect().top");
    await page.mouse.click(p.x, above - 8);
    assert.equal(await selectedLetter(page), 15);
    // Nothing there: the selection goes. A press outside the sheet does not clear it.
    await page.mouse.click(600, 800);
    assert.equal(await selectedLetter(page), null);
    assert.equal(await disabled(page, "chord-edit"), true);
    p = await point(page, 1);
    await page.mouse.click(p.x, p.y);
    await click(page, "zoom-in");
    assert.equal(await selectedLetter(page), 1, "the selection survives the repaint of a zoom");
    await page.pressKey("Escape");
    assert.equal(await selectedLetter(page), null);
    assert.equal(await page.eval("document.getElementById('sheet-wrap').classList.contains('chord-mode')"), true,
      "Escape clears the selection and does not leave the mode");
    assert.deepEqual(page.errors, []);
  });
});

test("a chord is hit from 6px around it at any zoom, and not from further", { skip: skip }, function () {
  return inEditor([HELLO], async function (page) {
    await startChords(page);
    for (var zoom of [100, 160]) {
      await setZoom(page, zoom);
      var r = await page.eval("(function () { var c = document.querySelector('#sheet .char[data-song-char=\"6\"] .chord')" +
        ".getBoundingClientRect(); return { l: c.left, r: c.right, t: c.top, b: c.bottom }; })()");
      var y = (r.t + r.b) / 2;
      await page.mouse.click(r.l - 5, y);
      assert.equal(await selectedLetter(page), 6, "5px left of the chord at " + zoom + "%");
      await page.mouse.click(600, 800);
      await page.mouse.click(r.r + 5, y);
      assert.equal(await selectedLetter(page), 6, "5px right of the chord at " + zoom + "%");
      await page.mouse.click(600, 800);
      // 9px away it is the neighbouring letter, or nothing, but not the chord.
      await page.mouse.click(r.r + 9, y);
      assert.notEqual(await selectedLetter(page), 6, "9px right of the chord at " + zoom + "%");
      await page.mouse.click(600, 800);
    }
  });
});

test("chords that overlap are told apart by which middle is nearer", { skip: skip }, function () {
  var crowded = {
    title: "Crowded",
    text: "abc",
    chords: [[0, "C#m7b5"], [1, "F#m7b5"]],
  };
  return inEditor([crowded], async function (page) {
    await startChords(page);
    var r = await page.eval("Array.from(document.querySelectorAll('#sheet .chord')).map(function (c) {" +
      "var b = c.getBoundingClientRect(); return { l: b.left, r: b.right, m: (b.left + b.right) / 2," +
      "y: (b.top + b.bottom) / 2 }; })");
    assert.ok(r[0].r > r[1].l, "the two chords overlap");
    var x = (r[0].m + r[1].m) / 2;
    await page.mouse.click(x - 1, r[0].y);
    assert.equal(await selectedLetter(page), 0, "just left of the middle between them: the first");
    await page.mouse.click(x + 1, r[0].y);
    assert.equal(await selectedLetter(page), 1, "just right of it: the second");
  });
});

test("under a mouse a chord is a light-blue pill and its letter a faint box, and the cursor can grab", { skip: skip }, function () {
  return inEditor([HELLO], async function (page) {
    var style = "(function (sel) { var e = document.querySelector(sel); var s = getComputedStyle(e);" +
      "return { bg: s.backgroundColor, shadow: s.boxShadow, cursor: s.cursor }; })";
    var chordSel = "#sheet .char[data-song-char=\"6\"] .chord";
    var letterSel = "#sheet .char[data-song-char=\"6\"]";
    // Outside the mode there is no hover effect at all.
    var p = await point(page, 6, "chord");
    await page.mouse.move(p.x, p.y);
    assert.equal((await page.eval(style + "('" + chordSel + "')")).shadow, "none");
    await startChords(page);
    await page.mouse.move(5, 700);
    var rest = await page.eval(style + "('" + chordSel + "')");
    assert.equal(rest.shadow, "none");
    assert.equal(rest.cursor, "grab");
    await page.mouse.move(p.x, p.y);
    var over = await page.eval(style + "('" + chordSel + "')");
    assert.notEqual(over.shadow, "none", "the chord under the pointer has its pill");
    assert.notEqual(over.bg, "rgba(0, 0, 0, 0)");
    assert.notEqual((await page.eval(style + "('" + letterSel + "')")).bg, "rgba(0, 0, 0, 0)", "and its letter a faint box");
    // Another chord has neither.
    assert.equal((await page.eval(style + "('#sheet .char[data-song-char=\"12\"] .chord')")).shadow, "none");
    // A letter with no chord under the pointer: only the faint box, the cursor of a letter.
    var q = await point(page, 2);
    await page.mouse.move(q.x, q.y);
    var plain = await page.eval(style + "('#sheet .char[data-song-char=\"2\"]')");
    assert.notEqual(plain.bg, "rgba(0, 0, 0, 0)");
    assert.equal(plain.cursor, "pointer");
    assert.equal((await page.eval(style + "('" + chordSel + "')")).shadow, "none");
    // The selected one stays blue under the pointer.
    await page.mouse.click(p.x, p.y);
    assert.equal((await page.eval(style + "('" + letterSel + "')")).bg, "rgba(0, 122, 255, 0.2)");
  });
});

test("the hover and the selection are screen only: no rule for them applies to print", { skip: skip }, function () {
  return inEditor([HELLO], async function (page) {
    // Every rule that names the mode is inside @media screen, so print (and the
    // copied image, which is drawn from the song, not the page) is the same as before.
    var loose = await page.eval("Array.from(document.styleSheets).reduce(function (all, s) {" +
      "return all.concat(Array.from(s.cssRules).filter(function (r) {" +
      "return r.selectorText && r.selectorText.indexOf('chord-mode') >= 0; })" +
      ".map(function (r) { return r.selectorText; })); }, [])");
    assert.deepEqual(loose, [], "chord-mode rules outside @media screen: " + loose.join(" | "));
    var screenRules = await page.eval("Array.from(document.styleSheets).reduce(function (n, s) {" +
      "return n + Array.from(s.cssRules).filter(function (r) { return r.media && r.media.mediaText.indexOf('screen') >= 0 &&" +
      "r.cssText.indexOf('chord-mode') >= 0; }).length; }, 0)");
    assert.ok(screenRules >= 2, "the rules are there, inside screen media");
  });
});

// Drag the chord on one letter to another letter with the mouse. Returns nothing.
async function dragChord(page, from, to, options) {
  var a = await point(page, from, "chord");
  var b = await point(page, to);
  await page.mouse.drag(a, b, options);
}

const SHOWN = [[0, "H", "C"], [6, "w", "Am"], [12, "S", "G"], [24, "T", "F"]];

function undoDisabled(page) { return disabled(page, "chord-undo"); }

test("dragging a chord moves it live from the first 4px, with no selecting first, as one Undo step", { skip: skip }, function () {
  return inEditor([HELLO], async function (page) {
    await startChords(page);
    // The press is on a chord that is not selected: it moves, and ends up selected.
    var a = await point(page, 6, "chord");
    var b = await point(page, 8);
    await page.mouse.move(a.x, a.y);
    await page.mouse.down(a.x, a.y);
    await page.mouse.move(b.x, b.y, 1);
    assert.deepEqual(await chordsShown(page), [[0, "H", "C"], [8, "r", "Am"], [12, "S", "G"], [24, "T", "F"]],
      "the chord is on the new letter while the button is down");
    assert.equal(await page.eval("document.getElementById('sheet-wrap').classList.contains('dragging')"), true);
    assert.equal(await page.eval("document.querySelectorAll('#sheet .chord.dragging').length"), 1);
    assert.equal(await undoDisabled(page), true, "nothing is a step of Undo before the pointer lets go");
    await page.mouse.up(b.x, b.y);
    assert.equal(await page.eval("document.getElementById('sheet-wrap').classList.contains('dragging')"), false);
    assert.equal(await page.eval("document.querySelectorAll('#sheet .chord.dragging').length"), 0);
    assert.equal(await selectedLetter(page), 8, "the moved chord is the selected one");
    assert.equal(await page.eval("document.getElementById('chord-live').textContent"), "Moved chord Am to line 1, letter r");
    assert.equal(await undoDisabled(page), false);
    // One drag, one step: a single Undo puts it back, Redo moves it again.
    await click(page, "chord-undo");
    assert.deepEqual(await chordsShown(page), SHOWN);
    assert.equal(await undoDisabled(page), true);
    await click(page, "chord-redo");
    assert.deepEqual(await chordsShown(page), [[0, "H", "C"], [8, "r", "Am"], [12, "S", "G"], [24, "T", "F"]]);
    assert.deepEqual(page.errors, []);
  });
});

test("a press that moves less than 4px is only a press", { skip: skip }, function () {
  return inEditor([HELLO], async function (page) {
    await startChords(page);
    var a = await point(page, 6, "chord");
    await page.mouse.move(a.x, a.y);
    await page.mouse.down(a.x, a.y);
    await page.mouse.move(a.x + 3, a.y, 1);
    await page.mouse.up(a.x + 3, a.y);
    assert.deepEqual(await chordsShown(page), SHOWN);
    assert.equal(await selectedLetter(page), 6);
    assert.equal(await undoDisabled(page), true);
    // Past 4px but back on the same letter: nothing moved, nothing to undo.
    await dragChord(page, 6, 6);
    await page.mouse.move(a.x, a.y);
    await page.mouse.down(a.x, a.y);
    await page.mouse.move(a.x + 5, a.y, 1);
    await page.mouse.move(a.x, a.y, 1);
    await page.mouse.up(a.x, a.y);
    assert.deepEqual(await chordsShown(page), SHOWN);
    assert.equal(await undoDisabled(page), true);
  });
});

test("Escape and a cancelled pointer put the chord back, and the release after does nothing", { skip: skip }, function () {
  return inEditor([HELLO], async function (page) {
    await startChords(page);
    var a = await point(page, 6, "chord");
    var b = await point(page, 9);
    await page.mouse.move(a.x, a.y);
    await page.mouse.down(a.x, a.y);
    await page.mouse.move(b.x, b.y, 1);
    assert.deepEqual((await chordsShown(page))[1], [9, "l", "Am"]);
    await page.pressKey("Escape");
    assert.deepEqual(await chordsShown(page), SHOWN);
    assert.equal(await selectedLetter(page), 6, "the chord that was selected is selected again");
    assert.equal(await page.eval("document.getElementById('sheet-wrap').classList.contains('dragging')"), false);
    assert.equal(await page.eval("document.getElementById('chord-live').textContent"), "Move cancelled");
    await page.mouse.move(b.x + 20, b.y, 1);
    await page.mouse.up(b.x + 20, b.y);
    assert.deepEqual(await chordsShown(page), SHOWN, "the pointer that is still down moves nothing now");
    assert.equal(await undoDisabled(page), true);
    // A touch that the browser takes over (it scrolls, a call comes in) is cancelled the same way.
    a = await point(page, 6, "chord");
    await page.touch.start(a.x, a.y);
    await page.touch.move(b.x, b.y);
    assert.deepEqual((await chordsShown(page))[1], [9, "l", "Am"]);
    await page.touch.cancel();
    assert.deepEqual(await chordsShown(page), SHOWN);
    assert.equal(await undoDisabled(page), true);
  });
});

test("a chord jumps over a letter that has a chord and crosses lines, nothing is lost", { skip: skip }, function () {
  return inEditor([HELLO], async function (page) {
    await startChords(page);
    // C at 0 dragged right over Am at 6: it lands past it.
    await dragChord(page, 0, 6);
    assert.deepEqual(await chordsShown(page), [[6, "w", "Am"], [7, "o", "C"], [12, "S", "G"], [24, "T", "F"]]);
    await click(page, "chord-undo");
    // G on line 2 dragged up to line 1.
    await dragChord(page, 12, 2);
    assert.deepEqual(await chordsShown(page), [[0, "H", "C"], [2, "l", "G"], [6, "w", "Am"], [24, "T", "F"]]);
    // And on down to line 3, in one drag that passes line 2.
    await dragChord(page, 2, 27);
    assert.deepEqual(await chordsShown(page), [[0, "H", "C"], [6, "w", "Am"], [24, "T", "F"], [27, "r", "G"]]);
    // Past the end of a line the line gets spaces for the chord, up to 10 past
    // its last letter (SongChordEdit.withRoom). The F of the next line moves on.
    var a = await point(page, 6, "chord");
    var end = await point(page, 10);
    await page.mouse.drag(a, { x: end.x + 300, y: end.y });
    assert.deepEqual(await chordsShown(page), [[0, "H", "C"], [20, " ", "Am"], [34, "T", "F"], [37, "r", "G"]]);
    // Dragged back onto the line, the spaces go again.
    a = await point(page, 20, "chord");
    var back = await point(page, 8);
    await page.mouse.drag(a, back);
    assert.deepEqual(await chordsShown(page), [[0, "H", "C"], [8, "r", "Am"], [24, "T", "F"], [27, "r", "G"]]);
    // Undo puts the text back with the chords: the spaces are there again.
    await click(page, "chord-undo");
    assert.deepEqual(await chordsShown(page), [[0, "H", "C"], [20, " ", "Am"], [34, "T", "F"], [37, "r", "G"]]);
    assert.deepEqual(page.errors, []);
  });
});

test("a chord grabbed by its edge moves with the pointer, not by its middle", { skip: skip }, function () {
  return inEditor([HELLO], async function (page) {
    await startChords(page);
    var r = await page.eval("(function () { var c = document.querySelector('#sheet .char[data-song-char=\"6\"] .chord')" +
      ".getBoundingClientRect(); return { r: c.right, y: (c.top + c.bottom) / 2 }; })()");
    var one = await point(page, 7);
    var six = await point(page, 6);
    var step = one.x - six.x;
    // Grabbed 4px from its right edge, a move of exactly one letter is one letter.
    await page.mouse.drag({ x: r.r + 4, y: r.y }, { x: r.r + 4 + step, y: one.y });
    assert.deepEqual((await chordsShown(page))[1], [7, "o", "Am"]);
  });
});

test("a finger drags a chord too, and Save keeps the chords where they were dropped", { skip: skip }, function () {
  return inEditor([HELLO], async function (page) {
    await startChords(page);
    var a = await point(page, 6, "chord");
    var b = await point(page, 9);
    await page.touch.drag(a, b);
    assert.deepEqual((await chordsShown(page))[1], [9, "l", "Am"]);
    assert.equal(await selectedLetter(page), 9);
    assert.equal(await undoDisabled(page), false);
    await click(page, "edit-save");
    assert.deepEqual((await chordsShown(page))[1], [9, "l", "Am"]);
    assert.equal(await page.eval("document.getElementById('persist-note').hidden"), false);
    assert.deepEqual(page.errors, []);
  });
});

async function selectLetter(page, letter) {
  var p = await point(page, letter);
  await page.mouse.click(p.x, p.y);
  assert.equal(await selectedLetter(page), letter);
}

function live(page) { return page.eval("document.getElementById('chord-live').textContent"); }

test("A to G put a major chord on the selected letter and replace the one there", { skip: skip }, function () {
  return inEditor([HELLO], async function (page) {
    await startChords(page);
    // Nothing selected: the keys do nothing.
    await page.type("a");
    assert.deepEqual(await chordsShown(page), SHOWN);
    await selectLetter(page, 1);
    await page.type("a");
    assert.deepEqual(await chordsShown(page), [[0, "H", "C"], [1, "e", "A"], [6, "w", "Am"], [12, "S", "G"], [24, "T", "F"]]);
    assert.equal(await live(page), "Added, Line 1, letter e, chord A");
    assert.equal(await page.eval("document.getElementById('chord-edit').title"), "Edit chord");
    // Lower case or upper case, the same. D replaces Am with D major.
    await selectLetter(page, 6);
    await page.type("D", 8);
    assert.deepEqual((await chordsShown(page))[2], [6, "w", "D"]);
    assert.equal(await live(page), "Replaced, Line 1, letter w, chord D");
    // With Ctrl, Cmd or Alt it is a shortcut of the browser and does nothing here.
    await page.type("e", 2);
    await page.type("e", 4);
    await page.type("e", 1);
    assert.deepEqual((await chordsShown(page))[2], [6, "w", "D"]);
    // The keyboard goes through the real stack of one step each, and Undo walks back.
    await click(page, "chord-undo");
    assert.deepEqual((await chordsShown(page))[2], [6, "w", "Am"]);
    await click(page, "chord-undo");
    assert.deepEqual(await chordsShown(page), SHOWN);
    assert.deepEqual(page.errors, []);
  });
});

test("the chord is typed as it is shown when the song is shown transposed, and kept as stored", { skip: skip }, function () {
  return inEditor([HELLO], async function (page) {
    await click(page, "transpose-up");
    await click(page, "transpose-up");
    assert.deepEqual((await chordsShown(page))[0], [0, "H", "D"]);
    await startChords(page);
    assert.equal(await disabled(page, "transpose-up"), true);
    await selectLetter(page, 1);
    await page.type("g");
    assert.deepEqual((await chordsShown(page))[1], [1, "e", "G"], "G is what was typed and what is shown");
    await click(page, "edit-save");
    // Still shown transposed by two, G as typed. Back at 0 it is F, as stored.
    assert.deepEqual((await chordsShown(page))[1], [1, "e", "G"]);
    await click(page, "transpose-reset");
    assert.deepEqual((await chordsShown(page))[0], [0, "H", "C"]);
    assert.deepEqual((await chordsShown(page))[1], [1, "e", "F"]);
  });
});

test("m toggles minor, Delete removes the chord", { skip: skip }, function () {
  return inEditor([HELLO], async function (page) {
    await startChords(page);
    await selectLetter(page, 6);
    await page.type("m");
    assert.deepEqual((await chordsShown(page))[1], [6, "w", "A"]);
    await page.type("m");
    assert.deepEqual((await chordsShown(page))[1], [6, "w", "Am"]);
    // m on a letter with no chord does nothing.
    await selectLetter(page, 2);
    await page.type("m");
    assert.equal((await chordsShown(page)).length, 4);
    await selectLetter(page, 6);
    await page.key("Backspace");
    assert.deepEqual(await chordsShown(page), [[0, "H", "C"], [12, "S", "G"], [24, "T", "F"]]);
    assert.equal(await live(page), "Deleted, Line 1, letter w, no chord");
    assert.equal(await selectedLetter(page), 6, "the letter stays selected");
    assert.equal(await disabled(page, "chord-delete"), true);
    await page.type("z", 2);
    assert.deepEqual(await chordsShown(page), [[0, "H", "C"], [6, "w", "Am"], [12, "S", "G"], [24, "T", "F"]]);
    await page.key("Delete");
    assert.equal((await chordsShown(page)).length, 3);
  });
});

test("Left and Right move the chord along its line and jump over a chord", { skip: skip }, function () {
  return inEditor([HELLO], async function (page) {
    await startChords(page);
    await selectLetter(page, 0);
    for (var i = 0; i < 5; i++) { await page.key("ArrowRight"); }
    assert.deepEqual((await chordsShown(page))[0], [5, " ", "C"]);
    await page.key("ArrowRight");
    assert.deepEqual(await chordsShown(page), [[6, "w", "Am"], [7, "o", "C"], [12, "S", "G"], [24, "T", "F"]],
      "it jumped over the chord at 6");
    assert.equal(await selectedLetter(page), 7, "the selection goes with the chord");
    await page.key("ArrowLeft");
    assert.deepEqual(await chordsShown(page), [[5, " ", "C"], [6, "w", "Am"], [12, "S", "G"], [24, "T", "F"]],
      "and back over it again");
    // At the start of the line it stays.
    await selectLetter(page, 12);
    await page.key("ArrowLeft");
    assert.equal(await live(page), "The chord cannot move left from here");
    assert.deepEqual((await chordsShown(page)).filter(function (c) { return c[2] === "G"; })[0], [12, "S", "G"]);
    assert.deepEqual(page.errors, []);
  });
});

test("the arrows do nothing on a letter with no chord, and Up and Down never change a chord", { skip: skip }, function () {
  return inEditor([HELLO], async function (page) {
    await startChords(page);
    await page.eval("window.prevented = []; window.addEventListener('keydown', function (e) { prevented.push(e.key + ':' + e.defaultPrevented); })");
    await selectLetter(page, 1);
    await page.key("ArrowRight");
    await page.key("ArrowLeft");
    await page.key("ArrowUp");
    await page.key("ArrowDown");
    assert.equal(await selectedLetter(page), 1, "the selection stays");
    assert.deepEqual(await chordsShown(page), SHOWN);
    // On a chord Up and Down do nothing either; Left and Right still move it.
    await selectLetter(page, 6);
    await page.key("ArrowUp");
    await page.key("ArrowDown");
    assert.deepEqual(await chordsShown(page), SHOWN, "the chord is not transposed");
    assert.equal(await selectedLetter(page), 6);
    assert.equal(await disabled(page, "chord-undo"), true, "nothing to undo");
    await page.key("ArrowRight");
    assert.deepEqual((await chordsShown(page))[1], [7, "o", "Am"]);
    // Only the moving arrow is taken from the browser; the others can scroll the page.
    assert.deepEqual(await page.eval("prevented"), ["ArrowRight:false", "ArrowLeft:false", "ArrowUp:false",
      "ArrowDown:false", "ArrowUp:false", "ArrowDown:false", "ArrowRight:true"]);
    assert.deepEqual(page.errors, []);
  });
});

test("Ctrl or Cmd+Z undoes and Shift with it redoes, and so do the buttons", { skip: skip }, function () {
  return inEditor([HELLO], async function (page) {
    await startChords(page);
    await selectLetter(page, 1);
    await page.type("c");
    await page.type("d");
    assert.equal((await chordsShown(page))[1][2], "D");
    await page.type("z", 2);
    assert.equal((await chordsShown(page))[1][2], "C");
    await page.type("z", 4);
    assert.equal((await chordsShown(page)).length, 4);
    assert.equal(await undoDisabled(page), true);
    await page.type("Z", 2 | 8);
    assert.equal((await chordsShown(page))[1][2], "C");
    await page.type("Z", 4 | 8);
    assert.equal((await chordsShown(page))[1][2], "D");
    assert.equal(await disabled(page, "chord-redo"), true);
    await click(page, "chord-undo");
    assert.equal((await chordsShown(page))[1][2], "C");
    assert.equal(await page.eval("document.activeElement.id"), "sheet");
    // A new edit after Undo drops what Redo had.
    await page.type("e");
    assert.equal(await disabled(page, "chord-redo"), true);
    // Save and Discard are the way out; Undo cannot go before where the draft began.
    await page.type("z", 2);
    await page.type("z", 2);
    await page.type("z", 2);
    assert.equal((await chordsShown(page)).length, 4);
    assert.deepEqual(page.errors, []);
  });
});

function entryState(page) {
  return page.eval("(function () { var f = document.getElementById('chord-entry-field');" +
    "var r = document.getElementById('chord-entry');" +
    "return { open: !r.hidden, value: f.value, red: f.classList.contains('invalid')," +
    "note: document.getElementById('chord-entry-note').textContent," +
    "okDisabled: document.getElementById('chord-entry-ok').disabled," +
    "focused: document.activeElement === f, selection: [f.selectionStart, f.selectionEnd] }; })()");
}

async function typeInto(page, text) {
  await page.eval("document.getElementById('chord-entry-field').select()");
  await page.insertText(text);
}

test("a double click opens the chord entry with C for a letter with none, and OK adds it", { skip: skip }, function () {
  return inEditor([HELLO], async function (page) {
    await startChords(page);
    var p = await point(page, 1);
    await page.mouse.doubleClick(p.x, p.y);
    var e = await entryState(page);
    assert.deepEqual(e, { open: true, value: "C", red: false, note: "Shown as C", okDisabled: false,
      focused: true, selection: [0, 1] });
    assert.equal(await selectedLetter(page), 1);
    // It is under the letter, on the screen.
    var box = await page.eval("(function () { var r = document.getElementById('chord-entry').getBoundingClientRect();" +
      "var l = document.querySelector('#sheet .char[data-song-char=\"1\"]').getBoundingClientRect();" +
      "return { top: r.top, bottom: r.bottom, left: r.left, right: r.right, letterBottom: l.bottom," +
      "letterMiddle: (l.left + l.right) / 2, w: innerWidth, h: innerHeight }; })()");
    assert.ok(box.top >= box.letterBottom, "under the letter");
    assert.ok(box.left >= 0 && box.right <= box.w && box.bottom <= box.h, "inside the window");
    assert.ok(Math.abs((box.left + box.right) / 2 - box.letterMiddle) < 140, "near the letter");
    assert.ok(parseFloat(await page.eval("getComputedStyle(document.getElementById('chord-entry-field')).fontSize")) >= 16);
    await typeInto(page, "F#m7");
    e = await entryState(page);
    assert.equal(e.note, "Shown as F♯m7");
    assert.equal(e.red, false);
    await page.key("Enter");
    assert.equal((await entryState(page)).open, false);
    assert.deepEqual((await chordsShown(page))[1], [1, "e", "F♯m7"]);
    assert.equal(await page.eval("document.activeElement.id"), "sheet", "the keyboard goes back to the sheet");
    assert.equal(await live(page), "Added, Line 1, letter e, chord F♯m7");
    await click(page, "chord-undo");
    assert.deepEqual(await chordsShown(page), SHOWN);
  });
});

test("the entry starts with the chord as shown, replaces it on OK, and Cancel changes nothing", { skip: skip }, function () {
  return inEditor([HELLO], async function (page) {
    await startChords(page);
    var p = await point(page, 6, "chord");
    await page.mouse.doubleClick(p.x, p.y);
    var e = await entryState(page);
    assert.equal(e.value, "Am");
    assert.deepEqual(e.selection, [0, 2], "all of it is selected, so typing replaces it");
    await typeInto(page, "Dm7");
    await page.eval("document.getElementById('chord-entry-ok').click()");
    assert.deepEqual((await chordsShown(page))[1], [6, "w", "Dm7"]);
    // The same chord again is not a step of Undo.
    await click(page, "chord-undo");
    await page.key("Enter");
    assert.equal((await entryState(page)).value, "Am");
    await page.key("Enter");
    assert.equal(await undoDisabled(page), true, "Am typed over Am is not a change");
    // Cancel button, Escape, and a press elsewhere.
    await page.key("F2");
    await typeInto(page, "G");
    await click(page, "chord-entry-cancel");
    assert.deepEqual(await chordsShown(page), SHOWN);
    assert.equal(await page.eval("document.activeElement.id"), "sheet");
    await page.key("F2");
    await typeInto(page, "G");
    await page.pressKey("Escape");
    assert.equal((await entryState(page)).open, false);
    assert.deepEqual(await chordsShown(page), SHOWN);
    await page.eval("document.getElementById('chord-edit').click()");
    assert.equal((await entryState(page)).open, true, "the Edit chord button opens it too");
    await page.mouse.click(900, 150);
    assert.equal((await entryState(page)).open, false);
    assert.equal(await selectedLetter(page), null, "and the press went on to clear the selection");
    assert.deepEqual(await chordsShown(page), SHOWN);
  });
});

test("the field is red with OK waiting while the text is not a chord", { skip: skip }, function () {
  return inEditor([HELLO], async function (page) {
    await startChords(page);
    await selectLetter(page, 2);
    await page.key("Enter");
    for (var bad of ["J", "x", "7", "", "  "]) {
      await typeInto(page, bad);
      var e = await entryState(page);
      assert.equal(e.red, true, JSON.stringify(bad) + " is red");
      assert.equal(e.okDisabled, true);
      assert.equal(e.note, "Not a chord. Start with a note from A to G.");
      await page.key("Enter");
      assert.equal((await entryState(page)).open, true, "Return does nothing for " + JSON.stringify(bad));
    }
    assert.deepEqual(await chordsShown(page), SHOWN);
    await typeInto(page, "Bb");
    e = await entryState(page);
    assert.equal(e.red, false);
    assert.equal(e.okDisabled, false);
    assert.equal(e.note, "Shown as B♭");
  });
});

test("with the song shown transposed the entry shows and takes the chord as shown", { skip: skip }, function () {
  return inEditor([HELLO], async function (page) {
    await click(page, "transpose-up");
    await click(page, "transpose-up");
    await startChords(page);
    await selectLetter(page, 6);
    await page.key("Enter");
    assert.equal((await entryState(page)).value, "Bm", "Am shown two steps up");
    await typeInto(page, "E");
    await page.key("Enter");
    assert.deepEqual((await chordsShown(page))[1], [6, "w", "E"]);
    await click(page, "edit-save");
    await click(page, "transpose-reset");
    assert.deepEqual((await chordsShown(page))[1], [6, "w", "D"], "stored two steps down from what was typed");
  });
});

test("a second tap of a finger on the selected letter opens the entry", { skip: skip }, function () {
  return inEditor([HELLO], async function (page) {
    await startChords(page);
    var c = await point(page, 6, "chord");
    await page.touch.tap(c.x, c.y);
    assert.equal(await selectedLetter(page), 6);
    assert.equal((await entryState(page)).open, false, "the first tap only selects");
    await page.touch.tap(c.x, c.y);
    assert.equal((await entryState(page)).open, true);
    assert.equal((await entryState(page)).value, "Am");
    await page.pressKey("Escape");
    // A tap on a letter with no chord selects, and a second tap opens C.
    var l = await point(page, 2);
    await page.touch.tap(l.x, l.y);
    assert.equal(await selectedLetter(page), 2);
    await page.touch.tap(l.x, l.y);
    assert.equal((await entryState(page)).value, "C");
    // A drag is not a tap.
    await page.pressKey("Escape");
    await page.touch.drag(c, await point(page, 9));
    assert.equal((await entryState(page)).open, false);
  });
});

test("in a narrow window the entry is a sheet at the bottom and the letter stays in view", { skip: skip }, function () {
  var many = { title: "Long", text: Array.from({ length: 30 }, function (_, i) { return "Line number " + i; }).join("\n"),
    chords: [[0, "C"]] };
  return inEditor([many], async function (page) {
    await startChords(page);
    await page.eval("document.getElementById('sheet-scroll').scrollTop = 0");
    var last = await page.eval("(function () { var b = document.querySelectorAll('#sheet .char'); return Number(b[b.length - 3].dataset.songChar); })()");
    await page.eval("document.querySelector('#sheet .char[data-song-char=\"" + last + "\"]').scrollIntoView({ block: 'end' })");
    await selectLetter(page, last);
    await page.key("Enter");
    var g = await page.eval("(function () { var r = document.getElementById('chord-entry').getBoundingClientRect();" +
      "var l = document.querySelector('#sheet .char.selected').getBoundingClientRect();" +
      "return { left: r.left, right: r.right, bottom: r.bottom, top: r.top, w: innerWidth, h: innerHeight," +
      "letterBottom: l.bottom, letterTop: l.top, font: parseFloat(getComputedStyle(document.getElementById('chord-entry-field')).fontSize) }; })()");
    assert.equal(g.left, 0);
    assert.equal(g.right, g.w);
    assert.equal(g.bottom, g.h, "at the bottom of the window");
    assert.ok(g.letterBottom <= g.top, "the selected letter is above the entry, not under it");
    assert.ok(g.letterTop >= 0, "and on the screen");
    assert.ok(g.font >= 16, "16px or more, so a phone does not zoom in");
    await page.pressKey("Escape");
    assert.equal(await page.eval("getComputedStyle(document.getElementById('sheet-wrap')).marginBottom"), "0px");
  }, { viewport: { width: 375, height: 700 } });
});

function longSong(lines, chordsPerLine) {
  var text = "";
  var chords = [];
  for (var i = 0; i < lines; i++) {
    var line = "Line number " + i + " of a long song with words";
    for (var c = 0; c < chordsPerLine; c++) {
      chords.push([Array.from(text).length + c * 5, ["C", "Am", "F", "G7", "Dm"][c % 5]]);
    }
    text += line + (i < lines - 1 ? "\n" : "");
  }
  return { title: "Long", text: text, chords: chords };
}

test("holding a chord near the bottom edge scrolls the sheet and the chord follows", { skip: skip }, function () {
  return inEditor([longSong(60, 1)], async function (page) {
    await startChords(page);
    var a = await point(page, 0, "chord");
    var edge = await page.eval("(function () { var r = document.getElementById('sheet-scroll').getBoundingClientRect();" +
      "return r.bottom - 6; })()");
    await page.mouse.move(a.x, a.y);
    await page.mouse.down(a.x, a.y);
    await page.mouse.move(a.x + 10, a.y + 40, 1);
    await page.mouse.move(a.x + 10, edge, 1);
    await new Promise(function (r) { setTimeout(r, 800); });
    var scrolled = await page.eval("document.getElementById('sheet-scroll').scrollTop");
    assert.ok(scrolled > 100, "the sheet scrolled (" + scrolled + ")");
    var line = await page.eval("(function () { var c = document.querySelector('#sheet .chord.dragging');" +
      "return Array.prototype.indexOf.call(document.getElementById('sheet').children, c.parentNode.parentNode); })()");
    assert.ok(line > 5, "the chord went down with the sheet, to line " + line);
    await page.mouse.up(a.x + 10, edge);
    assert.equal(await page.eval("document.getElementById('sheet-wrap').classList.contains('dragging')"), false);
    // Nothing keeps scrolling after the release.
    var before = await page.eval("document.getElementById('sheet-scroll').scrollTop");
    await new Promise(function (r) { setTimeout(r, 300); });
    assert.equal(await page.eval("document.getElementById('sheet-scroll').scrollTop"), before);
  }, { viewport: { width: 1000, height: 500 } });
});

test("a drag in a song of 600 chords follows the pointer", { skip: skip }, function () {
  return inEditor([longSong(120, 5)], async function (page) {
    await startChords(page);
    assert.equal((await chordsShown(page)).length, 600);
    var a = await point(page, 0, "chord");
    await page.mouse.move(a.x, a.y);
    await page.mouse.down(a.x, a.y);
    // Moves the pointer along the first line and back, 200 times, as real events of the
    // page and with layout read after each, and measures what the handler and the
    // layout took. A real mouse sends about 60 a second, so under 16ms is a frame.
    var result = await page.eval("(function () {" +
      "var scroll = document.getElementById('sheet-scroll');" +
      "var boxes = Array.from(document.querySelectorAll('#sheet .line')[0].children);" +
      "var xs = boxes.map(function (b) { var r = b.getBoundingClientRect(); return (r.left + r.right) / 2; });" +
      "var y = boxes[0].getBoundingClientRect().top + 8; var times = [];" +
      "for (var i = 0; i < 200; i++) {" +
      "var x = xs[Math.min(xs.length - 1, i % 2 ? Math.floor(i / 8) + 1 : 1 + (i % 7))];" +
      "var t = performance.now();" +
      "scroll.dispatchEvent(new PointerEvent('pointermove', { bubbles: true, clientX: x, clientY: y, pointerId: 1, pointerType: 'mouse' }));" +
      "document.getElementById('sheet').getBoundingClientRect(); times.push(performance.now() - t); }" +
      "times.sort(function (p, q) { return p - q; });" +
      "return { median: times[100], p95: times[190], max: times[199] }; })()");
    await page.mouse.up(a.x, a.y);
    // The key detection that spells the chords runs again when the chord passes another
    // one (the order changes): about 100ms for 600 chords, the "worst". Moves that
    // come back to an order seen a moment ago are served from a cache.
    console.log("# 600 chords, a move of the pointer: median " + result.median.toFixed(2) + " ms, 95th percentile " +
      result.p95.toFixed(2) + " ms, worst " + result.max.toFixed(2) + " ms");
    assert.ok(result.median < 16, "half of the moves took under a frame (took " + result.median + ")");
    assert.ok(result.max < 600, "even the worst move took under 600ms (took " + result.max + ")");
  });
});

test("at 375px and 320px every toolbar button, Save and Discard are inside the window in Edit chords", { skip: skip }, function () {
  var check = async function (page) {
    await startChords(page);
    var out = await page.eval("(function () {" +
      "var bad = []; document.querySelectorAll('.toolbar button, .toolbar-actions button').forEach(function (b) {" +
      "if (b.offsetParent === null) { return; } var r = b.getBoundingClientRect();" +
      "if (r.left < 0 || r.right > innerWidth + 0.5) { bad.push(b.id + ' ' + r.left + ' ' + r.right); } });" +
      "return { bad: bad, scroll: document.documentElement.scrollWidth, width: innerWidth }; })()");
    assert.deepEqual(out.bad, []);
    assert.ok(out.scroll <= out.width, "the page does not scroll sideways");
    for (var id of ["chord-edit", "chord-delete", "chord-undo", "chord-redo", "edit-save", "edit-discard"]) {
      var r = await page.eval("(function () { var r = document.getElementById('" + id + "').getBoundingClientRect();" +
        "return { w: r.width, h: r.height }; })()");
      assert.ok(r.w >= 28 && r.h >= 28, id + " is big enough to tap (" + r.w + "x" + r.h + ")");
    }
  };
  return inEditor([HELLO], check, { viewport: { width: 375, height: 700 } })
    .then(function () { return inEditor([HELLO], check, { viewport: { width: 320, height: 600 } }); });
});

test("leaving Edit chords with chords changed asks first, and with nothing changed does not", { skip: skip }, function () {
  var other = { title: "Other", text: "Other song", chords: [] };
  return inEditor([HELLO, other], async function (page) {
    var asking = "document.getElementById('leave-confirm').open";
    // Nothing changed: Back leaves.
    await startChords(page);
    await selectLetter(page, 1);
    await click(page, "back");
    assert.equal(await page.eval(asking), false);
    await page.waitFor("document.getElementById('song-view').hidden", "the list");
    await page.eval("location.hash = '#/song/1'");
    await page.waitFor("!document.getElementById('song-view').hidden", "the song");
    // A chord moved and moved back by Undo: the same as the start, nothing to lose.
    await startChords(page);
    await dragChord(page, 6, 9);
    await click(page, "chord-undo");
    await page.eval("location.hash = '#/song/2'");
    await page.waitFor("document.getElementById('song-title').textContent === 'Other'", "song 2");
    assert.equal(await page.eval(asking), false);
    await page.eval("location.hash = '#/song/1'");
    await page.waitFor("document.getElementById('song-title').textContent === 'Hello'", "song 1");
    // A chord moved: Back and another song ask.
    await startChords(page);
    await dragChord(page, 6, 9);
    await click(page, "back");
    assert.equal(await page.eval(asking), true);
    await click(page, "leave-confirm-keep");
    assert.deepEqual((await chordsShown(page))[1], [9, "l", "Am"], "the draft is as it was");
    assert.equal(await page.eval("document.getElementById('sheet-wrap').classList.contains('chord-mode')"), true);
    await page.eval("location.hash = '#/song/2'");
    await page.waitFor(asking, "the question for another song");
    assert.equal(await page.eval("location.hash"), "#/song/1");
    await click(page, "leave-confirm-discard");
    await page.waitFor("document.getElementById('song-title').textContent === 'Other'", "song 2");
    assert.equal(await page.eval("document.getElementById('sheet-wrap').classList.contains('chord-mode')"), false);
    assert.equal(await page.eval("document.getElementById('chord-actions').hidden"), true);
    await page.eval("location.hash = '#/song/1'");
    await page.waitFor("document.getElementById('song-title').textContent === 'Hello'", "song 1");
    assert.deepEqual(await chordsShown(page), SHOWN, "the discarded move is gone");
    // After Save the song keeps the chords (with the note) and leaving does not ask.
    await startChords(page);
    await dragChord(page, 6, 9);
    await click(page, "edit-save");
    await click(page, "back");
    assert.equal(await page.eval(asking), false);
  });
});
