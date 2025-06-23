for file in *.iso; do
	name=$(basename "${file}")
	mkdir -p tmpmnt && mount -o loop "${name}" tmpmnt/
	mkdir "${name/iso/ps3}"
	echo "Copying data for ${name/.iso/}"
	cp -rv tmpmnt/* "${name/iso/ps3}"/
	echo "Unmounting..."
	umount "${name}"
	echo "Squashing ${name/iso/}.."
	mksquashfs "${name/iso/ps3}" "${name/iso/ps3.squashfs}" -comp xz
	echo "Cleaning up..."
	rm -rf "${name/iso/ps3}"
	echo "Done"
done
