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
        clip: CGRect
    ) {
        UIColor.white.setFill()
        UIRectFill(clip)
        for glyph in drawing.glyphs {
            let font = UIFont(
                descriptor: CTFontCopyFontDescriptor(glyph.font) as UIFontDescriptor,
                size: CTFontGetSize(glyph.font) * zoom)
            let x = glyph.x * zoom - origin.x
            let top = glyph.baseline * zoom - font.ascender - origin.y
            if top > clip.maxY || top + font.lineHeight < clip.minY || x > clip.maxX {
                continue
            }
            (glyph.text as NSString).draw(
                at: CGPoint(x: x, y: top),
                withAttributes: [
                    .font: font,
                    .foregroundColor: UIColor(cgColor: glyph.color),
                ])
        }
    }
}
