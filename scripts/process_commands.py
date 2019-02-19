#!/usr/bin/env python

"""
Set of routines that are used to run and kill a shell command as needed
"""
import math, os, pprint, re, shlex, shutil, socket, stat, time
from datetime import datetime
from signal import alarm, signal, SIGALRM, SIGKILL, SIGTERM
from subprocess import Popen, PIPE, STDOUT
import smtplib
from email.mime.text import MIMEText
import getpass

class commException(Exception):
    def __init__(self, command, status, output):
        self.command = command
        self.status = status
        self.output = output
    def __str__(self):
        return "Command failed: '%s' with status '%s'" % (self.command,
                                                          self.status)

class process_commands:
    """ class to support process management """
    def __init__(self,verbosity):
        self.verbosity = verbosity
        self._logIndent = 0
        self.dry_run = False

    def log(self, msg, verbosity=1):
        """ print message as is if verbosity level is exceeded """
        if self.verbosity < verbosity:
            return
        indent = " " * (verbosity + self._logIndent)
        if isinstance(msg, str):
            print indent + msg
        elif isinstance(msg, commException):
            print indent + str(msg)
        else:
            pprint.pprint(msg, depth=6)


    def _get_process_progeny(self, pid):

        """ A helper funciton for _kill_progeny to try and find all
        child processes spawned (and children of children, etc.) of a
        given pid.  Note: this will miss orphaned children, perhaps
        there is a way to use session ids to track them... """
        
        pscmd = "ps -o pid,ppid "
        if sys.platform.lower().startswith("linux"):
            pscmd += "x"  # Linux is so "special"
        else:
            pscmd += "-x"

        p = Popen(shlex.split(pscmd), stdout=PIPE, stderr=STDOUT)
        psout = p.communicate()[0]
        ps_lines = psout.splitlines()[1:]
        ps_list = [map(int, l.split()) for l in ps_lines]
        progeny = [pid]
        xdone = False
        while not xdone:
            found = False
            for pid, ppid in ps_list[:]:
                if ppid in progeny:
                    progeny.append(pid)
                    ps_list.remove([pid, ppid])
                    found = True
            xdone = not found
        return progeny


    def _kill_progeny(self, proc):

        """ Send a term, then a kill signal to the process and any
        child processes that can be found. """

        # Try a sigterm
        pids = self._get_process_progeny(proc.pid)
        self.log("terminating pids: %s" % pids, 2)
        for pid in pids:
            try:
                os.kill(pid, SIGTERM)
            except OSError as ose:
                self.log("Ignoring error terminating pid %d: %s" %
                         (pid, ose), 2)
        time.sleep(5)

        # no more mr nice-guy
        self.log("killing pids: %s" % pids, 2)
        for pid in pids:
            try:
                os.kill(pid, SIGKILL)
            except OSError as ose:
                self.log("Ignoring error killing pid %d: %s" %
                         (pid, ose), 2)

        # These should now not block and possibly return something
        # informative
        output = proc.communicate()[0]
        status = proc.wait()
        return status, output        

    def comm(self, cmd, shell=False, timeout=0, ignore_dry_run=False):

        """ Run given command, honoring option.dry_run value (unless
        ignore_dry_run is True), returning status, output (combined
        stdout/err as a single string) and elapsed time.  If timeout
        is non-zero, then a sigalarm will be used to interrupt the
        command and the command and all child processes it has spawned
        will be sent sigterm & possibly sigkill signals. """

        if not ignore_dry_run and self.dry_run:
            self.log("dry-run: '%s' timeout=%d" % (cmd, timeout), 0)
            return (0, "ignored", 0.0)

        self.log("cmd: %s, timeout=%d" % (cmd, timeout), 2)

        if shell:
            cmd_arg = cmd
        else:
            cmd_arg = shlex.split(cmd)

        # timeout exception and handler
        class Alarm(Exception):
            pass

        def alarm_handler(signum, frame):
            raise Alarm

        if timeout > 0:
            signal(SIGALRM, alarm_handler)
            alarm(timeout)

        proc_tobe_killed = None
        t0 = time.time()
        try:
            proc = Popen(cmd_arg, shell=shell, stdout=PIPE, stderr=STDOUT)
            output = proc.communicate()[0]
            status = proc.wait()
            if timeout > 0:
                alarm(0) # clear alarm
        except OSError:
            self.log("Error running: %s" % cmd, 0)
            raise
        except Alarm:
            self.log("timeout exceeded on %s" % (cmd), 1)
            proc_tobe_killed = proc

        # Clean up, if timeout exceeded.
        if proc_tobe_killed is not None:
            status, output = self._kill_progeny(proc_tobe_killed)
        
        elapsed = time.time() - t0
        self.log("status: %d" % (status), 3)
        self.log("output: %s" % output, 3)
        return (status, output, elapsed)

    def sendmail(self,subject,msg,dest):

        me = "@".join([getpass.getuser(),"nersc.gov"])
        emsg = MIMEText(msg)
        emsg['Subject'] = subject
        emsg['From'] = me
        emsg['To'] = dest
        s=smtplib.SMTP('localhost')
        s.sendmail(me,dest,emsg.as_string())
        s.quit()





