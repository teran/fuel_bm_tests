fuel_bm_tests
=============

Requirements
------------
test_env.py:
* python modules: ipaddr, sys, os, re, logging, time, argparse

bm_tests.sh:
* working ```test_env.py```
* ipmitool
* dnsmasq
* tftp

Usage
-----
* ```test_env.py``` basic usage:

```bash
git clone https://github.com/adidenko/fuel_bm_tests
cd fuel_bm_tests
export PYTHONPATH="./pylibs:./environments"
python test_env.py --help
```

* deploying your own customized environment example:

```bash
git clone https://github.com/adidenko/fuel_bm_tests
cd fuel_bm_tests
mkdir /tmp/myenvs
cp environments/010_centos_kvm_nova_flat_3nodes.py /tmp/myenvs/myenv01.py
# customize env
vim /tmp/myenvs/myenv01.py
# export updated PYTHONPATH
export PYTHONPATH="./pylibs:./environments:./tmp/myenvs"
# you're ready to go
python test_env.py --help
```


* Jenkins jobs example for bare-metal tests:

    * Copy ```.bmtestsrc``` file to your jenkins user homedir
    * Edit ```.bmtestsrc``` in your jenkins user homedir to adjust it to your bare-metal environment
    * Create a jenkins jobs with the following Build action (shell script):

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

