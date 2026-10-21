//
//  ContentView.swift
//  softChord Viewer
//
//  Created by Matvey Adzhigirey on 10/21/26.
//

import SwiftUI
import UIKit
import UniformTypeIdentifiers

struct ContentView: View {
    private let songs: [SongTitle]
    private let errorMessage: String?
    @State private var filter = ""
    @State private var noticeTitle: String?
    @State private var noticeMessage: String?
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
                    List(SongFilter.matching(filter, in: songs)) { song in
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
                            Button("Copy as image") {
                                copyImage(song)
                            }
                            Button("Add to Photos") {
                                addToPhotos(song)
                            }
                        }
                    }
                    .contentMargins(.top, 0, for: .scrollContent)
                    // Kept outside the scrolling rows, so the field stays put while the list moves.
                    .safeAreaInset(edge: .top, spacing: 0) {
                        HStack(spacing: 8) {
                            Text("Search:")
                            SongFilterField(text: $filter)
                        }
                        .padding(.horizontal, 16)
                        .padding(.top, 8)
                        .padding(.bottom, 2)
                        .background(Color(.systemBackground))
                    }
                }
            }
            .toolbar(.hidden, for: .navigationBar)
            .navigationDestination(item: $viewedSong) { song in
                SongPage(song: song)
            }
            .alert(noticeTitle ?? "", isPresented: noticeIsPresented) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(noticeMessage ?? "")
            }
        }
    }

    private var noticeIsPresented: Binding<Bool> {
        Binding(
            get: { noticeTitle != nil },
            set: { isPresented in
                if !isPresented {
                    noticeTitle = nil
                    noticeMessage = nil
                }
            })
    }

    private func present(title: String, message: String) {
        noticeTitle = title
        noticeMessage = message
    }

    private func copy(_ song: SongTitle, includeChords: Bool) {
        do {
            UIPasteboard.general.string = try Songbook.songText(id: song.id, includeChords: includeChords)
        } catch {
            present(title: "Could not copy the song", message: String(describing: error))
        }
    }

    private func copyImage(_ song: SongTitle) {
        do {
            let image = SongSheetImage.image(for: try Songbook.sheet(id: song.id), scale: 2)
            guard let data = image.pngData() else {
                present(title: "Could not copy the song", message: "The song sheet could not be copied.")
                return
            }
            UIPasteboard.general.setItems([[UTType.png.identifier: data]])
        } catch {
            present(title: "Could not copy the song", message: String(describing: error))
        }
    }

    private func addToPhotos(_ song: SongTitle) {
        Task {
            do {
                let image = SongSheetImage.image(for: try Songbook.sheet(id: song.id), scale: 2)
                try await SongPhotoLibrary.add(image)
            } catch {
                present(title: "Could not add the song to Photos", message: String(describing: error))
            }
        }
    }
}

/// A rounded text field with the system clear button.
private struct SongFilterField: UIViewRepresentable {
    @Binding var text: String

    func makeUIView(context: Context) -> UITextField {
        let field = UITextField()
        field.borderStyle = .roundedRect
        field.font = .preferredFont(forTextStyle: .body)
        field.adjustsFontForContentSizeCategory = true
        field.clearButtonMode = .always
        field.autocorrectionType = .no
        field.autocapitalizationType = .none
        field.returnKeyType = .done
        field.setContentHuggingPriority(.defaultLow, for: .horizontal)
        field.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        field.addTarget(context.coordinator, action: #selector(Coordinator.textChanged(_:)), for: .editingChanged)
        field.delegate = context.coordinator
        return field
    }

    func updateUIView(_ field: UITextField, context: Context) {
        if field.text != text {
            field.text = text
        }
    }

    func sizeThatFits(_ proposal: ProposedViewSize, uiView: UITextField, context: Context) -> CGSize? {
        let width = proposal.width ?? UIView.layoutFittingExpandedSize.width
        let height = uiView.sizeThatFits(CGSize(width: width, height: CGFloat.greatestFiniteMagnitude)).height
        return CGSize(width: width, height: height)
    }

    func makeCoordinator() -> Coordinator {
        Coordinator(text: $text)
    }

    final class Coordinator: NSObject, UITextFieldDelegate {
        var text: Binding<String>

        init(text: Binding<String>) {
            self.text = text
        }

        @objc func textChanged(_ field: UITextField) {
            text.wrappedValue = field.text ?? ""
        }

        func textFieldShouldReturn(_ textField: UITextField) -> Bool {
            textField.resignFirstResponder()
            return true
        }
    }
}

#Preview {
    ContentView(songs: [
        SongTitle(id: 1, title: "Ангелы в небе Господа славят"),
        SongTitle(id: 2, title: "Благодарю, Тебя я"),
    ])
}
