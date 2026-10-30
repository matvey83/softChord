//
//  SongToolbar.swift
//  softChord Viewer
//
//  MIRRORED UI: this is the song toolbar of the web app. The buttons, their
//  order and groups, the icons (Assets.xcassets/Toolbar, exported from
//  softChord_web/index.html by tools/export_toolbar_icons.js), the labels, when
//  each shows or is dimmed, the sizes and the wrapping onto more rows follow
//  softChord_web/index.html (.toolbar), viewer.css (.toolbar, .narrow,
//  .edit-row, the 360 px rule), viewer.js (layoutToolbar, applyZoom, paintSong,
//  setEditing) and softchord_chord_mode.js (updateButtons). The desktop editor's
//  toolbar (src/softchord_toolbar.py rowWidth) follows them too (no Back or
//  title). All three wrap by the widest mode (SongToolbarMetrics): when its
//  buttons fit on one row every mode is one row, else the edit groups start the
//  next row in every mode. Change all three apps together.

import SwiftUI
import UIKit

/// Zoom steps for the song area, a whole percent (100 = normal).
/// MIRRORED UI: softChord_web/softchord_zoom.js (same range, step, grid and key).
enum SongZoom {
    static let min = 50
    static let max = 300
    static let step = 10
    static let normal = 100
    private static let key = "softchord.zoomPercent"

    static func clamp(_ percent: Int) -> Int {
        Swift.min(max, Swift.max(min, percent))
    }

    /// direction +1 zooms in, -1 out. The result stays on the 10% grid.
    static func stepped(_ percent: Int, _ direction: Int) -> Int {
        let current = clamp(percent)
        let next = direction > 0
            ? (current / step + 1) * step
            : (Int((Double(current) / Double(step)).rounded(.up)) - 1) * step
        return clamp(next)
    }

    static func load() -> Int {
        let saved = UserDefaults.standard.integer(forKey: key)
        return (min...max).contains(saved) ? saved : normal
    }

    static func save(_ percent: Int) {
        UserDefaults.standard.set(clamp(percent), forKey: key)
    }
}

/// The toolbar buttons, in the web order. The raw value is the web button id
/// and the icon name.
enum SongToolbarButton: String {
    case copyText = "copy-text", copyChords = "copy-chords", copyImage = "copy-image", print = "print"
    case transposeDown = "transpose-down", transposeUp = "transpose-up", transposeReset = "transpose-reset"
    case zoomOut = "zoom-out", zoomReset = "zoom-reset", zoomIn = "zoom-in"
    case editText = "edit-text", editChords = "edit-chords"
    case chordEdit = "chord-edit", chordDelete = "chord-delete", chordUndo = "chord-undo", chordRedo = "chord-redo"
    case discard = "edit-discard", save = "edit-save"
}

/// What the buttons show. MIRRORED UI: the enable and show rules of viewer.js.
struct SongToolbarState: Equatable {
    var editing = false
    var chordMode = false
    /// A transpose not saved while viewing: Discard and Save show.
    var pending = false
    var transposed = false
    var zoom = SongZoom.normal
    /// False while the text is typed in: that editor does not zoom yet.
    var canZoom = true
    var selection = SongChordSelectionState.none
    var canUndo = false
    var canRedo = false

    func label(_ button: SongToolbarButton) -> String {
        switch button {
        case .copyText: "Copy song text"
        case .copyChords: "Copy song text (with chords)"
        case .copyImage: "Copy song as image"
        case .transposeDown: "Transpose down"
        case .transposeUp: "Transpose up"
        case .transposeReset: "Reset transpose"
        case .zoomOut: "Zoom out"
        case .zoomReset: "Reset zoom (100%)"
        case .zoomIn: "Zoom in"
        case .print: "Print / Save as PDF"
        case .editText: "Edit Text…"
        case .editChords: "Edit Chords…"
        case .chordEdit: selection == .chord ? "Edit chord" : "Add chord"
        case .chordDelete: "Delete chord"
        case .chordUndo: "Undo"
        case .chordRedo: "Redo"
        case .discard: "Discard"
        case .save: "Save"
        }
    }

    func isEnabled(_ button: SongToolbarButton) -> Bool {
        switch button {
        // Copy and Print, and Transpose, are not shown while editing (see groups).
        case .copyText, .copyChords, .copyImage, .print, .transposeDown, .transposeUp:
            !editing
        // The other edit button switches the open edit to that mode (viewer.js switchEditing).
        case .editText: !(editing && !chordMode)
        case .editChords: !(editing && chordMode)
        case .transposeReset: !editing && transposed
        case .zoomOut: canZoom && zoom > SongZoom.min
        case .zoomReset: canZoom && zoom != SongZoom.normal
        case .zoomIn: canZoom && zoom < SongZoom.max
        case .chordEdit: selection != .none
        case .chordDelete: selection == .chord
        case .chordUndo: canUndo
        case .chordRedo: canRedo
        case .discard, .save: true
        }
    }

    /// The groups shown now, in order, with their names for VoiceOver.
    /// Copy and Print, and Transpose, need the song as saved, so their groups
    /// are hidden while editing (viewer.js setEditingState).
    var groups: [(name: String, buttons: [SongToolbarButton])] {
        var groups: [(name: String, buttons: [SongToolbarButton])] = []
        if !editing {
            // TODO: re-add Add to Photos to the toolbar (SongShareMenu's addSongToPhotos).
            groups.append(("Copy and print", [.copyText, .copyChords, .copyImage, .print]))
            groups.append(("Transpose", [.transposeDown, .transposeUp, .transposeReset]))
        }
        groups += [
            ("Zoom", [.zoomOut, .zoomReset, .zoomIn]),
            ("Edit", [.editText, .editChords]),
        ]
        if editing && chordMode {
            groups.append(("Chord", [.chordEdit, .chordDelete, .chordUndo, .chordRedo]))
        }
        if editing || pending {
            groups.append(("Finish editing", [.discard, .save]))
        }
        return groups
    }
}

/// How the toolbar is laid out (MIRRORED UI: viewer.js layoutToolbar).
enum SongToolbarRows: Equatable {
    /// Back, the title and the buttons on one row (38 pt buttons).
    case oneRow
    /// Back and the title, then the buttons on one row below (34 pt).
    case buttonRow
    /// Back and the title, then the buttons, the edit groups starting a row.
    case editRow
}

/// The widths of the toolbar's button rows, from the sizes SongToolbar draws.
/// MIRRORED UI: viewer.js layoutToolbar, softchord_toolbar.py rowWidth.
struct SongToolbarMetrics {
    /// Back, the title, Discard and Save scale with the text size (SongToolbar.scale).
    var scale: CGFloat = 1

    /// The title keeps at least this next to the buttons on one row (viewer.js TOOLBAR_TITLE_MIN).
    static let titleMin: CGFloat = 60

    /// Every mode: viewing with a transpose not saved (the widest), Edit Text, Edit Chords.
    static let modes: [SongToolbarState] = [
        SongToolbarState(pending: true),
        SongToolbarState(editing: true),
        SongToolbarState(editing: true, chordMode: true),
    ]

    static func buttonSize(oneRow: Bool, width: CGFloat) -> CGFloat {
        oneRow ? 38 : (width <= 360 ? 30 : 34)
    }

    func textWidth(_ text: String, size: CGFloat, semibold: Bool = false) -> CGFloat {
        let font = UIFont.systemFont(ofSize: size, weight: semibold ? .semibold : .regular)
        return ceil((text as NSString).size(withAttributes: [.font: font]).width)
    }

    var backWidth: CGFloat { textWidth("‹ Back", size: 17 * scale) + 4 }

    /// The buttons of state's mode on one row.
    func rowWidth(_ state: SongToolbarState, oneRow: Bool, width: CGFloat) -> CGFloat {
        let size = Self.buttonSize(oneRow: oneRow, width: width)
        let spacing: CGFloat = oneRow ? 6 : (width <= 360 ? 8 : 12)
        var x: CGFloat = 0
        for (index, group) in state.groups.enumerated() {
            let finish = group.name == "Finish editing"
            if index > 0 {
                x += spacing
                // The separators show on one row only, before each group but Chord and Finish.
                if oneRow && group.name != "Chord" && !finish {
                    x += 1 + spacing
                }
            }
            if finish {
                x += (oneRow ? 4 : 0) + 6 + group.buttons.reduce(0) {
                    $0 + textWidth(state.label($1), size: 15 * scale, semibold: $1 == .save) + 24
                }
            } else {
                let count = CGFloat(group.buttons.count)
                x += count * size + (count - 1) * (oneRow ? 2 : 0)
            }
        }
        return x
    }

    /// The widest mode's buttons on one row.
    func widestRow(oneRow: Bool, width: CGFloat) -> CGFloat {
        Self.modes.map { rowWidth($0, oneRow: oneRow, width: width) }.max() ?? 0
    }

    /// The rows for a toolbar this wide.
    func rows(width: CGFloat) -> SongToolbarRows {
        // 12 pt padding each side, 8 pt between Back, the title and the buttons.
        if widestRow(oneRow: true, width: width) <= width - 24 - backWidth - 16 - Self.titleMin {
            return .oneRow
        }
        return widestRow(oneRow: false, width: width) <= width - 16 ? .buttonRow : .editRow
    }
}

#if DEBUG
/// The toolbar last drawn, for unit tests: its SwiftUI buttons are not views they can press.
@MainActor enum SongToolbarTesting {
    static var shown: (state: SongToolbarState?, back: () -> Void, press: (SongToolbarButton) -> Void)?
}
#endif

/// Back, the title and the buttons, pinned above the song.
struct SongToolbar: View {
    var title: String
    /// Nil when the song could not be read: only Back and the title show.
    var state: SongToolbarState?
    var onBack: () -> Void
    var onButton: (SongToolbarButton) -> Void
    @State private var width: CGFloat = 390
    /// Back, the title, Discard and Save follow the text size setting, up to a third larger.
    /// (The web uses fixed sizes; the icons stay fixed in both.)
    @ScaledMetric(relativeTo: .body) private var textScale: CGFloat = 1
    private var scale: CGFloat { min(textScale, 1.35) }

    // MIRRORED UI: viewer.js layoutToolbar and viewer.css. The widest mode's
    // buttons decide, so the rows do not change with the mode.
    private var rows: SongToolbarRows { SongToolbarMetrics(scale: scale).rows(width: width) }
    private var wide: Bool { rows == .oneRow }
    private var buttonSize: CGFloat { SongToolbarMetrics.buttonSize(oneRow: wide, width: width) }

    var body: some View {
        #if DEBUG
        let _ = SongToolbarTesting.shown = (state, onBack, onButton)
        #endif
        Group {
            if wide {
                HStack(spacing: 8) {
                    back
                    heading
                    if let state {
                        HStack(spacing: 6) {
                            ForEach(Array(state.groups.enumerated()), id: \.offset) { index, group in
                                if index > 0 && group.name != "Chord" && group.name != "Finish editing" {
                                    Rectangle().fill(Color(white: 0.82)).frame(width: 1, height: 22)
                                }
                                groupView(group, state: state)
                            }
                        }
                    }
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
            } else {
                VStack(alignment: .leading, spacing: 2) {
                    HStack(spacing: 8) {
                        back
                        heading.padding(.trailing, 44)
                    }
                    if let state {
                        SongToolbarFlow(spacing: width <= 360 ? 8 : 12, rowSpacing: 2,
                                        breakBefore: rows == .editRow
                                            ? state.groups.firstIndex { $0.name == "Edit" } : nil) {
                            ForEach(Array(state.groups.enumerated()), id: \.offset) { _, group in
                                groupView(group, state: state)
                            }
                        }
                    }
                }
                .padding(.horizontal, 8)
                .padding(.vertical, 6)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.white)
        .overlay(alignment: .bottom) {
            Rectangle().fill(Color(red: 0.898, green: 0.898, blue: 0.918)).frame(height: 1)
        }
        .onGeometryChange(for: CGFloat.self) { $0.size.width } action: { width = $0 }
    }

    private var back: some View {
        Button(action: onBack) {
            Text("‹ Back").font(.system(size: 17 * scale)).foregroundStyle(Color(red: 0, green: 0.478, blue: 1))
                .padding(.vertical, 4).padding(.horizontal, 2)
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Back")
    }

    private var heading: some View {
        Text(title)
            .font(.system(size: (wide ? 17 : 16) * scale, weight: .semibold))
            .foregroundStyle(Color(red: 0.11, green: 0.11, blue: 0.118))
            .lineLimit(1)
            .truncationMode(.tail)
            .frame(maxWidth: .infinity)
    }

    private func groupView(_ group: (name: String, buttons: [SongToolbarButton]), state: SongToolbarState) -> some View {
        HStack(spacing: group.name == "Finish editing" ? 6 : (wide ? 2 : 0)) {
            ForEach(group.buttons, id: \.self) { button in
                buttonView(button, state: state)
            }
        }
        // MIRRORED UI: viewer.css #edit-actions margin-left (one row only).
        .padding(.leading, wide && group.name == "Finish editing" ? 4 : 0)
        .accessibilityElement(children: .contain)
        .accessibilityLabel(group.name)
    }

    @ViewBuilder
    private func buttonView(_ button: SongToolbarButton, state: SongToolbarState) -> some View {
        let label = state.label(button)
        if button == .discard || button == .save {
            let save = button == .save
            Button(label) { onButton(button) }
                .buttonStyle(SongToolbarTextStyle(prominent: save, scale: scale))
                .help(save ? "Keep the changes for now" : "Throw the changes away")
        } else {
            Button { onButton(button) } label: {
                Image(button.rawValue)
                    .resizable()
                    .frame(width: 22, height: 22)
                    .frame(width: buttonSize, height: buttonSize)
            }
            .buttonStyle(SongToolbarIconStyle())
            .disabled(!state.isEnabled(button))
            .accessibilityLabel(label)
            .help(label)
        }
    }
}

/// MIRRORED UI: viewer.css .tool (#1c1c1e, pressed #e5e5ea, dimmed to 35%).
private struct SongToolbarIconStyle: ButtonStyle {
    @Environment(\.isEnabled) private var isEnabled

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .foregroundStyle(Color(red: 0.11, green: 0.11, blue: 0.118))
            .background(configuration.isPressed ? Color(red: 0.898, green: 0.898, blue: 0.918) : .clear,
                        in: RoundedRectangle(cornerRadius: 8))
            .contentShape(Rectangle())
            .opacity(isEnabled ? 1 : 0.35)
    }
}

/// MIRRORED UI: viewer.css .tool-text and #edit-save.
private struct SongToolbarTextStyle: ButtonStyle {
    var prominent: Bool
    var scale: CGFloat = 1

    func makeBody(configuration: Configuration) -> some View {
        let blue = Color(red: 0, green: 0.478, blue: 1)
        configuration.label
            .font(.system(size: 15 * scale, weight: prominent ? .semibold : .regular))
            .foregroundStyle(prominent ? Color.white : Color(red: 0.11, green: 0.11, blue: 0.118))
            .padding(.horizontal, 12)
            .frame(minHeight: 34)
            .background(prominent ? blue : Color.white, in: RoundedRectangle(cornerRadius: 8))
            .overlay(RoundedRectangle(cornerRadius: 8).stroke(prominent ? blue : Color(white: 0.82), lineWidth: 1))
            .brightness(configuration.isPressed ? -0.04 : 0)
    }
}

/// Places the groups left to right and starts a new row when the next group
/// does not fit, and at breakBefore (the Edit group, see SongToolbarRows.editRow).
/// MIRRORED UI: viewer.css .toolbar-actions flex-wrap and .tool-break (narrow).
private struct SongToolbarFlow: Layout {
    var spacing: CGFloat
    var rowSpacing: CGFloat
    var breakBefore: Int? = nil

    private func frames(_ width: CGFloat, _ subviews: Subviews) -> (frames: [CGRect], size: CGSize) {
        var frames: [CGRect] = []
        var x: CGFloat = 0, y: CGFloat = 0, rowHeight: CGFloat = 0, used: CGFloat = 0
        for (index, view) in subviews.enumerated() {
            let size = view.sizeThatFits(.unspecified)
            if x > 0 && (x + size.width > width || index == breakBefore) {
                x = 0
                y += rowHeight + rowSpacing
                rowHeight = 0
            }
            frames.append(CGRect(origin: CGPoint(x: x, y: y), size: size))
            x += size.width + spacing
            used = max(used, x - spacing)
            rowHeight = max(rowHeight, size.height)
        }
        return (frames, CGSize(width: used, height: y + rowHeight))
    }

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        frames(proposal.width ?? .infinity, subviews).size
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let placed = frames(bounds.width, subviews).frames
        for (view, frame) in zip(subviews, placed) {
            view.place(at: CGPoint(x: bounds.minX + frame.minX, y: bounds.minY + frame.minY),
                       proposal: ProposedViewSize(frame.size))
        }
    }
}
