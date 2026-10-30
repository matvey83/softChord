// Drives the real web viewer in headless Chrome for tests (Chrome DevTools
// protocol over the WebSocket built into Node). Tests skip when Chrome is not
// installed, with a loud warning (see skipUnlessBrowser): set CHROME_BIN to point
// at it, or set SOFTCHORD_REQUIRE_BROWSER=1 to make them fail instead of skip.
//
// The page is served from a throw-away server. The songbook it opens is built in
// memory from the schema in src/songbook.sql. No repository .songbook is read.

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const http = require("node:http");
const { spawn } = require("node:child_process");
const initSqlJs = require("../sql-wasm.js");

const WEB_DIR = path.join(__dirname, "..");
const SCHEMA = path.join(WEB_DIR, "..", "src", "songbook.sql");

function findChrome() {
  var candidates = [
    process.env.CHROME_BIN,
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
  ];
  for (var i = 0; i < candidates.length; i++) {
    if (candidates[i] && fs.existsSync(candidates[i])) {
      return candidates[i];
    }
  }
  return null;
}

// songs: [{ title, text, chords: [[characterNum, "Am"], ...] }]
async function songbookBytes(songs) {
  var SQL = await initSqlJs({
    locateFile: function (file) { return path.join(WEB_DIR, file); },
  });
  var db = new SQL.Database();
  db.run(fs.readFileSync(SCHEMA, "utf8"));
  songs.forEach(function (song, index) {
    var id = index + 1;
    db.run("INSERT INTO songs (id, uuid, title, text, updated_at) VALUES (?, ?, ?, ?, 1700000000)",
      [id, "00000000-0000-4000-8000-" + String(id).padStart(12, "0"), song.title, song.text]);
    (song.chords || []).forEach(function (pair) {
      db.run("INSERT INTO song_chord_link (song_id, character_num, chord) VALUES (?, ?, ?)",
        [id, pair[0], pair[1]]);
    });
  });
  var bytes = db.export();
  db.close();
  return Buffer.from(bytes);
}

function startServer(songbook, transformHtml) {
  var types = {
    ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".wasm": "application/wasm",
  };
  var server = http.createServer(function (req, res) {
    var url = decodeURIComponent(req.url.split("?")[0]);
    if (url === "/zvuki_neba.songbook") {
      res.writeHead(200, { "content-type": "application/octet-stream" });
      res.end(songbook);
      return;
    }
    var rel = url.replace(/^\/softChord_web\//, "");
    var file = path.join(WEB_DIR, rel === "" ? "index.html" : rel);
    if (!url.startsWith("/softChord_web/") || !file.startsWith(WEB_DIR + path.sep) ||
        file.includes(path.sep + "tests" + path.sep) || !fs.existsSync(file)) {
      res.writeHead(404);
      res.end("not found");
      return;
    }
    res.writeHead(200, { "content-type": types[path.extname(file)] || "application/octet-stream" });
    var body = fs.readFileSync(file);
    if (transformHtml && path.basename(file) === "index.html") {
      body = Buffer.from(transformHtml(body.toString("utf8")));
    }
    res.end(body);
  });
  return new Promise(function (resolve) {
    server.listen(0, "127.0.0.1", function () { resolve(server); });
  });
}

function launchChrome(chrome, profile) {
  var child = spawn(chrome, [
    "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
    "--remote-debugging-port=0",
    // Headless Chrome has no mouse, so (hover: hover) would be false; this makes
    // it a browser with a mouse, as on a desktop (2 = hover, 4 = a fine pointer).
    "--blink-settings=primaryHoverType=2,availableHoverTypes=2,primaryPointerType=4,availablePointerTypes=4", "--user-data-dir=" + profile, "--window-size=1000,900", "about:blank",
  ], { stdio: ["ignore", "ignore", "pipe"] });
  return new Promise(function (resolve, reject) {
    var seen = "";
    var timer = setTimeout(function () { reject(new Error("Chrome did not start")); }, 20000);
    child.stderr.on("data", function (chunk) {
      seen += chunk;
      var match = /DevTools listening on (ws:\/\/[^\s]+)/.exec(seen);
      if (match) {
        clearTimeout(timer);
        resolve({ child: child, browserUrl: match[1] });
      }
    });
    child.on("exit", function () { reject(new Error("Chrome exited early: " + seen)); });
  });
}

function connect(url) {
  return new Promise(function (resolve, reject) {
    var ws = new WebSocket(url);
    var next = 1;
    var waiting = new Map();
    var client = {
      onEvent: null,
      send: function (method, params, sessionId) {
        return new Promise(function (ok, fail) {
          var id = next++;
          waiting.set(id, { ok: ok, fail: fail });
          var message = { id: id, method: method, params: params || {} };
          if (sessionId) { message.sessionId = sessionId; }
          ws.send(JSON.stringify(message));
        });
      },
      close: function () { ws.close(); },
    };
    ws.onmessage = function (event) {
      var message = JSON.parse(event.data);
      if (!message.id && client.onEvent) {
        client.onEvent(message);
      }
      if (message.id && waiting.has(message.id)) {
        var entry = waiting.get(message.id);
        waiting.delete(message.id);
        if (message.error) { entry.fail(new Error(message.error.message)); } else { entry.ok(message.result); }
      }
    };
    ws.onopen = function () { resolve(client); };
    ws.onerror = function () { reject(new Error("DevTools connection failed")); };
  });
}

// Opens the viewer on the given songs. Returns a page with eval(), pressKey(),
// printToPDF(), screenshot() and close(). Always call close().
async function openViewer(songs, options) {
  var chrome = findChrome();
  if (!chrome) {
    throw new Error("Chrome is not installed (set CHROME_BIN to its path)");
  }
  var viewport = (options && options.viewport) || { width: 1000, height: 900 };
  var server = await startServer(await songbookBytes(songs), options && options.html);
  var profile = fs.mkdtempSync(path.join(os.tmpdir(), "softchord-chrome-"));
  var launched = await launchChrome(chrome, profile);
  var client = await connect(launched.browserUrl);
  var target = await client.send("Target.createTarget", { url: "about:blank" });
  var attached = await client.send("Target.attachToTarget", { targetId: target.targetId, flatten: true });
  var session = attached.sessionId;
  function send(method, params) { return client.send(method, params, session); }
  await send("Page.enable");
  await send("Runtime.enable");
  await send("Emulation.setDeviceMetricsOverride", {
    width: viewport.width, height: viewport.height, deviceScaleFactor: 1, mobile: false,
  });
  // Uncaught errors in the page, so a test can say nothing threw.
  var errors = [];
  client.onEvent = function (message) {
    if (message.method === "Runtime.exceptionThrown") {
      var details = message.params.exceptionDetails;
      errors.push(details.exception && details.exception.description || details.text);
    }
  };
  var origin = "http://127.0.0.1:" + server.address().port;
  await send("Page.navigate", { url: origin + "/softChord_web/index.html" });

  var page = {
    origin: origin,
    errors: errors,
    send: send,
    // Runs an expression in the page. Promises are awaited. The value comes back as JSON.
    eval: async function (expression) {
      var result = await send("Runtime.evaluate", {
        expression: expression, awaitPromise: true, returnByValue: true,
      });
      if (result.exceptionDetails) {
        throw new Error("Page error: " + (result.exceptionDetails.exception &&
          result.exceptionDetails.exception.description || result.exceptionDetails.text));
      }
      return result.result.value;
    },
    // Polls until the expression is truthy.
    waitFor: async function (expression, what) {
      for (var i = 0; i < 100; i++) {
        if (await page.eval(expression)) { return; }
        await new Promise(function (r) { setTimeout(r, 100); });
      }
      throw new Error("Timed out waiting for " + (what || expression));
    },
    pressKey: async function (key) {
      var info = { key: key, code: key, windowsVirtualKeyCode: key === "Escape" ? 27 : 0 };
      await send("Input.dispatchKeyEvent", Object.assign({ type: "keyDown" }, info));
      await send("Input.dispatchKeyEvent", Object.assign({ type: "keyUp" }, info));
    },
    // Types text into the focused element like the keyboard or a paste would
    // (one input event, no key events).
    insertText: function (text) {
      return send("Input.insertText", { text: text });
    },
    // A key with a name the editor knows: Enter, Backspace, Delete, ArrowLeft,
    // ArrowRight, Home, End. Extra CDP options (modifiers, commands) can be added.
    key: async function (name, extra) {
      var codes = { Enter: 13, Backspace: 8, Delete: 46, ArrowLeft: 37, ArrowRight: 39,
        ArrowUp: 38, ArrowDown: 40, Home: 36, End: 35 };
      var info = Object.assign({
        key: name, code: name, windowsVirtualKeyCode: codes[name] || 0,
      }, name === "Enter" ? { text: "\r" } : {}, extra || {});
      await send("Input.dispatchKeyEvent", Object.assign({ type: info.text ? "keyDown" : "rawKeyDown" }, info));
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: info.key, code: info.code,
        windowsVirtualKeyCode: info.windowsVirtualKeyCode });
    },
    // A letter key as typed on a keyboard (keydown with text, so a keypress too).
    // With modifiers (1 Alt, 2 Ctrl, 4 Meta, 8 Shift) it is a shortcut: no text.
    type: async function (character, modifiers) {
      var upper = character.toUpperCase();
      var info = { key: character, code: "Key" + upper, windowsVirtualKeyCode: upper.charCodeAt(0),
        modifiers: modifiers || 0 };
      var shortcut = (info.modifiers & 7) !== 0;
      await send("Input.dispatchKeyEvent", Object.assign({ type: shortcut ? "rawKeyDown" : "keyDown" },
        info, shortcut ? {} : { text: character }));
      await send("Input.dispatchKeyEvent", Object.assign({ type: "keyUp" }, info));
    },
    // The mouse, in page (viewport) pixels. clickCount 2 is the second click of a double click.
    mouse: {
      move: function (x, y, buttons) {
        return send("Input.dispatchMouseEvent", { type: "mouseMoved", x: x, y: y, button: buttons ? "left" : "none",
          buttons: buttons || 0 });
      },
      down: function (x, y, clickCount) {
        return send("Input.dispatchMouseEvent", { type: "mousePressed", x: x, y: y, button: "left", buttons: 1,
          clickCount: clickCount || 1 });
      },
      up: function (x, y, clickCount) {
        return send("Input.dispatchMouseEvent", { type: "mouseReleased", x: x, y: y, button: "left", buttons: 0,
          clickCount: clickCount || 1 });
      },
      click: async function (x, y) {
        await page.mouse.move(x, y);
        await page.mouse.down(x, y);
        await page.mouse.up(x, y);
      },
      doubleClick: async function (x, y) {
        await page.mouse.move(x, y);
        await page.mouse.down(x, y, 1);
        await page.mouse.up(x, y, 1);
        await page.mouse.down(x, y, 2);
        await page.mouse.up(x, y, 2);
      },
      // Press at one point, move to the other in some steps, and let go unless release is false.
      drag: async function (from, to, options) {
        var steps = (options && options.steps) || 8;
        await page.mouse.move(from.x, from.y);
        await page.mouse.down(from.x, from.y);
        for (var i = 1; i <= steps; i++) {
          await page.mouse.move(from.x + (to.x - from.x) * i / steps, from.y + (to.y - from.y) * i / steps, 1);
        }
        if (!options || options.release !== false) {
          await page.mouse.up(to.x, to.y);
        }
      },
    },
    // One finger. The first call turns touch emulation on (pointerType "touch").
    touch: {
      send: async function (type, points) {
        await send("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 1 });
        return send("Input.dispatchTouchEvent", { type: type, touchPoints: points });
      },
      start: function (x, y) { return page.touch.send("touchStart", [{ x: x, y: y, id: 1 }]); },
      move: function (x, y) { return page.touch.send("touchMove", [{ x: x, y: y, id: 1 }]); },
      end: function () { return page.touch.send("touchEnd", []); },
      cancel: function () { return page.touch.send("touchCancel", []); },
      tap: async function (x, y) {
        await page.touch.start(x, y);
        await page.touch.end();
      },
      drag: async function (from, to, options) {
        var steps = (options && options.steps) || 8;
        await page.touch.start(from.x, from.y);
        for (var i = 1; i <= steps; i++) {
          await page.touch.move(from.x + (to.x - from.x) * i / steps, from.y + (to.y - from.y) * i / steps);
        }
        if (!options || options.release !== false) {
          await page.touch.end();
        }
      },
    },
    // The browser's own undo and redo, as Cmd/Ctrl+Z and Shift+Cmd/Ctrl+Z do.
    undo: function () {
      return page.key("z", { code: "KeyZ", windowsVirtualKeyCode: 90, commands: ["undo"] });
    },
    redo: function () {
      return page.key("z", { code: "KeyZ", windowsVirtualKeyCode: 90, commands: ["redo"] });
    },
    printToPDF: async function () {
      var result = await send("Page.printToPDF", { preferCSSPageSize: true, printBackground: true });
      return Buffer.from(result.data, "base64");
    },
    screenshot: async function () {
      var result = await send("Page.captureScreenshot", { format: "png" });
      return Buffer.from(result.data, "base64");
    },
    close: async function () {
      try { client.close(); } catch (error) { /* already closed */ }
      launched.child.kill("SIGKILL");
      server.close();
      server.closeAllConnections();
      // Chrome may still be writing into its profile for a moment after it is killed.
      fs.rmSync(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 });
    },
  };
  try {
    await page.waitFor("document.querySelectorAll('#song-list button').length > 0", "the song list");
  } catch (error) {
    await page.close();
    throw error;
  }
  return page;
}

// What the browser tests pass as { skip }. false when Chrome is there. Without it
// the browser tests do not run at all, which would look like a pass, so a warning is
// printed (to stderr, once per test file) and the skip reason says so. With
// SOFTCHORD_REQUIRE_BROWSER=1 (for a CI that must test the browser) nothing is
// skipped: the tests run and fail because Chrome is missing.
const MISSING = "Chrome is not installed (set CHROME_BIN), so the browser tests did NOT run";

function skipReason(chrome, env, warn) {
  if (chrome) {
    return false;
  }
  if (env.SOFTCHORD_REQUIRE_BROWSER === "1") {
    return false;
  }
  warn("\n!!! WARNING: " + MISSING + ".\n" +
    "!!! A green run does not cover the browser. Install Chrome or set CHROME_BIN,\n" +
    "!!! or set SOFTCHORD_REQUIRE_BROWSER=1 to make this a failure.\n\n");
  return MISSING;
}

function skipUnlessBrowser() {
  return skipReason(findChrome(), process.env, function (text) { process.stderr.write(text); });
}

module.exports = {
  findChrome: findChrome,
  openViewer: openViewer,
  skipReason: skipReason,
  skipUnlessBrowser: skipUnlessBrowser,
};
