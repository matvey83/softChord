//
//  SongPage.swift
//  softChord Viewer
//

import SwiftUI
import UIKit

struct SongPage: View {
    @Environment(\.dismiss) private var dismiss
    @State private var steps = 0
    @State private var noticeTitle: String?
    @State private var noticeMessage: String?
    @State private var editing = false
    @State private var closeWhenKeyboardEnds = false
    @State private var draft = ""
    /// Chord positions for the edit in progress. Note ids stay as stored.
    @State private var editChords: [SongChord] = []
    /// Lyrics drawn after Save. Nil means the songbook text.
    @State private var shownText: String?
    /// Chord positions drawn after Save. Nil means the songbook chords.
    @State private var shownChords: [SongChord]?

    let title: String
    private let songId: Int
    private let source: SongSource?
    private let errorMessage: String?

    init(song: SongTitle) {
        // Start listening before a tap can hide the keyboard. Save then knows
        // a hide is already running and does not start another one.
        _ = KeyboardActivity.shared
        title = song.title
        songId = song.id
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
        guard let source else {
            return []
        }
        let chords = SongTranspose.shifted(shownChords ?? source.chords, by: steps)
        return SongText.sheet(text: lyricText, chords: chords)
    }

    private var textWasEdited: Bool {
        guard let source else {
            return false
        }
        let currentText = editing ? draft : lyricText
        let currentChords = editing ? editChords : (shownChords ?? source.chords)
        return currentText != source.text || currentChords != source.chords
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
            } else {
                SongZoomCanvas(lines: lines)
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
                    .background(Color.white)
            }
        }
        .navigationBarTitleDisplayMode(.inline)
        .toolbar(.visible, for: .navigationBar)
        .navigationBarBackButtonHidden(true)
        .toolbar {
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
                        .frame(width: 100, height: 1)
                        .accessibilityHidden(true)
                }
                .sharedBackgroundVisibility(.hidden)
            }
        }
        .background {
            if source != nil {
                SongChromeDock(
                    editing: editing,
                    songId: songId,
                    steps: $steps,
                    onEdit: beginLyricEdit,
                    onDiscard: { closeLyricEditor(save: false) },
                    onSave: { closeLyricEditor(save: true) },
                    onNotice: { title, message in
                        noticeTitle = title
                        noticeMessage = message
                    }
                )
            }
        }
        .alert(noticeTitle ?? "", isPresented: noticeIsPresented) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(noticeMessage ?? "")
        }
        .safeAreaInset(edge: .bottom, spacing: 0) {
            if steps != 0 || textWasEdited {
                Text("Changes do not persist")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 8)
                    .background(Color.white)
            }
        }
    }

    private func beginLyricEdit() {
        draft = lyricText
        editChords = shownChords ?? source?.chords ?? []
        editing = true
    }

    private func lyricDraftChanged(_ newText: String) {
        editChords = SongLyricChords.moved(editChords, from: draft, to: newText)
        draft = newText
    }

    /// The field resigns before it leaves the screen. Removing it while the
    /// keyboard is still hiding asks UIKit to hide an input view that is
    /// already hidden.
    private func closeLyricEditor(save: Bool) {
        if save {
            let sameText = draft == source?.text
            let sameChords = editChords == source?.chords
            shownText = sameText ? nil : draft
            shownChords = sameChords ? nil : editChords
        }
        closeWhenKeyboardEnds = true
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
    var songId: Int
    @Binding var steps: Int
    var onEdit: () -> Void
    var onDiscard: () -> Void
    var onSave: () -> Void
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
        coordinator.editing = editing
        coordinator.onEdit = onEdit
        coordinator.onDiscard = onDiscard
        coordinator.onSave = onSave
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
        var editing = false
        var onEdit: () -> Void = {}
        private weak var anchor: SongChromeAnchor?
        var onDiscard: () -> Void = {}
        var onSave: () -> Void = {}
        var onNotice: (String, String) -> Void = { _, _ in }
        private var viewControls: UIView?
        private var editControls: UIView?

        func install(on anchor: SongChromeAnchor) {
            // The bar's container covers the screen and takes presses that land
            // on the buttons. They stay in the bar's own view, above that
            // container. The bar's controller presents the menu.
            self.anchor = anchor
            guard anchor.window != nil, anchor.panel == nil,
                  let bar = anchor.navigationBar(),
                  let parent = anchor.barOwner(for: bar) else {
                return
            }
            let panel = makePanel()
            panel.translatesAutoresizingMaskIntoConstraints = false
            parent.view.addSubview(panel)
            NSLayoutConstraint.activate([
                panel.topAnchor.constraint(equalTo: bar.safeAreaLayoutGuide.topAnchor),
                panel.trailingAnchor.constraint(equalTo: bar.layoutMarginsGuide.trailingAnchor),
            ])
            anchor.panel = panel
            anchor.installFrontObserver()
            anchor.moveHostAboveTheBar()
            applyEditing()
        }

        func applyEditing() {
            viewControls?.isHidden = editing
            editControls?.isHidden = !editing
        }

        private func makePanel() -> UIStackView {
            let menuButton = UIButton(configuration: menuConfiguration())
            menuButton.showsMenuAsPrimaryAction = true
            menuButton.menu = SongShareMenu.menu(
                songId: { [weak self] in self?.songId ?? 0 },
                report: { [weak self] title, message in
                    self?.onNotice(title, message)
                },
                onEdit: { [weak self] in
                    self?.onEdit()
                })
            menuButton.accessibilityLabel = "Menu"

            // Mirror: softchord_session.py transposeDown and transposeUp.
            let row = UIStackView(arrangedSubviews: [
                arrowButton("arrow.down", name: "Down", delta: -1),
                arrowButton("arrow.up", name: "Up", delta: 1),
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

            let trailing = UIStackView(arrangedSubviews: [stack, edits])
            trailing.axis = .vertical
            trailing.alignment = .trailing
            trailing.setContentHuggingPriority(.required, for: .horizontal)

            let panel = SongChromePanel(arrangedSubviews: [trailing])
            panel.axis = .horizontal
            panel.alignment = .top
            return panel
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

        private func textButton(_ title: String, prominent: Bool, action: Selector) -> UIButton {
            var config = prominent ? UIButton.Configuration.filled() : .bordered()
            config.title = title
            config.buttonSize = .small
            config.cornerStyle = .capsule
            let button = UIButton(configuration: config)
            button.addTarget(self, action: action, for: .touchUpInside)
            return button
        }

        @objc private func transposeTapped(_ sender: UIButton) {
            steps.wrappedValue += sender.tag
        }

        @objc private func discardTapped() {
            onDiscard()
        }

        @objc private func saveTapped() {
            onSave()
        }
    }
}

/// The gap between the buttons is not a button. Presses there belong to the song.
private final class SongChromePanel: UIStackView {
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

/// Chords drawn over the letters. Taps pass through to the text field.
/// A drag will be a gesture on the text view, and only when the press is
/// inside a chord box. This view stays out of the touch, so a press on a
/// letter still edits the text.
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
    private var chordAnchors: [(characterNum: Int, text: String)] = []
    /// Painted bounds in caret coordinates. A drag starts inside one of these.
    private var drawnChords: [DrawnChord] = []
    private var drawnRevision = ""
    private var isLayingOutChords = false

    private struct DrawnChord: Equatable {
        var text: String
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
        var placed: [(characterNum: Int, text: String)] = []
        var gaps: [Bool] = []
        var scalar = 0
        for line in lines {
            gaps.append(!line.chords.isEmpty)
            for chord in line.chords {
                placed.append((characterNum: scalar + chord.anchor, text: chord.text))
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
            key.append("|\(anchor.characterNum):\(anchor.text)")
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
                drawn.text, midX: rect.midX, baseline: normalBaseline, raisedBaseline: raisedBaseline)
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
        _ text: String, midX: CGFloat, baseline: CGFloat, raisedBaseline: CGFloat
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
                    .foregroundColor: chordColor,
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
private final class SongZoomScrollView: UIScrollView, UIScrollViewDelegate, UIGestureRecognizerDelegate {
    private let sheet = SongSheetUIView()
    private var loadedLines: [SongSheetLine] = []
    private var songSize: CGSize = .zero
    private var zoom: CGFloat = 1
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

    private var drawing = SongSheetLayout.drawing(for: [])

    var songSize: CGSize {
        drawing.size
    }

    override func draw(_ rect: CGRect) {
        SongSheetImage.draw(drawing, zoom: zoom, origin: contentOrigin, clip: bounds)
    }
}
