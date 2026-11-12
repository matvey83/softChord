//
//  SongToolbar.swift
//  SoftChord
//
//  MIRRORED UI: this is the song toolbar of the web app. The buttons, their
//  order and groups, the icons (Assets.xcassets/Toolbar, exported from
//  softChord_web/index.html by tools/export_toolbar_icons.js), the labels, when
//  each shows or is dimmed, the sizes and the wrapping onto more rows follow
//  softChord_web/index.html (.toolbar), viewer.css (.toolbar, .narrow,
//  .edit-row, the 360 px rule), viewer.js (layoutToolbar, applyZoom, paintSong,
//  refreshChrome) and softchord_chord_mode.js (updateButtons). The desktop
//  editor's toolbar (src/softchord_toolbar.py rowWidth) follows them too (no
//  Back or title). A song is already being edited. Copy, Print, Zoom and Undo
//  stay shown. Transpose is shown on Chords and hidden on Lyrics. Chord Add and
//  Delete are shown only on Chords. Discard and Save are shown only when the
//  draft is dirty. All three wrap by the widest segment (SongToolbarMetrics):
//  when its buttons fit on one row every segment is one row, else the
//  Chords/Lyrics switch and the groups after it start the next row in every
//  segment. Change all three apps together.

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

/// Chords or Lyrics. Existing, pasted and imported songs open on Chords. An
/// empty new song opens on Lyrics (see forOpen).
enum SongEditSegment: String, Equatable {
    case chords
    case lyrics

    /// "new" and an empty text start on Lyrics. Pasted, imported and existing
    /// songs start on Chords, including an existing song whose text is empty.
    static func forOpen(text: String, origin: String? = nil) -> SongEditSegment {
        if origin == "new" && text.isEmpty {
            return .lyrics
        }
        return .chords
    }
}

/// The toolbar buttons, in the web order. The raw value is the web button id
/// and, for icon buttons, the icon name.
enum SongToolbarButton: String {
    case copyText = "copy-text", copyChords = "copy-chords", copyImage = "copy-image", print = "print"
    case transposeDown = "transpose-down", transposeUp = "transpose-up", transposeReset = "transpose-reset"
    case zoomOut = "zoom-out", zoomReset = "zoom-reset", zoomIn = "zoom-in"
    case segmentChords = "segment-chords", segmentLyrics = "segment-lyrics"
    case chordEdit = "chord-edit", chordDelete = "chord-delete", chordUndo = "chord-undo", chordRedo = "chord-redo"
    case discard = "edit-discard", save = "edit-save"
}

/// What the buttons show. MIRRORED UI: the enable and show rules of viewer.js.
struct SongToolbarState: Equatable {
    /// True while the Chords segment is selected.
    var chordMode = true
    /// The draft differs from the last save, or the key does: Discard and Save show.
    var pending = false
    var transposed = false
    var zoom = SongZoom.normal
    var canZoom = true
    var selection = SongChordSelectionState.none
    var canUndo = false
    var canRedo = false

    var segment: SongEditSegment { chordMode ? .chords : .lyrics }

    func label(_ button: SongToolbarButton) -> String {
        switch button {
        case .copyText: "Copy song text"
        case .copyChords: "Copy song text (with chords)"
        case .copyImage: "Copy song as image"
        case .print: "Print / Save as PDF"
        case .transposeDown: "Transpose down"
        case .transposeUp: "Transpose up"
        case .transposeReset: "Reset transpose"
        case .zoomOut: "Zoom out"
        case .zoomReset: "Reset zoom (100%)"
        case .zoomIn: "Zoom in"
        case .segmentChords: "Chords"
        case .segmentLyrics: "Lyrics"
        case .chordEdit: selection == .chord ? "Edit chord" : "Add chord"
        case .chordDelete: "Delete chord"
        case .chordUndo: "Undo"
        case .chordRedo: "Redo"
        case .discard: "Discard"
        case .save: "Save"
        }
    }

    /// MIRRORED UI: the web button title and the desktop CHORDS_HELP / LYRICS_HELP.
    func help(_ button: SongToolbarButton) -> String {
        switch button {
        case .segmentChords:
            "Chords. Select a letter, then use Add chord. Drag a chord to move it. Delete removes it."
        case .segmentLyrics:
            "Lyrics. Edit the lyrics of the song. As text is moved, added, or removed, chords follow their letters. Switch to Chords to change the chords."
        case .save:
            "Keep the changes for now"
        case .discard:
            "Throw the changes away"
        default:
            label(button)
        }
    }

    func isEnabled(_ button: SongToolbarButton) -> Bool {
        switch button {
        case .copyText, .copyChords, .copyImage, .print, .transposeDown, .transposeUp:
            true
        case .segmentChords, .segmentLyrics:
            true
        case .transposeReset: transposed
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
    /// MIRRORED UI: viewer.js setEditingState and refreshChrome.
    var groups: [(name: String, buttons: [SongToolbarButton])] {
        var groups: [(name: String, buttons: [SongToolbarButton])] = [
            ("Copy and print", [.copyText, .copyChords, .copyImage, .print]),
        ]
        if chordMode {
            groups.append(("Transpose", [.transposeDown, .transposeUp, .transposeReset]))
        }
        groups += [
            ("Zoom", [.zoomOut, .zoomReset, .zoomIn]),
            ("Chords and Lyrics", [.segmentChords, .segmentLyrics]),
        ]
        if chordMode {
            groups.append(("Chord", [.chordEdit, .chordDelete]))
        }
        groups.append(("Undo", [.chordUndo, .chordRedo]))
        if pending {
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
    /// Back and the title, then the buttons, the segment and later groups starting a row.
    case editRow
}

/// The widths of the toolbar's button rows, from the sizes SongToolbar draws.
/// MIRRORED UI: viewer.js layoutToolbar, softchord_toolbar.py rowWidth.
struct SongToolbarMetrics {
    /// Back, the title, the segment, Discard and Save scale with the text size (SongToolbar.scale).
    var scale: CGFloat = 1

    /// The title keeps at least this next to the buttons on one row (viewer.js TOOLBAR_TITLE_MIN).
    static let titleMin: CGFloat = 60

    /// Every segment: Chords with Discard and Save (the widest), Lyrics with
    /// Discard and Save, and clean Chords.
    static let modes: [SongToolbarState] = [
        SongToolbarState(chordMode: true, pending: true),
        SongToolbarState(chordMode: false, pending: true),
        SongToolbarState(chordMode: true, pending: false),
    ]

    static func buttonSize(oneRow: Bool, width: CGFloat) -> CGFloat {
        oneRow ? 38 : (width <= 360 ? 30 : 34)
    }

    func textWidth(_ text: String, size: CGFloat, semibold: Bool = false) -> CGFloat {
        let font = UIFont.systemFont(ofSize: size, weight: semibold ? .semibold : .regular)
        return ceil((text as NSString).size(withAttributes: [.font: font]).width)
    }

    var backWidth: CGFloat { textWidth("‹ Back", size: 17 * scale) + 4 }

    /// Horizontal padding inside a Chords/Lyrics segment button (viewer.css .segment-btn).
    func segmentPad(oneRow: Bool, width: CGFloat) -> CGFloat {
        !oneRow && width <= 360 ? 8 : 12
    }

    func segmentWidth(_ state: SongToolbarState, oneRow: Bool, width: CGFloat) -> CGFloat {
        let pad = segmentPad(oneRow: oneRow, width: width)
        let size: CGFloat = 13 * scale
        return textWidth("Chords", size: size, semibold: state.chordMode) + 2 * pad
            + textWidth("Lyrics", size: size, semibold: !state.chordMode) + 2 * pad
    }

    /// The buttons of state's mode on one row.
    func rowWidth(_ state: SongToolbarState, oneRow: Bool, width: CGFloat) -> CGFloat {
        let size = Self.buttonSize(oneRow: oneRow, width: width)
        let spacing: CGFloat = oneRow ? 6 : (width <= 360 ? 8 : 12)
        var x: CGFloat = 0
        for (index, group) in state.groups.enumerated() {
            let finish = group.name == "Finish editing"
            let segment = group.name == "Chords and Lyrics"
            if index > 0 {
                x += spacing
                // The separators show on one row only, before each group but
                // Chord, Undo and Finish.
                if oneRow && group.name != "Chord" && group.name != "Undo" && !finish {
                    x += 1 + spacing
                }
            }
            if finish {
                x += (oneRow ? 4 : 0) + 6 + group.buttons.reduce(0) {
                    $0 + textWidth(state.label($1), size: 15 * scale, semibold: $1 == .save) + 24
                }
            } else if segment {
                x += segmentWidth(state, oneRow: oneRow, width: width)
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
    /// Back, the title, the segment, Discard and Save follow the text size setting, up to a third larger.
    /// (The web uses fixed sizes; the icons stay fixed in both.)
    @ScaledMetric(relativeTo: .body) private var textScale: CGFloat = 1
    private var scale: CGFloat { min(textScale, 1.35) }

    // MIRRORED UI: viewer.js layoutToolbar and viewer.css. The widest segment's
    // buttons decide, so the rows do not change with the segment.
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
                                if index > 0 && group.name != "Chord" && group.name != "Undo"
                                    && group.name != "Finish editing" {
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
                                            ? state.groups.firstIndex { $0.name == "Chords and Lyrics" } : nil) {
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
        HStack(spacing: group.name == "Finish editing" ? 6 : (group.name == "Chords and Lyrics" ? 0 : (wide ? 2 : 0))) {
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
                .help(state.help(button))
        } else if button == .segmentChords || button == .segmentLyrics {
            let selected = button == .segmentChords ? state.chordMode : !state.chordMode
            Button(label) { onButton(button) }
                .buttonStyle(SongToolbarSegmentStyle(
                    selected: selected,
                    side: button == .segmentChords ? .left : .right,
                    scale: scale,
                    height: buttonSize,
                    pad: SongToolbarMetrics(scale: scale).segmentPad(oneRow: wide, width: width)))
                .accessibilityLabel(label)
                .accessibilityAddTraits(selected ? .isSelected : [])
                .help(state.help(button))
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
            .help(state.help(button))
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

/// MIRRORED UI: viewer.css .segment-btn.
private struct SongToolbarSegmentStyle: ButtonStyle {
    enum Side { case left, right }
    var selected: Bool
    var side: Side
    var scale: CGFloat = 1
    var height: CGFloat = 38
    var pad: CGFloat = 12

    func makeBody(configuration: Configuration) -> some View {
        let blue = Color(red: 0, green: 0.478, blue: 1)
        let radii = side == .left
            ? RectangleCornerRadii(topLeading: 8, bottomLeading: 8, bottomTrailing: 0, topTrailing: 0)
            : RectangleCornerRadii(topLeading: 0, bottomLeading: 0, bottomTrailing: 8, topTrailing: 8)
        configuration.label
            .font(.system(size: 13 * scale, weight: selected ? .semibold : .regular))
            .foregroundStyle(selected ? Color.white : Color(red: 0.11, green: 0.11, blue: 0.118))
            .padding(.horizontal, pad)
            .frame(minHeight: height)
            .background(selected ? blue : Color.white, in: UnevenRoundedRectangle(cornerRadii: radii, style: .continuous))
            .overlay(UnevenRoundedRectangle(cornerRadii: radii, style: .continuous)
                .stroke(selected ? blue : Color(red: 0.78, green: 0.78, blue: 0.8), lineWidth: 1))
            .padding(.leading, side == .right && !selected ? -1 : 0)
            .zIndex(selected ? 1 : 0)
            .brightness(configuration.isPressed ? -0.04 : 0)
    }
}

/// Places the groups left to right and starts a new row when the next group
/// does not fit, and at breakBefore (the Chords/Lyrics switch, see SongToolbarRows.editRow).
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
