
# mPlane Protocol Reference Implementation
# Firelog probe component code
#
# (c) 2013-2014 mPlane Consortium (http://www.ict-mplane.eu)
#               Author: Marco Milanesio <marco.milanesio@eurecom.fr>
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""
Implements Firelog on the mPlane reference implementation.

"""

import re
import ipaddress
import threading
import subprocess
import collections
from datetime import datetime, timedelta
from ipaddress import ip_address
import mplane.model
import mplane.scheduler
import mplane.httpsrv
import tornado.web
import tornado.ioloop
import argparse
import psutil
import os
import time

plugin_filename = '/tmp/plugin_test.out'

def _firelog_process(url):
    cmd = '%s/firefox -P %s -url %s' % ('./firefox', 'firelog', url)
    return subprocess.Popen(cmd.split(" "), stdout=subprocess.PIPE)
    
def firelog_capability(ipaddr, url):
    cap = mplane.model.Capability(label="firelog", when = "now")
    cap.add_parameter("source.ip4",ipaddr)
    cap.add_parameter("source.ip6",ipaddr)
    cap.add_parameter("firelog.session.url")
    cap.add_result_column("cpuload")
    cap.add_result_column("memload")
    cap.add_result_column("firelog.plugin.file")
    cap.add_result_column("firelog.stat")
    cap.add_result_column("firelog.ping")
    cap.add_result_column("firelog.trace")
    return cap

class FirelogService(mplane.scheduler.Service):
    def __init__(self, cap):
        # verify the capability is acceptable
        if not ((cap.has_parameter("source.ip4") or 
                 cap.has_parameter("source.ip6")) and
                (cap.has_parameter("session.url"))): 
            raise ValueError("capability not acceptable")
        super(FirelogService, self).__init__(cap)
        self._mem = -1
        self._cpu = -1
        self._starttime = datetime.utcnow()
        #self._stats = None
        #self._ping = None
        #self._trace = None

    def run(self, spec, check_interrupt):
        if not spec.has_parameter("url"):
            raise ValueError("Missing url")
        
        count = None
        firelog_process = None

        def target():
            sipaddr = spec.get_parameter_value("source.ip4")
            url = spec.get_parameter_value("url")
            firelog_process = _firelog_process(url)
            cputable = []
            memtable = []
            while firelog_process.poll() == None:
                arr = psutil.cpu_percent(interval=0.1,percpu=True)
                cputable.append(sum(arr) / float(len(arr)))
                memtable.append(psutil.virtual_memory().percent)
                time.sleep(1)
                
            if firelog_process.poll() == 0:
                self._mem = float(sum(memtable) / len(memtable))
                self._cpu = float(sum(cputable) / len(cputable))

        t = threading.Thread(target=target)
        t.start()
        t.join()
        if t.is_alive():
            firelog_process.terminate()
            t.join()

        if os.path.isfile(plugin_filename):
            while not check_if_file_is_closed(plugin_filename):
                time.sleep(1)

        
        # TODO
        # add parsing/ping/db/logic
        
        # derive a result from the specification
        res = mplane.model.Result(specification=spec)

        # put actual start and end time into result
        now = datetime.utcnow()
        res.set_when(mplane.model.When(a = self._starttime, b = now))
        
        if os.path.isfile(plugin_filename):
            while not check_if_file_is_closed(plugin_filename):
                time.sleep(1)
            res.set_result_value("cpuload", self._cpu)
            res.set_result_value("memload", self._mem)
            res.set_result_value("firelog.plugin.file", plugin_filename)
        else:
            return None

        #res.set_result_value("firelog.stat", self._stats)
        #res.set_result_value("firelog.ping", self._ping)
        #res.set_result_value("firelog.trace", self._trace)

        return res

def check_if_file_is_closed(fname):
    cmd = 'fuser -a %s' % fname
    f = subprocess.Popen(cmd.split(' '), stdout=subprocess.PIPE)
    out, _ = f.communicate()
    if len(out) == 0:
        return True
    return False

def parse_args():
    global args
    parser = argparse.ArgumentParser(description="Run firelog probe server")
    parser.add_argument('--ip4addr', '-4', metavar="source-v4-address",
                        help="Browse and ping from the given IPv4 address")
    parser.add_argument('--ip6addr', '-6', metavar="source-v6-address",
                        help="Browse and ping from the given IPv6 address")
    parser.add_argument('--url', '-u', metavar="web page url",
                        help="Browse the given web page")
    args = parser.parse_args()

# For right now, start a Tornado-based ping server
if __name__ == "__main__":
    global args

    mplane.model.initialize_registry()
    parse_args()

    if args.url is None:
        raise ValueError("need a url")

    url = args.url
    ip4addr = None
    ip6addr = None
        
    if args.ip4addr:
        ip4addr = ip_address(args.ip4addr)
        if ip4addr.version != 4:
            raise ValueError("invalid IPv4 address")
    if args.ip6addr:
        ip6addr = ip_address(args.ip6addr)
        if ip6addr.version != 6:
            raise ValueError("invalid IPv6 address")
    if ip4addr is None and ip6addr is None:
        raise ValueError("need at least one source address to run")

    scheduler = mplane.scheduler.Scheduler()
    if ip4addr is not None:
        scheduler.add_service(FirelogService(firelog_capability(ip4addr, url)))
    if ip6addr is not None:
        scheduler.add_service(FirelogService(firelog_capability(ip6addr, url)))


    mplane.httpsrv.runloop(scheduler)
