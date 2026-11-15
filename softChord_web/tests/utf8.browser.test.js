// The copy buttons of the real viewer page, in headless Chrome, with a song in
// Cyrillic, accented Latin and emoji: Copy song text (both ways it can copy) and
// Copy song as image when the picture is saved as a file. Skipped when Chrome is
// not installed.

const test = require("node:test");
const assert = require("node:assert/strict");
const helper = require("./browser_helper");
const { inEditor, click } = require("./edit_helpers");

const skip = helper.skipUnlessBrowser();

const SAMPLE = "Привет café 🎵";
const SONG = { title: SAMPLE, text: SAMPLE + "\n" + SAMPLE, chords: [[0, "Am"], [7, "C"]] };

// The page's own UTF-8 bytes of a copied string, decoded back.
const DECODE = "(function (t) { return new TextDecoder('utf-8', { fatal: true })" +
  ".decode(new TextEncoder().encode(t)); })";

test("the page is UTF-8 and Copy song text copies the sample unchanged", { skip: skip }, function () {
  return inEditor([SONG], async function (page) {
    assert.equal(await page.eval("document.characterSet"), "UTF-8");
    await page.eval("window.__copied = []; Object.defineProperty(navigator, 'clipboard', " +
      "{ value: { writeText: function (t) { window.__copied.push(t); return Promise.resolve(); } } })");
    await click(page, "copy-text");
    await page.waitFor("window.__copied.length === 1", "the text copy");
    assert.equal(await page.eval("window.__copied[0]"), SAMPLE + "\r\n" + SAMPLE);
    assert.equal(await page.eval(DECODE + "(window.__copied[0])"), SAMPLE + "\r\n" + SAMPLE);
    await click(page, "copy-chords");
    await page.waitFor("window.__copied.length === 2", "the copy with chords");
    var withChords = await page.eval("window.__copied[1]");
    assert.ok(withChords.startsWith("Am"), withChords);
    assert.ok(withChords.endsWith("\r\n" + SAMPLE), withChords);
    assert.equal(await page.eval(DECODE + "(window.__copied[1])"), withChords);
  });
});

test("the old select-and-copy fallback copies the sample unchanged", { skip: skip }, function () {
  return inEditor([SONG], async function (page) {
    // No async clipboard: the viewer copies a hidden textarea instead.
    await page.eval("window.__copied = []; Object.defineProperty(navigator, 'clipboard', { value: undefined });" +
      "document.execCommand = function (name) {" +
      "  var area = document.activeElement;" +
      "  window.__copied.push(name + ':' + area.value.substring(area.selectionStart, area.selectionEnd));" +
      "  return true; }");
    await click(page, "copy-text");
    await page.waitFor("window.__copied.length === 1", "the text copy");
    // A textarea's value has \n line ends (HTML normalizes \r\n); the letters are the point here.
    assert.equal(await page.eval("window.__copied[0]"), "copy:" + SAMPLE + "\n" + SAMPLE);
  });
});

test("a picture saved as a file is a PNG named after the Unicode title", { skip: skip }, function () {
  return inEditor([SONG], async function (page) {
    // No image clipboard: the picture is downloaded instead.
    await page.eval("window.__saved = []; window.ClipboardItem = undefined;" +
      "URL.createObjectURL = function (blob) { window.__saved.push({ type: blob.type }); return 'blob:x'; };" +
      "HTMLAnchorElement.prototype.click = function () {" +
      "  window.__saved[window.__saved.length - 1].name = this.download; };");
    await click(page, "copy-image");
    await page.waitFor("window.__saved.length === 1 && window.__saved[0].name", "the saved picture");
    assert.deepEqual(await page.eval("window.__saved[0]"), { type: "image/png", name: SAMPLE + ".png" });
    // The notice names the file.
    await page.waitFor("document.getElementById('notice').open", "the notice");
    var notice = await page.eval("document.getElementById('notice').textContent");
    assert.ok(notice.includes(SAMPLE + ".png"), notice);
  });
});
