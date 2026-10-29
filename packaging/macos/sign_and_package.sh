#!/usr/bin/env bash
# Sign (if a Developer ID certificate is given), package as a DMG, and
# notarize (if Apple ID credentials are given) dist/softChord.app.
#
#   packaging/macos/sign_and_package.sh VERSION ARCH
#
# Writes dist/softChord-VERSION-macos-ARCH.dmg (softChord.app + Applications link).
#
# Optional environment (GitHub Actions secrets; NOTARY_PROFILE locally):
#   MACOS_CERT_P12       base64 of a .p12 with the "Developer ID Application" cert and key
#   MACOS_CERT_PASSWORD  password of that .p12
#   APPLE_ID             Apple ID email used for notarization
#   APPLE_APP_PASSWORD   app-specific password of that Apple ID
#   APPLE_TEAM_ID        Apple developer team ID (BP4KJ52H3T)
#   NOTARY_PROFILE       notarytool keychain profile instead of the three above
#   NOTARY_WAIT_SECONDS  how long to wait for Apple (default 600). If it is
#                        still pending, the DMG is kept signed but unstapled,
#                        with NAME.dmg.notarization-pending holding the
#                        submission ID, and the build only warns.
#
# Without the certificate the app keeps PyInstaller's ad-hoc signature and the
# DMG is unsigned: it works, but Gatekeeper asks the user to allow it. Without
# the Apple ID values the app is signed but not notarized. Both only warn.
set -euo pipefail

VER="${1:?usage: sign_and_package.sh VERSION ARCH}"
ARCH="${2:?usage: sign_and_package.sh VERSION ARCH}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
APP="$ROOT/dist/softChord.app"
DMG="$ROOT/dist/softChord-$VER-macos-$ARCH.dmg"
ENT="$ROOT/packaging/macos/entitlements.plist"
# shellcheck source=packaging/macos/notary.sh
. "$ROOT/packaging/macos/notary.sh"
WORK="$(mktemp -d)"
KC=""

warn() {
  if [ -n "${GITHUB_ACTIONS:-}" ]; then echo "::warning::$*"; else echo "WARNING: $*" >&2; fi
}

cleanup() {
  if [ -n "$KC" ]; then security delete-keychain "$KC" >/dev/null 2>&1 || true; fi
  rm -rf "$WORK"
}
trap cleanup EXIT

[ -d "$APP" ] || { echo "ERROR: $APP not found, build first" >&2; exit 1; }

IDENTITY=""
if [ -n "${MACOS_CERT_P12:-}" ] && [ -n "${MACOS_CERT_PASSWORD:-}" ]; then
  echo "Importing the signing certificate into a temporary keychain"
  KC="$WORK/softchord-signing.keychain-db"
  KC_PASS="$(uuidgen)"
  printf '%s' "$MACOS_CERT_P12" | base64 --decode > "$WORK/cert.p12"
  security create-keychain -p "$KC_PASS" "$KC"
  security set-keychain-settings -lut 3600 "$KC"
  security unlock-keychain -p "$KC_PASS" "$KC"
  security import "$WORK/cert.p12" -k "$KC" -f pkcs12 -P "$MACOS_CERT_PASSWORD" \
    -T /usr/bin/codesign -T /usr/bin/security >/dev/null
  rm -f "$WORK/cert.p12"
  security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k "$KC_PASS" "$KC" >/dev/null
  # Search the temp keychain first, keep the existing ones.
  # shellcheck disable=SC2046
  security list-keychains -d user -s "$KC" $(security list-keychains -d user | tr -d '"')
  IDENTITY="$(security find-identity -v -p codesigning "$KC" \
    | awk -F'"' '/Developer ID Application/ {print $2; exit}')"
  if [ -z "$IDENTITY" ]; then
    warn "MACOS_CERT_P12 has no valid \"Developer ID Application\" identity; shipping ad-hoc signed"
  fi
else
  warn "MACOS_CERT_P12/MACOS_CERT_PASSWORD not set; the app stays ad-hoc signed and is not notarized"
fi

if [ -n "$IDENTITY" ]; then
  echo "Signing with: $IDENTITY"
  sign() {
    codesign --force --timestamp --options runtime --entitlements "$ENT" \
      --sign "$IDENTITY" "$@"
  }
  # Inside out: every loose Mach-O file first (Python extensions, dylibs,
  # Qt plugins), then the frameworks, then the app itself.
  while IFS= read -r -d '' f; do
    if file -b "$f" | grep -q 'Mach-O'; then sign "$f"; fi
  done < <(find "$APP/Contents" -type f ! -path '*/MacOS/softChord' -print0)
  while IFS= read -r -d '' fw; do sign "$fw"; done \
    < <(find "$APP/Contents" -type d -name '*.framework' -print0)
  sign --deep "$APP"
  codesign --verify --deep --strict "$APP" && echo "codesign --verify: OK"
fi

echo "Creating $DMG"
STAGE="$WORK/dmg"
mkdir -p "$STAGE"
ditto "$APP" "$STAGE/softChord.app"
ln -s /Applications "$STAGE/Applications"
rm -f "$DMG"
hdiutil create -volname "softChord $VER" -srcfolder "$STAGE" -ov -format UDZO "$DMG"

PENDING="$DMG.notarization-pending"
rm -f "$PENDING"
if [ -n "$IDENTITY" ]; then
  codesign --force --timestamp --sign "$IDENTITY" "$DMG"
  if notary_available; then
    echo "Submitting for notarization"
    SUB_ID="$(notary_submit "$DMG")" || SUB_ID=""
    if [ -n "$SUB_ID" ]; then
      echo "Submission ID: $SUB_ID"
      STATUS="$(notary_poll "$SUB_ID" "${NOTARY_WAIT_SECONDS:-600}")"
    else
      STATUS="not submitted"
    fi
    case "$STATUS" in
      Accepted)
        xcrun stapler staple "$DMG"
        xcrun stapler validate "$DMG"
        ;;
      Invalid|Rejected)
        notary_fail_log "$SUB_ID"
        echo "ERROR: Apple rejected the DMG ($STATUS)" >&2
        exit 1
        ;;
      "not submitted")
        notary_warn "Could not submit $(basename "$DMG") for notarization; it is signed but not notarized"
        ;;
      *)
        # Signed but not stapled yet. It still opens without a warning once
        # Apple accepts it (Gatekeeper checks online). The staple workflow
        # (or tools/release.sh --staple) staples it later.
        echo "$SUB_ID" > "$PENDING"
        notary_warn "Notarization of $(basename "$DMG") still ${STATUS:-pending} (submission $SUB_ID). Run the Staple workflow later."
        ;;
    esac
  else
    notary_warn "APPLE_ID/APPLE_APP_PASSWORD/APPLE_TEAM_ID (or NOTARY_PROFILE) not set; the DMG is signed but not notarized"
  fi
fi

echo "Done: $DMG"
