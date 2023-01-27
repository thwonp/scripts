#!/bin/bash
URL=$1
youtube-dl -f bestaudio "${URL}" -x --audio-format mp3 --add-metadata --metadata-from-title "%(artist)s - %(title)s" 
ffmpeg-normalize *.mp3 -c:a mp3 -b:a 192k -ext mp3
mv *mp3 bak/
