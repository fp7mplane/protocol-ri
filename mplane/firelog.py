
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


def services(url):
    services = []
    if url is not None:
        services.append(FirelogService(firelog_capability(url)))
    return services
    
def _firelog_process(url):
    cmd = ''
    return subprocess.Popen(cmd.split(" "), stdout=subprocess.PIPE)
    
def firelog_capability(url):
    cap = mplane.model.Capability(label="firelog-diagnosis", when = "now + inf ... future")
    cap.add_parameter("destination.url")
    cap.add_result_column("firelog.diagnosis")
    return cap

class FirelogService(mplane.scheduler.Service):
    
    def __init__(self, cap):
        # verify the capability is acceptable
        #if not (cap.has_parameter("source.ip4") and
        if not cap.has_parameter("destination.url"):
            raise ValueError("capability not acceptable")
        super(FirelogService, self).__init__(cap)
        self._starttime = datetime.utcnow()
        
    def run(self, spec, check_interrupt):
        if not spec.has_parameter("destination.url"):
            raise ValueError("Missing url")
        
        firelog_process = None

        def target():
            #self._sipaddr = spec.get_parameter_value("source.ip4")
            url = spec.get_parameter_value("destination.url")
            firelog_process = _firelog_process(url)
            
        t = threading.Thread(target=target)
        t.start()
        out, err = t.join()
        if t.is_alive():
            firelog_process.terminate()
            out, err = t.join()
        
        # derive a result from the specification
        res = mplane.model.Result(specification=spec)

        # put actual start and end time into result
        now = datetime.utcnow()
        res.set_when(mplane.model.When(a = self._starttime, b = now))
        
        res.set_result_value("firelog.diagnosis", out)

        return res


def parse_args():
    global args
    parser = argparse.ArgumentParser(description="Run firelog probe server")
    parser.add_argument('--url', '-u', metavar="firelog session web page url",
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

    scheduler = mplane.scheduler.Scheduler()
    if url is not None:
        scheduler.add_service(FirelogService(firelog_capability(url)))
   
    mplane.httpsrv.runloop(scheduler)
