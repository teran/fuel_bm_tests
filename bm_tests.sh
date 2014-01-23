#!/bin/bash

SLEEP="sleep 30"

if [ -f ~/.bmtestsrc ] ; then
	. ~/.bmtestsrc
fi

export PYTHONPATH="$BMTEST_BASE/pylibs:$BMTEST_ENV_DIR"
PYTHON_BIN="/usr/bin/python"

FUEL_MASTER_NODE=`grep -o "ip=[[:digit:]]\+\.[[:digit:]]\+\.[[:digit:]]\+\.[[:digit:]]\+" $BMTEST_PXE_BOOT_FUEL_NODE | cut -d= -f2`
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
                continue
        fi
        if [ "$arg" == "create-only" ] || [ "$arg" == "create_only" ]; then
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
	rm -rf "./logs/${ts}_${env}"
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
		echo -n "Discovered nodes: $DISCOVERED_NODES, but should be $TOTAL_OS_NODES. Rebooting nodes ."
		./reboot_nodes.sh y &>/dev/null
		for i in {1..30} ; do
			DISCOVERED_NODES=`curl -s -X GET http://$FUEL_MASTER_NODE:8000/api/nodes | python -mjson.tool | grep discover | wc -l`
			if [ "$DISCOVERED_NODES" != "$TOTAL_OS_NODES" ] ; then
				echo -n "."
				sleep 10
			else
				echo "DONE"
				break
			fi
		done
	fi
	DISCOVERED_NODES=`curl -s -X GET http://$FUEL_MASTER_NODE:8000/api/nodes | python -mjson.tool | grep discover | wc -l`
	if [ "$DISCOVERED_NODES" != "$TOTAL_OS_NODES" ] ; then
		echo "TIMEOUT. Discovered only $DISCOVERED_NODES of $TOTAL_OS_NODES nodes. Exiting"
		continue
	fi

	# Let's rock-n-roll
	DEPLOY="no"
	if `echo "$@" | egrep -q 'create_only|create-only'`; then
		$PYTHON_BIN manage_env.py $ARGS $FUEL_MASTER_NODE $env remove $LOG
		$PYTHON_BIN manage_env.py $ARGS $FUEL_MASTER_NODE $env create $LOG
	else
		$PYTHON_BIN manage_env.py $ARGS $FUEL_MASTER_NODE $env remove $LOG
		$PYTHON_BIN manage_env.py $ARGS $FUEL_MASTER_NODE $env create $LOG && \
		$SLEEP && \
		$PYTHON_BIN manage_env.py $ARGS $FUEL_MASTER_NODE $env netverify $LOG && \
		$SLEEP && \
		$PYTHON_BIN manage_env.py $ARGS $FUEL_MASTER_NODE $env deploy $LOG && \
		(
			DEPLOY="done"
			$SLEEP && \
			$PYTHON_BIN manage_env.py $ARGS $FUEL_MASTER_NODE $env netverify $LOG 
			$SLEEP && \
			$PYTHON_BIN manage_env.py $ARGS $FUEL_MASTER_NODE $env ostf $LOG
		) || DEPLOY="failed"
	fi

	$PYTHON_BIN manage_env.py $ARGS $FUEL_MASTER_NODE $env snapshot $LOG

	if `echo "$@" | egrep -qv 'keep_env|keep-env|create_only|create-only'`; then
		$PYTHON_BIN manage_env.py $ARGS $FUEL_MASTER_NODE $env remove $LOG
	fi

	# Now lets prepare results and reports
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
			if [ "$DEPLOY" != "no" ] ; then
				egrep 'crit:|raise LVMError' localhost/var/log/remote/node-*/install/anaconda.log > anaconda.log
			fi
		popd &>/dev/null

		if [ -f "$LOGDIR/$SNAPDIR/anaconda.log" ] ; then
			mv $LOGDIR/$SNAPDIR/anaconda.log ./${ts}_${env}.anaconda.log &>/dev/null
		fi

		pushd $LOGDIR &>/dev/null
			rm -f $SNAPSHOT snapshot.tgz
			tar czf $SNAPSHOT $SNAPDIR
			rm -rf ./$SNAPDIR
		popd &>/dev/null
	fi
	if [ ! -z "$HTML_REP" ] ; then
		HTML="$LOG.html"
		if [ -s "./${ts}_${env}.anaconda.log" ] ; then
			ANACONDA_ERR=" (Anaconda errors)"
		else
			ANACONDA_ERR=""
		fi
		grep -q 'ERROR' $LOG && RES="<font color=red>FAILED$ANACONDA_ERR</font>" || RES="<font color=green>PASSED$ANACONDA_ERR</font>"
		# Add results zip download link
		ZIP="<a href='${JENKINS_BUILD_URL}artifact/artifacts/$env_name.zip'>Download results</a>"
		
		cat <<EOF > $HTML
		<a href="#" onclick="document.getElementById('${env_name}_descr_div').style.display=(document.getElementById('${env_name}_descr_div').style.display=='block')?'none':'block';">$env_name</a> - <a href="#" onclick="document.getElementById('${env_name}_div').style.display=(document.getElementById('${env_name}_div').style.display=='block')?'none':'block';">$RES</a> - $ZIP<br>
		<div id='${env_name}_descr_div' style='display:none;background-color:#FBFBF1;border:1px solid black;width:80%;margin:1%;'>
EOF
		echo -n "ISO: " >> $HTML
		cat $LOGDIR/fuel.version >> $HTML
		echo -e "<br><br><pre>" >> $HTML
		cat $BMTEST_ENV_DIR/$env.py >> $HTML
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
