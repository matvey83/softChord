// The real viewer page in headless Chrome: the toolbar buttons, Escape, reset
// states, zoom and print wrapping. Skipped when Chrome is not installed.

const test = require("node:test");
const assert = require("node:assert/strict");
const helper = require("./browser_helper");

const skip = helper.findChrome() ? false : "Chrome is not installed (set CHROME_BIN)";

const LONG = "Lorem ipsum dolor sit amet ".repeat(8).trim();
const SONGS = [
  { title: "Short", text: "Hello world\nSecond line", chords: [[0, "C"], [6, "Am"], [12, "G"]] },
  { title: "Long line", text: LONG, chords: [[0, "C"], [40, "F"], [100, "G"], [150, "Am"]] },
];

async function openSong(page, id) {
  await page.eval("location.hash = '#/song/" + id + "'");
  await page.waitFor("!document.getElementById('song-view').hidden", "the song page");
}

function click(page, id) {
  return page.eval("document.getElementById('" + id + "').click()");
}

function state(page, id) {
  return page.eval("document.getElementById('" + id + "').disabled");
}

async function inSong(name, songs, run) {
  var page = await helper.openViewer(songs);
  try {
    await run(page);
  } finally {
    await page.close();
  }
}

test("Escape closes the notice dialog and keeps the song open", { skip: skip }, function () {
  return inSong("escape", SONGS, async function (page) {
    await openSong(page, 1);
    await click(page, "transpose-up");
    await page.eval("document.getElementById('notice').showModal()");
    assert.equal(await page.eval("document.getElementById('notice').open"), true);
    await page.pressKey("Escape");
    assert.equal(await page.eval("document.getElementById('notice').open"), false);
    // Still on the song, still transposed.
    assert.equal(await page.eval("location.hash"), "#/song/1");
    assert.equal(await page.eval("document.getElementById('song-view').hidden"), false);
    assert.equal(await state(page, "transpose-reset"), false);
    // A second Escape, with no dialog, leaves the song.
    await page.pressKey("Escape");
    await page.waitFor("document.getElementById('song-view').hidden", "leaving the song");
    assert.equal(await page.eval("location.hash"), "#/");
  });
});

test("Reset transpose and the notice follow the steps, a whole octave counts as none", { skip: skip }, function () {
  return inSong("reset", SONGS, async function (page) {
    await openSong(page, 1);
    var noteHidden = "document.getElementById('persist-note').hidden";
    assert.equal(await state(page, "transpose-reset"), true);
    assert.equal(await page.eval(noteHidden), true);
    await click(page, "transpose-up");
    assert.equal(await state(page, "transpose-reset"), false);
    assert.equal(await page.eval(noteHidden), false);
    // Up then down by the same amount is back at the opened key.
    await click(page, "transpose-down");
    assert.equal(await state(page, "transpose-reset"), true);
    assert.equal(await page.eval(noteHidden), true);
    // Twelve steps up shows the same chords: Reset dims and the notice goes.
    var opened = await page.eval("document.getElementById('sheet').textContent");
    for (var i = 0; i < 12; i++) { await click(page, "transpose-up"); }
    assert.equal(await page.eval("document.getElementById('sheet').textContent"), opened);
    assert.equal(await state(page, "transpose-reset"), true);
    assert.equal(await page.eval(noteHidden), true);
    await click(page, "transpose-up");
    assert.notEqual(await page.eval("document.getElementById('sheet').textContent"), opened);
    assert.equal(await state(page, "transpose-reset"), false);
    assert.equal(await page.eval(noteHidden), false);
    await click(page, "transpose-reset");
    assert.equal(await page.eval("document.getElementById('sheet').textContent"), opened);
    assert.equal(await state(page, "transpose-reset"), true);
    // Another song starts from its own opened key.
    await click(page, "transpose-up");
    await page.eval("location.hash = '#/'");
    await openSong(page, 2);
    assert.equal(await state(page, "transpose-reset"), true);
  });
});

test("zoom buttons change only the song area and stop at their limits", { skip: skip }, function () {
  return inSong("zoom", SONGS, async function (page) {
    await openSong(page, 1);
    var sheetSize = "parseFloat(getComputedStyle(document.getElementById('sheet')).fontSize)";
    var toolbarSize = "document.querySelector('.toolbar').getBoundingClientRect().height + ':' + " +
      "document.getElementById('zoom-in').getBoundingClientRect().width";
    var toolbarBefore = await page.eval(toolbarSize);
    assert.equal(await page.eval(sheetSize), 20);
    assert.equal(await state(page, "zoom-reset"), true);
    await click(page, "zoom-in");
    await click(page, "zoom-in");
    assert.equal(await page.eval(sheetSize), 24);
    assert.equal(await state(page, "zoom-reset"), false);
    assert.equal(await page.eval(toolbarSize), toolbarBefore, "the toolbar does not zoom");
    await click(page, "zoom-reset");
    assert.equal(await page.eval(sheetSize), 20);
    assert.equal(await state(page, "zoom-reset"), true);
    for (var i = 0; i < 30; i++) { await click(page, "zoom-out"); }
    assert.equal(await page.eval(sheetSize), 10);
    assert.equal(await state(page, "zoom-out"), true);
    assert.equal(await state(page, "zoom-in"), false);
    for (i = 0; i < 40; i++) { await click(page, "zoom-in"); }
    assert.equal(await page.eval(sheetSize), 60);
    assert.equal(await state(page, "zoom-in"), true);
    // The zoom is kept when another song opens.
    await page.eval("location.hash = '#/'");
    await openSong(page, 2);
    assert.equal(await page.eval(sheetSize), 60);
  });
});

test("a line longer than the page wraps when printed, chords stay over their letters", { skip: skip }, function () {
  return inSong("print", SONGS, async function (page) {
    await openSong(page, 2);
    await page.send("Emulation.setEmulatedMedia", { media: "print" });
    await page.send("Emulation.setDeviceMetricsOverride", {
      width: 700, height: 900, deviceScaleFactor: 1, mobile: false,
    });
    var measured = await page.eval("(function () {" +
      "var line = document.querySelector('#sheet .line');" +
      "var rows = new Set(Array.from(line.querySelectorAll('.char')).map(function (c) {" +
      "  return Math.round(c.getBoundingClientRect().top); }));" +
      "var box = line.getBoundingClientRect();" +
      "var chords = Array.from(line.querySelectorAll('.chord')).map(function (c) {" +
      "  var char = c.parentElement.getBoundingClientRect(), r = c.getBoundingClientRect();" +
      "  return { off: Math.abs((r.left + r.right) / 2 - (char.left + char.right) / 2)," +
      "           above: r.bottom <= char.top + 2, inside: r.left >= 0 && r.right <= window.innerWidth };" +
      "});" +
      "return { rows: rows.size, scroll: line.scrollWidth, width: box.width, chords: chords };" +
      "})()");
    assert.ok(measured.rows >= 2, "wrapped onto " + measured.rows + " rows");
    assert.ok(measured.scroll <= measured.width + 1, "nothing runs past the right edge");
    assert.equal(measured.chords.length, 4);
    measured.chords.forEach(function (chord) {
      assert.ok(chord.off < 1.5, "chord centred on its letter");
      assert.ok(chord.above, "chord above its letter");
      assert.ok(chord.inside, "chord inside the page");
    });
    // The real print path also works and makes a PDF.
    var pdf = await page.printToPDF();
    assert.equal(pdf.subarray(0, 4).toString(), "%PDF");
  });
});

test("text that is not a chord shows in red, cut to 7 characters, and stays put when transposed", { skip: skip }, function () {
  var songs = [{
    title: "Odd",
    text: "Hello world again",
    chords: [[0, "C"], [6, "abcdefghij"], [12, "Пожалуйста"]],
  }];
  return inSong("unrecognized", songs, async function (page) {
    await openSong(page, 1);
    var read = "Array.from(document.querySelectorAll('#sheet .chord')).map(function (c) {" +
      "return { text: c.textContent, red: c.classList.contains('unrecognized')," +
      " color: getComputedStyle(c).color, style: getComputedStyle(c).fontStyle }; })";
    var chords = await page.eval(read);
    assert.deepEqual(chords.map(function (c) { return c.text; }), ["C", "abcdefg", "Пожалуй"]);
    assert.deepEqual(chords.map(function (c) { return c.red; }), [false, true, true]);
    assert.equal(chords[0].color, "rgb(0, 0, 255)");
    assert.equal(chords[1].color, "rgb(255, 0, 0)");

    await click(page, "transpose-up");
    chords = await page.eval(read);
    assert.deepEqual(chords.map(function (c) { return c.text; }), ["D♭", "abcdefg", "Пожалуй"]);

    // In print the text is also italic, since red may print as grey.
    await page.send("Emulation.setEmulatedMedia", { media: "print" });
    chords = await page.eval(read);
    assert.equal(chords[1].style, "italic");
    assert.equal(chords[0].style, "normal");
  });
});

test("Reset stays dimmed for a song with only text that is not a chord", { skip: skip }, function () {
  var songs = [{ title: "Only odd", text: "Hello world", chords: [[0, "N.C."], [6, "asdf"]] }];
  return inSong("only unrecognized", songs, async function (page) {
    await openSong(page, 1);
    assert.equal(await state(page, "transpose-reset"), true);
    await click(page, "transpose-up");
    assert.equal(await state(page, "transpose-reset"), true);
    assert.equal(await page.eval("document.getElementById('persist-note').hidden"), true);
    var texts = await page.eval(
      "Array.from(document.querySelectorAll('#sheet .chord')).map(function (c) { return c.textContent; })");
    assert.deepEqual(texts, ["N.C.", "asdf"]);
  });
});

test("printed pages keep a white border even when the browser's margins are None", { skip: skip }, function () {
  return inSong("print margins", SONGS, async function (page) {
    await openSong(page, 1);
    // "Margins: None" makes the browser ignore @page, so take it away here too.
    await page.eval("var s = document.createElement('style');" +
      "s.textContent = '@page { margin: 0 !important }'; document.head.appendChild(s); 1");
    await page.send("Emulation.setEmulatedMedia", { media: "print" });
    await page.send("Emulation.setDeviceMetricsOverride", {
      width: 700, height: 900, deviceScaleFactor: 1, mobile: false,
    });
    var mm = 96 / 25.4;
    var box = await page.eval("(function () {" +
      "var t = document.getElementById('song-title').getBoundingClientRect();" +
      "var l = document.querySelector('#sheet .line').getBoundingClientRect();" +
      "var m = getComputedStyle(document.querySelector('main'));" +
      "return { titleTop: t.top, titleLeft: t.left, lineLeft: l.left, right: window.innerWidth - l.right," +
      "         clone: m.boxDecorationBreak, pb: m.paddingBottom };" +
      "})()");
    assert.ok(box.titleTop >= 9 * mm, "title is " + box.titleTop + "px from the top edge");
    assert.ok(box.titleLeft >= 9 * mm, "title is " + box.titleLeft + "px from the left edge");
    assert.ok(box.lineLeft >= 9 * mm, "lyrics are " + box.lineLeft + "px from the left edge");
    assert.ok(box.right >= 9 * mm, "lyrics end " + box.right + "px from the right edge");
    // The padding is repeated at the top and bottom of every page, not only the first.
    assert.equal(box.clone, "clone");
    assert.ok(parseFloat(box.pb) >= 9 * mm, "bottom padding " + box.pb);
  });
});

test("the page still works when the toolbar buttons are missing from index.html", { skip: skip }, async function () {
  var page = await helper.openViewer(SONGS, {
    html: function (html) {
      return html.replace(/<div class="toolbar-actions">[\s\S]*?<\/header>/, "</header>");
    },
  });
  try {
    await openSong(page, 1);
    assert.equal(await page.eval("document.getElementById('song-title').textContent"), "Short");
    assert.ok((await page.eval("document.querySelectorAll('#sheet .char').length")) > 5);
    await page.pressKey("Escape");
    await page.waitFor("document.getElementById('song-view').hidden", "leaving the song");
    assert.deepEqual(page.errors, []);
  } finally {
    await page.close();
  }
});
