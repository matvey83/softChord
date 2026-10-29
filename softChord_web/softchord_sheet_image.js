// Lays out a chord sheet as positioned text and paints it, for Copy as image.
// The measurements follow SongSheetLayout.drawing in
// softChord Viewer/softChord Viewer/softchord_layout.swift: padding 16, 20 pt
// lyrics, 12 pt bold chords above the letters, accidentals raised in a symbol
// font. The title is added above the lyrics. The layout takes a measure
// function, so tests can run it without a canvas.

(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    root.SheetImage = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  var PADDING = 16;
  var LYRICS_SIZE = 20;
  var CHORDS_SIZE = 12;
  var TITLE_SIZE = 24;
  var TITLE_GAP = 12;
  var SERIF = "\"Times New Roman\", Times, serif";
  var SYMBOLS = "Arial, \"Arial Unicode MS\", sans-serif";
  var LYRICS_FONT = LYRICS_SIZE + "px " + SERIF;
  var CHORDS_FONT = "bold " + CHORDS_SIZE + "px " + SERIF;
  var SYMBOLS_FONT = "bold " + CHORDS_SIZE + "px " + SYMBOLS;
  var TITLE_FONT = "bold " + TITLE_SIZE + "px " + SERIF;
  var BLACK = "#000";
  var BLUE = "#00f";
  // Text in a chord position that is not a chord.
  var RED = "#f00";
  // Canvas limits: Chrome and Firefox allow 16384 px on a side, and iPhone
  // Safari allows only 16 777 216 px (4096 x 4096) in all. Stay under both with a
  // little room, so a long song is drawn smaller instead of failing.
  var MAX_SIDE = 16384;
  var MAX_AREA = 16000000;

  function isAccidental(ch) {
    return ch === "♯" || ch === "♭";
  }

  // measure(font, text) returns { width, ascent, descent } in CSS pixels.
  function layout(title, lines, measure) {
    var lyrics = measure(LYRICS_FONT, "x");
    var chords = measure(CHORDS_FONT, "x");
    var lyricsHeight = lyrics.ascent + lyrics.descent;
    var chordsHeight = chords.ascent + chords.descent;
    var lineHeight = lyricsHeight + chords.ascent;
    var chordGap = (lineHeight - lyricsHeight) * 1.03;
    var glyphs = [];
    var minX = PADDING;
    var maxX = PADDING;
    var y = PADDING;

    if (title) {
      var heading = measure(TITLE_FONT, title);
      glyphs.push({
        text: title,
        font: TITLE_FONT,
        color: BLACK,
        x: PADDING,
        baseline: y + heading.ascent,
      });
      maxX = Math.max(maxX, PADDING + heading.width);
      y += heading.ascent + heading.descent + TITLE_GAP;
    }

    for (var i = 0; i < lines.length; i++) {
      var line = lines[i];
      if (line.chords.length) {
        y += chordGap;
      }
      var lyricTop = y;
      var charBottom = lyricTop + lyricsHeight;
      var chars = Array.from(line.lyric);
      // Left edge of each letter, with one more entry for the right edge.
      var offsets = [0];
      for (var c = 1; c <= chars.length; c++) {
        offsets.push(measure(LYRICS_FONT, chars.slice(0, c).join("")).width);
      }
      if (line.lyric) {
        glyphs.push({
          text: line.lyric,
          font: LYRICS_FONT,
          color: BLACK,
          x: PADDING,
          baseline: lyricTop + lyrics.ascent,
        });
      }
      maxX = Math.max(maxX, PADDING + offsets[offsets.length - 1]);

      var chordTop = charBottom - lineHeight;
      var chordBottom = chordTop + chordsHeight;
      var normalBaseline = chordBottom - 0.2 * chordsHeight;
      var raisedBaseline = normalBaseline - chordsHeight / 10;
      for (var k = 0; k < line.chords.length; k++) {
        var chord = line.chords[k];
        // A letter of several code points (an accent, an emoji) is one span wide.
        var span = chord.span || 1;
        if (chord.anchor < 0 || chord.anchor + span >= offsets.length) {
          continue;
        }
        var parts = Array.from(chord.text);
        var widths = parts.map(function (ch) {
          return measure(isAccidental(ch) ? SYMBOLS_FONT : CHORDS_FONT, ch).width;
        });
        var total = widths.reduce(function (sum, w) { return sum + w; }, 0);
        var left = PADDING + offsets[chord.anchor];
        var right = PADDING + offsets[chord.anchor + span];
        var x = (left + right) / 2 - total / 2;
        minX = Math.min(minX, x);
        for (var p = 0; p < parts.length; p++) {
          var accidental = isAccidental(parts[p]);
          glyphs.push({
            text: parts[p],
            font: accidental ? SYMBOLS_FONT : CHORDS_FONT,
            color: chord.unrecognized ? RED : BLUE,
            x: x,
            baseline: accidental ? raisedBaseline : normalBaseline,
          });
          x += widths[p];
        }
        maxX = Math.max(maxX, x);
      }
      y = charBottom;
    }

    // A chord hanging off the left edge moves the whole sheet right.
    var shift = Math.max(0, PADDING - minX);
    if (shift > 0) {
      glyphs.forEach(function (glyph) { glyph.x += shift; });
      maxX += shift;
    }
    return { width: maxX + PADDING, height: y + PADDING, glyphs: glyphs };
  }

  // The pixel ratio to draw at: wanted, lowered so the canvas stays allowed.
  // It is never raised above what the limits need, so a very tall song gets a
  // ratio below 1 (a smaller picture) rather than a canvas the browser refuses.
  function scaleFor(drawing, wanted) {
    var scale = Math.max(1, wanted || 1);
    var side = Math.max(drawing.width, drawing.height);
    // One pixel less than the side limit, because pixelSize rounds up.
    scale = Math.min(scale, (MAX_SIDE - 1) / side);
    scale = Math.min(scale, Math.sqrt(MAX_AREA / (drawing.width * drawing.height)));
    return scale;
  }

  function pixelSize(drawing, scale) {
    return {
      width: Math.max(1, Math.ceil(drawing.width * scale)),
      height: Math.max(1, Math.ceil(drawing.height * scale)),
    };
  }

  // Paints a layout on a 2D context already sized to pixelSize.
  function paint(ctx, drawing, scale, pixels) {
    ctx.save();
    ctx.setTransform(scale, 0, 0, scale, 0, 0);
    ctx.fillStyle = "#fff";
    ctx.fillRect(0, 0, pixels.width / scale, pixels.height / scale);
    ctx.textBaseline = "alphabetic";
    ctx.textAlign = "left";
    drawing.glyphs.forEach(function (glyph) {
      ctx.font = glyph.font;
      ctx.fillStyle = glyph.color;
      ctx.fillText(glyph.text, glyph.x, glyph.baseline);
    });
    ctx.restore();
  }

  function fileName(title) {
    var base = String(title || "").replace(/[\\/:*?"<>|\u0000-\u001f]+/g, " ").replace(/\s+/g, " ").trim();
    return (base || "song") + ".png";
  }

  return {
    layout: layout,
    scaleFor: scaleFor,
    pixelSize: pixelSize,
    paint: paint,
    fileName: fileName,
    MAX_SIDE: MAX_SIDE,
    MAX_AREA: MAX_AREA,
    PADDING: PADDING,
    LYRICS_FONT: LYRICS_FONT,
    CHORDS_FONT: CHORDS_FONT,
    SYMBOLS_FONT: SYMBOLS_FONT,
    TITLE_FONT: TITLE_FONT,
  };
});
