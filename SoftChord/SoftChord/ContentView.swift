//
//  ContentView.swift
//  SoftChord
//
//  Created by Matvey Adzhigirey on 10/21/26.
//

import SwiftUI
import UIKit
import UniformTypeIdentifiers

struct ContentView: View {
    @State private var session: SongbookSession
    @State private var filter = ""
    @State private var noticeTitle: String?
    @State private var noticeMessage: String?
    @State private var isImporting = false
    /// Set while the list asks Save / Don't Save / Cancel before a change.
    @State private var pendingLeave: PendingLeave?

    private struct PendingLeave {
        var change: SongbookChangeRequest
        var songTitle: String
    }

    init(songs: [SongTitle]? = nil) {
        var session = SongbookSession()
        if let songs {
            session.songs = songs
            session.loadError = nil
        }
        _session = State(initialValue: session)
    }

    var body: some View {
        NavigationStack {
            Group {
                if let errorMessage = session.loadError {
                    Text(errorMessage)
                        .foregroundStyle(.red)
                        .padding()
                } else {
                    List(SongFilter.matching(filter, in: session.songs)) { song in
                        SongRow(song: song) { title, message in
                            present(title: title, message: message)
                        }
                        .equatable()
                    }
                    .contentMargins(.top, 0, for: .scrollContent)
                    // Header and Search stay put while the list moves. MIRRORED UI:
                    // the web list header (songbook name, Not saved, Sign in, Search).
                    .safeAreaInset(edge: .top, spacing: 0) {
                        VStack(alignment: .leading, spacing: 0) {
                            songbookHeader
                            HStack(spacing: 8) {
                                Text("Search:")
                                SongFilterField(text: $filter)
                            }
                            .padding(.horizontal, 16)
                            .padding(.top, 8)
                            .padding(.bottom, 2)
                        }
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
            .fileImporter(
                isPresented: $isImporting,
                allowedContentTypes: [SongbookSession.songbookContentType],
                allowsMultipleSelection: false
            ) { result in
                handleImportedFile(result)
            }
        }
    }

    /// The songbook name, a down-arrow menu, the grey Not saved label, and
    /// Sign in. The name truncates first; the arrow, label and Sign in stay.
    private var songbookHeader: some View {
        HStack(spacing: 8) {
            Menu {
                Section(SongbookSession.mySongbooksTitle) {
                    ForEach(session.entries) { entry in
                        Button {
                            requestChange(.switchTo(entry.id))
                        } label: {
                            if entry.id == session.currentId {
                                Label(entry.displayName, systemImage: "checkmark")
                            } else {
                                Text(entry.displayName)
                            }
                        }
                    }
                }
                Button(SongbookSession.openFromFilesTitle) {
                    requestChange(.openFile)
                }
                Divider()
                Button(SongbookSession.saveCopyTitle) { presentUnavailable(.saveCopy) }
                Button(SongbookSession.renameTitle) { presentUnavailable(.rename) }
                Button(SongbookSession.deleteTitle) { presentUnavailable(.delete) }
                Button(SongbookSession.shareTitle) { presentUnavailable(.share) }
            } label: {
                HStack(spacing: 4) {
                    Text(session.displayName)
                        .fontWeight(.semibold)
                        .lineLimit(1)
                        .truncationMode(.tail)
                    Image(systemName: "chevron.down")
                        .font(.subheadline.weight(.semibold))
                        .imageScale(.small)
                }
                .foregroundStyle(.primary)
            }
            .menuOrder(.fixed)
            Text(SongbookSession.indicator)
                .font(.footnote)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: true, vertical: false)
                .layoutPriority(1)
            Spacer(minLength: 8)
            Button(SongbookSession.signInTitle) {
                presentUnavailable(.signIn)
            }
            .fixedSize()
            .layoutPriority(1)
        }
        .padding(.horizontal, 16)
        .padding(.top, 8)
        // MIRRORED UI: the song page's Save / Don't Save / Cancel (SongLeavePrompt).
        .alert(SongLeavePrompt.title(for: pendingLeave?.songTitle ?? ""),
               isPresented: leaveIsPresented,
               presenting: pendingLeave) { pending in
            Button(SongLeavePrompt.Action.save.rawValue) {
                resolveLeave(.save, pending)
            }
            Button(SongLeavePrompt.Action.dontSave.rawValue, role: .destructive) {
                resolveLeave(.dontSave, pending)
            }
            Button(SongLeavePrompt.Action.cancel.rawValue, role: .cancel) {
                resolveLeave(.cancel, pending)
            }
        } message: { _ in
            Text(SongLeavePrompt.message)
        }
    }

    /// Back usually asks about a dirty draft before the list is reached, and
    /// then the draft is no longer published. A draft still published here
    /// (SongSessionEdits.unsavedDraft) is asked about before the change.
    private func requestChange(_ change: SongbookChangeRequest) {
        let unsaved = SongSessionEdits.unsavedDraft
        switch session.request(change, dirty: unsaved != nil) {
        case .ignore:
            break
        case .proceed(let change):
            perform(change)
        case .askToLeave(let change):
            pendingLeave = PendingLeave(change: change, songTitle: unsaved?.title ?? "")
        }
    }

    /// Cancel stays. Save and Don't Save settle the draft, then go ahead.
    private func resolveLeave(_ action: SongLeavePrompt.Action, _ pending: PendingLeave) {
        pendingLeave = nil
        if let change = SongLeavePrompt.resolvingUnsavedDraft(action, before: pending.change) {
            perform(change)
        }
    }

    private var leaveIsPresented: Binding<Bool> {
        Binding(
            get: { pendingLeave != nil },
            set: { isPresented in
                if !isPresented {
                    pendingLeave = nil
                }
            })
    }

    private func perform(_ change: SongbookChangeRequest) {
        switch change {
        case .switchTo(let id):
            _ = session.activate(id: id)
            filter = ""
        case .openFile:
            isImporting = true
        }
    }

    private func handleImportedFile(_ result: Result<[URL], Error>) {
        switch result {
        case .success(let urls):
            guard let url = urls.first else {
                return
            }
            if let failure = session.openPickedFile(url) {
                present(title: failure.title, message: failure.message)
            } else {
                filter = ""
            }
        case .failure(let error):
            // Cancelling the picker is not a failure.
            if let failure = SongbookSession.pickerFailure(error) {
                present(title: failure.title, message: failure.message)
            }
        }
    }

    private func presentUnavailable(_ item: SongbookUnavailableItem) {
        present(title: item.title, message: item.message)
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
                SongShareMenu.menu(songId: { songId }, report: report)
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

/// The song list menu. The song page toolbar (SongToolbar.swift) uses the same copy functions.
/// Mirror: softchord_session.py copySongText, copySongTextWithChords, and copySongAsImage.
/// They copy the song as it is shown: the song page passes `shown` (a saved edit
/// and the transpose). Without it, or when it has nothing, the song is read as the
/// list shows it, with the edit saved for this run (SongSessionEdits.shownSource).
enum SongShareMenu {
    static func menu(
        songId: @escaping () -> Int,
        report: @escaping (String, String) -> Void,
        onSelectSegment: ((SongEditSegment) -> Void)? = nil,
        shown: (() -> SongSource?)? = nil
    ) -> UIMenu {
        let song: () throws -> SongSource = {
            if let onScreen = shown?() {
                return onScreen
            }
            return try SongSessionEdits.shownSource(id: songId())
        }
        var children: [UIMenuElement] = [
            UIAction(title: "Copy song text") { _ in
                songShareCopy(song, includeChords: false, report: report)
            },
            UIAction(title: "Copy song text with chords") { _ in
                songShareCopy(song, includeChords: true, report: report)
            },
            UIAction(title: "Copy as image") { _ in
                copySongImage(song, report: report)
            },
            // TODO: re-add Add to Photos to the toolbar (and this menu): addSongToPhotos below.
        ]
        // The Chords/Lyrics switch also lives in this menu, when the song
        // page provides it (the list menu does not). Mirror: the desktop and
        // web overflow menus, which flip the same draft segment.
        if let onSelectSegment {
            children.append(UIAction(title: "Chords") { _ in
                onSelectSegment(.chords)
            })
            children.append(UIAction(title: "Lyrics") { _ in
                onSelectSegment(.lyrics)
            })
        }
        return UIMenu(children: children)
    }
}

private func shownSheet(_ song: () throws -> SongSource) throws -> [SongSheetLine] {
    let shown = try song()
    return SongText.sheet(text: shown.text, chords: shown.chords)
}

func copySongImage(_ song: () throws -> SongSource, report: @escaping (String, String) -> Void) {
    do {
        let image = SongSheetImage.image(for: try shownSheet(song), scale: 2)
        guard let data = image.pngData() else {
            report("Could not copy the song", "The song sheet could not be copied.")
            return
        }
        UIPasteboard.general.setItems([[UTType.png.identifier: data]])
    } catch {
        report("Could not copy the song", String(describing: error))
    }
}

func addSongToPhotos(_ song: () throws -> SongSource, report: @escaping (String, String) -> Void) {
    // Read the song now, as it is shown when the item is chosen.
    let sheet: [SongSheetLine]
    do {
        sheet = try shownSheet(song)
    } catch {
        report("Could not add the song to Photos", String(describing: error))
        return
    }
    Task {
        do {
            let image = SongSheetImage.image(for: sheet, scale: 2)
            try await SongPhotoLibrary.add(image)
        } catch {
            report("Could not add the song to Photos", String(describing: error))
        }
    }
}

func songShareCopy(_ song: () throws -> SongSource, includeChords: Bool, report: @escaping (String, String) -> Void) {
    do {
        let shown = try song()
        UIPasteboard.general.string = SongText.render(text: shown.text, chords: shown.chords, includeChords: includeChords)
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
