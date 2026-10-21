//
//  SongText.swift
//  softChord Viewer
//

import Foundation

struct SongChord: Equatable {
    var characterNum: Int
    var noteId: Int
    var chordTypeId: Int
    var bassNoteId: Int
    var marker: String
    var inParentheses: Bool
}

nonisolated struct SongSheetChord: Equatable {
    var anchor: Int
    var text: String
}

nonisolated struct SongSheetLine: Equatable {
    var lyric: String
    var chords: [SongSheetChord]
}

/// Lyrics, or lyrics with a chord line above each line that has chords.
/// Names and columns match the editor's Copy Song Text commands.
enum SongText {
    nonisolated static func render(text: String, chords: [SongChord], includeChords: Bool) -> String {
        let lines = text.components(separatedBy: "\n").map { Array($0.unicodeScalars) }
        let spelling = regions(for: chords)
        var song = ""

        for (lineNum, line) in lines.enumerated() {
            if includeChords && lineHasChords(lineNum, chords: chords, lines: lines) {
                var cells = Array(repeating: Unicode.Scalar(" "), count: line.count)
                for chord in chords {
                    guard let (chordLine, anchor) = lineAndColumn(chord.characterNum, lines: lines),
                          chordLine == lineNum else {
                        continue
                    }
                    let prefer = prefer(for: chord.characterNum, regions: spelling)
                    place(chordText(chord, prefer: prefer), on: &cells, anchor: anchor)
                }
                song += rstrip(cells) + "\n"
            }

            var lyric = line
            if !includeChords {
                lyric = Array(rstrip(lyric).unicodeScalars)
            }
            song += String(String.UnicodeScalarView(lyric)) + "\n"
        }

        if song.hasSuffix("\n") {
            song.removeLast()
        }
        return song.replacingOccurrences(of: "\n", with: "\r\n")
    }

    /// One lyric line, with each chord named and anchored on a letter.
    nonisolated static func sheet(text: String, chords: [SongChord]) -> [SongSheetLine] {
        let lines = text.components(separatedBy: "\n").map { Array($0.unicodeScalars) }
        let spelling = regions(for: chords)
        return lines.enumerated().map { lineNum, line in
            var placed: [SongSheetChord] = []
            for chord in chords {
                guard let (chordLine, anchor) = lineAndColumn(chord.characterNum, lines: lines),
                      chordLine == lineNum else {
                    continue
                }
                let prefer = prefer(for: chord.characterNum, regions: spelling)
                placed.append(SongSheetChord(anchor: anchor, text: chordText(chord, prefer: prefer)))
            }
            return SongSheetLine(lyric: String(String.UnicodeScalarView(line)), chords: placed)
        }
    }

    private nonisolated static let sharpNames = [
        "C", "C♯", "D", "D♯", "E", "F", "F♯", "G", "G♯", "A", "A♯", "B",
    ]
    private nonisolated static let flatNames = [
        "C", "D♭", "D", "E♭", "E", "F", "G♭", "G", "A♭", "A", "B♭", "B",
    ]
    private nonisolated static let typePrints = [
        "", "m", "sus4", "M7", "m7", "7", "9", "aug", "6", "m6", "11", "°", "°7",
    ]
    private nonisolated static let minorTypeIds: Set<Int> = [1, 4, 9]
    private nonisolated static let sharpMajorTonics: Set<Int> = [7, 2, 9, 4, 11, 6]
    private nonisolated static let flatMajorTonics: Set<Int> = [5, 10, 3, 8, 1]
    private nonisolated static let majorScale = [0, 2, 4, 5, 7, 9, 11]
    private nonisolated static let minorScale = [0, 2, 3, 5, 7, 8, 10]
    private nonisolated static let preferSharps = 0
    private nonisolated static let preferFlats = 1
    private nonisolated static let preferNeither = 2

    private nonisolated static func chordText(_ chord: SongChord, prefer: Int) -> String {
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

    private nonisolated static func noteString(_ noteId: Int, prefer: Int) -> String {
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

    private nonisolated static func place(_ chordText: String, on cells: inout [Unicode.Scalar], anchor: Int) {
        let chars = Array(chordText.unicodeScalars)
        let chordLen = chars.count
        guard chordLen > 0, !cells.isEmpty else {
            return
        }
        var left = anchor - (chordLen / 2)
        if chordLen % 2 == 0 {
            left += 1
        }
        var right = left + chordLen
        while left < 0 {
            left += 1
            right += 1
        }
        while right >= cells.count {
            right -= 1
            left -= 1
        }
        for (offset, char) in chars.enumerated() {
            var index = offset + left
            if index < 0 {
                index += cells.count
            }
            if cells.indices.contains(index) {
                cells[index] = char
            }
        }
    }

    private nonisolated static func lineAndColumn(_ songChar: Int, lines: [[Unicode.Scalar]]) -> (Int, Int)? {
        var start = 0
        for (lineNum, line) in lines.enumerated() {
            let end = start + line.count + 1
            if songChar < end - 1 {
                return (lineNum, songChar - start)
            }
            start = end
        }
        return nil
    }

    private nonisolated static func lineHasChords(_ lineNum: Int, chords: [SongChord], lines: [[Unicode.Scalar]]) -> Bool {
        for chord in chords {
            if let (chordLine, _) = lineAndColumn(chord.characterNum, lines: lines), chordLine == lineNum {
                return true
            }
        }
        return false
    }

    private nonisolated static func rstrip(_ scalars: [Unicode.Scalar]) -> String {
        var end = scalars.count
        while end > 0 && scalars[end - 1].properties.isWhitespace {
            end -= 1
        }
        return String(String.UnicodeScalarView(scalars[..<end]))
    }

    private nonisolated static func mod12(_ value: Int) -> Int {
        let remainder = value % 12
        return remainder >= 0 ? remainder : remainder + 12
    }

    private nonisolated static func regions(for chords: [SongChord]) -> [(start: Int, prefer: Int)] {
        let sorted = chords.sorted { $0.characterNum < $1.characterNum }
        let starts = regionStarts(sorted)
        var found: [(start: Int, prefer: Int)] = []
        for (index, startIndex) in starts.enumerated() {
            let endIndex = index + 1 < starts.count ? starts[index + 1] : sorted.count
            let group = Array(sorted[startIndex..<endIndex])
            let prefer = bestKey(group)?.prefer ?? preferNeither
            found.append((group.first?.characterNum ?? 0, prefer))
        }
        return found
    }

    private nonisolated static func prefer(for charNum: Int, regions: [(start: Int, prefer: Int)]) -> Int {
        var chosen = regions.first?.prefer ?? preferNeither
        for region in regions {
            if charNum >= region.start {
                chosen = region.prefer
            } else {
                break
            }
        }
        return chosen
    }

    private struct RankedKey {
        var score: Int
        var majorTonic: Int
        var tonic: Int
        var isMinor: Bool
        var prefer: Int
    }

    private struct DetectedKey {
        var prefer: Int
        var score: Int
        var majorTonic: Int
    }

    private nonisolated static func bestKey(_ chords: [SongChord]) -> DetectedKey? {
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
                prefer: preferForMajorTonic(majorTonic)))
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

    private nonisolated static func preferForMajorTonic(_ majorTonic: Int) -> Int {
        if sharpMajorTonics.contains(majorTonic) {
            return preferSharps
        }
        if flatMajorTonics.contains(majorTonic) {
            return preferFlats
        }
        return preferNeither
    }

    private nonisolated static func scoreKey(_ chords: [SongChord], tonic: Int, isMinor: Bool) -> Int {
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

    private nonisolated static func familyScore(_ chords: [SongChord], majorTonic: Int) -> Int {
        let relativeMinor = mod12(majorTonic - 3)
        return max(
            scoreKey(chords, tonic: majorTonic, isMinor: false),
            scoreKey(chords, tonic: relativeMinor, isMinor: true))
    }

    /// Chord-list indexes where a new key starts. Same cuts as the editor.
    private nonisolated static func regionStarts(_ chords: [SongChord]) -> [Int] {
        func splits(_ seq: [SongChord], offset: Int) -> [Int] {
            let count = seq.count
            if count < 10 {
                return [offset]
            }
            let wholeScore = bestKey(seq)?.score ?? 0
            var bestCut: Int?
            var bestGain = 0
            for cut in 5...(count - 5) {
                let left = Array(seq[..<cut])
                let right = Array(seq[cut...])
                guard let leftKey = bestKey(left), let rightKey = bestKey(right) else {
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
}
