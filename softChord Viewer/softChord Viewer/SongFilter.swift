//
//  SongFilter.swift
//  softChord Viewer
//

import Foundation

enum SongFilter {
    /// Titles that contain the query, ignoring case. A blank query keeps every song, in the same order.
    nonisolated static func matching(_ query: String, in songs: [SongTitle]) -> [SongTitle] {
        let text = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else {
            return songs
        }
        let needle = text.lowercased(with: Locale(identifier: "en_US"))
        return songs.filter { song in
            song.title.lowercased(with: Locale(identifier: "en_US")).contains(needle)
        }
    }
}
