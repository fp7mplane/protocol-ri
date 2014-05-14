#
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
##
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
import mplane.httpsrv
import sys
import cmd
import readline
import html.parser
import urllib3
from urllib3 import HTTPSConnectionPool
from urllib3 import HTTPConnectionPool
import os.path
import argparse

from datetime import datetime, timedelta

CAPABILITY_PATH_ELEM = "capability"

"""
Generic mPlane client for HTTP component-push workflows.

"""

class CrawlParser(html.parser.HTMLParser):
    """
    HTML parser class to extract all URLS in a href attributes in
    an HTML page. Used to extract links to Capabilities exposed
    as link collections.

    """
    def __init__(self, **kwargs):
        super(CrawlParser, self).__init__(**kwargs)
        self.urls = []

    def handle_starttag(self, tag, attrs):
        attrs = {k: v for (k,v) in attrs}
        if tag == "a" and "href" in attrs:
            self.urls.append(attrs["href"])

class HttpClient(object):
    """
    Implements an mPlane HTTP client endpoint for component-push workflows. 
    This client endpoint can retrieve capabilities from a given URL, then post 
    Specifications to the component and retrieve Results or Receipts; it can
    also present Redeptions to retrieve Results.

    Caches retrieved Capabilities, Receipts, and Results.

    """
    def __init__(self, security, posturl, capurl=None, certfile=None):
        # store urls
        self._posturl = posturl
        if capurl is not None:
            if capurl[0] != "/": 
                self._capurl = "/" + capurl 
            else: 
                self._capurl = capurl 
        else: 
            self._capurl = "/" + CAPABILITY_PATH_ELEM 
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

        print("new client: "+self._posturl+" "+self._capurl)

        # empty capability and measurement lists
        self._capabilities = []
        self._receipts = []
        self._results = []

    def get_mplane_reply(self, url=None, postmsg=None):
        """
        Given a URL, parses the object at the URL as an mPlane 
        message and processes it.

        Given a message to POST, sends the message to the given 
        URL and processes the reply as an mPlane message.

        """
        if postmsg is not None:
            print(postmsg)
            if url is None:
                url = "/"
            res = self.pool.urlopen('POST', url, 
                    body=mplane.model.unparse_json(postmsg).encode("utf-8"), 
                    headers={"content-type": "application/x-mplane+json"})
        else:
            res = self.pool.request('GET', url)
        print("get_mplane_reply "+url+" "+str(res.status)+" Content-Type "+res.getheader("content-type"))
        if res.status == 200 and \
           res.getheader("content-type") == "application/x-mplane+json":
            print("parsing json")
            return mplane.model.parse_json(res.data.decode("utf-8"))
        else:
            print("giving up")
            return None

    def handle_message(self, msg):
        """
        Processes a message. Caches capabilities, receipts, 
        and results, and handles Exceptions.

        """
        print("got message:")
        print(mplane.model.unparse_yaml(msg))

        if isinstance(msg, mplane.model.Capability):
            self.add_capability(msg)
        elif isinstance(msg, mplane.model.Receipt):
            self.add_receipt(msg)
        elif isinstance(msg, mplane.model.Result):
            self.add_result(msg)
        elif isinstance(msg, mplane.model.Exception):
            self._handle_exception(msg)
        else:
            # FIXME do something diagnostic here
            pass

    def capabilities(self):
        """Iterate over capabilities"""
        yield from self._capabilities

    def capability_at(self, index):
        """Retrieve a capability at a given index"""
        return self._capabilities[index]

    def add_capability(self, cap):
        """Add a capability to the capability cache"""
        print("adding "+repr(cap))
        self._capabilities.append(cap)

    def clear_capabilities(self):
        """Clear the capability cache"""
        self._capabilities.clear()

    def retrieve_capabilities(self, listurl=None):
        """
        Given a URL, retrieves an object, parses it as an HTML page, 
        extracts links to capabilities, and retrieves and processes them
        into the capability cache.

        """
        if listurl is None:
            listurl = self._capurl
            self.clear_capabilities()

        print("getting capabilities from "+self._capurl)
        res = self.pool.request('GET', self._capurl)
        if res.status == 200:
            parser = CrawlParser(strict=False)
            parser.feed(res.data.decode("utf-8"))
            parser.close()
            for capurl in parser.urls:
                self.handle_message(self.get_mplane_reply(url=capurl))
        else:
            print(listurl+": "+str(res.status))
       
    def receipts(self):
        """Iterate over receipts (pending measurements)"""
        yield from self._receipts

    def add_receipt(self, msg):
        """Add a receipt. Check for duplicates."""
        if msg.get_token() not in [receipt.get_token() for receipt in self.receipts()]:
            self._receipts.append(msg)

    def redeem_receipt(self, msg):
        self.handle_message(self.get_mplane_reply(postmsg=mplane.model.Redemption(receipt=msg)))

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
        if index >= len(self._results):
            index -= len(self._results)
            return self._receipts[index]
        else:
            return self._results[index]

    def _handle_exception(self, exc):
        print(repr(exc))


class SshClient(object):
    """ Skeleton for SSH Client"""
    
    def __init__(self, security, posturl, capurl=None):
        pass

class ClientShell(cmd.Cmd):

    intro = 'Welcome to the mplane client shell.   Type help or ? to list commands.\n'
    prompt = '|mplane| '

    def preloop(self):
        global args
        parse_args()
        self._certfile = args.CERTFILE
        self._service_address = args.SERVICE_ADDRESS
        self._service_port = args.SERVICE_PORT
        self._client = None
        self._defaults = {}
        self._when = None

        if self._certfile:
            mplane.utils.check_file(self._certfile)


    def do_connect(self, arg):
        """Connect to a probe or supervisor and retrieve capabilities"""

        # define default url
        supvsr_url = 'http://%s:%d' % (self._service_address, self._service_port)
        if self._certfile:
            supvsr_url = 'https://%s:%d' % (self._service_address, self._service_port)
        capurl = None

        if arg:
            args = arg.split()
            # get the requested url for the probe or supervisor
            if len(args) >= 1:
                supvsr_url = args[0]
            # get the requested 
            if len(args) > 1:
                capurl = args[1]     

        proto = supvsr_url.split('://')[0]
        if proto == 'http':
            ## force https in case security is available
            if self._certfile:
                supvsr_url = 'https://' + supvsr_url.split('://')[1]
            self._client = HttpClient(False, supvsr_url, capurl)
        elif proto == 'https':
            if self._certfile is not None:
                self._client = HttpClient(True, supvsr_url, capurl, self._certfile)
            else:
                raise SyntaxError("For https, need to specify the --certfile parameter when launching the client")
        elif proto == 'ssh':
            self._client = SshClient(True, supvsr_url, capurl)
        else:
            raise SyntaxError("Incorrect url format or protocol. Supported protocols: http, https(, ssh)")

        self._client.retrieve_capabilities()

    def do_listcap(self, arg):
        """List available capabilities by index"""
        for i, cap in enumerate(self._client.capabilities()):
            print ("%4u: %s" % (i, repr(cap)))

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
            try:
                self._show_stmt(self._client.capability_at(int(arg.split()[0])))
            except:
                print("No such capability "+arg)
        else:
            for i, cap in enumerate(self._client.capabilities()):
                print ("cap %4u ---------------------------------------" % i)
                self._show_stmt(cap)

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
        # Retrieve a capability and create a specification
#        try:
        cap = self._client.capability_at(int(arg.split()[0]))
        spec = mplane.model.Specification(capability=cap)
#        except:
#            print ("No such capability "+arg)
#            return

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
                # FIXME we really want to unparse this
                print("|param| "+pname+" = "+str(spec.get_parameter_value(pname)))

        # Validate specification
        spec.validate()

        # And send it to the server
        self._client.handle_message(self._client.get_mplane_reply(postmsg=spec))
        print("ok")

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

    parser.add_argument('-p', '--service-port', metavar='port', dest='SERVICE_PORT', default=mplane.httpsrv.DEFAULT_LISTEN_PORT, type=int, \
                        help = 'run the service on the specified port [default=%d]' % mplane.httpsrv.DEFAULT_LISTEN_PORT)
    parser.add_argument('-H', '--service-ipaddr', metavar='ip', dest='SERVICE_ADDRESS', default=mplane.httpsrv.DEFAULT_LISTEN_IP4, \
                        help = 'run the service on the specified IP address [default=%s]' % mplane.httpsrv.DEFAULT_LISTEN_IP4)

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
