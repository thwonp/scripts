#!/bin/bash
#
# Bulk-converts .chd disc images back to .cue/.bin pairs using chdman.
# Recurses into subdirectories from the current working directory.
# Use when migrating a CHD-based library back to raw CUE/BIN (e.g. for
# emulators or tools that don't support CHD).

set -euo pipefail
shopt -s globstar nullglob

for f in ./**/*.chd; do
    name="${f%.chd}"
    chdman extractcd -i "$name.chd" -o "$name.cue" --force
done
