//
//  SongPage.swift
//  softChord Viewer
//

import SwiftUI
import UIKit

/// Letters and chords kept after Save, for this run of the app.
/// The songbook file is not changed. Quit the app and the copy is gone.
enum SongSessionEdits {
    struct Copy: Equatable {
        var text: String?
        var chords: [SongChord]?
    }

    private static var copies: [Int: Copy] = [:]

    static func copy(for id: Int) -> Copy? {
        copies[id]
    }

    static func save(id: Int, text: String?, chords: [SongChord]?) {
        if text == nil, chords == nil {
            copies[id] = nil
        } else {
            copies[id] = Copy(text: text, chords: chords)
        }
    }

    static func reset() {
        copies = [:]
    }

    /// The song as the list shows it: the songbook's, with the copy saved for
    /// this run in its place.
    static func shownSource(id: Int) throws -> SongSource {
        var song = try Songbook.source(id: id)
        if let copy = copies[id] {
            song.text = copy.text ?? song.text
            song.chords = copy.chords ?? song.chords
        }
        return song
    }
}

struct SongPage: View {
    @Environment(\.dismiss) private var dismiss
    @State private var steps = 0
    @State private var noticeTitle: String?
    @State private var noticeMessage: String?
    @State private var editing = false
    /// Chord editing is the other edit mode. Only one of the two is on at a time.
    @State private var editingChords = false
    /// The letter picked in chord editing. Its chord, if it has one, is the selected chord.
    @State private var chordSelection: Int?
    @State private var chordRequest: SongChordEditRequest?
    /// Where the song controls end and where the chord view begins, both in window
    /// coordinates. The chord view starts below the controls, so they never cover text.
    @State private var panelBottom: CGFloat = 0
    @State private var chordViewTop: CGFloat = 0
    @State private var closeWhenKeyboardEnds = false
    /// Set once the keyboard has finished hiding, so Back can pop from the page.
    @State private var popWhenReady = false
    @State private var draft = ""
    /// Chord positions for the edit in progress. Note ids stay as stored.
    @State private var editChords: [SongChord] = []
    /// Lyrics drawn after Save. Nil means the songbook text.
    /// Also kept for this run of the app, so opening the song again shows them.
    @State private var shownText: String?
    /// Chord positions drawn after Save. Nil means the songbook chords.
    @State private var shownChords: [SongChord]?

    let title: String
    private let songId: Int
    private let source: SongSource?
    private let errorMessage: String?

    init(song: SongTitle) {
        // Start listening before a tap can hide the keyboard. Back then knows
        // a hide is already running and does not start another one.
        _ = KeyboardActivity.shared
        title = song.title
        songId = song.id
        let kept = SongSessionEdits.copy(for: song.id)
        _shownText = State(initialValue: kept?.text)
        _shownChords = State(initialValue: kept?.chords)
        do {
            source = try Songbook.source(id: song.id)
            errorMessage = nil
        } catch {
            source = nil
            errorMessage = String(describing: error)
        }
    }

    private var lyricText: String {
        shownText ?? source?.text ?? ""
    }

    private var lines: [SongSheetLine] {
        guard let shown = shownSong else {
            return []
        }
        return SongText.sheet(text: shown.text, chords: shown.chords)
    }

    /// The song as it is on screen while viewing: a saved edit, and the chords
    /// at the current transpose. Copy and Add to Photos use this.
    private var shownSong: SongSource? {
        guard let source else {
            return nil
        }
        return SongSource(text: lyricText, chords: SongTranspose.shifted(shownChords ?? source.chords, by: steps))
    }

    /// Unsaved keystrokes and a transpose are still only on this page.
    /// A saved edit stays for this run, but it is not in the songbook file.
    private var bannerText: String? {
        guard let source else {
            return nil
        }
        let storedText = shownText ?? source.text
        let storedChords = shownChords ?? source.chords
        let dirtyDraft = (editing || editingChords) && (draft != storedText || editChords != storedChords)
        let transposed = SongTranspose.changesChords(steps, in: storedChords)
        let kept = shownText != nil || shownChords != nil
        if dirtyDraft || (transposed && !kept) {
            return "Changes do not persist"
        }
        if kept {
            // The saved edit stays for this run. The transpose does not, so a
            // song with both says so for each.
            return transposed ? "Not written to the songbook. Transpose does not persist." : "Not written to the songbook"
        }
        return nil
    }

    /// The chord controls hang below the navigation bar, one row each. The
    /// chord view starts under the lowest of them.
    private var chordControlsInset: CGFloat {
        max(0, panelBottom - chordViewTop) + 8
    }

    var body: some View {
        Group {
            if let errorMessage {
                Text(errorMessage)
                    .foregroundStyle(.red)
                    .padding()
            } else if editing {
                // Mirror: CustomTextEdit.paintEvent in softchord_session.py
                // while lyric_editor_mode is on. The field paints the letters,
                // then the chords on top. A tap still places the caret.
                SongLyricEditor(
                    text: $draft,
                    chords: SongTranspose.shifted(editChords, by: steps),
                    editing: $editing,
                    closeWhenKeyboardEnds: $closeWhenKeyboardEnds,
                    onTextChange: lyricDraftChanged
                )
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
                    .background(Color.white)
            } else if editingChords {
                // Mirror: the desktop's Edit Chords mode (chordEditorSelected).
                // The letters are read-only. A press selects a letter and its
                // chord, and a drag moves the chord onto another letter.
                VStack(spacing: 0) {
                    Color.clear.frame(height: chordControlsInset)
                    SongChordEditor(
                        text: draft,
                        chords: SongTranspose.shifted(editChords, by: steps),
                        selection: $chordSelection,
                        onChordMoved: moveChord,
                        onEditRequested: requestChordEdit
                    )
                }
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
                    .background(Color.white)
                    .onGeometryChange(for: CGFloat.self) { $0.frame(in: .global).minY } action: {
                        chordViewTop = $0
                    }
            } else {
                SongZoomCanvas(lines: lines)
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
                    .background(Color.white)
            }
        }
        .sheet(item: $chordRequest) { request in
            SongChordTextSheet(request: request) { text in
                applyChordText(text, for: request)
            }
        }
        .navigationBarTitleDisplayMode(.inline)
        .toolbar(.visible, for: .navigationBar)
        .navigationBarBackButtonHidden(true)
        .toolbar {
            // The bar's own back item highlights and then loses the press.
            // The song controls draw Back instead, above the bar. This spacer
            // only keeps the title from sliding under that button. With no
            // song loaded there are no song controls, so the bar keeps Back.
            if source == nil {
                ToolbarItem(placement: .topBarLeading) {
                    Button {
                        dismiss()
                    } label: {
                        HStack(spacing: 4) {
                            Image(systemName: "chevron.left")
                            Text("Back")
                        }
                    }
                }
            } else {
                ToolbarItem(placement: .topBarLeading) {
                    Color.clear
                        .frame(width: 88, height: 1)
                        .accessibilityHidden(true)
                }
                .sharedBackgroundVisibility(.hidden)
            }
            ToolbarItem(placement: .principal) {
                // TODO: Under the title, show the subtitle when it is not empty,
                // and the auto-detected key in the editor's words
                // ("Auto-detected key: ..."). Port key_label and
                // format_auto_detected_key_text from softchord_chords.py.
                // This page keeps transpose in memory. The editor keeps saving it.
                Text(title)
                    .font(.headline)
                    .lineLimit(1)
            }
            // Leaves room so the title does not run under the buttons.
            // The buttons themselves are pinned to the top of the bar.
            if source != nil {
                ToolbarItem(placement: .topBarTrailing) {
                    Color.clear
                        .frame(width: editing || editingChords ? 170 : 140, height: 1)
                        .accessibilityHidden(true)
                }
                .sharedBackgroundVisibility(.hidden)
            }
        }
        .background {
            if source != nil {
                SongChromeDock(
                    editing: editing || editingChords,
                    chordMode: editingChords,
                    selectionState: chordSelectionState,
                    songId: songId,
                    steps: $steps,
                    chords: editingChords ? editChords : (shownChords ?? source?.chords ?? []),
                    onBack: { leaveSong() },
                    onEdit: beginLyricEdit,
                    onEditChords: beginChordEdit,
                    onEditChord: { requestChordEdit(chordSelection) },
                    onDeleteChord: deleteSelectedChord,
                    onDiscard: { finishEditing(save: false) },
                    onSave: { finishEditing(save: true) },
                    shownSong: { shownSong },
                    onPanelBottom: { panelBottom = $0 },
                    onNotice: { title, message in
                        noticeTitle = title
                        noticeMessage = message
                    }
                )
            }
        }
        .onChange(of: popWhenReady) { _, pop in
            if pop {
                dismiss()
            }
        }
        .alert(noticeTitle ?? "", isPresented: noticeIsPresented) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(noticeMessage ?? "")
        }
        .safeAreaInset(edge: .bottom, spacing: 0) {
            if let bannerText {
                Text(bannerText)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 8)
                    .background(Color.white)
            }
        }
    }

    private func beginLyricEdit() {
        guard !editing, !editingChords else {
            return
        }
        draft = lyricText
        editChords = shownChords ?? source?.chords ?? []
        editing = true
    }

    private func lyricDraftChanged(_ newText: String) {
        editChords = SongLyricChords.moved(editChords, from: draft, to: newText)
        draft = newText
    }

    /// Chord editing keeps the letters as they are. Chords are stored as the
    /// songbook has them, and drawn shifted by the transpose steps.
    private func beginChordEdit() {
        guard !editing, !editingChords else {
            return
        }
        draft = lyricText
        editChords = shownChords ?? source?.chords ?? []
        chordSelection = nil
        chordRequest = nil
        editingChords = true
    }

    private func moveChord(from: Int, to: Int) {
        editChords = SongLyricChords.reattached(editChords, from: from, to: to)
    }

    /// What the buttons need to know: nothing picked, a letter, or a chord.
    private var chordSelectionState: SongChordSelectionState {
        guard let selected = chordSelection else {
            return .none
        }
        return editChords.contains { $0.characterNum == selected } ? .chord : .letter
    }

    /// The text field starts with the chord as it is drawn, so a transposed
    /// song shows the shifted name. A letter with no chord starts with C.
    private func requestChordEdit(_ characterNum: Int?) {
        guard editingChords, let characterNum else {
            return
        }
        let shown = SongTranspose.shifted(editChords, by: steps)
        let current = SongText.displayedChordText(text: draft, chords: shown, characterNum: characterNum)
        chordRequest = SongChordEditRequest(
            characterNum: characterNum, initialText: current ?? "C", isNew: current == nil)
    }

    private func applyChordText(_ text: String, for request: SongChordEditRequest) {
        guard SoftchordChords.isValidChordText(text) else {
            return
        }
        if !request.isNew, text.trimmingCharacters(in: .whitespacesAndNewlines) == request.initialText {
            return
        }
        editChords = SongLyricChords.replaced(
            editChords, at: request.characterNum, withText: text, steps: steps)
    }

    private func deleteSelectedChord() {
        guard editingChords, let selected = chordSelection else {
            return
        }
        editChords = SongLyricChords.deleted(editChords, at: selected)
    }

    private func finishEditing(save: Bool) {
        if editingChords {
            if save {
                commitEdit()
            }
            // No keyboard is up in this mode, so the page can leave it now.
            chordRequest = nil
            chordSelection = nil
            editingChords = false
        } else {
            closeLyricEditor(save: save)
        }
    }

    private func commitEdit() {
        let sameText = draft == source?.text
        let sameChords = editChords == source?.chords
        shownText = sameText ? nil : draft
        shownChords = sameChords ? nil : editChords
        SongSessionEdits.save(id: songId, text: shownText, chords: shownChords)
    }

    /// The field resigns before it leaves the screen. Removing it while the
    /// keyboard is still hiding asks UIKit to hide an input view that is
    /// already hidden.
    private func closeLyricEditor(save: Bool) {
        if save {
            commitEdit()
        }
        closeWhenKeyboardEnds = true
    }

    /// Pop after the keyboard is down. Popping while a field is still typing
    /// hides the keyboard, and taking the page away hides it again.
    private func leaveSong() {
        let field = focusedTextInput()
        // Nothing is typing, and no hide is running. The list has to come
        // back from this press, not from a later turn.
        guard field != nil || KeyboardActivity.shared.isHiding else {
            dismiss()
            return
        }
        // The pop has to happen from the page update. Dismiss inside the
        // hide callback is ignored, and a view update during the hide
        // asks UIKit to hide the keyboard a second time.
        KeyboardActivity.shared.whenKeyboardIsDown(field) {
            popWhenReady = true
        }
    }

    private func focusedTextInput() -> UIView? {
        let scenes = UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }
        for scene in scenes {
            for window in scene.windows where window.isKeyWindow {
                if let field = firstResponder(in: window), field is UITextField || field is UITextView {
                    return field
                }
            }
        }
        return nil
    }

    private func firstResponder(in view: UIView) -> UIView? {
        if view.isFirstResponder {
            return view
        }
        for subview in view.subviews {
            if let found = firstResponder(in: subview) {
                return found
            }
        }
        return nil
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
}

/// Pins Back, the menu, and the transpose buttons to the top of the navigation bar.
/// A SwiftUI menu in that corner is rebuilt while it is closed, and the first
/// choice then waits. These buttons keep one menu for the life of the page.
private struct SongChromeDock: UIViewRepresentable {
    var editing: Bool
    var chordMode: Bool
    var selectionState: SongChordSelectionState
    var songId: Int
    @Binding var steps: Int
    /// The chords the page is showing. Transposing does nothing to a song with no
    /// recognized chord, so Reset stays dimmed for it.
    var chords: [SongChord]
    var onBack: () -> Void
    var onEdit: () -> Void
    var onEditChords: () -> Void
    var onEditChord: () -> Void
    var onDeleteChord: () -> Void
    var onDiscard: () -> Void
    var onSave: () -> Void
    var shownSong: () -> SongSource?
    var onPanelBottom: (CGFloat) -> Void
    var onNotice: (String, String) -> Void

    func makeUIView(context: Context) -> SongChromeAnchor {
        let view = SongChromeAnchor()
        view.isUserInteractionEnabled = false
        view.backgroundColor = .clear
        return view
    }

    func updateUIView(_ view: SongChromeAnchor, context: Context) {
        let coordinator = context.coordinator
        coordinator.songId = songId
        coordinator.steps = $steps
        coordinator.chords = chords
        coordinator.applyTransposeState()
        coordinator.editing = editing
        coordinator.chordMode = chordMode
        coordinator.selectionState = selectionState
        coordinator.onBack = onBack
        coordinator.onEdit = onEdit
        coordinator.onEditChords = onEditChords
        coordinator.onEditChord = onEditChord
        coordinator.onDeleteChord = onDeleteChord
        coordinator.onDiscard = onDiscard
        coordinator.onSave = onSave
        coordinator.shownSong = shownSong
        coordinator.onPanelBottom = onPanelBottom
        coordinator.onNotice = onNotice
        view.onInstall = { [weak coordinator, weak view] in
            guard let coordinator, let view else {
                return
            }
            coordinator.install(on: view)
        }
        coordinator.install(on: view)
        coordinator.applyEditing()
    }

    func makeCoordinator() -> Coordinator {
        Coordinator()
    }

    static func dismantleUIView(_ view: SongChromeAnchor, coordinator: Coordinator) {
        view.removePanel()
    }

    final class Coordinator: NSObject {
        var songId = 0
        var steps: Binding<Int> = .constant(0)
        var chords: [SongChord] = []
        var editing = false
        var chordMode = false
        var selectionState = SongChordSelectionState.none
        var onBack: () -> Void = {}
        var onEdit: () -> Void = {}
        var onEditChords: () -> Void = {}
        var onEditChord: () -> Void = {}
        var onDeleteChord: () -> Void = {}
        private weak var anchor: SongChromeAnchor?
        /// Set once the page drops the buttons, so a late update cannot put them
        /// back on the list.
        private var closed = false
        var onDiscard: () -> Void = {}
        var onSave: () -> Void = {}
        var shownSong: () -> SongSource? = { nil }
        var onPanelBottom: (CGFloat) -> Void = { _ in }
        private var reportedBottom: CGFloat?
        var onNotice: (String, String) -> Void = { _, _ in }
        private var viewControls: UIView?
        private var editControls: UIView?
        private var chordTools: UIView?
        private var resetTransposeButton: UIButton?
        private var editChordButton: UIButton?
        private var deleteChordButton: UIButton?

        func install(on anchor: SongChromeAnchor) {
            // The bar's container covers the screen and takes presses that land
            // on the buttons. They stay in the bar's own view, above that
            // container. The bar's controller presents the menu. An extra
            // child controller makes Back flash and then time out.
            // Once the page has left the window, a late update must not put
            // the buttons back on the list.
            self.anchor = anchor
            guard !closed, anchor.window != nil, anchor.panel == nil,
                  let bar = anchor.navigationBar(),
                  let parent = anchor.barOwner(for: bar) else {
                return
            }
            let panel = makePanel()
            panel.translatesAutoresizingMaskIntoConstraints = false
            parent.view.addSubview(panel)
            NSLayoutConstraint.activate([
                panel.topAnchor.constraint(equalTo: bar.safeAreaLayoutGuide.topAnchor),
                panel.leadingAnchor.constraint(equalTo: bar.layoutMarginsGuide.leadingAnchor),
                panel.trailingAnchor.constraint(equalTo: bar.layoutMarginsGuide.trailingAnchor),
            ])
            anchor.panel = panel
            anchor.installFrontObserver()
            anchor.moveHostAboveTheBar()
            applyEditing()
        }

        /// Reset transpose is dimmed until the song has been moved. The page starts
        /// at 0 steps each time a song is opened, so 0 is the key it had when it
        /// was loaded in this session. Up then Down by the same amount is 0 again, and so
        /// is a whole octave (12), which shows the same chords.
        func applyTransposeState() {
            resetTransposeButton?.isEnabled = SongTranspose.changesChords(steps.wrappedValue, in: chords)
        }

        func applyEditing() {
            viewControls?.isHidden = editing
            editControls?.isHidden = !editing
            chordTools?.isHidden = !(editing && chordMode)
            editChordButton?.isEnabled = selectionState != .none
            deleteChordButton?.isEnabled = selectionState == .chord
        }

        private func makePanel() -> SongChromePanel {
            let menuButton = UIButton(configuration: menuConfiguration())
            menuButton.showsMenuAsPrimaryAction = true
            menuButton.menu = SongShareMenu.menu(
                songId: { [weak self] in self?.songId ?? 0 },
                report: { [weak self] title, message in
                    self?.onNotice(title, message)
                },
                onEdit: { [weak self] in
                    self?.onEdit()
                },
                onEditChords: { [weak self] in
                    self?.onEditChords()
                },
                shown: { [weak self] in
                    self?.shownSong()
                })
            menuButton.accessibilityLabel = "Menu"

            // Mirror: softchord_session.py transposeDown and transposeUp, and the
            // Reset transpose button next to them.
            let reset = resetTransposeConfiguredButton()
            resetTransposeButton = reset
            let row = UIStackView(arrangedSubviews: [
                arrowButton("arrow.down", name: "Down", delta: -1),
                arrowButton("arrow.up", name: "Up", delta: 1),
                reset,
            ])
            row.axis = .horizontal
            row.spacing = 6
            row.alignment = .center

            let stack = UIStackView(arrangedSubviews: [menuButton, row])
            stack.axis = .vertical
            stack.alignment = .trailing
            stack.spacing = 6
            stack.setContentHuggingPriority(.required, for: .horizontal)
            viewControls = stack

            // Mirror: the desktop lyric editor keeps typed letters in the open song.
            // Save does that for this screen. The songbook file stays as it was.
            let edits = UIStackView(arrangedSubviews: [
                textButton("Discard", prominent: false, action: #selector(discardTapped)),
                textButton("Save", prominent: true, action: #selector(saveTapped)),
            ])
            edits.axis = .horizontal
            edits.spacing = 6
            edits.isHidden = true
            editControls = edits

            // Mirror: the desktop's chord dialog and deleteSelectedChord.
            let editChord = textButton("Edit chord", prominent: false, action: #selector(editChordTapped))
            let deleteChord = textButton("Delete chord", prominent: false, action: #selector(deleteChordTapped))
            editChordButton = editChord
            deleteChordButton = deleteChord
            let tools = UIStackView(arrangedSubviews: [editChord, deleteChord])
            tools.axis = .vertical
            tools.alignment = .trailing
            tools.spacing = 6
            tools.isHidden = true
            chordTools = tools

            let trailing = UIStackView(arrangedSubviews: [stack, edits, tools])
            trailing.axis = .vertical
            trailing.alignment = .trailing
            trailing.spacing = 6
            trailing.setContentHuggingPriority(.required, for: .horizontal)

            // The gap is not a control. The panel refuses presses that miss a button.
            let spacer = UIView()
            spacer.isUserInteractionEnabled = false
            spacer.setContentHuggingPriority(.fittingSizeLevel, for: .horizontal)
            spacer.setContentCompressionResistancePriority(.fittingSizeLevel, for: .horizontal)

            let panel = SongChromePanel(arrangedSubviews: [backButton(), spacer, trailing])
            panel.axis = .horizontal
            panel.alignment = .top
            // The page keeps its text below the lowest control.
            panel.onLayout = { [weak self, weak panel] in
                guard let self, let panel else {
                    return
                }
                let bottom = panel.convert(panel.bounds, to: nil).maxY
                guard bottom != self.reportedBottom else {
                    return
                }
                self.reportedBottom = bottom
                DispatchQueue.main.async { self.onPanelBottom(bottom) }
            }
            return panel
        }

        private func backButton() -> UIButton {
            var config = UIButton.Configuration.glass()
            config.title = "Back"
            config.image = UIImage(systemName: "chevron.left")
            config.imagePadding = 4
            config.buttonSize = .small
            config.cornerStyle = .capsule
            let button = UIButton(configuration: config, primaryAction: UIAction { [weak self] _ in
                // Take the buttons down before the pop. They are hosted on the
                // navigation controller, which stays up when the song leaves.
                self?.closeChrome()
                self?.onBack()
            })
            button.accessibilityLabel = "Back"
            button.setContentHuggingPriority(.required, for: .horizontal)
            button.setContentCompressionResistancePriority(.required, for: .horizontal)
            return button
        }

        private func menuConfiguration() -> UIButton.Configuration {
            var config = UIButton.Configuration.bordered()
            config.image = UIImage(systemName: "line.3.horizontal")
            config.buttonSize = .small
            config.cornerStyle = .capsule
            // A popup indicator is the extra chevron. This button is the menu itself.
            config.indicator = .none
            return config
        }

        private func arrowButton(_ symbol: String, name: String, delta: Int) -> UIButton {
            var config = UIButton.Configuration.bordered()
            config.image = UIImage(systemName: symbol)
            config.buttonSize = .small
            config.cornerStyle = .capsule
            let button = UIButton(configuration: config)
            button.accessibilityLabel = name
            button.tag = delta
            button.addTarget(self, action: #selector(transposeTapped(_:)), for: .touchUpInside)
            return button
        }

        private func resetTransposeConfiguredButton() -> UIButton {
            var config = UIButton.Configuration.bordered()
            config.image = UIImage(systemName: "arrow.counterclockwise")
            config.buttonSize = .small
            config.cornerStyle = .capsule
            let button = UIButton(configuration: config)
            button.accessibilityLabel = "Reset transpose"
            button.isEnabled = SongTranspose.changesChords(steps.wrappedValue, in: chords)
            button.addTarget(self, action: #selector(resetTransposeTapped), for: .touchUpInside)
            return button
        }

        private func textButton(_ title: String, prominent: Bool, action: Selector) -> UIButton {
            var config = prominent ? UIButton.Configuration.filled() : .bordered()
            config.title = title
            config.buttonSize = .small
            config.cornerStyle = .capsule
            // A title is one line. The button grows to fit it.
            config.titleLineBreakMode = .byClipping
            let button = UIButton(configuration: config)
            button.titleLabel?.numberOfLines = 1
            button.setContentHuggingPriority(.required, for: .horizontal)
            button.setContentCompressionResistancePriority(.required, for: .horizontal)
            button.addTarget(self, action: action, for: .touchUpInside)
            return button
        }

        private func closeChrome() {
            closed = true
            anchor?.removePanel()
        }

        @objc private func transposeTapped(_ sender: UIButton) {
            steps.wrappedValue += sender.tag
        }

        @objc private func resetTransposeTapped() {
            steps.wrappedValue = 0
        }

        @objc private func editChordTapped() {
            onEditChord()
        }

        @objc private func deleteChordTapped() {
            onDeleteChord()
        }

        @objc private func discardTapped() {
            onDiscard()
        }

        @objc private func saveTapped() {
            onSave()
        }
    }
}

/// The gap between Back and the menu is not a button. Presses there
/// belong to the song.
private final class SongChromePanel: UIStackView {
    var onLayout: (() -> Void)?

    override func layoutSubviews() {
        super.layoutSubviews()
        onLayout?()
    }

    override func point(inside point: CGPoint, with event: UIEvent?) -> Bool {
        for subview in subviews.reversed()
            where !subview.isHidden && subview.isUserInteractionEnabled && subview.alpha > 0.01 {
            if subview.point(inside: convert(point, to: subview), with: event) {
                return true
            }
        }
        return false
    }
}

/// Sits in the page so it can find the navigation bar, then removes its
/// buttons when the page goes away.
private final class SongChromeAnchor: UIView {
    var onInstall: (() -> Void)?
    weak var panel: UIView?
    private var frontObserver: CFRunLoopObserver?
    private var appearGeneration = 0

    override func didMoveToWindow() {
        super.didMoveToWindow()
        if window == nil {
            removePanel()
            return
        }
        let generation = appearGeneration
        DispatchQueue.main.async { [weak self] in
            guard let self, self.window != nil, self.appearGeneration == generation else {
                return
            }
            self.onInstall?()
        }
    }

    deinit {
        // The buttons live on the navigation controller, which stays on screen
        // after this page is popped. Drop them here if dismantle did not run.
        removePanel()
    }

    /// The bar container moves itself in front again during layout. This runs
    /// after that layout, while the run loop is waiting for the next press.
    func installFrontObserver() {
        guard frontObserver == nil else {
            return
        }
        let observer = CFRunLoopObserverCreateWithHandler(
            kCFAllocatorDefault,
            CFRunLoopActivity.beforeWaiting.rawValue,
            true,
            0
        ) { [weak self] _, _ in
            self?.moveHostAboveTheBar()
        }
        CFRunLoopAddObserver(CFRunLoopGetMain(), observer, .commonModes)
        frontObserver = observer
    }

    /// Puts the buttons just above the bar container. An open menu stays above them.
    /// A press that is already down is left alone. Moving a view cancels that press,
    /// which is how Back was flashing and then doing nothing. Back lives in the bar,
    /// so it has no UIControl tracking flag. Any finger still down has to count.
    func moveHostAboveTheBar() {
        guard let panel, let parent = panel.superview, !menuIsOpen(panel),
              let ourIndex = parent.subviews.firstIndex(of: panel) else {
            return
        }
        guard let barIndex = parent.subviews.indices.last(where: {
            String(describing: type(of: parent.subviews[$0])).contains("FloatingBar")
        }), ourIndex < barIndex else {
            return
        }
        let root = parent.window ?? parent
        guard !controlIsTracking(root), !touchIsDown(root) else {
            return
        }
        parent.insertSubview(panel, aboveSubview: parent.subviews[barIndex])
    }

    func removePanel() {
        appearGeneration += 1
        onInstall = nil
        removeFrontObserver()
        panel?.removeFromSuperview()
        panel = nil
    }

    func navigationBar() -> UINavigationBar? {
        var responder: UIResponder? = self
        while let current = responder {
            if let controller = current as? UIViewController {
                return controller.navigationController?.navigationBar
            }
            responder = current.next
        }
        return nil
    }

    /// The controller whose own view contains the bar.
    func barOwner(for bar: UIView) -> UIViewController? {
        var current: UIView? = bar
        while let view = current, !(view is UIWindow) {
            if let controller = view.next as? UIViewController, controller.view === view {
                return controller
            }
            current = view.superview
        }
        return nil
    }

    private func removeFrontObserver() {
        if let frontObserver {
            CFRunLoopRemoveObserver(CFRunLoopGetMain(), frontObserver, .commonModes)
        }
        frontObserver = nil
    }

    private func menuIsOpen(_ view: UIView) -> Bool {
        if let button = view as? UIButton, button.isHeld {
            return true
        }
        return view.subviews.contains { menuIsOpen($0) }
    }

    private func controlIsTracking(_ view: UIView) -> Bool {
        if let control = view as? UIControl, control.isTracking {
            return true
        }
        return view.subviews.contains { controlIsTracking($0) }
    }

    private func touchIsDown(_ view: UIView) -> Bool {
        if let recognizers = view.gestureRecognizers {
            for recognizer in recognizers where recognizer.numberOfTouches > 0 {
                return true
            }
        }
        return view.subviews.contains { touchIsDown($0) }
    }
}

/// Letters with the chords painted above them, without line wrapping.
/// Mirror: softchord_session.py sets the editor font to lyrics_font and
/// setLineWrapMode(NoWrap) on CustomTextEdit. paintChordLayer draws the chords.
private struct SongLyricEditor: UIViewRepresentable {
    @Binding var text: String
    var chords: [SongChord]
    @Binding var editing: Bool
    @Binding var closeWhenKeyboardEnds: Bool
    var onTextChange: (String) -> Void

    func makeUIView(context: Context) -> SongLyricTextView {
        let view = SongLyricTextView(frame: .zero, textContainer: nil)
        view.delegate = context.coordinator
        let lyricFont = UIFont(name: "TimesNewRomanPSMT", size: 20) ?? .systemFont(ofSize: 20)
        view.font = lyricFont
        view.textColor = .black
        view.backgroundColor = .white
        view.tintColor = .black
        view.typingAttributes = [
            .font: lyricFont,
            .foregroundColor: UIColor.black,
        ]
        view.text = text
        view.trackedText = text
        view.autocorrectionType = .no
        view.autocapitalizationType = .none
        view.spellCheckingType = .no
        view.smartQuotesType = .no
        view.smartDashesType = .no
        view.smartInsertDeleteType = .no
        view.textContainer.lineFragmentPadding = 0
        view.textContainer.lineBreakMode = .byClipping
        view.textContainer.widthTracksTextView = false
        view.textContainerInset = UIEdgeInsets(top: 16, left: 16, bottom: 16, right: 16)
        view.isScrollEnabled = true
        view.alwaysBounceVertical = true
        // The screen already shrinks this field when the keyboard is up.
        // The text view must not add a second keyboard inset on top of that.
        view.contentInsetAdjustmentBehavior = .never
        view.setContentHuggingPriority(.defaultLow, for: .horizontal)
        view.setContentHuggingPriority(.defaultLow, for: .vertical)
        view.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        view.setContentCompressionResistancePriority(.defaultLow, for: .vertical)
        view.fitToLongestLine()
        view.displayChords = chords
        view.refreshChordLayout()
        return view
    }

    func updateUIView(_ view: SongLyricTextView, context: Context) {
        context.coordinator.editing = $editing
        context.coordinator.closeWhenKeyboardEnds = $closeWhenKeyboardEnds
        context.coordinator.onTextChange = onTextChange
        view.displayChords = chords
        // Setting the text while it is being typed jumps the caret.
        if !view.isFirstResponder && view.text != text {
            view.text = text
            view.trackedText = text
            view.fitToLongestLine()
        }
        view.refreshChordLayout()
        context.coordinator.closeIfNeeded(view)
    }

    func sizeThatFits(_ proposal: ProposedViewSize, uiView: SongLyricTextView, context: Context) -> CGSize? {
        guard let width = proposal.width, let height = proposal.height else {
            return nil
        }
        return CGSize(width: width, height: height)
    }

    func makeCoordinator() -> Coordinator {
        Coordinator(
            editing: $editing,
            closeWhenKeyboardEnds: $closeWhenKeyboardEnds,
            onTextChange: onTextChange)
    }

    final class Coordinator: NSObject, UITextViewDelegate {
        var editing: Binding<Bool>
        var closeWhenKeyboardEnds: Binding<Bool>
        var onTextChange: (String) -> Void

        init(
            editing: Binding<Bool>,
            closeWhenKeyboardEnds: Binding<Bool>,
            onTextChange: @escaping (String) -> Void
        ) {
            self.editing = editing
            self.closeWhenKeyboardEnds = closeWhenKeyboardEnds
            self.onTextChange = onTextChange
        }

        func textViewDidChange(_ textView: UITextView) {
            guard let view = textView as? SongLyricTextView, !view.isApplyingChordGaps else {
                return
            }
            let newText = view.text ?? ""
            // Move the chords before the next draw, then tell the page.
            view.noteTextChange(newText)
            onTextChange(newText)
            view.fitToLongestLine()
        }

        private var didRequestClose = false
        private var didScheduleFinish = false

        /// Save and Discard set the binding. The field stays on screen until
        /// the keyboard has finished hiding.
        func closeIfNeeded(_ view: UITextView) {
            guard closeWhenKeyboardEnds.wrappedValue, !didRequestClose else {
                return
            }
            didRequestClose = true
            DispatchQueue.main.async { [weak self, weak view] in
                guard let self else {
                    return
                }
                guard let view else {
                    self.finishClose()
                    return
                }
                // The field stays on screen until the keyboard has finished hiding.
                let field: UIView? = view.isFirstResponder ? view : nil
                KeyboardActivity.shared.whenKeyboardIsDown(field) { [weak self] in
                    self?.finishClose()
                }
            }
        }

        private func finishClose() {
            guard !didScheduleFinish else {
                return
            }
            didScheduleFinish = true
            DispatchQueue.main.async { [weak self] in
                guard let self else {
                    return
                }
                self.closeWhenKeyboardEnds.wrappedValue = false
                self.editing.wrappedValue = false
            }
        }
    }
}

/// A second resign, after the field has already given up the keyboard,
/// asks UIKit to hide a keyboard that is already hidden.
func resignOnce(
    _ responder: UIResponder,
    isResigning: inout Bool,
    callSuper: () -> Bool
) -> Bool {
    guard responder.isFirstResponder, !isResigning else {
        return true
    }
    isResigning = true
    defer { isResigning = false }
    return callSuper()
}

/// Remembers when the software keyboard is on its way out.
/// Removing a field, or leaving the page, during that hide asks UIKit to
/// hide a keyboard that is already hidden.
private final class KeyboardActivity {
    static let shared = KeyboardActivity()

    private(set) var isHiding = false
    private var hideDuration = 0.25
    private var waiters: [() -> Void] = []
    private var fallback: DispatchWorkItem?

    private init() {
        let center = NotificationCenter.default
        center.addObserver(
            forName: UIResponder.keyboardWillHideNotification,
            object: nil,
            queue: .main
        ) { [weak self] note in
            guard let self else {
                return
            }
            self.isHiding = true
            let duration = note.userInfo?[UIResponder.keyboardAnimationDurationUserInfoKey] as? Double ?? 0.25
            self.hideDuration = duration
        }
        center.addObserver(
            forName: UIResponder.keyboardDidHideNotification,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            self?.finishHide()
        }
    }

    /// Resigns the field when it is still typing, then calls back once the
    /// keyboard is down. If the keyboard is already down, calls back now.
    /// A hide that is already running does not need another resign. That
    /// second resign is the warning about an invisible placement.
    func whenKeyboardIsDown(_ field: UIView?, then done: @escaping () -> Void) {
        if let field, field.isFirstResponder, !isHiding {
            // FIXME: Save still logs
            // "+[UIInputViewSetPlacementInvisible placementWithPlacement:]: Should not be called with an invisible placement".
            // This resign is what asks UIKit to hide the keyboard. The field
            // stays on screen until that hide finishes, and the log still happens here.
            _ = field.resignFirstResponder()
        }
        if isHiding {
            afterHide(done)
        } else {
            done()
        }
    }

    /// Calls back once the current hide has finished. If the keyboard is
    /// already down, calls back on the next turn.
    func afterHide(_ done: @escaping () -> Void) {
        guard isHiding else {
            DispatchQueue.main.async(execute: done)
            return
        }
        waiters.append(done)
        fallback?.cancel()
        let work = DispatchWorkItem { [weak self] in
            self?.finishHide()
        }
        fallback = work
        // didHide is the normal signal. If it never arrives, Back would stay
        // on the song, so leave once the animation should be over.
        DispatchQueue.main.asyncAfter(deadline: .now() + hideDuration + 0.35, execute: work)
    }

    private func finishHide() {
        guard isHiding || !waiters.isEmpty else {
            return
        }
        isHiding = false
        fallback?.cancel()
        fallback = nil
        let pending = waiters
        waiters.removeAll()
        // The keyboard is still inside its own notification. Changing the
        // page on the next turn keeps that hide from running a second time.
        DispatchQueue.main.async {
            pending.forEach { $0() }
        }
    }
}

/// Chords drawn over the letters. This view stays out of the touch, so a
/// press on a letter only edits the text.
/// Mirror: paintChordLayer, and determineClickedLetter in softchord_session.py.
private final class SongChordOverlay: UIView {
    weak var editor: SongLyricTextView?

    override init(frame: CGRect) {
        super.init(frame: frame)
        isUserInteractionEnabled = false
        backgroundColor = .clear
        isOpaque = false
    }

    required init?(coder: NSCoder) {
        nil
    }

    override func draw(_ rect: CGRect) {
        editor?.drawChordLayer(clip: rect)
    }
}

private final class SongLyricTextView: UITextView {
    private let chordOverlay = SongChordOverlay()
    private let chordFont = UIFont(name: "TimesNewRomanPS-BoldMT", size: 12) ?? .boldSystemFont(ofSize: 12)
    private let symbolFont = UIFont(name: "AppleSymbols", size: 12)
        ?? UIFont(name: "ArialUnicodeMS", size: 12)
        ?? .boldSystemFont(ofSize: 12)
    private let chordColor = UIColor(red: 0, green: 0, blue: 1, alpha: 1)
    /// Text in a chord position that is not a chord.
    private let unrecognizedChordColor = UIColor(red: 1, green: 0, blue: 0, alpha: 1)

    /// Shown chords. The page replaces this list, so a drag has to change
    /// the page's characterNum for the move to stick.
    var displayChords: [SongChord] = []
    var trackedText = ""
    fileprivate var isApplyingChordGaps = false

    private let pagePadding: CGFloat = 16
    private var measuredText: String?
    private var longestLine: CGFloat = 0
    private var containerWidth: CGFloat = -1
    /// Letters and width from the last full layout. A scroll does not change them.
    private var preparedText: String?
    private var preparedWidth: CGFloat = -1
    private var gapSignature: [Bool] = []
    private var chordAnchors: [(characterNum: Int, text: String, unrecognized: Bool)] = []
    /// Painted bounds in caret coordinates. A drag starts inside one of these.
    private var drawnChords: [DrawnChord] = []
    private var drawnRevision = ""
    private var isLayingOutChords = false

    private struct DrawnChord: Equatable {
        var text: String
        var unrecognized: Bool
        var box: SongChordBoxes.Box
    }

    /// Same gap the sheet leaves above a line that has chords.
    /// Mirror: getHeightsWithChords and the chord_gap in softchord_layout.py.
    private struct ChordMetrics {
        var gap: CGFloat
        var lineHeight: CGFloat
        var chordsHeight: CGFloat
    }

    override init(frame: CGRect, textContainer: NSTextContainer?) {
        super.init(frame: frame, textContainer: textContainer)
        chordOverlay.editor = self
        chordOverlay.clipsToBounds = true
        addSubview(chordOverlay)
    }

    required init?(coder: NSCoder) {
        nil
    }

    override var intrinsicContentSize: CGSize {
        CGSize(width: UIView.noIntrinsicMetric, height: UIView.noIntrinsicMetric)
    }

    private var isResigning = false

    override func resignFirstResponder() -> Bool {
        resignOnce(self, isResigning: &isResigning) {
            super.resignFirstResponder()
        }
    }

    override func layoutSubviews() {
        super.layoutSubviews()
        // Measuring a caret lays the text out, and that layout calls back here.
        // One pass measures every chord. A nested pass would lay the song out
        // again for each chord, which is the pause on the first edit.
        guard !isLayingOutChords else {
            return
        }
        isLayingOutChords = true
        defer { isLayingOutChords = false }
        fitToLongestLine()
        prepareTextLayout()
        // Carets are measured from the top of the song. The overlay uses that
        // same space, so the chords scroll with the letters. Boxes are rebuilt
        // here, after the carets have moved.
        let boxesChanged = updateDrawnChords()
        let size = CGSize(
            width: max(contentSize.width, bounds.width),
            height: max(contentSize.height, bounds.height))
        let next = CGRect(origin: .zero, size: size)
        if chordOverlay.frame != next {
            chordOverlay.frame = next
            chordOverlay.setNeedsDisplay()
        } else if boxesChanged {
            chordOverlay.setNeedsDisplay()
        }
        if subviews.last !== chordOverlay {
            bringSubviewToFront(chordOverlay)
        }
    }

    func noteTextChange(_ newText: String) {
        displayChords = SongLyricChords.moved(displayChords, from: trackedText, to: newText)
        trackedText = newText
        refreshChordLayout()
    }

    private func chordMetrics() -> ChordMetrics {
        let lyrics = font ?? .systemFont(ofSize: 20)
        let lyricsHeight = lyrics.ascender - lyrics.descender
        let chordsHeight = chordFont.ascender - chordFont.descender
        let lineHeight = lyricsHeight + chordFont.ascender - lyrics.leading - chordFont.leading
        return ChordMetrics(
            gap: (lineHeight - lyricsHeight) * 1.03,
            lineHeight: lineHeight,
            chordsHeight: chordsHeight)
    }

    /// Leaves room above a line that has chords, then remembers where each chord sits.
    func refreshChordLayout() {
        let source = text ?? ""
        let lines = SongText.sheet(text: source, chords: displayChords)
        var placed: [(characterNum: Int, text: String, unrecognized: Bool)] = []
        var gaps: [Bool] = []
        var scalar = 0
        for line in lines {
            gaps.append(!line.chords.isEmpty)
            for chord in line.chords {
                placed.append((
                    characterNum: scalar + chord.anchor, text: chord.text, unrecognized: chord.unrecognized))
            }
            scalar += line.lyric.unicodeScalars.count + 1
        }
        chordAnchors = placed
        drawnRevision = ""
        if gaps != gapSignature {
            gapSignature = gaps
            applyChordGaps(gaps)
        }
        setNeedsLayout()
        chordOverlay.setNeedsDisplay()
    }

    /// Lays the song out once, so each later caret read is a lookup.
    /// The width is the one fitToLongestLine just chose. A scroll, or a
    /// keyboard that only shortens the page, leaves the letters and the
    /// width alone, so this can skip the work.
    private func prepareTextLayout() {
        guard bounds.width > 0, let manager = textLayoutManager else {
            return
        }
        let current = text ?? ""
        guard current != preparedText || abs(containerWidth - preparedWidth) > 0.5 else {
            return
        }
        preparedText = current
        preparedWidth = containerWidth
        manager.ensureLayout(for: manager.documentRange)
    }

    /// Rebuilds the grab boxes from the carets. Returns whether they changed.
    private func updateDrawnChords() -> Bool {
        let revision = drawnRevisionKey()
        if revision == drawnRevision {
            return false
        }
        let source = text ?? ""
        let metrics = chordMetrics()
        var built: [DrawnChord] = []
        var complete = true
        for anchor in chordAnchors {
            guard let rect = chordRect(characterNum: anchor.characterNum, text: anchor.text, in: source, metrics: metrics) else {
                complete = false
                continue
            }
            built.append(DrawnChord(
                text: anchor.text,
                unrecognized: anchor.unrecognized,
                box: SongChordBoxes.Box(characterNum: anchor.characterNum, rect: rect)))
        }
        let changed = built != drawnChords
        drawnChords = built
        if complete {
            drawnRevision = revision
        }
        return changed
    }

    private func drawnRevisionKey() -> String {
        var key = "\(containerWidth)|\(contentSize.width)|\(contentSize.height)|\(textContainerInset.top)|\(text ?? "")"
        for anchor in chordAnchors {
            key.append("|\(anchor.characterNum):\(anchor.text):\(anchor.unrecognized)")
        }
        return key
    }

    /// Mirror: QtDocumentLayout.character_and_chord_boxes. The box hangs from
    /// the bottom of the letter's caret and is centered on that letter.
    private func chordRect(
        characterNum: Int, text: String, in source: String, metrics: ChordMetrics
    ) -> CGRect? {
        guard let utf16 = utf16Index(scalarIndex: characterNum, in: source),
              let start = position(from: beginningOfDocument, offset: utf16),
              let endIndex = utf16Index(scalarIndex: characterNum + 1, in: source),
              let end = position(from: beginningOfDocument, offset: endIndex) else {
            return nil
        }
        let startCaret = caretRect(for: start)
        let endCaret = caretRect(for: end)
        guard startCaret.isNull == false, startCaret.isInfinite == false else {
            return nil
        }
        let sameLine = endCaret.isNull == false
            && endCaret.isInfinite == false
            && abs(endCaret.minY - startCaret.minY) < 1
        let midX = sameLine ? (startCaret.minX + endCaret.minX) / 2 : startCaret.midX
        let width = chordLetterWidths(text).reduce(CGFloat(0)) { $0 + $1.width }
        let top = startCaret.maxY - metrics.lineHeight
        return CGRect(x: midX - (width / 2), y: top, width: width, height: metrics.chordsHeight)
    }

    func drawChordLayer(clip: CGRect) {
        let metrics = chordMetrics()
        for drawn in drawnChords {
            let rect = drawn.box.rect
            if rect.maxY < clip.minY || rect.minY > clip.maxY {
                continue
            }
            let normalBaseline = rect.maxY - (0.2 * metrics.chordsHeight)
            let raisedBaseline = normalBaseline - (metrics.chordsHeight / 10)
            drawChord(
                drawn.text, midX: rect.midX, baseline: normalBaseline, raisedBaseline: raisedBaseline,
                color: drawn.unrecognized ? unrecognizedChordColor : chordColor)
        }
    }

    private func chordLetterWidths(_ text: String) -> [(letter: Unicode.Scalar, font: UIFont, width: CGFloat)] {
        var widths: [(letter: Unicode.Scalar, font: UIFont, width: CGFloat)] = []
        for letter in text.unicodeScalars {
            let font = isAccidental(letter) ? symbolFont : chordFont
            let width = (String(letter) as NSString).size(withAttributes: [.font: font]).width
            widths.append((letter, font, width))
        }
        return widths
    }

    private func drawChord(
        _ text: String, midX: CGFloat, baseline: CGFloat, raisedBaseline: CGFloat, color: UIColor
    ) {
        let widths = chordLetterWidths(text)
        let width = widths.reduce(CGFloat(0)) { $0 + $1.width }
        var x = midX - (width / 2)
        for (letter, font, letterWidth) in widths {
            let usedBaseline = isAccidental(letter) ? raisedBaseline : baseline
            // draw(at:) takes the top of the letters. The baseline sits
            // one ascender below that.
            let y = usedBaseline - font.ascender
            (String(letter) as NSString).draw(
                at: CGPoint(x: x, y: y),
                withAttributes: [
                    .font: font,
                    .foregroundColor: color,
                ])
            x += letterWidth
        }
    }

    private func isAccidental(_ letter: Unicode.Scalar) -> Bool {
        letter == "♯" || letter == "♭"
    }

    private func utf16Index(scalarIndex: Int, in text: String) -> Int? {
        var scalars = 0
        var units = 0
        for scalar in text.unicodeScalars {
            if scalars == scalarIndex {
                return units
            }
            scalars += 1
            units += scalar.utf16.count
        }
        if scalars == scalarIndex {
            return units
        }
        return nil
    }

    /// The gap is not an edit. Undo should still remove letters, not this spacing.
    /// Mirror: ChordGapDocumentLayout. A top margin on the first line is ignored,
    /// so that line's room is the top inset. Later chord lines use paragraph spacing.
    private func applyChordGaps(_ gaps: [Bool]) {
        let metrics = chordMetrics()
        let storage = textStorage
        let selected = selectedRange
        let offset = contentOffset
        isApplyingChordGaps = true
        undoManager?.disableUndoRegistration()
        let top = pagePadding + metrics.gap
        if abs(textContainerInset.top - top) > 0.5 {
            textContainerInset = UIEdgeInsets(
                top: top, left: pagePadding, bottom: pagePadding, right: pagePadding)
        }
        storage.beginEditing()
        let ns = storage.string as NSString
        var line = 0
        var index = 0
        while index < ns.length {
            let range = ns.paragraphRange(for: NSRange(location: index, length: 0))
            if range.length == 0 {
                break
            }
            let style = NSMutableParagraphStyle()
            style.lineBreakMode = .byClipping
            if line > 0, line < gaps.count, gaps[line] {
                style.paragraphSpacingBefore = metrics.gap
            }
            storage.addAttribute(.paragraphStyle, value: style, range: range)
            index = range.location + range.length
            line += 1
        }
        storage.endEditing()
        undoManager?.enableUndoRegistration()
        selectedRange = selected
        contentOffset = offset
        isApplyingChordGaps = false
    }

    /// Keep the field wide enough for the longest line, so a line does not wrap.
    /// The width is remembered. Changing it on every layout pass fights the keyboard.
    func fitToLongestLine() {
        let current = text ?? ""
        if measuredText != current {
            measuredText = current
            let font = self.font ?? .systemFont(ofSize: 20)
            var longest: CGFloat = 0
            for line in current.components(separatedBy: "\n") {
                let width = (line as NSString).size(withAttributes: [.font: font]).width
                longest = max(longest, width)
            }
            longestLine = longest
        }
        guard bounds.width > 0 else {
            return
        }
        let inset = textContainerInset.left + textContainerInset.right + textContainer.lineFragmentPadding * 2
        let visible = max(bounds.width - inset, 1)
        let width = max(visible, ceil(longestLine) + 1)
        guard abs(width - containerWidth) > 0.5 else {
            return
        }
        containerWidth = width
        textContainer.size = CGSize(width: width, height: .greatestFiniteMagnitude)
    }
}

/// What the chord buttons can act on: nothing picked, a letter with no chord, or a chord.
enum SongChordSelectionState: Equatable {
    case none
    case letter
    case chord
}

/// One request to type a chord. A letter with no chord starts as a new chord.
private struct SongChordEditRequest: Identifiable {
    var characterNum: Int
    var initialText: String
    var isNew: Bool
    var id: Int { characterNum }
}

/// A small sheet with one text field. The text must be a valid chord
/// (SoftchordChords.isValidChordText, the test transposing relies on). While it
/// is not, the field is red and OK and Return do nothing. Cancel always works.
/// Mirror: ChordDialog in softchord_session.py.
private struct SongChordTextSheet: View {
    var request: SongChordEditRequest
    var onSave: (String) -> Void
    @Environment(\.dismiss) private var dismiss
    @State private var text: String
    @FocusState private var focused: Bool

    private var entry: SongLyricChords.ChordEntry {
        SongLyricChords.ChordEntry(text: text)
    }

    init(request: SongChordEditRequest, onSave: @escaping (String) -> Void) {
        self.request = request
        self.onSave = onSave
        _text = State(initialValue: request.initialText)
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Chord", text: $text)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .focused($focused)
                        .onSubmit(save)
                        .accessibilityIdentifier("Chord text")
                        .listRowBackground(entry.showsRed ? Color.red.opacity(0.35) : nil)
                } footer: {
                    Text(entry.footer)
                }
            }
            .navigationTitle(request.isNew ? "Add chord" : "Edit chord")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("OK", action: save)
                        .disabled(!entry.canSave)
                }
            }
        }
        .presentationDetents([.height(260)])
        .onAppear {
            focused = true
        }
    }

    private func save() {
        guard entry.canSave else {
            return
        }
        onSave(text)
        dismiss()
    }
}

private struct SongZoomCanvas: UIViewRepresentable {
    var lines: [SongSheetLine]

    func makeUIView(context: Context) -> SongZoomScrollView {
        let view = SongZoomScrollView()
        view.setLines(lines)
        return view
    }

    func updateUIView(_ view: SongZoomScrollView, context: Context) {
        view.setLines(lines)
    }

    func sizeThatFits(_ proposal: ProposedViewSize, uiView: SongZoomScrollView, context: Context) -> CGSize? {
        guard let width = proposal.width, let height = proposal.height else {
            return nil
        }
        return CGSize(width: width, height: height)
    }
}

/// Scrolls the sheet from the top-left and zooms with a two-finger pinch.
private class SongZoomScrollView: UIScrollView, UIScrollViewDelegate, UIGestureRecognizerDelegate {
    private let sheet = SongSheetUIView()
    private var loadedLines: [SongSheetLine] = []
    private var songSize: CGSize = .zero
    private(set) var zoom: CGFloat = 1
    private var baseZoom: CGFloat = 1
    private var lockToOrigin = true
    private var isLockingOrigin = false
    private var isPositioningSheet = false

    private let minimumSheetZoom: CGFloat = 0.25
    private let maximumSheetZoom: CGFloat = 4

    override init(frame: CGRect) {
        super.init(frame: frame)
        delegate = self
        backgroundColor = .white
        contentInsetAdjustmentBehavior = .never
        isMultipleTouchEnabled = true
        // The sheet stays on screen and is redrawn at the pinch scale. Scaling
        // its layer instead leaves a gray line on the right edge at zoom
        // levels where that edge falls between pixels.
        sheet.backgroundColor = .white
        sheet.isOpaque = true
        sheet.clipsToBounds = true
        sheet.isUserInteractionEnabled = false
        addSubview(sheet)

        let pinch = UIPinchGestureRecognizer(target: self, action: #selector(onPinch(_:)))
        pinch.delegate = self
        addGestureRecognizer(pinch)
    }

    required init?(coder: NSCoder) {
        nil
    }

    override var intrinsicContentSize: CGSize {
        CGSize(width: UIView.noIntrinsicMetric, height: UIView.noIntrinsicMetric)
    }

    /// Where letters and chords are, in song coordinates.
    var sheetDrawing: SongSheetLayout.Drawing {
        sheet.drawing
    }

    /// The selected letter and chord, drawn behind the sheet (song coordinates).
    func setSelection(_ selection: SongSheetSelection) {
        sheet.selection = selection
    }

    func setLines(_ lines: [SongSheetLine]) {
        guard lines != loadedLines else {
            return
        }
        // Replacing chords while the song is open keeps the pinch zoom in place.
        let hadSong = !loadedLines.isEmpty
        let keptZoom = zoom
        let keptOffset = contentOffset
        loadedLines = lines
        sheet.lines = lines
        songSize = sheet.songSize
        if hadSong {
            zoom = keptZoom
            lockToOrigin = false
            updateContentSize()
            contentOffset = keptOffset
        } else {
            zoom = 1
            lockToOrigin = true
            updateContentSize()
            setContentOffset(.zero, animated: false)
        }
        positionSheet()
    }

    override func layoutSubviews() {
        super.layoutSubviews()
        guard bounds.width > 0, bounds.height > 0 else {
            return
        }
        if lockToOrigin, !isLockingOrigin, zoom != 1 || contentOffset != .zero {
            isLockingOrigin = true
            zoom = 1
            updateContentSize()
            if contentOffset != .zero {
                setContentOffset(.zero, animated: false)
            }
            isLockingOrigin = false
        }
        positionSheet()
    }

    func scrollViewWillBeginDragging(_ scrollView: UIScrollView) {
        lockToOrigin = false
    }

    func gestureRecognizer(
        _ gestureRecognizer: UIGestureRecognizer,
        shouldRecognizeSimultaneouslyWith otherGestureRecognizer: UIGestureRecognizer
    ) -> Bool {
        gestureRecognizer is UIPinchGestureRecognizer
            || otherGestureRecognizer is UIPinchGestureRecognizer
    }

    @objc private func onPinch(_ gesture: UIPinchGestureRecognizer) {
        if gesture.state == .began {
            lockToOrigin = false
            baseZoom = zoom
        }
        guard gesture.state == .began || gesture.state == .changed else {
            return
        }
        // The sheet is pinned to the visible area, so this point is the
        // finger position on screen. Keep that song point under the fingers.
        let anchor = gesture.location(in: sheet)
        let songX = (contentOffset.x + anchor.x) / zoom
        let songY = (contentOffset.y + anchor.y) / zoom
        zoom = min(max(baseZoom * gesture.scale, minimumSheetZoom), maximumSheetZoom)
        updateContentSize()
        contentOffset = CGPoint(x: songX * zoom - anchor.x, y: songY * zoom - anchor.y)
        positionSheet()
    }

    private func updateContentSize() {
        contentSize = CGSize(width: songSize.width * zoom, height: songSize.height * zoom)
    }

    private func positionSheet() {
        guard !isPositioningSheet, bounds.width > 0, bounds.height > 0 else {
            return
        }
        let origin = contentOffset
        let size = bounds.size
        if sheet.zoom == zoom, sheet.contentOrigin == origin, sheet.frame.origin == origin, sheet.frame.size == size {
            return
        }
        isPositioningSheet = true
        sheet.contentOrigin = origin
        sheet.zoom = zoom
        sheet.frame = CGRect(origin: origin, size: size)
        sheet.setNeedsDisplay()
        isPositioningSheet = false
    }
}

private final class SongSheetUIView: UIView {
    var contentOrigin: CGPoint = .zero
    var zoom: CGFloat = 1

    var lines: [SongSheetLine] = [] {
        didSet {
            drawing = SongSheetLayout.drawing(for: lines)
            setNeedsDisplay()
        }
    }

    var selection = SongSheetSelection.none {
        didSet {
            if selection != oldValue {
                setNeedsDisplay()
            }
        }
    }

    private(set) var drawing = SongSheetLayout.drawing(for: [])

    var songSize: CGSize {
        drawing.size
    }

    override func draw(_ rect: CGRect) {
        SongSheetImage.draw(drawing, zoom: zoom, origin: contentOrigin, clip: bounds, selection: selection)
    }
}

/// The letters, read-only, drawn the way the song view draws them. Pinch zooms and a
/// drag scrolls. A press picks a letter and its chord, and a drag moves the chord.
/// Mirror: the desktop's Edit Chords mode, where lyric_editor_mode is off.
private struct SongChordEditor: UIViewRepresentable {
    var text: String
    var chords: [SongChord]
    @Binding var selection: Int?
    var onChordMoved: (Int, Int) -> Void
    var onEditRequested: (Int) -> Void

    func makeUIView(context: Context) -> SongChordZoomView {
        let view = SongChordZoomView()
        view.accessibilityIdentifier = "Song chords"
        update(view)
        return view
    }

    func updateUIView(_ view: SongChordZoomView, context: Context) {
        update(view)
    }

    func sizeThatFits(_ proposal: ProposedViewSize, uiView: SongChordZoomView, context: Context) -> CGSize? {
        guard let width = proposal.width, let height = proposal.height else {
            return nil
        }
        return CGSize(width: width, height: height)
    }

    private func update(_ view: SongChordZoomView) {
        let binding = $selection
        view.onSelectionChanged = { binding.wrappedValue = $0 }
        view.onChordMoved = onChordMoved
        view.onEditRequested = onEditRequested
        view.chords = chords
        view.text = text
        view.setLines(SongText.sheet(text: text, chords: chords))
        view.applySelection(selection)
    }
}

/// Selects a letter, drags the chord that is already selected, taps it to edit,
/// or clears the selection. A press on empty page is left to the scroll view.
/// A press that turns into a slide is a scroll, so nothing is picked.
private final class SongChordPress: UIGestureRecognizer {
    weak var zoomView: SongChordZoomView?
    private var mode = Mode.idle
    /// Where the finger went down on screen. A scroll moves the view under the
    /// finger, so the slide is measured in the window and not in the view.
    private var origin: CGPoint = .zero
    private var dragged = false
    /// A short slide still counts as a press.
    private let slideDistance: CGFloat = 6

    private enum Mode {
        case idle
        /// A press on the selected chord. A slide moves it. Letting go in place edits it.
        case drag
        /// A press that does its action when the finger lifts without sliding.
        case release(SongChordPick.Action)

        var isIdle: Bool {
            if case .idle = self {
                return true
            }
            return false
        }
    }

    /// The scroll must not start on the selected chord, or it would steal the drag.
    var armedToDrag: Bool {
        if case .drag = mode {
            return true
        }
        return false
    }

    override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent) {
        guard numberOfTouches == 1, let touch = touches.first, let zoomView else {
            // A second finger is a pinch.
            mode = .idle
            state = state == .possible ? .failed : .cancelled
            return
        }
        origin = touch.location(in: nil)
        dragged = false
        switch zoomView.pick(at: touch.location(in: zoomView)) {
        case .drag?:
            mode = .drag
            zoomView.fingerLetter = zoomView.selectedCharacterNum
        case let action?:
            mode = .release(action)
        case nil:
            mode = .idle
            state = .failed
        }
    }

    override func touchesMoved(_ touches: Set<UITouch>, with event: UIEvent) {
        guard !mode.isIdle, numberOfTouches == 1, let touch = touches.first, let zoomView else {
            // A second finger is a pinch.
            mode = .idle
            state = state == .possible ? .failed : .cancelled
            return
        }
        let now = touch.location(in: nil)
        let slide = hypot(now.x - origin.x, now.y - origin.y)
        if case .release = mode {
            if slide >= slideDistance {
                self.mode = .idle
                state = .failed
            }
            return
        }
        if !dragged, slide < slideDistance {
            return
        }
        dragged = true
        // Began and changed have to be separate turns. Setting both here
        // leaves the recognizer in changed without ever starting.
        state = state == .possible ? .began : .changed
        zoomView.moveSelectedChord(at: touch.location(in: zoomView))
    }

    override func touchesEnded(_ touches: Set<UITouch>, with event: UIEvent) {
        switch mode {
        case .release(let action):
            zoomView?.perform(action)
        case .drag where !dragged:
            zoomView?.requestEdit()
        default:
            break
        }
        state = dragged ? .ended : .failed
        mode = .idle
    }

    override func touchesCancelled(_ touches: Set<UITouch>, with event: UIEvent) {
        mode = .idle
        dragged = false
        state = .cancelled
    }

    override func canPrevent(_ prevented: UIGestureRecognizer) -> Bool {
        dragged
    }

    override func reset() {
        super.reset()
        mode = .idle
        dragged = false
    }
}

/// The song view with a chord picker on top. The page owns the chords. The view
/// reports a pick or a move and draws the pick as light blue behind the letter
/// and its chord. Touches are read in the zoomed sheet and converted to the song.
/// Mirror: determineClickedLetter and the chord drag in softchord_session.py.
private final class SongChordZoomView: SongZoomScrollView {
    var onSelectionChanged: (Int?) -> Void = { _ in }
    var onChordMoved: (Int, Int) -> Void = { _, _ in }
    var onEditRequested: (Int) -> Void = { _ in }
    /// The chords as drawn, so a move can tell a drop on the same letter from a real one.
    var chords: [SongChord] = []
    /// The letters, to keep a moved chord on its own line.
    var text = ""
    private(set) var selectedCharacterNum: Int?
    private let press = SongChordPress()

    override init(frame: CGRect) {
        super.init(frame: frame)
        press.zoomView = self
        press.cancelsTouchesInView = false
        press.delaysTouchesBegan = false
        press.delaysTouchesEnded = false
        addGestureRecognizer(press)
    }

    required init?(coder: NSCoder) {
        nil
    }

    override func setLines(_ lines: [SongSheetLine]) {
        super.setLines(lines)
        showSelection()
    }

    override func gestureRecognizerShouldBegin(_ gestureRecognizer: UIGestureRecognizer) -> Bool {
        if gestureRecognizer !== press, gestureRecognizer is UIPanGestureRecognizer, press.armedToDrag {
            return false
        }
        return super.gestureRecognizerShouldBegin(gestureRecognizer)
    }

    /// A point in the scroll view's content is the song drawn at the zoom.
    private func songPoint(_ contentPoint: CGPoint) -> CGPoint {
        CGPoint(x: contentPoint.x / zoom, y: contentPoint.y / zoom)
    }

    func pick(at contentPoint: CGPoint) -> SongChordPick.Action? {
        SongChordPick.action(
            in: sheetDrawing, at: contentPoint, zoom: zoom, selected: selectedCharacterNum)
    }

    func perform(_ action: SongChordPick.Action) {
        switch action {
        case .select(let index):
            selectLetter(index)
        case .clear:
            clearChordSelection()
        case .edit:
            requestEdit()
        case .drag:
            break
        }
    }

    private func selectLetter(_ index: Int) {
        selectedCharacterNum = index
        showSelection()
        onSelectionChanged(index)
    }

    private func clearChordSelection() {
        guard selectedCharacterNum != nil else {
            return
        }
        selectedCharacterNum = nil
        showSelection()
        onSelectionChanged(nil)
    }

    /// The page changed the selection, for example after a delete. No callback.
    func applySelection(_ index: Int?) {
        guard index != selectedCharacterNum else {
            return
        }
        selectedCharacterNum = index
        showSelection()
    }

    func requestEdit() {
        guard let selected = selectedCharacterNum else {
            return
        }
        onEditRequested(selected)
    }

    /// The letter the finger was over at its last move while dragging. A chord that
    /// jumped over a letter with a chord leaves the finger on that letter, and
    /// staying there moves nothing.
    var fingerLetter: Int?

    /// A chord dragged onto a letter that has a chord jumps over it to the next free
    /// letter on the line in the direction of the drag. Mirror: the chord drag in
    /// softchord_session.py.
    func moveSelectedChord(at contentPoint: CGPoint) {
        guard let from = selectedCharacterNum,
              let target = sheetDrawing.nearestLetter(at: songPoint(contentPoint)) else {
            return
        }
        guard let step = SongLyricChords.draggedChord(
            chords, in: text, chordAt: from, finger: fingerLetter ?? from, target: target) else {
            return
        }
        fingerLetter = step.finger
        let to = step.chordAt
        let next = step.chords
        guard to != from else {
            return
        }
        chords = next
        selectedCharacterNum = to
        onChordMoved(from, to)
        showSelection()
        onSelectionChanged(to)
    }

    /// Light blue behind the letter, and behind its chord if it has one.
    private func showSelection() {
        guard let selected = selectedCharacterNum else {
            setSelection(.none)
            return
        }
        let drawing = sheetDrawing
        let letter = drawing.letters.first { $0.characterNum == selected }?.rect
        let chord = drawing.chordBoxes.first { $0.characterNum == selected }?.rect
        setSelection(SongSheetSelection(letter: letter, chord: chord))
    }
}
