const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const chordsApi = require("../softchord_chords");
const SongText = require("../softchord_text");
const SongFilter = require("../song_filter");
const Songbook = require("../songbook");
const initSqlJs = require("../sql-wasm.js");

const SongTranspose = chordsApi.SongTranspose;
const SoftchordChords = chordsApi.SoftchordChords;

// The current schema, the same file the editor and the iPhone tests use.
function schemaSql() {
  return fs.readFileSync(path.join(__dirname, "..", "..", "src", "songbook.sql"), "utf8");
}

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
    rootText: null,
    bassText: null,
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
  db.run(schemaSql());
  db.run("INSERT INTO songs (id, uuid, text, title, updated_at) VALUES " +
    "(2, '2b0f0a5e-6f38-4d0b-9d6e-6c1d9a6e1b02', 'Hello world', 'beta Song', 1700000000)");
  db.run("INSERT INTO songs (id, uuid, text, title, updated_at) VALUES " +
    "(1, '5d1c3f0a-1c52-4a43-8f55-0a8d2f6f3a01', 'Hello', 'Alpha', 1700000001)");
  db.run("INSERT INTO song_chord_link (song_id, character_num, chord) VALUES (1, 4, 'Am')");
  db.run("INSERT INTO song_chord_link (song_id, character_num, chord) VALUES (1, 0, 'C')");
  db.run("INSERT INTO song_chord_link (song_id, character_num, chord) VALUES (2, 0, '(1:C/E)')");
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
  assert.throws(function () { Songbook.openBytes(SQL, emptyBytes); }, /old format/);

  var broken = new SQL.Database();
  broken.run("PRAGMA user_version = 2");
  var brokenBytes = broken.export();
  broken.close();
  assert.throws(function () { Songbook.openBytes(SQL, brokenBytes); }, /could not be read/);

  var newer = new SQL.Database();
  newer.run("PRAGMA user_version = 3");
  var newerBytes = newer.export();
  newer.close();
  assert.throws(function () { Songbook.openBytes(SQL, newerBytes); }, /newer format/);
});

test("the current schema is created from src/songbook.sql", async function () {
  var SQL = await initSqlJs({
    locateFile: function (file) {
      return path.join(__dirname, "..", file);
    },
  });
  var db = new SQL.Database();
  db.run(schemaSql());
  function names(sql) {
    return db.exec(sql)[0].values.map(function (row) { return row[0]; });
  }
  assert.deepEqual(names("SELECT name FROM pragma_table_info('songs')"),
    ["id", "uuid", "number", "title", "subtitle", "text", "updated_at"]);
  assert.deepEqual(names("SELECT name FROM pragma_table_info('song_chord_link')"),
    ["id", "song_id", "character_num", "chord"]);
  assert.deepEqual(names("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"),
    ["deleted_songs", "meta", "song_chord_link", "songs"]);
  assert.equal(db.exec("PRAGMA user_version")[0].values[0][0], 2);
  db.close();
});

test("meta, tombstones, uuids and orphan chord rows do not change what is shown", async function () {
  var SQL = await initSqlJs({
    locateFile: function (file) {
      return path.join(__dirname, "..", file);
    },
  });
  var db = new SQL.Database();
  db.run(schemaSql());
  db.run("INSERT INTO meta (key, value) VALUES ('format_version', '2')");
  db.run("INSERT INTO meta (key, value) VALUES ('name', 'Test')");
  db.run("INSERT INTO deleted_songs (uuid, deleted_at) VALUES ('gone', 1700000000)");
  db.run("INSERT INTO songs (id, uuid, number, title, subtitle, text, updated_at) VALUES " +
    "(7, '9c1d3e5f-0a1b-4c2d-8e3f-1a2b3c4d5e6f', NULL, 'Seven', '', 'Hello', 1700000000)");
  db.run("INSERT INTO song_chord_link (song_id, character_num, chord) VALUES (7, 0, 'C')");
  // A file from an older editor can still hold a chord of a missing song.
  db.run("INSERT INTO song_chord_link (song_id, character_num, chord) VALUES (99, 0, 'G')");
  var bytes = db.export();
  db.close();

  Songbook.openBytes(SQL, bytes);
  assert.deepEqual(Songbook.titles(), [{ id: 7, title: "Seven" }]);
  assert.equal(Songbook.source(7).chords.length, 1);
  assert.equal(Songbook.songText(7, true), "C\r\nHello");
  assert.throws(function () { Songbook.source(99); }, /not in the songbook/);
});

test("the repo songbooks have the current schema and the viewer reads all their chords", async function () {
  var SQL = await initSqlJs({
    locateFile: function (file) {
      return path.join(__dirname, "..", file);
    },
  });
  ["zvuki_neba.songbook", "solo_and_group_songs.songbook"].forEach(function (name) {
    var bytes = fs.readFileSync(path.join(__dirname, "..", "..", name));
    var db = new SQL.Database(bytes);
    var songs = db.exec("SELECT COUNT(*) FROM songs")[0].values[0][0];
    var chords = db.exec("SELECT COUNT(*) FROM song_chord_link")[0].values[0][0];
    var orphans = db.exec(
      "SELECT COUNT(*) FROM song_chord_link WHERE song_id NOT IN (SELECT id FROM songs)")[0].values[0][0];
    var uuids = db.exec("SELECT COUNT(DISTINCT uuid) FROM songs")[0].values[0][0];
    var columns = db.exec("SELECT name FROM pragma_table_info('songs')")[0].values
      .map(function (row) { return row[0]; });
    db.close();
    assert.deepEqual(columns,
      ["id", "uuid", "number", "title", "subtitle", "text", "updated_at"], name);
    assert.equal(orphans, 0, name);
    assert.equal(uuids, songs, name);

    Songbook.openBytes(SQL, new Uint8Array(bytes));
    var titles = Songbook.titles();
    assert.equal(titles.length, songs, name);
    var seen = 0;
    titles.forEach(function (entry) {
      seen += Songbook.source(entry.id).chords.length;
    });
    assert.equal(seen, chords, name);
  });
});

test("unreadable chord strings load as unknown chords drawn as ?", async function () {
  var SQL = await initSqlJs({
    locateFile: function (file) {
      return path.join(__dirname, "..", file);
    },
  });
  var db = new SQL.Database();
  // The viewer copes with a chord that is NULL, although the current schema
  // does not allow one, so this table leaves the column nullable.
  db.run(
    "CREATE TABLE songs (id INT PRIMARY KEY, text TEXT, title TEXT);" +
    "CREATE TABLE song_chord_link (" +
    "id INTEGER PRIMARY KEY, song_id INT, character_num INT, chord TEXT);" +
    "PRAGMA user_version = 2;");
  db.run("INSERT INTO songs (id, text, title) VALUES (1, 'Hello world', 'Alpha')");
  db.run("INSERT INTO song_chord_link (song_id, character_num, chord) VALUES (1, 0, 'N.C.')");
  db.run("INSERT INTO song_chord_link (song_id, character_num, chord) VALUES (1, 3, '')");
  db.run("INSERT INTO song_chord_link (song_id, character_num, chord) VALUES (1, 6, NULL)");
  db.run("INSERT INTO song_chord_link (song_id, character_num, chord) VALUES (1, 8, 'Am7add13/G')");
  var bytes = db.export();
  db.close();
  Songbook.openBytes(SQL, bytes);
  var chords = Songbook.source(1).chords;
  assert.equal(chords.length, 4);
  assert.deepEqual(chords.map(function (c) { return c.unknown; }), [true, true, true, false]);
  assert.equal(chords[0].raw, "N.C.");
  assert.deepEqual(Songbook.sheet(1)[0].chords.map(function (c) { return c.text; }),
    ["?", "?", "?", "Am7add13/G"]);
  var up = SongTranspose.shifted(chords, 2);
  assert.equal(up[0], chords[0]);
  assert.equal(SoftchordChords.chordText(up[3], 0), "Bm7add13/A");
});

test("shared chord vectors", function () {
  var file = path.join(__dirname, "..", "..", "tests", "chord_vectors.json");
  var cases = JSON.parse(fs.readFileSync(file, "utf8")).cases;
  assert.ok(cases.length > 100);
  cases.forEach(function (item) {
    var parsed = SoftchordChords.parseChord(item.input);
    var label = JSON.stringify(item.input);
    assert.equal(parsed.unknown, item.unknown, label);
    assert.equal(SoftchordChords.parsedChordString(parsed), item.canonical, label);
    if (item.unknown) {
      return;
    }
    assert.equal(parsed.rootText, item.root, label);
    assert.equal(parsed.noteId, item.note_id, label);
    assert.equal(parsed.isMinor ? "minor" : "major", item.quality, label);
    assert.equal(parsed.chordTypeId, item.type_id, label);
    assert.equal(parsed.isKnownType, item.known_type, label);
    assert.equal(parsed.suffix, item.suffix, label);
    assert.equal(parsed.bassText || null, item.bass, label);
    if (item.bass !== null) {
      assert.equal(parsed.bassNoteId, item.bass_id, label);
    }
    assert.equal(parsed.marker, item.marker, label);
    assert.equal(parsed.inParentheses, item.parens, label);
    var again = SoftchordChords.parseChord(item.canonical);
    assert.equal(SoftchordChords.parsedChordString(again), item.canonical, label);
  });
});

test("garbage chord strings never throw", function () {
  ["", "   ", "?", "(", ")", "()", ":", "/", "C/", "/C", "(:)", "\u0000", "💥", "C/H/", "((C))", null, undefined]
    .forEach(function (text) {
      SoftchordChords.parseChord(text);
      SoftchordChords.chordFromText(text, 0);
    });
});
