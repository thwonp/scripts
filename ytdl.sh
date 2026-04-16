#!/bin/bash
#
# Download a YouTube URL as an MP3, parse "Artist - Title" metadata from
# the video title, loudness-normalize the result, and archive the original
# into ./bak/. Intended for one-off music rips.
#
# Requires: yt-dlp, ffmpeg, ffmpeg-normalize.

set -euo pipefail

URL="${1:?usage: ytdl.sh <youtube-url>}"

yt-dlp -f bestaudio "${URL}" \
    -x --audio-format mp3 \
    --add-metadata \
    --parse-metadata "title:%(artist)s - %(title)s"

ffmpeg-normalize ./*.mp3 -c:a mp3 -b:a 192k -ext mp3

mkdir -p bak
mv -- ./*.mp3 bak/
