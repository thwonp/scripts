#!/bin/bash
IFS=$'\n'

# Parent directory of roms
# Sub-directories are used as playlist name
rom_parent_dir="ux0:/data/retroarch/roms" # VITA

# output directory
odir="tmp_thumbs"

rom_dir="roms"

## DANGER ##
rm -rf ${odir}/
mkdir -p "${odir}"

for dir in $(find ${rom_dir}/* -type d); do

  playlist_name="${dir#*/}"
  touch "${odir}/${playlist_name}.lpl"
  cat <<EOF > "${odir}/${playlist_name}.lpl"
{
  "version": "1.0",
  "items": [
EOF

  # Iterate over all files
  for file in $(ls ${rom_dir}/${playlist_name}/) ; do
    rom_label="${file%.*}"
    cat <<EOF >> "${odir}/${playlist_name}.lpl"
    {
      "path": "${rom_parent_dir}/${playlist_name}/${file}",
      "label": "${rom_label}",
      "core_path": "DETECT",
      "core_name": "DETECT",
      "crc32": "DETECT",
      "db_name": "${playlist_name}.lpl"
    },
EOF
  done
  # Remove final comma. This way is janky but preserves permissions
  sed '$d' "${odir}/${playlist_name}.lpl" > ${odir}/tmp_file.tmp
  mv "${odir}/tmp_file.tmp" "${odir}/${playlist_name}.lpl"
  cat <<EOF >> "${odir}/${playlist_name}.lpl"
    }
  ]
}
EOF

done
