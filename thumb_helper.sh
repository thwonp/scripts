#!/bin/bash
#
# ROM / thumbnail audit tool.
#
# Expects a working layout like:
#     ./roms/<system>/<rom-files>
#     ./thumbnails/<system>/covers/<basename>.png
#
# Reports, per system in $SYSTEMS:
#   - ROMs that have no matching cover PNG
#   - Cover PNGs that have no matching ROM
#
# Does not modify anything; the rename/move/delete lines are commented
# out. See retro-commands.md for the ImageMagick and ROM-patching
# one-liners that used to live at the bottom of this file.

set -uo pipefail

SYSTEMS=('wiiu')

matchsearch() {
    echo "------------------------------------------"
    echo "Checking if every ROM has a matching cover"
    echo "------------------------------------------"
    for system in "${SYSTEMS[@]}"; do
        local missing=0 matched=0 total=0
        for rom in "roms/${system}"/*; do
            [[ -e "$rom" ]] || continue
            ((total++))
            local base basename
            base="$(basename "$rom")"
            basename="${base%.*}"
            if [[ -f "thumbnails/${system}/${basename}.png" ]]; then
                ((matched++))
                # mv "${rom}" matched/roms/
                # mv "thumbnails/${system}/covers/${basename}.png" matched/covers/
            else
                echo "${basename}"
                ((missing++))
            fi
        done
        echo
        if (( missing > 0 )); then
            echo "${system} : ERROR - ${missing} / ${total} ROMs are missing covers!"
        fi
        if (( matched > 0 )); then
            echo "INFO: ${system} : Matched ${matched} / ${total} ROMs to covers"
        fi
    done

    echo "------------------------------------------"
    echo "Checking if every PNG has a matching ROM"
    echo "------------------------------------------"
    for system in "${SYSTEMS[@]}"; do
        local missing=0 matched=0 total=0
        for thumbnail in "thumbnails/${system}/covers"/*; do
            [[ -e "$thumbnail" ]] || continue
            ((total++))
            local base basename
            base="$(basename "$thumbnail")"
            basename="${base%.*}"
            if compgen -G "roms/${system}/${basename}.*" > /dev/null; then
                ((matched++))
            else
                # rm "${thumbnail}"
                ((missing++))
            fi
        done
        echo
        if (( missing > 0 )); then
            echo "${system} : ERROR - ${missing} / ${total} covers are missing ROMs!"
        fi
        if (( matched > 0 )); then
            echo "INFO: ${system} : Matched ${matched} / ${total} covers to ROMs"
        fi
    done
}

# Optional helper: strip dots from ROM base filenames. Disabled by default;
# uncomment the mv to actually rename.
stripChar() {
    for rom in roms/*/*; do
        [[ -e "$rom" ]] || continue
        local base basename extension path fixedname
        base="$(basename "$rom")"
        basename="${base%.*}"
        extension="${base##*.}"
        path="${rom%/*}"
        if [[ "$basename" == *.* ]]; then
            fixedname="${basename//./}"
            # mv "${rom}" "${path}/${fixedname}.${extension}"
            echo "would rename: ${rom} -> ${path}/${fixedname}.${extension}"
        fi
    done
}

matchsearch
