//
//  SongPage.swift
//  softChord Viewer
//

import CoreText
import SwiftUI
import UIKit

struct SongPage: View {
    @Environment(\.dismiss) private var dismiss

    let title: String
    private let lines: [SongSheetLine]
    private let errorMessage: String?

    init(song: SongTitle) {
        title = song.title
        do {
            lines = try Songbook.sheet(id: song.id)
            errorMessage = nil
        } catch {
            lines = []
            errorMessage = String(describing: error)
        }
    }

    var body: some View {
        Group {
            if let errorMessage {
                Text(errorMessage)
                    .foregroundStyle(.red)
                    .padding()
            } else {
                ScrollView([.horizontal, .vertical]) {
                    SongSheetCanvas(lines: lines)
                }
                .background(Color.white)
            }
        }
        .navigationTitle(title)
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
        }
    }
}

private struct SongSheetCanvas: UIViewRepresentable {
    var lines: [SongSheetLine]

    func makeUIView(context: Context) -> SongSheetUIView {
        let view = SongSheetUIView()
        view.backgroundColor = .white
        view.isOpaque = true
        view.setContentHuggingPriority(.required, for: .horizontal)
        view.setContentHuggingPriority(.required, for: .vertical)
        view.setContentCompressionResistancePriority(.required, for: .horizontal)
        view.setContentCompressionResistancePriority(.required, for: .vertical)
        view.lines = lines
        return view
    }

    func updateUIView(_ view: SongSheetUIView, context: Context) {
        view.lines = lines
    }

    func sizeThatFits(_ proposal: ProposedViewSize, uiView: SongSheetUIView, context: Context) -> CGSize? {
        uiView.intrinsicContentSize
    }
}

private final class SongSheetUIView: UIView {
    var lines: [SongSheetLine] = [] {
        didSet {
            drawing = SongSheetLayout.drawing(for: lines)
            invalidateIntrinsicContentSize()
            setNeedsDisplay()
        }
    }

    private var drawing = SongSheetLayout.drawing(for: [])

    override var intrinsicContentSize: CGSize {
        drawing.size
    }

    override func draw(_ rect: CGRect) {
        for glyph in drawing.glyphs {
            let font = UIFont(descriptor: CTFontCopyFontDescriptor(glyph.font) as UIFontDescriptor, size: CTFontGetSize(glyph.font))
            let top = glyph.baseline - font.ascender
            (glyph.text as NSString).draw(
                at: CGPoint(x: glyph.x, y: top),
                withAttributes: [
                    .font: font,
                    .foregroundColor: UIColor(cgColor: glyph.color),
                ])
        }
    }
}
