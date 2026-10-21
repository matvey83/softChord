//
//  Songbook.swift
//  softChord Viewer
//

import Foundation
import SQLite3

struct SongTitle: Identifiable, Equatable {
    let id: Int
    let title: String
}

enum SongbookError: Error, CustomStringConvertible {
    case missingFile
    case openFailed(String)
    case queryFailed(String)

    var description: String {
        switch self {
        case .missingFile:
            return "zvuki_neba.songbook was not copied into the app."
        case .openFailed(let message), .queryFailed(let message):
            return message
        }
    }
}

enum Songbook {
    /// Titles in the same order as the editor's song table.
    static func titles() throws -> [SongTitle] {
        guard let url = Bundle.main.url(forResource: "zvuki_neba", withExtension: "songbook") else {
            throw SongbookError.missingFile
        }
        return try titles(in: url)
    }

    static func titles(in url: URL) throws -> [SongTitle] {
        var db: OpaquePointer?
        if sqlite3_open_v2(url.path, &db, SQLITE_OPEN_READONLY, nil) != SQLITE_OK {
            let message = db.map { String(cString: sqlite3_errmsg($0)) } ?? "Could not open the songbook."
            sqlite3_close(db)
            throw SongbookError.openFailed(message)
        }
        defer { sqlite3_close(db) }

        var statement: OpaquePointer?
        let sql = "SELECT id, title FROM songs ORDER BY id"
        if sqlite3_prepare_v2(db, sql, -1, &statement, nil) != SQLITE_OK {
            let message = String(cString: sqlite3_errmsg(db))
            throw SongbookError.queryFailed(message)
        }
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

    private static func columnText(_ statement: OpaquePointer?, _ index: Int32) -> String {
        guard let statement, let bytes = sqlite3_column_text(statement, index) else {
            return ""
        }
        return String(cString: UnsafePointer<CChar>(OpaquePointer(bytes)))
    }
}
