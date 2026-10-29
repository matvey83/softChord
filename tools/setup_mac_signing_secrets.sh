#!/usr/bin/env bash
# Store the macOS signing and notarization secrets for GitHub Actions.
#
#   tools/setup_mac_signing_secrets.sh                 # export the cert from the login keychain
#   tools/setup_mac_signing_secrets.sh ~/DeveloperID.p12   # use a .p12 you exported
#
# Sets these repository secrets with gh secret set:
#   MACOS_CERT_P12, MACOS_CERT_PASSWORD, APPLE_ID, APPLE_APP_PASSWORD, APPLE_TEAM_ID
#
# Needs: the "Developer ID Application" certificate with its private key in
# your login keychain (or a .p12 of it), gh logged in with access to the repo,
# and an app-specific password from https://account.apple.com (Sign-In and
# Security → App-Specific Passwords). Passwords are read without echo and never
# printed; the temporary .p12 is deleted when the script ends.
set -euo pipefail

TEAM_ID_DEFAULT="BP4KJ52H3T"
cd "$(git rev-parse --show-toplevel)"
REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
die() { echo "ERROR: $*" >&2; exit 1; }

TMPD="$(mktemp -d)"
trap 'rm -rf "$TMPD"' EXIT
chmod 700 "$TMPD"

read -r -s -p "Password to protect the .p12 (a new one if exporting now): " P12_PASS; echo
[ -n "$P12_PASS" ] || die "the .p12 password cannot be empty"

if [ $# -ge 1 ]; then
  P12="$1"
  [ -f "$P12" ] || die "$P12 not found"
else
  echo "Developer ID Application identities in your keychains:"
  security find-identity -v -p codesigning | grep "Developer ID Application" \
    || die "no Developer ID Application certificate with a private key found"
  # security export writes every identity in the keychain, so only use it
  # when the login keychain holds just this one; otherwise export by hand.
  n="$(security find-identity -v login.keychain-db | grep -c '^ *[0-9]*)' || true)"
  if [ "$n" != 1 ]; then
    die "the login keychain has $n identities. Export only the Developer ID one:
  Keychain Access → login → My Certificates → right-click
  \"Developer ID Application: …\" → Export… → .p12, then run:
  tools/setup_mac_signing_secrets.sh /path/to/DeveloperID.p12"
  fi
  P12="$TMPD/cert.p12"
  echo "Exporting (macOS may ask to allow access to the key)"
  security export -k login.keychain-db -t identities -f pkcs12 -P "$P12_PASS" -o "$P12"
fi

# Check the password opens the file and it holds a Developer ID identity.
CHECK_KC="$TMPD/check.keychain-db"
security create-keychain -p check "$CHECK_KC"
security import "$P12" -k "$CHECK_KC" -f pkcs12 -P "$P12_PASS" >/dev/null \
  || { security delete-keychain "$CHECK_KC"; die "could not open the .p12 with that password"; }
security find-identity -v -p codesigning "$CHECK_KC" | grep -q "Developer ID Application" \
  || { security delete-keychain "$CHECK_KC"; die "the .p12 has no Developer ID Application identity"; }
security delete-keychain "$CHECK_KC"

read -r -p "Apple ID email for notarization: " APPLE_ID
read -r -s -p "App-specific password for that Apple ID: " APPLE_APP_PASSWORD; echo
read -r -p "Team ID [$TEAM_ID_DEFAULT]: " TEAM_ID
TEAM_ID="${TEAM_ID:-$TEAM_ID_DEFAULT}"

echo "Setting secrets on $REPO"
base64 -i "$P12" | tr -d '\n' | gh secret set MACOS_CERT_P12 -R "$REPO"
printf '%s' "$P12_PASS" | gh secret set MACOS_CERT_PASSWORD -R "$REPO"
printf '%s' "$APPLE_ID" | gh secret set APPLE_ID -R "$REPO"
printf '%s' "$APPLE_APP_PASSWORD" | gh secret set APPLE_APP_PASSWORD -R "$REPO"
printf '%s' "$TEAM_ID" | gh secret set APPLE_TEAM_ID -R "$REPO"
unset P12_PASS APPLE_APP_PASSWORD

echo "Done. Secrets on $REPO:"
gh secret list -R "$REPO"
echo "A user-exported .p12 passed as an argument was not deleted; remove it when done."
