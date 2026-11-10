// Source: server/api-contract.json on branch cursor/magic-link-auth-server-c270
// (Login PR 9, not merged). This file is a copy of that contract. Web auth
// mocks load it. JSON has no comments, so the source note lives here.
// Replace the file from that branch when the contract changes.

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
function pageHtml(options) {
  options = options || {};
  var origin = Object.prototype.hasOwnProperty.call(options, "origin")
    ? options.origin
    : contract.publicOrigin;
  var signedIn = !!options.signedIn;
  var offline = !!options.offline;
  var contractJson = JSON.stringify(contract).replace(/</g, "\\u003c");
  var meta = "";
  if (origin) {
    meta = '<meta name="softchord-api-origin" content="' + String(origin).replace(/"/g, "") + '">';
  }
  var script = [
    "<script>",
    "(function () {",
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
    "var orig = window.fetch.bind(window);",
    "window.fetch = function (url, options) {",
    "  var href = typeof url === 'string' ? url : (url && url.url) || '';",
    "  var parsed = null;",
    "  try { parsed = new URL(href, location.href); } catch (error) { parsed = null; }",
    "  var path = parsed ? parsed.pathname : '';",
    "  if (path.indexOf('/api/') !== 0) return orig(url, options);",
    "  var method = ((options && options.method) || 'GET').toUpperCase();",
    "  var headers = {};",
    "  var rawHeaders = options && options.headers;",
    "  if (rawHeaders && typeof rawHeaders.forEach === 'function') {",
    "    rawHeaders.forEach(function (value, key) { headers[String(key).toLowerCase()] = value; });",
    "  } else if (rawHeaders) {",
    "    Object.keys(rawHeaders).forEach(function (key) { headers[String(key).toLowerCase()] = rawHeaders[key]; });",
    "  }",
    "  window.__auth.push({ url: href, method: method, credentials: (options && options.credentials) || '', body: (options && options.body) || null, headers: headers });",
    "  var status = 500;",
    "  var responseBody = null;",
    "  if (method === 'GET' && path === '/api/me') {",
    "    status = session.signedIn ? 200 : 401;",
    "    responseBody = example('GET', '/api/me', status);",
    "  } else if (method === 'POST' && path === '/api/auth/request-link') {",
    "    status = 200;",
    "    responseBody = example('POST', '/api/auth/request-link', 200);",
    "  } else if (method === 'POST' && path === '/api/auth/logout') {",
    "    status = session.signedIn ? 200 : 401;",
    "    responseBody = example('POST', '/api/auth/logout', status);",
    "    if (status === 200) session.signedIn = false;",
    "  }",
    "  if (!responseBody) return Promise.reject(new Error('contract has no ' + method + ' ' + path + ' ' + status));",
    "  return Promise.resolve(new Response(JSON.stringify(responseBody), { status: status, headers: { 'content-type': 'application/json' } }));",
    "};",
    "})();",
    "</script>",
  ].join("\n");
  return function (html) {
    return html.replace("<head>", "<head>\n" + meta + "\n" + script);
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
