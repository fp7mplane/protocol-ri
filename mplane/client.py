#
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
import sys
import cmd
import readline
import urllib.request
import html.parser
import urllib.parse

from datetime import datetime, timedelta

CAPABILITY_PATH_ELEM = "capability"

class CrawlParser(html.parser.HTMLParser):
    def __init__(self, **kwargs):
        super(CrawlParser, self).__init__(**kwargs)
        self.urls = []

    def handle_starttag(self, tag, attrs):
        attrs = {k: v for (k,v) in attrs}
        if tag == "a" and "href" in attrs:
            self.urls.append(attrs["href"])

class HttpClient(object):
    """
    HTTP client endpoint. More docs go here.

    """
    def __init__(self, posturl, capurl=None):
        # store urls
        self._posturl = posturl
        if capurl is not None:
            self._capurl = capurl
        else:
            self._capurl = self._posturl
            if self._capurl[-1] != "/":
                self._capurl += "/"
            self._capurl += CAPABILITY_PATH_ELEM

        print("new client: "+self._posturl+" "+self._capurl)

        # empty capability and measurement lists
        self._capabilities = []
        self._receipts = []
        self._results = []

    def get_mplane_reply(self, url=None, postmsg=None):
        if postmsg is not None:
            if url is None:
                url = self._posturl
            req = urllib.request.Request(url, 
                    data=mplane.model.unparse_json(postmsg).encode("utf-8"),
                    headers={"Content-Type": "application/x-mplane+json"}, 
                    method="POST")
        else:
            req = urllib.request.Request(url)

        with urllib.request.urlopen(req) as res:
            print("get_mplane_reply "+url+" "+str(res.status)+" Content-Type "+res.getheader("Content-Type"))
            if res.status == 200 and \
               res.getheader("Content-Type") == "application/x-mplane+json":
                print("parsing json")
                return mplane.model.parse_json(res.read().decode("utf-8"))
            else:
                print("giving up")
                return None

    def handle_message(self, msg):
        print("got message:")
        print(mplane.model.unparse_yaml(msg))

        if isinstance(msg, mplane.model.Capability):
            self.add_capability(msg)
        elif isinstance(msg, mplane.model.Receipt):
            self.add_receipt(msg)
        elif isinstance(msg, mplane.model.Result):
            self.add_result(msg)
        elif isinstance(msg, mplane.model.Exception):
            self.handle_exception(msg)
        else:
            # FIXME do something diagnostic here
            pass

    def capabilities(self):
        """Iterate over capabilities"""
        yield from self._capabilities

    def capability_at(self, index):
        return self._capabilities[index]

    def add_capability(self, cap):
        print("adding "+repr(cap))
        self._capabilities.append(cap)

    def clear_capabilities(self):
        self._capabilities.clear()

    def retrieve_capabilities(self, listurl=None):
        # By default, use the stored capabilities 
        if listurl is None:
            listurl = self._capurl
            self.clear_capabilities()

        print("getting capabilities from "+listurl)
        with urllib.request.urlopen(listurl) as res:
            if res.status == 200:
                parser = CrawlParser(strict=False)
                parser.feed(res.read().decode("utf-8"))
                parser.close()
                for capurl in parser.urls:
                    self.handle_message(
                        self.get_mplane_reply(url=urllib.parse.urljoin(listurl, capurl)))
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
        for receipt in self.receipts():
            self.redeem_receipt(receipt)

    def delete_receipt_for(self, token):
        self._receipts = list(filter(lambda msg: msg.get_token() != token, self._receipts))

    def results(self):
        """Iterate over receipts (pending measurements)"""
        yield from self._results

    def add_result(self, msg):
        """Add a receipt. Check for duplicates."""
        if msg.get_token() not in [result.get_token() for results in self.results()]:
            self._results.append(msg)
            self.delete_receipt_for(msg.get_token())

    def measurements(self):
        """Iterate over all measurements (receipts and results)"""
        yield from self._results
        yield from self._receipts

    def measurement_at(index):
        if index >= len(self._results):
            index -= len(self._results)
            return self._receipts[index]
        else:
            return self._results[index]

    def handle_exception(self, exc):
        print(repr(exc))

class ClientShell(cmd.Cmd):

    intro = 'Welcome to the mplane client shell.   Type help or ? to list commands.\n'
    prompt = '|mplane| '

    def preloop(self):
        self._client = None
        self._defaults = {}

    def do_connect(self, arg):
        """Connect to a probe or supervisor via HTTP and retrieve capabilities"""
        args = arg.split()
        if len(args) >= 2:
            self._client = HttpClient(posturl=args[0], capurl=args[1])
        elif len(args) >= 1:
            self._client = HttpClient(posturl=args[0])
        else:
            print("Cannot connect without a url")

        self._client.retrieve_capabilities()

    def do_listcap(self, arg):
        """List available capabilities by number"""
        for i, cap in enumerate(self._client.capabilities()):
            print ("%4u: %s" % (i, repr(cap)))

    def do_listmeas(self, arg):
        """List running/completed measurements by number"""
        for i, meas in enumerate(self._client.measurements()):
            print ("%4u: %s" % (i, repr(meas)))

    def do_showcap(self, arg):
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
        """Show receipt/results for a measurement, given a number"""
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
        """Internal statement/result printer"""
        print(mplane.model.unparse_yaml(stmt))

    def do_runcap(self, arg):
        """
        Run a capability given a number, 
        filling in defaults for parameters, 
        and prompting for parameters not yet entered

        """
        # Retrieve a capability and create a specification
#        try:
        spec = mplane.model.Specification(
                    capability=self._client.capability_at(int(arg.split()[0])))
#        except:
#            print ("No such capability "+arg)
#            return

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

    def do_unset(self, arg):
        """Unset a default parameter value"""
        try:
            keys = arg.split()
            for key in keys:
                del self._defaults[key]
        except:
            print("Couldn't unset default(s) "+arg)

    def do_tsreset(self, arg):
        """Reset the temporal scope to run for 30 seconds 30 seconds from now"""
        st = datetime.utcnow()
        st += timedelta(seconds=30)
        et = st + timedelta(seconds=30)
        self._defaults["start"] = st.strftime("%Y-%m-%d %H:%M:%S")
        print("start = "+self._defaults["start"])
        self._defaults["end"] = et.strftime("%Y-%m-%d %H:%M:%S")
        print("end = "+self._defaults["end"])

    def do_EOF(self, arg):
        """Exit the shell by typing ^D"""
        print("Ciao!")
        return True

if __name__ == "__main__":
    mplane.model.initialize_registry()
    ClientShell().cmdloop()
