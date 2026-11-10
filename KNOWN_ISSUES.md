# Known issues

- Desktop: Undo cannot cross a Save. Save drops the draft's undo steps (by design).
- Login: There is no SoftChord domain or Cloudflare account yet. `server/wrangler.jsonc` uses placeholder D1 id `11111111-1111-4111-8111-111111111111` and rate-limit namespace `1001` for local dev only. The production origin, a real D1 id, and a real rate-limit namespace need the account owner before any deploy.
- Login: The per-IP burst is 10 requests per 60 seconds, because the Workers Rate Limiting binding only allows a 10- or 60-second window. Say if that burst should be different before launch.
- Login: The web session cookie lasts 400 days, and the server session lasts until sign-out. Say if sign-in on the web should expire sooner.
