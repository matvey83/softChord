// Chord names, chord strings, transpose, and the auto-detected key.
// Paired with softChord Viewer/softChord Viewer/softchord_chords.swift
// and src/softchord_chords.py. The chord string format is in docs/chord_format.md.

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
  var UNKNOWN_CHORD_TEXT = "?";
  // Alternative names for a type. Mirror: alternative_type_names.
  var ALTERNATIVE_TYPE_NAMES = {
    "sus": "sus4", "s4": "sus4", "maj7": "M7", "2": "9", "(7)": "7", "dim": "°", "dim7": "°7",
  };
  var NATURAL_NOTE_IDS = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
  // Look-alike Russian letters and the European H. Mirror: replace_russian_characeters.
  var LETTER_FIXES = {
    "\u0415": "E", "\u0421": "C", "\u0412": "B", "\u0410": "A", "H": "B", "\u041D": "B",
  };
  var ACCIDENTAL_SYMBOLS = { "#": "♯", "b": "♭", "♯": "♯", "♭": "♭" };
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
      if (chords[c].unknown) {
        continue;
      }
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
    chords = chords.filter(function (chord) {
      return !chord.unknown;
    });
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

  // Mirror: softchord_chords.py classify_suffix. Returns [chordTypeId, isKnownType].
  function classifySuffix(suffix) {
    var id = TYPE_PRINTS.indexOf(suffix);
    if (id >= 0) {
      return [id, true];
    }
    if (Object.prototype.hasOwnProperty.call(ALTERNATIVE_TYPE_NAMES, suffix)) {
      return [TYPE_PRINTS.indexOf(ALTERNATIVE_TYPE_NAMES[suffix]), true];
    }
    if (suffix.charAt(0) === "-") {
      return [1, false];
    }
    if (suffix.charAt(0) === "m" && suffix.slice(0, 2) !== "ma") {
      return [1, false];
    }
    return [0, false];
  }

  // Split a leading note name off an array of characters.
  // Mirror: softchord_chords.py _read_note.
  function readNote(chars) {
    if (!chars.length) {
      return null;
    }
    var letter = Object.prototype.hasOwnProperty.call(LETTER_FIXES, chars[0])
      ? LETTER_FIXES[chars[0]]
      : chars[0];
    if (!Object.prototype.hasOwnProperty.call(NATURAL_NOTE_IDS, letter)) {
      return null;
    }
    var noteId = NATURAL_NOTE_IDS[letter];
    var rest = chars.slice(1);
    var accidental = "";
    if (rest.length && Object.prototype.hasOwnProperty.call(ACCIDENTAL_SYMBOLS, rest[0])) {
      accidental = ACCIDENTAL_SYMBOLS[rest[0]];
      rest = rest.slice(1);
      noteId = mod12(noteId + (accidental === "♯" ? 1 : -1));
    }
    return { letter: letter, accidental: accidental, rest: rest, noteId: noteId };
  }

  // Parse a chord string. Tolerant: never fails, even for garbage.
  // Mirror: softchord_chords.py parse_chord.
  function parseChord(text) {
    var parsed = {
      unknown: true,
      raw: UNKNOWN_CHORD_TEXT,
      marker: "",
      inParentheses: false,
      rootText: "",
      noteId: -1,
      suffix: "",
      chordTypeId: -1,
      isKnownType: false,
      bassText: "",
      bassNoteId: -1,
      isMinor: false,
    };
    var raw = text == null ? "" : String(text).trim();
    parsed.raw = raw === "" ? UNKNOWN_CHORD_TEXT : raw;

    var body = Array.from(raw);
    var parens = body.length >= 2 && body[0] === "(" && body[body.length - 1] === ")";
    if (parens) {
      body = body.slice(1, body.length - 1);
    }
    var marker = "";
    var colon = body.indexOf(":");
    if (colon >= 0) {
      marker = body.slice(0, colon).join("");
      body = body.slice(colon + 1);
    }

    var note = readNote(body);
    if (!note) {
      return parsed;
    }
    var rest = note.rest;
    var bassText = "";
    var bassNoteId = -1;
    var slash = rest.lastIndexOf("/");
    if (slash >= 0) {
      var bass = readNote(rest.slice(slash + 1));
      if (bass && bass.rest.length === 0) {
        bassText = bass.letter + bass.accidental;
        bassNoteId = bass.noteId;
        rest = rest.slice(0, slash);
      }
    }
    var suffix = rest.join("");
    var typed = classifySuffix(suffix);
    parsed.unknown = false;
    parsed.marker = marker;
    parsed.inParentheses = parens;
    parsed.rootText = note.letter + note.accidental;
    parsed.noteId = note.noteId;
    parsed.isKnownType = typed[1];
    parsed.chordTypeId = typed[0];
    parsed.suffix = typed[1] ? TYPE_PRINTS[typed[0]] : suffix;
    parsed.bassText = bassText;
    parsed.bassNoteId = bassNoteId;
    parsed.isMinor = !!MINOR_TYPE_IDS[typed[0]];
    return parsed;
  }

  // The stored string of a known chord. Mirror: softchord_chords.py chord_string.
  function chordString(marker, rootText, suffix, bassText, inParentheses) {
    var text = rootText + suffix;
    if (marker) {
      text = marker + ":" + text;
    }
    if (bassText) {
      text += "/" + bassText;
    }
    if (inParentheses) {
      text = "(" + text + ")";
    }
    return text;
  }

  // The canonical string for a parsed chord. An unknown chord keeps its raw text.
  function parsedChordString(parsed) {
    if (parsed.unknown) {
      return parsed.raw;
    }
    return chordString(
      parsed.marker, parsed.rootText, parsed.suffix, parsed.bassText, parsed.inParentheses);
  }

  // A chord from its stored string. Never fails: text that cannot be read
  // becomes an unknown chord. Mirror: softchord_song.py SongChord.from_text.
  function chordFromText(text, characterNum) {
    var parsed = parseChord(text);
    if (parsed.unknown) {
      return {
        characterNum: characterNum,
        noteId: -1,
        chordTypeId: 0,
        bassNoteId: -1,
        marker: "",
        inParentheses: false,
        suffix: null,
        rootText: null,
        bassText: null,
        unknown: true,
        raw: parsed.raw,
      };
    }
    return {
      characterNum: characterNum,
      noteId: parsed.noteId,
      chordTypeId: parsed.chordTypeId,
      bassNoteId: parsed.bassNoteId,
      marker: parsed.marker,
      inParentheses: parsed.inParentheses,
      suffix: parsed.isKnownType ? null : parsed.suffix,
      rootText: parsed.rootText,
      bassText: parsed.bassText || null,
      unknown: false,
      raw: UNKNOWN_CHORD_TEXT,
    };
  }

  // Mirror: softchord_song.py SongChord.getChordText. An unknown chord is "?".
  function chordText(chord, prefer) {
    if (chord.unknown) {
      return UNKNOWN_CHORD_TEXT;
    }
    var note = chord.rootText || noteString(chord.noteId, prefer);
    var type = chord.suffix != null
      ? chord.suffix
      : (chord.chordTypeId >= 0 && chord.chordTypeId < TYPE_PRINTS.length
        ? TYPE_PRINTS[chord.chordTypeId]
        : "");
    var bass = "";
    if (chord.bassNoteId != null && chord.bassNoteId !== -1) {
      bass = chord.bassText || noteString(chord.bassNoteId, prefer);
    }
    return chordString(chord.marker || "", note, type, bass, !!chord.inParentheses);
  }

  function shifted(chords, steps) {
    if (transposeNote(0, steps) === 0) {
      return chords;
    }
    return chords.map(function (chord) {
      if (chord.unknown) {
        return chord;
      }
      // Only the root and bass change. The suffix is kept as it is.
      var copy = Object.assign({}, chord);
      copy.noteId = transposeNote(chord.noteId, steps);
      copy.rootText = null;
      if (chord.bassNoteId !== -1) {
        copy.bassNoteId = transposeNote(chord.bassNoteId, steps);
        copy.bassText = null;
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
      classifySuffix: classifySuffix,
      parseChord: parseChord,
      chordString: chordString,
      parsedChordString: parsedChordString,
      chordFromText: chordFromText,
      unknownChordText: UNKNOWN_CHORD_TEXT,
    },
    SongTranspose: {
      shifted: shifted,
    },
  };
});
