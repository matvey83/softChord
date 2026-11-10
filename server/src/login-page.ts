import { escapeHtml } from "./email.ts";
import type { ClientKind } from "./db.ts";

const FAILURE = "Open this link on the device where you requested it.";
const PASTE_HINT = "Paste this link into SoftChord if the button does not open the app.";

function tokenScript(): string {
  return `
    function tokenFromFragment() {
      var hash = window.location.hash;
      if (hash.charAt(0) === "#") hash = hash.slice(1);
      return new URLSearchParams(hash).get("t") || "";
    }
  `;
}

function signInScript(): string {
  return `
    ${tokenScript()}
    var errorEl = document.getElementById("form-error");
    document.getElementById("sign-in").addEventListener("click", function () {
      var token = tokenFromFragment();
      fetch("/api/auth/verify", {
        method: "POST",
        credentials: "same-origin",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ token: token })
      }).then(function (response) {
        if (response.ok) {
          document.getElementById("sign-in").hidden = true;
          document.getElementById("signed-in").hidden = false;
          return;
        }
        errorEl.hidden = false;
      }).catch(function () {
        errorEl.hidden = false;
      });
    });
  `;
}

function openAppScript(): string {
  return `
    ${tokenScript()}
    document.getElementById("open-app").addEventListener("click", function () {
      var token = tokenFromFragment();
      window.location.assign("softchord://login?token=" + encodeURIComponent(token));
    });
  `;
}

function appHref(value: string | undefined): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    if (url.protocol !== "https:" && url.protocol !== "http:") return null;
    return url.href;
  } catch {
    return null;
  }
}

function signedInMessage(appUrl: string | undefined): string {
  const href = appHref(appUrl);
  const back = href ? `<a href="${escapeHtml(href)}">Return to SoftChord.</a>` : "Return to SoftChord.";
  return `<p id="signed-in" hidden>You're signed in. ${back}</p>`;
}

export function renderLoginPage(client: ClientKind | null, hint: string, nonce: string, appUrl?: string): string {
  const native = client === "ios" || client === "desktop";
  const label = hint ? `Sign in as ${escapeHtml(hint)}` : "Sign in";
  const controls = native
    ? `<button type="button" id="open-app">Open in SoftChord</button>
    <p>${PASTE_HINT}</p>`
    : `<button type="button" id="sign-in">${label}</button>
    <p id="form-error" hidden>${FAILURE}</p>
    ${signedInMessage(appUrl)}`;
  const script = native ? openAppScript() : signInScript();
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="referrer" content="no-referrer">
  <title>Sign in to SoftChord</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 0; }
    main { max-width: 28rem; margin: 4rem auto; padding: 0 1.25rem; }
    button { font: inherit; margin: 0.5rem 0.5rem 0 0; padding: 0.5rem 0.8rem; }
    #form-error { color: #8a1f1f; }
  </style>
</head>
<body>
  <main>
    <h1>Sign in to SoftChord</h1>
    <p>This link signs in the device that asked for it.</p>
    ${controls}
  </main>
  <script nonce="${escapeHtml(nonce)}">${script}</script>
</body>
</html>
`;
}
