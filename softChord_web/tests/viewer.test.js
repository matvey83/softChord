const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

const chordsApi = require("../softchord_chords");
const SongText = require("../softchord_text");
const SongFilter = require("../song_filter");
const Songbook = require("../songbook");
const initSqlJs = require("../sql-wasm.js");

const SongTranspose = chordsApi.SongTranspose;

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

function progression(pairs, times, start, step) {
  var chords = [];
  var character = start || 0;
  var hop = step || 4;
  for (var n = 0; n < times; n++) {
    for (var i = 0; i < pairs.length; i++) {
      chords.push(chord(character, pairs[i][0], pairs[i][1]));
      character += hop;
    }
  }
  return chords;
}

test("song text matches the editor layout", function () {
  var chords = [
    chord(0, 0),
    chord(5, 9, 1),
    chord(26, 7),
  ];
  var text = "Test line one\nTest line two";
  var withChords = SongText.render(text, chords, true);
  assert.equal(
    withChords,
    "C    Am\r\nTest line one\r\n" + " ".repeat(11) + "G\r\nTest line two");
  assert.equal(SongText.render(text, chords, false), "Test line one\r\nTest line two");
});

test("sheet anchors chords on their letters", function () {
  var chords = [chord(0, 0), chord(5, 9, 1), chord(26, 7)];
  var lines = SongText.sheet("Test line one\nTest line two", chords);
  assert.deepEqual(lines.map(function (line) { return line.lyric; }), [
    "Test line one",
    "Test line two",
  ]);
  assert.deepEqual(lines[0].chords, [
    { anchor: 0, text: "C" },
    { anchor: 5, text: "Am" },
  ]);
  assert.deepEqual(lines[1].chords, [{ anchor: 12, text: "G" }]);
});

test("chord text keeps marker bass and parentheses", function () {
  var marked = {
    characterNum: 0,
    noteId: 0,
    chordTypeId: 0,
    bassNoteId: 4,
    marker: "1",
    inParentheses: true,
  };
  assert.equal(
    SongText.render("Hello world", [marked], true),
    "(1:C/E)\r\nHello world");
});

test("blank lines stay in the sheet", function () {
  var lines = SongText.sheet("One\n\nTwo", []);
  assert.deepEqual(lines.map(function (line) { return line.lyric; }), ["One", "", "Two"]);
});

test("A major spells sharps", function () {
  var chords = progression([[9, 0], [4, 0], [6, 1], [2, 0]], 3);
  var rendered = SongText.render("x".repeat(80), chords, true);
  assert.ok(rendered.includes("F♯"));
  assert.equal(rendered.includes("G♭"), false);
});

test("B flat major spells flats", function () {
  var chords = progression([[10, 0], [5, 0], [7, 1], [3, 0]], 3);
  var rendered = SongText.render("x".repeat(80), chords, true);
  assert.ok(rendered.includes("B♭"));
  assert.ok(rendered.includes("E♭"));
  assert.equal(rendered.includes("A♯"), false);
});

test("C major spells C sharp and E flat", function () {
  var chords = progression([[0, 0], [7, 0], [9, 1]], 4);
  chords.push(chord(80, 1));
  chords.push(chord(84, 3));
  var rendered = SongText.render("x".repeat(100), chords, true);
  assert.ok(rendered.includes("C♯"));
  assert.ok(rendered.includes("E♭"));
  assert.equal(rendered.includes("D♭"), false);
  assert.equal(rendered.includes("D♯"), false);
});

test("modulation keeps each region's spelling", function () {
  var aMajor = progression([[9, 0], [4, 0], [6, 1], [2, 0]], 4);
  var bFlat = progression([[10, 0], [5, 0], [7, 1], [3, 0]], 4, 200);
  var rendered = SongText.render("x".repeat(400), aMajor.concat(bFlat), true);
  assert.ok(rendered.includes("F♯"));
  assert.ok(rendered.includes("B♭"));
  assert.equal(rendered.includes("G♭"), false);
});

test("half step up moves root and bass", function () {
  var original = {
    characterNum: 4,
    noteId: 0,
    chordTypeId: 1,
    bassNoteId: 7,
    marker: "2",
    inParentheses: true,
  };
  assert.deepEqual(SongTranspose.shifted([original], 1), [{
    characterNum: 4,
    noteId: 1,
    chordTypeId: 1,
    bassNoteId: 8,
    marker: "2",
    inParentheses: true,
  }]);
});

test("half step down wraps C to B and leaves a missing bass", function () {
  var down = SongTranspose.shifted([chord(0, 0)], -1);
  assert.equal(down[0].noteId, 11);
  assert.equal(down[0].bassNoteId, -1);
});

test("an octave of half steps is the original chord", function () {
  var original = chord(2, 5, 4);
  original.bassNoteId = 9;
  assert.deepEqual(SongTranspose.shifted([original], 12), [original]);
  assert.deepEqual(SongTranspose.shifted([original], -12), [original]);
  assert.deepEqual(SongTranspose.shifted([original], 0), [original]);
});

test("transposed chords spell the new key", function () {
  var chords = progression([[9, 0], [4, 0], [6, 1], [2, 0]], 3);
  var rendered = SongText.render(
    "x".repeat(80),
    SongTranspose.shifted(chords, 1),
    true);
  assert.ok(rendered.includes("B♭"));
  assert.ok(rendered.includes("E♭"));
  assert.equal(rendered.includes("A♯"), false);
});

test("filter matches inside the title ignoring case", function () {
  var songs = [
    { id: 1, title: "Alpha" },
    { id: 2, title: "beta Song" },
    { id: 3, title: "Alpine" },
    { id: 4, title: "Бог моя защита" },
    { id: 5, title: "Вместе мы с вами" },
  ];
  assert.equal(SongFilter.matching("   ", songs), songs);
  assert.deepEqual(SongFilter.matching("alp", songs).map(function (song) { return song.id; }), [1, 3]);
  assert.deepEqual(SongFilter.matching("БОГ", songs).map(function (song) { return song.id; }), [4]);
  assert.deepEqual(SongFilter.matching("мы с", songs).map(function (song) { return song.id; }), [5]);
  assert.deepEqual(SongFilter.matching("zzz", songs), []);
});

test("a songbook file is read in id order", async function () {
  var SQL = await initSqlJs({
    locateFile: function (file) {
      return path.join(__dirname, "..", file);
    },
  });
  var db = new SQL.Database();
  db.run(
    "CREATE TABLE songs (id INT PRIMARY KEY, text TEXT, title TEXT);" +
    "CREATE TABLE song_chord_link (" +
    "id INTEGER PRIMARY KEY, song_id INT, character_num INT, note_id INT, " +
    "chord_type_id INT, bass_note_id INT, marker TEXT, in_parentheses INT);");
  db.run("INSERT INTO songs (id, text, title) VALUES (2, 'Hello world', 'beta Song')");
  db.run("INSERT INTO songs (id, text, title) VALUES (1, 'Hello', 'Alpha')");
  db.run(
    "INSERT INTO song_chord_link " +
    "(song_id, character_num, note_id, chord_type_id, bass_note_id, marker, in_parentheses) " +
    "VALUES (1, 4, 9, 1, NULL, '-1', 0)");
  db.run(
    "INSERT INTO song_chord_link " +
    "(song_id, character_num, note_id, chord_type_id, bass_note_id, marker, in_parentheses) " +
    "VALUES (1, 0, 0, 0, NULL, 'None', 0)");
  db.run(
    "INSERT INTO song_chord_link " +
    "(song_id, character_num, note_id, chord_type_id, bass_note_id, marker, in_parentheses) " +
    "VALUES (2, 0, 0, 0, 4, '1', 1)");
  var bytes = db.export();
  db.close();

  Songbook.openBytes(SQL, bytes);
  assert.deepEqual(Songbook.titles(), [
    { id: 1, title: "Alpha" },
    { id: 2, title: "beta Song" },
  ]);
  var alpha = Songbook.source(1);
  assert.deepEqual(alpha.chords.map(function (chord) { return chord.characterNum; }), [4, 0]);
  assert.equal(alpha.chords[0].marker, "");
  assert.equal(alpha.chords[0].bassNoteId, -1);
  assert.deepEqual(Songbook.sheet(1)[0].chords, [
    { anchor: 4, text: "Am" },
    { anchor: 0, text: "C" },
  ]);
  assert.equal(Songbook.songText(2, true), "(1:C/E)\r\nHello world");
  alpha.chords[0].noteId = 99;
  assert.equal(Songbook.source(1).chords[0].noteId, 9);
  assert.throws(function () { Songbook.source(999999); }, /not in the songbook/);

  var empty = new SQL.Database();
  var emptyBytes = empty.export();
  empty.close();
  assert.throws(function () { Songbook.openBytes(SQL, emptyBytes); }, /could not be read/);
});
