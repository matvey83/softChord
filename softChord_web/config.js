// API origin for sign-in. Leave this empty until this page and the API are
// served on the same address. Sign-in calls the origin only when it equals
// location.origin. Any other address is refused and no request is made.
// Set window.SOFTCHORD_API_ORIGIN before this file runs, or add
// <meta name="softchord-api-origin" content="..."> using this page's origin.
// This file does not replace a value that is already a string.
(function () {
  if (typeof window.SOFTCHORD_API_ORIGIN === "string") {
    return;
  }
  window.SOFTCHORD_API_ORIGIN = "";
})();
