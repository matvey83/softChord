// Songbook header and menu (Phase 1): the list header, My songbooks, opening a
// file in memory, the unsaved-edit prompt, and the not-available messages.
// No repository .songbook is read. Skipped when Chrome is not installed.

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const helper = require("./browser_helper");
const initSqlJs = require("../sql-wasm.js");

const skip = helper.skipUnlessBrowser();
const DEMO = ["Short", "Long line", "Short too", "Wide"];

const SONGS = [
  { title: "Short", text: "Hello world\nSecond line", chords: [[0, "C"], [6, "Am"]] },
  { title: "Long line", text: "La la la la", chords: [[0, "C"]] },
  { title: "Short too", text: "La la la", chords: [[0, "D"]] },
  { title: "Wide", text: "Wide enough", chords: [[0, "Am"]] },
];

function click(page, id) {
  return page.eval("document.getElementById('" + id + "').click()");
}

function titlesExpr() {
  return "Array.from(document.querySelectorAll('#song-list button')).map(function (b) { return b.textContent; })";
}

function noticeMessage(page) {
  return page.eval("document.getElementById('notice-message').textContent");
}

async function openMenu(page) {
  await click(page, "songbook-menu-button");
  await page.waitFor("!document.getElementById('songbook-menu').hidden", "the songbook menu");
}

async function chooseFile(page, filePath) {
  var doc = await page.send("DOM.getDocument", {});
  var found = await page.send("DOM.querySelector", {
    nodeId: doc.root.nodeId,
    selector: "#songbook-file",
  });
  if (!found.nodeId) {
    throw new Error("the songbook file input is missing");
  }
  await page.send("DOM.setFileInputFiles", { nodeId: found.nodeId, files: [filePath] });
}

async function waitForTitle(page, title) {
  await page.waitFor(
    "Array.from(document.querySelectorAll('#song-list button')).some(function (b) { return b.textContent === " +
    JSON.stringify(title) + "; })",
    "the song \"" + title + "\"");
}

function armFileClicks(page) {
  return page.eval("window.__fileClicks = 0;" +
    "document.getElementById('songbook-file').addEventListener('click', function () { window.__fileClicks++; });");
}

function armNetwork(page) {
  return page.eval("(function () {" +
    "window.__net = [];" +
    "var orig = window.fetch;" +
    "window.fetch = function () { window.__net.push(String(arguments[0])); return orig.apply(this, arguments); };" +
    "var open = XMLHttpRequest.prototype.open;" +
    "XMLHttpRequest.prototype.open = function () { window.__net.push(String(arguments[1])); return open.apply(this, arguments); };" +
    "if (navigator.sendBeacon) {" +
    "  var beacon = navigator.sendBeacon.bind(navigator);" +
    "  navigator.sendBeacon = function (url) { window.__net.push(String(url)); return beacon(url); };" +
    "}" +
    "})()");
}

async function writeBytes(dir, name, bytes) {
  var file = path.join(dir, name);
  fs.writeFileSync(file, bytes);
  return file;
}

async function newerFormatFile(dir) {
  var SQL = await initSqlJs({
    locateFile: function (file) { return path.join(__dirname, "..", file); },
  });
  var db = new SQL.Database();
  db.run("PRAGMA user_version = 3");
  var file = await writeBytes(dir, "newer.songbook", Buffer.from(db.export()));
  db.close();
  return file;
}

test("the song list header and menu show the open songbook, and the song page does not", { skip: skip }, async function () {
  var page = await helper.openViewer(SONGS);
  try {
    assert.equal(await page.eval("document.getElementById('songbook-name').textContent"), "zvuki_neba");
    assert.equal(await page.eval("document.getElementById('songbook-indicator').textContent"), "Not saved");
    assert.equal(await page.eval("getComputedStyle(document.getElementById('songbook-indicator')).color"), "rgb(142, 142, 147)");
    assert.equal(await page.eval("document.getElementById('sign-in').textContent"), "Sign in");
    var place = await page.eval("(function () {" +
      "var header = document.getElementById('songbook-header').getBoundingClientRect();" +
      "var search = document.querySelector('.search-bar').getBoundingClientRect();" +
      "var sign = document.getElementById('sign-in').getBoundingClientRect();" +
      "var name = document.getElementById('songbook-name').getBoundingClientRect();" +
      "return { headerAboveSearch: header.bottom <= search.top + 1, signRight: sign.left >= name.right," +
      "  nameFits: document.getElementById('songbook-name').scrollWidth <= document.getElementById('songbook-name').clientWidth + 1 };" +
      "})()");
    assert.equal(place.headerAboveSearch, true, "Search stays below the header");
    assert.equal(place.signRight, true, "Sign in stays on the right");
    assert.equal(place.nameFits, true, "the demo name fits at a desktop width");

    await page.eval("document.getElementById('search').value = 'Short';" +
      "document.getElementById('search').dispatchEvent(new Event('input'));");
    var filtered = await page.eval(titlesExpr());
    assert.deepEqual(filtered.filter(function (title) { return title.indexOf("Short") === 0; }).length, filtered.length);
    assert.ok(filtered.indexOf("Short") >= 0);
    assert.equal(filtered.indexOf("Long line"), -1);
    await page.eval("document.getElementById('search').value = '';" +
      "document.getElementById('search').dispatchEvent(new Event('input'));");
    assert.deepEqual(await page.eval(titlesExpr()), DEMO);

    await openMenu(page);
    assert.equal(await page.eval("document.getElementById('songbook-menu-button').getAttribute('aria-expanded')"), "true");
    assert.equal(await page.eval("document.getElementById('songbook-menu-label').textContent"), "My songbooks");
    assert.deepEqual(await page.eval("Array.from(document.querySelectorAll('#songbook-menu button')).map(function (b) { return b.getAttribute('data-action') || b.querySelector('.menu-item-label').textContent; })"),
      ["zvuki_neba", "open-file", "download", "rename", "delete", "share"]);
    assert.equal(await page.eval("document.querySelector('#songbook-menu button[data-action=open-file]').textContent"), "Open Songbook File…");
    assert.equal(await page.eval("document.querySelector('#songbook-menu-list button').getAttribute('aria-checked')"), "true");
    assert.equal(await page.eval("document.querySelector('#songbook-menu .menu-check').textContent"), "\u2713");
    var order = await page.eval("Array.from(document.getElementById('songbook-menu').children).map(function (el) { return el.getAttribute('data-action') || el.id || el.className; })");
    var openAt = order.indexOf("open-file");
    var downloadAt = order.indexOf("download");
    assert.ok(openAt >= 0 && downloadAt > openAt);
    assert.equal(order[openAt + 1], "menu-sep");
    await page.pressKey("Escape");
    assert.equal(await page.eval("document.getElementById('songbook-menu').hidden"), true);

    await page.eval("location.hash = '#/song/1'");
    await page.waitFor("!document.getElementById('song-view').hidden", "the song page");
    assert.equal(await page.eval("document.getElementById('songbook-header').offsetParent === null"), true, "the header is on the song list only");
    assert.equal(await page.eval("document.getElementById('song-title').textContent"), "Short");
    await click(page, "back");
    await page.waitFor("document.getElementById('song-view').hidden", "the song list");
    assert.equal(await page.eval("document.getElementById('songbook-header').offsetParent === null"), false);

    await page.send("Emulation.setEmulatedMedia", { media: "print" });
    assert.equal(await page.eval("getComputedStyle(document.getElementById('songbook-header')).display"), "none");
    assert.equal(await page.eval("getComputedStyle(document.getElementById('songbook-menu')).display"), "none");
    assert.deepEqual(page.errors, []);
  } finally {
    await page.close();
  }
});

test("opening a songbook file keeps it for this visit, and a bad file leaves the current one open", { skip: skip }, async function () {
  var dir = fs.mkdtempSync(path.join(os.tmpdir(), "softchord-songbook-"));
  var page = await helper.openViewer(SONGS);
  try {
    var valid = await writeBytes(dir, "opened-from-this-session.songbook",
      await helper.songbookBytes([{ title: "Filed", text: "From the file", chords: [[0, "G"]] }]));
    var invalid = await writeBytes(dir, "notes.songbook", Buffer.from("this is not a songbook\n"));
    var newer = await newerFormatFile(dir);
    var older = await writeBytes(dir, "older.songbook", await (async function () {
      var SQL = await initSqlJs({
        locateFile: function (file) { return path.join(__dirname, "..", file); },
      });
      var db = new SQL.Database();
      var bytes = Buffer.from(db.export());
      db.close();
      return bytes;
    })());
    var huge = path.join(dir, "huge.songbook");
    var fd = fs.openSync(huge, "w");
    fs.ftruncateSync(fd, 50 * 1024 * 1024 + 1);
    fs.closeSync(fd);

    await armNetwork(page);
    await openMenu(page);
    await page.eval("document.querySelector('#songbook-menu button[data-action=open-file]').click()");
    assert.equal(await page.eval("document.getElementById('leave-confirm').open"), false, "a clean list does not ask");
    await chooseFile(page, valid);
    await waitForTitle(page, "Filed");
    assert.deepEqual(await page.eval(titlesExpr()), ["Filed"]);
    assert.equal(await page.eval("document.getElementById('songbook-name').textContent"), "opened-from-this-session");
    assert.equal(await page.eval("document.getElementById('songbook-indicator').textContent"), "Not saved");
    assert.deepEqual(await page.eval("window.__net"), [], "opening a file does not fetch");

    await openMenu(page);
    var rows = await page.eval("Array.from(document.querySelectorAll('#songbook-menu-list button')).map(function (b) {" +
      "return { name: b.querySelector('.menu-item-label').textContent, checked: b.getAttribute('aria-checked') }; })");
    assert.deepEqual(rows, [
      { name: "zvuki_neba", checked: "false" },
      { name: "opened-from-this-session", checked: "true" },
    ]);

    await chooseFile(page, invalid);
    await page.waitFor("document.getElementById('notice').open", "the invalid-file message");
    assert.equal(await noticeMessage(page), "\u201cnotes.songbook\u201d isn't a softChord songbook.");
    assert.equal(await page.eval("document.querySelectorAll('#notice button').length"), 1);
    assert.equal(await page.eval("document.querySelector('#notice button').textContent"), "OK");
    await page.eval("document.querySelector('#notice button').click()");
    assert.deepEqual(await page.eval(titlesExpr()), ["Filed"]);
    assert.equal(await page.eval("document.getElementById('songbook-name').textContent"), "opened-from-this-session");

    await chooseFile(page, newer);
    await page.waitFor("document.getElementById('notice').open", "the format message");
    assert.equal(await noticeMessage(page), "This songbook is a newer format (version 3). Update this viewer.");
    await page.eval("document.querySelector('#notice button').click()");
    assert.deepEqual(await page.eval(titlesExpr()), ["Filed"]);

    await chooseFile(page, older);
    await page.waitFor("document.getElementById('notice').open", "the old-format message");
    assert.equal(await noticeMessage(page),
      "This songbook is an old format. Update SoftChord on your Mac, open the songbook there to convert it, then copy it here again.");
    await page.eval("document.querySelector('#notice button').click()");
    assert.deepEqual(await page.eval(titlesExpr()), ["Filed"]);

    await chooseFile(page, huge);
    await page.waitFor("document.getElementById('notice').open", "the too-large message");
    assert.equal(await noticeMessage(page),
      "This songbook is too large to open here. Open it in softChord on your computer.");
    await page.eval("document.querySelector('#notice button').click()");
    assert.deepEqual(await page.eval(titlesExpr()), ["Filed"]);
    assert.equal(await page.eval("document.getElementById('songbook-name').textContent"), "opened-from-this-session");

    await page.eval("document.getElementById('search').value = 'zzz'");
    await openMenu(page);
    await page.eval("Array.from(document.querySelectorAll('#songbook-menu-list button')).find(function (b) {" +
      "return b.querySelector('.menu-item-label').textContent === 'zvuki_neba'; }).click()");
    await waitForTitle(page, "Short");
    assert.equal(await page.eval("document.getElementById('search').value"), "", "a switch clears the search");
    assert.deepEqual(await page.eval(titlesExpr()), DEMO);
    assert.equal(await page.eval("document.getElementById('songbook-name').textContent"), "zvuki_neba");
    assert.deepEqual(await page.eval("window.__net"), [], "switching back to the demo does not fetch");

    await page.send("Emulation.setDeviceMetricsOverride", {
      width: 320, height: 700, deviceScaleFactor: 1, mobile: false,
    });
    await openMenu(page);
    await page.eval("Array.from(document.querySelectorAll('#songbook-menu-list button')).find(function (b) {" +
      "return b.querySelector('.menu-item-label').textContent === 'opened-from-this-session'; }).click()");
    await waitForTitle(page, "Filed");
    var narrow = await page.eval("(function () {" +
      "function box(el) { var r = el.getBoundingClientRect(); return { left: r.left, right: r.right, width: r.width }; }" +
      "var name = document.getElementById('songbook-name');" +
      "var caret = document.querySelector('.songbook-caret');" +
      "var indicator = document.getElementById('songbook-indicator');" +
      "var sign = document.getElementById('sign-in');" +
      "var width = window.innerWidth;" +
      "return { truncated: name.scrollWidth > name.clientWidth + 1, caret: box(caret), indicator: box(indicator)," +
      "  sign: box(sign), width: width, indicatorText: indicator.textContent, signText: sign.textContent };" +
      "})()");
    assert.equal(narrow.truncated, true, "the name truncates first");
    assert.equal(narrow.indicatorText, "Not saved");
    assert.equal(narrow.signText, "Sign in");
    assert.ok(narrow.caret.width > 4 && narrow.caret.right <= narrow.width + 1, "the arrow stays on screen");
    assert.ok(narrow.indicator.width > 20 && narrow.indicator.right <= narrow.width + 1, "Not saved stays on screen");
    assert.ok(narrow.sign.width > 20 && narrow.sign.right <= narrow.width + 1, "Sign in stays on screen");
    assert.ok(narrow.caret.right <= narrow.indicator.left + 1);
    assert.ok(narrow.indicator.right <= narrow.sign.left + 1);

    await page.eval("location.reload()");
    var reloaded = false;
    for (var i = 0; i < 50; i++) {
      try {
        reloaded = await page.eval("document.getElementById('songbook-name') &&" +
          " document.getElementById('songbook-name').textContent === 'zvuki_neba' &&" +
          " document.querySelectorAll('#song-list button').length === 4");
      } catch (error) {
        reloaded = false;
      }
      if (reloaded) {
        break;
      }
      await new Promise(function (r) { setTimeout(r, 100); });
    }
    assert.equal(reloaded, true, "reload shows the demo again");
    await openMenu(page);
    assert.deepEqual(await page.eval("Array.from(document.querySelectorAll('#songbook-menu-list .menu-item-label')).map(function (el) { return el.textContent; })"),
      ["zvuki_neba"]);
    assert.deepEqual(page.errors, []);
  } finally {
    await page.close();
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("switching songbooks or opening a file asks while a song has unsaved edits, and Cancel stays", { skip: skip }, async function () {
  var dir = fs.mkdtempSync(path.join(os.tmpdir(), "softchord-songbook-"));
  var page = await helper.openViewer(SONGS);
  try {
    var valid = await writeBytes(dir, "other.songbook",
      await helper.songbookBytes([{ title: "Filed", text: "From the file", chords: [[0, "G"]] }]));
    var invalid = await writeBytes(dir, "notes.songbook", Buffer.from("not a database"));
    await armFileClicks(page);

    await page.eval("location.hash = '#/song/1'");
    await page.waitFor("!document.getElementById('song-view').hidden", "the song");
    await click(page, "transpose-up");
    await page.waitFor("!document.getElementById('edit-actions').hidden", "the dirty draft");

    await openMenu(page);
    await page.eval("document.querySelector('#songbook-menu button[data-action=open-file]').click()");
    await page.waitFor("document.getElementById('leave-confirm').open", "the prompt before the file picker");
    assert.equal(await page.eval("window.__fileClicks"), 0, "Cancel is still available, so the picker has not opened");
    assert.equal(await page.eval("document.getElementById('leave-confirm-save').textContent"), "Save");
    assert.equal(await page.eval("document.getElementById('leave-confirm-discard').textContent"), "Don\u2019t Save");
    assert.equal(await page.eval("document.getElementById('leave-confirm-keep').textContent"), "Cancel");
    await click(page, "leave-confirm-keep");
    assert.equal(await page.eval("document.getElementById('leave-confirm').open"), false);
    assert.equal(await page.eval("window.__fileClicks"), 0);
    assert.equal(await page.eval("location.hash"), "#/song/1");
    assert.equal(await page.eval("document.getElementById('edit-actions').hidden"), false);
    assert.equal(await page.eval("document.getElementById('songbook-name').textContent"), "zvuki_neba");

    await openMenu(page);
    await page.eval("document.querySelector('#songbook-menu button[data-action=open-file]').click()");
    await page.waitFor("document.getElementById('leave-confirm').open", "the prompt again");
    await click(page, "leave-confirm-discard");
    assert.equal(await page.eval("window.__fileClicks"), 1);
    await chooseFile(page, invalid);
    await page.waitFor("document.getElementById('notice').open", "the invalid-file message");
    assert.equal(await noticeMessage(page), "\u201cnotes.songbook\u201d isn't a softChord songbook.");
    assert.equal(await page.eval("location.hash"), "#/song/1", "a bad file keeps the current songbook");
    assert.equal(await page.eval("document.getElementById('songbook-name').textContent"), "zvuki_neba");
    assert.equal(await page.eval("document.getElementById('edit-actions').hidden"), false, "the failed open keeps the unsaved edit");
    await page.eval("document.querySelector('#notice button').click()");

    await openMenu(page);
    await page.eval("document.querySelector('#songbook-menu button[data-action=open-file]').click()");
    await page.waitFor("document.getElementById('leave-confirm').open", "the prompt before a good file");
    await click(page, "leave-confirm-save");
    await chooseFile(page, valid);
    await waitForTitle(page, "Filed");
    assert.equal(await page.eval("document.getElementById('song-view').hidden"), true);
    assert.equal(await page.eval("document.getElementById('songbook-name').textContent"), "other");
    await page.eval("location.hash = '#/song/1'");
    await page.waitFor("!document.getElementById('song-view').hidden", "the filed song");
    assert.equal(await page.eval("document.getElementById('edit-actions').hidden"), true, "the previous songbook's edits were dropped");
    assert.equal(await page.eval("document.getElementById('transpose-reset').disabled"), true);

    await click(page, "transpose-up");
    await page.waitFor("!document.getElementById('edit-actions').hidden", "a new dirty draft");
    await openMenu(page);
    await page.eval("Array.from(document.querySelectorAll('#songbook-menu-list button')).find(function (b) {" +
      "return b.querySelector('.menu-item-label').textContent === 'zvuki_neba'; }).click()");
    await page.waitFor("document.getElementById('leave-confirm').open", "the prompt before switching");
    await click(page, "leave-confirm-keep");
    assert.equal(await page.eval("location.hash"), "#/song/1");
    assert.equal(await page.eval("document.getElementById('songbook-name').textContent"), "other");
    assert.equal(await page.eval("document.getElementById('edit-actions').hidden"), false);

    await openMenu(page);
    await page.eval("Array.from(document.querySelectorAll('#songbook-menu-list button')).find(function (b) {" +
      "return b.querySelector('.menu-item-label').textContent === 'zvuki_neba'; }).click()");
    await page.waitFor("document.getElementById('leave-confirm').open", "the prompt before Don't Save");
    await click(page, "leave-confirm-discard");
    await waitForTitle(page, "Short");
    assert.deepEqual(await page.eval(titlesExpr()), DEMO);
    assert.equal(await page.eval("document.getElementById('songbook-name').textContent"), "zvuki_neba");
    assert.equal(await page.eval("document.getElementById('leave-confirm').open"), false);
    assert.deepEqual(page.errors, []);
  } finally {
    await page.close();
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("Save on a menu switch drops the edit", { skip: skip }, async function () {
  var dir = fs.mkdtempSync(path.join(os.tmpdir(), "softchord-songbook-"));
  var page = await helper.openViewer(SONGS);
  try {
    var other = await writeBytes(dir, "other.songbook",
      await helper.songbookBytes([{ title: "Filed", text: "From the file", chords: [[0, "G"]] }]));
    await openMenu(page);
    await page.eval("document.querySelector('#songbook-menu button[data-action=open-file]').click()");
    await chooseFile(page, other);
    await waitForTitle(page, "Filed");
    await page.eval("document.querySelector('#song-list button').click()");
    await page.waitFor("!document.getElementById('song-view').hidden", "the filed song");
    await click(page, "transpose-up");
    await page.waitFor("!document.getElementById('edit-actions').hidden", "a dirty draft");
    await openMenu(page);
    await page.eval("Array.from(document.querySelectorAll('#songbook-menu-list button')).find(function (b) {" +
      "return b.querySelector('.menu-item-label').textContent === 'zvuki_neba'; }).click()");
    await page.waitFor("document.getElementById('leave-confirm').open", "Save before switching");
    await click(page, "leave-confirm-save");
    await waitForTitle(page, "Short");
    assert.equal(await page.eval("document.getElementById('song-view').hidden"), true);
    assert.equal(await page.eval("document.getElementById('songbook-name').textContent"), "zvuki_neba");
    assert.equal(await page.eval("location.hash"), "#/");

    await openMenu(page);
    await page.eval("Array.from(document.querySelectorAll('#songbook-menu-list button')).find(function (b) {" +
      "return b.querySelector('.menu-item-label').textContent === 'other'; }).click()");
    await waitForTitle(page, "Filed");
    await page.eval("document.querySelector('#song-list button').click()");
    await page.waitFor("!document.getElementById('song-view').hidden", "the filed song again");
    assert.equal(await page.eval("document.getElementById('edit-actions').hidden"), true, "Save did not keep the edit in the old songbook");
    assert.equal(await page.eval("document.getElementById('transpose-reset').disabled"), true);
    assert.equal(await page.eval("document.getElementById('song-title').textContent"), "Filed");
    assert.deepEqual(page.errors, []);
  } finally {
    await page.close();
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("Back after a switch does not open a song from the previous songbook", { skip: skip }, async function () {
  var dir = fs.mkdtempSync(path.join(os.tmpdir(), "softchord-songbook-"));
  var page = await helper.openViewer(SONGS);
  try {
    var other = await writeBytes(dir, "other.songbook",
      await helper.songbookBytes([{ title: "Filed", text: "From the file", chords: [[0, "G"]] }]));
    await page.eval("document.querySelector('#song-list button').click()");
    await page.waitFor("location.hash === '#/e/0/song/1'", "the demo song route");
    await click(page, "back");
    await page.waitFor("location.hash === '#/'", "back on the list");
    await openMenu(page);
    await page.eval("document.querySelector('#songbook-menu button[data-action=open-file]').click()");
    await chooseFile(page, other);
    await waitForTitle(page, "Filed");
    assert.equal(await page.eval("location.hash"), "#/");
    await page.eval("window.__backs = 0; window.addEventListener('popstate', function () { window.__backs++; });");
    await page.eval("history.back()");
    await page.waitFor("window.__backs > 0 && location.hash === '#/' && document.getElementById('song-view').hidden",
      "Back to stay on the new songbook's list");
    assert.equal(await page.eval("document.getElementById('songbook-name').textContent"), "other");
    assert.deepEqual(await page.eval(titlesExpr()), ["Filed"]);
    assert.deepEqual(page.errors, []);
  } finally {
    await page.close();
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("cancelling the file picker after Don't Save keeps the unsaved edit", { skip: skip }, async function () {
  var page = await helper.openViewer(SONGS);
  try {
    await armFileClicks(page);
    await page.eval("location.hash = '#/song/1'");
    await page.waitFor("!document.getElementById('song-view').hidden", "the song");
    await click(page, "transpose-up");
    await page.waitFor("!document.getElementById('edit-actions').hidden", "a dirty draft");
    await openMenu(page);
    await page.eval("document.querySelector('#songbook-menu button[data-action=open-file]').click()");
    await page.waitFor("document.getElementById('leave-confirm').open", "the prompt");
    await click(page, "leave-confirm-discard");
    assert.equal(await page.eval("window.__fileClicks"), 1, "Don't Save opens the picker");
    assert.equal(await page.eval("location.hash"), "#/song/1");
    assert.equal(await page.eval("document.getElementById('songbook-name').textContent"), "zvuki_neba");
    assert.equal(await page.eval("document.getElementById('edit-actions').hidden"), false, "cancelling the picker keeps the edit");
    assert.equal(await page.eval("document.getElementById('song-view').hidden"), false);
    assert.deepEqual(page.errors, []);
  } finally {
    await page.close();
  }
});

test("Sign in and the account items explain that they are not available, and do not fetch", { skip: skip }, async function () {
  var page = await helper.openViewer(SONGS);
  try {
    await armNetwork(page);
    var cases = [
      ["sign-in", "Sign-in isn't available yet", "softChord accounts are coming in a later update."],
      ["download", "Not available yet", "Saving songbooks from this app is coming in a later update."],
      ["rename", "Not available yet", "Renaming and deleting songbooks comes with softChord accounts in a later update."],
      ["delete", "Not available yet", "Renaming and deleting songbooks comes with softChord accounts in a later update."],
      ["share", "Sharing isn't available yet", "Sharing needs a softChord account, which is coming in a later update."],
    ];
    for (var i = 0; i < cases.length; i++) {
      var item = cases[i];
      if (item[0] === "sign-in") {
        await click(page, "sign-in");
      } else {
        await openMenu(page);
        await page.eval("document.querySelector('#songbook-menu button[data-action=" + JSON.stringify(item[0]) + "]').click()");
      }
      await page.waitFor("document.getElementById('notice').open", item[0]);
      assert.equal(await page.eval("document.getElementById('notice-title').textContent"), item[1]);
      assert.equal(await noticeMessage(page), item[2]);
      assert.equal(await page.eval("document.querySelectorAll('#notice button').length"), 1);
      assert.equal(await page.eval("document.querySelector('#notice button').textContent"), "OK");
      assert.equal(await page.eval("document.querySelector('#songbook-menu button[data-action=" +
        JSON.stringify(item[0] === "sign-in" ? "share" : item[0]) + "]').disabled"), false);
      await page.eval("document.querySelector('#notice button').click()");
      await page.waitFor("!document.getElementById('notice').open", "the message to close");
    }
    assert.deepEqual(await page.eval("window.__net"), []);
    assert.deepEqual(await page.eval(titlesExpr()), DEMO);
    assert.deepEqual(page.errors, []);
  } finally {
    await page.close();
  }
});
