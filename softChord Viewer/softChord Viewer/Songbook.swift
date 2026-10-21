//
//  Songbook.swift
//  softChord Viewer
//

import Foundation
import SQLite3

struct SongTitle: Identifiable, Equatable, Hashable {
    let id: Int
    let title: String
}

enum SongbookError: Error, CustomStringConvertible {
    case missingFile
    case openFailed(String)
    case queryFailed(String)
    case songNotFound

    var description: String {
        switch self {
        case .missingFile:
            return "zvuki_neba.songbook was not copied into the app."
        case .openFailed(let message), .queryFailed(let message):
            return message
        case .songNotFound:
            return "That song is not in the songbook."
        }
    }
}

enum Songbook {
    /// Titles in the same order as the editor's song table.
    nonisolated static func titles() throws -> [SongTitle] {
        guard let url = Bundle.main.url(forResource: "zvuki_neba", withExtension: "songbook") else {
            throw SongbookError.missingFile
        }
        return try titles(in: url)
    }

    nonisolated static func titles(in url: URL) throws -> [SongTitle] {
        try withDatabase(url) { db in
            let statement = try prepare(db, "SELECT id, title FROM songs ORDER BY id")
            defer { sqlite3_finalize(statement) }
            var titles: [SongTitle] = []
            while true {
                let step = sqlite3_step(statement)
                if step == SQLITE_DONE {
                    return titles
                }
                if step != SQLITE_ROW {
                    throw SongbookError.queryFailed(String(cString: sqlite3_errmsg(db)))
                }
                let id = Int(sqlite3_column_int64(statement, 0))
                titles.append(SongTitle(id: id, title: columnText(statement, 1)))
            }
        }
    }

    /// Song text in the editor's clipboard format, with Windows line endings.
    nonisolated static func songText(id: Int, includeChords: Bool) throws -> String {
        guard let url = Bundle.main.url(forResource: "zvuki_neba", withExtension: "songbook") else {
            throw SongbookError.missingFile
        }
        return try songText(id: id, includeChords: includeChords, in: url)
    }

    nonisolated static func songText(id: Int, includeChords: Bool, in url: URL) throws -> String {
        try withDatabase(url) { db in
            let body = try loadBody(id: id, db: db)
            return SongText.render(text: body.text, chords: body.chords, includeChords: includeChords)
        }
    }

    /// Lyric lines with chord names centered on the same letters as the editor.
    nonisolated static func sheet(id: Int) throws -> [SongSheetLine] {
        guard let url = Bundle.main.url(forResource: "zvuki_neba", withExtension: "songbook") else {
            throw SongbookError.missingFile
        }
        return try sheet(id: id, in: url)
    }

    nonisolated static func sheet(id: Int, in url: URL) throws -> [SongSheetLine] {
        try withDatabase(url) { db in
            let body = try loadBody(id: id, db: db)
            return SongText.sheet(text: body.text, chords: body.chords)
        }
    }

    private struct SongBody {
        var text: String
        var chords: [SongChord]
    }

    private nonisolated static func loadBody(id: Int, db: OpaquePointer) throws -> SongBody {
        let song = try prepare(db, "SELECT text FROM songs WHERE id=?")
        defer { sqlite3_finalize(song) }
        try bind(song, id: id, db: db)
        let step = sqlite3_step(song)
        if step == SQLITE_DONE {
            throw SongbookError.songNotFound
        }
        if step != SQLITE_ROW {
            throw SongbookError.queryFailed(String(cString: sqlite3_errmsg(db)))
        }
        let text = columnText(song, 0)

        let links = try prepare(
            db,
            "SELECT character_num, note_id, chord_type_id, bass_note_id, marker, in_parentheses "
                + "FROM song_chord_link WHERE song_id=? ORDER BY rowid")
        defer { sqlite3_finalize(links) }
        try bind(links, id: id, db: db)
        var chords: [SongChord] = []
        while true {
            let chordStep = sqlite3_step(links)
            if chordStep == SQLITE_DONE {
                break
            }
            if chordStep != SQLITE_ROW {
                throw SongbookError.queryFailed(String(cString: sqlite3_errmsg(db)))
            }
            chords.append(SongChord(
                characterNum: Int(sqlite3_column_int64(links, 0)),
                noteId: Int(sqlite3_column_int(links, 1)),
                chordTypeId: Int(sqlite3_column_int(links, 2)),
                bassNoteId: sqlite3_column_type(links, 3) == SQLITE_NULL ? -1 : Int(sqlite3_column_int(links, 3)),
                marker: normalizedMarker(columnText(links, 4)),
                inParentheses: sqlite3_column_int(links, 5) != 0))
        }
        return SongBody(text: text, chords: chords)
    }

    private nonisolated static func normalizedMarker(_ marker: String) -> String {
        if marker.isEmpty || marker == "-1" || marker == "None" {
            return ""
        }
        return marker
    }

    private nonisolated static func withDatabase<T>(_ url: URL, _ body: (OpaquePointer) throws -> T) throws -> T {
        var db: OpaquePointer?
        if sqlite3_open_v2(url.path, &db, SQLITE_OPEN_READONLY, nil) != SQLITE_OK {
            let message = db.map { String(cString: sqlite3_errmsg($0)) } ?? "Could not open the songbook."
            sqlite3_close(db)
            throw SongbookError.openFailed(message)
        }
        guard let db else {
            throw SongbookError.openFailed("Could not open the songbook.")
        }
        defer { sqlite3_close(db) }
        return try body(db)
    }

    private nonisolated static func prepare(_ db: OpaquePointer, _ sql: String) throws -> OpaquePointer {
        var statement: OpaquePointer?
        if sqlite3_prepare_v2(db, sql, -1, &statement, nil) != SQLITE_OK {
            throw SongbookError.queryFailed(String(cString: sqlite3_errmsg(db)))
        }
        guard let statement else {
            throw SongbookError.queryFailed("Could not read the songbook.")
        }
        return statement
    }

    private nonisolated static func bind(_ statement: OpaquePointer, id: Int, db: OpaquePointer) throws {
        if sqlite3_bind_int64(statement, 1, sqlite3_int64(Int64(id))) != SQLITE_OK {
            throw SongbookError.queryFailed(String(cString: sqlite3_errmsg(db)))
        }
    }

    private nonisolated static func columnText(_ statement: OpaquePointer?, _ index: Int32) -> String {
        guard let statement, let bytes = sqlite3_column_text(statement, index) else {
            return ""
        }
        return String(cString: UnsafePointer<CChar>(OpaquePointer(bytes)))
    }
}
