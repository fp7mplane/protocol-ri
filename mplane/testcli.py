### test command line client
### for integration into client.py
### do not use

import cmd
import readline
import mplane.model
import mplane.yaml

def get_capability(url):
    pass

def crawl_capabilities(url):
    pass

class ClientShell(cmd.Cmd):

    intro = 'Welcome to the mplane client shell.   Type help or ? to list commands.\n'
    prompt = '|mplane| '

    def preloop(self):
        self._caps=[]
        self._meas=[]
        self._defaults={}

    def do_connect(self, arg):
        """Connect to a component by URL and retrieve its capabilities"""
        pass

    def do_listcap(self, arg):
        """List available capabilities by number"""
        print("%4u capabilities:" % len(self._defaults))
        for cap, i in enumerate(self._caps):
            print ("%4u: %s" % i, repr(cap))

    def do_listmeas(self, arg):
        """List running/completed measurements by number"""
        print("%4u measurements:" % len(self._defaults))
        for meas, i in enumerate(self._meas):
            print ("%4u: %s" % i, repr(meas))

    def do_showcap(self, arg):
        """Show details for a capability, given a number"""
        if len(arg) > 0:
            try:
                self.show_stmt(self._caps[int(arg.split()[0])])
            except:
                print("No such capability "+arg.split()[0])
        else:
            for cap in self._caps:
                print ("cap %4u ---------------------------------------" % i)
                self._show_stmt(cap)

    def do_showmeas(self, arg):
        """Show receipt/results for a measurement, given a number"""
        if len(arg) > 0:
            try:
                self.show_stmt(self._meas[int(arg.split()[0])])
            except:
                print("No such measurement "+arg.split[0])
        else:
            for meas, i in enumerate(self._meas):
                print ("meas %4u --------------------------------------" % i)
                self._show_stmt(meas)

    def _show_stmt(self, arg):
        """Internal statement/result printer"""
        print(mplane.yaml.unparse(spec))

    def do_runcap(self, arg):
        """
        Run a capability given a number, 
        filling in defaults for parameters, 
        and prompting for parameters not yet entered

        """
        print("Can't run capabilities yet")

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
            print("%4u defaults:" % len(self._defaults))
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

    def do_EOF(self, arg):
        print("Ciao!")
        return True

if __name__ == "__main__":
    ClientShell().cmdloop()
