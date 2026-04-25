#!/bin/bash

# Step 1: Convert all .jpg images to .png and delete originals
find . -type f -name "*.jpg" | while read -r jpg_file; do
  png_file="${jpg_file%.jpg}.png"
  # Only convert if the .png doesn't already exist
  if [[ ! -f "$png_file" ]]; then
    if magick "$jpg_file" "$png_file"; then
      rm "$jpg_file"
    else
      echo "Failed to convert: $jpg_file" >&2
    fi
  fi
done

# Step 2: Generate composite images using magick
for file in covers/*.png; do
  # Construct paths
  dir=$(dirname "$file")
  mix_dir="${dir/covers/miximages-vert}"

  # Create the miximages-vert directory if it doesn't exist
  mkdir -p "$mix_dir"

  magick -size 480x720 xc:none \
    \( "${file/covers/screenshots}" -resize 480x480^ -gravity center -crop 480x480+0+0 \) -gravity center -geometry +0-20 -composite \
    \( -size 480x720 gradient:"rgba(0,0,0,0.5)-transparent" \) -gravity center -composite \
    \( "${file/covers/marquees}" -resize 480x150 \) -gravity north -geometry +0+5 -composite \
    \( "${file}" -resize 480x240 \) -gravity south -geometry +0+0 -composite \
    "$mix_dir/$(basename "$file")"
done

