# mPlane Protocol Reference Implementation
# tStat component code
#
# (c) 2013-2014 mPlane Consortium (http://www.ict-mplane.eu)
#               Author: Stefano Pentassuglia
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

import threading
from datetime import datetime
from time import sleep
import mplane.model
import mplane.scheduler
import mplane.utils
import mplane.tstat_caps
import mplane.azn
import mplane.tls
from urllib3 import HTTPSConnectionPool
from urllib3 import HTTPConnectionPool
import urllib3
import ssl
import argparse
import sys
import re
import json

DEFAULT_IP4_NET = "192.168.1.0/24"
DEFAULT_SUPERVISOR_IP4 = '127.0.0.1'
DEFAULT_SUPERVISOR_PORT = 8888
REGISTRATION_PATH = "register/capability"
SPECIFICATION_PATH = "show/specification"
RESULT_PATH = "register/result"


"""
Implements tStat proxy for integration into 
the mPlane reference implementation.
(capability push, specification pull)

"""

class tStatService(mplane.scheduler.Service):
    """
    This class handles the capabilities exposed by the proxy:
    executes them, and fills the results
    
    """
    
    def __init__(self, cap, fileconf):
        # verify the capability is acceptable
        mplane.tstat_caps.check_cap(cap)
        super(tStatService, self).__init__(cap)
        #self._logdir = logdir
        self._fileconf = fileconf

    def run(self, spec, check_interrupt):
        """
        Execute this Service
        
        """
        start_time = datetime.utcnow()

        # start measurement changing the tstat conf file
        self.change_conf(spec._label, True)

        # wait for specification execution
        wait_time = spec._when.timer_delays()
        wait_seconds = wait_time[1]
        if wait_seconds != None:
            sleep(wait_seconds)
        end_time = datetime.utcnow()

        # terminate measurement changing the tstat conf file
        self.change_conf(spec._label, False)
        
        # fill result message from tStat log
        print("specification " + spec._label + ": start = " + str(start_time) + ", end = " + str(end_time))
        res = self.fill_res(spec, start_time, end_time)
        return res
        
    def change_conf(self, cap_label, enable):
        """
        Changes the needed flags in the tStat runtime.conf file
        
        """
        newlines = []
        f = open(self._fileconf, 'r')
        for line in f:
            
            # read parameter names and values (discard comments or empty lines)
            if (line[0] != '[' and line[0] != '#' and
                line[0] != '\n' and line[0] != ' '):    
                param = line.split('#')[0]
                param_name = param.split(' = ')[0]
                
                # change flags according to the measurement requested
                if enable == True:
                    
                    # in order to activate optional sets, the basic set (log_tcp_complete) must be active too
                    if (cap_label == "tstat-log_tcp_complete-core" and param_name == 'log_tcp_complete'):
                        newlines.append(line.replace('0', '1'))
                        
                    elif (cap_label == "tstat-log_tcp_complete-end_to_end" and (
                        param_name == 'tcplog_end_to_end' 
                        or param_name == 'log_tcp_complete')):
                        newlines.append(line.replace('0', '1'))

                    elif (cap_label == "tstat-log_tcp_complete-tcp_options" and (
                        param_name == 'tcplog_options' or
                        param_name == 'log_tcp_complete')):
                        newlines.append(line.replace('0', '1'))

                    elif (cap_label == "tstat-log_tcp_complete-p2p_stats" and (
                        param_name == 'tcplog_p2p' or
                        param_name == 'log_tcp_complete')):
                        newlines.append(line.replace('0', '1'))

                    elif (cap_label == "tstat-log_tcp_complete-layer7" and (
                        param_name == 'tcplog_layer7' or
                        param_name == 'log_tcp_complete')):
                        newlines.append(line.replace('0', '1'))
                    else:
                        newlines.append(line)
                else:
                    if (cap_label == "tstat-log_tcp_complete-end_to_end" and param_name == 'tcplog_end_to_end'):
                        newlines.append(line.replace('1', '0'))

                    elif (cap_label == "tstat-log_tcp_complete-tcp_options" and param_name == 'tcplog_options'):
                        newlines.append(line.replace('1', '0'))

                    elif (cap_label == "tstat-log_tcp_complete-p2p_stats" and param_name == 'tcplog_p2p'):
                        newlines.append(line.replace('1', '0'))

                    elif (cap_label == "tstat-log_tcp_complete-layer7" and param_name == 'tcplog_layer7'):
                        newlines.append(line.replace('1', '0'))

                    else:
                        newlines.append(line) 
            else:
                newlines.append(line)
        f.close()
        
        f = open(self._fileconf, 'w')
        f.writelines(newlines)
        f.close
        
    def fill_res(self, spec, start, end):
        """
        Create a Result statement, fill it and return it
        
        """

        # derive a result from the specification
        res = mplane.model.Result(specification=spec)

        # put actual start and end time into result
        res.set_when(mplane.model.When(a = start, b = end))
        
        # fill result columns with DUMMY values
        for column_name in res.result_column_names():
            prim = res._resultcolumns[column_name].primitive_name()
            if prim == "natural":
                res.set_result_value(column_name, 0)
            elif prim == "string":
                res.set_result_value(column_name, "hello")
            elif prim == "real":
                res.set_result_value(column_name, 0.0)
            elif prim == "boolean":
                res.set_result_value(column_name, True)
            elif prim == "time":
                res.set_result_value(column_name, start)
            elif prim == "address":
                res.set_result_value(column_name, args.SUPERVISOR_IP4)
            elif prim == "url":
                res.set_result_value(column_name, "www.google.com")
        
        return res

def parse_args():
    """
    Parse arguments from command line
    
    """
    global args
    parser = argparse.ArgumentParser(description='run a Tstat mPlane proxy')
    parser.add_argument('-n', '--net-address', metavar='net-address', default=DEFAULT_IP4_NET, dest='IP4_NET',
                        help='Subnet IP4 and netmask observed by this probe (in the format x.x.x.x/n)')
    parser.add_argument('-d', '--supervisor-ip4', metavar='supervisor-ip4', default=DEFAULT_SUPERVISOR_IP4, dest='SUPERVISOR_IP4',
                        help='Supervisor IP address')
    parser.add_argument('-p', '--supervisor-port', metavar='supervisor-port', default=DEFAULT_SUPERVISOR_PORT, dest='SUPERVISOR_PORT',
                        help='Supervisor port number')
    parser.add_argument('-t', '--tlsfile', metavar="tls-conf-file", dest='TLSFILE', default = None,
                        help="Location of the configuration file for tls")
    parser.add_argument('-T', '--tstat-runtimeconf', metavar = 'path', dest = 'TSTAT_RUNTIMECONF', required = True,
                        help = 'Tstat runtime.conf configuration file path')
    args = parser.parse_args()

    # check format of subnet address
    net_pattern = re.compile("^\d{1,3}[.]\d{1,3}[.]\d{1,3}[.]\d{1,3}[/]\d{1,2}$")
    if not net_pattern.match(args.IP4_NET):
        print('\nERROR: Invalid network address format. The format must be: x.x.x.x/n\n')
        parser.print_help()
        sys.exit(1)
    else:
        
        # extract the subnet mask and check its format
        slash = args.IP4_NET.find("/")
        if slash > 0:
            netmask = int(args.IP4_NET[slash+1:])
            if (netmask < 8 or netmask > 24):
                print('\nERROR: Invalid netmask. It must be a number between 8 and 24\n')
                parser.print_help()
                sys.exit(1)

    # check format of Supervisor IP address
    ip4_pattern = re.compile("^\d{1,3}[.]\d{1,3}[.]\d{1,3}[.]\d{1,3}$")
    if not ip4_pattern.match(args.SUPERVISOR_IP4):
        print('\nERROR: invalid Supervisor IP format \n')
        parser.print_help()
        sys.exit(1)

    # check format of Supervisor port number
    args.SUPERVISOR_PORT = int(args.SUPERVISOR_PORT)
    if (args.SUPERVISOR_PORT <= 0 or args.SUPERVISOR_PORT > 65536):
        print('\nERROR: invalid port number \n')
        parser.print_help()
        sys.exit(1)
    
    # check if runtime.conf parameter has been inserted in the command line
    if not args.TSTAT_RUNTIMECONF:
        print('\nERROR: missing -T|--tstat-runtimeconf\n')
        parser.print_help()
        sys.exit(1)
    
class HttpProbe():
    """
    This class manages interactions with the supervisor:
    registration, specification retrievement, and return of results
    
    """
    
    def __init__(self, immediate_ms = 5000):
        parse_args()
        
        if args.TLSFILE is None:
            self._url = urllib3.util.parse_url("http://" + args.SUPERVISOR_IP4 + ":" + str(args.SUPERVISOR_PORT))
        else:
            self._url = urllib3.util.parse_url("https://" + args.SUPERVISOR_IP4 + ":" + str(args.SUPERVISOR_PORT))
        
        
        azn = mplane.azn.Authorization(args.TLSFILE)
        self.tls = mplane.tls.TlsState(args.TLSFILE)
        
        self.scheduler = mplane.scheduler.Scheduler(azn)
        self.pool = self.tls.pool_for(self._url)
        
        # generate a Service for each capability
        self.immediate_ms = immediate_ms
        self.scheduler.add_service(tStatService(mplane.tstat_caps.tcp_flows_capability(args.IP4_NET), args.TSTAT_RUNTIMECONF))
        self.scheduler.add_service(tStatService(mplane.tstat_caps.e2e_tcp_flows_capability(args.IP4_NET), args.TSTAT_RUNTIMECONF))
        self.scheduler.add_service(tStatService(mplane.tstat_caps.tcp_options_capability(args.IP4_NET), args.TSTAT_RUNTIMECONF))
        self.scheduler.add_service(tStatService(mplane.tstat_caps.tcp_p2p_stats_capability(args.IP4_NET), args.TSTAT_RUNTIMECONF))
        self.scheduler.add_service(tStatService(mplane.tstat_caps.tcp_layer7_capability(args.IP4_NET), args.TSTAT_RUNTIMECONF))
     
    def register_to_supervisor(self):
        """
        Sends a list of capabilities to the Supervisor, in order to register them
        
        """
        url = "/" + REGISTRATION_PATH
        
        # generate the capability list
        caps_list = ""
        no_caps_exposed = True
        sv_identity = self.tls.extract_peer_identity(self._url)
        for key in self.scheduler.capability_keys():
            cap = self.scheduler.capability_for_key(key)
            if self.scheduler._azn.check(cap, sv_identity):
                caps_list = caps_list + mplane.model.unparse_json(cap) + ","
                no_caps_exposed = False
        caps_list = "[" + caps_list[:-1].replace("\n","") + "]"
        connected = False
        
        if no_caps_exposed is True:
           print("\nNo Capabilities are being exposed to " + sv_identity + ", check permission files. Exiting")
           exit(0)
           
        # send the list to the supervisor, if reachable
        while not connected:
            try:
                res = self.pool.urlopen('POST', url, 
                    body=caps_list.encode("utf-8"), 
                    headers={"content-type": "application/x-mplane+json"})
                connected = True
                
            except:
                print("Supervisor unreachable. Retrying connection in 5 seconds")
                sleep(5)
                
        # handle response message
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
                            body=mplane.model.unparse_json(reply).encode("utf-8"), 
                            headers={"content-type": "application/x-mplane+json"})
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
                body=mplane.model.unparse_json(reply).encode("utf-8"), 
                headers={"content-type": "application/x-mplane+json"})
                
        # handle response
        if res.status == 200:
            print("Result for " + reply.get_label() + " successfully returned!")
        else:
            print("Error returning Result for " + reply.get_label())
            print("Supervisor said: " + str(res.status) + " - " + res.data.decode("utf-8"))
        pass

if __name__ == "__main__":
    mplane.model.initialize_registry()
    probe = HttpProbe()
    
    # register this probe to the Supervisor
    probe.register_to_supervisor()
    
    # periodically polls the Supervisor for Specifications
    print("Checking for Specifications...")
    while(True):
        probe.check_for_specs()
        sleep(5)