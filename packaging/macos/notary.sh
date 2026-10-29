# shellcheck shell=bash
# Notarization helpers, sourced by sign_and_package.sh and staple_release.sh.
#
# Credentials, first match wins:
#   NOTARY_PROFILE      a notarytool keychain profile (local Mac: softchord-notary)
#   APPLE_ID, APPLE_APP_PASSWORD, APPLE_TEAM_ID   (GitHub Actions secrets)
# Pending DMGs get a sidecar file NAME.dmg.notarization-pending holding the
# submission ID; staple_release.sh staples them once Apple accepts.

# (No arrays: macOS /bin/bash 3.2 treats an empty "${a[@]}" as unbound under set -u.)
_notary() {
  local cmd="$1"; shift
  if [ -n "${NOTARY_PROFILE:-}" ]; then
    xcrun notarytool "$cmd" "$@" --keychain-profile "$NOTARY_PROFILE"
  else
    xcrun notarytool "$cmd" "$@" --apple-id "$APPLE_ID" --password "$APPLE_APP_PASSWORD" \
      --team-id "$APPLE_TEAM_ID"
  fi
}

notary_available() {
  [ -n "${NOTARY_PROFILE:-}" ] ||
    { [ -n "${APPLE_ID:-}" ] && [ -n "${APPLE_APP_PASSWORD:-}" ] && [ -n "${APPLE_TEAM_ID:-}" ]; }
}

notary_warn() {
  if [ -n "${GITHUB_ACTIONS:-}" ]; then echo "::warning::$*"; else echo "WARNING: $*" >&2; fi
}

_json_field() { python3 -c 'import json,sys; print(json.load(sys.stdin).get(sys.argv[1], ""))' "$1"; }

# notary_submit FILE  -> prints the submission ID (retries the upload 3 times)
notary_submit() {
  local id="" try
  for try in 1 2 3; do
    id="$(_notary submit "$1" --output-format json \
      | _json_field id)" && [ -n "$id" ] && { echo "$id"; return 0; }
    echo "notarytool submit failed (try $try), retrying in 20s" >&2
    sleep 20
  done
  return 1
}

# notary_status ID  -> prints Accepted, In Progress, Invalid, Rejected or "" (network error)
notary_status() {
  _notary info "$1" --output-format json 2>/dev/null \
    | _json_field status || true
}

# notary_poll ID SECONDS -> prints the last status; stops early on a final one.
# Network errors only count as "not yet".
notary_poll() {
  local id="$1" deadline=$((SECONDS + $2)) st=""
  while :; do
    st="$(notary_status "$id")"
    case "$st" in Accepted|Invalid|Rejected) break ;; esac
    [ "$SECONDS" -ge "$deadline" ] && break
    echo "Notarization status: ${st:-unknown (network)}; checking again in 30s" >&2
    sleep 30
  done
  echo "$st"
}

# notary_fail_log ID: print Apple's log for a rejected submission.
notary_fail_log() {
  _notary log "$1" || true
}
