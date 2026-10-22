//
//  softchord_chords.swift
//  softChord Viewer
//
//  Paired with src/softchord_chords.py. Shared functions stay in this order:
//  preferFromMajorTonic, scoreKey, familyScore, bestDetectedKey,
//  detectRegionStartIndices, transposeNote.

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
    private static let minorTypeIds: Set<Int> = [1, 4, 9]
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
        return DetectedKey(prefer: best.prefer, score: best.score, majorTonic: best.majorTonic)
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

    /// Mirror: softchord_song.py SongChord.getChordText.
    static func chordText(_ chord: SongChord, prefer: Int) -> String {
        let note = noteString(chord.noteId, prefer: prefer)
        let type = typePrints.indices.contains(chord.chordTypeId) ? typePrints[chord.chordTypeId] : ""
        var text = chord.marker.isEmpty ? note + type : "\(chord.marker):\(note)\(type)"
        if chord.bassNoteId != -1 {
            text += "/" + noteString(chord.bassNoteId, prefer: prefer)
        }
        if chord.inParentheses {
            text = "(\(text))"
        }
        return text
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

// TODO: Port key_label and format_auto_detected_key_text from softchord_chords.py
// so the song page can show the detected key. bestDetectedKey here keeps
// prefer and score only. Leave the editor's key label as it is.

/// Half-step shifts for the open song. Nothing here is written to the songbook.
nonisolated enum SongTranspose {
    /// Mirror: softchord_song.py Song.transpose.
    /// The desktop saves the new chords. This copy stays in memory until the song is closed.
    nonisolated static func shifted(_ chords: [SongChord], by steps: Int) -> [SongChord] {
        guard SoftchordChords.transposeNote(0, steps: steps) != 0 else {
            return chords
        }
        return chords.map { chord in
            var shifted = chord
            shifted.noteId = SoftchordChords.transposeNote(chord.noteId, steps: steps)
            if chord.bassNoteId != -1 {
                shifted.bassNoteId = SoftchordChords.transposeNote(chord.bassNoteId, steps: steps)
            }
            return shifted
        }
    }
}
