
# mPlane Protocol Reference Implementation
# Tracebox probe component code
#
# (c) 2013-2014 mPlane Consortium (http://www.ict-mplane.eu)
#               Author: Korian Edeline <korian.edeline@ulg.ac.be>
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
Implements Tracebox for integration into 
the mPlane reference implementation.

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

_traceboxcmd = ["scamper", "-c", "tracebox"]
_traceboxopt_v6 = "-6"
_traceboxopt_dip = "-i"
_traceboxopt_udp = "-u"
_traceboxopt_dport = "-d"
_traceboxopt_probe = "-p"
_traceboxopt_ipl = "-t" # icmp payload length

LOOP4 = "127.0.0.1"
LOOP6 = "::1"

TraceboxValue = collections.namedtuple("TraceboxValue", ["addr", "modifs", "payload_len"])

def _detail_ipl(ipl):
    ipls = {"(full)": "Full packet", "(8B)" : "Layer 3 Header + First 8 L3 payload bytes", "(L3)" : "Layer 3 header", "(0)" : "Empty"}
    return ipls[ipl] if ipl in ipls else ipl

def _parse_tracebox(tb_output, quote_size):
    """
    returns list of tuple (intermediate.addr, intermediate.modifs)
    """
    tuples=[]
    if (len(tb_output)<3):
        return []

    min_words = 3 if quote_size else 2

    for line in tb_output[2:]:
        pline=line.split()
        if len(pline)<=min_words:
            tuples.append(TraceboxValue(pline[1], "", _detail_ipl(pline[2]) if quote_size else ""))
        else:
            tuples.append(TraceboxValue(pline[1]," ".join(pline[min_words:]), _detail_ipl(pline[2]) if quote_size else ""))
    return tuples



def _tracebox_process(sipaddr, dipaddr, v, udp=None, dport=None, probe=None, get_icmp_payload_len=None):
    tracebox_argv = list(_traceboxcmd)
    if v is 6:
        tracebox_argv[-1] += " "+_traceboxopt_v6
    if udp is not None:
        tracebox_argv[-1] += " "+_traceboxopt_udp
    if get_icmp_payload_len is not None:
        tracebox_argv[-1] += " "+_traceboxopt_ipl
    if dport is not None:
        tracebox_argv[-1] += " "+_traceboxopt_dport+" "+str(dport)
    if probe is not None:
        tracebox_argv[-1] += " "+_traceboxopt_probe+" "+str(probe)

    tracebox_argv += [_traceboxopt_dip, str(dipaddr)]

    print("running " + " ".join(tracebox_argv))
    return subprocess.Popen(tracebox_argv, stdout=subprocess.PIPE)

def _tracebox4_process(sipaddr, dipaddr, v=4, udp=None, dport=None, probe=None, get_icmp_payload_len=None):
    return _tracebox_process(sipaddr, dipaddr, v, udp, dport, probe, get_icmp_payload_len)

def _tracebox6_process(sipaddr, dipaddr, v=6, udp=None, dport=None, probe=None, get_icmp_payload_len=None):
    return _tracebox_process(sipaddr, dipaddr, v, udp, dport, probe, get_icmp_payload_len)

def tracebox4_standard_capability(ipaddr):
    cap = mplane.model.Capability(label="tracebox-standard-ip4", when = "now ... future")
    cap.add_parameter("source.ip4",ipaddr)
    cap.add_parameter("destination.ip4")
    cap.add_result_column("tracebox.hop.ip4")
    cap.add_result_column("tracebox.hop.modifications")
    return cap

def tracebox4_specific_capability(ipaddr):
    #!!! do not set udp=1 with probe=IP/TCP/ 
    cap = mplane.model.Capability(label="tracebox-specific-ip4", when = "now ... future")
    cap.add_parameter("source.ip4",ipaddr)
    cap.add_parameter("destination.ip4")
    cap.add_parameter("tracebox.udp")
    cap.add_parameter("tracebox.dport")
    cap.add_parameter("tracebox.probe")
    cap.add_result_column("tracebox.hop.ip4")
    cap.add_result_column("tracebox.hop.modifications")
    return cap

def tracebox4_specific_quotesize_capability(ipaddr):
    #!!! do not set udp=1 with probe=IP/TCP/ 
    cap = mplane.model.Capability(label="tracebox-specific-quotesize-ip4", when = "now ... future")
    cap.add_parameter("source.ip4",ipaddr)
    cap.add_parameter("destination.ip4")
    cap.add_parameter("tracebox.udp")
    cap.add_parameter("tracebox.dport")
    cap.add_parameter("tracebox.probe")
    cap.add_result_column("tracebox.hop.ip4")
    cap.add_result_column("tracebox.hop.modifications")
    cap.add_result_column("tracebox.hop.icmp.payload.len")
    return cap


def tracebox6_standard_capability(ipaddr):
    cap = mplane.model.Capability(label="tracebox-standard-ip6", when = "now ... future")
    cap.add_parameter("source.ip6",ipaddr)
    cap.add_parameter("destination.ip6")
    cap.add_result_column("tracebox.hop.ip6")
    cap.add_result_column("tracebox.hop.modifications")
    return cap

def tracebox6_specific_capability(ipaddr):
    #!!! do not set udp=1 with probe=IP/TCP/ (opposite is ok)
    cap = mplane.model.Capability(label="tracebox-specific-ip6", when = "now ... future")
    cap.add_parameter("source.ip6",ipaddr)
    cap.add_parameter("destination.ip6")
    cap.add_parameter("tracebox.udp")
    cap.add_parameter("tracebox.dport")
    cap.add_parameter("tracebox.probe")
    cap.add_result_column("tracebox.hop.ip6")
    cap.add_result_column("tracebox.hop.modifications")
    return cap

def tracebox6_specific_quotesize_capability(ipaddr):
    #!!! do not set udp=1 with probe=IP/TCP/ (opposite is ok)
    cap = mplane.model.Capability(label="tracebox-specific-quotesize-ip6", when = "now ... future")
    cap.add_parameter("source.ip6",ipaddr)
    cap.add_parameter("destination.ip6")
    cap.add_parameter("tracebox.udp")
    cap.add_parameter("tracebox.dport")
    cap.add_parameter("tracebox.probe")
    cap.add_result_column("tracebox.hop.ip6")
    cap.add_result_column("tracebox.hop.modifications")
    cap.add_result_column("tracebox.hop.icmp.payload.len")
    return cap


class TraceboxService(mplane.scheduler.Service):
    
    #default parameter values
    _default_udp=0
    _default_dport=80
    def _default_probe(self,udp):
        return "IP/"+("UDP" if udp else "TCP")

    #label keywords
    _quote_size="quotesize"

    def __init__(self, cap):
        # verify the capability is acceptable
        if not ((cap.has_parameter("source.ip4") or 
                 cap.has_parameter("source.ip6")) and
                (cap.has_parameter("destination.ip4") or 
                 cap.has_parameter("destination.ip6"))):
            raise ValueError("capability not acceptable")
        # retreive icmp payload len or not
        
        super(TraceboxService, self).__init__(cap)
        self._get_ipl = 1 if self._quote_size in self.capability().get_label() else None

    def run(self, spec, check_interrupt):

        # retreive parameters. if no value, sets tracebox default value        
        if spec.has_parameter("tracebox.udp"):
            udp=spec.get_parameter_value("tracebox.udp")
            if udp is None:
                spec.set_parameter_value("tracebox.udp",self._default_udp)

            dport=spec.get_parameter_value("tracebox.dport")
            if dport is None:
                spec.set_parameter_value("tracebox.dport",self._default_dport)

            probe=spec.get_parameter_value("tracebox.probe")
            if probe is None:
                spec.set_parameter_value("tracebox.probe",self._default_probe(udp))

        else:
            udp=None
            dport=None
            probe=None             
        
        #save probe start time    
        start_time=datetime.utcnow()

        #launch probe
        if spec.has_parameter("destination.ip4"):
            sipaddr = spec.get_parameter_value("source.ip4")
            dipaddr = spec.get_parameter_value("destination.ip4")
            tracebox_process = _tracebox4_process(sipaddr, dipaddr, udp=udp, dport=dport, probe=probe, get_icmp_payload_len=self._get_ipl)
        elif spec.has_parameter("destination.ip6"):
            sipaddr = spec.get_parameter_value("source.ip6")
            dipaddr = spec.get_parameter_value("destination.ip6")
            tracebox_process = _tracebox6_process(sipaddr, dipaddr, udp=udp, dport=dport, probe=probe, get_icmp_payload_len=self._get_ipl)
        else:
            raise ValueError("Missing destination")

        #wait for probe to finish ?
        #tracebox_process.wait()

        #save probe end time 
        end_time=datetime.utcnow()

        # read and parse output from tracebox
        tb_output = []
        for line in tracebox_process.stdout:
            tb_output.append(line.decode("utf-8"))     
 
        tb_parsed_output = _parse_tracebox(tb_output, self._get_ipl)

        # shut down and reap
        try:
            tracebox_process.kill()
        except OSError:
            pass
        tracebox_process.wait()
        
        # derive a result from the specification
        res = mplane.model.Result(specification=spec)

        # put actual start and end time into result
        res.set_when(mplane.model.When(a = start_time, b = end_time))

        # add results
        print(tb_parsed_output)
        
        for i, onehop in enumerate(tb_parsed_output):
            if res.has_parameter("destination.ip4"):
                res.set_result_value("tracebox.hop.ip4", onehop.addr,i)
            else:
                res.set_result_value("tracebox.hop.ip6", onehop.addr,i)
            res.set_result_value("tracebox.hop.modifications", onehop.modifs,i)
            if self._get_ipl:
                res.set_result_value("tracebox.hop.icmp.payload.len", onehop.payload_len, i)

        return res

def manually_test_tracebox():
    
    #standard tcp probe
    svc = TraceboxService(tracebox4_standard_capability(LOOP4))
    spec = mplane.model.Specification(capability=svc.capability())
    spec.set_parameter_value("source.ip4", LOOP4)
    spec.set_parameter_value("destination.ip4", "23.212.108.142")
    spec.set_when("now ... future")

    res = svc.run(spec, lambda: False)
    print(repr(res))
    print(mplane.model.unparse_yaml(res))

    #standard udp probe
    svc = TraceboxService(tracebox4_specific_capability(LOOP4))
    spec = mplane.model.Specification(capability=svc.capability())
    spec.set_parameter_value("source.ip4", LOOP4)
    spec.set_parameter_value("destination.ip4", "23.212.108.142")
    spec.set_parameter_value("tracebox.udp",1)
    spec.set_when("now ... future")

    res = svc.run(spec, lambda: False)
    print(repr(res))
    print(mplane.model.unparse_yaml(res))

    #changing dport
    svc = TraceboxService(tracebox4_specific_capability(LOOP4))
    spec = mplane.model.Specification(capability=svc.capability())
    spec.set_parameter_value("source.ip4", LOOP4)
    spec.set_parameter_value("destination.ip4", "23.212.108.142")
    spec.set_parameter_value("tracebox.dport",53)
    spec.set_when("now ... future")

    res = svc.run(spec, lambda: False)
    print(repr(res))
    print(mplane.model.unparse_yaml(res))

    #defining multiple tcp options
    svc = TraceboxService(tracebox4_specific_capability(LOOP4))
    spec = mplane.model.Specification(capability=svc.capability())
    spec.set_parameter_value("source.ip4", LOOP4)
    spec.set_parameter_value("destination.ip4", "23.212.108.142")
    spec.set_parameter_value("tracebox.probe","IP/TCP/MSS/SACK/MPJOIN")
    spec.set_when("now ... future")

    res = svc.run(spec, lambda: False)
    print(repr(res))
    print(mplane.model.unparse_yaml(res))

    
    #testing icmp payload len retreival
    svc = TraceboxService(tracebox4_specific_quotesize_capability(LOOP4))
    spec = mplane.model.Specification(capability=svc.capability())
    spec.set_parameter_value("source.ip4", LOOP4)
    spec.set_parameter_value("destination.ip4", "23.212.108.142")
    spec.set_parameter_value("tracebox.probe","IP/TCP/MSS/SACK/MPJOIN")
    spec.set_when("now ... future")

    res = svc.run(spec, lambda: False)
    print(repr(res))
    print(mplane.model.unparse_yaml(res))

    #same for IPv6
    svc = TraceboxService(tracebox6_standard_capability(LOOP6))
    spec = mplane.model.Specification(capability=svc.capability())
    spec.set_parameter_value("source.ip6", LOOP6)
    spec.set_parameter_value("destination.ip6", "2a00:1450:400c:c06::8a")
    spec.set_when("now ... future")

    res = svc.run(spec, lambda: False)
    print(repr(res))
    print(mplane.model.unparse_yaml(res))

    svc = TraceboxService(tracebox6_specific_capability(LOOP6))
    spec = mplane.model.Specification(capability=svc.capability())
    spec.set_parameter_value("source.ip6", LOOP6)
    spec.set_parameter_value("destination.ip6", "2a00:1450:400c:c06::8a")
    spec.set_parameter_value("tracebox.udp",1)
    spec.set_when("now ... future")

    res = svc.run(spec, lambda: False)
    print(repr(res))
    print(mplane.model.unparse_yaml(res))

    svc = TraceboxService(tracebox6_specific_capability(LOOP6))
    spec = mplane.model.Specification(capability=svc.capability())
    spec.set_parameter_value("source.ip6", LOOP6)
    spec.set_parameter_value("destination.ip6", "2a00:1450:400c:c06::8a")
    spec.set_parameter_value("tracebox.dport",53)
    spec.set_when("now ... future")

    res = svc.run(spec, lambda: False)
    print(repr(res))
    print(mplane.model.unparse_yaml(res))

    svc = TraceboxService(tracebox6_specific_capability(LOOP6))
    spec = mplane.model.Specification(capability=svc.capability())
    spec.set_parameter_value("source.ip6", LOOP6)
    spec.set_parameter_value("destination.ip6", "2a00:1450:400c:c06::8a")
    spec.set_parameter_value("tracebox.probe","IP/TCP/MSS/SACK/MPJOIN")
    spec.set_when("now ... future")

    res = svc.run(spec, lambda: False)
    print(repr(res))
    print(mplane.model.unparse_yaml(res))

    
    #testing icmp payload len retreival
    svc = TraceboxService(tracebox4_specific_quotesize_capability(LOOP4))
    spec = mplane.model.Specification(capability=svc.capability())
    spec.set_parameter_value("source.ip4", LOOP4)
    spec.set_parameter_value("destination.ip4", "23.212.108.142")
    spec.set_parameter_value("tracebox.probe","IP/TCP/MSS/SACK/MPJOIN")
    spec.set_when("now ... future")

    res = svc.run(spec, lambda: False)
    print(repr(res))
    print(mplane.model.unparse_yaml(res))


def parse_args():
    global args
    parser = argparse.ArgumentParser(description="Run an mPlane Tracebox probe server")
    parser.add_argument('--ip4addr', '-4', metavar="source-v4-address",
                        help="Launch Tracebox from the given IPv4 address")
    parser.add_argument('--ip6addr', '-6', metavar="source-v6-address",
                        help="Launch Tracebox from the given IPv6 address")
    args = parser.parse_args()

# For right now, start a Tornado-based tracebox server
if __name__ == "__main__":
    global args

    mplane.model.initialize_registry()
    parse_args()

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
    
    manually_test_tracebox()
    """
    scheduler = mplane.scheduler.Scheduler()
    if ip4addr is not None:
        scheduler.add_service(TraceboxService(tracebox4_standard_capability(ip4addr)))
        scheduler.add_service(TraceboxService(tracebox4_specific_capability(ip4addr)))
        scheduler.add_service(TraceboxService(tracebox4_specific_quotesize_capability(ip4addr)))
    if ip6addr is not None:
        scheduler.add_service(TraceboxService(tracebox6_standard_capability(ip6addr)))
        scheduler.add_service(TraceboxService(tracebox6_specific_capability(ip6addr)))
        scheduler.add_service(TraceboxService(tracebox6_specific_quotesize_capability(ip6addr)))    
    mplane.httpsrv.runloop(scheduler)
    """
