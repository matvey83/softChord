#!/usr/bin/env bash
# Turn the PyInstaller one-file build dist/softChord into the Linux release
# files:
#   dist/softChord-VER-linux-ARCH.AppImage
#   dist/softChord-VER-linux-ARCH.tar.gz   (softChord-VER-linux-ARCH/softChord)
#
# Usage: packaging/linux/package.sh VER [ARCH]    (ARCH defaults to x86_64)
#
# appimagetool and the AppImage runtime are downloaded at pinned releases and
# checked against their SHA-256. They run with APPIMAGE_EXTRACT_AND_RUN=1, so
# no FUSE is needed (CI runners and containers).
set -euo pipefail

VER="${1:?usage: package.sh VER [ARCH]}"
ARCH="${2:-x86_64}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HERE="$ROOT/packaging/linux"
DIST="$ROOT/dist"
EXE="$DIST/softChord"
NAME="softChord-$VER-linux-$ARCH"
DESKTOP_ID="com.matvey83.softchord"

TOOL_VER="1.9.1"          # https://github.com/AppImage/appimagetool/releases
RUNTIME_VER="20251108"    # https://github.com/AppImage/type2-runtime/releases
case "$ARCH" in
  x86_64)
    TOOL_SHA="ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0"
    RUNTIME_SHA="2fca8b443c92510f1483a883f60061ad09b46b978b2631c807cd873a47ec260d"
    ;;
  *)
    echo "ERROR: no pinned appimagetool for $ARCH (add its SHA-256 here)" >&2
    exit 1
    ;;
esac

command -v file >/dev/null || { echo "ERROR: appimagetool needs the file command (apt install file)" >&2; exit 1; }
[ -x "$EXE" ] || { echo "ERROR: $EXE missing: run build_softChord.py first" >&2; exit 1; }

WORK="$ROOT/build/linux-package"
rm -rf "$WORK"
mkdir -p "$WORK/tools"

fetch() {  # url file sha256
  curl -fsSL --retry 3 -o "$2" "$1"
  echo "$3  $2" | sha256sum -c -
}
TOOL="$WORK/tools/appimagetool-$ARCH.AppImage"
RUNTIME="$WORK/tools/runtime-$ARCH"
fetch "https://github.com/AppImage/appimagetool/releases/download/$TOOL_VER/appimagetool-$ARCH.AppImage" "$TOOL" "$TOOL_SHA"
fetch "https://github.com/AppImage/type2-runtime/releases/download/$RUNTIME_VER/runtime-$ARCH" "$RUNTIME" "$RUNTIME_SHA"
chmod +x "$TOOL"

# The AppDir: AppRun starts the one-file executable. The .desktop file and the
# icon at the top are what appimagetool needs; usr/share has them for desktop
# integration tools. The app itself registers them in ~/.local/share on launch
# (register_linux_file_association in src/softchord.py).
APPDIR="$WORK/softChord.AppDir"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/applications" \
  "$APPDIR/usr/share/icons/hicolor/256x256/apps" "$APPDIR/usr/share/mime/packages"
install -m 755 "$EXE" "$APPDIR/usr/bin/softChord"
cat > "$APPDIR/AppRun" <<'APPRUN'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/softChord" "$@"
APPRUN
chmod 755 "$APPDIR/AppRun"
cp "$HERE/$DESKTOP_ID.desktop" "$APPDIR/"
cp "$HERE/$DESKTOP_ID.desktop" "$APPDIR/usr/share/applications/"
cp "$HERE/softchord.png" "$APPDIR/"
cp "$HERE/softchord.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/"
ln -s softchord.png "$APPDIR/.DirIcon"
cp "$HERE/softchord-mime.xml" "$APPDIR/usr/share/mime/packages/softchord.xml"

rm -f "$DIST/$NAME.AppImage" "$DIST/$NAME.tar.gz"
APPIMAGE_EXTRACT_AND_RUN=1 ARCH="$ARCH" VERSION="$VER" \
  "$TOOL" --no-appstream --runtime-file "$RUNTIME" "$APPDIR" "$DIST/$NAME.AppImage"
chmod 755 "$DIST/$NAME.AppImage"

# The plain executable in a folder, for people who do not want an AppImage.
mkdir -p "$WORK/$NAME"
install -m 755 "$EXE" "$WORK/$NAME/softChord"
tar -C "$WORK" -czf "$DIST/$NAME.tar.gz" "$NAME"

ls -l "$DIST/$NAME.AppImage" "$DIST/$NAME.tar.gz"
