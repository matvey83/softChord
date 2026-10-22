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

    struct Drawing {
        var glyphs: [Glyph]
        var size: CGSize
    }

    // TODO: The web sheet should use these measurements. The desktop editor
    // keeps QtDocumentLayout until a new lyric renderer replaces it.
    nonisolated static func drawing(for lines: [SongSheetLine]) -> Drawing {
        let lyrics = font(candidates: ["TimesNewRomanPSMT", "Times New Roman"], size: 20, bold: false)
        let chords = font(candidates: ["TimesNewRomanPS-BoldMT", "TimesNewRomanPSMT"], size: 12, bold: true)
        let symbols = symbolsFont(size: 12, fallback: chords)
        let lyricsHeight = height(lyrics)
        let chordsHeight = height(chords)
        let lineHeight = lyricsHeight + CTFontGetAscent(chords) - CTFontGetLeading(lyrics) - CTFontGetLeading(chords)
        let chordGap = (lineHeight - lyricsHeight) * 1.03
        let padding: CGFloat = 16
        let black = CGColor(gray: 0, alpha: 1)
        let blue = CGColor(red: 0, green: 0, blue: 1, alpha: 1)

        var glyphs: [Glyph] = []
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

            for chord in line.chords {
                guard chord.anchor >= 0, chord.anchor + 1 < offsets.count else {
                    continue
                }
                let left = padding + offsets[chord.anchor]
                let right = padding + offsets[chord.anchor + 1]
                let width = chordWidth(chord.text, chords: chords, symbols: symbols)
                var letterX = ((left + right) / 2) - (width / 2)
                minX = min(minX, letterX)
                for letter in chord.text.unicodeScalars {
                    let accidental = letter == "♯" || letter == "♭"
                    let letterFont = accidental ? symbols : chords
                    let letterBaseline = accidental ? raisedBaseline : normalBaseline
                    glyphs.append(Glyph(
                        text: String(letter),
                        font: letterFont,
                        color: blue,
                        x: letterX,
                        baseline: letterBaseline))
                    letterX += advance(letter, font: letterFont)
                }
                maxX = max(maxX, letterX)
            }

            y = charBottom
        }

        let shift = max(0, padding - minX)
        if shift > 0 {
            for index in glyphs.indices {
                glyphs[index].x += shift
            }
            maxX += shift
        }

        return Drawing(glyphs: glyphs, size: CGSize(width: maxX + padding, height: y + padding))
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
