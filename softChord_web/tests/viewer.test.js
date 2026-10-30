const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const chordsApi = require("../softchord_chords");
const SongText = require("../softchord_text");
const SongFilter = require("../song_filter");
const SheetImage = require("../softchord_sheet_image");
const SongZoom = require("../softchord_zoom");
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
    { anchor: 0, text: "C", unrecognized: false },
    { anchor: 5, text: "Am", unrecognized: false },
  ]);
  assert.deepEqual(lines[1].chords, [{ anchor: 12, text: "G", unrecognized: false }]);
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

test("chords with no letter are not drawn and do not crash", function () {
  // "ab\ncd": index 2 is the line break, 5 is the end, 99 is far past it.
  var text = "ab\ncd";
  var letters = [chord(0, 0), chord(3, 7)];
  [2, 5, 99, -1].forEach(function (stray) {
    var chords = letters.concat([chord(stray, 3)]);
    var lines = SongText.sheet(text, chords);
    assert.deepEqual(lines[0].chords.map(function (c) { return c.anchor; }), [0]);
    assert.deepEqual(lines[1].chords.map(function (c) { return c.anchor; }), [0]);
    assert.equal(SongText.render(text, chords, true), "C\r\nab\r\nG\r\ncd");
  });
  var long = SongText.render("Oh", [chord(0, 0, 11)], true);
  assert.ok(long.includes("\r\nOh"));
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
    { anchor: 4, text: "Am", unrecognized: false },
    { anchor: 0, text: "C", unrecognized: false },
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

test("unreadable chord strings load as unrecognized chords drawn as their text", async function () {
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
    ["N.C.", "?", "?", "Am7add13/G"]);
  assert.deepEqual(Songbook.sheet(1)[0].chords.map(function (c) { return c.unrecognized; }),
    [true, true, true, false]);
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
      assert.equal(parsed.display, item.display, label);
      assert.equal(SoftchordChords.unrecognizedChordDisplay(item.input), item.display, label);
      // The drawn text of a chord made from this string.
      var made = SoftchordChords.chordFromText(item.input, 0);
      assert.equal(SoftchordChords.chordText(made, 0), item.display, label);
      return;
    }
    assert.equal(Object.prototype.hasOwnProperty.call(item, "display"), false, label);
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

test("only text that is not a chord is cut to 7 characters", function () {
  var shown = function (text) {
    return SoftchordChords.chordText(SoftchordChords.chordFromText(text, 0), 0);
  };
  assert.equal(shown("abcdefghij"), "abcdefg");
  assert.equal(shown("  asdf "), "asdf");
  assert.equal(shown("Пожалуйста"), "Пожалуй");
  assert.equal(shown("🎵🎵🎵🎵🎵🎵🎵🎵"), "🎵🎵🎵🎵🎵🎵🎵");
  assert.equal(shown(""), "?");
  assert.equal(shown("?"), "?");
  assert.equal(shown(null), "?");
  // A real chord is shown in full, spelled as it is.
  assert.equal(shown("Cmaj7sus4add9/F#"), "Cmaj7sus4add9/F♯");
});

test("transposing a song with no chord that can move changes nothing", function () {
  var unrecognized = SoftchordChords.chordFromText("N.C.", 0);
  var real = SoftchordChords.chordFromText("Am", 4);
  assert.equal(SongTranspose.changesChords([unrecognized], 1), false);
  assert.equal(SongTranspose.changesChords([], 1), false);
  assert.equal(SongTranspose.changesChords([unrecognized, real], 1), true);
  assert.equal(SongTranspose.changesChords([unrecognized, real], 12), false);
  assert.equal(SongTranspose.changesChords([unrecognized, real], -24), false);
  assert.equal(SongTranspose.changesChords([real], 13), true);
  // Unrecognized chords stay put and keep their text next to the moved ones.
  var shifted = SongTranspose.shifted([unrecognized, real], 2);
  assert.equal(shifted[0], unrecognized);
  assert.equal(SoftchordChords.chordText(shifted[1], 0), "Bm");
});

test("shared chord validity vectors", function () {
  var file = path.join(__dirname, "..", "..", "tests", "chord_vectors.json");
  var vectors = JSON.parse(fs.readFileSync(file, "utf8")).validity;
  assert.ok(vectors.valid.length > 10);
  vectors.valid.forEach(function (text) {
    assert.equal(SoftchordChords.isValidChordText(text), true, JSON.stringify(text));
  });
  vectors.invalid.forEach(function (text) {
    assert.equal(SoftchordChords.isValidChordText(text), false, JSON.stringify(text));
  });
  assert.equal(SoftchordChords.isValidChordText(null), false);
  assert.equal(SoftchordChords.isValidChordText(undefined), false);
});

test("garbage chord strings never throw", function () {
  ["", "   ", "?", "(", ")", "()", ":", "/", "C/", "/C", "(:)", "\u0000", "💥", "C/H/", "((C))", null, undefined]
    .forEach(function (text) {
      SoftchordChords.parseChord(text);
      SoftchordChords.chordFromText(text, 0);
    });
});

// A fixed-pitch stand-in for canvas measureText: half the font size per letter.
function fakeMeasure(font, text) {
  var size = parseFloat(/(\d+(?:\.\d+)?)px/.exec(font)[1]);
  return { width: Array.from(text).length * size / 2, ascent: size * 0.9, descent: size * 0.2 };
}

function glyphsOf(drawing, text) {
  return drawing.glyphs.filter(function (glyph) { return glyph.text === text; });
}

test("sheet image puts the title first and each chord over its letter", function () {
  var lines = SongText.sheet("Hello world\nplain", [chord(6, 7), chord(3, 0, 1)]);
  var drawing = SheetImage.layout("My song", lines, fakeMeasure);
  assert.equal(drawing.glyphs[0].text, "My song");
  assert.equal(drawing.glyphs[0].x, SheetImage.PADDING);
  var hello = glyphsOf(drawing, "Hello world")[0];
  var plain = glyphsOf(drawing, "plain")[0];
  var g = glyphsOf(drawing, "G")[0];
  assert.equal(hello.x, SheetImage.PADDING);
  // Letter 6 spans x 16+60 to 16+70 on the fake pitch, and G is 6 wide.
  assert.equal(g.x, 16 + 65 - 3);
  assert.ok(g.baseline < hello.baseline, "the chord sits above the lyric");
  assert.ok(g.baseline > hello.baseline - 20);
  assert.equal(g.color, "#00f");
  assert.equal(hello.color, "#000");
  assert.ok(plain.baseline > hello.baseline);
  assert.ok(drawing.width >= 16 + 11 * 10 + 16);
  assert.ok(drawing.height > plain.baseline);
});

test("sheet image draws text that is not a chord in red, cut to 7 characters", function () {
  var odd = SoftchordChords.chordFromText("abcdefghij", 3);
  var lines = SongText.sheet("Hello world", [chord(0, 0), odd]);
  var drawing = SheetImage.layout("", lines, fakeMeasure);
  assert.equal(glyphsOf(drawing, "C")[0].color, "#00f");
  ["a", "b", "c", "d", "e", "f", "g"].forEach(function (letter) {
    assert.equal(glyphsOf(drawing, letter)[0].color, "#f00", letter);
  });
  assert.equal(glyphsOf(drawing, "h").length, 0, "the rest is cut");
});

test("sheet image gives a line more room only when it has chords", function () {
  var without = SheetImage.layout("", SongText.sheet("a\nb", []), fakeMeasure);
  var withChord = SheetImage.layout("", SongText.sheet("a\nb", [chord(2, 0)]), fakeMeasure);
  assert.ok(Math.abs(withChord.height - without.height - (12 * 0.9) * 1.03) < 1e-9);
  assert.equal(without.glyphs.length, 2);
});

test("sheet image keeps a wide first chord inside the left padding", function () {
  var wide = chord(0, 0, 1);
  wide.bassNoteId = 4;
  var lines = SongText.sheet("a", [wide]);
  var drawing = SheetImage.layout("", lines, fakeMeasure);
  var xs = drawing.glyphs.map(function (glyph) { return glyph.x; });
  assert.ok(Math.min.apply(null, xs) >= SheetImage.PADDING - 1e-9);
  assert.ok(drawing.width > 32);
});

test("sheet image raises sharps and flats in the symbol font", function () {
  var lines = SongText.sheet("Hello", [chord(0, 6)]);
  var drawing = SheetImage.layout("", lines, fakeMeasure);
  var sharp = drawing.glyphs.filter(function (glyph) { return glyph.text === "♯" || glyph.text === "♭"; });
  var letter = glyphsOf(drawing, "F")[0] || glyphsOf(drawing, "G")[0];
  assert.equal(sharp.length, 1);
  assert.equal(sharp[0].font, SheetImage.SYMBOLS_FONT);
  assert.ok(sharp[0].baseline < letter.baseline);
  assert.ok(sharp[0].x > letter.x);
});

test("sheet image scale and file name stay in range", function () {
  assert.equal(SheetImage.scaleFor({ width: 400, height: 600 }, 3), 3);
  assert.ok(SheetImage.scaleFor({ width: 400, height: 60000 }, 2) * 60000 <= 16384);
  var size = SheetImage.pixelSize({ width: 100.2, height: 50 }, 2);
  assert.deepEqual(size, { width: 201, height: 100 });
  assert.equal(SheetImage.fileName("Ты мой Бог: Святой?"), "Ты мой Бог Святой.png");
  assert.equal(SheetImage.fileName(""), "song.png");
});

test("sheet image paint draws on a white page at the given scale", function () {
  var calls = [];
  var ctx = {
    save: function () { calls.push(["save"]); },
    restore: function () { calls.push(["restore"]); },
    setTransform: function () { calls.push(["setTransform"].concat([].slice.call(arguments))); },
    fillRect: function () { calls.push(["fillRect"].concat([].slice.call(arguments))); },
    fillText: function (text, x, y) { calls.push(["fillText", text, x, y, ctx.font, ctx.fillStyle]); },
  };
  var drawing = SheetImage.layout("T", SongText.sheet("Hi", [chord(0, 0)]), fakeMeasure);
  var pixels = SheetImage.pixelSize(drawing, 2);
  SheetImage.paint(ctx, drawing, 2, pixels);
  assert.deepEqual(calls[1], ["setTransform", 2, 0, 0, 2, 0, 0]);
  assert.equal(calls[2][0], "fillRect");
  var texts = calls.filter(function (call) { return call[0] === "fillText"; });
  assert.deepEqual(texts.map(function (call) { return call[1]; }), ["T", "Hi", "C"]);
  assert.equal(texts[2][5], "#00f");
});

test("the song toolbar has a labelled button for every action", function () {
  var html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
  var expected = {
    "copy-text": "Copy song text",
    "copy-chords": "Copy song text (with chords)",
    "copy-image": "Copy song as image",
    "transpose-down": "Transpose down",
    "transpose-up": "Transpose up",
    "transpose-reset": "Reset transpose",
    "zoom-out": "Zoom out",
    "zoom-reset": "Reset zoom (100%)",
    "zoom-in": "Zoom in",
    "print": "Print / Save as PDF",
  };
  var order = [];
  Object.keys(expected).forEach(function (id) {
    var match = new RegExp("<button id=\"" + id + "\"[^>]*>([\\s\\S]*?)</button>").exec(html);
    assert.ok(match, id);
    assert.ok(match[0].includes("title=\"" + expected[id] + "\""), id + " tooltip");
    assert.ok(match[0].includes("aria-label=\"" + expected[id] + "\""), id + " aria-label");
    assert.ok(match[1].includes("<svg"), id + " icon");
    order.push(html.indexOf("id=\"" + id + "\""));
  });
  var sorted = order.slice().sort(function (a, b) { return a - b; });
  assert.deepEqual(order, sorted, "copy, then transpose, then zoom, then print buttons");
  assert.ok(html.indexOf("id=\"back\"") < order[0]);
  assert.ok(html.includes("softchord_sheet_image.js"));
  assert.ok(html.indexOf("<!--") < html.indexOf("<html"), "README link comment stays at the top");
});

test("the toolbar buttons are wired to the copy actions in viewer.js", function () {
  var code = fs.readFileSync(path.join(__dirname, "..", "viewer.js"), "utf8");
  assert.ok(/copyTextButton\.addEventListener\("click"[\s\S]*?copyShownText\(false/.test(code));
  assert.ok(/copyChordsButton\.addEventListener\("click"[\s\S]*?copyShownText\(true/.test(code));
  assert.ok(/copyImageButton\.addEventListener\("click", copyShownImage\)/.test(code));
  assert.ok(code.includes("navigator.clipboard.write"));
  assert.ok(code.includes("download"));
});

test("zoom steps by 10 percent and stops at 50 and 300", function () {
  assert.equal(SongZoom.DEFAULT, 100);
  assert.equal(SongZoom.stepped(100, 1), 110);
  assert.equal(SongZoom.stepped(100, -1), 90);
  var p = 100;
  for (var i = 0; i < 100; i++) { p = SongZoom.stepped(p, 1); }
  assert.equal(p, 300);
  for (i = 0; i < 100; i++) { p = SongZoom.stepped(p, -1); }
  assert.equal(p, 50);
  assert.equal(SongZoom.stepped(300, 1), 300);
  assert.equal(SongZoom.stepped(50, -1), 50);
  // Twenty steps up then twenty down comes back exactly (no float drift).
  p = 100;
  for (i = 0; i < 20; i++) { p = SongZoom.stepped(p, 1); }
  for (i = 0; i < 20; i++) { p = SongZoom.stepped(p, -1); }
  assert.equal(p, 100);
});

test("zoom snaps stray values to the 10 percent grid and clamps", function () {
  assert.equal(SongZoom.stepped(105, 1), 110);
  assert.equal(SongZoom.stepped(105, -1), 100);
  assert.equal(SongZoom.stepped(5, 1), 60);
  assert.equal(SongZoom.clamp(1000), 300);
  assert.equal(SongZoom.clamp(-5), 50);
  assert.equal(SongZoom.clamp("abc"), 100);
});

test("saved zoom is read back only when it is sane", function () {
  assert.equal(SongZoom.parseStored("150"), 150);
  assert.equal(SongZoom.parseStored("50"), 50);
  assert.equal(SongZoom.parseStored("300"), 300);
  ["", "49", "301", "abc", "1e2", "-100", "100.5", null, undefined, 150].forEach(function (bad) {
    assert.equal(SongZoom.parseStored(bad), 100, String(bad));
  });
});

test("zoom is saved and loaded through storage, and survives broken storage", function () {
  var data = {};
  var storage = {
    getItem: function (k) { return k in data ? data[k] : null; },
    setItem: function (k, v) { data[k] = v; },
  };
  assert.equal(SongZoom.load(storage), 100);
  SongZoom.save(storage, 140);
  assert.equal(data[SongZoom.STORAGE_KEY], "140");
  assert.equal(SongZoom.load(storage), 140);
  var broken = {
    getItem: function () { throw new Error("blocked"); },
    setItem: function () { throw new Error("full"); },
  };
  assert.equal(SongZoom.load(broken), 100);
  SongZoom.save(broken, 140);
  assert.equal(SongZoom.load(null), 100);
  SongZoom.save(null, 140);
});

test("zoom changes only the song area font, and not the toolbar or the image", function () {
  var css = fs.readFileSync(path.join(__dirname, "..", "viewer.css"), "utf8");
  var code = fs.readFileSync(path.join(__dirname, "..", "viewer.js"), "utf8");
  var html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
  // --zoom is set on the sheet's parent only and read only by the font size of
  // the sheet and of the editor lying over it.
  assert.ok(/sheetWrap\.style\.setProperty\("--zoom"/.test(code));
  // Twice: the font size of both, and the textarea's own copy of it that is never
  // under 16px (see --boost).
  assert.equal(css.split("--zoom").length - 1, 2);
  assert.ok(/#sheet, #sheet-editor \{[^}]*font-size: calc\(20px \* var\(--zoom, 1\)\)/.test(css));
  assert.ok(/#sheet-editor \{\s*font-size: max\(16px, calc\(20px \* var\(--zoom, 1\) \* var\(--boost, 1\)\)\)/.test(css));
  // Chords scale with the sheet, so they stay over their letters.
  assert.ok(/\.chord \{[^}]*font-size: 0\.6em/.test(css));
  // The only transform is the textarea's scale back down from its 16px font.
  assert.equal(/zoom: /.test(css), false);
  assert.equal(css.split(/transform: *scale/).length - 1, 1);
  assert.ok(/#sheet-wrap\.boosted #sheet-editor \{\s*transform: scale\(calc\(1 \/ var\(--boost, 1\)\)\)/.test(css));
  // The picture is drawn from the song at its normal size.
  var imageCode = /function renderSongImage[\s\S]*?\n  \}\n/.exec(code)[0];
  assert.equal(imageCode.includes("zoom"), false);
  assert.equal(imageCode.includes("Zoom"), false);
  assert.ok(/zoomOutButton\.addEventListener\("click"[\s\S]*?zoomBy\(-1\)/.test(code));
  assert.ok(/zoomInButton\.addEventListener\("click"[\s\S]*?zoomBy\(1\)/.test(code));
  assert.ok(html.indexOf("softchord_zoom.js") < html.indexOf("viewer.js"));
  // Each zoom icon is a circle (the glass) with a handle, and Zoom in adds a vertical bar.
  var out = /id="zoom-out"[\s\S]*?<\/button>/.exec(html)[0];
  var inn = /id="zoom-in"[\s\S]*?<\/button>/.exec(html)[0];
  assert.ok(out.includes("<circle") && inn.includes("<circle"));
  assert.equal(out.includes("M10.5 7.5v6"), false);
  assert.ok(inn.includes("M10.5 7.5v6"));
});

test("reset zoom is only for a song area that is not at 100 percent", function () {
  assert.equal(SongZoom.isDefault(100), true);
  [50, 90, 110, 300].forEach(function (p) {
    assert.equal(SongZoom.isDefault(p), false, String(p));
  });
  // A stray stored value is snapped by clamp, and 100 stays the only normal size.
  assert.equal(SongZoom.isDefault("abc"), true);
  assert.equal(SongZoom.isDefault(1000), false);
});

test("the Reset zoom button sits between Zoom out and Zoom in and is wired in viewer.js", function () {
  var html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
  var code = fs.readFileSync(path.join(__dirname, "..", "viewer.js"), "utf8");
  var out = html.indexOf("id=\"zoom-out\"");
  var reset = html.indexOf("id=\"zoom-reset\"");
  var inn = html.indexOf("id=\"zoom-in\"");
  assert.ok(out < reset && reset < inn);
  assert.ok(/zoomResetButton\.disabled = SongZoom\.isDefault\(shown\)/.test(code));
  assert.ok(/zoomResetButton\.addEventListener\("click", resetZoom\)/.test(code));
  assert.ok(/function resetZoom[\s\S]*?zoomPercent = SongZoom\.DEFAULT[\s\S]*?SongZoom\.save/.test(code));
});

test("the Print button calls the browser print dialog", function () {
  var code = fs.readFileSync(path.join(__dirname, "..", "viewer.js"), "utf8");
  assert.ok(/printButton\.addEventListener\("click", function \(\) \{\s*window\.print\(\);/.test(code));
});

test("print styles keep only the song, in black on white, at a fixed size", function () {
  var css = fs.readFileSync(path.join(__dirname, "..", "viewer.css"), "utf8");
  var at = css.indexOf("@media print");
  assert.ok(at > 0, "print rules exist");
  assert.ok(/@page \{ margin: [^}]+\}/.test(css), "page margins");
  var print = css.slice(at);
  // The chrome around the song is not printed.
  var hide = /([^{}]*)\{\s*display: none !important;\s*\}/.exec(print)[1];
  ["#back", ".toolbar-actions", "#persist-note", "#toast", "#menu", "#notice"].forEach(function (sel) {
    assert.ok(hide.includes(sel), sel + " is hidden when printing");
  });
  assert.equal(hide.includes("#song-title"), false, "the title is printed");
  assert.equal(/#sheet(?![-\w])/.test(hide), false, "the song is printed");
  assert.ok(hide.includes("#sheet-editor"), "the editor is not printed");
  // The song area is not a scroll box, so every page gets printed.
  assert.ok(/#sheet-scroll \{[^}]*overflow: visible/.test(print));
  // Fixed size (the on-screen zoom is not used), black chords, white page.
  assert.ok(/#sheet \{[^}]*font-size: 12pt/.test(print));
  assert.equal(print.includes("var("), false);
  assert.ok(/\.chord \{ color: #000; \}/.test(print));
  assert.ok(/body[\s\S]*?background: #fff/.test(print));
  // A chord line and its lyric line stay on one page, and the room for the
  // chords is padding so it is not lost at the top of a page.
  assert.ok(/\.line \{[^}]*break-inside: avoid/.test(print));
  assert.ok(/\.line\.has-chords \{[^}]*margin-top: 0;[^}]*padding-top: 1\.15em/.test(print));
});

test("Reset transpose is wired to the transpose state in viewer.js", function () {
  var html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
  var code = fs.readFileSync(path.join(__dirname, "..", "viewer.js"), "utf8");
  // Starts dimmed in the page, then follows the steps after every paint.
  assert.ok(/id="transpose-reset"[^>]* disabled>/.test(html));
  assert.ok(html.indexOf("id=\"transpose-up\"") < html.indexOf("id=\"transpose-reset\""));
  assert.ok(/var transposed = SongTranspose\.changesChords\(source\.chords, steps\);/.test(code));
  assert.ok(/transposeReset\.disabled = !transposed/.test(code));
  // The note also stays after Save (savedEdit), see the Edit text tests.
  assert.ok(/persistNote\.hidden = !\(transposed \|\| savedEdit\)/.test(code));
  assert.ok(/transposeReset\.addEventListener\("click"[\s\S]*?steps = 0;[\s\S]*?paintSong\(\)/.test(code));
  // Opening a song starts from 0 again, so "original" means as opened.
  assert.ok(/openId = id;\s*steps = 0;/.test(code));
});

test("a whole octave of steps shows exactly the chords as opened", function () {
  var chords = [chord(0, 0), chord(5, 9, 1), chord(26, 7)];
  var shown = function (steps) {
    return JSON.stringify(
      SongText.sheet("Test line one\nTest line two", SongTranspose.shifted(chords, steps)));
  };
  var original = shown(0);
  // Reset is dimmed at 0 and at every whole octave, because these show the opened chords.
  [12, -12, 24, -24, 36].forEach(function (n) {
    assert.equal(shown(n), original, String(n));
  });
  // Anything between is a different key, and 13 is the same as 1.
  [1, 2, 5, -3, 11, -11, 13].forEach(function (n) {
    assert.notEqual(shown(n), original, String(n));
  });
  assert.equal(shown(13), shown(1));
  assert.equal(shown(-13), shown(-1));
});

// Letters of several code points. Chords stay numbered by code point (as in the
// songbook, the desktop editor and the iPhone app), but the sheet draws a letter
// with its accents or joiners as one box.
test("the sheet anchors a chord to the whole letter when it sits on an accent or a joiner", function () {
  var family = "\u{1F468}\u200D\u{1F469}\u200D\u{1F467}";
  var text = "e\u0301x " + family + " \u0438\u0306!";
  // code points: e=0 accent=1 x=2 space=3 family=4..8 space=9 и=10 breve=11 !=12
  var chords = [chord(1, 0), chord(2, 2), chord(6, 4), chord(11, 7)];
  var line = SongText.sheet(text, chords)[0];
  assert.deepEqual(SongText.letters(line.lyric),
    ["e\u0301", "x", " ", family, " ", "\u0438\u0306", "!"]);
  var anchors = line.chords.map(function (c) { return [c.anchor, c.span || 1]; });
  assert.deepEqual(anchors, [[0, 2], [2, 1], [4, 5], [10, 2]]);
});

test("a song with only single code point letters has no span on its chords", function () {
  var line = SongText.sheet("Hello", [chord(1, 0)])[0];
  assert.deepEqual(line.chords.map(function (c) { return Object.keys(c).sort(); }),
    [["anchor", "text", "unrecognized"]]);
});

test("the picture centres a chord over the whole letter, not over its accent", function () {
  function measure(font, text) {
    return { width: Array.from(text).length * 10, ascent: 9, descent: 3 };
  }
  // Letter 0 is two code points wide (20 px), so a chord on it is centred at 16 + 10.
  var drawing = SheetImage.layout("", [{
    lyric: "e\u0301x", chords: [{ anchor: 0, span: 2, text: "A", unrecognized: false }],
  }], measure);
  var glyph = drawing.glyphs.filter(function (g) { return g.text === "A"; })[0];
  assert.equal(glyph.x, 16 + 10 - 5);
});

// A song of about 24 000 letters in 600 lines with a chord on every other line twice.
function bigSong() {
  var lines = [];
  var chords = [];
  var at = 0;
  for (var i = 0; i < 600; i++) {
    var text = "Line " + i + " of the long song, with words in";
    lines.push(text);
    if (i % 2 === 0) {
      chords.push(chord(at + 2, 0));
      chords.push(chord(at + 15, 9, 1));
    }
    at += text.length + 1;
  }
  return { text: lines.join("\n"), chords: chords };
}

test("sheet of a long song is fast enough to be painted on every keystroke", function () {
  var song = bigSong();
  assert.ok(song.text.length > 20000);
  var typed = song.text.slice(0, 5000) + "x" + song.text.slice(5000);
  var moved = song.chords.map(function (c) {
    return Object.assign({}, c, { characterNum: c.characterNum >= 5000 ? c.characterNum + 1 : c.characterNum });
  });
  SongText.sheet(typed, moved);
  var started = process.hrtime.bigint();
  var lines;
  for (var i = 0; i < 20; i++) {
    lines = SongText.sheet(typed, moved);
  }
  var each = Number(process.hrtime.bigint() - started) / 1e6 / 20;
  assert.equal(lines.length, 600);
  assert.equal(lines.filter(function (l) { return l.chords.length === 2; }).length, 300);
  // About 225 ms each before the search for a chord's line and the key detection
  // were made cheaper, about 5 ms after. The limit leaves room for a slow machine.
  assert.ok(each < 60, "one sheet took " + each.toFixed(1) + " ms");
});

test("the remembered key detection gives the same sheet and text as working it out again", function () {
  function freshText() {
    var name = require.resolve("../softchord_text");
    delete require.cache[name];
    return require("../softchord_text");
  }
  var seed = 12345;
  function random(limit) {
    seed = (seed * 1103515245 + 12345) % 2147483648;
    return seed % limit;
  }
  var warm = SongText;
  for (var round = 0; round < 40; round++) {
    var lines = [];
    for (var i = 0; i < 6 + random(10); i++) {
      lines.push("Line number " + i);
    }
    var text = lines.join("\n");
    var chords = [];
    var count = 1 + random(26);
    for (var c = 0; c < count; c++) {
      chords.push(chord(random(text.length + 3), random(12), random(3)));
    }
    // The same chords again a letter later, as after typing, and then other chords.
    var later = chords.map(function (item) { return Object.assign({}, item, { characterNum: item.characterNum + 1 }); });
    [[text, chords], ["x" + text, later], [text, chords]].forEach(function (pair) {
      var fresh = freshText();
      assert.deepEqual(warm.sheet(pair[0], pair[1]), fresh.sheet(pair[0], pair[1]), "sheet, round " + round);
      assert.equal(warm.render(pair[0], pair[1], true), fresh.render(pair[0], pair[1], true), "text, round " + round);
    });
  }
});

test("every chord row is read as it is, also the same chord twice on one letter", async function () {
  var SQL = await initSqlJs({
    locateFile: function (file) {
      return path.join(__dirname, "..", file);
    },
  });
  var db = new SQL.Database();
  db.run(schemaSql());
  db.run("INSERT INTO songs (id, uuid, text, title, updated_at) VALUES " +
    "(1, '5d1c3f0a-1c52-4a43-8f55-0a8d2f6f3a01', 'Hello world', 'Alpha', 1700000001)");
  db.run("INSERT INTO songs (id, uuid, text, title, updated_at) VALUES " +
    "(2, '2b0f0a5e-6f38-4d0b-9d6e-6c1d9a6e1b02', 'Hello', 'Beta', 1700000002)");
  [[1, 0, "C"], [1, 0, "C"], [1, 6, "Am"], [1, 0, "G"],
    [2, 0, "C"], [2, 0, "C"]].forEach(function (row) {
    db.run("INSERT INTO song_chord_link (song_id, character_num, chord) VALUES (?, ?, ?)", row);
  });
  var bytes = db.export();
  db.close();
  Songbook.openBytes(SQL, bytes);
  assert.deepEqual(Songbook.source(1).chords.map(function (c) { return c.characterNum; }), [0, 0, 6, 0]);
  assert.equal(Songbook.source(2).chords.length, 2);
  assert.equal(Songbook.sheet(2)[0].chords.length, 2);
});
