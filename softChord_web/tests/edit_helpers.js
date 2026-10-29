// Helpers shared by the browser tests of the Edit text mode (headless Chrome).
//
// Alignment is measured from pixels. The page is drawn twice, once with only the
// textarea's letters visible and once with only the sheet's letters, and the ink
// centre of every letter is compared. That is what a reader sees, so it catches
// a textarea that is a pixel off its sheet. Safari and Firefox are not tested.

const assert = require("node:assert/strict");
const helper = require("./browser_helper");

async function inEditor(songs, run) {
  var page = await helper.openViewer(songs);
  try {
    await page.eval("location.hash = '#/song/1'");
    await page.waitFor("!document.getElementById('song-view').hidden", "the song page");
    await run(page);
    assert.deepEqual(page.errors, [], "no uncaught errors in the page");
  } finally {
    await page.close();
  }
}

function click(page, id) {
  return page.eval("document.getElementById('" + id + "').click()");
}

async function startEditing(page) {
  await click(page, "edit-text");
  await page.waitFor("document.activeElement.id === 'sheet-editor'", "the editor to take focus");
}

function editorValue(page) {
  return page.eval("document.getElementById('sheet-editor').value");
}

function select(page, from, to) {
  return page.eval("document.getElementById('sheet-editor').setSelectionRange(" + from + ", " + to + ")");
}

function disabled(page, id) {
  return page.eval("document.getElementById('" + id + "').disabled");
}

// What the sheet shows: [[song char index, letter, chord text], ...]
function chordsShown(page) {
  return page.eval("Array.from(document.querySelectorAll('#sheet .char')).filter(function (c) {" +
    "return c.querySelector('.chord'); }).map(function (c) {" +
    "return [Number(c.dataset.songChar), c.firstChild.textContent, c.querySelector('.chord').textContent]; })");
}

function sheetText(page) {
  return page.eval("Array.from(document.querySelectorAll('#sheet .line')).map(function (line) {" +
    "return Array.from(line.querySelectorAll('.char')).map(function (c) {" +
    "return c.firstChild.textContent; }).join(''); }).join('\\n')");
}

// Ink centre of every visible letter, textarea against sheet, in pixels.
async function inkOffsets(page) {
  async function shot(css) {
    await page.eval("(function () { var s = document.createElement('style'); s.id = 'probe-style';" +
      "s.textContent = " + JSON.stringify(css) + "; document.head.appendChild(s); })()");
    var png = await page.screenshot();
    await page.eval("document.getElementById('probe-style').remove()");
    return png.toString("base64");
  }
  var quiet = "#sheet-editor { caret-color: transparent !important; }" +
    "#sheet-editor::selection { background: transparent !important; color: #000 !important;" +
    "-webkit-text-fill-color: #000 !important; }" +
    "#toast { display: none !important; }";
  var editorOnly = await shot(quiet + "#sheet { visibility: hidden; }" +
    "#sheet-editor { color: #000 !important; -webkit-text-fill-color: #000 !important; }");
  var sheetOnly = await shot(quiet + ".chord { display: none !important; }");
  return page.eval("(async function () {" +
    "function load(b64) { return new Promise(function (ok) { var i = new Image();" +
    "i.onload = function () { ok(i); }; i.src = 'data:image/png;base64,' + b64; }); }" +
    "var a = await load(" + JSON.stringify(editorOnly) + "), b = await load(" + JSON.stringify(sheetOnly) + ");" +
    "function pixels(img) { var c = document.createElement('canvas'); c.width = img.width; c.height = img.height;" +
    "var x = c.getContext('2d'); x.drawImage(img, 0, 0); return x.getImageData(0, 0, c.width, c.height); }" +
    "var A = pixels(a), B = pixels(b);" +
    "function centre(D, l, t, r, bt) { var sx = 0, sy = 0, w = 0;" +
    "for (var y = Math.max(0, t); y < Math.min(D.height, bt); y++) {" +
    "for (var x = Math.max(0, l); x < Math.min(D.width, r); x++) {" +
    "var i = (y * D.width + x) * 4; var d = 255 - (D.data[i] + D.data[i + 1] + D.data[i + 2]) / 3;" +
    "if (d > 0) { sx += d * x; sy += d * y; w += d; } } }" +
    "return w ? { x: sx / w, y: sy / w } : null; }" +
    "var out = []; var dpr = window.devicePixelRatio || 1;" +
    "document.querySelectorAll('#sheet .char').forEach(function (sp) {" +
    "if (!sp.firstChild.textContent.trim()) { return; }" +
    "var r = sp.getBoundingClientRect();" +
    "var args = [Math.floor(r.left * dpr), Math.floor(r.top * dpr), Math.ceil(r.right * dpr), Math.ceil(r.bottom * dpr)];" +
    "var ca = centre(A, args[0], args[1], args[2], args[3]), cb = centre(B, args[0], args[1], args[2], args[3]);" +
    "if (ca && cb) { out.push({ ch: sp.firstChild.textContent, dx: ca.x - cb.x, dy: ca.y - cb.y }); }" +
    "else if (ca || cb) { out.push({ ch: sp.firstChild.textContent, missing: true }); } });" +
    "return out; })()");
}

// Every letter of the textarea is within a pixel of the same letter of the sheet,
// and every chord is centred over its letter.
async function assertAligned(page, what, tolerance) {
  tolerance = tolerance || 1;
  var offsets = await inkOffsets(page);
  assert.ok(offsets.length > 0, what + ": letters were measured");
  offsets.forEach(function (o) {
    assert.ok(!o.missing, what + ": " + o.ch + " is drawn by both");
    assert.ok(Math.abs(o.dx) <= tolerance && Math.abs(o.dy) <= tolerance,
      what + ": " + o.ch + " is off by " + o.dx.toFixed(2) + ", " + o.dy.toFixed(2));
  });
  var chordOffsets = await page.eval("Array.from(document.querySelectorAll('#sheet .chord')).map(function (c) {" +
    "var l = c.parentElement.getBoundingClientRect(), r = c.getBoundingClientRect();" +
    "return Math.abs((l.left + l.right) / 2 - (r.left + r.right) / 2); })");
  chordOffsets.forEach(function (d) {
    assert.ok(d <= 1, what + ": a chord is " + d.toFixed(2) + "px off the middle of its letter");
  });
}

async function setZoom(page, percent) {
  // Same path as the buttons: click until the sheet has the size.
  var want = 20 * percent / 100;
  for (var i = 0; i < 40; i++) {
    var size = await page.eval("parseFloat(getComputedStyle(document.getElementById('sheet')).fontSize)");
    if (size === want) { return; }
    await click(page, size < want ? "zoom-in" : "zoom-out");
  }
  throw new Error("could not reach zoom " + percent);
}

module.exports = {
  inEditor: inEditor, click: click, startEditing: startEditing, editorValue: editorValue,
  select: select, disabled: disabled, chordsShown: chordsShown, sheetText: sheetText,
  inkOffsets: inkOffsets, assertAligned: assertAligned, setZoom: setZoom,
};
