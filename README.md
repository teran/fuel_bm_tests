fuel_bm_tests
=============

Requirements
------------
manage_env.py:
* python modules: ipaddr, sys, os, re, logging, time, argparse

bm_tests.sh:
* working ```manage_env.py```
* ipmitool
* dnsmasq
* tftp
* zip

Usage
-----
* ```manage_env.py``` basic usage:

```bash
git clone https://github.com/adidenko/fuel_bm_tests
cd fuel_bm_tests
export PYTHONPATH="./pylibs:./environments"
python manage_env.py --help
```

* deploying your own custom environment example:

```bash
# set your fuel master node IP address
export FUEL_MASTER_NODE="172.16.100.100"

# get the tool
git clone https://github.com/adidenko/fuel_bm_tests
cd fuel_bm_tests

# create your env file
mkdir /tmp/myenvs
cp environments/010_centos_kvm_nova_flat_3nodes.py /tmp/myenvs/myenv01.py

# customize env file
vim /tmp/myenvs/myenv01.py

# export updated PYTHONPATH to include path to your custom envs
export PYTHONPATH="./pylibs:./environments:/tmp/myenvs"

# you're ready to go
python manage_env.py --help
python manage_env.py $FUEL_MASTER_NODE myenv01 create /tmp/myenv01.log && \
python manage_env.py $FUEL_MASTER_NODE myenv01 netverify /tmp/myenv01.log && \
python manage_env.py $FUEL_MASTER_NODE myenv01 deploy /tmp/myenv01.log

# you can run OpenStack Health Check, detailed results will be saved in $LOG.ostf
python manage_env.py $FUEL_MASTER_NODE myenv01 ostf /tmp/myenv01.log
cat /tmp/myenv01.log.ostf
```


* Jenkins jobs example for bare-metal tests:

    * Copy ```.bmtestsrc``` file to your jenkins user homedir
    * Edit ```.bmtestsrc``` in your jenkins user homedir to adjust it to your bare-metal environment
    * Create a jenkins job with the following Build action (shell script):

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

