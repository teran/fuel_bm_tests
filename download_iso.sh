#!/bin/bash

if [ -f ~/.bmtestsrc ] ; then
	. ~/.bmtestsrc
fi

if [ "$BMTEST_ISO_DOWNLOAD_DIR" == "" ] ; then
	ISODIR='/home/jenkins/fueliso'
else
	ISODIR="$BMTEST_ISO_DOWNLOAD_DIR"
fi

URL="$1"

if [ "$URL" == "" ] ; then
        echo "Please provide ISO URL as argument"
        exit 1
fi

mkdir -p "$ISODIR" || exit 1
fuel_iso_name=`echo $URL | egrep -o 'fuel-.*\.iso'`

if [ ! -f "$ISODIR/$fuel_iso_name" ] ; then
	wget -O "$ISODIR/$fuel_iso_name" "$URL" || exit 1
fi
echo "$ISODIR/$fuel_iso_name"
