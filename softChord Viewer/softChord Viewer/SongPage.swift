//
//  SongPage.swift
//  softChord Viewer
//

import SwiftUI
import UIKit

/// Letters, chords and the transpose kept after Save, for this run of the app.
/// The songbook file is not changed. Quit the app and the copy is gone.
enum SongSessionEdits {
    struct Copy: Equatable {
        var text: String?
        var chords: [SongChord]?
        /// The transpose kept with Save. The chords above are stored untransposed.
        var steps = 0
    }

    private static var copies: [Int: Copy] = [:]

    static func copy(for id: Int) -> Copy? {
        copies[id]
    }

    static func save(id: Int, text: String?, chords: [SongChord]?, steps: Int = 0) {
        if text == nil, chords == nil, steps == 0 {
            copies[id] = nil
        } else {
            copies[id] = Copy(text: text, chords: chords, steps: steps)
        }
    }

    static func reset() {
        copies = [:]
    }

    /// The song as it opens: the songbook's, with the copy saved for this run
    /// in its place, at the transpose saved with it.
    static func shownSource(id: Int) throws -> SongSource {
        var song = try Songbook.source(id: id)
        if let copy = copies[id] {
            song.text = copy.text ?? song.text
            song.chords = SongTranspose.shifted(copy.chords ?? song.chords, by: copy.steps)
        }
        return song
    }
}

struct SongPage: View {
    @Environment(\.dismiss) private var dismiss
    /// The transpose shown. A song opens at the transpose kept with Save.
    @State private var steps = 0
    /// The transpose kept with Save. Steps that differ from it (by more than whole
    /// octaves, see changesChords) are a change: Save and Discard show.
    @State private var savedSteps = 0
    @State private var noticeTitle: String?
    @State private var noticeMessage: String?
    @State private var editing = false
    /// Chord editing is the other edit mode. Only one of the two is on at a time.
    @State private var editingChords = false
    /// The letter picked in chord editing. Its chord, if it has one, is the selected chord.
    @State private var chordSelection: Int?
    @State private var chordRequest: SongChordEditRequest?
    /// MIRRORED UI: the zoom of viewer.js. The zoom chosen with the buttons, kept
    /// for every song; the zoom that fits the widest line on screen (nil when the
    /// chosen zoom fits); set once the buttons or a pinch zoomed this song, which
    /// then shows at exactly that zoom.
    @State private var zoomPercent = SongZoom.load()
    @State private var fitPercent: Int?
    @State private var songZoomed = false
    /// The zoom left by a pinch, which is not kept for other songs.
    @State private var pinchPercent: Int?
    @State private var closeWhenKeyboardEnds = false
    /// Set once the keyboard has finished hiding, so Back can pop from the page.
    @State private var popWhenReady = false
    @State private var askingToLeave = false
    /// Edit Chords was pressed while the text is edited: open it once the keyboard is down.
    @State private var switchingToChords = false
    @State private var toast: String?
    @State private var toastTask: Task<Void, Never>?
    @State private var draft = ""
    /// Chord positions for the edit in progress. Note ids stay as stored.
    @State private var editChords: [SongChord] = []
    /// Undo and Redo in chord editing: the text and chords before each change (a
    /// chord moved right of its line gives the line spaces). A drag is one change.
    /// Dropped on Save and Discard. Mirror: the desktop edit's undo.
    @State private var chordUndo: [SongChordEditState] = []
    @State private var chordRedo: [SongChordEditState] = []
    /// Set when the first move of a drag has been put on the undo list.
    @State private var dragRecorded = false
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
        _steps = State(initialValue: kept?.steps ?? 0)
        _savedSteps = State(initialValue: kept?.steps ?? 0)
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

    /// True when the song is shown in another key than the one kept with Save.
    private var stepsChanged: Bool {
        guard let source else {
            return false
        }
        return SongTranspose.changesChords(steps - savedSteps, in: shownChords ?? source.chords)
    }

    /// An edit or a transpose that Back would lose. MIRRORED UI: viewer.js draftChanged.
    private var hasUnsavedChanges: Bool {
        guard let source else {
            return false
        }
        let storedText = shownText ?? source.text
        let storedChords = shownChords ?? source.chords
        return stepsChanged
            || ((editing || editingChords) && (draft != storedText || editChords != storedChords))
    }

    /// MIRRORED UI: viewer.js persistNote. Shown while editing, and while the
    /// song shows a saved edit or another key than the songbook's.
    private var bannerText: String? {
        guard let source else {
            return nil
        }
        let kept = shownText != nil || shownChords != nil
        let transposed = SongTranspose.changesChords(steps, in: shownChords ?? source.chords)
        return editing || editingChords || kept || transposed ? "Changes do not persist" : nil
    }

    /// MIRRORED UI: viewer.js showToast (#toast): a short note at the bottom.
    private func showToast(_ message: String) {
        toast = message
        toastTask?.cancel()
        toastTask = Task { @MainActor in
            try? await Task.sleep(for: .seconds(2.2))
            if !Task.isCancelled {
                toast = nil
            }
        }
    }

    /// The zoom the song is shown at. A wide song opens smaller so it fits.
    private var shownZoom: Int {
        if let pinchPercent {
            return pinchPercent
        }
        return songZoomed || fitPercent == nil ? zoomPercent : min(zoomPercent, fitPercent!)
    }

    /// The sheet reports the zoom that fits its widest line. Only a smaller one is
    /// used, and not while editing (viewer.js fitToWidth).
    private func fitChanged(_ fit: Int) {
        guard !editing, !editingChords else {
            return
        }
        let next = fit < zoomPercent ? max(SongZoom.min, fit) : nil
        if next != fitPercent {
            fitPercent = next
        }
    }

    private func zoomTo(_ percent: Int) {
        songZoomed = true
        pinchPercent = nil
        zoomPercent = SongZoom.clamp(percent)
        SongZoom.save(zoomPercent)
        showToast("Zoom \(zoomPercent)%")
    }

    private func pinched(_ scale: CGFloat) {
        songZoomed = true
        pinchPercent = SongZoom.clamp(Int((scale * 100).rounded()))
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
                SongChordEditor(
                    text: draft,
                    chords: SongTranspose.shifted(editChords, by: steps),
                    selection: $chordSelection,
                    zoom: CGFloat(shownZoom) / 100,
                    onPinched: pinched,
                    onFit: fitChanged,
                    onChordMoved: moveChord,
                    onDragBegan: { dragRecorded = false },
                    onEditRequested: requestChordEdit
                )
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
                    .background(Color.white)
            } else {
                SongZoomCanvas(lines: lines, zoom: CGFloat(shownZoom) / 100, onPinched: pinched, onFit: fitChanged)
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
                    .background(Color.white)
            }
        }
        .overlay(alignment: .bottom) {
            if let toast {
                Text(toast)
                    .font(.system(size: 14))
                    .foregroundStyle(.white)
                    .multilineTextAlignment(.center)
                    .padding(.vertical, 10)
                    .padding(.horizontal, 16)
                    .background(Color(red: 0.11, green: 0.11, blue: 0.118).opacity(0.92),
                                in: RoundedRectangle(cornerRadius: 10))
                    .padding(.bottom, 24)
                    .padding(.horizontal, 16)
                    .allowsHitTesting(false)
            }
        }
        .sheet(item: $chordRequest) { request in
            SongChordTextSheet(request: request) { text in
                applyChordText(text, for: request)
            }
        }
        // MIRRORED UI: the web song toolbar (SongToolbar.swift), pinned above the song.
        .toolbar(.hidden, for: .navigationBar)
        .navigationBarBackButtonHidden(true)
        .safeAreaInset(edge: .top, spacing: 0) {
            // TODO: Under the title, show the subtitle when it is not empty,
            // and the auto-detected key in the editor's words
            // ("Auto-detected key: ..."). Port key_label and
            // format_auto_detected_key_text from softchord_chords.py.
            SongToolbar(title: title, state: source == nil ? nil : toolbarState,
                        onBack: backTapped, onButton: toolbarTapped)
                // MIRRORED UI: the desktop's Save / Don't Save / Cancel sheet
                // (softchord_session.py _leaveEditMessageBox) and viewer.js leave-confirm.
                .alert("Do you want to save the changes you made to \u{201C}\(title)\u{201D}?",
                       isPresented: $askingToLeave) {
                    Button("Save") { finishAndLeave(save: true) }
                    Button("Don\u{2019}t Save", role: .destructive) { finishAndLeave(save: false) }
                    Button("Cancel", role: .cancel) {}
                } message: {
                    Text("Your changes will be lost if you don\u{2019}t save them.")
                }
        }
        .onChange(of: editing) { _, now in
            if !now {
                textEditorClosed()
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

    private var toolbarState: SongToolbarState {
        SongToolbarState(
            editing: editing || editingChords,
            chordMode: editingChords,
            pending: stepsChanged,
            transposed: SongTranspose.changesChords(steps, in: shownChords ?? source?.chords ?? []),
            zoom: shownZoom,
            canZoom: !editing,
            selection: chordSelectionState,
            canUndo: !chordUndo.isEmpty,
            canRedo: !chordRedo.isEmpty)
    }

    private func toolbarTapped(_ button: SongToolbarButton) {
        let report: (String, String) -> Void = { title, message in
            noticeTitle = title
            noticeMessage = message
        }
        let song: () throws -> SongSource = {
            guard let shownSong else {
                throw CocoaError(.fileReadUnknown)
            }
            return shownSong
        }
        switch button {
        case .copyText: songShareCopy(song, includeChords: false, report: report)
        case .copyChords: songShareCopy(song, includeChords: true, report: report)
        case .copyImage: copySongImage(song, report: report)
        case .transposeDown: steps -= 1
        case .transposeUp: steps += 1
        case .transposeReset: steps = 0
        case .zoomOut: zoomTo(SongZoom.stepped(shownZoom, -1))
        case .zoomIn: zoomTo(SongZoom.stepped(shownZoom, 1))
        case .zoomReset: zoomTo(SongZoom.normal)
        case .print: SongPrint.present(lines, title: title)
        case .editText: editingChords ? switchEditing(toChords: false) : beginLyricEdit()
        case .editChords: editing ? switchEditing(toChords: true) : beginChordEdit()
        case .chordEdit: requestChordEdit(chordSelection)
        case .chordDelete: deleteSelectedChord()
        case .chordUndo: undoChordChange()
        case .chordRedo: redoChordChange()
        case .discard: finish(save: false)
        case .save:
            let changed = hasUnsavedChanges
            finish(save: true)
            if changed {
                showToast("Saved")
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
        chordUndo = []
        chordRedo = []
        editingChords = true
    }

    /// MIRRORED UI: viewer.js switchEditing and the desktop's startEdit. Edit Text
    /// while editing chords, or Edit Chords while editing the text: the draft (text
    /// and chords) goes on in the other mode without asking, and one Save or
    /// Discard keeps or drops all of it. Chord undo starts over.
    private func switchEditing(toChords: Bool) {
        if toChords {
            // The text field leaves once the keyboard is down (see editing's onChange).
            switchingToChords = true
            closeWhenKeyboardEnds = true
        } else {
            chordRequest = nil
            chordSelection = nil
            chordUndo = []
            chordRedo = []
            editingChords = false
            editing = true
        }
    }

    private func textEditorClosed() {
        guard switchingToChords else {
            return
        }
        switchingToChords = false
        chordSelection = nil
        chordRequest = nil
        chordUndo = []
        chordRedo = []
        editingChords = true
    }

    private var chordEditState: SongChordEditState {
        SongChordEditState(text: draft, chords: editChords)
    }

    /// Puts the text and chords as they are now on the undo list, before a change.
    private func setChords(_ chords: [SongChord], text: String? = nil) {
        let next = SongChordEditState(text: text ?? draft, chords: chords)
        guard next != chordEditState else {
            return
        }
        chordUndo.append(chordEditState)
        chordRedo = []
        draft = next.text
        editChords = next.chords
    }

    /// One step of a drag. `to` is a letter of the text with room right of the
    /// line that holds `roomAt` (SongLyricChords.withRoom), and the lines the
    /// chord left and went to lose the spaces no chord needs.
    /// MIRRORED: softchord_chord_mode.js dragTo, softchord_session.py placeChord.
    private func moveChord(from: Int, to: Int, roomAt: Int?) {
        let moved = SongLyricChords.movedWithRoom(editChords, in: draft, from: from, to: to, roomAt: roomAt)
        // Every step of one drag is the same change.
        if dragRecorded {
            draft = moved.text
            editChords = moved.chords
        } else {
            dragRecorded = true
            setChords(moved.chords, text: moved.text)
        }
    }

    private func undoChordChange() {
        guard editingChords, let previous = chordUndo.popLast() else {
            return
        }
        chordRedo.append(chordEditState)
        draft = previous.text
        editChords = previous.chords
        chordSelection = nil
    }

    private func redoChordChange() {
        guard editingChords, let next = chordRedo.popLast() else {
            return
        }
        chordUndo.append(chordEditState)
        draft = next.text
        editChords = next.chords
        chordSelection = nil
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
        setChords(SongLyricChords.replaced(
            editChords, at: request.characterNum, withText: text, steps: steps))
    }

    private func deleteSelectedChord() {
        guard editingChords, let selected = chordSelection else {
            return
        }
        // The spaces only this chord needed at the end of its line go too.
        let tidy = SongLyricChords.tidied(
            SongLyricChords.deleted(editChords, at: selected), in: draft, touched: [selected])
        setChords(tidy.chords, text: tidy.text)
        chordSelection = tidy.moved(selected)
    }

    /// Save and Discard: the edit, with a transpose made before it, or while
    /// viewing only the transpose.
    private func finish(save: Bool) {
        switchingToChords = false
        if editing || editingChords {
            finishEditing(save: save)
        } else {
            finishTranspose(save: save)
        }
    }

    /// Save keeps the key for this run, like a saved edit. Discard goes back
    /// to the key that was kept.
    private func finishTranspose(save: Bool) {
        if save {
            savedSteps = steps
            SongSessionEdits.save(id: songId, text: shownText, chords: shownChords, steps: savedSteps)
        } else {
            steps = savedSteps
        }
    }

    private func finishEditing(save: Bool) {
        // A transpose made before the edit is part of it.
        if save {
            savedSteps = steps
        } else {
            steps = savedSteps
        }
        if editingChords {
            if save {
                commitEdit()
            }
            // No keyboard is up in this mode, so the page can leave it now.
            chordRequest = nil
            chordSelection = nil
            chordUndo = []
            chordRedo = []
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
        SongSessionEdits.save(id: songId, text: shownText, chords: shownChords, steps: savedSteps)
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

    private func backTapped() {
        if hasUnsavedChanges {
            askingToLeave = true
        } else {
            leaveSong()
        }
    }

    private func finishAndLeave(save: Bool) {
        finish(save: save)
        leaveSong()
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
    var zoom: CGFloat
    var onPinched: (CGFloat) -> Void
    var onFit: (Int) -> Void

    func makeUIView(context: Context) -> SongZoomScrollView {
        let view = SongZoomScrollView()
        updateUIView(view, context: context)
        return view
    }

    func updateUIView(_ view: SongZoomScrollView, context: Context) {
        view.onPinched = onPinched
        view.onFit = onFit
        view.setRequestedZoom(zoom)
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

    // MIRRORED UI: softchord_zoom.js MIN and MAX.
    private let minimumSheetZoom = CGFloat(SongZoom.min) / 100
    private let maximumSheetZoom = CGFloat(SongZoom.max) / 100
    /// The zoom the page asks for (buttons, fit). A pinch reports where it ended.
    private var requestedZoom: CGFloat = 1
    var onPinched: (CGFloat) -> Void = { _ in }
    /// The whole percent at which the widest line fits the width.
    var onFit: (Int) -> Void = { _ in }
    private var reportedFit: Int?

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

    /// Keeps the top-left song point in place.
    func setRequestedZoom(_ scale: CGFloat) {
        guard abs(scale - requestedZoom) > 0.001 else {
            return
        }
        requestedZoom = scale
        guard abs(scale - zoom) > 0.006 else {
            return
        }
        let songX = contentOffset.x / zoom
        let songY = contentOffset.y / zoom
        zoom = scale
        updateContentSize()
        let maxX = max(0, contentSize.width - bounds.width)
        let maxY = max(0, contentSize.height - bounds.height)
        contentOffset = CGPoint(x: min(songX * zoom, maxX), y: min(songY * zoom, maxY))
        positionSheet()
    }

    private func reportFit() {
        guard bounds.width > 0, songSize.width > 0 else {
            return
        }
        let fit = Int(((bounds.width - 1) / songSize.width * 100).rounded(.down))
        guard fit != reportedFit else {
            return
        }
        reportedFit = fit
        let report = onFit
        DispatchQueue.main.async { report(fit) }
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
            zoom = requestedZoom
            lockToOrigin = true
            updateContentSize()
            setContentOffset(.zero, animated: false)
        }
        positionSheet()
        reportFit()
    }

    override func layoutSubviews() {
        super.layoutSubviews()
        guard bounds.width > 0, bounds.height > 0 else {
            return
        }
        if lockToOrigin, !isLockingOrigin, zoom != requestedZoom || contentOffset != .zero {
            isLockingOrigin = true
            zoom = requestedZoom
            updateContentSize()
            if contentOffset != .zero {
                setContentOffset(.zero, animated: false)
            }
            isLockingOrigin = false
        }
        positionSheet()
        reportFit()
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
        if gesture.state == .ended {
            requestedZoom = zoom
            onPinched(zoom)
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
/// The text and the chords of Edit chords, one step of its Undo.
struct SongChordEditState: Equatable {
    var text: String
    var chords: [SongChord]
}

private struct SongChordEditor: UIViewRepresentable {
    var text: String
    var chords: [SongChord]
    @Binding var selection: Int?
    var zoom: CGFloat
    var onPinched: (CGFloat) -> Void
    var onFit: (Int) -> Void
    var onChordMoved: (Int, Int, Int?) -> Void
    var onDragBegan: () -> Void
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
        view.onDragBegan = onDragBegan
        view.onEditRequested = onEditRequested
        view.onPinched = onPinched
        view.onFit = onFit
        view.setRequestedZoom(zoom)
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
            zoomView.onDragBegan()
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
    var onChordMoved: (Int, Int, Int?) -> Void = { _, _, _ in }
    /// A press on the selected chord, before it moves. The moves of one drag are one undo step.
    var onDragBegan: () -> Void = {}
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
    /// Right of the last letter of a line the line gets spaces for the chord, up to
    /// SongLyricChords.room, and loses those the chord leaves again.
    /// MIRRORED: softchord_chord_mode.js dragTo, softchord_session.py
    /// dragChordPastLineEnd.
    func moveSelectedChord(at contentPoint: CGPoint) {
        let point = songPoint(contentPoint)
        guard let from = selectedCharacterNum else {
            return
        }
        var room = SongLyricChords.ChordRoom(text: text, chords: chords, at: text.unicodeScalars.count, count: 0)
        var roomAt: Int?
        var target: Int
        if let letter = sheetDrawing.nearestLetter(at: point) {
            target = letter
        } else if let end = lineEnd(rightOf: point) {
            room = SongLyricChords.withRoom(chords, in: text, at: end.characterNum)
            guard let range = SongLyricChords.letterRange(in: room.text, at: end.characterNum) else {
                return
            }
            let steps = Int(ceil((point.x - end.rect.maxX) / max(end.rect.width, 1)))
            target = min(range.upperBound, end.characterNum + max(1, steps))
            roomAt = end.characterNum
        } else {
            return
        }
        guard let step = SongLyricChords.draggedChord(
            room.chords, in: room.text, chordAt: room.shifted(from),
            finger: room.shifted(fingerLetter ?? from), target: target) else {
            return
        }
        guard step.chordAt != room.shifted(from) else {
            fingerLetter = roomAt == nil ? step.finger : fingerLetter
            return
        }
        let moved = SongLyricChords.movedWithRoom(chords, in: text, from: from, to: step.chordAt, roomAt: roomAt)
        let to = moved.moved(step.chordAt)
        fingerLetter = moved.moved(step.finger)
        chords = moved.chords
        if moved.text != text {
            text = moved.text
            setLines(SongText.sheet(text: text, chords: chords))
        }
        selectedCharacterNum = to
        onChordMoved(from, step.chordAt, roomAt)
        showSelection()
        onSelectionChanged(to)
    }

    /// The last letter of the line nearest the point, when the point is right of it.
    private func lineEnd(rightOf point: CGPoint) -> (characterNum: Int, rect: CGRect)? {
        let letters = sheetDrawing.letters
        func gap(_ letter: SongSheetLayout.Letter) -> CGFloat {
            max(letter.reach.minY - point.y, point.y - letter.reach.maxY, 0)
        }
        guard let nearest = letters.map(gap).min() else {
            return nil
        }
        guard let last = letters.filter({ gap($0) - nearest < 0.01 }).max(by: { $0.rect.maxX < $1.rect.maxX }),
              point.x >= last.rect.maxX,
              SongLyricChords.letterRange(in: text, at: last.characterNum)?.upperBound == last.characterNum else {
            return nil
        }
        return (last.characterNum, last.rect)
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
