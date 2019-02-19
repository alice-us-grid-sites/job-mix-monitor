#!/bin/bash

#
# run_client.sh clusters outfile
#
# example:
#   run_client.sh "HPCS:LBL:ORNL" /tmp/us_sites.txt
#

export JAVA_HOME=`cat conf/env.JAVA_HOME`
export PATH=$JAVA_HOME/bin:$PATH

# HPCS, LBL, or ORNL
cluster=$1
outfile=$2

CP="bin"

for a in lib/*.jar; do
    CP="$CP:$a"
done

#set -o noclobber

java \
    -server -Xmx256m -XX:CompileThreshold=500 \
    -classpath ${CP} \
    -Djava.security.policy=bin/policy.all \
    -Dlia.Monitor.ConfigURL=file:conf/App.properties \
    -Djava.util.logging.config.class=lia.Monitor.monitor.LoggerConfigClass \
    JobMixClient -o "$outfile" -c "$cluster" >>/dev/null 2>&1 & 

