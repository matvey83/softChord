//
//  softChord_ViewerTests.swift
//  softChord ViewerTests
//
//  Created by Matvey Adzhigirey on 10/21/26.
//

import SQLite3
import Testing
import UIKit
@testable import softChord_Viewer

struct softChord_ViewerTests {

    @Test func songTextMatchesTheEditorLayout() {
        let chords = [
            SongChord(characterNum: 0, noteId: 0, chordTypeId: 0, bassNoteId: -1, marker: "", inParentheses: false),
            SongChord(characterNum: 5, noteId: 9, chordTypeId: 1, bassNoteId: -1, marker: "", inParentheses: false),
            SongChord(characterNum: 26, noteId: 7, chordTypeId: 0, bassNoteId: -1, marker: "", inParentheses: false),
        ]
        let text = "Test line one\nTest line two"
        let withChords = SongText.render(text: text, chords: chords, includeChords: true)
        #expect(withChords == "C    Am\r\nTest line one\r\n" + String(repeating: " ", count: 11) + "G\r\nTest line two")

        let plain = SongText.render(text: text, chords: chords, includeChords: false)
        #expect(plain == "Test line one\r\nTest line two")
    }

    @Test func sheetAnchorsChordsOnTheirLetters() {
        let chords = [
            SongChord(characterNum: 0, noteId: 0, chordTypeId: 0, bassNoteId: -1, marker: "", inParentheses: false),
            SongChord(characterNum: 5, noteId: 9, chordTypeId: 1, bassNoteId: -1, marker: "", inParentheses: false),
            SongChord(characterNum: 26, noteId: 7, chordTypeId: 0, bassNoteId: -1, marker: "", inParentheses: false),
        ]
        let lines = SongText.sheet(text: "Test line one\nTest line two", chords: chords)
        #expect(lines.map(\.lyric) == ["Test line one", "Test line two"])
        #expect(lines[0].chords == [
            SongSheetChord(anchor: 0, text: "C"),
            SongSheetChord(anchor: 5, text: "Am"),
        ])
        #expect(lines[1].chords == [SongSheetChord(anchor: 12, text: "G")])
    }

    @Test func chordTextKeepsMarkerBassAndParentheses() {
        let chord = SongChord(
            characterNum: 0, noteId: 0, chordTypeId: 0, bassNoteId: 4, marker: "1", inParentheses: true)
        let rendered = SongText.render(text: "Hello world", chords: [chord], includeChords: true)
        #expect(rendered == "(1:C/E)\r\nHello world")
    }

    @Test func blankLinesStayInTheSheet() {
        let lines = SongText.sheet(text: "One\n\nTwo", chords: [])
        #expect(lines.map(\.lyric) == ["One", "", "Two"])
    }

    @Test func aMajorSpellsSharps() {
        let chords = progression([(9, 0), (4, 0), (6, 1), (2, 0)], times: 3)
        let rendered = SongText.render(text: String(repeating: "x", count: 80), chords: chords, includeChords: true)
        #expect(rendered.contains("F♯"))
        #expect(!rendered.contains("G♭"))
    }

    @Test func bFlatMajorSpellsFlats() {
        let chords = progression([(10, 0), (5, 0), (7, 1), (3, 0)], times: 3)
        let rendered = SongText.render(text: String(repeating: "x", count: 80), chords: chords, includeChords: true)
        #expect(rendered.contains("B♭"))
        #expect(rendered.contains("E♭"))
        #expect(!rendered.contains("A♯"))
    }

    @Test func cMajorSpellsCSharpAndEFlat() {
        var chords = progression([(0, 0), (7, 0), (9, 1)], times: 4)
        chords.append(chord(at: 80, note: 1))
        chords.append(chord(at: 84, note: 3))
        let rendered = SongText.render(text: String(repeating: "x", count: 100), chords: chords, includeChords: true)
        #expect(rendered.contains("C♯"))
        #expect(rendered.contains("E♭"))
        #expect(!rendered.contains("D♭"))
        #expect(!rendered.contains("D♯"))
    }

    @Test func modulationKeepsEachRegionsSpelling() {
        let aMajor = progression([(9, 0), (4, 0), (6, 1), (2, 0)], times: 4)
        let bFlat = progression([(10, 0), (5, 0), (7, 1), (3, 0)], times: 4, start: 200)
        let rendered = SongText.render(
            text: String(repeating: "x", count: 400), chords: aMajor + bFlat, includeChords: true)
        #expect(rendered.contains("F♯"))
        #expect(rendered.contains("B♭"))
        #expect(!rendered.contains("G♭"))
    }

}

struct SongFilterTests {
    @Test func blankFilterKeepsEverySong() {
        let songs = sampleSongs
        #expect(SongFilter.matching("   ", in: songs) == songs)
    }

    @Test func filterMatchesInsideTheTitleIgnoringCase() {
        let songs = sampleSongs
        #expect(SongFilter.matching("alp", in: songs).map(\.id) == [1, 3])
        #expect(SongFilter.matching("БОГ", in: songs).map(\.id) == [4])
        #expect(SongFilter.matching("мы с", in: songs).map(\.id) == [5])
        #expect(SongFilter.matching("zzz", in: songs).isEmpty)
    }

    private var sampleSongs: [SongTitle] {
        [
            SongTitle(id: 1, title: "Alpha"),
            SongTitle(id: 2, title: "beta Song"),
            SongTitle(id: 3, title: "Alpine"),
            SongTitle(id: 4, title: "Бог моя защита"),
            SongTitle(id: 5, title: "Вместе мы с вами"),
        ]
    }
}

struct SongSheetLayoutTests {
    @Test func chordSitsAboveItsLyric() {
        let drawing = SongSheetLayout.drawing(for: [
            SongSheetLine(lyric: "Hello", chords: [SongSheetChord(anchor: 0, text: "C")]),
        ])
        let lyric = drawing.glyphs.first { $0.text == "Hello" }
        let chord = drawing.glyphs.first { $0.text == "C" }
        #expect(lyric != nil)
        #expect(chord != nil)
        #expect(chord!.baseline < lyric!.baseline)
        #expect(lyric!.x == 16)
        #expect(colorParts(lyric!.color) == [0, 1])
        #expect(colorParts(chord!.color) == [0, 0, 1, 1])
        #expect(drawing.glyphs.allSatisfy { $0.x >= 0 })
    }

    @Test func chordsAddHeightAndLongerLyricsAddWidth() {
        let plain = SongSheetLayout.drawing(for: [SongSheetLine(lyric: "Hello", chords: [])])
        let withChord = SongSheetLayout.drawing(for: [
            SongSheetLine(lyric: "Hello", chords: [SongSheetChord(anchor: 0, text: "C")]),
        ])
        let longer = SongSheetLayout.drawing(for: [SongSheetLine(lyric: "Hello there", chords: [])])
        #expect(withChord.size.height > plain.size.height)
        #expect(longer.size.width > plain.size.width)
    }
}

@MainActor
struct SongSheetImageTests {
    @Test func imageIsWhiteWithBlackLyricsAndBlueChords() {
        let lines = [SongSheetLine(lyric: "Hello", chords: [SongSheetChord(anchor: 0, text: "C")])]
        let drawing = SongSheetLayout.drawing(for: lines)
        let image = SongSheetImage.image(for: lines, scale: 1)
        // The renderer rounds the sheet up to a whole point, which adds a sliver of white.
        #expect(image.size.width >= drawing.size.width && image.size.width < drawing.size.width + 1)
        #expect(image.size.height >= drawing.size.height && image.size.height < drawing.size.height + 1)
        #expect(image.scale == 1)
        let pixels = pixels(of: image)
        #expect(pixels.contains { $0.x > 250 && $0.y > 250 && $0.z > 250 })
        #expect(pixels.contains { $0.x < 40 && $0.y < 40 && $0.z < 40 })
        #expect(pixels.contains { $0.x < 80 && $0.y < 80 && $0.z > 180 })
    }
}

struct SongbookReadTests {
    @Test func readsTitlesTextAndChordsFromASongbook() throws {
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("songbook-\(UUID().uuidString).songbook")
        defer { try? FileManager.default.removeItem(at: url) }
        try writeSongbook(at: url)

        let titles = try Songbook.titles(in: url)
        #expect(titles.map(\.id) == [1, 2])
        #expect(titles.map(\.title) == ["Alpha", "beta Song"])

        let plain = try Songbook.songText(id: 1, includeChords: false, in: url)
        #expect(plain == "Hello")
        let withChord = try Songbook.songText(id: 1, includeChords: true, in: url)
        #expect(withChord == "C\r\nHello")

        let marked = try Songbook.songText(id: 2, includeChords: true, in: url)
        #expect(marked == "(1:C/E)\r\nHello world")

        let sheet = try Songbook.sheet(id: 1, in: url)
        #expect(sheet == [SongSheetLine(lyric: "Hello", chords: [SongSheetChord(anchor: 0, text: "C")])])

        #expect(throws: SongbookError.songNotFound) {
            try Songbook.sheet(id: 99, in: url)
        }
    }
}

private func chord(at character: Int, note: Int, type: Int = 0) -> SongChord {
    SongChord(
        characterNum: character, noteId: note, chordTypeId: type, bassNoteId: -1, marker: "", inParentheses: false)
}

private func progression(_ pairs: [(Int, Int)], times: Int, start: Int = 0, step: Int = 4) -> [SongChord] {
    var chords: [SongChord] = []
    var character = start
    for _ in 0..<times {
        for (note, type) in pairs {
            chords.append(chord(at: character, note: note, type: type))
            character += step
        }
    }
    return chords
}

private func colorParts(_ color: CGColor) -> [CGFloat] {
    color.components ?? []
}

private func pixels(of image: UIImage) -> [SIMD3<UInt8>] {
    guard let cgImage = image.cgImage else {
        return []
    }
    let width = cgImage.width
    let height = cgImage.height
    var bytes = [UInt8](repeating: 0, count: width * height * 4)
    bytes.withUnsafeMutableBytes { buffer in
        guard let context = CGContext(
            data: buffer.baseAddress,
            width: width,
            height: height,
            bitsPerComponent: 8,
            bytesPerRow: width * 4,
            space: CGColorSpaceCreateDeviceRGB(),
            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
        ) else {
            return
        }
        context.draw(cgImage, in: CGRect(x: 0, y: 0, width: width, height: height))
    }
    var colors: [SIMD3<UInt8>] = []
    colors.reserveCapacity(width * height)
    var index = 0
    while index + 3 < bytes.count {
        colors.append(SIMD3(bytes[index], bytes[index + 1], bytes[index + 2]))
        index += 4
    }
    return colors
}

private func writeSongbook(at url: URL) throws {
    var db: OpaquePointer?
    if sqlite3_open(url.path, &db) != SQLITE_OK {
        throw SongbookError.openFailed("Could not create the test songbook.")
    }
    guard let db else {
        throw SongbookError.openFailed("Could not create the test songbook.")
    }
    defer { sqlite3_close(db) }
    try exec(
        db,
        """
        CREATE TABLE songs (id INTEGER PRIMARY KEY, text TEXT, title TEXT);
        CREATE TABLE song_chord_link (
            song_id INTEGER, character_num INTEGER, note_id INTEGER, chord_type_id INTEGER,
            bass_note_id INTEGER, marker TEXT, in_parentheses INTEGER);
        INSERT INTO songs (id, text, title) VALUES (2, 'Hello world', 'beta Song');
        INSERT INTO songs (id, text, title) VALUES (1, 'Hello', 'Alpha');
        INSERT INTO song_chord_link (
            song_id, character_num, note_id, chord_type_id, bass_note_id, marker, in_parentheses)
        VALUES (1, 0, 0, 0, NULL, '-1', 0);
        INSERT INTO song_chord_link (
            song_id, character_num, note_id, chord_type_id, bass_note_id, marker, in_parentheses)
        VALUES (2, 0, 0, 0, 4, '1', 1);
        """)
}

private func exec(_ db: OpaquePointer, _ sql: String) throws {
    var error: UnsafeMutablePointer<CChar>?
    if sqlite3_exec(db, sql, nil, nil, &error) != SQLITE_OK {
        let message = error.map { String(cString: $0) } ?? "Could not write the test songbook."
        sqlite3_free(error)
        throw SongbookError.queryFailed(message)
    }
}
