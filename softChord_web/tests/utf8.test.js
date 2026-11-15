// Copied and exported text is UTF-8. The same sample (Cyrillic, accented Latin,
// emoji) is used by the desktop (src/test_song.py) and iPhone
// (SoftChordTests/Utf8Tests.swift) tests. The copy buttons in the real page are
// tested in utf8.browser.test.js. src/test_utf8_guards.py runs the same source
// scan from the desktop suite.

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const SongText = require("../softchord_text");
const SheetImage = require("../softchord_sheet_image");
const Songbook = require("../songbook");
const initSqlJs = require("../sql-wasm.js");

const SAMPLE = "Привет café 🎵";
const WEB_DIR = path.join(__dirname, "..");

function chord(character, note, type) {
  return {
    characterNum: character,
    noteId: note,
    chordTypeId: type || 0,
    bassNoteId: -1,
    marker: "",
    inParentheses: false,
  };
}

function utf8RoundTrip(text) {
  var bytes = new TextEncoder().encode(text);
  return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
}

test("copied song text keeps Cyrillic, accents and emoji through UTF-8", function () {
  var text = SAMPLE + "\n" + SAMPLE;
  var chords = [chord(0, 9, 1), chord(7, 0)];
  var plain = SongText.render(text, chords, false);
  assert.equal(plain, SAMPLE + "\r\n" + SAMPLE);
  assert.equal(utf8RoundTrip(plain), plain);
  var withChords = SongText.render(text, chords, true);
  assert.ok(withChords.endsWith(SAMPLE), withChords);
  assert.equal(utf8RoundTrip(withChords), withChords);
  assert.ok(!withChords.includes("?") && !withChords.includes("�"), withChords);
});

test("songbook text is read as UTF-8 and copies out unchanged", async function () {
  var SQL = await initSqlJs({
    locateFile: function (file) { return path.join(WEB_DIR, file); },
  });
  var db = new SQL.Database();
  db.run(fs.readFileSync(path.join(WEB_DIR, "..", "src", "songbook.sql"), "utf8"));
  db.run("INSERT INTO songs (id, uuid, text, title, updated_at) VALUES (?, ?, ?, ?, 1700000000)",
    [1, "00000000-0000-4000-8000-000000000001", SAMPLE + "\n" + SAMPLE, SAMPLE]);
  db.run("INSERT INTO song_chord_link (song_id, character_num, chord) VALUES (1, 0, 'Am')");
  var bytes = db.export();
  db.close();

  Songbook.openBytes(SQL, bytes);
  assert.deepEqual(Songbook.titles(), [{ id: 1, title: SAMPLE }]);
  assert.equal(Songbook.source(1).text, SAMPLE + "\n" + SAMPLE);
  assert.equal(Songbook.songText(1, false), SAMPLE + "\r\n" + SAMPLE);
  assert.equal(Songbook.songText(1, true), "Am\r\n" + SAMPLE + "\r\n" + SAMPLE);
});

test("the saved picture keeps a Unicode title in its file name", function () {
  assert.equal(SheetImage.fileName(SAMPLE), SAMPLE + ".png");
  assert.equal(SheetImage.fileName("a/b: " + SAMPLE), "a b " + SAMPLE + ".png");
});

test("every page declares UTF-8 in its first 1024 bytes", function () {
  var pages = fs.readdirSync(WEB_DIR).filter(function (name) { return name.endsWith(".html"); });
  assert.ok(pages.length > 0);
  pages.forEach(function (name) {
    var head = fs.readFileSync(path.join(WEB_DIR, name)).subarray(0, 1024).toString("latin1");
    assert.match(head, /<meta\s+charset=["']?utf-8["']?\s*\/?>/i,
      name + ": add <meta charset=\"utf-8\"> near the top of <head>");
  });
});

// The full scan (Blob/File types, data: URLs, text MIME types, btoa) is in
// src/test_utf8_guards.py. This is the short version that runs with node --test.
test("text Blobs and data: URLs in the viewer declare charset=utf-8", function () {
  var problems = [];
  fs.readdirSync(WEB_DIR).filter(function (name) {
    return name.endsWith(".js") && name !== "sql-wasm.js";
  }).forEach(function (name) {
    var lines = fs.readFileSync(path.join(WEB_DIR, name), "utf8").split("\n");
    lines.forEach(function (line, index) {
      var where = name + ":" + (index + 1);
      if (/new\s+(Blob|File)\s*\(/.test(line) && !/charset=utf-8/i.test(line) &&
          !/type:\s*["'](image\/|application\/(octet-stream|wasm|x-sqlite3|vnd\.sqlite3))/.test(line)) {
        problems.push(where + ": give the Blob/File a type with ;charset=utf-8");
      }
      if (/["']data:text\//.test(line) && !/charset=utf-8/i.test(line)) {
        problems.push(where + ": use data:text/...;charset=utf-8");
      }
    });
  });
  assert.deepEqual(problems, []);
});
