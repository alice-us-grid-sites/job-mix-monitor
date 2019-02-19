#!/bin/bash

#
# -- pulls MonaLisa client jar files from repository
#
REPOSITORY=http://monalisa.cern.ch/~repupdate

cd `dirname $0`/lib

for file in *.jar; do
    echo -n "$file ... "
    wget -q ${REPOSITORY}/${file} -O ${file}.tmp && mv ${file}.tmp ${file}
    echo "done"
done
