#!/usr/bin/env bash
# Start a desktop release:  tools/release.sh 1.2
#
# 1. Checks: on master, in sync with origin, no uncommitted changes in the
#    files the build uses, gh logged in, docs/release_notes/vVERSION.md exists,
#    the tag does not exist yet.
# 2. Sets __version__ in src/softchord_version.py and commits only that file
#    (skipped when it already says VERSION).
# 3. Pushes master, creates the draft GitHub release vVERSION with the notes
#    file, and pushes the tag. The tag push runs .github/workflows/build.yml,
#    which attaches the DMGs, the Windows zip and the exe to the draft.
# 4. You check the assets and publish the draft on GitHub.
#
# Other local changes (Xcode project, songbooks, logs) are left alone.
set -euo pipefail

VER="${1:?usage: tools/release.sh VERSION   (for example 1.2)}"
VER="${VER#v}"
TAG="v$VER"
cd "$(git rev-parse --show-toplevel)"

die() { echo "ERROR: $*" >&2; exit 1; }

[[ "$VER" =~ ^[0-9]+(\.[0-9]+){1,2}$ ]] || die "VERSION must look like 1.2 or 1.2.3"
command -v gh >/dev/null || die "gh (GitHub CLI) is not installed"
gh auth status >/dev/null 2>&1 || die "gh is not logged in (gh auth login)"

BUILD_PATHS=(src softchord.spec build_softChord.py requirements.txt requirements-build.txt
             packaging .github docs/release_notes)
[ "$(git rev-parse --abbrev-ref HEAD)" = master ] || die "not on master"
[ -z "$(git status --porcelain -- "${BUILD_PATHS[@]}")" ] \
  || { git status --short -- "${BUILD_PATHS[@]}"; die "uncommitted changes in files the build uses"; }
other="$(git status --porcelain --untracked-files=no)"
[ -z "$other" ] || { echo "Note: these local changes are not part of the release:"; echo "$other"; }

git fetch -q origin master --tags
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/master)" ] \
  || die "master and origin/master differ; pull or push first"
! git rev-parse -q --verify "refs/tags/$TAG" >/dev/null || die "tag $TAG already exists"
! gh release view "$TAG" >/dev/null 2>&1 || die "a GitHub release $TAG already exists"

NOTES="docs/release_notes/$TAG.md"
[ -f "$NOTES" ] || die "write $NOTES first (copy the previous one)"

VFILE=src/softchord_version.py
CUR="$(python3 build_softChord.py --version)"
if [ "$CUR" != "$VER" ]; then
  sed -i.bak -E "s/^__version__ = \".*\"/__version__ = \"$VER\"/" "$VFILE" && rm -f "$VFILE.bak"
  [ "$(python3 build_softChord.py --version)" = "$VER" ] || die "could not set the version in $VFILE"
  git add -- "$VFILE"
  git commit -q -m "Version $VER" -- "$VFILE"
  echo "Committed: Version $VER"
fi

echo "About to push master, create the draft release $TAG and push the tag."
read -r -p "Continue? [y/N] " ok
[ "$ok" = y ] || [ "$ok" = Y ] || die "stopped; nothing pushed (a version commit may be local)"

git push -q origin master
gh release create "$TAG" --draft --title "softChord $VER" --notes-file "$NOTES" --target master
git tag -a "$TAG" -m "softChord $VER"
git push -q origin "$TAG"

echo
echo "Started. Watch the build:  gh run watch \$(gh run list --workflow build.yml -L1 --json databaseId -q '.[0].databaseId')"
echo "Then check the assets and publish: gh release edit $TAG --draft=false   (or on github.com)"
