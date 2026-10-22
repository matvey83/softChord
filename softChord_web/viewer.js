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
  var persistNote = document.getElementById("persist-note");
  var transposeDown = document.getElementById("transpose-down");
  var transposeUp = document.getElementById("transpose-up");
  var menu = document.getElementById("menu");
  var notice = document.getElementById("notice");
  var noticeTitle = document.getElementById("notice-title");
  var noticeMessage = document.getElementById("notice-message");

  // The .songbook next to this folder. A future server replaces Songbook.load.
  var songbookUrl = "../zvuki_neba.songbook";

  var allTitles = [];
  var loadError = null;
  var openId = null;
  var steps = 0;
  var menuSongId = null;

  function notify(title, message) {
    noticeTitle.textContent = title;
    noticeMessage.textContent = message;
    if (typeof notice.showModal === "function" && !notice.open) {
      notice.showModal();
    }
  }

  function copyText(text) {
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
  // approximation. Then pinch and Ctrl-scroll zoom, and Copy as image.
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
          chord.className = "chord";
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
      transposeDown.hidden = true;
      transposeUp.hidden = true;
      document.title = "softChord Viewer";
      return;
    }
    songError.hidden = true;
    transposeDown.hidden = false;
    transposeUp.hidden = false;
    songTitle.textContent = source.title;
    document.title = source.title;
    var chords = SongTranspose.shifted(source.chords, steps);
    paintSheet(SongText.sheet(source.text, chords));
    persistNote.hidden = steps === 0;
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

  // TODO: Open this menu on a long press, and add Copy as image once the
  // sheet uses the shared measurements.
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
    try {
      copyText(Songbook.songText(menuSongId, action.dataset.action === "chords"));
    } catch (error) {
      notify("Could not copy the song", String(error.message || error));
    }
  });

  document.addEventListener("click", function (event) {
    if (!menu.hidden && !menu.contains(event.target)) {
      menu.hidden = true;
    }
  });

  document.getElementById("back").addEventListener("click", function () {
    location.hash = "#/";
  });

  transposeDown.addEventListener("click", function () {
    steps -= 1;
    paintSong();
  });

  transposeUp.addEventListener("click", function () {
    steps += 1;
    paintSong();
  });

  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") {
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
