#
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
#
# mPlane Protocol Reference Implementation
# ICMP Ping probe component code for component-initiated workflow
#
# (c) 2013-2014 mPlane Consortium (http://www.ict-mplane.eu)
#               Author: Attila Bokor <attila.bokor@netvisor.hu>
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
Implements ICMP ping (delay.twoway.icmp) for integration into 
the mPlane reference implementation.

"""

import argparse
import collections
from datetime import datetime
from ipaddress import ip_address
import json
import os
import platform
import re
import subprocess
import threading
from time import sleep

from urllib3 import HTTPConnectionPool
from urllib3 import HTTPSConnectionPool

import mplane.httpsrv
import mplane.model
import mplane.scheduler


_pingline_re = re.compile("icmp_seq=(\d+)\s+\S+=(\d+)\s+time=([\d\.]+)\s+ms")
_pingline_unreachable_re = re.compile("icmp_seq=(\d+)\s+Destination Host Unreachable")

_ping4cmd = "ping"
_ping6cmd = "ping6"
_pingopts = ["-n"]
_pingopt_period = "-i"
_pingopt_count = "-c"
_pingopt_source = "-S"

LOOP4 = "127.0.0.1"
LOOP6 = "::1"
DEFAULT_SUPERVISOR_IP4 = 'localhost'
DEFAULT_SUPERVISOR_PORT = 8888
REGISTRATION_PATH = "register/capability"
SPECIFICATION_PATH = "show/specification"
RESULT_PATH = "register/result"

PingValue = collections.namedtuple("PingValue", ["time", "seq", "ttl", "usec"])

def _parse_ping_line(line):
    m = _pingline_re.search(line)    
    if m is not None:
        mg = m.groups()
        return PingValue(datetime.utcnow(), int(mg[0]), int(mg[1]), int(float(mg[2]) * 1000))

    unreachable = _pingline_unreachable_re.search(line)
    if unreachable is not None:
        urg = unreachable.groups()
        return PingValue(datetime.utcnow(), int(urg[0]), None, None)
    
    return None

def _ping_process(progname, sipaddr, dipaddr, period=None, count=None):
    ping_argv = [progname]
    if period is not None:
        ping_argv += [_pingopt_period, str(period)]
    if count is not None:
        ping_argv += [_pingopt_count, str(count)]
    ping_argv += [_pingopt_source, str(sipaddr)]
    ping_argv += [str(dipaddr)]

    print("running " + " ".join(ping_argv))

    return subprocess.Popen(ping_argv, stdout=subprocess.PIPE)

def _ping4_process(sipaddr, dipaddr, period=None, count=None):
    return _ping_process(_ping4cmd, sipaddr, dipaddr, period, count)

def _ping6_process(sipaddr, dipaddr, period=None, count=None):
    return _ping_process(_ping6cmd, sipaddr, dipaddr, period, count)

def pings_min_delay(pings):
    return min(map(lambda x: x.usec, pings))

def pings_mean_delay(pings):
    return int(sum(map(lambda x: x.usec, pings)) / len(pings))

def pings_median_delay(pings):
    return sorted(map(lambda x: x.usec, pings))[int(len(pings) / 2)]

def pings_max_delay(pings):
    return max(map(lambda x: x.usec, pings))

def pings_start_time(pings):
    return pings[0].time

def pings_end_time(pings):
    return pings[-1].time

def ping4_aggregate_capability(ipaddr):
    cap = mplane.model.Capability(label="ping-average-ip4", when = "now ... future / 1s")
    cap.add_parameter("source.ip4",ipaddr)
    cap.add_parameter("destination.ip4")
    cap.add_result_column("delay.twoway.icmp.us.min")
    cap.add_result_column("delay.twoway.icmp.us.mean")
    cap.add_result_column("delay.twoway.icmp.us.max")
    cap.add_result_column("delay.twoway.icmp.count")
    return cap

def ping4_singleton_capability(ipaddr):
    cap = mplane.model.Capability(label="ping-detail-ip4", when = "now ... future / 1s")
    cap.add_parameter("source.ip4",ipaddr)
    cap.add_parameter("destination.ip4")
    cap.add_result_column("time")
    cap.add_result_column("delay.twoway.icmp.us")
    return cap

def ping6_aggregate_capability(ipaddr):
    cap = mplane.model.Capability(label="ping-average-ip6", when = "now ... future / 1s")
    cap.add_parameter("source.ip6",ipaddr)
    cap.add_parameter("destination.ip6")
    cap.add_result_column("delay.twoway.icmp.us.min")
    cap.add_result_column("delay.twoway.icmp.us.mean")
    cap.add_result_column("delay.twoway.icmp.us.max")
    cap.add_result_column("delay.twoway.icmp.count")
    return cap

def ping6_singleton_capability(ipaddr):
    cap = mplane.model.Capability(label="ping-detail-ip6", when = "now ... future / 1s")
    cap.add_parameter("source.ip6",ipaddr)
    cap.add_parameter("destination.ip6")
    cap.add_result_column("time")
    cap.add_result_column("delay.twoway.icmp.us")
    return cap

class PingService(mplane.scheduler.Service):
    def __init__(self, cap):
        # verify the capability is acceptable
        if not ((cap.has_parameter("source.ip4") or 
                 cap.has_parameter("source.ip6")) and
                (cap.has_parameter("destination.ip4") or 
                 cap.has_parameter("destination.ip6")) and
                (cap.has_result_column("delay.twoway.icmp.us") or
                 cap.has_result_column("delay.twoway.icmp.us.min") or
                 cap.has_result_column("delay.twoway.icmp.us.mean") or                
                 cap.has_result_column("delay.twoway.icmp.us.max") or
                 cap.has_result_column("delay.twoway.icmp.count"))):
            raise ValueError("capability not acceptable")
        super(PingService, self).__init__(cap)

    def run(self, spec, check_interrupt):
        # unpack parameters
        period = spec.when().period().total_seconds()
        duration = spec.when().duration().total_seconds()
        if duration is not None and duration > 0:
            count = int(duration / period)
        else:
            count = None

        if spec.has_parameter("destination.ip4"):
            sipaddr = spec.get_parameter_value("source.ip4")
            dipaddr = spec.get_parameter_value("destination.ip4")
            ping_process = _ping4_process(sipaddr, dipaddr, period, count)
        elif spec.has_parameter("destination.ip6"):
            sipaddr = spec.get_parameter_value("source.ip6")
            dipaddr = spec.get_parameter_value("destination.ip6")
            ping_process = _ping6_process(sipaddr, dipaddr, period, count)
        else:
            raise ValueError("Missing destination")
      
        # read output from ping
        pings = []
        for line in ping_process.stdout:
            if check_interrupt():
                break
            s = line.decode()

            oneping = _parse_ping_line(s)
            if oneping is not None:
                print("ping "+repr(oneping))
                pings.append(oneping)
                
                
        # shut down and reap
        try:
            ping_process.kill()
        except OSError:
            pass
        ping_process.wait()

        # derive a result from the specification
        res = mplane.model.Result(specification=spec)

        # put actual start and end time into result
        res.set_when(mplane.model.When(a = pings_start_time(pings), b = pings_end_time(pings)))

        # are we returning aggregates or raw numbers?
        if res.has_result_column("delay.twoway.icmp.us"):
            # raw numbers
            for i, oneping in enumerate(pings):
                res.set_result_value("delay.twoway.icmp.us", oneping.usec, i)
            if res.has_result_column("time"):
                for i, oneping in enumerate(pings):
                    res.set_result_value("time", oneping.time, i)
        else:
            # aggregates. single row.
            if res.has_result_column("delay.twoway.icmp.us.min"):
                res.set_result_value("delay.twoway.icmp.us.min", pings_min_delay(pings))
            if res.has_result_column("delay.twoway.icmp.us.mean"):
                res.set_result_value("delay.twoway.icmp.us.mean", pings_mean_delay(pings))
            if res.has_result_column("delay.twoway.icmp.us.median"):
                res.set_result_value("delay.twoway.icmp.us.median", pings_median_delay(pings))
            if res.has_result_column("delay.twoway.icmp.us.max"):
                res.set_result_value("delay.twoway.icmp.us.max", pings_max_delay(pings))
            if res.has_result_column("delay.twoway.icmp.count"):
                res.set_result_value("delay.twoway.icmp.count", len(pings))


        return res

class PingProbe():
    """
    This class manages interactions with the supervisor:
    registration, specification retrievement, and return of results    
    """

    def __init__(self):
        """
        initiates a Ping probe for component-initiated workflow based on command-line arguments  
        """
        self.parse_args()
        headers={"content-type": "application/x-mplane+json"}
        if self.certfile is None:                        
            if( self.forget_mplane_identity is not None ):
                headers={"content-type": "application/x-mplane+json","Forget-MPlane-Identity": self.forget_mplane_identity}
            self.pool = HTTPConnectionPool(self.supervisorhost, self.supervisorport, headers=headers)
        else:
            self.pool = HTTPSConnectionPool(self.supervisorhost, self.supervisorport, key_file=self.key, cert_file=self.certfile, ca_certs=self.ca, headers=headers)

        self.dn = mplane.httpsrv.get_dn( self.certfile, self.certfile );
        self.scheduler = mplane.scheduler.Scheduler(self.certfile, self.certfile)

        if self.ip4addr is not None:
            self.scheduler.add_service(PingService(ping4_aggregate_capability(self.ip4addr)))
            self.scheduler.add_service(PingService(ping4_singleton_capability(self.ip4addr)))
        if self.ip6addr is not None:
            self.scheduler.add_service(PingService(ping6_aggregate_capability(self.ip6addr)))
            self.scheduler.add_service(PingService(ping6_singleton_capability(self.ip6addr)))

    def register_capabilities(self):
        print( "Registering capabilities to supervisor at " + self.supervisorhost + ":" + str(self.supervisorport) )
        
        caps_list = ""
        for key in self.scheduler.capability_keys():
            cap = self.scheduler.capability_for_key(key)
            if (self.scheduler.ac.check_azn(cap._label, self.dn)):
                caps_list = caps_list + mplane.model.unparse_json(cap) + ","
        caps_list = "[" + caps_list[:-1].replace("\n","") + "]"
        
        while True:
            try:
                res = self.pool.urlopen('POST', "/" + REGISTRATION_PATH, 
                    body=caps_list.encode("utf-8"))
                
                if res.status == 200:
                    body = json.loads(res.data.decode("utf-8"))
                    print("\nCapability registration outcome:")
                    for key in body:
                        if body[key]['registered'] == "ok":
                            print(key + ": Ok")
                        else:
                            print(key + ": Failed (" + body[key]['reason'] + ")")
                    print("")
                else:
                    print("Error registering capabilities, Supervisor said: " + str(res.status) + " - " + res.data.decode("utf-8"))
                    exit(1)
                break

            except:
                print("Supervisor unreachable. Retrying connection in 5 seconds")
                sleep(5)
    
    def check_for_specs(self):
        """
        Poll the supervisor for specifications
        
        """
        url = "/" + SPECIFICATION_PATH
        
        # send a request for specifications
        res = self.pool.request('GET', url)
        if res.status == 200:
            
            # specs retrieved: split them if there is more than one
            specs = mplane.utils.split_stmt_list(res.data.decode("utf-8"))
            for spec in specs:
                
                # hand spec to scheduler
                reply = self.scheduler.receive_message(self.dn, spec)
                
                # return error if spec is not authorized
                if isinstance(reply, mplane.model.Exception):
                    result_url = "/" + RESULT_PATH
                    # send result to the Supervisor
                    res = self.pool.urlopen('POST', result_url, 
                            body=mplane.model.unparse_json(reply).encode("utf-8"))
                    return
                
                # enqueue job
                job = self.scheduler.job_for_message(reply)
                
                # launch a thread to monitor the status of the running measurement
                t = threading.Thread(target=self.return_results, args=[job])
                t.start()
                
        # not registered on supervisor, need to re-register
        elif res.status == 428:
            print("\nRe-registering capabilities on Supervisor")
            self.register_to_supervisor()
        pass

    def return_results(self, job):
        """
        Monitors a job, and as soon as it is complete sends it to the Supervisor
        
        """
        url = "/" + RESULT_PATH
        reply = job.get_reply()
        
        # check if job is completed
        while job.finished() is not True:
            if job.failed():
                reply = job.get_reply()
                break
            sleep(1)
        if isinstance (reply, mplane.model.Receipt):
            reply = job.get_reply()
        
        # send result to the Supervisor
        res = self.pool.urlopen('POST', url, 
                body=mplane.model.unparse_json(reply).encode("utf-8") )

        # handle response
        if res.status == 200:
            print("Result for " + reply.get_label() + " successfully returned!")
        else:
            print("Error returning Result for " + reply.get_label())
            print("Supervisor said: " + str(res.status) + " - " + res.data.decode("utf-8"))
        pass
    
    def parse_args(self):
        global args
        parser = argparse.ArgumentParser(description="Run an mPlane ping probe server")
        parser.add_argument('--ip4addr', '-4', metavar="source-v4-address",
                            help="Ping from the given IPv4 address")
        parser.add_argument('--ip6addr', '-6', metavar="source-v6-address",
                            help="Ping from the given IPv6 address")
        parser.add_argument('--disable-ssl', action='store_true', default=False, dest='DISABLE_SSL',
                            help='Disable secure communication')
        parser.add_argument('--certfile', metavar="cert-file-location",
                            help="Location of the configuration file for certificates")
        parser.add_argument('--supervisorhost', metavar="supervisorhost",
                            help="IP or host name where supervisor runs (default: localhost)")
        parser.add_argument('--supervisorport', metavar="supervisorport",
                            help="port on which supervisor listens (default: 8888)")
        parser.add_argument('--forget-mplane-identity', metavar="forget_mplane_identity",
                            help="ID to use in non-secure mode instead of certificate's subject")
        args = parser.parse_args()
        
        self.forget_mplane_identity = args.forget_mplane_identity
        self.supervisorhost = args.supervisorhost or DEFAULT_SUPERVISOR_IP4
        self.supervisorport = args.supervisorport or DEFAULT_SUPERVISOR_PORT
        
        self.ip4addr = None
        self.ip6addr = None        

        if args.ip4addr:
            self.ip4addr = ip_address(args.ip4addr)
            if self.ip4addr.version != 4:
                raise ValueError("invalid IPv4 address")
        if args.ip6addr:
            self.ip6addr = ip_address(args.ip6addr)
            if self.ip6addr.version != 6:
                raise ValueError("invalid IPv6 address")
        if self.ip4addr is None and self.ip6addr is None:
            raise ValueError("need at least one source address to run")
    
        if not args.DISABLE_SSL:
            if args.certfile is None:
                raise ValueError("without --disable-ssl, need to specify cert file")
            else:
                print( "pwd: " + os.getcwd() + " - cert config file: " + args.certfile )
                mplane.utils.check_file(args.certfile)
                self.certfile = mplane.utils.normalize_path(mplane.utils.read_setting(args.certfile, "cert"))
                self.key = mplane.utils.normalize_path(mplane.utils.read_setting(args.certfile, "key"))
                self.ca = mplane.utils.normalize_path(mplane.utils.read_setting(args.certfile, "ca-chain"))
                mplane.utils.check_file(self.certfile)
                mplane.utils.check_file(self.key)
                mplane.utils.check_file(self.ca)
        else:
            self.certfile = None
            self.key = None
            self.ca = None


def manually_test_ping():
    svc = PingService(ping4_aggregate_capability(LOOP4))
    spec = mplane.model.Specification(capability=svc.capability())
    spec.set_parameter_value("destination.ip4", LOOP4)
    spec.set_when("now + 5s / 1s")

    res = svc.run(spec, lambda: False)
    print(repr(res))
    print(mplane.model.unparse_yaml(res))

    svc = PingService(ping4_singleton_capability(LOOP4))
    spec = mplane.model.Specification(capability=svc.capability())
    spec.set_parameter_value("destination.ip4", LOOP4)
    spec.set_when("now + 5s / 1s")

    res = svc.run(spec, lambda: False)
    print(repr(res))
    print(mplane.model.unparse_yaml(res))

    svc = PingService(ping6_aggregate_capability(LOOP6))
    spec = mplane.model.Specification(capability=svc.capability())
    spec.set_parameter_value("destination.ip6", LOOP6)
    spec.set_when("now + 5s / 1s")

    res = svc.run(spec, lambda: False)
    print(repr(res))
    print(mplane.model.unparse_yaml(res))

    svc = PingService(ping6_singleton_capability(LOOP6))
    spec = mplane.model.Specification(capability=svc.capability())
    spec.set_parameter_value("destination.ip6", LOOP6)
    spec.set_when("now + 5s / 1s")

    res = svc.run(spec, lambda: False)
    print(repr(res))
    print(mplane.model.unparse_yaml(res))

# For right now, start a Tornado-based ping server
if __name__ == "__main__":
    if platform.system() != "Linux":
        print("Linux is supported only. Output lines of ping command won't probably be parsed correctly.")
#        exit(2)
    
    mplane.model.initialize_registry()
    
    pingprobe = PingProbe();   
    pingprobe.register_capabilities()
    
    print("Checking for Specifications...")
    while True:
        pingprobe.check_for_specs()
        sleep(5)
