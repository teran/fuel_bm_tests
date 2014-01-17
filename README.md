fuel_bm_tests
=============

Requirements
------------
* python modules: ipaddr, sys, os, re, logging, time, argparse
* ipmitool (for bare-metal)

Usage
-----
* test_env.py usage:

```bash
git clone https://github.com/adidenko/fuel_bm_tests
cd fuel_bm_tests
export PYTHONPATH="./pylibs:./environments"
python test_env.py --help
```

* Jenkins jobs example for bare-metal tests:

```bash
export BMTEST_BASE="$WORKSPACE"
export JENKINS_BUILD_URL="$BUILD_URL"
rm -rf logs/* ./RESULT.txt ./RESULT.html ./*anaconda.log ./SUMMARY.txt
./bm_tests.sh html-report $ENVIRONMENT_NAME
if [ -s ./*anaconda.log ] ; then
    mv ./*anaconda.log $ARTIFACTS_DIR/ || true
fi
cat ./RESULT.html >> $ARTIFACTS_DIR/RESULT.html
```

