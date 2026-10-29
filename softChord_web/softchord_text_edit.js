// Moving chords along when the lyric text is edited. Pure functions, no DOM.
//
// Same rule as the desktop editor and the iPhone app, so a song edited on any
// of them keeps its chords on the same letters:
//   softchord_text.py     lyric_renumber_map
//   softchord_text.swift  SongLyricChords.renumberMap
// The unchanged start of the text and the unchanged end of the text keep their
// letters. A chord on a letter that was deleted or replaced is dropped. The end
// never reaches into the start (Hello to Helo keeps one l), so two old letters
// never map to one new letter and no two chords end up on the same letter.
// A chord that has no letter (past the end of the text, or below zero) is in
// neither the start nor the end, so the first edit drops it. One on a line break
// is kept like any other letter.
// tests/lyric_chord_vectors.json holds the cases all three test suites read.
//
// All positions are indexes of Unicode code points, like the chords' characterNum
// (a textarea reports UTF-16 offsets, so use codePointIndex to convert).

(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    root.SongTextEdit = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  function toArray(text) {
    return Array.isArray(text) ? text : Array.from(text);
  }

  // Old letter index -> index of that same letter in the new text, as a plain
  // object. A letter with no entry was deleted or replaced.
  function renumberMap(oldText, newText) {
    var previous = toArray(oldText);
    var text = toArray(newText);
    var map = {};
    var shortest = Math.min(previous.length, text.length);

    var prefix = 0;
    while (prefix < shortest && previous[prefix] === text[prefix]) {
      map[prefix] = prefix;
      prefix += 1;
    }

    var suffix = 0;
    while (suffix < shortest - prefix &&
           previous[previous.length - 1 - suffix] === text[text.length - 1 - suffix]) {
      map[previous.length - 1 - suffix] = text.length - 1 - suffix;
      suffix += 1;
    }
    return map;
  }

  // The chords that survive the edit, moved to their letters in newText.
  // The chords passed in are not changed. Their order is kept.
  function moveChords(chords, oldText, newText) {
    var map = renumberMap(oldText, newText);
    var moved = [];
    for (var i = 0; i < chords.length; i++) {
      var to = map[chords[i].characterNum];
      if (to === undefined) {
        continue;
      }
      var copy = {};
      for (var key in chords[i]) {
        if (Object.prototype.hasOwnProperty.call(chords[i], key)) {
          copy[key] = chords[i][key];
        }
      }
      copy.characterNum = to;
      moved.push(copy);
    }
    return moved;
  }

  // \r\n and a lone \r become \n. Every other character is kept as typed.
  function normalizeNewlines(text) {
    return String(text).replace(/\r\n?/g, "\n");
  }

  // The song's text with \r\n and \r turned into \n, and its chords moved
  // to the same letters. The \r of a \r\n is gone, so a chord that sat on it
  // is dropped (it was on a line break, not on a letter).
  function normalizeSong(text, chords) {
    var letters = Array.from(String(text));
    var map = {};
    var out = [];
    for (var i = 0; i < letters.length; i++) {
      if (letters[i] === "\r") {
        if (letters[i + 1] === "\n") {
          continue;
        }
        map[i] = out.length;
        out.push("\n");
        continue;
      }
      map[i] = out.length;
      out.push(letters[i]);
    }
    var moved = [];
    for (var c = 0; c < chords.length; c++) {
      var to = map[chords[c].characterNum];
      if (to === undefined) {
        continue;
      }
      var copy = Object.assign({}, chords[c]);
      copy.characterNum = to;
      moved.push(copy);
    }
    return { text: out.join(""), chords: moved };
  }

  // Code point index for a UTF-16 offset in text (what a textarea selection
  // reports). An offset in the middle of a surrogate pair counts that pair.
  function codePointIndex(text, utf16Offset) {
    var count = 0;
    var offset = 0;
    var limit = Math.min(Math.max(utf16Offset, 0), text.length);
    while (offset < limit) {
      var code = text.charCodeAt(offset);
      var pair = code >= 0xd800 && code <= 0xdbff && offset + 1 < text.length;
      offset += pair ? 2 : 1;
      count += 1;
    }
    return count;
  }

  // How many snapshots (text and chords) an edit keeps for Undo and Redo. Each one
  // holds all the chords of the song, so a long editing session is cut off here.
  // Undo goes on past it with the browser's own text undo, and the chords then
  // follow their letters with moveChords (chords dropped earlier stay dropped).
  var HISTORY_LIMIT = 200;

  // Makes snapshot the newest of history (cutting off what Redo would have gone to)
  // and drops the oldest ones above the limit. Changes history; returns the new
  // current index.
  function pushSnapshot(history, index, snapshot, limit) {
    history.length = index + 1;
    history.push(snapshot);
    var over = history.length - (limit || HISTORY_LIMIT);
    if (over > 0) {
      history.splice(0, over);
    }
    return history.length - 1;
  }

  return {
    HISTORY_LIMIT: HISTORY_LIMIT,
    pushSnapshot: pushSnapshot,
    renumberMap: renumberMap,
    moveChords: moveChords,
    normalizeNewlines: normalizeNewlines,
    normalizeSong: normalizeSong,
    codePointIndex: codePointIndex,
  };
});
