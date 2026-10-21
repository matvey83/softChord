//
//  SongPage.swift
//  softChord Viewer
//

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
                SongZoomCanvas(lines: lines)
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
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
        loadedLines = lines
        sheet.lines = lines
        songSize = sheet.songSize
        zoom = 1
        lockToOrigin = true
        updateContentSize()
        setContentOffset(.zero, animated: false)
        positionSheet()
    }

    override func layoutSubviews() {
        super.layoutSubviews()
        guard bounds.width > 0, bounds.height > 0 else {
            return
        }
        if lockToOrigin, !isLockingOrigin {
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
        isPositioningSheet = true
        sheet.contentOrigin = contentOffset
        sheet.zoom = zoom
        sheet.frame = CGRect(origin: contentOffset, size: bounds.size)
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
