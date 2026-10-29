const test = require("node:test");
const assert = require("node:assert/strict");

const helper = require("./browser_helper");

test("without Chrome the browser tests skip with a loud warning", function () {
  var printed = "";
  var reason = helper.skipReason(null, {}, function (text) { printed += text; });
  assert.equal(typeof reason, "string");
  assert.match(reason, /did NOT run/);
  assert.match(printed, /WARNING/);
  assert.match(printed, /SOFTCHORD_REQUIRE_BROWSER=1/);
});

test("with SOFTCHORD_REQUIRE_BROWSER=1 a missing Chrome is not skipped, so the tests fail", function () {
  var printed = "";
  assert.equal(helper.skipReason(null, { SOFTCHORD_REQUIRE_BROWSER: "1" }, function (text) { printed += text; }), false);
  assert.equal(printed, "", "nothing to warn about, the tests fail on their own");
  // Any other value does not count.
  assert.equal(typeof helper.skipReason(null, { SOFTCHORD_REQUIRE_BROWSER: "0" }, function () {}), "string");
});

test("with Chrome nothing is skipped and nothing is printed", function () {
  var printed = "";
  assert.equal(helper.skipReason("/usr/bin/chrome", {}, function (text) { printed += text; }), false);
  assert.equal(printed, "");
});
