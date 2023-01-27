#!/bin/bash

# Grab .chd file
for f in ./**/*.chd
do
	name=${f%.chd} # Remove '.chd' from file name
	chdman extractcd -i "$name.chd" -o "$name.cue" --force
done


for file in *.chd; do chdman extractcd -i "${file}" -o "${file%.chd}.cue" --force