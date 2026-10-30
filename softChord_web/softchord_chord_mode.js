// Edit chords: the part of the page that deals with chords only. The song text
// stays as it is and chords are selected, moved, typed in and deleted on the sheet.
//
// viewer.js owns the draft ({text, chords, history, index}, the chords as stored,
// not transposed), the toolbar and Save and Discard, and gives this file what it
// needs through the host object of create(). The rules of what a move or an edit
// does to the chords are in softchord_chord_edit.js (SongChordEdit).
//
// host:
//   sheet, sheetWrap, sheetScroll    the sheet and the areas around it
//   buttons {edit, remove, undo, redo}  the chord buttons of the toolbar
//   live                              a status element read out by screen readers
//   entry {root, field, note, ok, cancel}  the chord entry (one text field)
//   draft()                           the draft while chords are edited, else null
//   steps()                           half steps the song is shown transposed by
//   repaint()                         paints the sheet again from the draft

(function (root) {
  function create(host) {
    var buttons = host.buttons;
    // The selected letter, as the code point where it starts (the data-song-char of
    // its box on the sheet), or null.
    var selected = null;

    function copyChords(chords) {
      return chords.map(function (chord) { return Object.assign({}, chord); });
    }

    function active() {
      return !!host.draft();
    }

    // The box of a letter on the sheet, from its number.
    function letterBox(letter) {
      return host.sheet.querySelector('.char[data-song-char="' + letter + '"]');
    }

    function announce(message) {
      host.live.textContent = "";
      // A changed text is what a screen reader reads out, so the same message
      // twice in a row still needs a change in between.
      host.live.textContent = message;
    }

    function chordOnSelection() {
      var d = host.draft();
      return d && selected !== null ? root.SongChordEdit.chordAt(d.chords, d.text, selected) : null;
    }

    // ---- Hit-testing ----
    // A chord is a child of the box of its letter, drawn above it, so a pointer on a
    // chord is on a chord element, and the viewer's CSS makes that element 6px
    // larger all round (the same slop as the iPhone app, in screen pixels at any
    // zoom). Chords of neighbouring letters can overlap (a long name over a short
    // word): the chord whose middle is nearest the pointer is the one.
    function chordAtPoint(x, y) {
      var found = null;
      var best = Infinity;
      document.elementsFromPoint(x, y).forEach(function (element) {
        if (!element.classList || !element.classList.contains("chord") || !host.sheet.contains(element)) {
          return;
        }
        var rect = element.getBoundingClientRect();
        var distance = Math.abs(x - (rect.left + rect.right) / 2);
        if (distance < best) {
          best = distance;
          found = element;
        }
      });
      return found;
    }

    // The letter under a point: its box, or null. The room above a line (where its
    // chords are) belongs to the letters of that line, so a point over a letter in
    // the chord band is on that letter. With clamp, a point left or right of the
    // line is on its first or last letter (a drag is not lost when the pointer
    // goes a little too far).
    function letterAtPoint(x, y, clamp) {
      var rows = host.sheet.children;
      for (var i = 0; i < rows.length; i++) {
        var rect = rows[i].getBoundingClientRect();
        var room = parseFloat(getComputedStyle(rows[i]).marginTop) || 0;
        if (y < rect.top - room) {
          return null;
        }
        if (y >= rect.bottom) {
          continue;
        }
        var boxes = rows[i].children;
        var first = null;
        var last = null;
        for (var b = 0; b < boxes.length; b++) {
          if (boxes[b].dataset.songChar === undefined) {
            continue;
          }
          var box = boxes[b].getBoundingClientRect();
          first = first || boxes[b];
          last = boxes[b];
          if (x >= box.left && x < box.right) {
            return boxes[b];
          }
        }
        if (!clamp || !first) {
          return null;
        }
        return x < first.getBoundingClientRect().left ? first : last;
      }
      return null;
    }

    // ---- Selection ----
    function lineNumber(box) {
      return Array.prototype.indexOf.call(host.sheet.children, box.parentNode) + 1;
    }

    function selectionMessage() {
      var box = selected === null ? null : letterBox(selected);
      if (!box) {
        return "Nothing selected";
      }
      var chord = box.querySelector(".chord");
      var letter = box.firstChild.textContent;
      var name = letter === " " ? "space" : letter === "\t" ? "tab" : letter;
      return "Line " + lineNumber(box) + ", letter " + name + ", " +
        (chord ? "chord " + chord.textContent : "no chord");
    }

    function applySelection() {
      Array.prototype.forEach.call(host.sheet.querySelectorAll(".char.selected"), function (box) {
        box.classList.remove("selected");
      });
      if (selected === null) {
        return;
      }
      var box = letterBox(selected);
      if (box) {
        box.classList.add("selected");
      } else {
        selected = null;
      }
    }

    // The letter number to select, or null for none.
    function select(letter, silently) {
      selected = letter;
      applySelection();
      updateButtons();
      if (!silently) {
        announce(selectionMessage());
      }
    }

    // Undo, Redo, and the buttons that need a selected letter or chord.
    // MIRRORED UI: the iOS toolbar (planned SongToolbar.swift) enables them the same way.
    function updateButtons() {
      var d = host.draft();
      buttons.undo.disabled = !d || d.index <= 0;
      buttons.redo.disabled = !d || d.index >= d.history.length - 1;
      var has = !!chordOnSelection();
      buttons.edit.disabled = !d || selected === null;
      buttons.edit.title = has ? "Edit chord" : "Add chord";
      buttons.edit.setAttribute("aria-label", buttons.edit.title);
      buttons.remove.disabled = !has;
    }

    // Keeps what the draft has now as one more step of Undo, and paints it.
    function commit(chords, message) {
      var d = host.draft();
      if (!d) {
        return;
      }
      d.chords = chords;
      d.index = root.SongTextEdit.pushSnapshot(d.history, d.index,
        { text: d.text, chords: copyChords(chords) });
      host.repaint();
      if (message) {
        announce(message);
      }
    }

    function goTo(index, message) {
      var d = host.draft();
      if (!d || index < 0 || index >= d.history.length) {
        return;
      }
      d.index = index;
      d.chords = copyChords(d.history[index].chords);
      host.repaint();
      announce(message);
    }

    function undo() {
      var d = host.draft();
      if (d) {
        goTo(d.index - 1, "Undone");
      }
    }

    function redo() {
      var d = host.draft();
      if (d) {
        goTo(d.index + 1, "Redone");
      }
    }

    function afterPaint() {
      markDragging();
      applySelection();
      updateButtons();
    }

    function enter() {
      selected = null;
      applySelection();
      updateButtons();
    }

    function leave() {
      closeEntry(false);
      cancelDrag();
      press = null;
      selected = null;
      host.live.textContent = "";
      updateButtons();
    }

    // ---- Pointer ----
    // A press on a chord can be a drag from the first pixel, with no step of
    // selecting first. It is a drag once the pointer is 4px away from where it went
    // down (the iPhone app has 6 on its larger screens; a mouse is steadier). Until
    // then it is a press that selects.
    var DRAG_SLOP = 4;
    var EDGE = 32;
    var press = null;
    var drag = null;
    var scroller = null;

    function pointerLetter(drag, x, y) {
      // The chord is dragged by where the pointer took hold of it, not by its middle.
      var box = letterAtPoint(x - drag.grabX, y, true);
      return box ? Number(box.dataset.songChar) : null;
    }

    // Moves the chord to where the pointer is, live: the draft has the chords as
    // they are now, and one Undo step is made only when the pointer lets go.
    function dragTo(x, y) {
      var d = host.draft();
      var target = pointerLetter(drag, x, y);
      if (!d || target === null) {
        return;
      }
      var step = root.SongChordEdit.draggedChord(d.chords, d.text, drag.chordAt, drag.finger, target);
      if (!step) {
        return;
      }
      drag.finger = step.finger;
      if (step.chords !== d.chords) {
        d.chords = step.chords;
        drag.chordAt = step.chordAt;
        selected = step.chordAt;
        host.repaint();
      }
    }

    function markDragging() {
      Array.prototype.forEach.call(host.sheet.querySelectorAll(".chord.dragging"), function (chord) {
        chord.classList.remove("dragging");
      });
      if (drag && drag.active) {
        var box = letterBox(drag.chordAt);
        var chord = box && box.querySelector(".chord");
        if (chord) {
          chord.classList.add("dragging");
        }
      }
    }

    function stopDrag() {
      if (scroller) {
        clearInterval(scroller);
        scroller = null;
      }
      if (drag && host.sheetScroll.hasPointerCapture && host.sheetScroll.hasPointerCapture(drag.pointerId)) {
        host.sheetScroll.releasePointerCapture(drag.pointerId);
      }
      host.sheetWrap.classList.remove("dragging");
      drag = null;
      markDragging();
    }

    // Esc, a cancelled pointer or leaving the mode: the chord goes back where it was.
    function cancelDrag() {
      if (!drag) {
        return false;
      }
      var was = drag;
      var d = host.draft();
      stopDrag();
      if (was.active && d) {
        d.chords = copyChords(was.startChords);
        selected = was.letter;
        host.repaint();
        announce("Move cancelled");
      }
      return was.active;
    }

    function finishDrag() {
      var d = host.draft();
      var was = drag;
      stopDrag();
      if (!was.active || !d) {
        return;
      }
      var same = JSON.stringify(d.chords) === JSON.stringify(was.startChords);
      if (same) {
        selected = was.letter;
        applySelection();
        updateButtons();
        return;
      }
      commit(d.chords);
      select(was.chordAt, true);
      var box = letterBox(was.chordAt);
      announce("Moved chord " + box.querySelector(".chord").textContent + " to line " + lineNumber(box) +
        ", letter " + (box.firstChild.textContent === " " ? "space" : box.firstChild.textContent));
    }

    // While the pointer waits near the top or the bottom edge the sheet scrolls, and
    // the chord follows the letter that comes under the pointer.
    function startScroller() {
      scroller = setInterval(function () {
        if (!drag || !drag.active) {
          return;
        }
        var rect = host.sheetScroll.getBoundingClientRect();
        var speed = drag.y < rect.top + EDGE ? -Math.ceil((rect.top + EDGE - drag.y) / 3) :
          drag.y > rect.bottom - EDGE ? Math.ceil((drag.y - (rect.bottom - EDGE)) / 3) : 0;
        if (speed) {
          var before = host.sheetScroll.scrollTop;
          host.sheetScroll.scrollTop = before + Math.max(-30, Math.min(30, speed));
          if (host.sheetScroll.scrollTop !== before) {
            dragTo(drag.x, drag.y);
          }
        }
      }, 30);
    }

    host.sheetScroll.addEventListener("pointerdown", function (event) {
      if (!active() || (event.pointerType === "mouse" && event.button !== 0)) {
        return;
      }
      cancelDrag();
      var chord = chordAtPoint(event.clientX, event.clientY);
      var box = chord ? chord.parentNode : letterAtPoint(event.clientX, event.clientY, false);
      var letter = box ? Number(box.dataset.songChar) : null;
      press = {
        pointerId: event.pointerId,
        type: event.pointerType,
        letter: letter,
        onChord: !!chord,
        wasSelected: letter !== null && letter === selected,
      };
      select(letter);
      host.sheet.focus({ preventScroll: true });
      if (chord) {
        var rect = chord.getBoundingClientRect();
        drag = {
          pointerId: event.pointerId,
          letter: letter,
          chordAt: letter,
          finger: letter,
          startX: event.clientX,
          startY: event.clientY,
          x: event.clientX,
          y: event.clientY,
          grabX: event.clientX - (rect.left + rect.right) / 2,
          active: false,
          startChords: copyChords(host.draft().chords),
        };
        // The repaint of a move replaces boxes of the sheet, and the stream of the
        // pointer must not end with one: this element is never replaced.
        try { host.sheetScroll.setPointerCapture(event.pointerId); } catch (error) { /* gone already */ }
        if (event.pointerType === "mouse") {
          event.preventDefault();
        }
      }
    });

    host.sheetScroll.addEventListener("pointermove", function (event) {
      if (!drag || drag.pointerId !== event.pointerId) {
        return;
      }
      drag.x = event.clientX;
      drag.y = event.clientY;
      if (!drag.active) {
        if (Math.hypot(drag.x - drag.startX, drag.y - drag.startY) < DRAG_SLOP) {
          return;
        }
        drag.active = true;
        host.sheetWrap.classList.add("dragging");
        markDragging();
        startScroller();
      }
      dragTo(drag.x, drag.y);
    });

    host.sheetScroll.addEventListener("pointerup", function (event) {
      var dragged = false;
      if (drag && drag.pointerId === event.pointerId) {
        dragged = drag.active;
        finishDrag();
      }
      if (press && press.pointerId === event.pointerId) {
        // A second tap of a finger on the selected letter is the double click of a
        // mouse: the chord entry.
        var again = !dragged && press.type !== "mouse" && press.wasSelected && press.letter !== null;
        press = null;
        if (again) {
          openEntry();
        }
      }
    });

    host.sheetScroll.addEventListener("dblclick", function (event) {
      if (!active()) {
        return;
      }
      var chord = chordAtPoint(event.clientX, event.clientY);
      var box = chord ? chord.parentNode : letterAtPoint(event.clientX, event.clientY, false);
      if (box) {
        if (Number(box.dataset.songChar) !== selected) {
          select(Number(box.dataset.songChar));
        }
        openEntry();
      }
    });

    host.sheetScroll.addEventListener("pointercancel", function (event) {
      if (drag && drag.pointerId === event.pointerId) {
        cancelDrag();
      }
      if (press && press.pointerId === event.pointerId) {
        press = null;
      }
    });

    // ---- Keyboard ----
    // With the sheet focused. Letters A to G put that chord on the selected letter
    // (major, replacing what is there), m toggles minor, Left and Right move the
    // chord along its line (with no chord there they do nothing; Up and Down do
    // nothing either), Delete and Backspace remove it, Cmd/Ctrl+Z and Shift+Cmd/Ctrl+Z undo and redo. Escape
    // cancels a move in progress, else clears the selection. Escape never leaves the
    // mode: Save or Discard does. Shortcuts of the browser (Cmd+R and the like) are
    // left alone: only Z with Ctrl or Meta is taken.
    function edit(chords, prefix) {
      commit(chords);
      applySelection();
      updateButtons();
      announce(prefix + ", " + selectionMessage());
    }

    // The chord as typed on the selected letter. The same chord again is not a step.
    function setChord(typed) {
      var d = host.draft();
      var had = chordOnSelection();
      var next = root.SongChordEdit.replaced(d.chords, d.text, selected, typed, host.steps());
      if (JSON.stringify(next) !== JSON.stringify(d.chords)) {
        edit(next, had ? "Replaced" : "Added");
      }
    }

    // ---- Chord entry ----
    // One text field for the chord, in a popover under the letter (a sheet at the
    // bottom of a narrow window). It starts with the chord as it is shown, or C for
    // a letter with none, all selected. The field is red and OK waits while the text
    // is not a chord, and the footer says what it will be shown as. Enter is OK, Esc
    // or a press elsewhere is Cancel. Nothing changes in the song until OK.
    var entry = host.entry;
    var entryLetter = null;

    function entryIsOpen() {
      return entryLetter !== null;
    }

    function validateEntry() {
      var result = root.SongChordEdit.entry(entry.field.value);
      entry.field.classList.toggle("invalid", result.showsRed);
      entry.field.setAttribute("aria-invalid", result.showsRed ? "true" : "false");
      entry.note.textContent = result.footer;
      entry.ok.disabled = !result.isValid;
      return result.isValid;
    }

    function narrow() {
      return window.matchMedia("(max-width: 760px)").matches;
    }

    function placeEntry() {
      if (!entryIsOpen()) {
        return;
      }
      var box = letterBox(entryLetter);
      if (!box) {
        return;
      }
      var vv = window.visualViewport;
      entry.root.style.setProperty("--keyboard",
        vv ? Math.max(0, window.innerHeight - vv.height - vv.offsetTop) + "px" : "0px");
      var rect = box.getBoundingClientRect();
      if (narrow()) {
        entry.root.style.left = "";
        entry.root.style.top = "";
        var top = entry.root.getBoundingClientRect().top;
        if (rect.bottom + 8 > top) {
          host.sheetScroll.scrollTop += rect.bottom + 8 - top;
        }
        return;
      }
      var width = entry.root.offsetWidth;
      var height = entry.root.offsetHeight;
      var left = Math.max(8, Math.min(rect.left + rect.width / 2 - width / 2, window.innerWidth - width - 8));
      var below = rect.bottom + 8;
      var y = below + height + 8 <= window.innerHeight ? below : Math.max(8, rect.top - 8 - height);
      entry.root.style.left = left + "px";
      entry.root.style.top = y + "px";
    }

    function openEntry() {
      var d = host.draft();
      if (!d || selected === null) {
        return;
      }
      if (entryLetter === selected) {
        entry.field.focus();
        return;
      }
      cancelDrag();
      var shown = root.SongChordEdit.displayedChordText(d.text, d.chords, selected, host.steps());
      entryLetter = selected;
      entry.field.value = shown || "C";
      validateEntry();
      entry.root.hidden = false;
      host.sheetWrap.classList.add("entry-open");
      var box = letterBox(selected);
      if (box && box.scrollIntoView) {
        box.scrollIntoView({ block: "nearest", inline: "nearest" });
      }
      placeEntry();
      entry.field.focus();
      entry.field.select();
    }

    function closeEntry(focusSheet) {
      if (!entryIsOpen()) {
        return;
      }
      entryLetter = null;
      entry.root.hidden = true;
      host.sheetWrap.classList.remove("entry-open");
      if (focusSheet) {
        host.sheet.focus({ preventScroll: true });
      }
    }

    function acceptEntry() {
      if (!entryIsOpen() || !validateEntry()) {
        return;
      }
      var typed = entry.field.value;
      var letter = entryLetter;
      closeEntry(true);
      selected = letter;
      setChord(typed);
    }

    entry.field.addEventListener("input", validateEntry);
    entry.field.addEventListener("keydown", function (event) {
      if (event.isComposing) {
        return;
      }
      if (event.key === "Enter") {
        event.preventDefault();
        acceptEntry();
      } else if (event.key === "Escape") {
        event.preventDefault();
        closeEntry(true);
      }
    });
    entry.ok.addEventListener("click", acceptEntry);
    entry.cancel.addEventListener("click", function () { closeEntry(true); });
    // A press anywhere else cancels, and goes on to do what it was for.
    document.addEventListener("pointerdown", function (event) {
      if (entryIsOpen() && !entry.root.contains(event.target)) {
        closeEntry(false);
      }
    }, true);
    window.addEventListener("resize", placeEntry);
    host.sheetScroll.addEventListener("scroll", placeEntry);
    if (window.visualViewport) {
      window.visualViewport.addEventListener("resize", placeEntry);
      window.visualViewport.addEventListener("scroll", placeEntry);
    }

    function toggleMinor() {
      var d = host.draft();
      var next = root.SongChordEdit.toggledMinor(d.chords, d.text, selected);
      if (next) {
        edit(next, "Changed");
      }
    }

    function removeChord() {
      var d = host.draft();
      if (d && selected !== null && chordOnSelection()) {
        edit(root.SongChordEdit.deleted(d.chords, d.text, selected), "Deleted");
      }
    }

    function nudge(direction) {
      var d = host.draft();
      var step = root.SongChordEdit.nudged(d.chords, d.text, selected, direction);
      if (!step) {
        announce("The chord cannot move " + (direction < 0 ? "left" : "right") + " from here");
        return;
      }
      selected = step.chordAt;
      edit(step.chords, "Moved");
    }

    host.sheet.addEventListener("keydown", function (event) {
      if (!active() || event.isComposing) {
        return;
      }
      if (event.key === "Escape") {
        if (!cancelDrag() && selected !== null) {
          select(null);
        }
        return;
      }
      if (drag && drag.active) {
        // The pointer is moving a chord: only Escape does anything meanwhile.
        event.preventDefault();
        return;
      }
      var key = event.key;
      var handled = false;
      if (event.ctrlKey || event.metaKey) {
        if (!event.altKey && (key === "z" || key === "Z")) {
          if (event.shiftKey) {
            redo();
          } else {
            undo();
          }
          handled = true;
        } else if (!event.altKey && !event.metaKey && (key === "y" || key === "Y")) {
          redo();
          handled = true;
        }
      } else if (!event.altKey && selected !== null) {
        if (/^[a-gA-G]$/.test(key)) {
          setChord(key.toUpperCase());
          handled = true;
        } else if (key === "m" || key === "M") {
          toggleMinor();
          handled = true;
        } else if (key === "Enter" || key === "F2") {
          openEntry();
          handled = true;
        } else if (key === "Delete" || key === "Backspace") {
          removeChord();
          handled = true;
        } else if ((key === "ArrowLeft" || key === "ArrowRight") && chordOnSelection()) {
          // With no chord on the letter the arrows (and Up and Down always) are left
          // to the browser, which scrolls the page.
          nudge(key === "ArrowLeft" ? -1 : 1);
          handled = true;
        }
      }
      if (handled) {
        event.preventDefault();
      }
    });

    buttons.edit.addEventListener("click", openEntry);

    buttons.remove.addEventListener("click", function () {
      removeChord();
      host.sheet.focus({ preventScroll: true });
    });

    // The keyboard goes on working after a click on the toolbar.
    buttons.undo.addEventListener("click", function () {
      undo();
      host.sheet.focus({ preventScroll: true });
    });
    buttons.redo.addEventListener("click", function () {
      redo();
      host.sheet.focus({ preventScroll: true });
    });

    return {
      enter: enter,
      leave: leave,
      afterPaint: afterPaint,
      commit: commit,
      undo: undo,
      redo: redo,
      announce: announce,
      select: select,
      selected: function () { return selected; },
      chordAtPoint: chordAtPoint,
      letterAtPoint: letterAtPoint,
      updateButtons: updateButtons,
    };
  }

  root.SongChordMode = { create: create };
})(typeof globalThis !== "undefined" ? globalThis : this);
