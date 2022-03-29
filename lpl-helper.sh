#!/bin/bash

# A script for generating Retroach playlist files and cleaning illegal characters from thumbnails.

IFS=$'\n'

function usage {
  echo 'usage: '"${SCRIPT}"' [-p|platform] [-o|output_dir] [-t|thumbnail_dir] [-g|generate_lpls] [-c|clean_thumbs] [-h|help]'
  echo '  -p [platform]      "vita" or "windows" : Sets rom location path in the systems format'
  echo '  -o [output_dir]    Output directory for lpl playlist files'
  echo '  -t [thumbnail_dir] Input directory where thumbnail files are stored to target for cleaning'
  echo '  -g [generate_lpls] Trigger lpl generation. Requires options "p" and "o"'
  echo '  -c [clean_thumbs]  Trigger thumbnail name cleaning. Requires option "t"'
  echo '  -h [help]          show this help screen'
}

function generate_lpls {
  # Start fresh with a clean output directory.
  rm -rf ${ODIR}/
  mkdir -p "${ODIR}"

  for dir in $(find ${rom_dir}/* -type d); do
  # Scan sub-directories to generate a unique playlist for each system.
    playlist_name="${dir#*/}"
    touch "${ODIR}/${playlist_name}.lpl"
    cat <<EOF > "${ODIR}/${playlist_name}.lpl"
{
  "version": "1.0",
  "items": [
EOF

    for file in $(ls ${rom_dir}/${playlist_name}/) ; do
      # Iterate over all rom files and add it to the playlist.
      rom_label="${file%.*}"
      cat <<EOF >> "${ODIR}/${playlist_name}.lpl"
    {
      "path": "${ROM_PARENT_DIR}/${playlist_name}/${file}",
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
    sed '$d' "${ODIR}/${playlist_name}.lpl" > ${ODIR}/tmp_file.tmp
    mv "${ODIR}/tmp_file.tmp" "${ODIR}/${playlist_name}.lpl"
    cat <<EOF >> "${ODIR}/${playlist_name}.lpl"
    }
  ]
}
EOF

  done
}

function clean_thumb_names {
  # Strips illegal characters from thumbnails by renaming .png files.

  CHARS=('&' '*' '/' ':' '`' '<' '>' '?' '\' '|')
  
  for file in ${THUMB_DIR}/* ; do    
    file=${file#${THUMB_DIR}/} # Substring to remove leading directory
  
    if $(grep -q ".png" <<<"${file}"); then
      thumb="${file}"
      
      for illegal_char in "${CHARS[@]}"; do
        if grep -q "${illegal_char}" <<<"${thumb}"; then
          thumb_clean="${thumb//${illegal_char}/_}"
          echo "INFO: Illegal char ${illegal_char} found in $thumb"
          echo "INFO: Renaming to: $thumb_clean"
          mv "${THUMB_DIR}/${thumb}" "${THUMB_DIR}/${thumb_clean}"
        fi
      done
    fi
  done
}

function platform_select {
  if [[ "$1" -eq "vita" ]]; then
    ROM_PARENT_DIR="ux0:/data/retroarch/roms"
  elsif [[ "$1" -eq "windows" ]]; then
    ROM_PARENT_DIR="C:\\RetroArch-Win64\\roms\\"
  else
    echo "Error: Please select a valid platform: windows or vita"
  fi
}

while getopts p:f:upsh flag; do
  case "${flag}" in
    p | --platform            ) platform_select ${OPTARG}
                                ;;
    o | --output_dir          ) ODIR=${OPTARG}
                                ;;
    t | --thumbnail_dir       ) THUMB_DIR=${OPTARG}
                                ;;
    g | --generate_lpls       ) generate_lpls
                                ;;
    c | --clean_thumbs        ) clean_thumb_names
                                ;;
    h | --help                ) usage
                                exit 0
                                ;;
    *                         ) >&2 echo 'ERROR: Unknown option: "'"${flag}"'"'
                                usage
                                exit 9
                                ;;
    esac
done

# chdman createcd -i "Policenauts (Japan) (Disc 2) [En by Slowbeef v1.0].cue" -o "Policenauts - Eng. Patch - Disc 2.chd"
# xargs -P 10 -n 1 curl -O -L < ../psxurls
