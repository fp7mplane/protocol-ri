#
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
#
# mPlane Protocol Reference Implementation
# OTT probe component code for component-initiated workflow
# Implementation is based on the Ping probe written by <attila.bokor@netvisor.hu> (ping_ci.py)
#
# (c) 2013-2014 mPlane Consortium (http://www.ict-mplane.eu)
#               Author: Gabor Molnar <gabor.molnar@netvisor.hu>
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
Implements OTT probe for integration into 
the mPlane reference implementation.

"""

import argparse
import collections
from datetime import datetime, timedelta
from ipaddress import ip_address
import json
import os
import platform
import re
import subprocess
import threading
from time import sleep

import urllib3
from urllib3 import HTTPConnectionPool
from urllib3 import HTTPSConnectionPool

import mplane.httpsrv
import mplane.model
import mplane.scheduler

import socket
import sys

DEFAULT_SUPERVISOR_IP4  = 'localhost'
DEFAULT_SUPERVISOR_PORT = 8888

REGISTRATION_PATH  = "register/capability"
SPECIFICATION_PATH = "show/specification"
RESULT_PATH        = "register/result"

urllib3.disable_warnings()


class OttService(mplane.scheduler.Service):
    """
    This class parses the capabilities and executes the external
    probe-ott software with the parameters specified in the
    parameters

    this inherited class implements the OTT service based on the mplane scheduler
    - gets parameters from probe-ott via ott_process
    - sets the result YAML

    """

    def __init__(self, ipaddr):
        """
        verify the capability is acceptable
        and setting up the service

        """

        self.caplist = ["bandwidth.nominal.kbps", "http.code.max", "http.redirectcount.max", "qos.manifest", "qos.content", "qos.aggregate", "qos.level" ]
        cap = self.assembleCapabilities(ipaddr)
        if not ((cap.has_parameter("source.ip4")) and (cap.has_parameter("content.url")) and (self.contains_result(cap))):
            raise ValueError("capability not acceptable")
        super(OttService, self).__init__(cap)

    def run(self, spec, check_interrupt):
        """
        get the parameters and execute the service
        read the output JSON from probe-ott from STDOUT
        create the result and send it back
  
        """

        try:
          period = spec.when().period().total_seconds()
          duration = spec.when().duration().total_seconds()
          o_duration = duration
          if spec.has_parameter("content.url"):
              url = spec.get_parameter_value("content.url")
          else:
              raise ValueError("Missing URL")
      
          res = mplane.model.Result(specification=spec)
          index = -1
          s = datetime.utcnow()
          while (duration > 0):
            index += 1
            o_process = self.ott_process(period, url)
            duration -= period
            jsonS = ""
            for line in o_process.stdout:
              strLine = line.decode()
              if strLine is "}":
                 jsonS += strLine
                 break
              jsonS += strLine

            jsonO = json.loads(jsonS)

            #print(jsonS)
            errcode = [jsonO["manifestQos.Max"], jsonO["contentQos.Max"]]
            res.set_result_value("time", 				str(s + timedelta(seconds=(index*period) ) ), index)
            res.set_result_value("bandwidth.nominal.kbps",	jsonO["nominalBitrate.Max"], index)
            res.set_result_value("http.code.max", 		jsonO["httpCode.Max"], index)
            res.set_result_value("http.redirectcount.max", 	jsonO["redirect.Max"], index)
            res.set_result_value("qos.manifest", 			errcode[0], index)
            res.set_result_value("qos.content", 			errcode[1], index)
            res.set_result_value("qos.aggregate", 		min(errcode), index)
            res.set_result_value("qos.level", 			jsonO["qualityIndex.Max"], index)
          res.set_when(mplane.model.When(a=s, b=(  s + timedelta( seconds=((index+1)*period) ) )))
          return res
        except:
          print("Unexpected error in run:", sys.exc_info())
          raise


    def assembleCapabilities(self, ipaddr):
        """
        method for assembling the offered parameters
    
        """

        cap = mplane.model.Capability(label="ott-download", when = "now ... future / 1s")
        cap.add_parameter("source.ip4",ipaddr)
        cap.add_parameter("content.url")
        cap.add_result_column("time")
        for c in self.caplist:
            cap.add_result_column(c)
        return cap


    def contains_result(self, cap):
        """
        returns True if the offered parameter is listed in the capabilities

        """

        for c in self.caplist:
            if cap.has_result_column(c):
                return True
        return False

    def ott_process(self, period=None, url=None):
        """
        This method starts the measurement and
        opens a pipe to redirect the output
        to STDOUT
        
        """

        ott_argv = ["probe-ott"]
        ott_argv += [ "--slot", "-1"]
        if period is not None:
            ott_argv += ["--mplane", str(int(period))]
        if url is not None:
            ott_argv += ["--url", str(url)]

        print("running " + " ".join(ott_argv))

        return subprocess.Popen(ott_argv, stdout=subprocess.PIPE)

class OttProbe():
    """
    This class manages interactions with the supervisor:
    registration, specification retrievement, and return of results    

    """

    def __init__(self):
        """
        initiates a OTT probe for component-initiated workflow based on command-line arguments  

        """

        self.parse_args()
        headers={"content-type": "application/x-mplane+json"}
        if self.certfile is None:
            self.pool = HTTPConnectionPool(self.supervisorhost, self.supervisorport, headers=headers)
        else:
            self.pool = HTTPSConnectionPool(self.supervisorhost, self.supervisorport, key_file=self.key, cert_file=self.certfile, ca_certs=self.ca, headers=headers)

        self.dn = mplane.httpsrv.get_dn( self.certfile, self.certfile );
        self.scheduler = mplane.scheduler.Scheduler(self.certfile, self.certfile)

        if self.ip4addr is not None:
            self.scheduler.add_service(OttService(self.ip4addr))
    
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
                
                job = self.scheduler.job_for_message(reply)
                
                # launch a thread to monitor the status of the running measurement
                t = threading.Thread(target=self.return_results, args=[job])
                t.start()
                
        elif res.status == 428:
            print("\nRe-registering capabilities on Supervisor")
            self.register_to_supervisor()
        pass

    def return_results(self, job):
      """
      Monitors a job, and as soon as it is complete sends it to the Supervisor
        
      """

      try:
        url = "/" + RESULT_PATH
        reply = job.get_reply()
        
        while job.finished() is not True:
            if job.failed():
              try:
                reply = job.get_reply()
                break
              except:
                print("Unexpected error in return_results job.get_reply():", sys.exc_info())
                raise
            sleep(1)
        if isinstance (reply, mplane.model.Receipt):
            reply = job.get_reply()
        
        res = self.pool.urlopen('POST', url, body=mplane.model.unparse_json(reply).encode("utf-8") ) 

        if res.status == 200:
            print("Result for " + reply.get_label() + " successfully returned!")
        else:
            print("Error returning Result for " + reply.get_label())
            print("Supervisor said: " + str(res.status) + " - " + res.data.decode("utf-8"))
        pass
      except:
        print("Unexpected error in return_results:", sys.exc_info())
        raise
    
    def parse_args(self):
        global args
        parser = argparse.ArgumentParser(description="Run an mPlane OTT probe server")
        parser.add_argument('--disable-ssl', action='store_true', default=False, dest='DISABLE_SSL', 
								help='Disable secure communication')
        parser.add_argument('-n', '--ip4addr', 	
			metavar="source-v4-address", 		help="Ping from the given IPv4 address")
        parser.add_argument('-c', '--certfile',
	 		metavar="cert-file-location", 		help="Location of the configuration file for certificates")
        parser.add_argument('-d', '--supervisorhost',
		 	metavar="supervisorhost", 		help="IP or host name where supervisor runs (default: localhost)")
        parser.add_argument('-p', '--supervisorport',
			metavar="supervisorport", 		help="port on which supervisor listens (default: 8888)")
        args = parser.parse_args()
        
        self.supervisorhost = args.supervisorhost or DEFAULT_SUPERVISOR_IP4
        self.supervisorport = args.supervisorport or DEFAULT_SUPERVISOR_PORT
        
        self.ip4addr = None

        if args.ip4addr:
            self.ip4addr = ip_address(args.ip4addr)
            if self.ip4addr.version != 4:
                raise ValueError("invalid IPv4 address")
        if self.ip4addr is None :
             iplist = []
             [iplist.append(ip) for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1]
             print("Source address not defined. Lists of IPs found: " + ''.join(iplist) + " Using first: " + iplist[0])
             self.ip4addr = ip_address(iplist[0])
             if self.ip4addr.version != 4:
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


def manually_test_ott():
    svc = OttService("127.0.0.1")
    spec = mplane.model.Specification(capability=svc.capability())
    spec.set_parameter_value("source.ip4", "127.0.0.1")
    spec.set_parameter_value("content.url", "http://devimages.apple.com/iphone/samples/bipbop/bipbopall.m3u8")
    spec.set_when("now + 20s / 10s")

    res = svc.run(spec, lambda: False)
    print(repr(res))
    print(mplane.model.unparse_yaml(res))

if __name__ == "__main__":
    mplane.model.initialize_registry()
    ottprobe = OttProbe()
#    manually_test_ott() # uncomment this line for testing 
    ottprobe.register_capabilities()

    print("Checking for Specifications...")
    while True:
        ottprobe.check_for_specs()
        sleep(5)
