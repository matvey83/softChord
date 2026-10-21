//
//  ContentView.swift
//  softChord Viewer
//
//  Created by Matvey Adzhigirey on 10/21/26.
//

import SwiftUI

struct ContentView: View {
    private let songs: [SongTitle]
    private let errorMessage: String?

    init(songs: [SongTitle]? = nil) {
        if let songs {
            self.songs = songs
            self.errorMessage = nil
            return
        }
        do {
            self.songs = try Songbook.titles()
            self.errorMessage = nil
        } catch {
            self.songs = []
            self.errorMessage = String(describing: error)
        }
    }

    var body: some View {
        Group {
            if let errorMessage {
                Text(errorMessage)
                    .foregroundStyle(.red)
                    .padding()
            } else {
                List(songs) { song in
                    Text(song.title)
                }
            }
        }
    }
}

#Preview {
    ContentView(songs: [
        SongTitle(id: 1, title: "Ангелы в небе Господа славят"),
        SongTitle(id: 2, title: "Благодарю, Тебя я"),
    ])
}
