// Web sign-in against a mocked API. The mock loads tests/api-contract.json
// (see auth_mock.js). No repository .songbook is read. Skipped when Chrome
// is not installed.

const test = require("node:test");
const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const helper = require("./browser_helper");
const auth = require("./auth_mock");

const skip = helper.skipUnlessBrowser();
const SONGS = [
  { title: "Short", text: "Hello world", chords: [[0, "C"]] },
  { title: "Other", text: "La la", chords: [[0, "D"]] },
];
const STUBS = [
  ["download", "Not available yet", "Saving songbooks from this app is coming in a later update."],
  ["rename", "Not available yet", "Renaming and deleting songbooks comes with softChord accounts in a later update."],
  ["delete", "Not available yet", "Renaming and deleting songbooks comes with softChord accounts in a later update."],
  ["share", "Sharing isn't available yet", "Sharing needs a softChord account, which is coming in a later update."],
];

function click(page, id) {
  return page.eval("document.getElementById('" + id + "').click()");
}

function titlesExpr() {
  return "Array.from(document.querySelectorAll('#song-list button')).map(function (b) { return b.textContent; })";
}

function callsExpr(path) {
  return "window.__auth.filter(function (call) { return call.url.indexOf(" + JSON.stringify(path) + ") !== -1; })";
}

async function openMenu(page) {
  await click(page, "songbook-menu-button");
  await page.waitFor("!document.getElementById('songbook-menu').hidden", "the songbook menu");
}

async function assertStubs(page) {
  for (var i = 0; i < STUBS.length; i++) {
    var item = STUBS[i];
    await openMenu(page);
    await page.eval("document.querySelector('#songbook-menu button[data-action=" + JSON.stringify(item[0]) + "]').click()");
    await page.waitFor("document.getElementById('notice').open", item[0]);
    assert.equal(await page.eval("document.getElementById('notice-title').textContent"), item[1]);
    assert.equal(await page.eval("document.getElementById('notice-message').textContent"), item[2]);
    await page.eval("document.querySelector('#notice button').click()");
    await page.waitFor("!document.getElementById('notice').open", "the message to close");
  }
}

async function waitForMe(page) {
  var path = auth.endpoint("me").path;
  await page.waitFor(callsExpr(path) + ".length > 0", "GET /api/me");
}

test("Sign in sends the email, then Check your email, and Resend posts again", { skip: skip }, async function () {
  var example = auth.webRequestExample();
  var link = auth.endpoint("request-link");
  var page = await helper.openViewer(SONGS, { html: auth.pageHtml() });
  try {
    await waitForMe(page);
    assert.equal(await page.eval("document.getElementById('sign-in').textContent"), "Sign in");
    assert.equal(await page.eval("document.getElementById('notice').open"), false);
    var titles = await page.eval(titlesExpr());
    await assertStubs(page);
    assert.equal((await page.eval(callsExpr(link.path))).length, 0, "the other account items do not request a link");

    await click(page, "sign-in");
    await page.waitFor("document.getElementById('sign-in-panel').open", "the email form");
    assert.equal(await page.eval("document.getElementById('sign-in-request').hidden"), false);
    assert.equal(await page.eval("document.getElementById('sign-in-check').hidden"), true);
    assert.equal(await page.eval("document.getElementById('notice').open"), false, "the form is not the not-available notice");
    await click(page, "sign-in-cancel");
    await page.waitFor("!document.getElementById('sign-in-panel').open", "cancel");
    assert.equal(await page.eval("document.getElementById('sign-in').textContent"), "Sign in");
    assert.equal((await page.eval(callsExpr(link.path))).length, 0, "cancel does not send");

    await click(page, "sign-in");
    await page.waitFor("document.getElementById('sign-in-panel').open", "the email form again");
    await page.eval("document.getElementById('sign-in-email').focus()");
    await page.insertText(example.email);
    await click(page, "sign-in-send");
    await page.waitFor("!document.getElementById('sign-in-check').hidden", "Check your email");
    assert.equal(await page.eval("document.getElementById('sign-in-check-title').textContent"), "Check your email");
    assert.equal(await page.eval("document.getElementById('sign-in-address').textContent"), example.email);
    assert.equal(await page.eval("document.getElementById('sign-in-resend').textContent"), "Resend");

    await click(page, "sign-in-resend");
    await page.waitFor(callsExpr(link.path) + ".length >= 2", "the resend");
    var calls = await page.eval(callsExpr(link.path));
    assert.equal(calls.length, 2);
    var verifiers = [];
    calls.forEach(function (call) {
      assert.equal(call.method, link.method);
      assert.equal(new URL(call.url).origin, auth.contract.publicOrigin);
      assert.equal(new URL(call.url).pathname, link.path);
      assert.equal(call.credentials, "include");
      assert.match(String(call.headers["content-type"] || ""), /application\/json/);
      assert.equal(call.headers.authorization, undefined);
      var body = JSON.parse(call.body);
      assert.deepEqual(Object.keys(body).sort(), Object.keys(example).sort());
      assert.equal(body.email, example.email);
      assert.equal(body.client, "web");
      assert.match(body.verifier, /^[A-Za-z0-9_-]{43,128}$/);
      assert.equal(crypto.createHash("sha256").update(body.verifier).digest("hex"), body.verifier_hash);
      verifiers.push(body.verifier);
    });
    assert.notEqual(verifiers[0], verifiers[1], "resend uses a new verifier");
    var me = (await page.eval(callsExpr(auth.endpoint("me").path)))[0];
    assert.equal(me.method, "GET");
    assert.equal(me.credentials, "include");
    assert.deepEqual(await page.eval(titlesExpr()), titles, "the open songbook stays");
    await click(page, "sign-in-check-cancel");
    await page.waitFor("!document.getElementById('sign-in-panel').open", "cancel after send");
    assert.equal(await page.eval("document.getElementById('sign-in').textContent"), "Sign in");
    assert.deepEqual(page.errors, []);
  } finally {
    await page.close();
  }
});

test("a signed-in /api/me shows the email and Sign out, and the other items stay unavailable", { skip: skip }, async function () {
  var email = auth.responseJson("GET", auth.endpoint("me").path, 200).email;
  var logout = auth.endpoint("logout");
  var page = await helper.openViewer(SONGS, { html: auth.pageHtml({ signedIn: true }) });
  try {
    await page.waitFor(
      "document.getElementById('sign-in').textContent === " + JSON.stringify(email),
      "the signed-in email");
    var place = await page.eval("(function () {" +
      "var sign = document.getElementById('sign-in').getBoundingClientRect();" +
      "return { text: document.getElementById('sign-in').textContent, right: sign.right, width: window.innerWidth," +
      "  menu: document.getElementById('sign-in').getAttribute('aria-haspopup') };" +
      "})()");
    assert.equal(place.text, email);
    assert.equal(place.menu, "menu");
    assert.ok(place.right <= place.width + 1, "the email stays on screen");
    var titles = await page.eval(titlesExpr());
    await assertStubs(page);
    assert.equal(await page.eval("document.getElementById('sign-in').textContent"), email, "the stubs leave the account signed in");

    await click(page, "sign-in");
    await page.waitFor("!document.getElementById('account-menu').hidden", "the account menu");
    assert.equal(await page.eval("document.getElementById('sign-out').textContent"), "Sign out (this device)");
    await click(page, "sign-out");
    await page.waitFor("document.getElementById('sign-in').textContent === 'Sign in'", "signed out");
    assert.equal(await page.eval("document.getElementById('account-menu').hidden"), true);
    var calls = await page.eval(callsExpr(logout.path));
    assert.equal(calls.length, 1);
    assert.equal(calls[0].method, logout.method);
    assert.equal(calls[0].credentials, "include");
    assert.equal(new URL(calls[0].url).origin, auth.contract.publicOrigin);
    assert.equal(new URL(calls[0].url).pathname, logout.path);
    assert.equal(calls[0].headers.authorization, undefined);
    assert.deepEqual(await page.eval(titlesExpr()), titles, "sign-out keeps the open songbook");
    assert.deepEqual(page.errors, []);
  } finally {
    await page.close();
  }
});

test("offline disables Sign in and shows Offline", { skip: skip }, async function () {
  var link = auth.endpoint("request-link");
  var page = await helper.openViewer(SONGS, { html: auth.pageHtml({ offline: true }) });
  try {
    await waitForMe(page);
    assert.equal(await page.eval("document.getElementById('sign-in').disabled"), true);
    assert.equal(await page.eval("document.getElementById('sign-in').textContent"), "Sign in");
    assert.equal(await page.eval("document.getElementById('sign-in-offline').hidden"), false);
    assert.equal(await page.eval("document.getElementById('sign-in-offline').textContent"), "Offline");
    await page.eval("document.getElementById('sign-in').click()");
    assert.equal(await page.eval("document.getElementById('sign-in-panel').open"), false);
    assert.equal(await page.eval("document.getElementById('notice').open"), false);
    assert.equal((await page.eval(callsExpr(link.path))).length, 0);

    await page.eval("window.__online = true; window.dispatchEvent(new Event('online'));");
    await page.waitFor("!document.getElementById('sign-in').disabled", "Sign in enabled online");
    assert.equal(await page.eval("document.getElementById('sign-in-offline').hidden"), true);
    assert.equal((await page.eval(callsExpr(link.path))).length, 0);
    assert.deepEqual(page.errors, []);
  } finally {
    await page.close();
  }
});

test("with no API origin, Sign in says the server is not configured and does not fetch", { skip: skip }, async function () {
  var page = await helper.openViewer(SONGS, { html: auth.pageHtml({ origin: "" }) });
  try {
    await page.waitFor("document.getElementById('sign-in').textContent === 'Sign in'", "the signed-out header");
    assert.deepEqual(await page.eval("window.__auth"), []);
    await click(page, "sign-in");
    await page.waitFor("document.getElementById('notice').open", "the not-configured notice");
    assert.equal(await page.eval("document.getElementById('notice-title').textContent"), "Sign-in isn't available yet");
    assert.equal(await page.eval("document.getElementById('notice-message').textContent"), "The server is not configured.");
    assert.equal(await page.eval("document.getElementById('sign-in-panel').open"), false);
    await page.eval("document.querySelector('#notice button').click()");
    await assertStubs(page);
    assert.deepEqual(await page.eval("window.__auth"), [], "no origin means no auth request");
    assert.deepEqual(await page.eval(titlesExpr()), ["Short", "Other"]);
    assert.deepEqual(page.errors, []);
  } finally {
    await page.close();
  }
});
