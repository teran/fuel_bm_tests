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
HTML_REP=""
rm -f ./RESULT.txt ./RESULT.html

for arg in "$@" ; do
	if [ "$arg" == "keep-env" ] || [ "$arg" == "keep_env" ]; then
		ARGS="$ARGS -k"
		continue
	fi
	if [ "$arg" == "create-only" ] || [ "$arg" == "create_only" ]; then
		ARGS="$ARGS -c"
		continue
	fi
	if [ "$arg" == "html-report" ] || [ "$arg" == "html_report" ]; then
		HTML_REP="yes"
		continue
	fi

	if [ -f "$arg" ] ; then
		env=`basename $arg | sed -e 's#\.py$##'`
	else
		env="$arg"
	fi
	echo
	ts=`date +"%Y-%m-%d_%H-%M-%S"`
	LOGDIR="./logs/${ts}_${env}"
        env_name="${ts}_${env}"
	LOG="$LOGDIR/bmtest.out"
	mkdir -p "$LOGDIR"
	curl -s http://$FUEL_MASTER_NODE:8000/api/version > "$LOGDIR/fuel.version"
	if ! grep -q 'release' "$LOGDIR/fuel.version" ; then
		echo "ERROR: No release found via http://$FUEL_MASTER_NODE:8000/api/version"
		exit 1
	fi

	# run tests
	DISCOVERED_NODES=`curl -s -X GET http://$FUEL_MASTER_NODE:8000/api/nodes | python -mjson.tool | grep discover | wc -l`
	echo "##### Running tests for environment: $env #####"
	echo "##### Running tests for environment: $env #####" >> ./RESULT.txt
	if [ "$DISCOVERED_NODES" != "$TOTAL_OS_NODES" ] ; then
		echo "Discovered nodes: $DISCOVERED_NODES, but should be $TOTAL_OS_NODES. Rebooting nodes."
		./reboot_nodes.sh y &>/dev/null
		sleep 180
	fi
	$PYTHON_BIN run_tests.py $ARGS $FUEL_MASTER_NODE $env $LOG
	cat $LOG >> ./RESULT.txt
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
			egrep 'crit:|raise LVMError' localhost/var/log/remote/node-*/install/anaconda.log > anaconda.log
		popd &>/dev/null

		mv $LOGDIR/$SNAPDIR/anaconda.log ./${ts}_${env}.anaconda.log &>/dev/null

		pushd $LOGDIR &>/dev/null
			rm -f $SNAPSHOT snapshot.tgz
			tar czf $SNAPSHOT $SNAPDIR
			rm -rf ./$SNAPDIR
		popd &>/dev/null
	fi
	if [ ! -z "$HTML_REP" ] ; then
		HTML="$LOG.html"
		grep -q 'ERROR' $LOG && RES="<font color=red>FAILED</font>" || RES="<font color=green>PASSED</font>"
		# Add results zip download link
		ZIP="<a href='${JENKINS_BUILD_URL}artifact/artifacts/$env_name.zip'>Download results</a>"
		
		cat <<EOF > $HTML
		<a href="#" onclick="document.getElementById('${env_name}_descr_div').style.display=(document.getElementById('${env_name}_descr_div').style.display=='block')?'none':'block';">$env_name</a> - <a href="#" onclick="document.getElementById('${env_name}_div').style.display=(document.getElementById('${env_name}_div').style.display=='block')?'none':'block';">$RES</a> - $ZIP<br>
		<div id='${env_name}_descr_div' style='display:none;background-color:#FBFBF1;border:1px solid black;width:80%;margin:1%;'><pre>
EOF
		cat ./environments/$env.py >> $HTML
		echo "</pre></div>" >> $HTML

		cat <<EOF >> $HTML
		<div id='${env_name}_div' style='display:none;background-color:#F2F2F2;border:1px solid black;width:80%;margin:1%;'>
EOF
		
		sed -e 's#OK#<font color="green">OK</font>#g' \
		-e 's#ERROR#<font color="red">ERROR</font>#g' \
		-e 's#$#<br>#' \
		-e 's#\t#\&nbsp;\&nbsp;\&nbsp;\&nbsp;\&nbsp;\&nbsp;#' \
		$LOG >> $HTML

		# add anaconda to HTML report
		if [ -s "./${ts}_${env}.anaconda.log" ] ; then
			cat <<EOF >> $HTML
			<a href="#" onclick="document.getElementById('${env_name}_anaconda_div').style.display=(document.getElementById('${env_name}_anaconda_div').style.display=='block')?'none':'block';">Show/Hide Anaconda errors</a><br>
			<div id='${env_name}_anaconda_div' style='display:none;background-color:#FBF0F0;border:1px solid black;width:80%;margin:1%;'><pre>
EOF
			cat "./${ts}_${env}.anaconda.log" >> $HTML
			echo "</pre></div>" >> $HTML
		fi

		cat <<EOF >> $HTML
		<a href="#" onclick="document.getElementById('${env_name}_ostf_div').style.display=(document.getElementById('${env_name}_ostf_div').style.display=='block')?'none':'block';">Show/Hide OSTF results</a>
EOF
		
		OSTF=`sed -e 's#$#<br>#' -e 's#success#<font color="green">success</font>#g' -e 's#failure#<font color="red">failure</font>#g' -e 's#\t#\&nbsp;\&nbsp;\&nbsp;\&nbsp;\&nbsp;\&nbsp;#' ${LOG}.ostf`
		echo "<div id='${env_name}_ostf_div' style='display:none;background-color:#FBFBFB;border:1px solid black;width:80%;margin:1%;'>" >> $HTML
		echo "$OSTF</div></div>" >> $HTML
		cat $HTML >> ./RESULT.html
		echo '<br>' >> ./RESULT.html
	fi
	grep -q 'ERROR' $LOG && PT_RES="FAILED" || PT_RES="PASSED"
	echo "$env_name - $PT_RES" >> ./SUMMARY.txt
done
