#!/bin/bash
#
# Builds a "rom_basename,proper_name" CSV (mame_fixed.csv) by joining each
# entry in <SYSTEM>_romlist.txt against the <path>/<name> pairs in the
# matching <SYSTEM>_gamelist.xml. Used to produce MAME/NEOGEO title
# lookup tables for frontends that don't consume gamelist.xml directly.
#
# Exits non-zero on the first ROM that has no matching <path> entry so
# missing metadata is caught immediately.

SYSTEMS=('NEOGEO' 'ARCADE')

for system in ${SYSTEMS[@]}; do
    for file in $(<"${system}"_romlist.txt); do
        name=$(grep '<path>./'"${file}"'</path>' "${system}_gamelist.xml" -A 1 | tail -1)
        
        if [ "x${name}" = "x" ]; then
            echo "ERROR: No match for ${file}"
            exit 22
        fi

        name_clean=$(sed 's/<\/name.*//' <<<"${name/*<name>/}")
        echo "${file/.zip/},${name_clean}" >> mame_fixed.csv
    done
done