//
//  SongFilter.swift
//  softChord Viewer
//

import Foundation

enum SongFilter {
    /// Titles that contain the query, ignoring case. A blank query keeps every song, in the same order.
    /// TODO: Also match the song number, the way the editor's song list filter does.
    nonisolated static func matching(_ query: String, in songs: [SongTitle]) -> [SongTitle] {
        let text = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else {
            return songs
        }
        let locale = Locale(identifier: "en_US")
        let needle = text.lowercased(with: locale)
        return songs.filter { song in
            song.title.lowercased(with: locale).contains(needle)
        }
    }
}
