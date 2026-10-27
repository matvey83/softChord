// Drives the real web viewer in headless Chrome for tests (Chrome DevTools
// protocol over the WebSocket built into Node). Tests skip when Chrome is not
// installed: set CHROME_BIN to point at it.
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
    "--remote-debugging-port=0", "--user-data-dir=" + profile, "--window-size=1000,900", "about:blank",
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
    throw new Error("Chrome is not installed");
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
      fs.rmSync(profile, { recursive: true, force: true });
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

module.exports = { findChrome: findChrome, openViewer: openViewer };
