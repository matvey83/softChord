//
//  softChord_ViewerTests.swift
//  softChord ViewerTests
//
//  Created by Matvey Adzhigirey on 10/21/26.
//

import Testing
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

    @Test func chordTextKeepsMarkerBassAndParentheses() {
        let chord = SongChord(
            characterNum: 0, noteId: 0, chordTypeId: 0, bassNoteId: 4, marker: "1", inParentheses: true)
        let rendered = SongText.render(text: "Hello world", chords: [chord], includeChords: true)
        #expect(rendered == "(1:C/E)\r\nHello world")
    }

}
