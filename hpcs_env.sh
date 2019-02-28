#!/bin/bash

# --> clone gitlab repo, as needed.
# # git clone https://github.com/alice-us-grid-sites/job-mix-monitor.git
#
#
# 
# --> environment:

echo "/global/home/users/rjporter/mon/jdk-11" > conf/env.JAVA_HOME
export JAVA_HOME=`cat conf/env.JAVA_HOME`
export PATH=$JAVA_HOME/bin:$PATH
# -> default python is ok

#
# 1) get jar files locally if needed until Costin can fix the ML repo used in the update scripts
# cp ~/mon/MLclient_hpcs/lib/*.jar lib/
# 
# 2) build system if needed
# cd bin; ./recompile.sh ; cd ../
# 
# 3) run client, query ORNL, write to /tmp/jobmix_ornl.txt. 
# ./run_client.sh HPCS /tmp/jobmix_hpcs.txt
# 
# 4) run python evaluation tool
# ./scripts/eval_jobmix.py -i /tmp/jobmix_hpcs.txt
#

