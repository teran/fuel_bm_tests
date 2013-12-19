#!/bin/bash

if [ -f ~/.bmtestsrc ] ; then
	. ~/.bmtestsrc
fi

if [ "$BMTEST_BASE" == "" ] ; then
	BASE='/home/jenkins'
else
	BASE="$BMTEST_BASE"
fi

if [ "$BMTEST_FUELNODE_IPMI_IP" == "" ] ; then
	IPMI="192.168.168.168"
else
	IPMI="$BMTEST_FUELNODE_IPMI_IP"
fi

if [ "$BMTEST_FUELNODE_IPMI_USER" == "" ] ; then
	USER='jenkins'
else
	USER="$BMTEST_FUELNODE_IPMI_USER"
fi

if [ "$BMTEST_FUELNODE_IPMI_PASS" == "" ] ; then
	PASS='ipmipass'
else
	PASS="$BMTEST_FUELNODE_IPMI_PASS"
fi

if [ "$1" == "" ] ; then
	read -p "Are you sure you want to reboot fuel node? (y/N):" rpl
else
	rpl="$1"
fi

if [ "$rpl" == "Y" ] || [ "$rpl" == "y" ] ; then
	for host in $IPMI; do
		echo -ne "$host \t"
		ipmitool -H $host -U $USER -P $PASS power reset
	done
fi
