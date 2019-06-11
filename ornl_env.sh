#!/bin/bash

# --> clone gitlab repo, as needed.
# git clone https://github.com/alice-us-grid-sites/job-mix-monitor.git


# --> environment:
echo "/cvmfs/alice.cern.ch/el6-x86_64/Packages/JDK/10.0.2_JALIEN-2" > conf/env.JAVA_HOME
export JAVA_HOME=`cat conf/env.JAVA_HOME`
export PATH=$JAVA_HOME/bin:$PATH
. /opt/rh/python27/enable 

#
# 1) get jar files locally if needed until Costin can fix the ML repo used in the update scripts
# cp ~/github/job-mix-monitor/lib/*.jar lib/
#
# 2) build system if needed
# cd bin; ./recompile.sh ; cd ../
#
# 3) run client, query ORNL, write to /tmp/jobmix_ornl.txt. 
# ./run_client.sh ORNL /tmp/jobmix_ornl.txt
#
# 4) run python evaluation tool
# ./scripts/eval_jobmix.py -i /tmp/jobmix_ornl.txt

