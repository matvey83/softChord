//
//  softchord_text.swift
//  softChord Viewer
//
//  Paired with src/softchord_text.py.
//  place, then render, match place_chord_on_line and format_song_text.

import Foundation

/// One chord on one letter.
///
/// A chord whose suffix is not a known type (for example "maj9") keeps that
/// text in `suffix`, and `chordTypeId` is then only its base quality (0 major,
/// 1 minor). An unknown (unrecognized) chord has no root: it is drawn in red as the
/// first 7 characters of `raw`, its original text ("?" when empty). `rootText` and `bassText` are the spellings read from the
/// songbook. Changing the note drops them (see SongTranspose.shifted).
///
/// Mirror: softchord_song.py SongChord.
nonisolated struct SongChord: Equatable {
    var characterNum: Int
    var noteId: Int
    var chordTypeId: Int
    var bassNoteId: Int
    var marker: String
    var inParentheses: Bool
    var suffix: String? = nil
    var rootText: String? = nil
    var bassText: String? = nil
    var unknown: Bool = false
    var raw: String = SoftchordChords.unknownChordText

    /// Read a chord string. Never fails. Mirror: softchord_song.py SongChord.from_text.
    static func from(text: String, characterNum: Int) -> SongChord {
        let parsed = SoftchordChords.parseChord(text)
        if parsed.unknown {
            return SongChord(
                characterNum: characterNum, noteId: -1, chordTypeId: 0, bassNoteId: -1,
                marker: "", inParentheses: false, unknown: true, raw: parsed.raw)
        }
        return SongChord(
            characterNum: characterNum, noteId: parsed.noteId, chordTypeId: parsed.chordTypeId,
            bassNoteId: parsed.bassNoteId, marker: parsed.marker, inParentheses: parsed.inParentheses,
            suffix: parsed.isKnownType ? nil : parsed.suffix,
            rootText: parsed.rootText,
            bassText: parsed.bassText.isEmpty ? nil : parsed.bassText)
    }
}

nonisolated struct SongSheetChord: Equatable {
    var anchor: Int
    var text: String
    /// Text that is not a chord. It is drawn in red.
    var unrecognized: Bool = false
}

nonisolated struct SongSheetLine: Equatable {
    var lyric: String
    var chords: [SongSheetChord]
}

/// Lyrics, or lyrics with a chord line above each line that has chords.
/// Names and columns match the editor's Copy Song Text commands.
enum SongText {
    /// Mirror: softchord_text.py place_chord_on_line.
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

    /// Mirror: softchord_text.py format_song_text, via Song.getAsText.
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
                    place(SoftchordChords.chordText(chord, prefer: prefer), on: &cells, anchor: anchor)
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

    /// The chord text drawn on a letter, spelled as the sheet spells it.
    /// Nil when the letter has no chord. This is what a chord edit starts from.
    nonisolated static func displayedChordText(text: String, chords: [SongChord], characterNum: Int) -> String? {
        var scalar = 0
        for line in sheet(text: text, chords: chords) {
            for chord in line.chords where scalar + chord.anchor == characterNum {
                return chord.text
            }
            scalar += line.lyric.unicodeScalars.count + 1
        }
        return nil
    }

    /// One lyric line, with each chord named and anchored on a letter.
    /// The editor paints this instead of returning it.
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
                placed.append(SongSheetChord(
                    anchor: anchor, text: SoftchordChords.chordText(chord, prefer: prefer),
                    unrecognized: chord.unknown))
            }
            return SongSheetLine(lyric: String(String.UnicodeScalarView(line)), chords: placed)
        }
    }

    /// Mirror: softchord_song.py Song.songCharToLineChar.
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

    /// Mirror: softchord_song.py Song.updateSharpsOrFlats.
    /// Unknown chords have no root, so they take no part in key detection.
    private nonisolated static func regions(for chords: [SongChord]) -> [(start: Int, prefer: Int)] {
        let sorted = chords.filter { !$0.unknown }.sorted { $0.characterNum < $1.characterNum }
        let starts = SoftchordChords.detectRegionStartIndices(sorted)
        var found: [(start: Int, prefer: Int)] = []
        for (index, startIndex) in starts.enumerated() {
            let endIndex = index + 1 < starts.count ? starts[index + 1] : sorted.count
            let group = Array(sorted[startIndex..<endIndex])
            let prefer = SoftchordChords.bestDetectedKey(group)?.prefer ?? SoftchordChords.preferNeither
            found.append((group.first?.characterNum ?? 0, prefer))
        }
        return found
    }

    private nonisolated static func prefer(for charNum: Int, regions: [(start: Int, prefer: Int)]) -> Int {
        var chosen = regions.first?.prefer ?? SoftchordChords.preferNeither
        for region in regions {
            if charNum >= region.start {
                chosen = region.prefer
            } else {
                break
            }
        }
        return chosen
    }
}

/// Chords follow the letters while the lyrics are edited.
/// Mirror: softchord_session.py _lyric_renumber_map and _renumber_lyric_chords.
enum SongLyricChords {
    nonisolated static func moved(_ chords: [SongChord], from previous: String, to text: String) -> [SongChord] {
        if previous == text || chords.isEmpty {
            return chords
        }
        let map = renumberMap(from: previous, to: text)
        var kept: [SongChord] = []
        kept.reserveCapacity(chords.count)
        for var chord in chords {
            guard let newIndex = map[chord.characterNum] else {
                continue
            }
            chord.characterNum = newIndex
            kept.append(chord)
        }
        return kept
    }

    /// The chord that was on `from` now sits on `to`.
    /// A chord that was already on `to` is dropped, so a letter keeps one chord.
    nonisolated static func reattached(_ chords: [SongChord], from: Int, to: Int) -> [SongChord] {
        guard from != to, chords.contains(where: { $0.characterNum == from }) else {
            return chords
        }
        return chords.compactMap { chord in
            if chord.characterNum == to {
                return nil
            }
            if chord.characterNum == from {
                var moved = chord
                moved.characterNum = to
                return moved
            }
            return chord
        }
    }

    /// The chord typed for a letter. It replaces the chord there, or is added.
    /// The page shows chords shifted by `steps` but keeps them as stored, so the
    /// typed name is shifted back by the same steps before it is kept.
    /// Text that is not a chord becomes an unrecognized chord and keeps the typed text.
    nonisolated static func replaced(_ chords: [SongChord], at characterNum: Int, withText text: String, steps: Int) -> [SongChord] {
        let typed = SongChord.from(text: text, characterNum: characterNum)
        let stored = SongTranspose.shifted([typed], by: -steps)[0]
        var result = chords.filter { $0.characterNum != characterNum }
        let index = result.firstIndex { $0.characterNum > characterNum } ?? result.count
        result.insert(stored, at: index)
        return result
    }

    nonisolated static func deleted(_ chords: [SongChord], at characterNum: Int) -> [SongChord] {
        chords.filter { $0.characterNum != characterNum }
    }

    /// What the chord sheet does with the text typed so far. The field is red and OK and
    /// Return do nothing while it is not a valid chord. Mirror: ChordDialog in softchord_session.py.
    nonisolated struct ChordEntry: Equatable {
        var text: String

        /// The same test the parser and transposing use.
        var isValid: Bool {
            SoftchordChords.isValidChordText(text)
        }

        var showsRed: Bool { !isValid }
        var canSave: Bool { isValid }
        var footer: String { SongLyricChords.preview(ofTyped: text) }
    }

    /// What the chord sheet says about the text typed so far.
    nonisolated static func preview(ofTyped text: String) -> String {
        if !SoftchordChords.isValidChordText(text) {
            return "Not a chord. Start with a note from A to G."
        }
        let chord = SongChord.from(text: text, characterNum: 0)
        return "Shown as " + SoftchordChords.chordText(chord, prefer: SoftchordChords.preferNeither)
    }

    /// Old letter index to the index of that same letter after the edit.
    /// A letter that was deleted has no entry, so the chord on it is dropped.
    /// The walk from the end overwrites the walk from the start where they meet,
    /// matching the desktop map.
    private nonisolated static func renumberMap(from previous: String, to text: String) -> [Int: Int] {
        let old = Array(previous.unicodeScalars)
        let new = Array(text.unicodeScalars)
        var map: [Int: Int] = [:]
        var index = 0
        while index < old.count && index < new.count && old[index] == new[index] {
            map[index] = index
            index += 1
        }
        var back = 1
        while back <= old.count && back <= new.count {
            let oldIndex = old.count - back
            let newIndex = new.count - back
            if old[oldIndex] != new[newIndex] {
                break
            }
            map[oldIndex] = newIndex
            back += 1
        }
        return map
    }
}
