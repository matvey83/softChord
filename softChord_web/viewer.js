// Song list and chord sheet.
// The open song is kept in memory. Transpose draws a shifted copy and does
// not write the songbook, so chord and text editing can change that copy later.

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

  // The open song as shown now: its text and chords at the current transpose.
  function shownSong() {
    var source = Songbook.source(openId);
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
    sheet.style.setProperty("--zoom", String(zoomPercent / 100));
    zoomOutButton.disabled = zoomPercent <= SongZoom.MIN;
    zoomInButton.disabled = zoomPercent >= SongZoom.MAX;
    zoomResetButton.disabled = SongZoom.isDefault(zoomPercent);
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
  function paintSheet(lines) {
    var songChar = 0;
    var frag = document.createDocumentFragment();
    for (var i = 0; i < lines.length; i++) {
      var line = lines[i];
      var row = document.createElement("div");
      row.className = "line" + (line.chords.length ? " has-chords" : "");
      var chars = Array.from(line.lyric);
      if (!chars.length) {
        row.appendChild(document.createElement("br"));
      }
      for (var a = 0; a < chars.length; a++) {
        var span = document.createElement("span");
        span.className = "char";
        // Song-wide character index. Chord editing can use this as the anchor.
        span.dataset.songChar = String(songChar + a);
        span.textContent = chars[a];
        for (var c = 0; c < line.chords.length; c++) {
          if (line.chords[c].anchor !== a) {
            continue;
          }
          var chord = document.createElement("span");
          chord.className = "chord" + (line.chords[c].unrecognized ? " unrecognized" : "");
          appendChord(chord, line.chords[c].text);
          span.appendChild(chord);
        }
        row.appendChild(span);
      }
      frag.appendChild(row);
      songChar += chars.length + 1;
    }
    sheet.replaceChildren(frag);
  }

  function paintSong() {
    var source;
    try {
      source = Songbook.source(openId);
    } catch (error) {
      songTitle.textContent = "";
      songError.hidden = false;
      songError.textContent = String(error.message || error);
      sheet.replaceChildren();
      persistNote.hidden = true;
      toolbarActions.hidden = true;
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
    persistNote.hidden = !transposed;
    // Dimmed until the song has been transposed. Up then down by the same
    // amount brings steps back to 0, which dims it again, and so does a whole
    // octave (12), which shows the same chords.
    transposeReset.disabled = !transposed;
  }

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
      listView.hidden = false;
      songView.hidden = true;
      document.title = "softChord Viewer";
      paintList();
      return;
    }
    if (openId !== id) {
      openId = id;
      steps = 0;
      sheetScroll.scrollTop = 0;
      sheetScroll.scrollLeft = 0;
    }
    listView.hidden = true;
    songView.hidden = false;
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
