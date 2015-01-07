#
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
##
# mPlane Protocol Reference Implementation
# Simple client command-line interface
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

class ClientShell(cmd.Cmd):

    intro = 'mPlane client shell (rev 7.1.2015). \n'\
            'Type help or ? to list commands. ^D to exit.\n'
    prompt = '|mplane| '

    def __init__(self, tls_state=None):
        super().__init__()
        self._client = mplane.client.HttpClient(tls_state = tls_state)
        self._defaults = {}
        self._when = None

        # don't print tracebacks by default
        self._print_tracebacks = False

    def do_seturl(self, arg):
        """
        Set the default URL for this client. 
        The default URL is the URL that will be used to invoke 
        capabilities which do not have an explicit link.

        Usage: seturl [url]

        """
        try:
            url = arg.split()[0]
        except:
            print("Usage: seturl [url]")
            return

        self._client.set_default_url(url)

    def do_getcap(self, arg):
        """
        Retrieve capabilities from a given URL.

        Usage: getcap [url]

        """
        try:
            url = arg.split()[0]
        except:
            print("Usage: getcap [url]")
            return

        self._client.retrieve_capabilities(url)
        print("ok")

    def do_listcap(self, arg):
        """
        List available capabilities by label (if available) or token 
        (for unlabeled capabilities)

        Usage: listcap 

        """
        for label in self._client.capability_labels():
            print("Capability %s (token %s)" %
                  (label, self._client.capability_for(label).get_token()))

        for token in self._client_capability_tokens():
            cap = self._client.capability_for(token)
            if cap.get_label() is None:
                print("Capability (token %s)" % (token))

    def do_showcap(self, arg):
        """
        Show details for a capability by label or token

        Usage: showcap [label-or-token] 

        """
        print (mplane.render.render_text(self.client.capability_for(arg)))

   def do_when(self, arg):
        """
        Get or set a default temporal scope to use for capability 
        invocation.

        Usage: when
        Usage: when [temporal-scope]

        """
        if len(arg) > 0:
            try:
                self._when = mplane.model.When(arg)
            except:
                print("Invalid temporal scope "+arg)
                return

        print("when = "+str(self._when))

    def do_set(self, arg):
        """
        Set a default parameter value for subsequent capability 
        invocation.

        Usage: set [parameter-name] [value]

        """
        try:
            sarg = arg.split()
            key = sarg.pop(0)
            val = " ".join(sarg)
            self._defaults[key] = val
            print(key + " = " + val)
        except:
            print("Couldn't set default "+arg)

    def do_unset(self, arg):
        """
        Unset values for previously set default parameters. 
        Without an argument, clears all defaults.

        Usage: unset
        Usage: unset [parameter-name] ([parameter-name] ...)

        """
        if len(arg) > 0:
            try:
                keys = arg.split()
                for key in keys:
                    del self._defaults[key]
            except:
                print("Couldn't unset default(s) "+arg)
                return
        else:
            self._defaults.clear()

        print("ok")

    def do_runcap(self, arg):
        """
        Invoke a capability, identified by label or token. Uses any
        default temporal scope set by a previous when command, and any
        applicable default parameters. Parameters and temporal
        scopes required for the capability but not present are prompted for.

        The optional second argument sets a label for the specification (which
        will apply to the receipt and results as well). If no relabel is given,
        the specification will have the same label as the capability, with a
        serial number attached.

        Usage: runcap [label-or-token] ([relabel])

        """

        try:
            arglist = arg.split()

            if len(arglist) >= 1:
                capspec = arglist[0]
                if len(arglist) >= 2:
                    relabel = arglist[1]
                else:
                    relabel = None
            else:
                print("Usage: runcap [label-or-token] ([relabel])")
                return
        except:
            print("Usage: runcap [label-or-token] ([relabel])")
            return

        # Retrieve a capability
        cap = self._client.capability_for(capspec)

        # Prompt for when if missing or inappropriate
        while self._when is None or \
              not self._when.follows(cap.when()):
            sys.stdout.write("|when| = ")
            self._when = mplane.model.When(input())

        # Prompt for missing capabilities
        # WORK POINTER

        # Now invoke it
        self._client.invoke_capability(cap.get_token(), when, params, relabel)
        print("ok")

    def do_connect(self, arg):
        """Connect to a probe or supervisor and retrieve capabilities"""
        args = arg.split()
        if len(args) >= 2:
            capurl = args[1]     
        elif len(args) >= 1:
            capurl = None
        else:
            print("Cannot connect without a url")
            return

        proto = args[0].split('://')[0]
        if proto == 'http':
            self._client = HttpClient(args[0], capurl)
        elif proto == 'https':
            if self._tlsconfig is not None:
                self._client = HttpClient(args[0], capurl, self._tlsconfig)
            else:
                raise SyntaxError("For HTTPS, need to specify the --tlsconfig parameter when launching the client")
        else:
            raise SyntaxError("Incorrect url format or protocol. Supported protocols: http, https")

        self._client.retrieve_capabilities()

    def do_listmeas(self, arg):
        """List running/completed measurements by index"""
        for i, meas in enumerate(self._client.measurements()):
            print ("%4u: %s" % (i, repr(meas)))

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

    def do_tbenable(self, arg):
        """Enable tracebacks on uncaught exceptions"""
        self._print_tracebacks = True

    def do_EOF(self, arg):
        """Exit the shell by typing ^D"""
        print("Ciao!")
        self.exited = True
        return True

    def handle_uncaught(self, e):
        print("An exception occurred:")
        print(e)
        if self._print_tracebacks:
            traceback.print_tb(sys.exc_info()[2])
        print("You can try to continue, but client state may be inconsistent.")
        print("Use the connect command to start over.\n")

        
def parse_args():
    parser = argparse.ArgumentParser(description="Run an mPlane client")
    parser.add_argument('--tlsconfig', metavar="config-file",
                        help="TLS configuration file")
    return parser.parse_args()
    
if __name__ == "__main__":
    # boot the model
    mplane.model.initialize_registry()

    # look for TLS configuration
    args = parse_args()
    if args.tlsconfig is not None:
        mplane.utils.check_file(args.tlsconfig)

    # create a shell
    cs = ClientShell(tlsconfig=args.tlsconfig)

    while not cs.exited:
        try:
            cs.cmdloop()
        except Exception as e:
            cs.handle_uncaught(e)