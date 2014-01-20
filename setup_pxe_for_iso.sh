#!/bin/bash
ISO="$1"
HOW="$2"
MNT='/tmp/fuel_auto_iso_tmp'

if [ -f ~/.bmtestsrc ] ; then
	. ~/.bmtestsrc
fi

if [ "$BMTEST_BASE" == "" ] ; then
	BASE='/home/jenkins/fuel_bm_tests'
else
	BASE="$BMTEST_BASE"
fi
if [ "$BMTEST_TFTP_ISO_FILES_OWNER" == "" ] ; then
	USER="jenkins"
else
	USER="$BMTEST_TFTP_ISO_FILES_OWNER"
fi

if [ "$BMTEST_TFTP_ISO_DIR" == "" ] ; then
	TFTP_BASE='/srv/tftp/fuel_bmtests'
else
	TFTP_BASE="$BMTEST_TFTP_ISO_DIR"
fi

if [ "$BMTEST_KS_CFG" == "" ] ; then
	KS_CFG="/srv/tftp/ks_bmtests.cfg"
else
	KS_CFG="$BMTEST_KS_CFG"
fi

if [ "$BMTEST_KS_DIFF" == "" ] ; then
	KS_DIFF="$BASE/ks.diff"
else
	KS_DIFF="$BMTEST_KS_DIFF"
fi

id $USER > /dev/null || exit 1

if [ "$HOW" == "7z" ] ; then
	7z --help > /dev/null || exit 1
fi

if [ "$ISO" == "" ] ; then
	echo "Please provide full path/name to a ISO file as argument"
	exit 1
fi

if ! [ -f "$ISO" ] ; then
	echo "ERROR: Cant's open $ISO"
	exit 1
fi

find "$TFTP_BASE" -type f | xargs -P 1 -L 1 chmod 644
find "$TFTP_BASE" -type d | xargs -P 1 -L 1 chmod 755

if [[ $EUID -eq 0 ]]; then
	su -s /bin/bash $USER -c "rm -rf $TFTP_BASE/*"
	su -s /bin/bash $USER -c "rm -rf $TFTP_BASE/.??*"
else
	rm -rf $TFTP_BASE/*
	rm -rf $TFTP_BASE/.??*
fi

#############
case "$HOW" in
	"7z")
		cd "$TFTP_BASE"
		if [[ $EUID -eq 0 ]]; then
			su -s /bin/bash $USER -c "7z x $ISO"
		else
			7z x $ISO
		fi
		find "$TFTP_BASE" -type f | xargs -P 1 -L 1 chmod 644
		find "$TFTP_BASE" -type d | xargs -P 1 -L 1 chmod 755
		;;
	*)
		mkdir -p $MNT || exit 1
		if [[ $EUID -eq 0 ]]; then
			mount -o loop $ISO $MNT
			su -s /bin/bash $USER -c "rsync -a $MNT/ $TFTP_BASE/"
			umount $MNT
		else
			sudo mount -o loop $ISO $MNT
			rsync -a $MNT/ $TFTP_BASE/
			sudo umount $MNT
		fi
		rmdir $MNT
		;;
esac

#############
rm -f "$KS_CFG"
cp "$TFTP_BASE/ks.cfg" "$KS_CFG" 
patch -p1 "$KS_CFG" < $KS_DIFF || exit 1
echo "DONE"
