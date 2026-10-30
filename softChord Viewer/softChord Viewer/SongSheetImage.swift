//
//  SongSheetImage.swift
//  softChord Viewer
//

import CoreText
import UIKit

/// The letter and chord picked in chord editing. Only the screen draws it: an image
/// (Copy as image, Add to Photos) never has one. The rectangles are in song coordinates.
struct SongSheetSelection: Equatable {
    var letter: CGRect?
    var chord: CGRect?

    static let none = SongSheetSelection()
}

/// Draws a chord sheet and can copy that drawing into an image.
enum SongSheetImage {
    /// Mirror: the selected letter and chord of the web app (viewer.css, #007aff). The
    /// letter gets a light blue box (20%, corners of 3pt). The chord gets a halo: 25%
    /// reaching 2pt past the chord, with a 1pt #007aff line around it and rounded
    /// corners. The 2pt, 1pt and corners are screen points, so they do not grow with
    /// the pinch zoom. Behind the letters and chords.
    static let selectionBlue = UIColor(red: 0, green: 122 / 255, blue: 1, alpha: 1)

    static func drawSelection(_ selection: SongSheetSelection, zoom: CGFloat, origin: CGPoint) {
        func onScreen(_ rect: CGRect) -> CGRect {
            CGRect(
                x: rect.minX * zoom - origin.x,
                y: rect.minY * zoom - origin.y,
                width: rect.width * zoom,
                height: rect.height * zoom)
        }
        if let letter = selection.letter {
            selectionBlue.withAlphaComponent(0.2).setFill()
            UIBezierPath(roundedRect: onScreen(letter), cornerRadius: 3).fill()
        }
        if let chord = selection.chord {
            let halo = onScreen(chord).insetBy(dx: -2, dy: -2)
            selectionBlue.withAlphaComponent(0.25).setFill()
            UIBezierPath(roundedRect: halo, cornerRadius: 4).fill()
            let line = UIBezierPath(roundedRect: halo.insetBy(dx: -0.5, dy: -0.5), cornerRadius: 4.5)
            line.lineWidth = 1
            selectionBlue.setStroke()
            line.stroke()
        }
    }

    static func image(for lines: [SongSheetLine], scale: CGFloat) -> UIImage {
        image(for: SongSheetLayout.drawing(for: lines), scale: scale)
    }

    static func image(for drawing: SongSheetLayout.Drawing, scale: CGFloat) -> UIImage {
        let format = UIGraphicsImageRendererFormat()
        format.scale = scale
        format.opaque = true
        let renderer = UIGraphicsImageRenderer(size: drawing.size, format: format)
        return renderer.image { _ in
            draw(drawing, zoom: 1, origin: .zero, clip: CGRect(origin: .zero, size: drawing.size))
        }
    }

    static func draw(
        _ drawing: SongSheetLayout.Drawing,
        zoom: CGFloat,
        origin: CGPoint,
        clip: CGRect,
        selection: SongSheetSelection = .none
    ) {
        UIColor.white.setFill()
        UIRectFill(clip)
        drawSelection(selection, zoom: zoom, origin: origin)
        // One font per face for this frame. A font per chord letter made scrolling hitch.
        var fonts: [UnsafeRawPointer: UIFont] = [:]
        for glyph in drawing.glyphs {
            let ascent = CTFontGetAscent(glyph.font) * zoom
            let descent = CTFontGetDescent(glyph.font) * zoom
            let x = glyph.x * zoom - origin.x
            let topEstimate = glyph.baseline * zoom - ascent - origin.y
            if topEstimate - 2 > clip.maxY || topEstimate + ascent + descent + 2 < clip.minY || x > clip.maxX {
                continue
            }
            let key = Unmanaged.passUnretained(glyph.font).toOpaque()
            let font: UIFont
            if let cached = fonts[key] {
                font = cached
            } else {
                font = UIFont(
                    descriptor: CTFontCopyFontDescriptor(glyph.font) as UIFontDescriptor,
                    size: CTFontGetSize(glyph.font) * zoom)
                fonts[key] = font
            }
            let top = glyph.baseline * zoom - font.ascender - origin.y
            (glyph.text as NSString).draw(
                at: CGPoint(x: x, y: top),
                withAttributes: [
                    .font: font,
                    .foregroundColor: UIColor(cgColor: glyph.color),
                ])
        }
    }
}

/// Prints the song as it is shown, at its normal size (smaller when a line is
/// wider than the page), starting a new page between song lines.
/// MIRRORED UI: the web toolbar's Print button (viewer.js window.print()).
enum SongPrint {
    static func present(_ lines: [SongSheetLine], title: String) {
        let info = UIPrintInfo.printInfo()
        info.outputType = .general
        info.jobName = title
        let controller = UIPrintInteractionController.shared
        controller.printInfo = info
        controller.printPageRenderer = SongPrintRenderer(drawing: SongSheetLayout.drawing(for: lines))
        controller.present(animated: true)
    }
}

private final class SongPrintRenderer: UIPrintPageRenderer {
    let drawing: SongSheetLayout.Drawing
    /// The song y where each page starts.
    private var starts: [CGFloat] = []

    init(drawing: SongSheetLayout.Drawing) {
        self.drawing = drawing
        super.init()
    }

    private var scale: CGFloat {
        min(1, printableRect.width / max(1, drawing.size.width))
    }

    override var numberOfPages: Int {
        let pageHeight = printableRect.height / scale
        let lineTops = Set(drawing.letters.map { $0.reach.minY }).sorted()
        starts = []
        var start: CGFloat = 0
        while start < drawing.size.height, pageHeight > 0 {
            starts.append(start)
            let limit = start + pageHeight
            if limit >= drawing.size.height {
                break
            }
            start = lineTops.last { $0 > start + 1 && $0 <= limit } ?? limit
        }
        return max(1, starts.count)
    }

    override func drawPage(at pageIndex: Int, in printableRect: CGRect) {
        guard pageIndex < starts.count, let context = UIGraphicsGetCurrentContext() else {
            return
        }
        let start = starts[pageIndex]
        let end = pageIndex + 1 < starts.count ? starts[pageIndex + 1] : drawing.size.height
        let clip = CGRect(x: 0, y: 0, width: drawing.size.width, height: end - start)
        context.saveGState()
        context.translateBy(x: printableRect.minX, y: printableRect.minY)
        context.scaleBy(x: scale, y: scale)
        context.clip(to: clip)
        SongSheetImage.draw(drawing, zoom: 1, origin: CGPoint(x: 0, y: start), clip: clip)
        context.restoreGState()
    }
}
