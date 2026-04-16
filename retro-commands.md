# Retro Gaming Command Reference

Useful one-liners and commands for ROM management, image processing, and patching.

## ImageMagick

### Install
```bash
# Fedora / RHEL
yum install ImageMagick

# Debian / Ubuntu
apt install ImageMagick
```

### Resize images

Resize to max dimensions while preserving aspect ratio (only shrinks, never enlarges):
```bash
mogrify -resize 250x250\> *.png
```

RG35XX (GarlicOS) — resize and pad to 640x480, left-aligned:
```bash
mogrify -resize 340x480 -extent 640x480 -gravity West -background none *.png
```

Miyoo Mini — shrink to fit within 250x360:
```bash
mogrify -resize 250x360\> *.png
```

### Convert format

Convert a single file (inside a loop over files):
```bash
convert "${file}" "${file/.jpg/.png}"
```

## ROM Patching

### Floating IPS (Flips)
```bash
./flips-linux --apply darkhalf_patch.ips "Dark Half.sfc" patchedRom.sfc
```

### xdelta3
```bash
xdelta3 -d -s rom.sfc patch.IPS patchedRom.sfc
```

## CHD Conversion

Create a CHD from a CUE/BIN pair:
```bash
chdman createcd -i "Policenauts (Japan) (Disc 2) [En by Slowbeef v1.0].cue" -o "Policenauts - Eng. Patch - Disc 2.chd"
```

## Bulk Downloads

Parallel download a list of URLs (10 at a time):
```bash
xargs -P 10 -n 1 curl -O -L < ../psxurls
```
