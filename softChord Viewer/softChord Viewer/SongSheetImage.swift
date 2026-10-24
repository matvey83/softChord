//
//  SongSheetImage.swift
//  softChord Viewer
//

import CoreText
import UIKit

/// Draws a chord sheet and can copy that drawing into an image.
enum SongSheetImage {
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
        highlights: [CGRect] = []
    ) {
        UIColor.white.setFill()
        UIRectFill(clip)
        // Behind the letters. The rectangles are in song coordinates.
        UIColor(red: 0.68, green: 0.85, blue: 1, alpha: 1).setFill()
        for rect in highlights {
            UIRectFill(CGRect(
                x: rect.minX * zoom - origin.x,
                y: rect.minY * zoom - origin.y,
                width: rect.width * zoom,
                height: rect.height * zoom))
        }
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
