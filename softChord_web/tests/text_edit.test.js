const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const SongTextEdit = require("../softchord_text_edit");

// The cases the desktop and iPhone tests read too, so the three agree.
const vectors = JSON.parse(fs.readFileSync(
  path.join(__dirname, "..", "..", "tests", "lyric_chord_vectors.json"), "utf8"));

function chordAt(index, extra) {
  return Object.assign({
    characterNum: index, noteId: 0, chordTypeId: 0, bassNoteId: -1,
    marker: "", inParentheses: false,
  }, extra || {});
}

function positions(chords) {
  return chords.map(function (chord) { return chord.characterNum; });
}

test("the shared vectors are there", function () {
  assert.ok(vectors.cases.length > 30);
});

test("every shared vector moves the chords the same way", function () {
  vectors.cases.forEach(function (c) {
    var chords = c.chords_in.map(function (i) { return chordAt(i); });
    var moved = SongTextEdit.moveChords(chords, c.old, c.new);
    assert.deepEqual(positions(moved), c.chords_out, c.name);
  });
});

test("the shared vectors keep exactly the chords listed as kept", function () {
  vectors.cases.forEach(function (c) {
    var chords = c.chords_in.map(function (i) { return chordAt(i, { noteId: i % 12 }); });
    var moved = SongTextEdit.moveChords(chords, c.old, c.new);
    assert.deepEqual(moved.map(function (chord) { return chord.noteId; }),
      c.kept.map(function (i) { return i % 12; }), c.name);
  });
});

test("moveChords keeps everything else about a chord and does not change its input", function () {
  var chord = chordAt(2, { noteId: 7, chordTypeId: 3, bassNoteId: 4, marker: "1", inParentheses: true });
  var moved = SongTextEdit.moveChords([chord], "abc", "xabc");
  assert.equal(moved[0].characterNum, 3);
  assert.equal(moved[0].noteId, 7);
  assert.equal(moved[0].chordTypeId, 3);
  assert.equal(moved[0].bassNoteId, 4);
  assert.equal(moved[0].marker, "1");
  assert.equal(moved[0].inParentheses, true);
  assert.equal(chord.characterNum, 2);
  assert.notEqual(moved[0], chord);
});

test("Hello to Helo keeps one l and loses no chord to a second one", function () {
  var chords = [0, 1, 2, 3, 4].map(function (i) { return chordAt(i); });
  assert.deepEqual(positions(SongTextEdit.moveChords(chords, "Hello", "Helo")), [0, 1, 2, 3]);
});

test("a chord on a deleted letter is dropped, and the others follow their letters", function () {
  var chords = [chordAt(0), chordAt(3), chordAt(6)];
  var moved = SongTextEdit.moveChords(chords, "abc def", "abcdef");
  assert.deepEqual(positions(moved), [0, 5]);
  assert.deepEqual(positions(SongTextEdit.moveChords(chords, "abc def", "abc  def")), [0, 3, 7]);
});

test("Enter in the middle of a line moves the chords after it down with their letters", function () {
  var chords = [chordAt(0), chordAt(4), chordAt(8)];
  var moved = SongTextEdit.moveChords(chords, "one two\nthree", "one \ntwo\nthree");
  assert.deepEqual(positions(moved), [0, 5, 9]);
});

test("Backspace joining two lines keeps the chords on both", function () {
  var chords = [chordAt(0), chordAt(4)];
  var moved = SongTextEdit.moveChords(chords, "ab\ncd", "abcd");
  assert.deepEqual(positions(moved), [0, 3]);
});

test("positions are code points, not UTF-16 units", function () {
  // "𝄞" is two UTF-16 units and one letter.
  var chords = [chordAt(0), chordAt(1), chordAt(2)];
  var moved = SongTextEdit.moveChords(chords, "𝄞ab", "x𝄞ab");
  assert.deepEqual(positions(moved), [1, 2, 3]);
  var cyrillic = SongTextEdit.moveChords([chordAt(0), chordAt(4)], "Звуки", "Звуки неба");
  assert.deepEqual(positions(cyrillic), [0, 4]);
  var front = SongTextEdit.moveChords([chordAt(0), chordAt(4)], "Звуки", "Мои Звуки");
  assert.deepEqual(positions(front), [4, 8]);
});

test("a chord past the end of the old text is dropped", function () {
  assert.deepEqual(positions(SongTextEdit.moveChords([chordAt(9)], "abc", "abcd")), []);
});

test("normalizeNewlines turns CRLF and CR into LF and keeps other whitespace", function () {
  assert.equal(SongTextEdit.normalizeNewlines("a\r\nb\rc\nd"), "a\nb\nc\nd");
  assert.equal(SongTextEdit.normalizeNewlines("a\r\n\r\nb"), "a\n\nb");
  assert.equal(SongTextEdit.normalizeNewlines(" a\t b  \n"), " a\t b  \n");
});

test("normalizeSong moves the chords with their letters when a CRLF loses its CR", function () {
  // "ab\r\ncd\r\nef": a0 b1 CR2 LF3 c4 d5 CR6 LF7 e8 f9
  var song = SongTextEdit.normalizeSong("ab\r\ncd\r\nef", [chordAt(0), chordAt(4), chordAt(8), chordAt(2)]);
  assert.equal(song.text, "ab\ncd\nef");
  assert.deepEqual(positions(song.chords), [0, 3, 6]);
  var lone = SongTextEdit.normalizeSong("a\rb", [chordAt(2)]);
  assert.equal(lone.text, "a\nb");
  assert.deepEqual(positions(lone.chords), [2]);
  var plain = SongTextEdit.normalizeSong("a\nb", [chordAt(0), chordAt(1), chordAt(2)]);
  assert.equal(plain.text, "a\nb");
  assert.deepEqual(positions(plain.chords), [0, 1, 2]);
});

test("codePointIndex converts a UTF-16 offset", function () {
  var text = "a𝄞b";
  assert.equal(SongTextEdit.codePointIndex(text, 0), 0);
  assert.equal(SongTextEdit.codePointIndex(text, 1), 1);
  assert.equal(SongTextEdit.codePointIndex(text, 3), 2);
  assert.equal(SongTextEdit.codePointIndex(text, 4), 3);
  assert.equal(SongTextEdit.codePointIndex(text, 99), 3);
  assert.equal(SongTextEdit.codePointIndex(text, -5), 0);
});

// A small seeded generator, so a failure can be repeated.
function random(seed) {
  var state = seed;
  return function () {
    state = (state * 1664525 + 1013904223) % 4294967296;
    return state / 4294967296;
  };
}

test("random edits: every kept chord stays on its own letter, none double, order is kept", function () {
  var next = random(12345);
  var alphabet = ["a", "b", "c", " ", "\n", "я", "𝄞"];
  function randomText(max) {
    var length = Math.floor(next() * max);
    var text = [];
    for (var i = 0; i < length; i++) {
      text.push(alphabet[Math.floor(next() * alphabet.length)]);
    }
    return text;
  }
  for (var round = 0; round < 500; round++) {
    var old = randomText(14);
    var cut = Math.floor(next() * (old.length + 1));
    var cutEnd = cut + Math.floor(next() * (old.length - cut + 1));
    var edited = old.slice(0, cut).concat(randomText(5), old.slice(cutEnd));
    var chords = old.map(function (_, i) { return chordAt(i, { marker: String(i) }); });
    var moved = SongTextEdit.moveChords(chords, old.join(""), edited.join(""));
    var seen = {};
    moved.forEach(function (chord, i) {
      assert.ok(chord.characterNum >= 0 && chord.characterNum < edited.length);
      assert.equal(seen[chord.characterNum], undefined, "two chords on one letter");
      seen[chord.characterNum] = true;
      if (i > 0) {
        assert.ok(chord.characterNum > moved[i - 1].characterNum, "order kept");
      }
      // The chord's old letter is the letter it now sits on.
      assert.equal(edited[chord.characterNum], old[Number(chord.marker)]);
    });
    // Everything before the edit is unchanged, so no chord there is lost.
    for (var i = 0; i < cut; i++) {
      assert.ok(seen[i], "start kept");
    }
    // The same text changes nothing.
    var same = SongTextEdit.moveChords(chords, old.join(""), old.join(""));
    assert.deepEqual(positions(same), positions(chords));
  }
});

test("pushSnapshot adds the newest snapshot, cuts off what Redo would reach, and keeps at most the limit", function () {
  var history = [{ n: 0 }, { n: 1 }, { n: 2 }];
  // Undo went back to 1, then a new edit: snapshot 2 is gone.
  var index = SongTextEdit.pushSnapshot(history, 1, { n: 3 });
  assert.equal(index, 2);
  assert.deepEqual(history.map(function (s) { return s.n; }), [0, 1, 3]);

  history = [];
  index = -1;
  for (var n = 0; n < 10; n++) {
    index = SongTextEdit.pushSnapshot(history, index, { n: n }, 4);
    assert.equal(index, history.length - 1);
  }
  assert.deepEqual(history.map(function (s) { return s.n; }), [6, 7, 8, 9], "the oldest are let go");
  assert.equal(SongTextEdit.HISTORY_LIMIT, 200);

  history = [];
  index = -1;
  for (n = 0; n < 500; n++) {
    index = SongTextEdit.pushSnapshot(history, index, { n: n });
  }
  assert.equal(history.length, 200);
  assert.equal(history[199].n, 499);
});
