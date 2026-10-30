//
//  softchord_chords.swift
//  softChord Viewer
//
//  Paired with src/softchord_chords.py. Shared functions stay in this order:
//  preferFromMajorTonic, scoreKey, familyScore, bestDetectedKey,
//  detectRegionStartIndices, transposeNote, parseChord, isValidChordText, chordString.

import Foundation

/// Chord names, transpose, and auto-detected key. No UI.
nonisolated enum SoftchordChords {
    static let preferSharps = 0
    static let preferFlats = 1
    static let preferNeither = 2

    private static let sharpNames = [
        "C", "C♯", "D", "D♯", "E", "F", "F♯", "G", "G♯", "A", "A♯", "B",
    ]
    private static let flatNames = [
        "C", "D♭", "D", "E♭", "E", "F", "G♭", "G", "A♭", "A", "B♭", "B",
    ]
    private static let typePrints = [
        "", "m", "sus4", "M7", "m7", "7", "9", "aug", "6", "m6", "11", "°", "°7",
    ]
    fileprivate static let minorTypeIds: Set<Int> = [1, 4, 9]
    /// Alternative names for a type. Mirror: alternative_type_names.
    private static let alternativeTypeNames = [
        "sus": "sus4", "s4": "sus4", "maj7": "M7", "2": "9", "(7)": "7", "dim": "°", "dim7": "°7",
    ]
    private static let naturalNoteIds: [Unicode.Scalar: Int] = [
        "C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11,
    ]
    /// Look-alike Russian letters and the European H. Mirror: replace_russian_characeters.
    private static let letterFixes: [Unicode.Scalar: Unicode.Scalar] = [
        "\u{0415}": "E", "\u{0421}": "C", "\u{0412}": "B", "\u{0410}": "A",
        "H": "B", "\u{041D}": "B",
    ]
    private static let accidentalSymbols: [Unicode.Scalar: String] = [
        "#": "♯", "b": "♭", "♯": "♯", "♭": "♭",
    ]
    /// Shown, in red, for a chord whose text is empty. Other text that is not a chord
    /// (for example "asdf" or "N.C.") is shown as it is, up to `unrecognizedMaxLength`
    /// characters, in red. A recognized chord is never shortened.
    static let unknownChordText = "?"
    static let unrecognizedMaxLength = 7
    private static let sharpMajorTonics: Set<Int> = [7, 2, 9, 4, 11, 6]
    private static let flatMajorTonics: Set<Int> = [5, 10, 3, 8, 1]
    private static let majorScale = [0, 2, 4, 5, 7, 9, 11]
    private static let minorScale = [0, 2, 3, 5, 7, 8, 10]

    private struct RankedKey {
        var score: Int
        var majorTonic: Int
        var tonic: Int
        var isMinor: Bool
        var prefer: Int
    }

    struct DetectedKey {
        var prefer: Int
        var score: Int
        var majorTonic: Int
        var tonic = 0
        var isMinor = false
    }

    /// Mirror: softchord_chords.py key_label ("F♯m", "B♭").
    static func keyLabel(tonic: Int, isMinor: Bool, prefer: Int) -> String {
        let names = prefer == preferFlats ? flatNames : sharpNames
        return names[mod12(tonic)] + (isMinor ? "m" : "")
    }

    /// Mirror: softchord_chords.py prefer_from_major_tonic.
    static func preferFromMajorTonic(_ majorTonic: Int) -> Int {
        if sharpMajorTonics.contains(majorTonic) {
            return preferSharps
        }
        if flatMajorTonics.contains(majorTonic) {
            return preferFlats
        }
        return preferNeither
    }

    /// Mirror: softchord_chords.py score_key.
    static func scoreKey(_ chords: [SongChord], tonic: Int, isMinor: Bool) -> Int {
        let intervals = isMinor ? minorScale : majorScale
        let scale = Set(intervals.map { mod12(tonic + $0) })
        let dominant = mod12(tonic + 7)
        let parsed = chords.map { ($0.noteId, minorTypeIds.contains($0.chordTypeId)) }
        var total = 0
        for (index, chord) in parsed.enumerated() {
            let (root, qualityMinor) = chord
            if root == tonic {
                total += 3
                if qualityMinor == isMinor {
                    total += 1
                }
            } else if root == dominant {
                total += qualityMinor ? 1 : 2
            } else if scale.contains(root) {
                total += 1
            }
            if index + 1 < parsed.count {
                let (nextRoot, nextMinor) = parsed[index + 1]
                if root == dominant && !qualityMinor && nextRoot == tonic && nextMinor == isMinor {
                    total += 2
                }
            }
        }
        return total
    }

    /// Mirror: softchord_chords.py family_score.
    static func familyScore(_ chords: [SongChord], majorTonic: Int) -> Int {
        let relativeMinor = mod12(majorTonic - 3)
        return max(
            scoreKey(chords, tonic: majorTonic, isMinor: false),
            scoreKey(chords, tonic: relativeMinor, isMinor: true))
    }

    /// Mirror: softchord_chords.py best_detected_key.
    /// The desktop also builds a key label. Callers here only need the spelling.
    static func bestDetectedKey(_ chords: [SongChord]) -> DetectedKey? {
        if chords.isEmpty {
            return nil
        }
        var ranked: [RankedKey] = []
        for majorTonic in 0..<12 {
            let relativeMinor = mod12(majorTonic - 3)
            let majorScore = scoreKey(chords, tonic: majorTonic, isMinor: false)
            let minorScore = scoreKey(chords, tonic: relativeMinor, isMinor: true)
            let tonic: Int
            let isMinor: Bool
            let score: Int
            if majorScore >= minorScore {
                tonic = majorTonic
                isMinor = false
                score = majorScore
            } else {
                tonic = relativeMinor
                isMinor = true
                score = minorScore
            }
            ranked.append(RankedKey(
                score: score,
                majorTonic: majorTonic,
                tonic: tonic,
                isMinor: isMinor,
                prefer: preferFromMajorTonic(majorTonic)))
        }
        ranked.sort { lhs, rhs in
            if lhs.score != rhs.score { return lhs.score > rhs.score }
            if lhs.majorTonic != rhs.majorTonic { return lhs.majorTonic > rhs.majorTonic }
            if lhs.tonic != rhs.tonic { return lhs.tonic > rhs.tonic }
            if lhs.isMinor != rhs.isMinor { return lhs.isMinor && !rhs.isMinor }
            return lhs.prefer > rhs.prefer
        }
        let best = ranked[0]
        return DetectedKey(prefer: best.prefer, score: best.score, majorTonic: best.majorTonic,
                           tonic: best.tonic, isMinor: best.isMinor)
    }

    /// Mirror: softchord_chords.py detect_region_start_indices.
    static func detectRegionStartIndices(_ chords: [SongChord]) -> [Int] {
        func splits(_ seq: [SongChord], offset: Int) -> [Int] {
            let count = seq.count
            if count < 10 {
                return [offset]
            }
            let wholeScore = bestDetectedKey(seq)?.score ?? 0
            var bestCut: Int?
            var bestGain = 0
            for cut in 5...(count - 5) {
                let left = Array(seq[..<cut])
                let right = Array(seq[cut...])
                guard let leftKey = bestDetectedKey(left), let rightKey = bestDetectedKey(right) else {
                    continue
                }
                if leftKey.majorTonic == rightKey.majorTonic {
                    continue
                }
                let leftVersusRight = leftKey.score - familyScore(left, majorTonic: rightKey.majorTonic)
                let rightVersusLeft = rightKey.score - familyScore(right, majorTonic: leftKey.majorTonic)
                if leftVersusRight < 1 || rightVersusLeft < 1 {
                    continue
                }
                let gain = leftKey.score + rightKey.score - wholeScore
                if gain > bestGain || (gain == bestGain && bestCut != nil) {
                    bestGain = gain
                    bestCut = cut
                }
            }
            var minimumGain = 4
            if wholeScore != 0 {
                minimumGain = max(minimumGain, Int(0.2 * Double(wholeScore)))
            }
            guard let bestCut, bestGain >= minimumGain else {
                return [offset]
            }
            return splits(Array(seq[..<bestCut]), offset: offset)
                + splits(Array(seq[bestCut...]), offset: offset + bestCut)
        }

        if chords.isEmpty {
            return []
        }
        return splits(chords, offset: 0)
    }

    /// Mirror: softchord_chords.py transpose_note.
    /// Any number of half steps is folded into one octave. One half step matches the desktop.
    static func transposeNote(_ noteId: Int, steps: Int) -> Int {
        mod12(noteId + steps)
    }

    /// What to draw for text that is not a chord: its first 7 characters. A character
    /// is a Unicode scalar, as in the other versions, so a Russian word or an emoji
    /// counts one each. Empty text is "?". Mirror: softchord_chords.py unrecognized_chord_display.
    static func unrecognizedChordDisplay(_ raw: String) -> String {
        let text = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        if text.isEmpty {
            return unknownChordText
        }
        return String(String.UnicodeScalarView(text.unicodeScalars.prefix(unrecognizedMaxLength)))
    }

    /// The fields of one chord string. Mirror: softchord_chords.py ParsedChord.
    struct ParsedChord: Equatable {
        var unknown = true
        var raw = SoftchordChords.unknownChordText
        var display = SoftchordChords.unknownChordText
        var marker = ""
        var inParentheses = false
        var rootText = ""
        var noteId = -1
        var suffix = ""
        var chordTypeId = -1
        var isKnownType = false
        var bassText = ""
        var bassNoteId = -1

        var isMinor: Bool {
            !unknown && SoftchordChords.minorTypeIds.contains(chordTypeId)
        }
    }

    /// Mirror: softchord_chords.py classify_suffix. Returns (chordTypeId, isKnownType).
    static func classifySuffix(_ suffix: String) -> (Int, Bool) {
        if let id = typePrints.firstIndex(of: suffix) {
            return (id, true)
        }
        if let official = alternativeTypeNames[suffix], let id = typePrints.firstIndex(of: official) {
            return (id, true)
        }
        if suffix.hasPrefix("-") {
            return (1, false)
        }
        if suffix.hasPrefix("m") && !suffix.hasPrefix("ma") {
            return (1, false)
        }
        return (0, false)
    }

    private static func scalarString(_ scalars: ArraySlice<Unicode.Scalar>) -> String {
        String(String.UnicodeScalarView(scalars))
    }

    /// Split a leading note name off the text. Mirror: softchord_chords.py _read_note.
    private static func readNote(_ text: ArraySlice<Unicode.Scalar>)
        -> (letter: Unicode.Scalar, accidental: String, rest: ArraySlice<Unicode.Scalar>, noteId: Int)? {
        guard let first = text.first else {
            return nil
        }
        let letter = letterFixes[first] ?? first
        guard var noteId = naturalNoteIds[letter] else {
            return nil
        }
        var rest = text.dropFirst()
        var accidental = ""
        if let next = rest.first, let symbol = accidentalSymbols[next] {
            accidental = symbol
            rest = rest.dropFirst()
            noteId = mod12(noteId + (symbol == "♯" ? 1 : -1))
        }
        return (letter, accidental, rest, noteId)
    }

    /// Parse a chord string. Tolerant: never fails, even for garbage.
    /// Mirror: softchord_chords.py parse_chord.
    static func parseChord(_ text: String) -> ParsedChord {
        var parsed = ParsedChord()
        let raw = text.trimmingCharacters(in: .whitespacesAndNewlines)
        parsed.raw = raw.isEmpty ? unknownChordText : raw
        parsed.display = unrecognizedChordDisplay(raw)

        var body = Array(raw.unicodeScalars)[...]
        let parens = body.count >= 2 && body.first == "(" && body.last == ")"
        if parens {
            body = body.dropFirst().dropLast()
        }

        var marker = ""
        if let colon = body.firstIndex(of: ":") {
            marker = scalarString(body[body.startIndex..<colon])
            body = body[(colon + 1)...]
        }

        guard let note = readNote(body) else {
            return parsed
        }

        var rest = note.rest
        var bassText = ""
        var bassNoteId = -1
        if let slash = rest.lastIndex(of: "/"),
           let bass = readNote(rest[(slash + 1)...]), bass.rest.isEmpty {
            bassText = String(bass.letter) + bass.accidental
            bassNoteId = bass.noteId
            rest = rest[rest.startIndex..<slash]
        }

        let suffix = scalarString(rest)
        let (typeId, known) = classifySuffix(suffix)
        parsed.unknown = false
        parsed.marker = marker
        parsed.inParentheses = parens
        parsed.rootText = String(note.letter) + note.accidental
        parsed.noteId = note.noteId
        parsed.isKnownType = known
        parsed.chordTypeId = typeId
        parsed.suffix = known ? typePrints[typeId] : suffix
        parsed.bassText = bassText
        parsed.bassNoteId = bassNoteId
        return parsed
    }

    /// True when typed text is a chord the editors may save: parseChord finds a root
    /// note, so transposing changes it. Empty text, "?" and text with no root are not.
    /// Mirror: softchord_chords.py is_valid_chord_text.
    static func isValidChordText(_ text: String) -> Bool {
        !parseChord(text).unknown
    }

    /// The stored string of a known chord. Mirror: softchord_chords.py chord_string.
    static func chordString(
        marker: String, rootText: String, suffix: String, bassText: String, inParentheses: Bool
    ) -> String {
        var text = rootText + suffix
        if !marker.isEmpty {
            text = marker + ":" + text
        }
        if !bassText.isEmpty {
            text += "/" + bassText
        }
        if inParentheses {
            text = "(" + text + ")"
        }
        return text
    }

    /// The canonical string for a parsed chord. Unknown chords keep their raw text.
    /// Mirror: softchord_chords.py parsed_chord_string.
    static func parsedChordString(_ parsed: ParsedChord) -> String {
        if parsed.unknown {
            return parsed.raw
        }
        return chordString(
            marker: parsed.marker, rootText: parsed.rootText, suffix: parsed.suffix,
            bassText: parsed.bassText, inParentheses: parsed.inParentheses)
    }

    /// Mirror: softchord_song.py SongChord.getChordText. An unrecognized chord is its
    /// first 7 characters ("?" when empty).
    static func chordText(_ chord: SongChord, prefer: Int) -> String {
        if chord.unknown {
            return unrecognizedChordDisplay(chord.raw)
        }
        let note = chord.rootText ?? noteString(chord.noteId, prefer: prefer)
        let type = chord.suffix
            ?? (typePrints.indices.contains(chord.chordTypeId) ? typePrints[chord.chordTypeId] : "")
        var bass = ""
        if chord.bassNoteId != -1 {
            bass = chord.bassText ?? noteString(chord.bassNoteId, prefer: prefer)
        }
        return chordString(
            marker: chord.marker, rootText: note, suffix: type, bassText: bass,
            inParentheses: chord.inParentheses)
    }

    private static func noteString(_ noteId: Int, prefer: Int) -> String {
        guard sharpNames.indices.contains(noteId) else {
            return ""
        }
        if prefer == preferSharps {
            return sharpNames[noteId]
        }
        if prefer == preferFlats {
            return flatNames[noteId]
        }
        // C and Am spell C♯ and F♯, and use flats for the other black keys.
        if noteId == 1 || noteId == 6 {
            return sharpNames[noteId]
        }
        return flatNames[noteId]
    }

    private static func mod12(_ value: Int) -> Int {
        let remainder = value % 12
        return remainder >= 0 ? remainder : remainder + 12
    }
}

// TODO: Port format_auto_detected_key_text from softchord_chords.py so the song
// page can show the detected key. Leave the editor's key label as it is.

/// Half-step shifts for the open song. Nothing here is written to the songbook.
nonisolated enum SongTranspose {
    /// True when `steps` changes the chords. A whole octave (12 half steps, up or
    /// down) shows the same chords, so it counts as not transposed. So does any
    /// number of steps when no chord has a root, because unrecognized chords do not
    /// move. Reset transpose and the "Changes do not persist" note both use this one
    /// rule. Mirror: softchord_song.py Song.has_transposable_chords.
    nonisolated static func changesChords(_ steps: Int, in chords: [SongChord]) -> Bool {
        steps % 12 != 0 && chords.contains { !$0.unknown }
    }

    /// Mirror: softchord_song.py Song.transpose.
    /// The desktop saves the new chords. This copy stays in memory until the song is closed.
    nonisolated static func shifted(_ chords: [SongChord], by steps: Int) -> [SongChord] {
        guard SoftchordChords.transposeNote(0, steps: steps) != 0 else {
            return chords
        }
        return chords.map { chord in
            if chord.unknown {
                return chord
            }
            // Only the root and bass change. The suffix is kept as it is.
            var shifted = chord
            shifted.noteId = SoftchordChords.transposeNote(chord.noteId, steps: steps)
            shifted.rootText = nil
            if chord.bassNoteId != -1 {
                shifted.bassNoteId = SoftchordChords.transposeNote(chord.bassNoteId, steps: steps)
                shifted.bassText = nil
            }
            return shifted
        }
    }
}
