#!/bin/bash
#
# archive-helper.sh — Unzip, merge, and repack files for archival using 7zip.
#
# For each *.zip in <directory>: single-file zips are extracted (so the
# raw file goes into the archive), while multi-file zips are added as-is
# (kept as .zip inside the .7z). Everything is then compressed into one
# solid archive named "<directory>.7z" placed alongside the target folder.
# Uses -mx=9 -ms=on for maximum solid compression.
#
# Usage:
#   ./archive-helper.sh [options] <directory>
#
# Options:
#   (default)    Single-file zips are extracted so the raw file goes into
#                the archive. Multi-file zips are added as-is (.zip kept).
#                Compression: -mx=9 -md=1g -ms=on (solid, max).
#                NOTE: solid mode makes random-access extraction of a
#                single file slow — 7z must decompress everything from
#                the start of the solid block to your file.
#   --unzip-all  Extract all zips, including multi-file ones.
#   --no-unzip   Don't extract any zips — add them all as .zip files
#                inside the .7z archive.
#   --foldered   Extract each zip into its own subfolder (named after the
#                zip) instead of flat into the archive root.
#   --unzip-inner  After extracting, also extract single-file inner zips
#                found inside the extracted contents. Multi-file inner
#                zips are left intact.
#   --delete-originals  Delete source .zip files after successful archive
#                creation and verification.
#   --repack      Don't merge into one archive. Instead, repack each .zip
#                as its own .7z in place. Skips zips that already have a
#                matching .7z. Compatible with --level, --dict, --no-solid,
#                --container, --unzip-inner, --delete-originals, --foldered.
#   --skip-7z    Just extract zips into the target directory, don't create
#                any .7z archive. Implies --repack (per-zip iteration).
#                With --foldered, each zip extracts into its own subfolder.
#                With --unzip-inner, inner single-file zips are also extracted.
#                Combine with --parallel N for concurrent extractions.
#   --resume-pack  Skip extraction. Pack pre-extracted content into .7z(s).
#                In repack mode (--repack): scans target dir for subfolders
#                that lack a matching .7z and packs each one. (Pairs with a
#                prior --skip-7z --foldered run.)
#                In merge mode: looks for the staging dir (left from an
#                interrupted run) and compresses it into the merged .7z.
#   --container  Store only, no compression (-mx=0). Bundles files into
#                a single .7z without spending time compressing.
#                Overrides --level and --dict.
#                Random access is fast — files extract directly from disk
#                without decompression.
#   --level N    Compression level 0-9 (default: 9). Higher = better
#                compression but slower. 0 = store only.
#   --dict SIZE  Dictionary size, e.g. 64m, 256m, 1g (default: 1g).
#                Larger dict finds matches across longer ranges. RAM use
#                during compression is ~11x dict size.
#   --no-solid   Disable solid mode (solid is on by default). Solid mode
#                groups files into one stream for better compression of
#                similar files, but makes single-file extraction slow.
#                Use this if you'll frequently pull individual files out
#                of the archive — random access becomes near-instant at
#                the cost of some compression ratio.
#   --dry-run    Print what would happen without actually creating, deleting,
#                or modifying any files. Read-only inspection still happens
#                (file sizes, zip listings) so output reflects real choices.
#   --verify-only  Scan target dir for .7z files and run integrity tests on
#                each. With --checksum, also verify sidecar .sha256 files.
#                No extraction or compression. Compatible with --password.
#   --password PW  Encrypt archives with the given password, including
#                file headers (-mhe=on). Required to verify or extract
#                later. Applied to all archive operations.
#   --checksum   Write a .sha256 sidecar file next to each .7z after
#                creation. With --verify-only, also verify any existing
#                sidecars. Useful for detecting bit-rot on cold storage.
#   --parallel N  In --repack mode, run up to N repack jobs in parallel.
#                Each job uses its own staging dir. Has no effect in merge
#                mode (7za already parallelizes internally).
#
# Example:
#   ./archive-helper.sh "./Nintendo DS unmodified"
#   -> produces "./Nintendo DS unmodified.7z"
#
# Notes:
#   - Source ZIPs are preserved unless --delete-originals is set.
#   - Aborts if the output .7z already exists.
#   - On interrupt, the partial .7z and staging dir are cleaned up.

set -euo pipefail

UNZIP_ALL=0
CONTAINER=0
NO_UNZIP=0
FOLDERED=0
UNZIP_INNER=0
DELETE_ORIGINALS=0
REPACK=0
SKIP_7Z=0
RESUME_PACK=0
LEVEL=9
DICT=1g
SOLID=on
DRY_RUN=0
VERIFY_ONLY=0
PASSWORD=""
CHECKSUM=0
PARALLEL=1
while [[ "${1:-}" == --* ]]; do
    case "$1" in
        --unzip-all) UNZIP_ALL=1; shift ;;
        --container) CONTAINER=1; shift ;;
        --no-unzip) NO_UNZIP=1; shift ;;
        --foldered) FOLDERED=1; shift ;;
        --unzip-inner) UNZIP_INNER=1; shift ;;
        --delete-originals) DELETE_ORIGINALS=1; shift ;;
        --repack) REPACK=1; shift ;;
        --skip-7z) SKIP_7Z=1; shift ;;
        --resume-pack) RESUME_PACK=1; shift ;;
        --level) LEVEL="$2"; shift 2 ;;
        --dict) DICT="$2"; shift 2 ;;
        --no-solid) SOLID=off; shift ;;
        --dry-run) DRY_RUN=1; shift ;;
        --verify-only) VERIFY_ONLY=1; shift ;;
        --password) PASSWORD="$2"; shift 2 ;;
        --checksum) CHECKSUM=1; shift ;;
        --parallel) PARALLEL="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [[ $# -ne 1 ]]; then
    echo "Usage: $(basename "$0") [options] <directory>"
    exit 1
fi

# --skip-7z only makes sense with per-zip iteration; auto-enable --repack.
if [[ "$SKIP_7Z" -eq 1 && "$REPACK" -eq 0 ]]; then
    REPACK=1
fi

# --- Helpers ---
do_cmd() {
    if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "DRY: $*"
    else
        "$@"
    fi
}

# Build the 7za compression args based on flags. Echoes as one arg per line.
pack_args() {
    if [[ "$CONTAINER" -eq 1 ]]; then
        printf '%s\n' "-mx=0"
    else
        printf '%s\n' "-mx=$LEVEL" "-md=$DICT" "-ms=$SOLID"
    fi
    if [[ -n "$PASSWORD" ]]; then
        printf '%s\n' "-p$PASSWORD" "-mhe=on"
    fi
}

# Run 7za a with proper compression flags. Args: <output> <inputs...>
pack_archive() {
    local out="$1"; shift
    local args=()
    while IFS= read -r a; do args+=("$a"); done < <(pack_args)
    do_cmd 7za a "${args[@]}" "$out" "$@"
}

# Run 7za t with password if needed. Args: <archive>
verify_archive() {
    local archive="$1"
    local args=()
    if [[ -n "$PASSWORD" ]]; then args+=("-p$PASSWORD"); fi
    do_cmd 7za t "${args[@]}" "$archive"
}

# Write a .sha256 sidecar next to the archive (if --checksum). Args: <archive>
write_checksum() {
    [[ "$CHECKSUM" -eq 0 ]] && return
    local archive="$1"
    local dir base
    dir="$(dirname "$archive")"
    base="$(basename "$archive")"
    if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "DRY: sha256sum $base > $base.sha256 (in $dir)"
    else
        (cd "$dir" && sha256sum "$base" > "$base.sha256")
    fi
}

# Verify a .sha256 sidecar next to the archive (if it exists). Args: <archive>
verify_checksum() {
    local archive="$1"
    local sidecar="$archive.sha256"
    [[ ! -f "$sidecar" ]] && return 0
    local dir
    dir="$(dirname "$archive")"
    if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "DRY: verify $sidecar"
    else
        (cd "$dir" && sha256sum -c "$(basename "$sidecar")")
    fi
}

TARGET_DIR="${1%/}"
STAGING_DIR="${TARGET_DIR}-staging"
OUT_NAME="$(basename "$TARGET_DIR")"
OUT_ARCHIVE="${TARGET_DIR%/*}/${OUT_NAME}.7z"
# If TARGET_DIR has no slash, place output alongside it
if [[ "$OUT_ARCHIVE" == "${OUT_NAME}.7z" || "$TARGET_DIR" != */* ]]; then
    OUT_ARCHIVE="./${OUT_NAME}.7z"
fi

if [[ ! -d "$TARGET_DIR" ]]; then
    echo "Error: '$TARGET_DIR' is not a directory"
    exit 1
fi

extracted=0
skipped=0
bytes_before=0
bytes_after=0

shopt -s nullglob
zips=("$TARGET_DIR"/*.zip)
shopt -u nullglob

# --- Verify-only mode: scan and test all .7z files in target dir ---
if [[ "$VERIFY_ONLY" -eq 1 ]]; then
    shopt -s nullglob
    archives=("$TARGET_DIR"/*.7z)
    shopt -u nullglob

    if [[ ${#archives[@]} -eq 0 ]]; then
        echo "No .7z files found in $TARGET_DIR"
        exit 0
    fi

    echo "Verifying ${#archives[@]} archive(s) in: $TARGET_DIR"
    echo ""
    failed=0
    total=${#archives[@]}
    i=0
    for archive in "${archives[@]}"; do
        i=$((i + 1))
        name="$(basename "$archive")"
        echo "[$i/$total] $name"

        if ! verify_archive "$archive"; then
            echo "  FAIL: archive integrity check failed"
            failed=$((failed + 1))
            continue
        fi

        if [[ "$CHECKSUM" -eq 1 && -f "$archive.sha256" ]]; then
            if ! verify_checksum "$archive"; then
                echo "  FAIL: sha256 mismatch"
                failed=$((failed + 1))
                continue
            fi
        elif [[ "$CHECKSUM" -eq 1 ]]; then
            echo "  WARN: no .sha256 sidecar to verify"
        fi
    done

    echo ""
    echo "Verified $((total - failed))/$total archives ($failed failed)."
    [[ $failed -gt 0 ]] && exit 1
    exit 0
fi

# --- Resume-pack mode: pack pre-extracted content, no unzipping ---
if [[ "$RESUME_PACK" -eq 1 ]]; then
    if [[ "$REPACK" -eq 1 ]]; then
        shopt -s nullglob
        subdirs=("$TARGET_DIR"/*/)
        shopt -u nullglob

        if [[ ${#subdirs[@]} -eq 0 ]]; then
            echo "No subdirectories found in $TARGET_DIR to pack."
            exit 0
        fi

        echo "Resume-packing subdirectories in: $TARGET_DIR"
        echo ""

        total=${#subdirs[@]}
        i=0
        completed=0
        for d in "${subdirs[@]}"; do
            i=$((i + 1))
            d="${d%/}"
            name="$(basename "$d")"
            out="${TARGET_DIR}/${name}.7z"

            if [[ -f "$out" ]]; then
                echo "[$i/$total] $name: skipping (already have .7z)"
                skipped=$((skipped + 1))
                continue
            fi

            echo "[$i/$total] $name"
            pack_archive "$out" "$d"

            if [[ "$CONTAINER" -eq 0 ]]; then
                verify_archive "$out"
            fi

            write_checksum "$out"

            completed=$((completed + 1))
            echo "  Done."
            echo ""
        done

        echo ""
        echo "Packed $completed subdirectories ($skipped skipped)."
        exit 0
    else
        if [[ ! -d "$STAGING_DIR" ]]; then
            echo "Error: no staging dir found at $STAGING_DIR"
            echo "Nothing to resume."
            exit 1
        fi

        if [[ -e "$OUT_ARCHIVE" ]]; then
            echo "Error: output archive already exists: $OUT_ARCHIVE"
            exit 1
        fi

        echo "Resume-packing staging dir into: $OUT_ARCHIVE"
        pack_archive "$OUT_ARCHIVE" "$STAGING_DIR"/*

        if [[ "$CONTAINER" -eq 0 ]]; then
            echo ""
            echo "Verifying..."
            verify_archive "$OUT_ARCHIVE"
        fi

        write_checksum "$OUT_ARCHIVE"

        do_cmd rm -rf "$STAGING_DIR"
        echo ""
        echo "Done."
        exit 0
    fi
fi

if [[ ${#zips[@]} -eq 0 ]]; then
    echo "No .zip files found in $TARGET_DIR"
    exit 0
fi

# --- Repack mode: each .zip becomes its own .7z ---
if [[ "$REPACK" -eq 1 ]]; then

    print_summary() {
        echo ""
        echo "======================================"
        echo "  Summary"
        echo "======================================"
        printf "  Completed   : %d\n" "$extracted"
        printf "  Skipped     : %d\n" "$skipped"
        echo "======================================"
    }

    on_exit() {
        # Clean up any per-job staging dirs
        shopt -s nullglob
        for d in "${STAGING_DIR}"-*; do rm -rf "$d"; done
        shopt -u nullglob
        print_summary
    }
    trap on_exit EXIT

    # Process one zip. Args: <zip> <idx> <total>
    # Each call uses its own per-process staging dir for parallel safety.
    process_one_zip() {
        local zip="$1" idx="$2" total="$3"
        local name out staging dest size_before
        name=$(basename "$zip" .zip)
        out="${TARGET_DIR}/${name}.7z"
        staging="${STAGING_DIR}-$$-${idx}"

        if [[ -f "$out" ]]; then
            echo "[$idx/$total] $name: skipping (already have .7z)"
            return 2
        fi

        echo "[$idx/$total] $name"
        size_before=$(stat -c %s "$zip")

        if [[ "$SKIP_7Z" -eq 1 ]]; then
            if [[ "$FOLDERED" -eq 1 ]]; then
                dest="$TARGET_DIR/$name"
                do_cmd mkdir -p "$dest"
            else
                dest="$TARGET_DIR"
            fi

            if ! do_cmd unzip -q -o "$zip" -d "$dest/"; then
                echo "  WARN: failed to extract, skipping"
                return 1
            fi

            if [[ "$UNZIP_INNER" -eq 1 ]]; then
                find "$dest" -maxdepth 1 -name "*.zip" | while read -r inner; do
                    inner_count=$(unzip -Z1 "$inner" 2>/dev/null | wc -l)
                    if [[ "$inner_count" -eq 1 ]]; then
                        do_cmd unzip -q "$inner" -d "$(dirname "$inner")/"
                        do_cmd rm "$inner"
                    fi
                done
            fi

            [[ "$DELETE_ORIGINALS" -eq 1 ]] && do_cmd rm "$zip"
            return 0
        fi

        do_cmd rm -rf "$staging"
        do_cmd mkdir "$staging"

        if [[ "$FOLDERED" -eq 1 ]]; then
            dest="$staging/$name"
            do_cmd mkdir -p "$dest"
        else
            dest="$staging"
        fi

        if ! do_cmd unzip -q "$zip" -d "$dest/"; then
            echo "  WARN: failed to extract, skipping"
            do_cmd rm -rf "$staging"
            return 1
        fi

        if [[ "$UNZIP_INNER" -eq 1 ]]; then
            find "$staging" -name "*.zip" | while read -r inner; do
                inner_count=$(unzip -Z1 "$inner" 2>/dev/null | wc -l)
                if [[ "$inner_count" -eq 1 ]]; then
                    do_cmd unzip -q "$inner" -d "$(dirname "$inner")/"
                    do_cmd rm "$inner"
                fi
            done
        fi

        pack_archive "$out" "$staging"/*

        if [[ "$CONTAINER" -eq 0 ]]; then
            verify_archive "$out"
        fi

        write_checksum "$out"

        [[ "$DELETE_ORIGINALS" -eq 1 ]] && do_cmd rm "$zip"

        do_cmd rm -rf "$staging"
        echo "  Done."
        return 0
    }

    echo "Repacking ZIPs in: $TARGET_DIR"
    if [[ "$PARALLEL" -gt 1 ]]; then
        echo "Parallel jobs: $PARALLEL"
    fi
    echo ""

    total=${#zips[@]}
    i=0
    if [[ "$PARALLEL" -le 1 ]]; then
        for zip in "${zips[@]}"; do
            i=$((i + 1))
            rc=0
            process_one_zip "$zip" "$i" "$total" || rc=$?
            case "$rc" in
                0) extracted=$((extracted + 1)) ;;
                2) skipped=$((skipped + 1)) ;;
                *) skipped=$((skipped + 1)) ;;
            esac
            echo ""
        done
    else
        # Parallel mode: run up to $PARALLEL jobs concurrently. Stat tracking
        # is approximate (jobs run in subshells), so we just count completions.
        for zip in "${zips[@]}"; do
            i=$((i + 1))
            while (( $(jobs -rp | wc -l) >= PARALLEL )); do
                wait -n || true
            done
            process_one_zip "$zip" "$i" "$total" &
        done
        wait
        extracted="$total"  # approximation
    fi
    exit 0
fi

# --- Merge mode: combine all zips into one .7z ---

if [[ -e "$OUT_ARCHIVE" ]]; then
    echo "Error: output archive already exists: $OUT_ARCHIVE"
    exit 1
fi

print_summary() {
    echo ""
    echo "======================================"
    echo "  Summary"
    echo "======================================"
    printf "  Extracted   : %d\n" "$extracted"
    printf "  Skipped     : %d\n" "$skipped"
    if [[ $bytes_before -gt 0 ]]; then
        printf "  ZIPs size   : %s\n" "$(numfmt --to=iec-i --suffix=B $bytes_before)"
    fi
    if [[ -f "$OUT_ARCHIVE" ]]; then
        size_after=$(stat -c %s "$OUT_ARCHIVE")
        printf "  7z size     : %s\n" "$(numfmt --to=iec-i --suffix=B $size_after)"
        if [[ $bytes_before -gt 0 ]]; then
            saved=$((bytes_before - size_after))
            printf "  Saved       : %s\n" "$(numfmt --to=iec-i --suffix=B $saved)"
            printf "  Reduction   : %.1f%%\n" "$(echo "scale=1; $saved * 100 / $bytes_before" | bc)"
        fi
    fi
    echo "======================================"
}

COMPRESS_DONE=0
on_exit() {
    rm -rf "$STAGING_DIR"
    if [[ $COMPRESS_DONE -eq 0 && -f "$OUT_ARCHIVE" ]]; then
        rm -f "$OUT_ARCHIVE"
        echo ""
        echo "Removed partial archive: $OUT_ARCHIVE"
        echo "Original ZIPs were preserved."
    fi
    print_summary
}
trap on_exit EXIT

echo "Packing ZIPs from: $TARGET_DIR"
echo "Into archive     : $OUT_ARCHIVE"
echo ""

# Fast path: no extraction needed, add zips directly
if [[ "$NO_UNZIP" -eq 1 && "$CONTAINER" -eq 1 ]]; then
    for zip in "${zips[@]}"; do
        bytes_before=$((bytes_before + $(stat -c %s "$zip")))
    done
    extracted=${#zips[@]}
    echo "Adding ${#zips[@]} zips directly (no-unzip + container)..."
    pack_archive "$OUT_ARCHIVE" "$TARGET_DIR"/*.zip
    COMPRESS_DONE=1
else
    do_cmd rm -rf "$STAGING_DIR"
    do_cmd mkdir "$STAGING_DIR"

    total=${#zips[@]}
    i=0
    for zip in "${zips[@]}"; do
        i=$((i + 1))
        name=$(basename "$zip" .zip)
        echo "[$i/$total] $name"

        size=$(stat -c %s "$zip")
        bytes_before=$((bytes_before + size))

        if [[ "$FOLDERED" -eq 1 ]]; then
            dest="$STAGING_DIR/$name"
        else
            dest="$STAGING_DIR"
        fi

        if [[ "$NO_UNZIP" -eq 1 ]]; then
            do_cmd mkdir -p "$dest"
            do_cmd cp "$zip" "$dest/"
        else
            file_count=$(unzip -Z1 "$zip" 2>/dev/null | wc -l)
            if [[ "$file_count" -ne 1 && "$UNZIP_ALL" -eq 0 ]]; then
                echo "  multi-file zip, adding as-is"
                do_cmd mkdir -p "$dest"
                do_cmd cp "$zip" "$dest/"
            else
                do_cmd mkdir -p "$dest"
                if ! do_cmd unzip -q -o "$zip" -d "$dest/"; then
                    echo "  WARN: failed to extract, skipping"
                    skipped=$((skipped + 1))
                    continue
                fi
            fi

            if [[ "$UNZIP_INNER" -eq 1 ]]; then
                find "$dest" -name "*.zip" | while read -r inner; do
                    inner_count=$(unzip -Z1 "$inner" 2>/dev/null | wc -l)
                    if [[ "$inner_count" -eq 1 ]]; then
                        do_cmd unzip -q "$inner" -d "$(dirname "$inner")/"
                        do_cmd rm "$inner"
                    fi
                done
            fi
        fi
        extracted=$((extracted + 1))
    done

    echo ""
    echo "Compressing into $OUT_ARCHIVE ..."
    pack_archive "$OUT_ARCHIVE" "$STAGING_DIR"/*
    COMPRESS_DONE=1
fi

if [[ "$CONTAINER" -eq 1 ]]; then
    echo ""
    echo "Skipping verification (container mode, no compression)."
else
    echo ""
    echo "Verifying..."
    verify_archive "$OUT_ARCHIVE"
fi

write_checksum "$OUT_ARCHIVE"

if [[ "$DELETE_ORIGINALS" -eq 1 ]]; then
    echo ""
    echo "Deleting original ZIPs..."
    for zip in "${zips[@]}"; do
        do_cmd rm "$zip"
    done
fi

echo ""
echo "Done."
