//
//  Utf8Tests.swift
//  SoftChordTests
//
//  Copied and exported text is UTF-8. The same sample (Cyrillic, accented
//  Latin, emoji) is used by the desktop (src/test_song.py) and web
//  (softChord_web/tests/utf8.test.js) tests. A source scan in
//  src/test_utf8_guards.py also fails on non-UTF-8 String/Data conversions.
//

import Foundation
import SQLite3
import Testing
import UIKit
import UniformTypeIdentifiers
@testable import SoftChord

/// Shared with the desktop and web tests.
let utf8Sample = "Привет café 🎵"

@Suite(.serialized)
struct Utf8Tests {

    @MainActor private func sampleSource() -> SongSource {
        SongSource(
            text: utf8Sample + "\n" + utf8Sample,
            chords: [SongChord.from(text: "Am", characterNum: 0)])
    }

    @Test @MainActor func songTextRoundTripsThroughUTF8Bytes() throws {
        for includeChords in [false, true] {
            let source = sampleSource()
            let text = SongText.render(text: source.text, chords: source.chords, includeChords: includeChords)
            #expect(text.contains(utf8Sample))
            let bytes = Data(text.utf8)
            let decoded = try #require(String(data: bytes, encoding: .utf8))
            #expect(decoded == text)
            #expect(!decoded.contains("?"))
        }
    }

    /// Copy Song Text (with and without chords) puts UTF-8 plain text on the pasteboard.
    @Test @MainActor func copySongTextIsUTF8OnThePasteboard() throws {
        let pasteboard = try #require(UIPasteboard(name: UIPasteboard.Name(UUID().uuidString), create: true))
        defer { UIPasteboard.remove(withName: pasteboard.name) }
        for includeChords in [false, true] {
            var failure: String?
            let source = sampleSource()
            songShareCopy({ source }, includeChords: includeChords, report: { _, message in failure = message },
                          pasteboard: pasteboard)
            #expect(failure == nil)
            let expected = SongText.render(text: source.text, chords: source.chords, includeChords: includeChords)
            #expect(pasteboard.string == expected)
            let data = try #require(pasteboard.data(forPasteboardType: UTType.utf8PlainText.identifier))
            #expect(String(data: data, encoding: .utf8) == expected)
        }
    }

    /// Song titles and text are read from the songbook as UTF-8 and copy back out unchanged.
    @Test @MainActor func songbookTextIsReadAsUTF8() throws {
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("utf8-\(UUID().uuidString).songbook")
        defer { try? FileManager.default.removeItem(at: url) }
        try writeSongbook(at: url)
        try withTestDatabase(url) { db in
            try exec(db, "UPDATE songs SET title = '\(utf8Sample)', text = '\(utf8Sample)' WHERE id = 1;")
        }
        let titles = try Songbook.titles(in: url)
        #expect(titles.contains { $0.id == 1 && $0.title == utf8Sample })
        let source = try Songbook.source(id: 1, in: url)
        #expect(source.text == utf8Sample)
        let plain = try Songbook.songText(id: 1, includeChords: false, in: url)
        #expect(plain == utf8Sample)
        let withChords = try Songbook.songText(id: 1, includeChords: true, in: url)
        #expect(withChords.hasSuffix(utf8Sample))
        #expect(String(data: Data(withChords.utf8), encoding: .utf8) == withChords)
    }
}
