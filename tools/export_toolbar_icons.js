#!/usr/bin/env node
// Writes the song toolbar icons out of softChord_web/index.html, where they are
// drawn inline, into the files the other apps use:
//   softChord_web/icons/toolbar/<button id>.svg   (shared: iOS now, desktop later)
//   softChord Viewer/softChord Viewer/Assets.xcassets/Toolbar/<button id>.imageset
// MIRRORED UI: index.html is the source. Change an icon there, run
//   node tools/export_toolbar_icons.js
// and commit the files it writes. softChord_web/tests/toolbar_mirror.test.js
// fails while they differ.
"use strict";
var fs = require("fs");
var path = require("path");

var root = path.join(__dirname, "..");

// [id, svg body] for every icon button of the song toolbar, in toolbar order.
function toolbarIcons(html) {
  var out = [];
  var re = /<button id="([a-z-]+)" class="tool"[^>]*>\s*<svg viewBox="0 0 24 24"[^>]*>([\s\S]*?)<\/svg>/g;
  var m;
  while ((m = re.exec(html))) {
    out.push([m[1], m[2]]);
  }
  return out;
}

// A standalone file: the stroke style from viewer.css (.tool svg) is written on
// the root, black, so an asset catalog can tint it as a template.
function svgFile(body) {
  return '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" ' +
    'fill="none" stroke="#000000" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' +
    body + "</svg>\n";
}

function imagesetJson(id) {
  return JSON.stringify({
    images: [{ filename: id + ".svg", idiom: "universal" }],
    info: { author: "xcode", version: 1 },
    properties: { "preserves-vector-representation": true, "template-rendering-intent": "template" },
  }, null, 2) + "\n";
}

function expectedFiles() {
  var html = fs.readFileSync(path.join(root, "softChord_web", "index.html"), "utf8");
  var files = {};
  var catalog = path.join(root, "softChord Viewer", "softChord Viewer", "Assets.xcassets", "Toolbar");
  files[path.join(catalog, "Contents.json")] =
    JSON.stringify({ info: { author: "xcode", version: 1 } }, null, 2) + "\n";
  toolbarIcons(html).forEach(function (icon) {
    var svg = svgFile(icon[1]);
    files[path.join(root, "softChord_web", "icons", "toolbar", icon[0] + ".svg")] = svg;
    var set = path.join(catalog, icon[0] + ".imageset");
    files[path.join(set, icon[0] + ".svg")] = svg;
    files[path.join(set, "Contents.json")] = imagesetJson(icon[0]);
  });
  return files;
}

module.exports = { toolbarIcons: toolbarIcons, expectedFiles: expectedFiles };

if (require.main === module) {
  var files = expectedFiles();
  Object.keys(files).forEach(function (file) {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, files[file]);
  });
  console.log("wrote " + Object.keys(files).length + " files");
}
