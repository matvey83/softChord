const test = require("node:test");
const assert = require("node:assert/strict");

const SheetImage = require("../softchord_sheet_image");

// iPhone Safari draws at most 16 777 216 px (4096 x 4096) on a canvas, and the
// other browsers at most 16384 px on a side.
const IPHONE_AREA = 16777216;

function pixelsFor(drawing, wanted) {
  var scale = SheetImage.scaleFor(drawing, wanted);
  return { scale: scale, pixels: SheetImage.pixelSize(drawing, scale) };
}

test("a normal song is drawn at the wanted sharpness", function () {
  var result = pixelsFor({ width: 600, height: 900 }, 2);
  assert.equal(result.scale, 2);
  assert.deepEqual(result.pixels, { width: 1200, height: 1800 });
  // Never below 1 for a wanted ratio, and an odd wanted value is kept.
  assert.equal(SheetImage.scaleFor({ width: 600, height: 900 }, 0), 1);
  assert.equal(SheetImage.scaleFor({ width: 600, height: 900 }, 3), 3);
});

test("the picture area stays under what iPhone Safari can draw", function () {
  assert.ok(SheetImage.MAX_AREA < IPHONE_AREA);
  [[600, 9000], [3000, 6000], [1200, 12000], [800, 20000]].forEach(function (size) {
    var result = pixelsFor({ width: size[0], height: size[1] }, 3);
    var area = result.pixels.width * result.pixels.height;
    assert.ok(area <= IPHONE_AREA, size.join("x") + " area " + area);
    assert.ok(result.pixels.width <= SheetImage.MAX_SIDE && result.pixels.height <= SheetImage.MAX_SIDE);
  });
});

test("a very tall or wide song is scaled down below 1 instead of past the side limit", function () {
  // The old floor of 0.1 left these over 16384 px on a side.
  [[600, 200000], [600, 1000000], [200000, 100], [100, 5000000]].forEach(function (size) {
    var drawing = { width: size[0], height: size[1] };
    var result = pixelsFor(drawing, 2);
    assert.ok(result.scale > 0 && result.scale < 1, size.join("x") + " scale " + result.scale);
    assert.ok(result.pixels.width <= SheetImage.MAX_SIDE, size.join("x") + " width");
    assert.ok(result.pixels.height <= SheetImage.MAX_SIDE, size.join("x") + " height");
    assert.ok(result.pixels.width >= 1 && result.pixels.height >= 1);
  });
});

test("a song just under the limits is not shrunk more than it has to be", function () {
  var drawing = { width: 600, height: 9000 };
  var result = pixelsFor(drawing, 2);
  var area = result.pixels.width * result.pixels.height;
  assert.ok(area > SheetImage.MAX_AREA * 0.99, "uses the room it has: " + area);
});
