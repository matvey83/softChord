#!/bin/sh
# Put the repo songbook inside the app bundle. The song list reads this copy.
set -eu

songbook="${SRCROOT}/../zvuki_neba.songbook"
dest_dir="${BUILT_PRODUCTS_DIR}/${UNLOCALIZED_RESOURCES_FOLDER_PATH}"

if [ ! -f "$songbook" ]; then
  echo "error: zvuki_neba.songbook not found at $songbook" >&2
  exit 1
fi

mkdir -p "$dest_dir"
cp "$songbook" "$dest_dir/zvuki_neba.songbook"
