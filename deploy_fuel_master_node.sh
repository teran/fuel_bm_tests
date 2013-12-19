#!/bin/bash

if [ -f ~/.bmtestsrc ] ; then
	. ~/.bmtestsrc
fi

if [ "$BMTEST_BASE" == "" ] ; then
	BASE='/home/jenkins/fuel_bm_tests'
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

if [ "$BMTEST_PXECFG" == "" ] ; then
	PXECFG='/srv/tftp/pxelinux.cfg/01-00-22-33-44-55-66'
else
	PXECFG="$BMTEST_PXECFG"
fi

ipmitool -H $IPMI -U $USER -P $PASS chassis bootdev pxe

cp $BASE/pxelinux.bootpxe $PXECFG
$BASE/reboot_fuel.sh y
sleep 180 && ipmitool -H $IPMI -U $USER -P $PASS chassis bootdev disk &>/dev/null &
sleep 180 &&  cp $BASE/pxelinux.bootlocal $PXECFG &

echo DONE
