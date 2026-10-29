// Song list and chord sheet.
// The open song is kept in memory. Transpose draws a shifted copy and does
// not write the songbook. Edit text changes the copy kept here (see the Edit
// text section below) and does not write the songbook either.

(function () {
  var listView = document.getElementById("list-view");
  var songView = document.getElementById("song-view");
  var search = document.getElementById("search");
  var songList = document.getElementById("song-list");
  var listError = document.getElementById("list-error");
  var songTitle = document.getElementById("song-title");
  var songError = document.getElementById("song-error");
  var sheet = document.getElementById("sheet");
  var sheetScroll = document.getElementById("sheet-scroll");
  var sheetWrap = document.getElementById("sheet-wrap") || document.createElement("div");
  // Toolbar parts the page may not have (an older cached index.html, or a
  // trimmed page): a missing one becomes a detached stand-in, so the song list
  // and the song still work and nothing throws.
  function optional(id) {
    return document.getElementById(id) || document.createElement("button");
  }
  var persistNote = optional("persist-note");
  var transposeDown = optional("transpose-down");
  var transposeUp = optional("transpose-up");
  var transposeReset = optional("transpose-reset");
  var toolbarActions = document.querySelector(".toolbar-actions") || document.createElement("div");
  var copyTextButton = optional("copy-text");
  var copyChordsButton = optional("copy-chords");
  var copyImageButton = optional("copy-image");
  var zoomOutButton = optional("zoom-out");
  var printButton = optional("print");
  var zoomResetButton = optional("zoom-reset");
  var zoomInButton = optional("zoom-in");
  var editButton = optional("edit-text");
  var editActions = optional("edit-actions");
  var saveButton = optional("edit-save");
  var discardButton = optional("edit-discard");
  var editor = document.getElementById("sheet-editor") || document.createElement("textarea");
  var toast = optional("toast");
  var menu = document.getElementById("menu");
  var notice = document.getElementById("notice");
  var noticeTitle = document.getElementById("notice-title");
  var noticeMessage = document.getElementById("notice-message");

  // The .songbook next to this folder. A future server replaces Songbook.load.
  var songbookUrl = "../zvuki_neba.songbook";

  var allTitles = [];
  var loadError = null;
  var openId = null;
  // Half steps the open song is shifted from how it was when it was opened.
  // Opening a song always starts at 0, so 0 is the key the song had when it
  // was loaded in this session, and Reset transpose goes back to it.
  var steps = 0;
  // Song area zoom in percent. It stays when another song is opened and is
  // remembered in this browser. It never touches the toolbar or the copied image.
  var zoomStorage = null;
  try {
    zoomStorage = window.localStorage;
  } catch (error) {
    // Blocked storage: zoom still works, it is just not remembered.
  }
  var zoomPercent = SongZoom.load(zoomStorage);
  var menuSongId = null;
  var toastTimer = null;
  // Edit text. savedEdit is the text and chords the user kept with Save, for
  // the open song only (the songbook is not written), and draft is the edit in
  // progress. Both are thrown away when the page leaves the song. Chords in
  // both are not transposed: they are shown shifted by steps, like the iPhone app.
  var savedEdit = null;
  var draft = null;
  var composing = false;

  function notify(title, message) {
    noticeTitle.textContent = title;
    noticeMessage.textContent = message;
    if (typeof notice.showModal === "function") {
      if (!notice.open) {
        notice.showModal();
      }
    } else {
      window.alert(title + "\n" + message);
    }
  }

  // Returns a promise. The async clipboard comes first, and the old
  // select-and-copy way is the fallback where it is missing or refused.
  function copyText(text) {
    if (navigator.clipboard && typeof navigator.clipboard.writeText === "function" &&
        window.isSecureContext !== false) {
      return navigator.clipboard.writeText(text).catch(function () {
        copyTextOldWay(text);
      });
    }
    try {
      copyTextOldWay(text);
      return Promise.resolve();
    } catch (error) {
      return Promise.reject(error);
    }
  }

  function copyTextOldWay(text) {
    var area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.left = "-9999px";
    document.body.appendChild(area);
    area.select();
    var ok = document.execCommand("copy");
    area.remove();
    if (!ok) {
      throw new Error("The song could not be copied.");
    }
  }

  // A short message that fades on its own. Failures use the notice dialog.
  function showToast(message) {
    toast.textContent = message;
    toast.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      toast.hidden = true;
    }, 2200);
  }

  // The open song: the songbook's copy, or the text and chords kept with Save.
  // The chords are not transposed.
  function openSource() {
    var source = Songbook.source(openId);
    if (savedEdit && savedEdit.id === openId) {
      source.text = savedEdit.text;
      source.chords = savedEdit.chords.map(function (chord) {
        return Object.assign({}, chord);
      });
    }
    return source;
  }

  // The open song as shown now: its text and chords at the current transpose.
  function shownSong() {
    var source = openSource();
    return {
      title: source.title,
      text: source.text,
      chords: SongTranspose.shifted(source.chords, steps),
    };
  }

  function copyShownText(includeChords, doneMessage) {
    var done;
    try {
      var song = shownSong();
      done = copyText(SongText.render(song.text, song.chords, includeChords));
    } catch (error) {
      done = Promise.reject(error);
    }
    return done.then(function () {
      showToast(doneMessage);
    }, function (error) {
      notify("Could not copy the song", String(error.message || error));
    });
  }

  function measureWith(ctx) {
    return function (font, text) {
      ctx.font = font;
      var m = ctx.measureText(text);
      var size = parseFloat(/(\d+(?:\.\d+)?)px/.exec(font)[1]);
      return {
        width: m.width,
        ascent: m.fontBoundingBoxAscent != null ? m.fontBoundingBoxAscent : size * 0.891,
        descent: m.fontBoundingBoxDescent != null ? m.fontBoundingBoxDescent : size * 0.216,
      };
    };
  }

  // Draws the shown song, title first, and gives back a promise of a PNG blob.
  function renderSongImage() {
    return new Promise(function (resolve, reject) {
      try {
        var song = shownSong();
        var canvas = document.createElement("canvas");
        var ctx = canvas.getContext("2d");
        var drawing = SheetImage.layout(
          song.title, SongText.sheet(song.text, song.chords), measureWith(ctx));
        // Sharp enough to paste into a document, even on a 1x screen.
        var scale = SheetImage.scaleFor(drawing, Math.max(2, window.devicePixelRatio || 1));
        var pixels = SheetImage.pixelSize(drawing, scale);
        canvas.width = pixels.width;
        canvas.height = pixels.height;
        SheetImage.paint(canvas.getContext("2d"), drawing, scale, pixels);
        canvas.toBlob(function (blob) {
          if (blob) {
            resolve({ blob: blob, name: SheetImage.fileName(song.title) });
          } else {
            reject(new Error("The picture could not be made."));
          }
        }, "image/png");
      } catch (error) {
        reject(error);
      }
    });
  }

  function downloadBlob(blob, name) {
    var url = URL.createObjectURL(blob);
    var link = document.createElement("a");
    link.href = url;
    link.download = name;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 10000);
  }

  // Copies the picture to the clipboard. Where the browser cannot (no image
  // clipboard, a page that is not secure, or permission refused) the picture
  // is saved as a file instead and the notice says so.
  function copyShownImage() {
    var made = renderSongImage();
    var canCopy = window.isSecureContext !== false &&
      typeof ClipboardItem !== "undefined" &&
      navigator.clipboard && typeof navigator.clipboard.write === "function";
    var copied = Promise.resolve(false);
    if (canCopy) {
      // The blob is passed as a promise so Safari still sees the click.
      var item = new ClipboardItem({
        "image/png": made.then(function (result) { return result.blob; }),
      });
      copied = navigator.clipboard.write([item]).then(function () {
        return true;
      }, function () {
        return false;
      });
    }
    return Promise.all([made, copied]).then(function (results) {
      if (results[1]) {
        showToast("Copied song as image");
        return;
      }
      downloadBlob(results[0].blob, results[0].name);
      notify("Image saved as a file",
        "This browser would not copy the picture to the clipboard, so it was saved as " +
        results[0].name + " instead.");
    }, function (error) {
      notify("Could not copy the song as an image", String(error.message || error));
    });
  }

  function applyZoom() {
    // The sheet and the editor over it read it from this one parent.
    sheetWrap.style.setProperty("--zoom", String(zoomPercent / 100));
    // The room kept above every line while editing: about 1.15em, but an even
    // number of whole pixels (see viewer.css).
    sheetWrap.style.setProperty("--edit-gap", 2 * Math.round(0.575 * 20 * zoomPercent / 100) + "px");
    // See --boost in viewer.css: the textarea is never set below 16px (the CSS
    // font-size is also max(16px, ...), so rounding cannot leave it just under).
    // A whole-number boost or a little more than 16px made the letters no closer
    // to the sheet's, so it is the exact ratio. Below 80%
    // the letters can still differ from the sheet's by up to about a pixel
    // vertically, because the browser rounds ascent and line height to whole
    // pixels for each font size separately.
    var size = 20 * zoomPercent / 100;
    var boost = size < 16 ? 16 / size : 1;
    sheetWrap.style.setProperty("--boost", String(boost));
    sheetWrap.classList.toggle("boosted", boost > 1);
    zoomOutButton.disabled = zoomPercent <= SongZoom.MIN;
    zoomInButton.disabled = zoomPercent >= SongZoom.MAX;
    zoomResetButton.disabled = SongZoom.isDefault(zoomPercent);
    fitTabs();
    if (draft) {
      sizeEditor();
    }
  }

  function zoomBy(direction) {
    var next = SongZoom.stepped(zoomPercent, direction);
    if (next === zoomPercent) {
      return;
    }
    zoomPercent = next;
    SongZoom.save(zoomStorage, zoomPercent);
    applyZoom();
    showToast("Zoom " + zoomPercent + "%");
  }

  function resetZoom() {
    if (zoomPercent === SongZoom.DEFAULT) {
      return;
    }
    zoomPercent = SongZoom.DEFAULT;
    SongZoom.save(zoomStorage, zoomPercent);
    applyZoom();
    showToast("Zoom " + zoomPercent + "%");
  }

  function showListMessage(text, isError) {
    listError.hidden = !text;
    listError.textContent = text || "";
    listError.className = isError ? "error" : "status";
  }

  function paintList() {
    if (loadError) {
      showListMessage(loadError, true);
      songList.replaceChildren();
      return;
    }
    showListMessage("", false);
    var songs = SongFilter.matching(search.value, allTitles);
    var frag = document.createDocumentFragment();
    for (var i = 0; i < songs.length; i++) {
      var item = document.createElement("li");
      var button = document.createElement("button");
      button.type = "button";
      button.dataset.id = String(songs[i].id);
      // TODO: Show the song number in front of the title when it is not -1.
      button.textContent = songs[i].title;
      item.appendChild(button);
      frag.appendChild(item);
    }
    songList.replaceChildren(frag);
  }

  function appendChord(node, text) {
    var chars = Array.from(text);
    for (var i = 0; i < chars.length; i++) {
      var ch = chars[i];
      if (ch === "♯" || ch === "♭") {
        var accidental = document.createElement("span");
        accidental.className = "accidental";
        accidental.textContent = ch;
        node.appendChild(accidental);
      } else {
        node.appendChild(document.createTextNode(ch));
      }
    }
  }

  // TODO: Show the subtitle and "Auto-detected key: ..." under the title.
  // Paint with the same measurements as SongSheetLayout.drawing (gap, chord
  // center, accidental raise, padding 16, left shift) instead of the CSS
  // approximation. Then pinch and Ctrl-scroll zoom (they can reuse zoomBy).
  // The editor keeps drawing with Qt.
  // The rows now in the sheet, one {key, start, row} per song line (key is the
  // line's text and chords, start its first code point in the song). Typing changes
  // one line, so painting again only builds the rows that differ from these.
  var painted = [];

  function lineKey(line) {
    var key = line.lyric + "\u0000";
    for (var c = 0; c < line.chords.length; c++) {
      var chord = line.chords[c];
      key += chord.anchor + ":" + (chord.span || 1) + ":" + (chord.unrecognized ? 1 : 0) + ":" +
        chord.text + "\u0001";
    }
    return key;
  }

  // Fills the empty row with the letters of the line, each with its chords.
  function buildRowInto(row, line, songChar) {
    row.className = "line" + (line.chords.length ? " has-chords" : "");
    // One box per letter as the reader sees it (an accent or an emoji with its
    // joiners is part of its letter), numbered by the code point it starts at,
    // which is how chords are numbered in the songbook.
    var chars = SongText.letters(line.lyric);
    var length = 0;
    if (!chars.length) {
      row.appendChild(document.createElement("br"));
    }
    for (var a = 0; a < chars.length; a++) {
      var span = document.createElement("span");
      span.className = chars[a] === "\t" ? "char tab" : "char";
      // Song-wide character index. Chord editing can use this as the anchor.
      span.dataset.songChar = String(songChar + length);
      span.textContent = chars[a];
      for (var c = 0; c < line.chords.length; c++) {
        if (line.chords[c].anchor !== length) {
          continue;
        }
        var chord = document.createElement("span");
        chord.className = "chord" + (line.chords[c].unrecognized ? " unrecognized" : "");
        appendChord(chord, line.chords[c].text);
        span.appendChild(chord);
      }
      row.appendChild(span);
      length += chars[a].length === 1 ? 1 : Array.from(chars[a]).length;
    }
  }

  function paintSheet(lines) {
    var next = [];
    var songChar = 0;
    for (var i = 0; i < lines.length; i++) {
      next.push({ key: lineKey(lines[i]), start: songChar, row: null });
      songChar += Array.from(lines[i].lyric).length + 1;
    }
    // What is in the sheet is what was painted last, unless something else has
    // been put there (an error clears it).
    var old = sheet.children.length === painted.length ? painted : [];
    // Rows that are the same at the top and at the bottom are kept.
    var top = 0;
    while (top < old.length && top < next.length && old[top].key === next[top].key) {
      next[top].row = old[top].row;
      top++;
    }
    var bottom = 0;
    while (bottom < old.length - top && bottom < next.length - top &&
      old[old.length - 1 - bottom].key === next[next.length - 1 - bottom].key) {
      var kept = next[next.length - 1 - bottom];
      kept.row = old[old.length - 1 - bottom].row;
      var shift = kept.start - old[old.length - 1 - bottom].start;
      if (shift !== 0) {
        for (var k = 0; k < kept.row.children.length; k++) {
          var box = kept.row.children[k];
          if (box.dataset && box.dataset.songChar !== undefined) {
            box.dataset.songChar = String(Number(box.dataset.songChar) + shift);
          }
        }
      }
      bottom++;
    }
    var frag = document.createDocumentFragment();
    for (var n = top; n < next.length - bottom; n++) {
      var row = document.createElement("div");
      buildRowInto(row, lines[n], next[n].start);
      next[n].row = row;
      frag.appendChild(row);
    }
    // Replace the rows between the kept ones.
    var stale = old.length - top - bottom;
    var before = old[top + stale] ? old[top + stale].row : null;
    for (var r = 0; r < stale; r++) {
      sheet.removeChild(old[top + r].row);
    }
    if (old.length === 0) {
      sheet.replaceChildren(frag);
    } else {
      sheet.insertBefore(frag, before);
    }
    painted = next;
    fitTabs();
  }

  // A tab moves the next letter to the next tab stop, a whole number of 8 spaces
  // from the start of the line, like in the textarea over the sheet. The sheet
  // draws every letter in a box of its own, and a box holding only a tab is
  // always 8 spaces wide, so each tab box gets the width that reaches the next
  // stop from where it begins (in em, so it follows the zoom and the printed size).
  // The text and the chords' positions in it are not changed, only the box.
  function fitTabs() {
    var tabs = sheet.querySelectorAll(".char.tab");
    if (!tabs.length) {
      return;
    }
    var i;
    for (i = 0; i < tabs.length; i++) {
      tabs[i].style.width = "";
    }
    var stop = tabs[0].getBoundingClientRect().width;
    var fontSize = parseFloat(getComputedStyle(sheet).fontSize);
    if (!(stop > 0) || !(fontSize > 0)) {
      return;
    }
    var widths = [];
    var line = null;
    var lineLeft = 0;
    var moved = 0;
    for (i = 0; i < tabs.length; i++) {
      if (tabs[i].parentNode !== line) {
        line = tabs[i].parentNode;
        lineLeft = line.getBoundingClientRect().left;
        moved = 0;
      }
      // Where this tab begins once the tabs before it on its line are fitted.
      var begin = tabs[i].getBoundingClientRect().left - lineLeft + moved;
      var width = (Math.floor(begin / stop + 0.0001) + 1) * stop - begin;
      widths.push(width);
      moved += width - stop;
    }
    for (i = 0; i < tabs.length; i++) {
      tabs[i].style.width = widths[i] / fontSize + "em";
    }
  }

  function paintSong() {
    var source;
    try {
      source = openSource();
    } catch (error) {
      songTitle.textContent = "";
      songError.hidden = false;
      songError.textContent = String(error.message || error);
      sheet.replaceChildren();
      persistNote.hidden = true;
      toolbarActions.hidden = true;
      leaveEditing();
      transposeReset.disabled = true;
      document.title = "softChord Viewer";
      return;
    }
    songError.hidden = true;
    toolbarActions.hidden = false;
    songTitle.textContent = source.title;
    document.title = source.title;
    var chords = SongTranspose.shifted(source.chords, steps);
    paintSheet(SongText.sheet(source.text, chords));
    // The note and Reset follow the same rule: a whole octave (12) shows the
    // same chords, so it counts as not transposed. So does a song with no chord
    // that can move (text that is not a chord stays as it is).
    var transposed = SongTranspose.changesChords(source.chords, steps);
    persistNote.hidden = !(transposed || savedEdit);
    // Dimmed until the song has been transposed. Up then down by the same
    // amount brings steps back to 0, which dims it again, and so does a whole
    // octave (12), which shows the same chords.
    transposeReset.disabled = !transposed;
  }

  // ---- Edit text ----
  // The whole text of the song can be typed in. The textarea lies exactly over
  // the sheet and its own letters are see-through, so what is seen is the sheet
  // painted from the draft, with the chords above their letters. After every
  // change the chords are moved to the letters they were on (SongTextEdit, the
  // same rule as the desktop editor and the iPhone app) and the sheet is
  // painted again, so the chords follow the text as it is typed.
  //
  // textarea.value is only set once, when editing starts. Setting it again
  // would move the caret and clear the browser's own undo, which Undo and Redo
  // use. For those the draft keeps a snapshot {text, chords} per change: the
  // browser undoes the text, and the chords of the snapshot with that text come
  // back, including chords that were dropped with deleted letters.

  function cloneChords(chords) {
    return chords.map(function (chord) { return Object.assign({}, chord); });
  }

  function sameChords(a, b) {
    return a.length === b.length && a.every(function (chord, index) {
      return JSON.stringify(chord) === JSON.stringify(b[index]);
    });
  }

  function paintDraft(text, chords) {
    paintSheet(SongText.sheet(text, SongTranspose.shifted(chords, steps)));
    sizeEditor();
  }

  // The textarea is as big as everything it holds, so it never scrolls itself.
  // The song area scrolls the sheet and the textarea together.
  function sizeEditor() {
    if (editor.hidden) {
      return;
    }
    // The textarea is laid out boost times as large as it is seen (see --boost in
    // viewer.css), so the sizes of the sheet are multiplied to match.
    var boost = parseFloat(sheetWrap.style.getPropertyValue("--boost")) || 1;
    editor.style.height = "0px";
    editor.style.width = sheetWrap.clientWidth * boost + "px";
    // A line wider than the song area scrolls it. The sheet's padding to the right
    // of that line is not counted in its scroll width, so it is added here.
    var rows = sheet.scrollWidth > sheet.clientWidth ? (sheet.scrollWidth + 32) * boost : 0;
    var width = Math.max(sheetWrap.clientWidth * boost, editor.scrollWidth, rows);
    editor.style.width = width + "px";
    editor.style.height = Math.max(editor.scrollHeight, sheet.offsetHeight * boost) + "px";
  }

  // These buttons need the song as it is on disk or in the viewer, so they wait
  // until Save or Discard. Zoom is not among them: the textarea is sized in em
  // from the same --zoom as the sheet, so it scales together with it.
  function setEditingState(on) {
    // The textarea holds the same words as the sheet under it, and has the label
    // "Song text". A screen reader would read the song twice, so while editing
    // only the textarea is left for it.
    if (on) {
      sheet.setAttribute("aria-hidden", "true");
    } else {
      sheet.removeAttribute("aria-hidden");
    }
    [printButton, copyTextButton, copyChordsButton, copyImageButton, transposeDown,
      transposeUp, transposeReset, editButton].forEach(function (button) {
      button.disabled = on;
    });
    editActions.hidden = !on;
    sheetWrap.classList.toggle("editing", on);
    editor.hidden = !on;
  }

  // The song line at the top of the song area, and how far its top edge is from
  // the top of the area (negative when it is cut off). Opening or leaving the
  // editor changes the height of the lines (every line gets room for chords while
  // editing), so the area is scrolled back to put this line where it was.
  function topLine() {
    var base = sheetScroll.getBoundingClientRect().top;
    var rows = sheet.children;
    for (var i = 0; i < rows.length; i++) {
      var rect = rows[i].getBoundingClientRect();
      if (rect.bottom > base + 0.5) {
        return { index: i, offset: rect.top - base };
      }
    }
    return null;
  }

  function scrollToLine(anchor) {
    var rows = sheet.children;
    if (!anchor || !rows.length) {
      return;
    }
    var row = rows[Math.min(anchor.index, rows.length - 1)];
    var base = sheetScroll.getBoundingClientRect().top;
    sheetScroll.scrollTop += row.getBoundingClientRect().top - base - anchor.offset;
  }

  // UTF-16 offset in the text of the start of its line number (the textarea's unit).
  function lineStartOffset(text, lineIndex) {
    var offset = 0;
    for (var i = 0; i < lineIndex; i++) {
      var next = text.indexOf("\n", offset);
      if (next < 0) {
        break;
      }
      offset = next + 1;
    }
    return offset;
  }

  function startEditing() {
    if (draft || openId == null) {
      return;
    }
    var source;
    try {
      source = openSource();
    } catch (error) {
      return;
    }
    var normal = SongTextEdit.normalizeSong(source.text, source.chords);
    draft = {
      text: normal.text,
      chords: normal.chords,
      history: [{ text: normal.text, chords: cloneChords(normal.chords) }],
      index: 0,
    };
    composing = false;
    var anchor = topLine();
    // Nothing is written anywhere, so say so before the first key is typed, not
    // only after Save. Save, Discard and paintSong set the note again from what
    // is really kept.
    persistNote.hidden = false;
    setEditingState(true);
    editor.value = draft.text;
    paintDraft(draft.text, draft.chords);
    editor.focus({ preventScroll: true });
    // The caret starts on the first line that shows, not at the top of the song.
    var caret = lineStartOffset(draft.text, anchor ? anchor.index : 0);
    editor.setSelectionRange(caret, caret);
    scrollToLine(anchor);
  }

  // Leaves the editing screen without saving. paintSong draws the song after it.
  function leaveEditing() {
    if (!draft) {
      return;
    }
    draft = null;
    composing = false;
    setEditingState(false);
    editor.value = "";
  }

  function finishEditing(save) {
    if (!draft) {
      return;
    }
    var kept = draft;
    var anchor = topLine();
    leaveEditing();
    if (save) {
      var original = Songbook.source(openId);
      var normal = SongTextEdit.normalizeSong(original.text, original.chords);
      // Nothing was changed: there is nothing that would not persist. The chords are
      // compared too. A song with a chord that has no letter (past the end of the
      // text, from a damaged songbook) loses it with the first edit (see
      // SongTextEdit.moveChords), so typing a letter and deleting it again is a change
      // here: the text is the same but a chord is gone, and the note is shown. That
      // is as it should be.
      if (kept.text === normal.text && sameChords(kept.chords, normal.chords)) {
        savedEdit = null;
      } else {
        savedEdit = { id: openId, text: kept.text, chords: kept.chords };
      }
    }
    paintSong();
    scrollToLine(anchor);
    // The button that was clicked is gone from the screen, so the keyboard would
    // otherwise be left on the page itself. Edit text is where the user was.
    editButton.focus({ preventScroll: true });
    if (save && savedEdit) {
      showToast("Saved");
    }
  }

  function forgetEdits() {
    savedEdit = null;
    leaveEditing();
  }

  // The index of the snapshot with this text, nearest to the current one and
  // looking only in the direction Undo or Redo went. -1 when there is none.
  function snapshotWith(text, direction) {
    for (var i = draft.index + direction; i >= 0 && i < draft.history.length; i += direction) {
      if (draft.history[i].text === text) {
        return i;
      }
    }
    return -1;
  }

  // The text the textarea holds now has become the draft's text.
  function commitEdit(inputType) {
    var text = editor.value;
    if (!draft || text === draft.text) {
      return;
    }
    var chords = null;
    if (inputType === "historyUndo" || inputType === "historyRedo") {
      var found = snapshotWith(text, inputType === "historyUndo" ? -1 : 1);
      if (found >= 0) {
        draft.index = found;
        chords = cloneChords(draft.history[found].chords);
      }
    }
    if (chords === null) {
      // A normal edit, or an undo past the oldest snapshot kept (SongTextEdit.HISTORY_LIMIT):
      // the chords follow their letters, and this is the newest snapshot.
      chords = SongTextEdit.moveChords(draft.chords, draft.text, text);
      draft.index = SongTextEdit.pushSnapshot(draft.history, draft.index,
        { text: text, chords: cloneChords(chords) });
    }
    draft.text = text;
    draft.chords = chords;
    paintDraft(text, chords);
  }

  editor.addEventListener("input", function (event) {
    if (!draft) {
      return;
    }
    if (composing || event.isComposing) {
      // Show the letters being composed, with the chords as they would move
      // from the text before the composition began. The snapshot waits for
      // compositionend.
      paintDraft(editor.value, SongTextEdit.moveChords(draft.chords, draft.text, editor.value));
      return;
    }
    commitEdit(event.inputType);
  });

  editor.addEventListener("compositionstart", function () {
    composing = true;
  });

  editor.addEventListener("compositionend", function () {
    composing = false;
    commitEdit("insertCompositionText");
  });

  editButton.addEventListener("click", startEditing);
  saveButton.addEventListener("click", function () { finishEditing(true); });
  discardButton.addEventListener("click", function () { finishEditing(false); });
  window.addEventListener("resize", function () {
    if (draft) {
      sizeEditor();
    }
  });

  function songIdFromHash() {
    var match = /^#\/song\/(\d+)$/.exec(location.hash);
    return match ? Number(match[1]) : null;
  }

  function showFromHash() {
    var id = songIdFromHash();
    menu.hidden = true;
    if (id == null) {
      openId = null;
      steps = 0;
      forgetEdits();
      listView.hidden = false;
      songView.hidden = true;
      document.title = "softChord Viewer";
      paintList();
      return;
    }
    if (openId !== id) {
      openId = id;
      steps = 0;
      forgetEdits();
      sheetScroll.scrollTop = 0;
      sheetScroll.scrollLeft = 0;
    }
    listView.hidden = true;
    songView.hidden = false;
    // The address of the song that is being edited again (#/song/01 is song 1):
    // painting the song now would put the saved text over the sheet while the
    // textarea still holds the draft. The edit goes on as it was.
    if (draft) {
      return;
    }
    paintSong();
  }

  search.addEventListener("input", paintList);
  search.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
      search.blur();
    }
  });

  songList.addEventListener("click", function (event) {
    var button = event.target.closest("button");
    if (!button) {
      return;
    }
    location.hash = "#/song/" + button.dataset.id;
  });

  // TODO: Open this menu on a long press. The open song has toolbar buttons.
  songList.addEventListener("contextmenu", function (event) {
    var button = event.target.closest("button");
    if (!button) {
      return;
    }
    event.preventDefault();
    menuSongId = Number(button.dataset.id);
    menu.hidden = false;
    menu.style.left = event.clientX + "px";
    menu.style.top = event.clientY + "px";
    var rect = menu.getBoundingClientRect();
    if (rect.right > window.innerWidth) {
      menu.style.left = Math.max(8, window.innerWidth - rect.width - 8) + "px";
    }
    if (rect.bottom > window.innerHeight) {
      menu.style.top = Math.max(8, window.innerHeight - rect.height - 8) + "px";
    }
  });

  menu.addEventListener("click", function (event) {
    var action = event.target.closest("button");
    if (!action || menuSongId == null) {
      return;
    }
    menu.hidden = true;
    var done;
    try {
      done = copyText(Songbook.songText(menuSongId, action.dataset.action === "chords"));
    } catch (error) {
      done = Promise.reject(error);
    }
    done.catch(function (error) {
      notify("Could not copy the song", String(error.message || error));
    });
  });

  document.addEventListener("click", function (event) {
    if (!menu.hidden && !menu.contains(event.target)) {
      menu.hidden = true;
    }
  });

  document.getElementById("back").addEventListener("click", function () {
    location.hash = "#/";
  });

  copyTextButton.addEventListener("click", function () {
    copyShownText(false, "Copied song text");
  });

  copyChordsButton.addEventListener("click", function () {
    copyShownText(true, "Copied song text with chords");
  });

  copyImageButton.addEventListener("click", copyShownImage);

  zoomOutButton.addEventListener("click", function () { zoomBy(-1); });

  zoomResetButton.addEventListener("click", resetZoom);

  // The browser's print dialog also offers "Save as PDF". What is printed is
  // decided by the @media print rules in viewer.css (the song as shown, with its
  // current transpose, at a fixed size that ignores the on-screen zoom).
  printButton.addEventListener("click", function () {
    window.print();
  });

  zoomInButton.addEventListener("click", function () { zoomBy(1); });

  transposeDown.addEventListener("click", function () {
    steps -= 1;
    paintSong();
  });

  transposeUp.addEventListener("click", function () {
    steps += 1;
    paintSong();
  });

  transposeReset.addEventListener("click", function () {
    // paintSong dims the button when nothing is changed (see changesChords).
    if (transposeReset.disabled) {
      return;
    }
    steps = 0;
    paintSong();
    showToast("Transpose reset");
  });

  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") {
      return;
    }
    // Escape closes the notice dialog itself. It must not also leave the song.
    if (event.defaultPrevented || notice.open) {
      return;
    }
    // Escape does nothing while the text is edited, so that a stray press does
    // not throw the edit away. Save or Discard finishes it, and so does Back.
    if (draft) {
      return;
    }
    if (!menu.hidden) {
      menu.hidden = true;
      return;
    }
    if (!songView.hidden) {
      location.hash = "#/";
    }
  });

  applyZoom();
  window.addEventListener("hashchange", showFromHash);
  showListMessage("Opening songbook…", false);
  Songbook.load(songbookUrl).then(function () {
    allTitles = Songbook.titles();
    loadError = null;
    showListMessage("", false);
    showFromHash();
    if (songIdFromHash() == null) {
      search.focus();
    }
  }).catch(function (error) {
    loadError = String(error.message || error);
    showFromHash();
  });
})();
