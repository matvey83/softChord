// Clipboard text and the chords anchored to each lyric line.
// Paired with softChord Viewer/softChord Viewer/softchord_text.swift.

(function (root, factory) {
  var chordsApi = typeof root.SoftchordChords !== "undefined"
    ? { SoftchordChords: root.SoftchordChords }
    : require("./softchord_chords");
  var api = factory(chordsApi.SoftchordChords);
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    root.SongText = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function (SoftchordChords) {
  function isWhitespace(ch) {
    return /\s/u.test(ch);
  }

  function rstrip(chars) {
    var end = chars.length;
    while (end > 0 && isWhitespace(chars[end - 1])) {
      end -= 1;
    }
    return chars.slice(0, end).join("");
  }

  // Center the chord on the anchor letter. An even-length name sits one
  // column to the right, and a name that would hang off the line is moved in.
  function place(chordText, cells, anchor) {
    var chars = Array.from(chordText);
    var chordLen = chars.length;
    if (chordLen === 0 || cells.length === 0) {
      return;
    }
    var left = anchor - Math.floor(chordLen / 2);
    if (chordLen % 2 === 0) {
      left += 1;
    }
    var right = left + chordLen;
    while (left < 0) {
      left += 1;
      right += 1;
    }
    while (right >= cells.length) {
      right -= 1;
      left -= 1;
    }
    for (var offset = 0; offset < chars.length; offset++) {
      var index = offset + left;
      if (index < 0) {
        index += cells.length;
      }
      if (index >= 0 && index < cells.length) {
        cells[index] = chars[offset];
      }
    }
  }

  // The letters a reader sees: a base letter with its accents, an emoji with its
  // skin tone or its joiners, a flag, are each one letter even though they are
  // several code points. Chords are stored by code point, so each letter also
  // says where it starts. Without Intl.Segmenter (old browsers) every code point
  // is a letter, as before.
  var segmenter = typeof Intl !== "undefined" && typeof Intl.Segmenter === "function"
    ? new Intl.Segmenter(undefined, { granularity: "grapheme" })
    : null;

  // The letters of one line as strings. Joined, they are the line.
  function letters(line) {
    if (!segmenter) {
      return Array.from(line);
    }
    var found = [];
    var parts = segmenter.segment(line);
    for (var part of parts) {
      found.push(part.segment);
    }
    return found;
  }

  function linesOf(text) {
    return text.split("\n").map(function (line) {
      return Array.from(line);
    });
  }

  // Where each line starts, as a code point index in the song (lines are joined by
  // one line break). Worked out once per song, so a chord finds its line by binary
  // search instead of walking all the lines.
  function lineStarts(lines) {
    var starts = [];
    var at = 0;
    for (var i = 0; i < lines.length; i++) {
      starts.push(at);
      at += lines[i].length + 1;
    }
    return starts;
  }

  // Line and column of a letter. A line break, a negative number and a number
  // past the end have no letter, so a chord stored there is not drawn.
  function lineAndColumn(songChar, lines, starts) {
    if (songChar < 0 || !lines.length) {
      return null;
    }
    var low = 0;
    var high = lines.length - 1;
    while (low < high) {
      var middle = (low + high + 1) >> 1;
      if (starts[middle] <= songChar) {
        low = middle;
      } else {
        high = middle - 1;
      }
    }
    var column = songChar - starts[low];
    return column < lines[low].length ? [low, column] : null;
  }

  // For every line, the indexes of the chords that are drawn on it, in the order
  // they are given (a chord on a line break or past the end is on no line).
  function chordsByLine(chords, lines, starts) {
    var byLine = lines.map(function () { return []; });
    var found = [];
    for (var i = 0; i < chords.length; i++) {
      var at = lineAndColumn(chords[i].characterNum, lines, starts);
      found.push(at);
      if (at) {
        byLine[at[0]].push(i);
      }
    }
    return { byLine: byLine, found: found };
  }

  // The key detection below only looks at the roots and types of the chords, in
  // order, and it is slow for a long song (it tries every place to split it: about
  // 100 ms for 600 chords). Typing moves chords but rarely changes that sequence,
  // and a chord dragged along a line changes it only when it passes another chord,
  // and goes back to an order it had a moment ago when it is dragged back. So the
  // last few answers are kept, the oldest dropped first.
  var REGION_CACHE_SIZE = 32;
  var regionCache = new Map();

  // Unknown chords have no root, so they take no part in key detection.
  function regions(chords) {
    var sorted = chords.filter(function (chord) {
      return !chord.unknown;
    }).sort(function (a, b) {
      return a.characterNum - b.characterNum;
    });
    var signature = sorted.map(function (chord) {
      return chord.noteId + ":" + chord.chordTypeId;
    }).join("|");
    var groups = regionCache.get(signature);
    if (groups) {
      // Used just now, so it goes to the back of the line to be dropped.
      regionCache.delete(signature);
    } else {
      var starts = SoftchordChords.detectRegionStartIndices(sorted);
      groups = [];
      for (var index = 0; index < starts.length; index++) {
        var startIndex = starts[index];
        var endIndex = index + 1 < starts.length ? starts[index + 1] : sorted.length;
        var group = sorted.slice(startIndex, endIndex);
        var detected = SoftchordChords.bestDetectedKey(group);
        groups.push({
          first: group.length ? startIndex : -1,
          prefer: detected ? detected.prefer : SoftchordChords.preferNeither,
        });
      }
      if (regionCache.size >= REGION_CACHE_SIZE) {
        regionCache.delete(regionCache.keys().next().value);
      }
    }
    regionCache.set(signature, groups);
    return groups.map(function (group) {
      return {
        start: group.first >= 0 ? sorted[group.first].characterNum : 0,
        prefer: group.prefer,
      };
    });
  }

  function preferFor(charNum, regions) {
    var chosen = regions.length ? regions[0].prefer : SoftchordChords.preferNeither;
    for (var i = 0; i < regions.length; i++) {
      if (charNum >= regions[i].start) {
        chosen = regions[i].prefer;
      } else {
        break;
      }
    }
    return chosen;
  }

  function render(text, chords, includeChords) {
    var lines = linesOf(text);
    var placed = chordsByLine(chords, lines, lineStarts(lines));
    var spelling = regions(chords);
    var song = "";
    for (var lineNum = 0; lineNum < lines.length; lineNum++) {
      var line = lines[lineNum];
      var onLine = placed.byLine[lineNum];
      if (includeChords && onLine.length) {
        var cells = [];
        for (var cell = 0; cell < line.length; cell++) {
          cells.push(" ");
        }
        for (var i = 0; i < onLine.length; i++) {
          var chord = chords[onLine[i]];
          var prefer = preferFor(chord.characterNum, spelling);
          place(SoftchordChords.chordText(chord, prefer), cells, placed.found[onLine[i]][1]);
        }
        song += rstrip(cells) + "\n";
      }
      var lyric = includeChords ? line.join("") : rstrip(line);
      song += lyric + "\n";
    }
    if (song.charAt(song.length - 1) === "\n") {
      song = song.slice(0, -1);
    }
    return song.split("\n").join("\r\n");
  }

  // For each code point of a line: the code point where its letter starts, and
  // how many code points the letter has. Null when every letter is one code point.
  function letterSpans(line) {
    var parts = letters(line.join(""));
    if (parts.length === line.length) {
      return null;
    }
    var starts = [];
    var lengths = [];
    var at = 0;
    for (var i = 0; i < parts.length; i++) {
      var size = Array.from(parts[i]).length;
      for (var k = 0; k < size; k++) {
        starts.push(at);
        lengths.push(size);
      }
      at += size;
    }
    return { starts: starts, lengths: lengths };
  }

  // The chords of every line, each with the column of its letter. A chord stored
  // on an accent or on a joiner is drawn over the whole letter, so its anchor is
  // where the letter starts, and span (only when more than 1) says how many code
  // points the letter has.
  function sheet(text, chords) {
    var lines = linesOf(text);
    var located = chordsByLine(chords, lines, lineStarts(lines));
    var spelling = regions(chords);
    return lines.map(function (line, lineNum) {
      var placed = [];
      var spans = null;
      var onLine = located.byLine[lineNum];
      if (onLine.length) {
        spans = letterSpans(line);
      }
      for (var i = 0; i < onLine.length; i++) {
        var chord = chords[onLine[i]];
        var column = located.found[onLine[i]][1];
        var prefer = preferFor(chord.characterNum, spelling);
        var anchor = spans ? spans.starts[column] : column;
        var entry = {
          anchor: anchor,
          text: SoftchordChords.chordText(chord, prefer),
          unrecognized: !!chord.unknown,
        };
        if (spans && spans.lengths[column] > 1) {
          entry.span = spans.lengths[column];
        }
        placed.push(entry);
      }
      return { lyric: line.join(""), chords: placed };
    });
  }

  return {
    render: render,
    sheet: sheet,
    letters: letters,
  };
});
