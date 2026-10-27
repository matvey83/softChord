//
//  softchord_layout.swift
//  softChord Viewer
//
//  Paired with src/softchord_layout.py.

import CoreGraphics
import CoreText
import Foundation

/// Positions lyrics and chords the way the editor and the PDF export paint them.
/// Mirror: softchord_layout.py QtDocumentLayout.character_and_chord_boxes. Core Text measures the
/// letters here. Qt cursor rectangles measure them on the desktop.
enum SongSheetLayout {
    struct Glyph {
        var text: String
        var font: CTFont
        var color: CGColor
        var x: CGFloat
        /// Baseline, with y growing downward.
        var baseline: CGFloat
    }

    /// A lyric letter, by its place in the song. The rectangle is the letter itself.
    /// The reach adds the chord row above it, so a finger there still belongs to the letter.
    struct Letter: Equatable {
        var characterNum: Int
        var rect: CGRect
        var reach: CGRect
    }

    struct Drawing {
        var glyphs: [Glyph]
        var size: CGSize
        var letters: [Letter] = []
        /// The painted chords. Each box carries the letter its chord is on.
        var chordBoxes: [SongChordBoxes.Box] = []

        /// The letter under the point. A newline and the margin are misses.
        nonisolated func letter(at point: CGPoint) -> Int? {
            letters.first { $0.rect.contains(point) }?.characterNum
        }

        /// The letter nearest the point, even up in the chord row. The line is the one
        /// closest in height. The side margin is still a miss, so a drag past the end
        /// of a line does not jump.
        /// Mirror: the nearest letter while a chord is dragged in softchord_session.py.
        nonisolated func nearestLetter(at point: CGPoint) -> Int? {
            func gap(_ letter: Letter) -> CGFloat {
                max(letter.reach.minY - point.y, point.y - letter.reach.maxY, 0)
            }
            guard let nearest = letters.map(gap).min() else {
                return nil
            }
            var best: Letter?
            for letter in letters where gap(letter) - nearest < 0.01 {
                if point.x < letter.rect.minX - 2 || point.x >= letter.rect.maxX + 2 {
                    continue
                }
                if best == nil || abs(point.x - letter.rect.midX) < abs(point.x - best!.rect.midX) {
                    best = letter
                }
            }
            return best?.characterNum
        }
    }

    // TODO: The web sheet should use these measurements. The desktop editor
    // keeps QtDocumentLayout until a new lyric renderer replaces it.
    /// Loads the sheet fonts. The song list starts this before a song is opened.
    nonisolated static func warm() {
        _ = lyricsFont
        _ = chordsFont
        _ = symbolsFontCached
    }

    // Resolved once. Looking the names up on every song made the first paint wait.
    private nonisolated static let lyricsFont = font(
        candidates: ["TimesNewRomanPSMT", "Times New Roman"], size: 20, bold: false)
    private nonisolated static let chordsFont = font(
        candidates: ["TimesNewRomanPS-BoldMT", "TimesNewRomanPSMT"], size: 12, bold: true)
    private nonisolated static let symbolsFontCached = symbolsFont(size: 12, fallback: chordsFont)

    nonisolated static func drawing(for lines: [SongSheetLine]) -> Drawing {
        let lyrics = lyricsFont
        let chords = chordsFont
        let symbols = symbolsFontCached
        let lyricsHeight = height(lyrics)
        let chordsHeight = height(chords)
        let lineHeight = lyricsHeight + CTFontGetAscent(chords) - CTFontGetLeading(lyrics) - CTFontGetLeading(chords)
        let chordGap = (lineHeight - lyricsHeight) * 1.03
        let padding: CGFloat = 16
        let black = CGColor(gray: 0, alpha: 1)
        let blue = CGColor(red: 0, green: 0, blue: 1, alpha: 1)
        // Text in a chord position that is not a chord.
        let red = CGColor(red: 1, green: 0, blue: 0, alpha: 1)

        var glyphs: [Glyph] = []
        var letters: [Letter] = []
        var chordBoxes: [SongChordBoxes.Box] = []
        var lineStart = 0
        var y = padding
        var minX = padding
        var maxX = padding

        for line in lines {
            if !line.chords.isEmpty {
                y += chordGap
            }
            let lyricTop = y
            let charBottom = lyricTop + lyricsHeight
            let lyricBaseline = lyricTop + CTFontGetAscent(lyrics)
            let offsets = caretOffsets(line.lyric, font: lyrics)
            glyphs.append(Glyph(text: line.lyric, font: lyrics, color: black, x: padding, baseline: lyricBaseline))
            let lineRight = padding + (offsets.last ?? 0)
            maxX = max(maxX, lineRight)

            let chordTop = charBottom - lineHeight
            let chordBottom = chordTop + chordsHeight
            let normalBaseline = chordBottom - (0.2 * chordsHeight)
            let raisedBaseline = normalBaseline - (chordsHeight / 10)

            let reachTop = line.chords.isEmpty ? lyricTop : lyricTop - chordGap
            for index in 0..<max(0, offsets.count - 1) {
                let left = padding + offsets[index]
                let width = offsets[index + 1] - offsets[index]
                letters.append(Letter(
                    characterNum: lineStart + index,
                    rect: CGRect(x: left, y: lyricTop, width: width, height: lyricsHeight),
                    reach: CGRect(x: left, y: reachTop, width: width, height: charBottom - reachTop)))
            }

            for chord in line.chords {
                guard chord.anchor >= 0, chord.anchor + 1 < offsets.count else {
                    continue
                }
                let left = padding + offsets[chord.anchor]
                let right = padding + offsets[chord.anchor + 1]
                let width = chordWidth(chord.text, chords: chords, symbols: symbols)
                var letterX = ((left + right) / 2) - (width / 2)
                minX = min(minX, letterX)
                chordBoxes.append(SongChordBoxes.Box(
                    characterNum: lineStart + chord.anchor,
                    rect: CGRect(x: letterX, y: chordTop, width: width, height: chordsHeight)))
                for letter in chord.text.unicodeScalars {
                    let accidental = letter == "♯" || letter == "♭"
                    let letterFont = accidental ? symbols : chords
                    let letterBaseline = accidental ? raisedBaseline : normalBaseline
                    glyphs.append(Glyph(
                        text: String(letter),
                        font: letterFont,
                        color: chord.unrecognized ? red : blue,
                        x: letterX,
                        baseline: letterBaseline))
                    letterX += advance(letter, font: letterFont)
                }
                maxX = max(maxX, letterX)
            }

            y = charBottom
            lineStart += line.lyric.unicodeScalars.count + 1
        }

        let shift = max(0, padding - minX)
        if shift > 0 {
            for index in glyphs.indices {
                glyphs[index].x += shift
            }
            for index in letters.indices {
                letters[index].rect.origin.x += shift
                letters[index].reach.origin.x += shift
            }
            for index in chordBoxes.indices {
                chordBoxes[index].rect.origin.x += shift
            }
            maxX += shift
        }

        return Drawing(
            glyphs: glyphs,
            size: CGSize(width: maxX + padding, height: y + padding),
            letters: letters,
            chordBoxes: chordBoxes)
    }

    private nonisolated static func height(_ font: CTFont) -> CGFloat {
        CTFontGetAscent(font) + CTFontGetDescent(font)
    }

    private nonisolated static func font(candidates: [String], size: CGFloat, bold: Bool) -> CTFont {
        for name in candidates {
            let created = CTFontCreateWithName(name as CFString, size, nil)
            let actual = CTFontCopyPostScriptName(created) as String
            if actual.caseInsensitiveCompare(name) == .orderedSame {
                return bold ? boldFont(created, size: size) : created
            }
        }
        let created = CTFontCreateWithName("TimesNewRomanPSMT" as CFString, size, nil)
        return bold ? boldFont(created, size: size) : created
    }

    private nonisolated static func boldFont(_ font: CTFont, size: CGFloat) -> CTFont {
        if let bold = CTFontCreateCopyWithSymbolicTraits(font, size, nil, .traitBold, .traitBold) {
            return bold
        }
        return font
    }

    private nonisolated static func symbolsFont(size: CGFloat, fallback: CTFont) -> CTFont {
        let names = ["ArialUnicodeMS", "Arial Unicode MS", "AppleSymbols", "Apple Symbols"]
        for name in names {
            let created = CTFontCreateWithName(name as CFString, size, nil)
            let actual = CTFontCopyPostScriptName(created) as String
            guard actual.caseInsensitiveCompare(name) == .orderedSame, containsAccidental(created) else {
                continue
            }
            return boldFont(created, size: size)
        }
        return fallback
    }

    private nonisolated static func containsAccidental(_ font: CTFont) -> Bool {
        var characters = Array("♯".utf16)
        var glyphs = [CGGlyph](repeating: 0, count: characters.count)
        return CTFontGetGlyphsForCharacters(font, &characters, &glyphs, characters.count)
    }

    private nonisolated static func caretOffsets(_ text: String, font: CTFont) -> [CGFloat] {
        let line = CTLineCreateWithAttributedString(NSAttributedString(string: text, attributes: attributes(font)))
        let encoded = text as NSString
        var offsets = [CGFloat]()
        var index = 0
        while index < encoded.length {
            offsets.append(CTLineGetOffsetForStringIndex(line, index, nil))
            let unit = encoded.character(at: index)
            index += (unit >= 0xD800 && unit <= 0xDBFF) ? 2 : 1
        }
        offsets.append(CTLineGetOffsetForStringIndex(line, encoded.length, nil))
        return offsets
    }

    private nonisolated static func chordWidth(_ text: String, chords: CTFont, symbols: CTFont) -> CGFloat {
        text.unicodeScalars.reduce(0) { total, letter in
            let font = (letter == "♯" || letter == "♭") ? symbols : chords
            return total + advance(letter, font: font)
        }
    }

    private nonisolated static func advance(_ letter: Unicode.Scalar, font: CTFont) -> CGFloat {
        let line = CTLineCreateWithAttributedString(
            NSAttributedString(string: String(letter), attributes: attributes(font)))
        return CTLineGetTypographicBounds(line, nil, nil, nil)
    }

    private nonisolated static func attributes(_ font: CTFont) -> [NSAttributedString.Key: Any] {
        [NSAttributedString.Key(kCTFontAttributeName as String): font]
    }
}

/// The painted chord a finger is on.
/// Mirror: determineClickedLetter in softchord_session.py. A press inside the
/// box is on the chord. The edges are left for the letter, so a tap there
/// still edits the text. Pass a slop to count a few pixels around the box.
/// The first box wins when two overlap.
enum SongChordBoxes {
    struct Box: Equatable {
        var characterNum: Int
        var rect: CGRect
    }

    nonisolated static func characterNum(at point: CGPoint, boxes: [Box], slop: CGFloat = 0) -> Int? {
        for box in boxes {
            let rect = box.rect.insetBy(dx: -slop, dy: -slop)
            if point.x > rect.minX, point.x < rect.maxX, point.y > rect.minY, point.y < rect.maxY {
                return box.characterNum
            }
        }
        return nil
    }
}

/// What a press does in chord editing.
/// The first press selects the chord, or a letter that has none. A later
/// press on that chord can drag it, and a tap in place edits it. A tap on the
/// selected letter edits its chord too, or adds one. Any other press clears
/// the selection.
enum SongChordPick {
    /// A few pixels around the painted chord still count as a press on it.
    static let slop: CGFloat = 6

    enum Action: Equatable {
        case select(Int)
        case clear
        case drag
        case edit
    }

    static func action(
        selected: Int?,
        hit: Int?,
        pressedSelectedChord: Bool,
        selectedHasChord: Bool
    ) -> Action? {
        if selected != nil {
            if pressedSelectedChord && selectedHasChord {
                return .drag
            }
            if hit == selected {
                return .edit
            }
            return .clear
        }
        if let hit {
            return .select(hit)
        }
        return nil
    }
}

extension SongChordPick {
    /// A press in the zoomed sheet. The point is in the sheet's content, which is the
    /// song drawn at `zoom`. The slop stays a few screen points at any zoom.
    nonisolated static func action(
        in drawing: SongSheetLayout.Drawing,
        at contentPoint: CGPoint,
        zoom: CGFloat,
        selected: Int?
    ) -> Action? {
        let point = CGPoint(x: contentPoint.x / zoom, y: contentPoint.y / zoom)
        let slop = SongChordPick.slop / zoom
        let onChord = SongChordBoxes.characterNum(at: point, boxes: drawing.chordBoxes, slop: slop)
        let selectedBox = drawing.chordBoxes.first { $0.characterNum == selected }
        let onSelectedChord = selectedBox.map {
            SongChordBoxes.characterNum(at: point, boxes: [$0], slop: slop) != nil
        } ?? false
        return action(
            selected: selected,
            hit: onChord ?? drawing.letter(at: point),
            pressedSelectedChord: onSelectedChord,
            selectedHasChord: selectedBox != nil)
    }
}
