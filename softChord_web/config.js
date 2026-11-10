// API origin for sign-in. Leave this empty until a server is configured.
// An empty value means Sign in does not call the network.
// Set a full origin here (for example http://127.0.0.1:8787 for wrangler dev),
// or set window.SOFTCHORD_API_ORIGIN before this file runs, or add
// <meta name="softchord-api-origin" content="https://...">.
// This file does not replace a value that is already a string.
(function () {
  if (typeof window.SOFTCHORD_API_ORIGIN === "string") {
    return;
  }
  window.SOFTCHORD_API_ORIGIN = "";
})();
