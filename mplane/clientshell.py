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

# Needs to be rewritten to use client.py interface
class ClientShell(cmd.Cmd):

    intro = 'mPlane client shell (rev 25.11.2014). \n'\
            'Type help or ? to list commands. ^D to exit.\n'
    prompt = '|mplane| '

    def __init__(self, tlsconfig=None):
        super().__init__()
        self.exited = False
        self._client = None
        self._defaults = {}
        self._when = None
        self._tlsconfig = tlsconfig 
        self._mserial = 0

        # don't print tracebacks by default
        self._print_tracebacks = False

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

        Usage: runcap (number or label) (spec label)]

        """

        arglist = arg.split()

        if len(arglist) >= 1:
            capspec = arglist[0]
            if len(arglist) >= 2:
                relabel = arglist[1]
            else:
                relabel = None
        else:
            raise ValueError("runcap requires a capability index or label")

        # Retrieve a capability
        try:
            capnum = int(capspec)
        except:
            capnum = None

        if capnum:
            cap = self._client.capability_at(capnum)
        else:
            cap = self._client.capability_by_label(capspec)

        # and create a specification
        spec = mplane.model.Specification(capability=cap)

        # Set temporal scope or prompt for new one
        while self._when is None or \
              not self._when.follows(cap.when()):
            sys.stdout.write("|when| = ")
            self._when = mplane.model.When(input())

        spec.set_when(self._when)

        # Fill in single values and retoken the spec
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

        # Retoken and relabel the specification
        spec.retoken()
        if relabel:
            spec.relabel(relabel)
        else:
            spec.relabel(cap.get_label() + "-" + str(self._mserial))

        # Increase sent serial number
        self._mserial += 1

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