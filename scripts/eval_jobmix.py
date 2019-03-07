#!/usr/bin/env python

"""

Code which takes MonaLisa client output on cluster use by job type (username) and sorts data for input to local monitor.  

{"Farm":"HPCS","Node":"skar","rss":"10512596.000000","virtualmem":"18711128.000000","count":"5.000000","workdir_size":"493.746094"}
{"Farm":"HPCS","Node":"aborisso","rss":"0.000000","virtualmem":"0.000000","count":"1.000000","workdir_size":"0.085938"}
{"Farm":"HPCS","Node":"junlee","rss":"1704796.000000","virtualmem":"4535596.000000","count":"4.000000","workdir_size":"67.082031"}
{"Farm":"HPCS","Node":"sjaelani","rss":"2438736.000000","virtualmem":"6153948.000000","count":"6.000000","workdir_size":"295.398438"}
{"Farm":"LBL","Node":"alidaq","rss":"0.000000","virtualmem":"0.000000","count":"1.000000","workdir_size":"1122.035156"}
{"Farm":"LBL","Node":"fkellere","rss":"1220420.000000","virtualmem":"2582992.000000","count":"2.000000","workdir_size":"199.242188"}
{"Farm":"LBL","Node":"vvislavi","rss":"16207068.000000","virtualmem":"34908696.000000","count":"23.000000","workdir_size":"95.609375"}
{"Farm":"LBL","Node":"aliprod","rss":"1292168624.000000","virtualmem":"2690549284.000000","count":"1347.000000","workdir_size":"1700731.582031"}

Code output:

    jobmix, sim=12.1 train=74.8 other=13.1
    jobrss, sim_rss=0.73 train_rss=0.72 other_rss=0.50 all_rss=0.69
    jobvmem, sim_vmem=1.71 train_vmem=1.79 other_vmem=1.20 all_vmem=1.70

Where jobmix is in '%',  jobrss in GB, jobvmem in GB

Code is run:

    python jobmix.py -i filename -c cluster

        takes a '-v' option for debugging only
        -c 'LBL' or 'HPCS' or
            if cluster is ommitted, then all lines are processed.
"""

import sys
if sys.version[0:3] < '2.6':
    print "Python version 2.6 or greater required (found: %s)." % \
        sys.version[0:5]
    sys.exit(-1)

import math, os, pprint, re, shlex, shutil, socket, stat, time
from shutil import copyfile
from signal import alarm, signal, SIGALRM, SIGKILL, SIGTERM
from subprocess import Popen, PIPE, STDOUT
import argparse
from ConfigParser import RawConfigParser
from process_commands import process_commands
import json

#---- Gobal defaults ---- Can be overwritten with commandline arguments 

INPUTFILE = 'PUNT' # used to default to /dev/stdin, but removed that option.  Now no default... 
FARMKEY = 'Farm'
OURKEYS = ['count','rss','virtualmem','workdir_size']
OURUSERS = ['aliprod','alitrain','alidaq','users']

#----------------------------------------
class jobmix:
    """ application class """

    def __init__(self, args):
        self.inputfile=args.input_file
        self.cluster = args.cluster
        self.thekeys = OURKEYS
        self.theusers = OURUSERS
        self.mydict = {}
        for user in self.theusers:
            self.mydict[user]={}
        self._zerodata()
        self.proc_c = process_commands(args.verbosity)

#-----------------------------------
    def _zerodata(self):
        for user in self.theusers:
            for key in self.thekeys:
                self.mydict[user][key] = 0.0

#-----------------------------------
    def checkData(self,rdata):
        for key in self.thekeys:
            if key not in rdata:
                self.proc_c.log("Missing key %s" % (key),1)
                return False
        return True

#-----------------------------------
    def filldata(self,adict, data):
        for key in self.thekeys:
            adict[key]+=data[key]

#-----------------------------------
    def store_data(self, rdata):
        if not self.checkData(rdata):
            return
        data = {key:float(rdata[key]) for key in self.thekeys}
        data['rss']=data['rss']/(1024.*1024.)
        data['virtualmem']=data['virtualmem']/(1024.*1024.)
        self.proc_c.log("Filled values %.4f and %.4f and %.4f" % (data['rss'], data['virtualmem'], data['count']), 1)

        done=False
        for key in self.theusers:
            if rdata['Node'] == key:
                self.filldata(self.mydict[key],data)
                done=True
        if not done:
            self.filldata(self.mydict['users'],data)

        self.proc_c.log("Filled values for user=%s " % (rdata['Node']), 1)


#-----------------------------------
    def process_dict(self, adict, numjobs):
        arss = '0.0'
        avmem = '0.0'
        apercent = '0.0'
        atot = '0'
        if adict['count'] > 0:
            arss  = "%.2f" % (adict['rss']/adict['count'])
            avmem = "%.2f" % (adict['virtualmem']/adict['count'])
            apercent = "%.1f" % (100.0*(adict['count']/numjobs))
            atot = "%.0f" % (adict['count'])
        return arss, avmem, apercent, atot

#-----------------------------------
    def process_data(self):
        numjobs = 0.0
        for user in self.theusers:
            numjobs += self.mydict[user]['count']
        if numjobs == 0:
            return
        srss =0.0
        svmem = 0.0
        for user in self.theusers:
            srss += self.mydict[user]['rss']
            svmem+= self.mydict[user]['virtualmem']
        ave_rss = "%.2f" % ((srss)/numjobs)
        ave_vmem = "%.2f" % ((svmem)/numjobs)
        sim_rss, sim_vmem, sim, simtot = self.process_dict(self.mydict['aliprod'],numjobs)
        train_rss, train_vmem, train, traintot = self.process_dict(self.mydict['alitrain'],numjobs)
        daq_rss, daq_vmem, daq, daqtot = self.process_dict(self.mydict['alidaq'],numjobs)
        other_rss, other_vmem, other, othertot = self.process_dict(self.mydict['users'],numjobs)

# --- print the results then zero the containers
        self.proc_c.log("jobtot, sim=%s train=%s daq=%s other=%s" % (simtot,traintot,daqtot,othertot), 0)
        self.proc_c.log("jobmix, sim=%s train=%s daq=%s other=%s" % (sim,train,daq,other), 0)
        self.proc_c.log("jobrss, sim_rss=%s train_rss=%s daq_rss=%s other_rss=%s all_rss=%s" % (sim_rss,train_rss,daq_rss,other_rss,ave_rss),0 )
        self.proc_c.log("jobvmem, sim_vmem=%s train_vmem=%s daq_vmem=%s other_vmem=%s all_vmem=%s" % (sim_vmem,train_vmem,daq_vmem,other_vmem,ave_vmem), 0)
        self._zerodata()

#-----------------------------------
    def go(self):

        rdata = {}
        with open(self.inputfile, 'r') as input:
            for line in input:
                try:
                    rdata = json.loads(line)
                    if self.cluster in line:
                        self.store_data(rdata)
                except (Exception), oops:
                    self.proc_c.log("line = %s, oops=%s" % (line, oops), 0)
            self.process_data()


def main():
    """ Generic program structure to parse args, initialize and start application """
#-------- parse config file to override input and defaults

    desc = """ summarize MLclient output per cluster """

    p = argparse.ArgumentParser(description=desc, epilog="None")
    p.add_argument("-v", "--verbose", action="count", dest="verbosity", default=0, help="be verbose about actions, repeatable")
    p.add_argument("-i",dest="input_file",default=INPUTFILE,help="input text file ... default is punt")
    p.add_argument("-c",dest="cluster",default=FARMKEY,help="cluster name to select.  default is all")
    args = p.parse_args()

    if "PUNT" in args.input_file:
        print "No input file given ... exiting"
        return -1

    try:
        myapp = jobmix(args)
        return(myapp.go())
    except (Exception), oops:
        if args.verbosity >= 2:
            import traceback
            traceback.print_exc()
        else:
            print oops
            return -1
                                                                                                                                                                
if __name__ == "__main__":                      
    sys.exit(main())


