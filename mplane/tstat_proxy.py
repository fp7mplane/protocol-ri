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
from urllib3 import HTTPSConnectionPool
from urllib3 import HTTPConnectionPool
from socket import socket
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
    parser.add_argument('--disable-ssl', action='store_true', default=False, dest='DISABLE_SSL',
                        help='Disable secure communication')
    parser.add_argument('-c', '--certfile', metavar="path", dest='CERTFILE', default = None,
                        help="Location of the configuration file for certificates")
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

    # check if the file containing the paths for the 
    # certificates has been inserted in the command line
    # (only if security is enabled)
    if args.DISABLE_SSL == False and not args.CERTFILE:
        print('\nERROR: missing -C|--certfile\n')
        parser.print_help()
        sys.exit(1)
        

    
class HttpProbe():
    """
    This class manages interactions with the supervisor:
    registration, specification retrievement, and return of results
    
    """
    
    def __init__(self, immediate_ms = 5000):
        parse_args()
        self.dn = None
        
        # check if security is enabled, if so read certificate files
        self.security = not args.DISABLE_SSL
        if self.security:
            mplane.utils.check_file(args.CERTFILE)
            self.cert = mplane.utils.normalize_path(mplane.utils.read_setting(args.CERTFILE, "cert"))
            self.key = mplane.utils.normalize_path(mplane.utils.read_setting(args.CERTFILE, "key"))
            self.ca = mplane.utils.normalize_path(mplane.utils.read_setting(args.CERTFILE, "ca-chain"))
            mplane.utils.check_file(self.cert)
            mplane.utils.check_file(self.key)
            mplane.utils.check_file(self.ca)
            self.pool = HTTPSConnectionPool(args.SUPERVISOR_IP4, args.SUPERVISOR_PORT, key_file=self.key, cert_file=self.cert, ca_certs=self.ca)
        else: 
            self.pool = HTTPConnectionPool(args.SUPERVISOR_IP4, args.SUPERVISOR_PORT)
        
        # get server DN, for Access Control purposes
        self.dn = self.get_dn()
        
        # generate a Service for each capability
        self.immediate_ms = immediate_ms
        self.scheduler = mplane.scheduler.Scheduler(self.security, self.cert)
        self.scheduler.add_service(tStatService(mplane.tstat_caps.tcp_flows_capability(args.IP4_NET), args.TSTAT_RUNTIMECONF))
        self.scheduler.add_service(tStatService(mplane.tstat_caps.e2e_tcp_flows_capability(args.IP4_NET), args.TSTAT_RUNTIMECONF))
        self.scheduler.add_service(tStatService(mplane.tstat_caps.tcp_options_capability(args.IP4_NET), args.TSTAT_RUNTIMECONF))
        self.scheduler.add_service(tStatService(mplane.tstat_caps.tcp_p2p_stats_capability(args.IP4_NET), args.TSTAT_RUNTIMECONF))
        self.scheduler.add_service(tStatService(mplane.tstat_caps.tcp_layer7_capability(args.IP4_NET), args.TSTAT_RUNTIMECONF))
        
    def get_dn(self):
        """
        Extracts the DN from the server. 
        If SSL is disabled, returns a dummy DN
        
        """
        if self.security == True:
            
            # extract DN from server certificate.
            # Unfortunately, there seems to be no way to do this using urllib3,
            # thus ssl library is being used
            s = socket()
            c = ssl.wrap_socket(s,cert_reqs=ssl.CERT_REQUIRED, keyfile=self.key, certfile=self.cert, ca_certs=self.ca)
            c.connect((args.SUPERVISOR_IP4, args.SUPERVISOR_PORT))
            cert = c.getpeercert()
            
            dn = ""
            for elem in cert.get('subject'):
                if dn == "":
                    dn = dn + str(elem[0][1])
                else: 
                    dn = dn + "." + str(elem[0][1])
        else:
            dn = "org.mplane.Test PKI.Test Clients.mPlane-Client"
        return dn
     
    def register_to_supervisor(self):
        """
        Sends a list of capabilities to the Supervisor, in order to register them
        
        """
        url = "/" + REGISTRATION_PATH
        
        # generate the capability list
        caps_list = ""
        for key in self.scheduler.capability_keys():
            cap = self.scheduler.capability_for_key(key)
            if (self.scheduler.ac.check_azn(cap._label, self.dn)):
                caps_list = caps_list + mplane.model.unparse_json(cap) + ","
        caps_list = "[" + caps_list[:-1].replace("\n","") + "]"
        connected = False
        
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