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

  function linesOf(text) {
    return text.split("\n").map(function (line) {
      return Array.from(line);
    });
  }

  // Line and column of a letter. A line break, a negative number and a number
  // past the end have no letter, so a chord stored there is not drawn.
  function lineAndColumn(songChar, lines) {
    if (songChar < 0) {
      return null;
    }
    var start = 0;
    for (var lineNum = 0; lineNum < lines.length; lineNum++) {
      var end = start + lines[lineNum].length + 1;
      if (songChar < end - 1) {
        return [lineNum, songChar - start];
      }
      if (songChar === end - 1) {
        return null;
      }
      start = end;
    }
    return null;
  }

  function lineHasChords(lineNum, chords, lines) {
    for (var i = 0; i < chords.length; i++) {
      var found = lineAndColumn(chords[i].characterNum, lines);
      if (found && found[0] === lineNum) {
        return true;
      }
    }
    return false;
  }

  // Unknown chords have no root, so they take no part in key detection.
  function regions(chords) {
    var sorted = chords.filter(function (chord) {
      return !chord.unknown;
    }).sort(function (a, b) {
      return a.characterNum - b.characterNum;
    });
    var starts = SoftchordChords.detectRegionStartIndices(sorted);
    var found = [];
    for (var index = 0; index < starts.length; index++) {
      var startIndex = starts[index];
      var endIndex = index + 1 < starts.length ? starts[index + 1] : sorted.length;
      var group = sorted.slice(startIndex, endIndex);
      var detected = SoftchordChords.bestDetectedKey(group);
      var prefer = detected ? detected.prefer : SoftchordChords.preferNeither;
      found.push({
        start: group.length ? group[0].characterNum : 0,
        prefer: prefer,
      });
    }
    return found;
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
    var spelling = regions(chords);
    var song = "";
    for (var lineNum = 0; lineNum < lines.length; lineNum++) {
      var line = lines[lineNum];
      if (includeChords && lineHasChords(lineNum, chords, lines)) {
        var cells = [];
        for (var cell = 0; cell < line.length; cell++) {
          cells.push(" ");
        }
        for (var i = 0; i < chords.length; i++) {
          var found = lineAndColumn(chords[i].characterNum, lines);
          if (!found || found[0] !== lineNum) {
            continue;
          }
          var prefer = preferFor(chords[i].characterNum, spelling);
          place(SoftchordChords.chordText(chords[i], prefer), cells, found[1]);
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

  function sheet(text, chords) {
    var lines = linesOf(text);
    var spelling = regions(chords);
    return lines.map(function (line, lineNum) {
      var placed = [];
      for (var i = 0; i < chords.length; i++) {
        var found = lineAndColumn(chords[i].characterNum, lines);
        if (!found || found[0] !== lineNum) {
          continue;
        }
        var prefer = preferFor(chords[i].characterNum, spelling);
        placed.push({
          anchor: found[1],
          text: SoftchordChords.chordText(chords[i], prefer),
          unrecognized: !!chords[i].unknown,
        });
      }
      return { lyric: line.join(""), chords: placed };
    });
  }

  return {
    render: render,
    sheet: sheet,
  };
});
