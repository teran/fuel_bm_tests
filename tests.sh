#!/bin/bash

if [ -f ~/.bmtestsrc ] ; then
	. ~/.bmtestsrc
fi

export PYTHONPATH="$BMTEST_BASE/pylibs:./environments"
PYTHON_BIN="/usr/bin/python"

FUEL_MASTER_NODE=`grep -o "ip=[[:digit:]]\+\.[[:digit:]]\+\.[[:digit:]]\+\.[[:digit:]]\+" ./pxelinux.bootpxe | cut -d= -f2`
if [ "$?" != "0" ] ; then
	FUEL_MASTER_NODE="192.168.128.10"
fi

#echo "PYTHONPATH=$PYTHONPATH"

if [ "$BMTEST_OSNODES_IPMI_IPS" == "" ] ; then
	TOTAL_OS_NODES=4
else
	TOTAL_OS_NODES=`echo $BMTEST_OSNODES_IPMI_IPS | wc -w`
fi

if [[ $EUID -eq 0 ]]; then
	echo "Don't run it as root"
	exit 1
fi

ARGS=""
for arg in "$@" ; do
	if [ "$arg" == "keep-env" ] || [ "$arg" == "keep_env" ]; then
		ARGS="$ARGS -k"
		continue
	fi
	if [ "$arg" == "create-only" ] || [ "$arg" == "create_only" ]; then
		ARGS="$ARGS -c"
		continue
	fi
	if [ -f "$arg" ] ; then
		env=`basename $arg | sed -e 's#\.py$##'`
	else
		env="$arg"
	fi
	if ! grep -q 'release' "$LOGDIR/fuel.version" ; then
		echo "ERROR: No release found via http://$FUEL_MASTER_NODE:8000/api/version"
		exit 1
	fi
	echo
	DISCOVERED_NODES=`curl -s -X GET http://$FUEL_MASTER_NODE:8000/api/nodes | python -mjson.tool | grep discover | wc -l`
	echo "##### Running tests for environment: $env #####"
	if [ "$DISCOVERED_NODES" != "$TOTAL_OS_NODES" ] ; then
		echo "Discovered nodes: $DISCOVERED_NODES, but should be $TOTAL_OS_NODES. Rebooting nodes."
		./reboot_nodes.sh y &>/dev/null
		sleep 180
	fi
	ts=`date +"%Y-%m-%d_%H-%M-%S"`
	LOGDIR="./logs/${ts}_${env}"
	LOG="$LOGDIR/bmtest.out"
	mkdir -p "$LOGDIR"
	curl -s http://$FUEL_MASTER_NODE:8000/api/version > "$LOGDIR/fuel.version"
		
	# run tests
	$PYTHON_BIN run_tests.py $ARGS $FUEL_MASTER_NODE $env $LOG
	SNAPSHOT="NONE"
	if curl -s -X GET --data '' http://$FUEL_MASTER_NODE:8000/api/tasks | grep status | grep dump | grep ready | grep 'fuel-snapshot'  &>/dev/null ; then
		URI=`curl -s -X GET --data '' http://$FUEL_MASTER_NODE:8000/api/tasks | grep status | grep dump | grep ready | grep -o '/dump/fuel-snapshot.*tgz'`
		SNAPSHOT=`echo $URI | grep -o "fuel-snapshot.*tgz"`
		SNAPDIR=`echo $SNAPSHOT | sed -e 's#\.tgz$##'`
		wget -q -O $LOGDIR/snapshot.tgz http://$FUEL_MASTER_NODE:8000$URI

		pushd $LOGDIR &>/dev/null
			tar xzf snapshot.tgz &>/dev/null
			mkdir -p $SNAPDIR
		popd &>/dev/null

		pushd $LOGDIR/$SNAPDIR &>/dev/null
			mkdir -p tmplogs
			for curnode in node-* ; do mv localhost/var/log/remote/$curnode tmplogs/ ; done
			rm -rf localhost/var/log/remote/node-*
			mv tmplogs/node-* localhost/var/log/remote/
			rm -rf tmplogs
		popd &>/dev/null

		pushd $LOGDIR &>/dev/null
			rm -f $SNAPSHOT snapshot.tgz
			tar czf $SNAPSHOT $SNAPDIR
			rm -rf ./$SNAPDIR
		popd &>/dev/null
	fi
done
