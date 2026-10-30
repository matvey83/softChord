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
    /// Write one chord name into a monospace chord row, starting above its
    /// letter (where a text import reads it from). `free` is the first column
    /// it may use (one space after the name before it); a name past the end
    /// of the line adds columns. Returns the first column the next name may use.
    /// Mirror: softchord_text.py place_chord_on_line.
    private nonisolated static func place(_ chordText: String, on cells: inout [Unicode.Scalar], anchor: Int, free: Int) -> Int {
        let chars = Array(chordText.unicodeScalars)
        guard !chars.isEmpty else {
            return free
        }
        let left = max(anchor, free, 0)
        if cells.count < left + chars.count {
            cells.append(contentsOf: Array(repeating: Unicode.Scalar(" "), count: left + chars.count - cells.count))
        }
        for (offset, char) in chars.enumerated() {
            cells[left + offset] = char
        }
        return left + chars.count + 1
    }

    /// Mirror: softchord_text.py format_song_text, via Song.getAsText.
    nonisolated static func render(text: String, chords: [SongChord], includeChords: Bool) -> String {
        let lines = text.components(separatedBy: "\n").map { Array($0.unicodeScalars) }
        let spelling = regions(for: chords)
        var song = ""

        for (lineNum, line) in lines.enumerated() {
            if includeChords && lineHasChords(lineNum, chords: chords, lines: lines) {
                var cells = Array(repeating: Unicode.Scalar(" "), count: line.count)
                // Left to right; of two chords on one letter the later is written.
                var names: [Int: String] = [:]
                for chord in chords {
                    guard let (chordLine, anchor) = lineAndColumn(chord.characterNum, lines: lines),
                          chordLine == lineNum else {
                        continue
                    }
                    let prefer = prefer(for: chord.characterNum, regions: spelling)
                    names[anchor] = SoftchordChords.chordText(chord, prefer: prefer)
                }
                var free = 0
                for anchor in names.keys.sorted() {
                    free = place(names[anchor]!, on: &cells, anchor: anchor, free: free)
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
        guard songChar >= 0 else {
            return nil
        }
        var start = 0
        for (lineNum, line) in lines.enumerated() {
            let end = start + line.count + 1
            if songChar < end - 1 {
                return (lineNum, songChar - start)
            }
            if songChar == end - 1 {
                // The line break has no letter, so nothing is drawn there.
                return nil
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
/// Mirror: softchord_session.py _renumber_lyric_chords and softchord_text.py lyric_renumber_map.
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

    /// The chord that was on `from` now sits on `to`. `to` has to be free: a
    /// letter never gets two chords, so a move onto a letter that has a chord
    /// changes nothing. Use nextFreeCharacter to find the letter to move to.
    nonisolated static func reattached(_ chords: [SongChord], from: Int, to: Int) -> [SongChord] {
        guard from != to,
              chords.contains(where: { $0.characterNum == from }),
              !chords.contains(where: { $0.characterNum == to }) else {
            return chords
        }
        return chords.map { chord in
            guard chord.characterNum == from else {
                return chord
            }
            var moved = chord
            moved.characterNum = to
            return moved
        }
    }

    /// First and last letter of the line that holds `index`. Nil for a line break
    /// or an index outside the text. A chord only sits on a letter of its own line.
    /// Mirror: softchord_text.py line_letter_range.
    nonisolated static func letterRange(in text: String, at index: Int) -> ClosedRange<Int>? {
        let letters = Array(text.unicodeScalars)
        guard index >= 0, index < letters.count, letters[index] != "\n" else {
            return nil
        }
        var first = index
        while first > 0 && letters[first - 1] != "\n" {
            first -= 1
        }
        var last = index
        while last + 1 < letters.count && letters[last + 1] != "\n" {
            last += 1
        }
        return first...last
    }

    /// The letter a chord lands on when it is moved onto `target`. A letter that has a
    /// chord is jumped over, and so is every other one, to the next free letter of the
    /// line in `direction` (1 right, -1 left). Chords are never lost and a letter never
    /// gets two. With `allowOtherDirection` (a drag) a line with no free letter that way
    /// is tried the other way. Nil means the chord stays. `occupied` holds the letters
    /// that have a chord, without the chord that moves.
    /// Mirror: softchord_text.py next_free_character.
    nonisolated static func nextFreeCharacter(
        in text: String, target: Int, direction: Int, occupied: Set<Int>, allowOtherDirection: Bool = false
    ) -> Int? {
        guard let range = letterRange(in: text, at: target) else {
            return nil
        }
        let step = direction < 0 ? -1 : 1
        for each in allowOtherDirection ? [step, -step] : [step] {
            var position = target
            while range.contains(position) {
                if !occupied.contains(position) {
                    return position
                }
                position += each
            }
        }
        return nil
    }

    /// 1 or -1: which way a chord dragged onto `target` goes past a chord. The finger
    /// moved from the letter `previous` to `target`. A target on another line than the
    /// chord goes forward (1), as does no movement.
    /// Mirror: softchord_text.py chord_drag_direction.
    nonisolated static func dragDirection(in text: String, chord: Int, previous: Int, target: Int) -> Int {
        let letters = Array(text.unicodeScalars)
        func lineStart(_ index: Int) -> Int {
            var start = max(0, min(index, letters.count))
            while start > 0 && letters[start - 1] != "\n" {
                start -= 1
            }
            return start
        }
        if lineStart(chord) != lineStart(target) {
            return 1
        }
        return target < previous ? -1 : 1
    }

    /// One step of a chord drag: where the chord and the finger are after the finger
    /// moved onto the letter `target`.
    struct ChordDragStep: Equatable {
        /// The letter the finger is over now. A chord that jumped over a letter with a
        /// chord leaves the finger on that letter, and staying there moves nothing.
        var finger: Int
        /// The letter the dragged chord is on now. The same as before if it did not move.
        var chordAt: Int
        var chords: [SongChord]
    }

    /// The finger moved from the letter `finger` to `target` while dragging the chord
    /// on `chordAt`. Nil when the finger is still on the same letter. The chord lands
    /// on the next free letter of its line in the direction of the drag, and the
    /// chords are never lost. This is the whole drag rule: the song page's
    /// moveSelectedChord only adds the selection and the callbacks.
    /// Mirror: the chord drag in softchord_session.py.
    nonisolated static func draggedChord(
        _ chords: [SongChord], in text: String, chordAt from: Int, finger previous: Int, target: Int
    ) -> ChordDragStep? {
        guard target != previous else {
            return nil
        }
        let occupied = Set(chords.map(\.characterNum)).subtracting([from])
        let direction = dragDirection(in: text, chord: from, previous: previous, target: target)
        guard let to = nextFreeCharacter(
            in: text, target: target, direction: direction, occupied: occupied, allowOtherDirection: true),
              to != from else {
            return ChordDragStep(finger: target, chordAt: from, chords: chords)
        }
        let next = reattached(chords, from: from, to: to)
        guard next != chords else {
            return ChordDragStep(finger: target, chordAt: from, chords: chords)
        }
        return ChordDragStep(finger: target, chordAt: to, chords: next)
    }

    // MARK: Room right of a line
    // A chord can go up to `room` letters right of the last letter of its line
    // (not a space). The line gets spaces for it while it is dragged there
    // (withRoom), and after a move or a delete the lines it touched lose the
    // spaces at their end that no chord needs (tidied): a line keeps spaces only
    // up to its last chord. Other lines keep theirs, and so do a line of only
    // spaces and a tab. The text changes with the chords, so one undo has both.
    // MIRRORED: softchord_text.py chord_room and tidy_chord_room,
    // softchord_chord_edit.js withRoom and tidied.
    nonisolated static let room = 10

    /// The text and chords with a padded line, and where the spaces went in.
    struct ChordRoom: Equatable {
        var text: String
        var chords: [SongChord]
        /// count spaces went in at at: a position from at on moves by count.
        var at: Int
        var count: Int

        func shifted(_ position: Int) -> Int {
            position >= at ? position + count : position
        }
    }

    /// The line that holds `index` with spaces up to `room` letters right of its
    /// last letter that is not a space.
    nonisolated static func withRoom(_ chords: [SongChord], in text: String, at index: Int) -> ChordRoom {
        let letters = Array(text.unicodeScalars)
        guard let range = letterRange(in: text, at: index) else {
            return ChordRoom(text: text, chords: chords, at: letters.count, count: 0)
        }
        var last = range.upperBound
        while last >= range.lowerBound && letters[last] == " " {
            last -= 1
        }
        let end = range.upperBound + 1
        let count = last + 1 + room - end
        guard last >= range.lowerBound, count > 0 else {
            return ChordRoom(text: text, chords: chords, at: end, count: 0)
        }
        var scalars = String.UnicodeScalarView()
        scalars.append(contentsOf: letters[..<end])
        scalars.append(contentsOf: Array(repeating: Unicode.Scalar(" "), count: count))
        scalars.append(contentsOf: letters[end...])
        let padded = ChordRoom(text: String(scalars), chords: chords, at: end, count: count)
        return ChordRoom(text: padded.text, chords: chords.map { chord in
            var moved = chord
            moved.characterNum = padded.shifted(chord.characterNum)
            return moved
        }, at: end, count: count)
    }

    /// The text and chords after `tidied`, and where a position went.
    struct ChordTidy: Equatable {
        var text: String
        var chords: [SongChord]
        var gaps: [Range<Int>]

        func moved(_ position: Int) -> Int {
            var by = 0
            for gap in gaps {
                if position >= gap.upperBound {
                    by += gap.count
                } else if position >= gap.lowerBound {
                    by += position - gap.lowerBound
                }
            }
            return position - by
        }
    }

    /// The lines that hold a position of `touched` without the spaces at their end
    /// past their last chord.
    nonisolated static func tidied(_ chords: [SongChord], in text: String, touched: [Int]) -> ChordTidy {
        let letters = Array(text.unicodeScalars)
        let taken = Set(chords.map(\.characterNum))
        var gaps: [Range<Int>] = []
        var first = 0
        for i in 0...letters.count where i == letters.count || letters[i] == "\n" {
            var cut = i
            while cut > first && letters[cut - 1] == " " && !taken.contains(cut - 1) {
                cut -= 1
            }
            if cut > first && cut < i && touched.contains(where: { $0 >= first && $0 <= i }) {
                gaps.append(cut..<i)
            }
            first = i + 1
        }
        guard !gaps.isEmpty else {
            return ChordTidy(text: text, chords: chords, gaps: [])
        }
        var scalars = String.UnicodeScalarView()
        var at = 0
        for gap in gaps {
            scalars.append(contentsOf: letters[at..<gap.lowerBound])
            at = gap.upperBound
        }
        scalars.append(contentsOf: letters[at...])
        var tidy = ChordTidy(text: String(scalars), chords: chords, gaps: gaps)
        tidy.chords = chords.map { chord in
            var moved = chord
            moved.characterNum = tidy.moved(chord.characterNum)
            return moved
        }
        return tidy
    }

    /// A drag step with room: the chord on `from` (a letter of `text`) goes to `to`,
    /// a letter of the text with room at `roomAt` (or of `text` itself), and the
    /// lines it left and went to are tidied. The view and the page both call this,
    /// so the drawn chords and the kept ones stay the same.
    nonisolated static func movedWithRoom(
        _ chords: [SongChord], in text: String, from: Int, to: Int, roomAt: Int?
    ) -> ChordTidy {
        let room = roomAt.map { withRoom(chords, in: text, at: $0) }
            ?? ChordRoom(text: text, chords: chords, at: Array(text.unicodeScalars).count, count: 0)
        let start = room.shifted(from)
        let moved = reattached(room.chords, from: start, to: to)
        return tidied(moved, in: room.text, touched: [start, to])
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
    /// The unchanged end never reaches into the unchanged start, so two old letters
    /// never map to one new letter (Hello to Helo keeps one l).
    /// A chord past the end of the text (or below zero) has no entry either, so the
    /// first edit drops it. One on a line break is kept.
    /// Mirror: softchord_text.py lyric_renumber_map.
    nonisolated static func renumberMap(from previous: String, to text: String) -> [Int: Int] {
        let old = Array(previous.unicodeScalars)
        let new = Array(text.unicodeScalars)
        let shortest = min(old.count, new.count)
        var map: [Int: Int] = [:]
        var prefix = 0
        while prefix < shortest && old[prefix] == new[prefix] {
            map[prefix] = prefix
            prefix += 1
        }
        var suffix = 0
        while suffix < shortest - prefix && old[old.count - 1 - suffix] == new[new.count - 1 - suffix] {
            map[old.count - 1 - suffix] = new.count - 1 - suffix
            suffix += 1
        }
        return map
    }
}
