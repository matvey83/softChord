// Source: server/api-contract.json at 42ca7c921a6d811dd80eb7fc533ede4e5964bb9d
// on branch cursor/magic-link-auth-server-c270 (Login PR 9, not merged).
// This file is a copy of that contract. Web auth mocks load it.
// JSON has no comments, so the source note lives here.
// Replace the file from that commit when the contract changes.

const fs = require("node:fs");
const path = require("node:path");

const contract = JSON.parse(fs.readFileSync(path.join(__dirname, "api-contract.json"), "utf8"));

function responseJson(method, requestPath, status) {
  var cases = contract.cases || [];
  for (var i = 0; i < cases.length; i++) {
    var steps = cases[i].steps || [];
    for (var j = 0; j < steps.length; j++) {
      var step = steps[j];
      var req = step.request || {};
      var res = step.response || {};
      var reqPath = String(req.path || "").split("?")[0];
      if (req.method === method && reqPath === requestPath && res.status === status && res.json) {
        return res.json;
      }
    }
  }
  return null;
}

function endpoint(id) {
  var endpoints = contract.endpoints || [];
  for (var i = 0; i < endpoints.length; i++) {
    if (endpoints[i].id === id) {
      return endpoints[i];
    }
  }
  throw new Error("contract has no endpoint " + id);
}

// The page mock has to be installed before viewer.js. openViewer applies this
// to index.html. Non-API fetches (the songbook, wasm) keep the real fetch.
// Omitting origin points the page at its own address. A string origin is
// installed as SOFTCHORD_API_ORIGIN. An empty origin leaves it unset.
function pageHtml(options) {
  options = options || {};
  var signedIn = !!options.signedIn;
  var offline = !!options.offline;
  var originSetup = "";
  if (!Object.prototype.hasOwnProperty.call(options, "origin")) {
    originSetup = "window.SOFTCHORD_API_ORIGIN = location.origin;";
  } else if (options.origin) {
    originSetup = "window.SOFTCHORD_API_ORIGIN = " + JSON.stringify(String(options.origin)) + ";";
  }
  var contractJson = JSON.stringify(contract).replace(/</g, "\\u003c");
  var script = [
    "<script>",
    "(function () {",
    originSetup,
    "window.__online = " + (offline ? "false" : "true") + ";",
    "try {",
    "  Object.defineProperty(navigator, 'onLine', { configurable: true, get: function () { return window.__online !== false; } });",
    "} catch (error) {}",
    "var contract = " + contractJson + ";",
    "var session = { signedIn: " + (signedIn ? "true" : "false") + " };",
    "window.__auth = [];",
    "function example(method, path, status) {",
    "  var cases = contract.cases || [];",
    "  for (var i = 0; i < cases.length; i++) {",
    "    var steps = cases[i].steps || [];",
    "    for (var j = 0; j < steps.length; j++) {",
    "      var step = steps[j];",
    "      var req = step.request || {};",
    "      var res = step.response || {};",
    "      var reqPath = String(req.path || '').split('?')[0];",
    "      if (req.method === method && reqPath === path && res.status === status && res.json) return res.json;",
    "    }",
    "  }",
    "  return null;",
    "}",
    "function endpointMethod(path) {",
    "  var endpoints = contract.endpoints || [];",
    "  for (var i = 0; i < endpoints.length; i++) {",
    "    if (endpoints[i].path === path) return endpoints[i].method;",
    "  }",
    "  return '';",
    "}",
    "var orig = window.fetch.bind(window);",
    "window.fetch = function (url, options) {",
    "  var href = typeof url === 'string' ? url : (url && url.url) || '';",
    "  var parsed = null;",
    "  try { parsed = new URL(href, location.href); } catch (error) { parsed = null; }",
    "  var path = parsed ? parsed.pathname : '';",
    "  if (path.indexOf('/api/') !== 0 && path !== '/login') return orig(url, options);",
    "  if (path === '/login' && ((options && options.method) || 'GET').toUpperCase() === 'GET') return orig(url, options);",
    "  var method = ((options && options.method) || 'GET').toUpperCase();",
    "  var headers = {};",
    "  var rawHeaders = options && options.headers;",
    "  if (rawHeaders && typeof rawHeaders.forEach === 'function') {",
    "    rawHeaders.forEach(function (value, key) { headers[String(key).toLowerCase()] = value; });",
    "  } else if (rawHeaders) {",
    "    Object.keys(rawHeaders).forEach(function (key) { headers[String(key).toLowerCase()] = rawHeaders[key]; });",
    "  }",
    "  var entry = { url: href, method: method, credentials: (options && options.credentials) || '', body: (options && options.body) || null, headers: headers };",
    "  window.__auth.push(entry);",
    "  var contentType = typeof headers['content-type'] === 'string' ? headers['content-type'].trim().toLowerCase() : '';",
    "  var sentOrigin = typeof headers.origin === 'string' && headers.origin ? headers.origin : location.origin;",
    "  var urlOrigin = parsed ? parsed.origin : '';",
    "  var expected = endpointMethod(path);",
    "  var status = 500;",
    "  var responseBody = null;",
    "  function reply(code, body) { status = code; responseBody = body; }",
    "  if (method === 'POST' && contentType !== 'application/json') {",
    "    reply(400, example('POST', '/api/auth/request-link', 400) || { error: 'invalid_request' });",
    "  } else if (expected && method !== expected) {",
    "    reply(405, example(method, path, 405) || { error: 'method_not_allowed' });",
    "  } else if (method === 'POST' && (path === '/api/auth/request-link' || path === '/api/auth/verify') && sentOrigin !== urlOrigin) {",
    "    reply(403, example('POST', path, 403) || { error: 'forbidden' });",
    "  } else if (method === 'GET' && path === '/api/me') {",
    "    reply(session.signedIn ? 200 : 401, example('GET', '/api/me', session.signedIn ? 200 : 401));",
    "  } else if (method === 'POST' && path === '/api/auth/request-link') {",
    "    reply(200, example('POST', '/api/auth/request-link', 200));",
    "  } else if (method === 'POST' && path === '/api/auth/logout') {",
    "    if (!session.signedIn) {",
    "      reply(401, example('POST', '/api/auth/logout', 401));",
    "    } else if (sentOrigin !== urlOrigin) {",
    "      reply(403, example('POST', '/api/auth/logout', 403));",
    "    } else {",
    "      reply(200, example('POST', '/api/auth/logout', 200));",
    "      session.signedIn = false;",
    "    }",
    "  }",
    "  if (!responseBody) return Promise.reject(new Error('contract has no ' + method + ' ' + path + ' ' + status));",
    "  entry.status = status;",
    "  return Promise.resolve(new Response(JSON.stringify(responseBody), { status: status, headers: { 'content-type': 'application/json' } }));",
    "};",
    "})();",
    "</script>",
  ].join("\n");
  return function (html) {
    return html.replace("<head>", "<head>\n" + script);
  };
}

function webRequestExample() {
  var cases = contract.cases || [];
  for (var i = 0; i < cases.length; i++) {
    var steps = cases[i].steps || [];
    for (var j = 0; j < steps.length; j++) {
      var json = steps[j].request && steps[j].request.json;
      if (json && json.client === "web" && json.verifier && json.verifier_hash) {
        return json;
      }
    }
  }
  throw new Error("contract has no web request-link body");
}

module.exports = {
  contract: contract,
  responseJson: responseJson,
  endpoint: endpoint,
  pageHtml: pageHtml,
  webRequestExample: webRequestExample,
};
