//
//  SongFilter.swift
//  softChord Viewer
//

import Foundation

enum SongFilter {
    /// Titles that contain the query, ignoring case. A blank query keeps every song, in the same order.
    /// Titles that start with the query come first, then titles that contain it, each in the songbook's order.
    /// TODO: Also match the song number, the way the editor's song list filter does.
    nonisolated static func matching(_ query: String, in songs: [SongTitle]) -> [SongTitle] {
        let text = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else {
            return songs
        }
        let locale = Locale(identifier: "en_US")
        let needle = text.lowercased(with: locale)
        var starts: [SongTitle] = []
        var contains: [SongTitle] = []
        for song in songs {
            let title = song.title.lowercased(with: locale)
            if title.hasPrefix(needle) {
                starts.append(song)
            } else if title.contains(needle) {
                contains.append(song)
            }
        }
        return starts + contains
    }
}
