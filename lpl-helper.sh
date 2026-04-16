#!/bin/bash
#
# RetroArch playlist helper.
#
#   -g  Mirror a ROM tree (rom_dir/<system>/<files>) into one .lpl per
#       subdirectory. Each entry's path is rewritten for the target
#       device (-p vita|windows|android|linux); label is the filename
#       without its extension; core_path/core_name/crc32 are "DETECT" for
#       RetroArch to resolve at scan/launch. No hashing or DB lookup
#       is performed here, so subdirectory names must match RetroArch's
#       expected system names for DETECT to match a core.
#
#   -c  Replace filesystem-illegal characters (& * / : ` < > ? \ |) in
#       thumbnail PNG filenames with underscores.
#
# Requires: jq.

set -euo pipefail

SCRIPT="${0##*/}"

usage() {
    cat <<EOF
usage: ${SCRIPT} [-p platform] [-r rom_dir] [-o output_dir] [-t thumbnail_dir] [-g] [-c] [-h]
  -p platform       vita | windows | android | linux: rom path style used inside the .lpl
  -r rom_dir        Root directory containing per-system ROM subdirectories
  -o output_dir     Output directory for .lpl playlist files
  -t thumbnail_dir  Directory of thumbnail PNGs to clean
  -g                Generate .lpl playlists (requires -p, -r, -o)
  -c                Clean illegal characters from thumbnail filenames (requires -t)
  -h                Show this help
EOF
}

platform_select() {
    case "$1" in
        vita)
            ROM_PARENT_DIR="ux0:/data/retroarch/roms"
            PATH_SEPARATOR="/"
            ;;
        windows)
            ROM_PARENT_DIR='C:\RetroArch-Win64\roms'
            PATH_SEPARATOR='\'
            ;;
        android)
            ROM_PARENT_DIR="/storage/emulated/0/RetroArch/roms"
            PATH_SEPARATOR="/"
            ;;
        linux)
            ROM_PARENT_DIR="${HOME}/RetroArch/roms"
            PATH_SEPARATOR="/"
            ;;
        *)
            echo "Error: valid platforms are vita, windows, android, linux" >&2
            exit 2
            ;;
    esac
}

generate_lpls() {
    : "${ROM_DIR:?-r rom_dir is required}"
    : "${ODIR:?-o output_dir is required}"
    : "${ROM_PARENT_DIR:?-p platform is required}"

    rm -rf -- "${ODIR:?}/"
    mkdir -p "${ODIR}"

    for dir in "${ROM_DIR}"/*/; do
        [[ -d "$dir" ]] || continue
        playlist_name="$(basename "$dir")"
        playlist_file="${ODIR}/${playlist_name}.lpl"

        # Build items array safely with jq, then wrap in the playlist envelope.
        items="[]"
        for file in "${ROM_DIR}/${playlist_name}"/*; do
            [[ -f "$file" ]] || continue
            rom_name="$(basename "$file")"
            rom_label="${rom_name%.*}"
            rom_path="${ROM_PARENT_DIR}${PATH_SEPARATOR}${playlist_name}${PATH_SEPARATOR}${rom_name}"

            items=$(jq --arg path "$rom_path" \
                       --arg label "$rom_label" \
                       --arg db "${playlist_name}.lpl" \
                       '. += [{
                            path: $path,
                            label: $label,
                            core_path: "DETECT",
                            core_name: "DETECT",
                            crc32: "DETECT",
                            db_name: $db
                        }]' <<<"$items")
        done

        jq -n --argjson items "$items" '{version: "1.0", items: $items}' > "$playlist_file"
    done
}

clean_thumb_names() {
    : "${THUMB_DIR:?-t thumbnail_dir is required}"

    local chars=('&' '*' '/' ':' '`' '<' '>' '?' '\' '|')

    for file in "${THUMB_DIR}"/*.png; do
        [[ -f "$file" ]] || continue
        local base clean
        base="$(basename "$file")"
        clean="$base"
        for illegal in "${chars[@]}"; do
            clean="${clean//${illegal}/_}"
        done
        if [[ "$clean" != "$base" ]]; then
            echo "INFO: Renaming '$base' -> '$clean'"
            mv -- "${THUMB_DIR}/${base}" "${THUMB_DIR}/${clean}"
        fi
    done
}

do_generate=0
do_clean=0

while getopts "p:r:o:t:gch" flag; do
    case "$flag" in
        p) platform_select "$OPTARG" ;;
        r) ROM_DIR="$OPTARG" ;;
        o) ODIR="$OPTARG" ;;
        t) THUMB_DIR="$OPTARG" ;;
        g) do_generate=1 ;;
        c) do_clean=1 ;;
        h) usage; exit 0 ;;
        *) usage; exit 2 ;;
    esac
done

if (( do_generate )); then generate_lpls; fi
if (( do_clean )); then clean_thumb_names; fi
if (( ! do_generate && ! do_clean )); then
    usage
    exit 2
fi
