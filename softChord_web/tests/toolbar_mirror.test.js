// MIRRORED UI: the iOS app draws the same song toolbar as index.html, with the
// same icons (exported by tools/export_toolbar_icons.js) and the same buttons in
// the same order (SongToolbar.swift). These checks fail when one app changes and
// the other does not.
"use strict";
var test = require("node:test");
var assert = require("node:assert");
var fs = require("fs");
var path = require("path");
var exporter = require("../../tools/export_toolbar_icons.js");

var root = path.join(__dirname, "..", "..");

test("the toolbar icon files match the icons drawn in index.html", function () {
  var files = exporter.expectedFiles();
  assert.ok(Object.keys(files).length > 40);
  Object.keys(files).forEach(function (file) {
    var rel = path.relative(root, file);
    assert.ok(fs.existsSync(file), rel + " is missing: run node tools/export_toolbar_icons.js");
    assert.equal(fs.readFileSync(file, "utf8"), files[file],
      rel + " differs from index.html: run node tools/export_toolbar_icons.js");
  });
});
