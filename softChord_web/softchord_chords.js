// Chord names, transpose, and the auto-detected key.
// Paired with softChord Viewer/softChord Viewer/softchord_chords.swift.

(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    root.SoftchordChords = api.SoftchordChords;
    root.SongTranspose = api.SongTranspose;
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  var PREFER_SHARPS = 0;
  var PREFER_FLATS = 1;
  var PREFER_NEITHER = 2;

  var SHARP_NAMES = [
    "C", "C♯", "D", "D♯", "E", "F", "F♯", "G", "G♯", "A", "A♯", "B",
  ];
  var FLAT_NAMES = [
    "C", "D♭", "D", "E♭", "E", "F", "G♭", "G", "A♭", "A", "B♭", "B",
  ];
  var TYPE_PRINTS = [
    "", "m", "sus4", "M7", "m7", "7", "9", "aug", "6", "m6", "11", "°", "°7",
  ];
  var MINOR_TYPE_IDS = { 1: true, 4: true, 9: true };
  var SHARP_MAJOR_TONICS = { 7: true, 2: true, 9: true, 4: true, 11: true, 6: true };
  var FLAT_MAJOR_TONICS = { 5: true, 10: true, 3: true, 8: true, 1: true };
  var MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11];
  var MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10];

  function mod12(value) {
    var remainder = value % 12;
    return remainder >= 0 ? remainder : remainder + 12;
  }

  function preferFromMajorTonic(majorTonic) {
    if (SHARP_MAJOR_TONICS[majorTonic]) {
      return PREFER_SHARPS;
    }
    if (FLAT_MAJOR_TONICS[majorTonic]) {
      return PREFER_FLATS;
    }
    return PREFER_NEITHER;
  }

  function scoreKey(chords, tonic, isMinor) {
    var intervals = isMinor ? MINOR_SCALE : MAJOR_SCALE;
    var scale = {};
    for (var i = 0; i < intervals.length; i++) {
      scale[mod12(tonic + intervals[i])] = true;
    }
    var dominant = mod12(tonic + 7);
    var parsed = [];
    for (var c = 0; c < chords.length; c++) {
      parsed.push([chords[c].noteId, !!MINOR_TYPE_IDS[chords[c].chordTypeId]]);
    }
    var total = 0;
    for (var index = 0; index < parsed.length; index++) {
      var root = parsed[index][0];
      var qualityMinor = parsed[index][1];
      if (root === tonic) {
        total += 3;
        if (qualityMinor === isMinor) {
          total += 1;
        }
      } else if (root === dominant) {
        total += qualityMinor ? 1 : 2;
      } else if (scale[root]) {
        total += 1;
      }
      if (index + 1 < parsed.length) {
        var nextRoot = parsed[index + 1][0];
        var nextMinor = parsed[index + 1][1];
        if (root === dominant && !qualityMinor && nextRoot === tonic && nextMinor === isMinor) {
          total += 2;
        }
      }
    }
    return total;
  }

  function familyScore(chords, majorTonic) {
    var relativeMinor = mod12(majorTonic - 3);
    return Math.max(
      scoreKey(chords, majorTonic, false),
      scoreKey(chords, relativeMinor, true));
  }

  function bestDetectedKey(chords) {
    if (!chords.length) {
      return null;
    }
    var ranked = [];
    for (var majorTonic = 0; majorTonic < 12; majorTonic++) {
      var relativeMinor = mod12(majorTonic - 3);
      var majorScore = scoreKey(chords, majorTonic, false);
      var minorScore = scoreKey(chords, relativeMinor, true);
      var tonic;
      var isMinor;
      var score;
      if (majorScore >= minorScore) {
        tonic = majorTonic;
        isMinor = false;
        score = majorScore;
      } else {
        tonic = relativeMinor;
        isMinor = true;
        score = minorScore;
      }
      ranked.push({
        score: score,
        majorTonic: majorTonic,
        tonic: tonic,
        isMinor: isMinor,
        prefer: preferFromMajorTonic(majorTonic),
      });
    }
    ranked.sort(function (lhs, rhs) {
      if (lhs.score !== rhs.score) {
        return rhs.score - lhs.score;
      }
      if (lhs.majorTonic !== rhs.majorTonic) {
        return rhs.majorTonic - lhs.majorTonic;
      }
      if (lhs.tonic !== rhs.tonic) {
        return rhs.tonic - lhs.tonic;
      }
      if (lhs.isMinor !== rhs.isMinor) {
        return lhs.isMinor ? -1 : 1;
      }
      if (lhs.prefer !== rhs.prefer) {
        return rhs.prefer - lhs.prefer;
      }
      return 0;
    });
    var best = ranked[0];
    return { prefer: best.prefer, score: best.score, majorTonic: best.majorTonic };
  }

  function detectRegionStartIndices(chords) {
    function splits(seq, offset) {
      var count = seq.length;
      if (count < 10) {
        return [offset];
      }
      var whole = bestDetectedKey(seq);
      var wholeScore = whole ? whole.score : 0;
      var bestCut = null;
      var bestGain = 0;
      for (var cut = 5; cut <= count - 5; cut++) {
        var left = seq.slice(0, cut);
        var right = seq.slice(cut);
        var leftKey = bestDetectedKey(left);
        var rightKey = bestDetectedKey(right);
        if (!leftKey || !rightKey) {
          continue;
        }
        if (leftKey.majorTonic === rightKey.majorTonic) {
          continue;
        }
        var leftVersusRight = leftKey.score - familyScore(left, rightKey.majorTonic);
        var rightVersusLeft = rightKey.score - familyScore(right, leftKey.majorTonic);
        if (leftVersusRight < 1 || rightVersusLeft < 1) {
          continue;
        }
        var gain = leftKey.score + rightKey.score - wholeScore;
        if (gain > bestGain || (gain === bestGain && bestCut !== null)) {
          bestGain = gain;
          bestCut = cut;
        }
      }
      var minimumGain = 4;
      if (wholeScore !== 0) {
        minimumGain = Math.max(minimumGain, Math.trunc(0.2 * wholeScore));
      }
      if (bestCut === null || bestGain < minimumGain) {
        return [offset];
      }
      return splits(seq.slice(0, bestCut), offset).concat(
        splits(seq.slice(bestCut), offset + bestCut));
    }

    if (!chords.length) {
      return [];
    }
    return splits(chords, 0);
  }

  function transposeNote(noteId, steps) {
    return mod12(noteId + steps);
  }

  function noteString(noteId, prefer) {
    if (noteId < 0 || noteId >= SHARP_NAMES.length) {
      return "";
    }
    if (prefer === PREFER_SHARPS) {
      return SHARP_NAMES[noteId];
    }
    if (prefer === PREFER_FLATS) {
      return FLAT_NAMES[noteId];
    }
    // C and Am spell C♯ and F♯, and use flats for the other black keys.
    if (noteId === 1 || noteId === 6) {
      return SHARP_NAMES[noteId];
    }
    return FLAT_NAMES[noteId];
  }

  function chordText(chord, prefer) {
    var note = noteString(chord.noteId, prefer);
    var type = chord.chordTypeId >= 0 && chord.chordTypeId < TYPE_PRINTS.length
      ? TYPE_PRINTS[chord.chordTypeId]
      : "";
    var text = chord.marker ? chord.marker + ":" + note + type : note + type;
    if (chord.bassNoteId !== -1) {
      text += "/" + noteString(chord.bassNoteId, prefer);
    }
    if (chord.inParentheses) {
      text = "(" + text + ")";
    }
    return text;
  }

  function shifted(chords, steps) {
    if (transposeNote(0, steps) === 0) {
      return chords;
    }
    return chords.map(function (chord) {
      var copy = {
        characterNum: chord.characterNum,
        noteId: transposeNote(chord.noteId, steps),
        chordTypeId: chord.chordTypeId,
        bassNoteId: chord.bassNoteId,
        marker: chord.marker,
        inParentheses: chord.inParentheses,
      };
      if (chord.bassNoteId !== -1) {
        copy.bassNoteId = transposeNote(chord.bassNoteId, steps);
      }
      return copy;
    });
  }

  return {
    SoftchordChords: {
      preferSharps: PREFER_SHARPS,
      preferFlats: PREFER_FLATS,
      preferNeither: PREFER_NEITHER,
      preferFromMajorTonic: preferFromMajorTonic,
      scoreKey: scoreKey,
      familyScore: familyScore,
      bestDetectedKey: bestDetectedKey,
      detectRegionStartIndices: detectRegionStartIndices,
      transposeNote: transposeNote,
      chordText: chordText,
    },
    SongTranspose: {
      shifted: shifted,
    },
  };
});
