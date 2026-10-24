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
                        SongRow(song: song) { title, message in
                            present(title: title, message: message)
                        }
                        .equatable()
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
            .navigationDestination(for: SongTitle.self) { song in
                SongPage(song: song)
            }
            .task {
                // The sheet fonts are loaded once, after the titles are up.
                Task.detached(priority: .utility) {
                    SongSheetLayout.warm()
                }
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
}

/// A song title. The row stays put while the list's other state changes, so its
/// menu is not rebuilt when nothing in the row changed.
private struct SongRow: View, Equatable {
    let song: SongTitle
    let report: (String, String) -> Void

    static func == (lhs: SongRow, rhs: SongRow) -> Bool {
        lhs.song == rhs.song
    }

    var body: some View {
        NavigationLink(value: song) {
            // TODO: Show the song number in front of the title when it is not -1.
            Text(song.title)
                .foregroundStyle(.primary)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .navigationLinkIndicatorVisibility(.hidden)
        .background {
            // SwiftUI's context menu refreshes itself while it is closed.
            // That refresh blocks the screen on launch, so the items are
            // built only when the press starts.
            SongRowMenuInstaller(songId: song.id, report: report)
        }
    }
}

/// Long-press menu for one row. The interaction is added to the cell, and the
/// items are created when the press begins.
private struct SongRowMenuInstaller: UIViewRepresentable {
    var songId: Int
    var report: (String, String) -> Void

    func makeUIView(context: Context) -> SongRowMenuAnchor {
        let view = SongRowMenuAnchor()
        view.isUserInteractionEnabled = false
        view.backgroundColor = .clear
        view.isOpaque = false
        return view
    }

    func updateUIView(_ view: SongRowMenuAnchor, context: Context) {
        let coordinator = context.coordinator
        coordinator.songId = songId
        coordinator.report = report
        view.onAttach = { [weak coordinator] anchor in
            coordinator?.install(on: anchor)
        }
        coordinator.install(on: view)
    }

    func makeCoordinator() -> Coordinator {
        Coordinator()
    }

    final class Coordinator: NSObject, UIContextMenuInteractionDelegate {
        var songId = 0
        var report: (String, String) -> Void = { _, _ in }
        private weak var installedOn: UIView?
        private var interaction: UIContextMenuInteraction?

        func install(on anchor: UIView) {
            guard let cell = anchor.enclosingCollectionCell() else {
                return
            }
            if installedOn === cell {
                return
            }
            if let installedOn, let interaction {
                installedOn.removeInteraction(interaction)
            }
            let interaction = UIContextMenuInteraction(delegate: self)
            cell.addInteraction(interaction)
            self.interaction = interaction
            installedOn = cell
        }

        func contextMenuInteraction(
            _ interaction: UIContextMenuInteraction,
            configurationForMenuAtLocation location: CGPoint
        ) -> UIContextMenuConfiguration? {
            let songId = self.songId
            let report = self.report
            return UIContextMenuConfiguration(identifier: nil, previewProvider: nil) { _ in
                SongShareMenu.menu(songId: { songId }, report: report, onEdit: nil)
            }
        }

        deinit {
            if let installedOn, let interaction {
                installedOn.removeInteraction(interaction)
            }
        }
    }
}

/// Finds the list cell once this anchor is on screen.
private final class SongRowMenuAnchor: UIView {
    var onAttach: ((UIView) -> Void)?

    override func didMoveToWindow() {
        super.didMoveToWindow()
        guard window != nil else {
            return
        }
        DispatchQueue.main.async { [weak self] in
            guard let self, self.window != nil else {
                return
            }
            self.onAttach?(self)
        }
    }
}

private extension UIView {
    func enclosingCollectionCell() -> UICollectionViewCell? {
        var current: UIView? = self
        while let view = current {
            if let cell = view as? UICollectionViewCell {
                return cell
            }
            current = view.superview
        }
        return nil
    }
}

/// The song list menu and the song page menu share these items.
/// Mirror: softchord_session.py copySongText, copySongTextWithChords, and copySongAsImage.
enum SongShareMenu {
    static func menu(
        songId: @escaping () -> Int,
        report: @escaping (String, String) -> Void,
        onEdit: (() -> Void)?
    ) -> UIMenu {
        var children: [UIMenuElement] = [
            UIAction(title: "Copy song text") { _ in
                songShareCopy(songId: songId(), includeChords: false, report: report)
            },
            UIAction(title: "Copy song text with chords") { _ in
                songShareCopy(songId: songId(), includeChords: true, report: report)
            },
            UIAction(title: "Copy as image") { _ in
                copySongImage(songId: songId(), report: report)
            },
            UIAction(title: "Add to Photos") { _ in
                addSongToPhotos(songId: songId(), report: report)
            },
        ]
        if let onEdit {
            // Mirror: softchord_session.py lyricEditorSelected.
            children.append(UIAction(title: "Edit song text...") { _ in
                onEdit()
            })
        }
        return UIMenu(children: children)
    }
}

private func copySongImage(songId: Int, report: @escaping (String, String) -> Void) {
    do {
        let image = SongSheetImage.image(for: try Songbook.sheet(id: songId), scale: 2)
        guard let data = image.pngData() else {
            report("Could not copy the song", "The song sheet could not be copied.")
            return
        }
        UIPasteboard.general.setItems([[UTType.png.identifier: data]])
    } catch {
        report("Could not copy the song", String(describing: error))
    }
}

private func addSongToPhotos(songId: Int, report: @escaping (String, String) -> Void) {
    Task {
        do {
            let image = SongSheetImage.image(for: try Songbook.sheet(id: songId), scale: 2)
            try await SongPhotoLibrary.add(image)
        } catch {
            report("Could not add the song to Photos", String(describing: error))
        }
    }
}

private func songShareCopy(songId: Int, includeChords: Bool, report: @escaping (String, String) -> Void) {
    do {
        UIPasteboard.general.string = try Songbook.songText(id: songId, includeChords: includeChords)
    } catch {
        report("Could not copy the song", String(describing: error))
    }
}

/// The list search field. Resigning it twice asks UIKit to hide a keyboard
/// that is already hidden.
private final class SongSearchField: UITextField {
    private var isResigning = false

    override func resignFirstResponder() -> Bool {
        resignOnce(self, isResigning: &isResigning) {
            super.resignFirstResponder()
        }
    }
}

/// A rounded text field with the system clear button.
private struct SongFilterField: UIViewRepresentable {
    @Binding var text: String

    func makeUIView(context: Context) -> UITextField {
        let field = SongSearchField()
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
