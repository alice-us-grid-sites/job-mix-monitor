### Job Mix Monitor

**Purpose:**
Monitor the mix of jobs types(_sim_, _train_, _reco_, _other_) running on one or more identified grid sites, tabulate average usage for _rss_ and _vmem_.

#### Implementation

Simple MLclient code (bin/JobMixClient.java) registers with sites and queries a specific set of information.  That information is periodically updated, organized and written to a _tmp_ file. Once sufficient data is obtain (e.g. results from every cluster requested or timeout period), the _tmp_ file is moved to a target file for additional processing and upload to local monitoring apparatus (e.g. _grafana_).

Additional processing is done via python script (scripts/eval_jobmix.py) to evaluate sums and averages for upload to local monitor.

**For site specific prep, build, & run see:** _ornl_env.sh_ and _hpcs_env.sh_ 

#### Prepare

* obtain set of jar files from monalisa repository.  See update_mlclient.sh and lib/list_of_jarfiles.txt
* jdk installed and add file "conf/env.JAVA_HOME" containing the path to the jdk
* python 2.7.x installed


#### Build

* run update_mkclient.sh as needed one the original jar files are installed
* cd bin/;  ./recompile.sh

#### Run MonaLisa Client code

* ./run_client.sh Site1:Site2:Site3 outputfile


Code will run in background, write to "outputfile.tmp" until all three sites have reported, then copy outputfile.tmp to outputfile, and repeat.  Only 1 site is ok.

#### Run python evaluation

* ./scripts/eval_jobmix.py -i inputfile [-c Site]

where inputfile is output of MonaLisa client and Site is optional to select an individual site. Without that all sites are added together.  The output is:

jobmix, sim=69.8 train=26.0 daq=0.1 other=4.1

jobrss, sim_rss=1.00 train_rss=1.05 daq_rss=0.00 other_rss=0.55 all_rss=0.99

jobvmem, sim_vmem=2.38 train_vmem=2.59 daq_vmem=0.00 other_vmem=1.59 all_vmem=2.40

This says, 69.8% of jobs are simulation, with average rss of 1.0GB and vmem of 2.38GB.  And so one. _other_ are all individual users.





