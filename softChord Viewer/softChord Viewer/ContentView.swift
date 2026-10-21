//
//  ContentView.swift
//  softChord Viewer
//
//  Created by Matvey Adzhigirey on 10/21/26.
//

import SwiftUI
import UIKit

struct ContentView: View {
    private let songs: [SongTitle]
    private let errorMessage: String?
    @State private var copyError: String?
    @State private var viewedSong: SongTitle?

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
        NavigationStack {
            Group {
                if let errorMessage {
                    Text(errorMessage)
                        .foregroundStyle(.red)
                        .padding()
                } else {
                    List(songs) { song in
                        Button {
                            viewedSong = song
                        } label: {
                            Text(song.title)
                                .foregroundStyle(.primary)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)
                        .contextMenu {
                            Button("Copy song text") {
                                copy(song, includeChords: false)
                            }
                            Button("Copy song text with chords") {
                                copy(song, includeChords: true)
                            }
                        }
                    }
                }
            }
            .toolbar(.hidden, for: .navigationBar)
            .navigationDestination(item: $viewedSong) { song in
                SongPage(song: song)
            }
            .alert("Could not copy the song", isPresented: copyErrorIsPresented) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(copyError ?? "")
            }
        }
    }

    private var copyErrorIsPresented: Binding<Bool> {
        Binding(
            get: { copyError != nil },
            set: { isPresented in
                if !isPresented {
                    copyError = nil
                }
            })
    }

    private func copy(_ song: SongTitle, includeChords: Bool) {
        do {
            UIPasteboard.general.string = try Songbook.songText(id: song.id, includeChords: includeChords)
        } catch {
            copyError = String(describing: error)
        }
    }
}

#Preview {
    ContentView(songs: [
        SongTitle(id: 1, title: "Ангелы в небе Господа славят"),
        SongTitle(id: 2, title: "Благодарю, Тебя я"),
    ])
}
