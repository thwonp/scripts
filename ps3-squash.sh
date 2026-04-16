#!/bin/bash
#
# Repackage PS3 .iso images as xz-compressed .squashfs archives.
# For each .iso in the current directory: loop-mount it, copy the
# contents out, mksquashfs the result, and clean up. Mount point is
# unmounted on exit even if something fails mid-loop.
#
# Requires: mksquashfs (squashfs-tools), mount privileges (run as root
# or with the appropriate capabilities).

set -euo pipefail

MNT="tmpmnt"

cleanup() {
    if mountpoint -q "${MNT}" 2>/dev/null; then
        umount "${MNT}" || true
    fi
    rm -rf "${MNT}"
}
trap cleanup EXIT

for file in *.iso; do
    [[ -f "$file" ]] || continue
    name="$(basename "$file")"
    out_dir="${name/.iso/.ps3}"
    out_squash="${name/.iso/.ps3.squashfs}"

    mkdir -p "${MNT}"
    mount -o loop "${name}" "${MNT}"

    mkdir -p "${out_dir}"
    echo "Copying data for ${name%.iso}"
    cp -rv "${MNT}/." "${out_dir}/"

    echo "Unmounting..."
    umount "${MNT}"

    echo "Squashing ${out_dir}..."
    mksquashfs "${out_dir}" "${out_squash}" -comp xz

    echo "Cleaning up..."
    rm -rf "${out_dir}"
    echo "Done: ${out_squash}"
done
