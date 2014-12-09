# mPlane Protocol Reference Implementation
# Simple mPlane Supervisor and CLI (JSON over HTTP)
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

from threading import Thread
import mplane.model
import mplane.utils
import mplane.sec
import mplane.sv_handlers
import ssl
import sys
import cmd
import copy
import math
from collections import OrderedDict
import tornado.web
import tornado.httpserver
import argparse

DEFAULT_LISTEN_PORT = 8888
DEFAULT_LISTEN_IP4 = '127.0.0.1'

REGISTRATION_PATH = "register/capability"
SPECIFICATION_PATH = "show/specification"
RESULT_PATH = "register/result"
S_CAPABILITY_PATH = "show/capability"
S_SPECIFICATION_PATH = "register/specification"
S_RESULT_PATH = "show/result"


"""
Generic mPlane Supervisor for cap-push, spec-pull workflows.
Actually it is an HTTP server

"""
    
def parse_args():
    """
    Parse arguments from command line
    
    """
    global args
    parser = argparse.ArgumentParser(description="run mPlane Supervisor")

    parser.add_argument('-p', '--listen-port', metavar='port', dest='LISTEN_PORT', default=DEFAULT_LISTEN_PORT, type=int, \
                        help = 'run the service on the specified port [default=%d]' % DEFAULT_LISTEN_PORT)
    parser.add_argument('-s', '--listen-ipaddr', metavar='ip', dest='LISTEN_IP4', default=DEFAULT_LISTEN_IP4, \
                        help = 'run the service on the specified IP address [default=%s]' % DEFAULT_LISTEN_IP4)                        
    parser.add_argument('--disable-ssl', action='store_true', default=False, dest='DISABLE_SSL',
                        help='Disable ssl communication')
    parser.add_argument('-c', '--certfile', metavar="path", default=None, dest='CERTFILE',
                        help="Location of the configuration file for certificates")
    args = parser.parse_args()

    if args.DISABLE_SSL == False and not args.CERTFILE:
        print('\nerror: missing -c|--certfile option\n')
        parser.print_help()
        sys.exit(1)

def listen_in_background():
    """
    The server listens for requests in background, while 
    the supervisor console remains accessible
    """
    tornado.ioloop.IOLoop.instance().start()

class HttpSupervisor(object):
    """
    Implements an mPlane HTTP supervisor endpoint for component-push workflows. 
    This supervisor endpoint can register capabilities sent by components, then expose 
    Specifications for which the component will periodically check, and receive Results or Receipts
 
    This supervisor aggregates capabilities of the same type.
    Also, it exposes Capabilities to a Client, receives Specifications from it, and returns Results.
    
    Performs Authentication (both with Probes and Client) and Authorization (with Client)
    Caches retrieved Capabilities, Receipts, and Results.
    """
    def __init__(self):
        parse_args()
                
        application = tornado.web.Application([
        
                # Handlers of the HTTP Server
                (r"/" + REGISTRATION_PATH, mplane.sv_handlers.RegistrationHandler, {'supervisor': self}),
                (r"/" + REGISTRATION_PATH + "/", mplane.sv_handlers.RegistrationHandler, {'supervisor': self}),
                (r"/" + SPECIFICATION_PATH, mplane.sv_handlers.SpecificationHandler, {'supervisor': self}),
                (r"/" + SPECIFICATION_PATH + "/", mplane.sv_handlers.SpecificationHandler, {'supervisor': self}),
                (r"/" + RESULT_PATH, mplane.sv_handlers.ResultHandler, {'supervisor': self}),
                (r"/" + RESULT_PATH + "/", mplane.sv_handlers.ResultHandler, {'supervisor': self}),
                (r"/" + S_CAPABILITY_PATH, mplane.sv_handlers.S_CapabilityHandler, {'supervisor': self}),
                (r"/" + S_CAPABILITY_PATH + "/", mplane.sv_handlers.S_CapabilityHandler, {'supervisor': self}),
                (r"/" + S_SPECIFICATION_PATH, mplane.sv_handlers.S_SpecificationHandler, {'supervisor': self}),
                (r"/" + S_SPECIFICATION_PATH + "/", mplane.sv_handlers.S_SpecificationHandler, {'supervisor': self}),
                (r"/" + S_RESULT_PATH, mplane.sv_handlers.S_ResultHandler, {'supervisor': self}),
                (r"/" + S_RESULT_PATH + "/", mplane.sv_handlers.S_ResultHandler, {'supervisor': self}),
            ])
            
        # check if security is enabled, if so read certificate files
        self._sec = not args.DISABLE_SSL   
        if self._sec == True:
            self.ac = mplane.sec.Authorization(self._sec)
            self.base_url = "https://" + args.LISTEN_IP4 + ":" + str(args.LISTEN_PORT) + "/"
            cert = mplane.utils.normalize_path(mplane.utils.read_setting(args.CERTFILE, "cert"))
            key = mplane.utils.normalize_path(mplane.utils.read_setting(args.CERTFILE, "key"))
            ca = mplane.utils.normalize_path(mplane.utils.read_setting(args.CERTFILE, "ca-chain"))
            mplane.utils.check_file(cert)
            mplane.utils.check_file(key)
            mplane.utils.check_file(ca)
            
            http_server = tornado.httpserver.HTTPServer(application, ssl_options=dict(certfile=cert, keyfile=key, cert_reqs=ssl.CERT_REQUIRED, ca_certs=ca))
        else:
            self.base_url = "http://" + args.LISTEN_IP4 + ":" + str(args.LISTEN_PORT) + "/"
            http_server = tornado.httpserver.HTTPServer(application)
         
        # run the server   
        http_server.listen(args.LISTEN_PORT, args.LISTEN_IP4)
        t = Thread(target=listen_in_background)
        t.setDaemon(True)
        t.start()

        print("new Supervisor: "+str(args.LISTEN_IP4)+":"+str(args.LISTEN_PORT))
   
        # structures for storing Capabilities, Specifications and Results
        self._capabilities = OrderedDict()
        self._specifications = OrderedDict()
        self._receipts = OrderedDict()
        self._results = OrderedDict()
        self._dn_to_ip = dict()              # DN - IP associations
        self._label_to_dn = dict()           # Cap Label - DN associations
        self._registered_dn = []
        
    def register(self, cap, dn):
        """
        This function stores the new capability in the corresponding structures
        """
        
        # stores the association Label - DN
        label = cap.get_label()
        mplane.utils.add_value_to(self._label_to_dn, label, dn)
        
        # stores the DN to keep track of registered DNs
        self._registered_dn.append(dn)

        # register capability
        mplane.utils.add_value_to(self._capabilities, dn, cap)
        return
            
    def add_result(self, msg, dn):
        """Add a result. Check for duplicates and if result is expected."""
        if dn in self._receipts:
            for receipt in self._receipts[dn]:
                if str(receipt.get_token()) == str(msg.get_token()):
                    if dn not in self._results:
                        self._results[dn] = [msg]
                    else:
                        for result in self._results[dn]:
                            if str(result.get_token()) == str(msg.get_token):
                                print("WARNING: Duplicated result received!")
                                return False
                        self._results[dn].append(msg)
                    
                    self._receipts[dn].remove(receipt)
                    return True
                
        print("WARNING: Received an unexpected Result!")
        return False
        
    def add_spec(self, spec, dn):
        """
        Add a specification to the queue. Check for already running specs, 
        and for already enqueued specs of the same type
        """
        
        # If unset, set token
        if spec._token is None:
            spec._token = spec._default_token()
          
        if dn not in self._specifications:
            # check if a specification of the same type is already running on the probe
            if dn in self._receipts:
                for rec in self._receipts[dn]:
                    if str(rec.get_token()) == str(spec.get_token()):
                        print("There is already a Measurement running for this Capability. Try again later")
                        return False
            self._specifications[dn] = [spec]
            return True
        else:
            # check if a specification is already in queue for the needed probe
            for prev_spec in self._specifications[dn]:
                if spec.fulfills(prev_spec):
                    print("There is already a Specification for this Capability. Try again later")
                    return False
            self._specifications[dn].append(spec)
            return True

    def measurements(self):
        """Return a list of all the ongoing measurements (specifications, receipts and results)"""
        measurements = OrderedDict()
        
        for dn in self._specifications:
            if dn not in measurements:
                measurements[dn] = copy.deepcopy(self._specifications[dn])
            else:
                for spec in self._specifications[dn]:
                    measurements[dn].append(spec)
        
        for dn in self._receipts:
            if dn not in measurements:
                measurements[dn] = copy.deepcopy(self._receipts[dn])
            else:
                for receipt in self._receipts[dn]:
                    measurements[dn].append(receipt)
                
        for dn in self._results:
            if dn not in measurements:
                measurements[dn] = copy.deepcopy(self._results[dn])
            else:
                for result in self._results[dn]:
                    measurements[dn].append(result)
                
        return measurements

    def _handle_exception(self, exc):
        print(repr(exc))

class SupervisorShell(cmd.Cmd):

    intro = 'Welcome to the mPlane Supervisor shell.   Type help or ? to list commands.\n'
    prompt = '|mplane| '

    def preloop(self):
        self._supervisor = HttpSupervisor()
        self._defaults = {}
        self._when = None

    def do_listcap(self, arg):
        """List available capabilities by index"""
        i = 1
        for key in self._supervisor._capabilities:
            for cap in self._supervisor._capabilities[key]:
                print(str(i) + " - " + cap.get_label() + " fsdfswfdrom " + self._supervisor._dn_to_ip[key])
                i = i + 1

    def do_showcap(self, arg):
        """
        Show a capability given a capability index; 
        without an index, shows all capabilities

        """
        if len(arg) > 0:
            i = 1
            for key in self._supervisor._capabilities:
                for cap in self._supervisor._capabilities[key]:
                    if str(i) == arg:
                        self._show_stmt(cap)
                        return
                    i = i + 1
            print("No such capability: " + arg)
            
        else:
            for key in self._supervisor._capabilities:
                for cap in self._supervisor._capabilities[key]:
                    self._show_stmt(cap)
            
    def do_listmeas(self, arg):
        """List enqueued/running/completed measurements by index"""
        i = 1
        meas = self._supervisor.measurements()
        for dn in meas:
            for m in meas[dn]:
                print(str(i) + " - " + repr(m))
                i = i + 1

    def do_showmeas(self, arg):
        """
        Show specification/receipt/results for a measurement, given a measurement index.
        """
        meas = self._supervisor.measurements()
        if len(arg) > 0:
            i = 1
            for dn in meas:
                for m in meas[dn]:
                    if str(i) == arg:
                        self._show_stmt(m)
                        return
                    i = i + 1
            print("No such measurement: " + arg)
        else:
            for dn in meas:
                for m in meas[dn]:
                    self._show_stmt(m)

    def _show_stmt(self, stmt):
        print(mplane.model.unparse_yaml(stmt))

    def do_runcap(self, arg):
        """
        Run a capability given an index, filling in temporal 
        scope and defaults for parameters. Prompts for parameters 
        not yet entered.

        """
        i = 1
        # iterate over capabilities
        for key in self._supervisor._capabilities:
            for cap in self._supervisor._capabilities[key]:
                if str(i) == arg:
                    spec = self.fill_spec(cap)
                    # enqueue the spec for the component
                    if not self._supervisor.add_spec(spec, key):
                        mplane.utils.print_then_prompt("Specification is temporarily unavailable. Try again later")
                        return
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
            
    def do_exit(self, arg): 
        """Exits from this shell"""
        
        return True
    
if __name__ == "__main__":
    mplane.model.initialize_registry()
    SupervisorShell().cmdloop()