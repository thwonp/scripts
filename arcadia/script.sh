
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