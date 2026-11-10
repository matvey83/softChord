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
      assert.equal(new URL(call.url).origin, page.origin);
      assert.equal(new URL(call.url).pathname, link.path);
      assert.equal(call.credentials, "include");
      assert.equal(call.headers["content-type"], "application/json");
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

    var mePath = auth.endpoint("me").path;
    var meBefore = await page.eval(callsExpr(mePath) + ".length");
    await page.eval("document.dispatchEvent(new Event('visibilitychange'))");
    await page.waitFor(callsExpr(mePath) + ".length > " + meBefore, "a visible page checks the session again");
    var meOnce = await page.eval(callsExpr(mePath) + ".length");
    await page.eval("document.dispatchEvent(new Event('visibilitychange')); window.dispatchEvent(new Event('focus'));");
    assert.equal(await page.eval(callsExpr(mePath) + ".length"), meOnce, "focus and visibility share one check per 5 seconds");
    await page.eval("(function () { var now = Date.now(); Date.now = function () { return now + 5000; }; })()");
    await page.eval("window.dispatchEvent(new Event('focus'))");
    await page.waitFor(callsExpr(mePath) + ".length > " + meOnce, "a focus 5 seconds later checks again");
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
    assert.equal(new URL(calls[0].url).origin, page.origin);
    assert.equal(new URL(calls[0].url).pathname, logout.path);
    assert.equal(calls[0].headers["content-type"], "application/json");
    assert.equal(calls[0].body, "{}");
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

test("an origin on another address shows the same-address notice and does not fetch", { skip: skip }, async function () {
  var page = await helper.openViewer(SONGS, { html: auth.pageHtml({ origin: auth.contract.publicOrigin }) });
  try {
    await page.waitFor("document.getElementById('sign-in').textContent === 'Sign in'", "the signed-out header");
    assert.notEqual(auth.contract.publicOrigin, page.origin);
    assert.deepEqual(await page.eval("window.__auth"), []);
    await click(page, "sign-in");
    await page.waitFor("document.getElementById('notice').open", "the same-address notice");
    assert.equal(await page.eval("document.getElementById('notice-title').textContent"), "Sign-in isn't available yet");
    assert.equal(await page.eval("document.getElementById('notice-message').textContent"), "The server must be on the same address as this page.");
    assert.equal(await page.eval("document.getElementById('sign-in-panel').open"), false);
    assert.deepEqual(await page.eval("window.__auth"), []);
    assert.deepEqual(page.errors, []);
  } finally {
    await page.close();
  }
});

test("a 400 sign-out says it was not accepted, and a 401 clears the signed-in header", { skip: skip }, async function () {
  var email = auth.responseJson("GET", "/api/me", 200).email;
  var page = await helper.openViewer(SONGS, { html: auth.pageHtml({ signedIn: true }) });
  try {
    await page.waitFor(
      "document.getElementById('sign-in').textContent === " + JSON.stringify(email),
      "the signed-in email");
    await page.eval("(function () {" +
      "var orig = window.fetch;" +
      "window.fetch = function (url, options) {" +
      "  var path = new URL(String(url), location.href).pathname;" +
      "  if (path === '/api/auth/logout' && window.__logoutStatus) {" +
      "    return Promise.resolve(new Response(JSON.stringify({ error: 'invalid_request' })," +
      "      { status: window.__logoutStatus, headers: { 'content-type': 'application/json' } }));" +
      "  }" +
      "  return orig.apply(this, arguments);" +
      "};" +
      "})()");
    await page.eval("window.__logoutStatus = 400");
    await click(page, "sign-in");
    await page.waitFor("!document.getElementById('account-menu').hidden", "the account menu");
    await click(page, "sign-out");
    await page.waitFor("document.getElementById('notice').open", "the sign-out error");
    assert.equal(await page.eval("document.getElementById('notice-title').textContent"), "Could not sign out");
    assert.equal(await page.eval("document.getElementById('notice-message').textContent"), "The sign-out request was not accepted.");
    assert.equal(await page.eval("document.getElementById('sign-in').textContent"), email, "a 400 leaves the account signed in");
    await page.eval("document.querySelector('#notice button').click()");
    await page.waitFor("!document.getElementById('notice').open", "the error to close");

    await page.eval("window.__logoutStatus = 500");
    await click(page, "sign-in");
    await page.waitFor("!document.getElementById('account-menu').hidden", "the account menu for a server error");
    await click(page, "sign-out");
    await page.waitFor("document.getElementById('notice').open", "the server-error notice");
    assert.equal(await page.eval("document.getElementById('notice-title').textContent"), "Could not sign out");
    assert.equal(await page.eval("document.getElementById('notice-message').textContent"), "The server had an error.");
    assert.equal(await page.eval("document.getElementById('sign-in').textContent"), email, "a 500 leaves the account signed in");
    await page.eval("document.querySelector('#notice button').click()");
    await page.waitFor("!document.getElementById('notice').open", "the server-error to close");

    await page.eval("window.__logoutStatus = 401");
    await click(page, "sign-in");
    await page.waitFor("!document.getElementById('account-menu').hidden", "the account menu again");
    await click(page, "sign-out");
    await page.waitFor("document.getElementById('sign-in').textContent === 'Sign in'", "401 clears the header");
    assert.equal(await page.eval("document.getElementById('notice').open"), false);
    assert.deepEqual(page.errors, []);
  } finally {
    await page.close();
  }
});

test("the mock accepts application/json with a charset, and rejects another type, a wrong method, and a foreign Origin", { skip: skip }, async function () {
  var logout = auth.endpoint("logout");
  var link = auth.endpoint("request-link");
  var page = await helper.openViewer(SONGS, { html: auth.pageHtml({ signedIn: true }) });
  try {
    await page.waitFor(
      "document.getElementById('sign-in').textContent === " + JSON.stringify(auth.responseJson("GET", "/api/me", 200).email),
      "the signed-in email");
    var result = await page.eval("(async function () {" +
      "var origin = location.origin;" +
      "async function call(path, options) {" +
      "  var response = await fetch(origin + path, options);" +
      "  return { status: response.status, body: await response.json() };" +
      "}" +
      "var missing = await call('/api/auth/logout', { method: 'POST', credentials: 'include', body: '{}' });" +
      "var other = await call('/api/auth/request-link', { method: 'POST', credentials: 'include', headers: { 'content-type': 'text/plain; charset=utf-8' }, body: '{}' });" +
      "var wrong = await call('/api/auth/logout', { method: 'GET', credentials: 'include' });" +
      "var foreign = await call('/api/auth/logout', { method: 'POST', credentials: 'include', headers: { 'content-type': 'application/json', origin: 'https://evil.example' }, body: '{}' });" +
      "var link = await call('/api/auth/request-link', { method: 'POST', credentials: 'include', headers: { 'content-type': 'application/json', origin: 'https://evil.example' }, body: '{}' });" +
      "var posted = await call('/api/me', { method: 'POST', credentials: 'include', headers: { 'content-type': 'application/json' }, body: '{}' });" +
      "var charset = await call('/api/auth/logout', { method: 'POST', credentials: 'include', headers: { 'content-type': 'application/json; charset=utf-8' }, body: '{}' });" +
      "return { missing: missing, charset: charset, other: other, wrong: wrong, foreign: foreign, link: link, posted: posted };" +
      "})()");
    assert.equal(result.missing.status, 400);
    assert.deepEqual(result.missing.body, auth.responseJson("POST", link.path, 400));
    assert.equal(result.charset.status, 200);
    assert.deepEqual(result.charset.body, auth.responseJson("POST", logout.path, 200));
    assert.equal(result.other.status, 400);
    assert.deepEqual(result.other.body, auth.responseJson("POST", link.path, 400));
    assert.equal(result.wrong.status, 405);
    assert.deepEqual(result.wrong.body, auth.responseJson("GET", logout.path, 405));
    assert.equal(result.foreign.status, 403);
    assert.deepEqual(result.foreign.body, auth.responseJson("POST", logout.path, 403));
    assert.equal(result.link.status, 403);
    assert.deepEqual(result.link.body, { error: "forbidden" });
    assert.equal(result.posted.status, 405);
    assert.deepEqual(result.posted.body, auth.responseJson("POST", "/api/me", 405));
    assert.equal(await page.eval("document.getElementById('sign-in').textContent"), auth.responseJson("GET", "/api/me", 200).email, "a rejected logout leaves the session");
    assert.deepEqual(page.errors, []);
  } finally {
    await page.close();
  }
});
