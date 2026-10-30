const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const SongChordEdit = require("../softchord_chord_edit");
const SongText = require("../softchord_text");
const chordsApi = require("../softchord_chords");

const SongTranspose = chordsApi.SongTranspose;
const SoftchordChords = chordsApi.SoftchordChords;

// The cases the desktop and iPhone tests read too, so the three agree.
const vectors = JSON.parse(fs.readFileSync(
  path.join(__dirname, "..", "..", "tests", "chord_move_vectors.json"), "utf8"));

function chord(index, note) {
  return {
    characterNum: index, noteId: note || 0, chordTypeId: 0, bassNoteId: -1,
    marker: "", inParentheses: false,
  };
}

function positions(chords) {
  return chords.map(function (each) { return each.characterNum; });
}

// A tiny seeded random number generator (SplitMix64 in 32 bits would do, but
// this is enough to repeat a failing run).
function seeded(seed) {
  var state = seed >>> 0;
  return function () {
    state = (state + 0x6d2b79f5) >>> 0;
    var t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

test("the shared jump vectors are there and every one lands the same way", function () {
  assert.ok(vectors.jumps.length > 20);
  vectors.jumps.forEach(function (item) {
    var landing = SongChordEdit.nextFreeCharacter(
      item.text, item.target, item.direction, item.occupied, item.allow_other_direction);
    assert.equal(landing, item.expected, item.name);
  });
});

test("the shared direction vectors give the same direction", function () {
  assert.ok(vectors.directions.length > 5);
  vectors.directions.forEach(function (item) {
    assert.equal(
      SongChordEdit.dragDirection(item.text, item.chord, item.previous, item.target),
      item.expected, item.name);
  });
});

test("a jump lands on a free letter of the same line (random cases, always the same ones)", function () {
  var random = seeded(20261028);
  for (var n = 0; n < 1000; n++) {
    var letters = [];
    var length = Math.floor(random() * 10);
    for (var i = 0; i < length; i++) {
      letters.push(["a", "b", "\n"][Math.floor(random() * 3)]);
    }
    var text = letters.join("");
    var occupied = [];
    for (i = 0; i < length; i++) {
      if (random() < 0.5) {
        occupied.push(i);
      }
    }
    var target = Math.floor(random() * (length + 2)) - 1;
    var direction = random() < 0.5 ? 1 : -1;
    var landing = SongChordEdit.nextFreeCharacter(text, target, direction, occupied, random() < 0.5);
    if (landing === null) {
      continue;
    }
    assert.ok(!occupied.includes(landing), text);
    assert.notEqual(letters[landing], "\n", text);
    var between = letters.slice(Math.min(landing, target), Math.max(landing, target));
    assert.ok(!between.includes("\n"), text);
  }
});

test("a moved chord never shares a letter or loses a chord", function () {
  var chords = [chord(1, 1), chord(2, 2), chord(4, 4)];
  var landing = SongChordEdit.nextFreeCharacter("0123456789", 2, 1, [2, 4], true);
  assert.equal(landing, 3);
  var moved = SongChordEdit.reattached(chords, "0123456789", 1, landing);
  assert.deepEqual(positions(moved), [3, 2, 4]);
  assert.deepEqual(moved.map(function (each) { return each.noteId; }), [1, 2, 4]);
  // The first letter of a full line cannot take another chord.
  var full = [chord(0), chord(1), chord(2)];
  assert.equal(SongChordEdit.reattached(full, "abc", 0, 2), full);
  // The input is not changed.
  assert.deepEqual(positions(chords), [1, 2, 4]);
});

test("dragging over several chords and back follows the pointer", function () {
  // The page drives a drag like this, with the pointer on a letter and the chord
  // on the next free one. The same steps as the iPhone test.
  var text = "0123456789";
  var chords = [chord(1, 1), chord(2, 2), chord(3, 3)];
  var at = 1;
  var finger = 1;
  function drag(target) {
    var step = SongChordEdit.draggedChord(chords, text, at, finger, target);
    if (!step) {
      return;
    }
    finger = step.finger;
    at = step.chordAt;
    chords = step.chords;
  }
  drag(2);
  assert.equal(at, 4);
  drag(2);
  assert.equal(at, 4);
  drag(3);
  assert.equal(at, 4);
  drag(5);
  assert.equal(at, 5);
  drag(3);
  assert.equal(at, 1);
  assert.deepEqual(positions(chords).sort(function (a, b) { return a - b; }), [1, 2, 3]);
  assert.deepEqual(chords.map(function (each) { return each.noteId; }).sort(), [1, 2, 3]);
});

test("a drag onto the letter the pointer is already on does nothing", function () {
  var chords = [chord(1)];
  assert.equal(SongChordEdit.draggedChord(chords, "abcdef", 1, 3, 3), null);
});

test("a drag can take a chord to another line, and a full line keeps it where it is", function () {
  var text = "abc\ndef";
  var step = SongChordEdit.draggedChord([chord(1)], text, 1, 1, 5);
  assert.equal(step.chordAt, 5);
  assert.deepEqual(positions(step.chords), [5]);
  // A line full of chords: the chord does not move, but the pointer does.
  var full = [chord(0), chord(1), chord(2), chord(5)];
  var stay = SongChordEdit.draggedChord(full, text, 5, 5, 1);
  assert.equal(stay.chordAt, 5);
  assert.equal(stay.finger, 1);
  assert.equal(stay.chords, full);
});

test("an arrow key moves a chord one letter, jumps over chords, and stops at the end of the line", function () {
  var text = "abcd\nefgh";
  var chords = [chord(0, 1), chord(1, 2), chord(3, 3)];
  var right = SongChordEdit.nudged(chords, text, 0, 1);
  assert.equal(right.chordAt, 2);
  assert.deepEqual(positions(right.chords), [2, 1, 3]);
  // No free letter to the right: it stays.
  assert.equal(SongChordEdit.nudged([chord(2), chord(3)], text, 2, 1), null);
  // The first letter of a line has no letter to the left (not the line above).
  assert.equal(SongChordEdit.nudged([chord(5)], text, 5, -1), null);
  // A letter with no chord has nothing to move.
  assert.equal(SongChordEdit.nudged(chords, text, 2, 1), null);
  assert.equal(SongChordEdit.nudged([chord(1)], text, 1, -1).chordAt, 0);
});

test("a typed chord replaces the one on the letter or is added in order, and is stored without the transpose", function () {
  var text = "abcdef";
  var chords = [chord(1, 1), chord(4, 4)];
  var added = SongChordEdit.replaced(chords, text, 2, "D", 0);
  assert.deepEqual(positions(added), [1, 2, 4]);
  assert.equal(added[1].noteId, 2);
  var replaced = SongChordEdit.replaced(chords, text, 1, "Am", 0);
  assert.deepEqual(positions(replaced), [1, 4]);
  assert.equal(replaced[0].noteId, 9);
  assert.equal(replaced[0].chordTypeId, 1);
  // Shown two half steps up: typing D is storing C.
  var stored = SongChordEdit.replaced([], text, 3, "D", 2);
  assert.equal(stored[0].noteId, 0);
  assert.equal(SongText.sheet(text, SongTranspose.shifted(stored, 2))[0].chords[0].text, "D");
  // Text that is not a chord is kept as an unrecognized chord, whatever the transpose.
  var odd = SongChordEdit.replaced([], text, 0, "xyz", 3);
  assert.equal(odd[0].unknown, true);
  assert.equal(SongText.sheet(text, SongTranspose.shifted(odd, 3))[0].chords[0].text, "xyz");
  assert.deepEqual(positions(chords), [1, 4]);
});

test("a chord is deleted from its letter only", function () {
  var chords = [chord(1), chord(2), chord(4)];
  assert.deepEqual(positions(SongChordEdit.deleted(chords, "abcdef", 2)), [1, 4]);
  assert.deepEqual(positions(SongChordEdit.deleted(chords, "abcdef", 3)), [1, 2, 4]);
});

test("m flips major and minor, an unrecognized chord stays", function () {
  var text = "abcdef";
  var chords = [chord(1, 0), chord(3, 7)];
  var minor = SongChordEdit.toggledMinor(chords, text, 3);
  assert.equal(minor[1].chordTypeId, 1);
  assert.equal(SongChordEdit.toggledMinor(minor, text, 3)[1].chordTypeId, 0);
  var odd = SongChordEdit.replaced([], text, 0, "??", 0);
  assert.equal(SongChordEdit.toggledMinor(odd, text, 0), null);
  assert.equal(SongChordEdit.toggledMinor(chords, text, 5), null);
  assert.equal(chords[0].noteId, 0);
});

test("the chord entry starts with the chord as it is shown", function () {
  var text = "abc\ndef";
  var chords = [chord(5, 9)];
  assert.equal(SongChordEdit.displayedChordText(text, chords, 5, 0), "A");
  assert.equal(SongChordEdit.displayedChordText(text, chords, 5, 3), "C");
  assert.equal(SongChordEdit.displayedChordText(text, chords, 4, 0), null);
  assert.equal(SongChordEdit.displayedChordText(text, chords, 3, 0), null);
});

test("the chord entry says what is typed, the same words as the iPhone app", function () {
  assert.deepEqual(SongChordEdit.entry("Am7"), { isValid: true, showsRed: false, footer: "Shown as Am7" });
  assert.deepEqual(SongChordEdit.entry("hello"), {
    isValid: false, showsRed: true, footer: "Not a chord. Start with a note from A to G.",
  });
  assert.equal(SongChordEdit.entry("").isValid, false);
  assert.equal(SongChordEdit.entry("  C  ").isValid, true);
  // Same test as the parser and transposing use.
  ["C", "Dm", "F#m7", "Bb/D", "x", "", "H"].forEach(function (text) {
    assert.equal(SongChordEdit.entry(text).isValid, SoftchordChords.isValidChordText(text), text);
  });
});

test("an accented letter or an emoji is one letter: a chord lands on its start and never inside", function () {
  // "e" + combining acute (2 code points), then a, then a family emoji (5 code points), then b.
  var text = "e\u0301a\u{1F468}\u200D\u{1F469}\u200D\u{1F467}b";
  assert.equal(Array.from(text).length, 9);
  assert.equal(SongChordEdit.letterStart(text, 1), 0);
  assert.equal(SongChordEdit.letterStart(text, 4), 2 + 0 + 1);
  assert.equal(SongChordEdit.letterStart(text, 7), 3);
  // Moving onto the middle of a letter means that letter.
  assert.equal(SongChordEdit.nextFreeCharacter(text, 1, 1, [], false), 0);
  assert.equal(SongChordEdit.nextFreeCharacter(text, 5, 1, [], false), 3);
  // A jump goes over a letter that has a chord to the next letter, not the next code point.
  assert.equal(SongChordEdit.nextFreeCharacter(text, 0, 1, [0], false), 2);
  assert.equal(SongChordEdit.nextFreeCharacter(text, 3, 1, [3], false), 8);
  // An arrow key steps over the whole letter.
  var right = SongChordEdit.nudged([chord(0)], text, 0, 1);
  assert.equal(right.chordAt, 2);
  var again = SongChordEdit.nudged(right.chords, text, 2, 1);
  assert.equal(again.chordAt, 3);
  assert.equal(SongChordEdit.nudged(again.chords, text, 3, 1).chordAt, 8);
  assert.equal(SongChordEdit.nudged([chord(8)], text, 8, 1), null);
  assert.equal(SongChordEdit.nudged([chord(8)], text, 8, -1).chordAt, 3);
  // A chord that an old songbook put inside a letter is on that letter.
  assert.equal(SongChordEdit.chordAt([chord(1)], text, 0).characterNum, 1);
  var moved = SongChordEdit.draggedChord([chord(1)], text, 0, 0, 2);
  assert.equal(moved.chordAt, 2);
  assert.deepEqual(positions(moved.chords), [2]);
  // And typing on a letter replaces the chord that was stored inside it.
  assert.deepEqual(positions(SongChordEdit.replaced([chord(1)], text, 0, "C", 0)), [0]);
  assert.deepEqual(SongChordEdit.deleted([chord(1)], text, 1), []);
});

test("the neighbouring letter on the line", function () {
  var text = "abc\n\nde\nfghi";
  assert.equal(SongChordEdit.neighbour(text, 0, 1), 1);
  assert.equal(SongChordEdit.neighbour(text, 2, 1), null);
  assert.equal(SongChordEdit.neighbour(text, 0, -1), null);
  assert.equal(SongChordEdit.neighbour(text, 3, 1), null, "a line break has no letter");
});

// MIRRORED: test_song.py TestChordRoom and softChord_ViewerTests chordRoomRightOfTheLine
// use the same text and moves.
test("a chord moves up to 10 letters right of its line, and the spaces go again", function () {
  let text = "Hi you\nab";
  let chords = [chord(5, 1), chord(7, 2)];
  let at = 5;
  function nudge(direction) {
    const room = SongChordEdit.withRoom(text, chords, at);
    const step = SongChordEdit.nudged(room.chords, room.text, at, direction);
    if (!step) {
      return false;
    }
    const tidy = SongChordEdit.tidied(room.text, step.chords, step.chordAt);
    text = tidy.text;
    chords = tidy.chords;
    at = tidy.index;
    return true;
  }
  assert.ok(nudge(1));
  assert.equal(text, "Hi you \nab");
  assert.deepEqual(positions(chords), [6, 8]);
  for (let i = 0; i < 9; i++) {
    assert.ok(nudge(1));
  }
  assert.equal(text, "Hi you" + " ".repeat(10) + "\nab");
  assert.deepEqual(positions(chords), [15, 17]);
  assert.equal(nudge(1), false, "no more than 10");
  for (let i = 0; i < 10; i++) {
    assert.ok(nudge(-1));
  }
  assert.equal(text, "Hi you\nab");
  assert.deepEqual(positions(chords), [5, 7]);
});

test("tidied keeps the spaces a chord needs, other lines, lines of only spaces and tabs", function () {
  const text = "ab   \n   \nc \t\nd    x\ne  \nf  ";
  const tidy = SongChordEdit.tidied(text, [chord(3), chord(14), chord(25)], 3, [3, 7, 11, 15, 22]);
  assert.equal(tidy.text, "ab  \n   \nc \t\nd    x\ne\nf  ");
  assert.deepEqual(positions(tidy.chords), [3, 13, 22]);
  assert.equal(tidy.index, 3);
  const deleted = SongChordEdit.tidied("ab  ", [], 3);
  assert.equal(deleted.text, "ab");
  assert.equal(deleted.index, 2);
});
