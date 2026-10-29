// The rules of Edit chords: which letter a moved chord lands on, and the changes
// a chord edit makes to the list of chords. Pure functions, no DOM.
//
// Same rules as the desktop editor and the iPhone app, so a song edited on any of
// them behaves the same:
//   softchord_text.py     next_free_character, chord_drag_direction, line_letter_range
//   softchord_text.swift  SongLyricChords.nextFreeCharacter, dragDirection, letterRange,
//                         draggedChord, reattached, replaced, deleted, ChordEntry
// tests/chord_move_vectors.json holds the jump and direction cases that all three
// test suites read.
//
// Positions are indexes of Unicode code points, like the chords' characterNum. The
// one difference from the other apps: the web sheet draws a letter with its accents
// or an emoji with its joiners as ONE letter (see SongText.letters), so a chord must
// never land inside one. Every function here works on whole letters: a position
// inside a letter means that letter, and a chord that was stored inside one counts
// as being on it. When every letter is one code point (plain text) this is exactly
// the other apps' rule.
//
// The chords are the objects of softchord_chords.js. Nothing here changes its
// arguments: a changed list is a new array, and a chord that moved is a copy.

(function (root, factory) {
  var chordsApi = typeof root.SoftchordChords !== "undefined" && typeof root.SongTranspose !== "undefined"
    ? { SoftchordChords: root.SoftchordChords, SongTranspose: root.SongTranspose }
    : require("./softchord_chords");
  var textApi = typeof root.SongText !== "undefined" ? root.SongText : require("./softchord_text");
  var api = factory(chordsApi.SoftchordChords, chordsApi.SongTranspose, textApi);
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    root.SongChordEdit = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function (SoftchordChords, SongTranspose, SongText) {
  // The last text looked at: its code points, and for each one the code point
  // where its letter starts. A drag asks again for every pointer move, with the
  // same text.
  var known = { text: null, points: [], starts: [] };

  function look(text) {
    if (known.text === text) {
      return known;
    }
    var points = Array.from(text);
    var starts = [];
    var lines = text.split("\n");
    var at = 0;
    for (var i = 0; i < lines.length; i++) {
      var letters = SongText.letters(lines[i]);
      for (var l = 0; l < letters.length; l++) {
        var size = Array.from(letters[l]).length;
        for (var k = 0; k < size; k++) {
          starts.push(at);
        }
        at += size;
      }
      if (i < lines.length - 1) {
        starts.push(at);
        at += 1;
      }
    }
    known = { text: text, points: points, starts: starts };
    return known;
  }

  // The code point where the letter holding index starts. An index outside the
  // text is its own letter (a chord with no letter is never on a drawn one).
  function letterStart(text, index) {
    var starts = look(text).starts;
    return index >= 0 && index < starts.length ? starts[index] : index;
  }

  function letterOf(text, chord) {
    return letterStart(text, chord.characterNum);
  }

  // The chord drawn on a letter (the first one, when an old songbook has two).
  function chordAt(chords, text, index) {
    var letter = letterStart(text, index);
    for (var i = 0; i < chords.length; i++) {
      if (letterOf(text, chords[i]) === letter) {
        return chords[i];
      }
    }
    return null;
  }

  // {first, last}: the first and last code point of the line that holds index.
  // Null for a line break, or an index that is not in the text. A chord can only
  // sit on a letter of its own line. Mirror: line_letter_range.
  function letterRange(text, index) {
    var points = look(text).points;
    if (index < 0 || index >= points.length || points[index] === "\n") {
      return null;
    }
    var first = index;
    while (first > 0 && points[first - 1] !== "\n") {
      first -= 1;
    }
    var last = index;
    while (last + 1 < points.length && points[last + 1] !== "\n") {
      last += 1;
    }
    return { first: first, last: last };
  }

  // The letter a chord lands on when it is moved onto target. A letter that has a
  // chord is jumped over, and so is every other one, to the next free letter of
  // the line in direction (1 right, -1 left). Chords are never lost and a letter
  // never gets two. With allowOtherDirection (a drag does, an arrow key does not) a
  // line with no free letter that way is tried the other way. Null means the chord
  // stays. occupied holds the letters that have a chord, without the chord that
  // moves. Mirror: next_free_character.
  function nextFreeCharacter(text, target, direction, occupied, allowOtherDirection) {
    var data = look(text);
    var start = letterStart(text, target);
    var range = letterRange(text, start);
    if (!range) {
      return null;
    }
    var taken = new Set(occupied);
    var step = direction < 0 ? -1 : 1;
    var steps = allowOtherDirection ? [step, -step] : [step];
    for (var s = 0; s < steps.length; s++) {
      var position = start;
      while (position >= range.first && position <= range.last) {
        if (data.starts[position] === position && !taken.has(position)) {
          return position;
        }
        position += steps[s];
      }
    }
    return null;
  }

  function lineStartIndex(points, index) {
    var start = Math.max(0, Math.min(index, points.length));
    while (start > 0 && points[start - 1] !== "\n") {
      start -= 1;
    }
    return start;
  }

  // 1 or -1: which way a chord dragged onto target goes past a chord. The pointer
  // moved from the letter previous to target. A target on another line than the
  // chord goes forward (1), as does no movement. Mirror: chord_drag_direction.
  function dragDirection(text, chord, previous, target) {
    var points = look(text).points;
    if (lineStartIndex(points, chord) !== lineStartIndex(points, target)) {
      return 1;
    }
    return target < previous ? -1 : 1;
  }

  // The letters that have a chord, as the code points where the letters start.
  function occupiedLetters(chords, text) {
    return new Set(chords.map(function (chord) { return letterOf(text, chord); }));
  }

  // The chord that was on the letter from now sits on the letter to. to has to be
  // free: a letter never gets two chords, so a move onto a letter that has a chord
  // changes nothing. Use nextFreeCharacter to find the letter to move to.
  // Mirror: reattached.
  function reattached(chords, text, from, to) {
    var start = letterStart(text, from);
    var end = letterStart(text, to);
    if (start === end || !chordAt(chords, text, start) || chordAt(chords, text, end)) {
      return chords;
    }
    return chords.map(function (chord) {
      if (letterOf(text, chord) !== start) {
        return chord;
      }
      var moved = Object.assign({}, chord);
      moved.characterNum = end;
      return moved;
    });
  }

  // One step of a chord drag. The pointer moved from the letter finger to target
  // while dragging the chord on the letter from. Null when the pointer is still on
  // the same letter. Otherwise {finger, chordAt, chords}: where the pointer and the
  // chord are now. The chord lands on the next free letter of its line in the
  // direction of the drag and chords are never lost. A chord that jumped over a
  // letter with a chord leaves the pointer on that letter, and staying there moves
  // nothing. Mirror: SongLyricChords.draggedChord.
  function draggedChord(chords, text, from, finger, target) {
    var start = letterStart(text, from);
    var over = letterStart(text, target);
    if (over === letterStart(text, finger)) {
      return null;
    }
    var occupied = occupiedLetters(chords, text);
    occupied.delete(start);
    var direction = dragDirection(text, start, letterStart(text, finger), over);
    var landing = nextFreeCharacter(text, over, direction, occupied, true);
    if (landing === null || landing === start) {
      return { finger: over, chordAt: start, chords: chords };
    }
    var next = reattached(chords, text, start, landing);
    if (next === chords) {
      return { finger: over, chordAt: start, chords: chords };
    }
    return { finger: over, chordAt: landing, chords: next };
  }

  // The letter next to the letter at on its line, in direction. Null at the end of
  // the line.
  function neighbour(text, index, direction) {
    var data = look(text);
    var start = letterStart(text, index);
    var range = letterRange(text, start);
    if (!range) {
      return null;
    }
    if (direction < 0) {
      return start > range.first ? data.starts[start - 1] : null;
    }
    var next = start + 1;
    while (next <= range.last && data.starts[next] === start) {
      next += 1;
    }
    return next <= range.last ? next : null;
  }

  // An arrow key on a chord: the chord moves to the next letter of its line,
  // jumping over letters that have a chord. Null when it stays (no free letter that
  // way, or the end of the line). Otherwise {chordAt, chords}.
  function nudged(chords, text, index, direction) {
    var start = letterStart(text, index);
    if (!chordAt(chords, text, start)) {
      return null;
    }
    var target = neighbour(text, start, direction);
    if (target === null) {
      return null;
    }
    var occupied = occupiedLetters(chords, text);
    occupied.delete(start);
    var landing = nextFreeCharacter(text, target, direction, occupied, false);
    if (landing === null || landing === start) {
      return null;
    }
    var next = reattached(chords, text, start, landing);
    return next === chords ? null : { chordAt: landing, chords: next };
  }

  // The chord typed for a letter. It replaces the chord there, or is added. The
  // sheet shows chords shifted by steps but keeps them as stored, so the typed
  // name is shifted back by the same steps before it is kept. Text that is not a
  // chord becomes an unrecognized chord and keeps the typed text.
  // Mirror: SongLyricChords.replaced.
  function replaced(chords, text, index, typed, steps) {
    var at = letterStart(text, index);
    var chord = SoftchordChords.chordFromText(typed, at);
    var stored = SongTranspose.shifted([chord], -steps)[0];
    var result = chords.filter(function (each) { return letterOf(text, each) !== at; });
    var place = result.length;
    for (var i = 0; i < result.length; i++) {
      if (result[i].characterNum > at) {
        place = i;
        break;
      }
    }
    result.splice(place, 0, stored);
    return result;
  }

  // Mirror: SongLyricChords.deleted.
  function deleted(chords, text, index) {
    var at = letterStart(text, index);
    return chords.filter(function (each) { return letterOf(text, each) !== at; });
  }

  function withChord(chords, text, index, change) {
    var at = letterStart(text, index);
    var changed = false;
    var result = chords.map(function (chord) {
      if (changed || letterOf(text, chord) !== at) {
        return chord;
      }
      changed = true;
      return change(Object.assign({}, chord));
    });
    return changed ? result : null;
  }

  // The m key: major becomes minor and any other chord becomes major. Null for no
  // chord and for an unrecognized chord. Same as the desktop editor's m key.
  function toggledMinor(chords, text, index) {
    var chord = chordAt(chords, text, index);
    if (!chord || chord.unknown) {
      return null;
    }
    return withChord(chords, text, index, function (copy) {
      copy.chordTypeId = copy.chordTypeId === 0 ? 1 : 0;
      copy.suffix = null;
      return copy;
    });
  }

  // What the sheet shows for the chord on a letter at the transpose steps (the chord
  // sheet starts with this), or null when the letter has no chord.
  function displayedChordText(text, chords, index, steps) {
    var at = letterStart(text, index);
    var lines = SongText.sheet(text, SongTranspose.shifted(chords, steps));
    var begin = 0;
    for (var i = 0; i < lines.length; i++) {
      var size = Array.from(lines[i].lyric).length;
      if (at >= begin && at < begin + size) {
        for (var c = 0; c < lines[i].chords.length; c++) {
          if (begin + lines[i].chords[c].anchor === at) {
            return lines[i].chords[c].text;
          }
        }
        return null;
      }
      begin += size + 1;
    }
    return null;
  }

  // What the chord entry says about the text typed so far. The field is red, and
  // OK and Return do nothing, while the text is not a chord. Mirror: ChordEntry.
  function entry(text) {
    var valid = SoftchordChords.isValidChordText(text);
    return {
      isValid: valid,
      showsRed: !valid,
      footer: valid
        ? "Shown as " + SoftchordChords.chordText(
          SoftchordChords.chordFromText(text, 0), SoftchordChords.preferNeither)
        : "Not a chord. Start with a note from A to G.",
    };
  }

  return {
    letterStart: letterStart,
    chordAt: chordAt,
    letterRange: letterRange,
    nextFreeCharacter: nextFreeCharacter,
    dragDirection: dragDirection,
    reattached: reattached,
    draggedChord: draggedChord,
    neighbour: neighbour,
    nudged: nudged,
    replaced: replaced,
    deleted: deleted,
    toggledMinor: toggledMinor,
    displayedChordText: displayedChordText,
    entry: entry,
  };
});
