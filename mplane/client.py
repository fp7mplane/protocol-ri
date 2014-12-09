# mPlane Protocol Reference Implementation
# Simple mPlane client and CLI (JSON over HTTP)
#
# (c) 2013-2014 mPlane Consortium (http://www.ict-mplane.eu)
#               Author: Brian Trammell <brian@trammell.ch>
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

import mplane.model
import mplane.utils
import sys
import cmd
import readline
import urllib3
from collections import OrderedDict
from urllib3 import HTTPSConnectionPool
from urllib3 import HTTPConnectionPool
import os.path
import argparse
import json

from datetime import datetime, timedelta

DEFAULT_SV_PORT = 8888
DEFAULT_SV_IP4 = '127.0.0.1'
S_CAPABILITY_PATH = "show/capability"
S_SPECIFICATION_PATH = "register/specification"
S_RESULT_PATH = "show/result"

"""
Generic mPlane client for HTTP component-push workflows.

"""

class HttpClient(object):
    """
    Implements an mPlane HTTP client endpoint for component-push workflows. 
    This client endpoint can retrieve capabilities from a given URL, then post 
    Specifications to the component and retrieve Results or Receipts; it can
    also present Redeptions to retrieve Results.

    Caches retrieved Capabilities, Receipts, and Results.

    """
    def __init__(self, security, posturl, certfile=None):
        # store urls
        self._posturl = posturl
        url = urllib3.util.parse_url(posturl) 

        if security == True: 
            cert = mplane.utils.normalize_path(mplane.utils.read_setting(certfile, "cert"))
            key = mplane.utils.normalize_path(mplane.utils.read_setting(certfile, "key"))
            ca = mplane.utils.normalize_path(mplane.utils.read_setting(certfile, "ca-chain"))
            mplane.utils.check_file(cert)
            mplane.utils.check_file(key)
            mplane.utils.check_file(ca)
            self.pool = HTTPSConnectionPool(url.host, url.port, key_file=key, cert_file=cert, ca_certs=ca) 
        else: 
            self.pool = HTTPConnectionPool(url.host, url.port) 

        print("new client: "+self._posturl)

        # empty capability and measurement lists
        self._capabilities = OrderedDict()
        self._receipts = []
        self._results = []

    def get_mplane_reply(self, url, postmsg=None):
        """
        Given a URL, parses the object at the URL as an mPlane 
        message and processes it.

        Given a message to POST, sends the message to the given 
        URL and processes the reply as an mPlane message.

        """
        if postmsg is not None:
            print(postmsg)
            res = self.pool.urlopen('POST', url, 
                    body=postmsg.encode("utf-8"), 
                    headers={"content-type": "application/x-mplane+json"})
        else:
            res = self.pool.request('GET', url)
        print("get_mplane_reply "+url+" "+str(res.status)+" Content-Type "+res.getheader("content-type"))
        if res.status == 200 and \
           res.getheader("content-type") == "application/x-mplane+json":
            print("parsing json")
            return mplane.model.parse_json(res.data.decode("utf-8"))
        else:
            return [res.status, res.data.decode("utf-8")]

    def handle_message(self, msg, dn = None):
        """
        Processes a message. Caches capabilities, receipts, 
        and results, and handles Exceptions.

        """
        try:
            print("got message:")
            print(mplane.model.unparse_yaml(msg))

            if isinstance(msg, mplane.model.Capability):
                self.add_capability(msg, dn)
            elif isinstance(msg, mplane.model.Receipt):
                self.add_receipt(msg)
            elif isinstance(msg, mplane.model.Result):
                self.add_result(msg)
            elif isinstance(msg, mplane.model.Exception):
                self._handle_exception(msg)
            else:
                pass
        except:
            print("Supervisor returned: " + str(msg[0]) + " - " + msg[1])

    def add_capability(self, cap, dn):
        """Add a capability to the capability cache"""
        print("adding "+repr(cap))
        mplane.utils.add_value_to(self._capabilities, dn, cap)

    def clear_capabilities(self):
        """Clear the capability cache"""
        self._capabilities = OrderedDict()

    def retrieve_capabilities(self):
        """
        Given a URL, retrieves an object, parses it as an HTML page, 
        extracts links to capabilities, and retrieves and processes them
        into the capability cache.

        """
        self.clear_capabilities()
        url = "/" + S_CAPABILITY_PATH

        print("getting capabilities from " + url)
        res = self.pool.request('GET', url)
        if res.status == 200:
            body = json.loads(res.data.decode("utf-8"))
            for key in body:
                print(key)
                print(body[key])
                caps = mplane.utils.split_stmt_list(json.dumps(body[key]))
                for cap in caps:
                    self.handle_message(cap, key)
        else:
            print("Supervisor returned: " + str(res.status) + " - " + res.data.decode("utf-8"))
       
    def receipts(self):
        """Iterate over receipts (pending measurements)"""
        yield from self._receipts

    def add_receipt(self, msg):
        """Add a receipt. Check for duplicates."""
        if msg.get_token() not in [receipt.get_token() for receipt in self.receipts()]:
            self._receipts.append(msg)

    def redeem_receipt(self, msg):
        self.handle_message(self.get_mplane_reply("/"+S_RESULT_PATH, mplane.model.unparse_json(mplane.model.Redemption(receipt=msg))))

    def redeem_receipts(self):
        """
        Send all pending receipts to the Component,
        attempting to retrieve results.

        """
        for receipt in self.receipts():
            self.redeem_receipt(receipt)

    def _delete_receipt_for(self, token):
        self._receipts = list(filter(lambda msg: msg.get_token() != token, self._receipts))

    def results(self):
        """Iterate over receipts (pending measurements)"""
        yield from self._results

    def add_result(self, msg):
        """Add a receipt. Check for duplicates."""
        if msg.get_token() not in [result.get_token() for result in self.results()]:
            self._results.append(msg)
            self._delete_receipt_for(msg.get_token())

    def measurements(self):
        """Iterate over all measurements (receipts and results)"""
        yield from self._results
        yield from self._receipts

    def measurement_at(index):
        """Retrieve a measurement at a given index"""
        if index < len(self._results):
            return self._results[index]
        else:
            index -= len(self._results)
            return self._receipts[index]

    def _handle_exception(self, exc):
        print(repr(exc))

class ClientShell(cmd.Cmd):

    intro = 'Welcome to the mplane client shell.   Type help or ? to list commands.\n'
    prompt = '|mplane| '

    def preloop(self):
        global args
        parse_args()
        self._certfile = args.CERTFILE
        self._supervisor_ip4 = args.SUPERVISOR_IP4
        self._supervisor_port = args.SUPERVISOR_PORT
        self._client = None
        self._defaults = {}
        self._when = None

        if self._certfile:
            mplane.utils.check_file(self._certfile)


    def do_connect(self, arg):
        """Connect to a probe or supervisor and retrieve capabilities"""

        # define default url
        supvsr_url = 'http://%s:%d' % (self._supervisor_ip4, self._supervisor_port)
        if self._certfile:
            supvsr_url = 'https://%s:%d' % (self._supervisor_ip4, self._supervisor_port)
        capurl = None

        if arg:
            args = arg.split()
            # get the requested url for the probe or supervisor
            if len(args) >= 1:
                supvsr_url = args[0] 

        proto = supvsr_url.split('://')[0]
        if proto == 'http':
            ## force https in case security is available
            if self._certfile:
                supvsr_url = 'https://' + supvsr_url.split('://')[1]
            self._client = HttpClient(False, supvsr_url)
        elif proto == 'https':
            if self._certfile is not None:
                self._client = HttpClient(True, supvsr_url, self._certfile)
            else:
                raise SyntaxError("For https, need to specify the --certfile parameter when launching the client")
        else:
            raise SyntaxError("Incorrect url format or protocol. Supported protocols: http, https(, ssh)")

        self._client.retrieve_capabilities()

    def do_listcap(self, arg):
        """List available capabilities by index"""
        i = 1
        for key in self._client._capabilities:
            for cap in self._client._capabilities[key]:
                print(str(i) + " - " + cap.get_label() + " from " + key)
                i = i + 1

    def do_listmeas(self, arg):
        """List running/completed measurements by index"""
        for i, meas in enumerate(self._client.measurements()):
            print ("%4u: %s" % (i, repr(meas)))

    def do_showcap(self, arg):
        """
        Show a capability given a capability index; 
        without an index, shows all capabilities

        """        
        if len(arg) > 0:
            i = 1
            for key in self._client._capabilities:
                for cap in self._client._capabilities[key]:
                    if str(i) == arg:
                        self._show_stmt(cap)
                        return
                    i = i + 1
            print("No such capability: " + arg)
            
        else:
            i = 1
            for key in self._client._capabilities:
                for cap in self._client._capabilities[key]:
                    print ("cap %4u ---------------------------------------" % i)
                    self._show_stmt(cap)
                    i = i + 1

    def do_showmeas(self, arg):
        """Show receipt/results for a measurement, given a measurement index"""
        if len(arg) > 0:
            try:
                self._show_stmt(self._client.measurement_at(int(arg.split()[0])))
            except:
                print("No such measurement "+arg)
        else:
            for i, meas in enumerate(self._client.measurements()):
                print ("meas %4u --------------------------------------" % i)
                self._show_stmt(meas)

    def _show_stmt(self, stmt):
        print(mplane.model.unparse_yaml(stmt))

    def do_runcap(self, arg):
        """
        Run a capability given an index, filling in temporal 
        scope and defaults for parameters. Prompts for parameters 
        not yet entered.

        """
        i = 1
        # iterate over single capabilities
        for key in self._client._capabilities:
            for cap in self._client._capabilities[key]:
                if str(i) == arg:
                    
                    # fill the specification
                    spec = self.fill_spec(cap)
                    
                    # And send it to the server, with the correct JSON format
                    msg = "{\"" + key + "\":" + mplane.model.unparse_json(spec) + "}"
                    self._client.handle_message(self._client.get_mplane_reply("/"+S_SPECIFICATION_PATH, msg))
                    print("ok")
                    return
                    
                i = i + 1
        print("No such capability: " + arg)
            
    def fill_spec(self, cap):
        """
        Fills the parameters of a specification, 
        then validates and returns it ready to be enqueued

        """
        spec = mplane.model.Specification(capability=cap)
        
        # Set temporal scope or prompt for new one  
        while self._when is None or \
              not self._when.follows(cap.when()) or \
              (self._when.period is None and cap.when().period() is not None):
            sys.stdout.write("|when| = ")
            self._when = mplane.model.When(input())

        spec.set_when(self._when)

        # Fill in single values
        spec.set_single_values()

        # Fill in parameter values
        for pname in spec.parameter_names():
            if spec.get_parameter_value(pname) is None:
                if pname in self._defaults:
                    # set parameter value from defaults
                    print("|param| "+pname+" = "+self._defaults[pname])
                    spec.set_parameter_value(pname, self._defaults[pname])
                else:
                    # set parameter value with input
                    sys.stdout.write("|param| "+pname+" = ")
                    spec.set_parameter_value(pname, input())
            else:
                print("|param| "+pname+" = "+str(spec.get_parameter_value(pname)))

        # Validate specification
        spec.validate()
        return spec

    def do_redeem(self, arg):
        """Attempt to redeem all outstanding receipts"""
        self._client.redeem_receipts()
        print("ok")

    def do_show(self, arg):
        """Show a default parameter value, or all values if no parameter name given"""
        if len(arg) > 0:
            try:
                key = arg.split()[0]
                val = self._defaults[key]
                print(key + " = " + val)
            except:
                print("No such default "+key)
        else:
            print("%4u defaults" % len(self._defaults))
            for key, val in self._defaults.items():
                print(key + " = " + val)

    def do_set(self, arg):
        """Set a default parameter value"""
        try:
            sarg = arg.split()
            key = sarg.pop(0)
            val = " ".join(sarg)
            self._defaults[key] = val
            print(key + " = " + val)
        except:
            print("Couldn't set default "+arg)

    def do_when(self, arg):
        """Set a default temporal scope"""
        if len(arg) > 0:
            try:
                self._when = mplane.model.When(arg)
            except:
                print("Invalid temporal scope "+arg)
        else:
            print("when = "+str(self._when))

    def do_unset(self, arg):
        """Unset a default parameter value"""
        try:
            keys = arg.split()
            for key in keys:
                del self._defaults[key]
        except:
            print("Couldn't unset default(s) "+arg)

    def do_EOF(self, arg):
        """Exit the shell by typing ^D"""
        print("Ciao!")
        return True
        
def parse_args():
    global args
    parser = argparse.ArgumentParser(description="run mPlane client")

    parser.add_argument('-p', '--supervisor-port', metavar='port', dest='SUPERVISOR_PORT', default=DEFAULT_SV_PORT, type=int, \
                        help = 'connect to the supervisor on the specified port [default=%d]' % DEFAULT_SV_PORT)
    parser.add_argument('-d', '--supervisor-ipaddr', metavar='ip', dest='SUPERVISOR_IP4', default=DEFAULT_SV_IP4, \
                        help = 'connect to the supervisor on the specified IP address [default=%s]' % DEFAULT_SV_IP4)

    parser.add_argument('--disable-sec', action='store_true', default=False, dest='DISABLE_SEC',
                        help='Disable secure communication')
    parser.add_argument('-c', '--certfile', metavar="path", default=None, dest='CERTFILE',
                        help="Location of the configuration file for certificates")
    args = parser.parse_args()

    if args.DISABLE_SEC == False and not args.CERTFILE:
        print('\nerror: missing -c|--certfile option\n')
        parser.print_help()
        sys.exit(1)
        #raise ValueError("Need --logdir and --fileconf as parameters")

    
if __name__ == "__main__":
    mplane.model.initialize_registry()
    ClientShell().cmdloop()
