SYSTEMS=('wiiu')

function matchsearch(){
  echo "------------------------------------------"
  echo "Checking if every ROM has a matching cover"
  echo "------------------------------------------"
  for system in ${SYSTEMS[@]}; do
    tmp_missing_check='0'
    tmp_matching_check='0'
    rom_counter='0'
    for rom in roms/${system}/*; do
      ((rom_counter++))
      base=$(echo "${rom}" | cut -d '/' -f 3);
      basename="${base%.*}" 
      extension="${base##*.}"
      path=${rom%/*}
      thumb=$(find thumbnails/${system} -type f -name "${basename}".png )   
      grep -q . <<<"${thumb}"
      if [[ $? -ne 0 ]]; then
        echo "${basename}"
        ((tmp_missing_check++))
      else
        ((tmp_matching_check++))
        # echo "Found a match for ${rom}"
        # mv "${rom}" matched/roms/
        # mv thumbnails/"${system}"/covers/"${basename}".png matched/covers/
      fi
    done
    echo
    if [[ $tmp_missing_check -gt '0' ]]; then
      echo "${system} : ERROR - ${tmp_missing_check} / $rom_counter ROMs are missing covers!"
    fi
    if [[ $tmp_matching_check -gt '0' ]]; then
      echo "INFO: ${system} : Matched $tmp_matching_check / $rom_counter ROMs to covers"
    fi
  done

  echo "------------------------------------------"
  echo "Checking if every PNG has a matching ROM"
  echo "------------------------------------------"
  for system in ${SYSTEMS[@]}; do
    tmp_missing_check=0
    tmp_matching_check='0'
    file_counter='0'
      for thumbnail in thumbnails/${system}/covers/*; do
        ((file_counter++))
        base=$(echo "${thumbnail}" | cut -d '/' -f 4);
        basename="${base%.*}" 
        extension="${base##*.}"
        path=${thumbnail%/*}
        rom=$(find roms/${system} -type f -name "${basename}".* )   
        grep -q . <<<"${rom}"
        if [[ $? -ne 0 ]]; then
          # echo "${thumbnail}"
          # rm "${thumbnail}"
          ((tmp_missing_check++))
        else
          ((tmp_matching_check++))
        fi
    done
    echo
    if [[ $tmp_missing_check -gt 0 ]]; then
      echo "${system} : ERROR - ${tmp_missing_check} / $file_counter covers are missing ROMs!"
    fi
    if [[ $tmp_matching_check -gt '0' ]]; then
      echo "INFO: ${system} : Matched $tmp_matching_check / $file_counter covers to ROMs"
    fi
  done
}

function stripChar(){
  for rom in roms/*/*; do
    base=$(echo "${rom}" | cut -d '/' -f 3);
    basename="${base%.*}" 
    extension="${base##*.}"
    path=${rom%/*}
    if egrep -q "\." <<<"${basename}"; then
      fixedname=$(sed 's/\.//g' <<<"${basename}")
     # mv "${rom}" "${path}""/""${fixedname}"."${extension}"
    fi
  done
}

matchsearch

# for file in * ; do if grep -v "USA" <<<"${file}"; then rm "${file}"; fi; done
# for file in * ; do newname="${file/ \(USA*/.png}"; mv "${file}" "${newname}"; done
# for file in * ; do newname="${file/ \(Euro*/.png}"; mv "${file}" "${newname}"; done

# sudo yum install ImageMagick
# mogrify -resize 250x250\> *.png
# ./flips-linux --apply darkhalf_patch.ips Dark\ Half.sfc patchedRom.sfc
# xdelta3 -d -s rom.sfc patch.IPS patchedRom.sfc
