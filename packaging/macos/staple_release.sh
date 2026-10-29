#!/usr/bin/env bash
# Staple DMGs whose notarization was still pending when the build finished.
#
#   packaging/macos/staple_release.sh TAG        (for example v1.1)
#
# For every NAME.dmg.notarization-pending asset on the GitHub release TAG:
#   Accepted          download NAME.dmg, staple, re-upload it (--clobber) and
#                     delete the .notarization-pending asset
#   Invalid/Rejected  print Apple's log and fail
#   anything else     report it and leave it for the next run
# Needs gh (logged in, or GH_TOKEN) and notarization credentials: NOTARY_PROFILE
# (local, e.g. softchord-notary) or APPLE_ID, APPLE_APP_PASSWORD, APPLE_TEAM_ID.
set -euo pipefail

TAG="${1:?usage: staple_release.sh TAG}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=packaging/macos/notary.sh
. "$ROOT/packaging/macos/notary.sh"
notary_available || { echo "ERROR: no notarization credentials (NOTARY_PROFILE or APPLE_*)" >&2; exit 1; }

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

PENDING_ASSETS="$(gh release view "$TAG" --json assets -q '.assets[].name' | grep '\.notarization-pending$' || true)"
if [ -z "$PENDING_ASSETS" ]; then
  echo "No pending notarizations on $TAG"
  exit 0
fi

failed=0
waiting=0
for asset in $PENDING_ASSETS; do
  dmg="${asset%.notarization-pending}"
  gh release download "$TAG" -p "$asset" -D "$WORK" --clobber
  id="$(tr -d '[:space:]' < "$WORK/$asset")"
  st="$(notary_status "$id")"
  echo "$dmg: submission $id is ${st:-unknown (network error)}"
  case "$st" in
    Accepted)
      gh release download "$TAG" -p "$dmg" -D "$WORK" --clobber
      xcrun stapler staple "$WORK/$dmg"
      xcrun stapler validate "$WORK/$dmg"
      gh release upload "$TAG" "$WORK/$dmg" --clobber
      gh release delete-asset "$TAG" "$asset" -y
      echo "$dmg: stapled and re-uploaded"
      ;;
    Invalid|Rejected)
      notary_fail_log "$id"
      failed=1
      ;;
    *)
      waiting=1
      ;;
  esac
done

[ "$failed" = 0 ] || { echo "ERROR: Apple rejected at least one DMG (log above)" >&2; exit 1; }
[ "$waiting" = 0 ] || notary_warn "Some DMGs are still waiting for Apple; run this again later"
