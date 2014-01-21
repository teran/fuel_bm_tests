#!/bin/bash

if [ -f ~/.bmtestsrc ] ; then
	. ~/.bmtestsrc
fi

if [ "$BMTEST_BASE" == "" ] ; then
	BASE='/home/jenkins/fuel_bm_tests'
else
	BASE="$BMTEST_BASE"
fi

if [ "$BMTEST_OSNODES_IPMI_IPS" == "" ] ; then
	IPMI="172.16.1.101 172.16.1.102 172.16.1.103"
else
	IPMI="$BMTEST_OSNODES_IPMI_IPS"
fi

if [ "$BMTEST_OSNODES_IPMI_USER" == "" ] ; then
	USER='jenkins'
else
	USER="$BMTEST_OSNODES_IPMI_USER"
fi

if [ "$BMTEST_OSNODES_IPMI_PASS" == "" ] ; then
	PASS='ipmipass'
else
	PASS="$BMTEST_OSNODES_IPMI_PASS"
fi


if [ "$1" == "" ] ; then
        read -p "Are you sure you want to reboot OpenStack nodes? (y/N):" rpl
else
        rpl="$1"
fi

if [ "$rpl" == "Y" ] || [ "$rpl" == "y" ] ; then
	for host in $IPMI; do
		echo -ne "$host \t"
		ipmitool -H $host -U $USER -P $PASS chassis bootdev pxe
		sleep 1
		ipmitool -H $host -U $USER -P $PASS power reset
		sleep 1
	done
fi
echo DONE
