#!/usr/bin/env python

"""

Code which takes MonaLisa client output on cluster use by job type (username) and sorts data for input to local monitor.  

{"Farm":"LBL_HPCS","Node":"sparmar","rss":"540160.000000","virtualmem":"2515380.000000","cpu_time":"2.000000","run_time":"139.000000","count":"8.000000","workdir_size":"1.898438"}
{"Farm":"LBL_HPCS","Node":"yozhou","rss":"4190052.000000","virtualmem":"16899908.000000","cpu_time":"0.000000","run_time":"1752.000000","count":"15.000000","workdir_size":"187.578125"}
{"Farm":"LBL_HPCS","Node":"aliprod","rss":"1214092232.000000","virtualmem":"2746202196.000000","cpu_time":"135348.000000","run_time":"156530.000000","count":"1329.000000","workdir_size":"1868899.160156"}
{"Farm":"LBL_HPCS","Node":"ymao","rss":"23633024.000000","virtualmem":"30936420.000000","cpu_time":"445.000000","run_time":"516.000000","count":"4.000000","workdir_size":"20.808594"}


Code output:

alice nsim=1329.0,ntrain=4.0,ndaq=0,nother=27.0,nall=1360,psim=97.7,ptrain=0.3,pdaq=0.0,pother=2.0,sim_rss=0.87,train_rss=0.50,daq_rss=0.0,other_rss=1.00,all_rss=0.87,sim_vmem=1.97,train_vmem=1.44,daq_vmem=0.0,other_vmem=1.78,all_vmem=1.97,sim_eff=86.47,train_eff=2.01,daq_eff=0.00,other_eff=18.57,all_eff=84.87



Code is run:

    python eval_jobmix.py -i filename [-c cluster]

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
from datetime import datetime
from signal import alarm, signal, SIGALRM, SIGKILL, SIGTERM
from subprocess import Popen, PIPE, STDOUT
import argparse
from ConfigParser import RawConfigParser
from process_commands import process_commands
import json

#---- Gobal defaults ---- Can be overwritten with commandline arguments 

INPUTFILE = 'PUNT' # used to default to /dev/stdin, but removed that option.  Now no default... 
FARMKEY = 'Farm'
OURKEYS = ['count','rss','cpu_time','run_time','virtualmem','workdir_size']
OURUSERS = ['aliprod','alitrain','alidaq','users']
MAX_AVMEM=6.0

#----------------------------------------
class jobmix:
    """ application class """

    def __init__(self, args):
        self.inputfile=args.input_file
        self.cluster = args.cluster
        self.maxavmem=args.maxavmem
        self.thekeys = OURKEYS
        self.theusers = OURUSERS
        self.mydict = {}
        self.njobs = 0.0
        for user in self.theusers:
            self.mydict[user]={}
        self._zerodata()
        self.proc_c = process_commands(args.verbosity)

#-----------------------------------
    def _zerodata(self):
        for user in self.theusers:
            for key in self.thekeys:
                self.mydict[user][key] = 0.0
        self.njobs = 0.0

#-----------------------------------
    def checkData(self,rdata):
        # fill in any missing keys - support new keys added later
        for key in self.thekeys:
            if key not in rdata:
                rdata[key]=0.0
        return rdata

#-----------------------------------
    def filldata(self,adict, data):
        self.njobs += data['count']
        for key in self.thekeys:
            adict[key]+=data[key]

#---------------------------------------------
    def save_badpeople(self, data, uname):
        # write out a /tmp/<username>.dat file containing timestamp and amount of memory
        self.proc_c.log("will test against %2.f" % (self.maxavmem), 1)

        if data['count'] > 0.:
            vmem=data['virtualmem']/data['count']
            if vmem > self.maxavmem:
                fname= uname.join(["/tmp/",".dat"])
                fp = open(fname,"a+")
                json.dump(data,fp)
                date_time=(datetime.now()).strftime("%m-%d-%Y %H:%M:%S")
                endstr=date_time.join([" ","\n"])
                fp.write(endstr)

#-----------------------------------
    def store_data(self, rdata):
#       Fill in missing keys so code runs smoothly
        xdata = self.checkData(rdata)

        data = {key:float(xdata[key]) for key in self.thekeys}
        data['rss']=data['rss']/(1024.*1024.)
        data['virtualmem']=data['virtualmem']/(1024.*1024.)
        self.save_badpeople(data,xdata['Node'])

        self.proc_c.log("Filled values %.4f and %.4f and %.4f" % (data['rss'], data['virtualmem'], data['count']), 1)

# data is either one of the Node keynames (aliprod, alitrain, or alidaq) or a general user.  Try Nodes, if not, assume it's added to 'users'.
        done=False
        for key in self.theusers:
            if rdata['Node'] == key:
                self.filldata(self.mydict[key],data)
                done=True
        if not done:
            self.filldata(self.mydict['users'],data)

        self.proc_c.log("Filled values for user=%s " % (xdata['Node']), 1)


#-----------------------------------
    def process_dict(self, adict):
        ''' Calculate a set of averages & the cpu eff (cputime/runtime), & return the set'''
        arss = 0.0
        avmem = 0.0
        apercent = 0.0
        atot = 0
        aeff = 0.0
        if adict['count'] > 0:
            arss  = (adict['rss']/adict['count'])
            avmem = (adict['virtualmem']/adict['count'])
            apercent = (100.0*(adict['count']/self.njobs))
            atot = (adict['count'])
            if adict['run_time'] > 0:
                aeff = (100.0*(adict['cpu_time']/adict['run_time']))
        return arss, avmem, apercent, atot, aeff

#-----------------------------------
    def process_data(self):
        if self.njobs == 0: 
            return

        arss  = 0.0
        avmem = 0.0
        for user in self.theusers:
            arss  += self.mydict[user]['rss']
            avmem += self.mydict[user]['virtualmem']
        arss  /= self.njobs
        avmem /= self.njobs

        sim_rss, sim_vmem, sim, simtot, sim_eff = self.process_dict(self.mydict['aliprod'])
        train_rss, train_vmem, train, traintot, train_eff = self.process_dict(self.mydict['alitrain'])
        daq_rss, daq_vmem, daq, daqtot, daq_eff = self.process_dict(self.mydict['alidaq'])
        other_rss, other_vmem, other, othertot, other_eff = self.process_dict(self.mydict['users'])

        aeff = ((simtot*sim_eff+traintot*train_eff+daqtot*daq_eff+othertot*other_eff)/self.njobs)
#
# -- one line format for grafana consumption
#
        self.proc_c.log("alice \
nsim=%d,ntrain=%d,ndaq=%d,nother=%d,nall=%d,\
psim=%.1f,ptrain=%.1f,pdaq=%.1f,pother=%.1f,\
sim_rss=%.2f,train_rss=%.2f,daq_rss=%.2f,other_rss=%.2f,all_rss=%.2f,\
sim_vmem=%.2f,train_vmem=%.2f,daq_vmem=%.2f,other_vmem=%.2f,all_vmem=%.2f,\
sim_eff=%.2f,train_eff=%.2f,daq_eff=%.2f,other_eff=%.2f,all_eff=%.2f" 

                % (simtot,traintot,daqtot,othertot,self.njobs,
                    sim,train,daq,other,
                    sim_rss,train_rss,daq_rss,other_rss,arss,
                    sim_vmem,train_vmem,daq_vmem,other_vmem,avmem,
                    sim_eff,train_eff,daq_eff,other_eff,aeff), 0)

        self._zerodata()

#-----------------------------------
    def go(self):
        ''' Job reads the input file line-by-line until end of file, as each pass of the client replaces input file.
        Each line contains the records for 1 username, 
        Each line is stored in one of the predefined dicts: aliprod, alitrain, alidaq, users. 
        At end of file, process the data
        Process = do some simple math, write a high memory user file for tracking, write a one line output for feeding grafana'''

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
    p.add_argument("-x",dest="maxavmem",type=float, default=MAX_AVMEM,help="max ave vmem, over which user info is written to /tmp/<username.dat")

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


