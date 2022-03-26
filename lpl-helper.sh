#!/bin/bash

# A script for generating Retroach playlist files by scanning ROMs.

IFS=$'\n'

function generate_lpls {
  # Parent directory of roms
  # Sub-directories are used as playlist name
  rom_parent_dir="ux0:/data/retroarch/roms" # Vita
  # rom_parent_dir="C:\\RetroArch-Win64\\roms\\" # Windows
  rom_dir="roms"

  # Output directory
  odir="tmp_thumbs"

  # Start fresh with a clean output directory.
  rm -rf ${odir}/
  mkdir -p "${odir}"

  for dir in $(find ${rom_dir}/* -type d); do
  # Scan sub-directories to generate a unique playlist for each system.
    playlist_name="${dir#*/}"
    touch "${odir}/${playlist_name}.lpl"
    cat <<EOF > "${odir}/${playlist_name}.lpl"
{
  "version": "1.0",
  "items": [
EOF

    for file in $(ls ${rom_dir}/${playlist_name}/) ; do
      # Iterate over all rom files and add it to the playlist.
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
    # Remove final comma from the json. 
    # This method is janky but allows permissions to be preserved.
    sed '$d' "${odir}/${playlist_name}.lpl" > ${odir}/tmp_file.tmp
    mv "${odir}/tmp_file.tmp" "${odir}/${playlist_name}.lpl"
    cat <<EOF >> "${odir}/${playlist_name}.lpl"
    }
  ]
}
EOF

  done
}


function clean_thumb_names {
  # Strips illegal characters from thumbnails by renaming .png files.

  CHARS=('&' '*' '/' ':' '`' '<' '>' '?' '\' '|')
  
  for file in ${DIR}/* ; do    
    file=${file#${DIR}/} # Substring to remove leading directory
  
    if $(grep -q ".png" <<<"${file}"); then
      thumb="${file}"
      
      for illegal_char in "${CHARS[@]}"; do
        if grep -q "${illegal_char}" <<<"${thumb}"; then
          thumb_clean="${thumb//${illegal_char}/_}"
          echo "INFO: Illegal char ${illegal_char} found in $thumb"
          echo "INFO: Renaming to: $thumb_clean"
          mv "${DIR}/${thumb}" "${DIR}/${thumb_clean}"
        fi
      done
    fi
  done
}

# TODO: getopts function

generate_lpls

# chdman createcd -i "Policenauts (Japan) (Disc 2) [En by Slowbeef v1.0].cue" -o "Policenauts - Eng. Patch - Disc 2.chd"
# xargs -P 10 -n 1 curl -O -L < ../psxurls
