#!/bin/bash
#
# In-place transcoder for .mp4 files in the current directory.
# Re-encodes each video to H.264 at CRF 28 / 30 fps with AAC 96k audio,
# scaling to fit inside 640x480 while preserving aspect ratio. Intended
# for trimming the storage size of per-game preview videos used by
# emulator frontends.
#
# Runs one job per CPU core (via xargs -P $(nproc)). Each file is
# written to temp_<name> first and atomically moved over the original
# on success. Failures are logged (with an even-dimension fallback
# retry) to conversion_log.txt; the original file is left untouched.

set -u

log_file="conversion_log.txt"
: > "$log_file"  # Clear log file

convert_video() {
  file="$1"
  dir="$(dirname "$file")"
  base="$(basename "$file")"
  temp_file="$dir/temp_$base"

  rm -f "$temp_file"  # Ensure no leftover temp file

  # First attempt
  if ffmpeg -i "$file" \
    -vf "scale='min(640,iw)':'min(480,ih)':force_original_aspect_ratio=decrease" \
    -r 30 \
    -c:v libx264 -preset veryfast -crf 28 \
    -c:a aac -b:a 96k \
    "$temp_file" -y > /dev/null 2>&1; then

    mv -f "$temp_file" "$file"
    echo "✅ Converted: $file" | tee -a "$log_file"

  else
    rm -f "$temp_file"

    # Fallback: enforce even dimensions
    if ffmpeg -i "$file" \
      -vf "scale='min(640,iw)':'min(480,ih)':force_original_aspect_ratio=decrease,scale=trunc(iw/2)*2:trunc(ih/2)*2" \
      -r 30 \
      -c:v libx264 -preset veryfast -crf 28 \
      -c:a aac -b:a 96k \
      "$temp_file" -y > /dev/null 2>&1; then

      mv -f "$temp_file" "$file"
      echo "⚠️  Fallback succeeded: $file" | tee -a "$log_file"
    else
      echo "❌ Failed to convert: $file" | tee -a "$log_file"
      rm -f "$temp_file"
    fi
  fi
}

export -f convert_video
export log_file

# Only .mp4 files in the current directory
find . -maxdepth 1 -type f -iname "*.mp4" -print0 | \
  xargs -0 -n 1 -P "$(nproc)" bash -c 'convert_video "$0"'
