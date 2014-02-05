### test command line client
### for integration into client.py
### do not use

import cmd
import readline
import mplane.model
import mplane.json
import mplane.yaml
import urllib.request
import html.parser

class CrawlParser(html.parser.HTMLParser):
    def __init__(self, **kwargs):
        super(LinkParser, self).__init__(**kwargs)
        self.urls = []

    def handle_starttag(self, tag, attrs):
        if tag == "a" and "href" in attrs:
            self.urls.append(attrs["href"])

def parse_capability_links(htbody):
    parser = CrawlParser(strict=False)
    parser.feed(htbody)
    parser.close()
    return parser.urls

def get_mplane_message(url_or_req):
    with urllib.request.urlopen(url_or_req) as res:
        if res.status == 200 and \
               res.getheader("Content-Type") == "application/x-mplane+json":
            return mplane.json.parse(res.read())
        else:
            return None

def crawl_capabilities(url):
    with urllib.request.urlopen(url) as res:
        if res.status == 200 and \
               res.getheader("Content-Type") == "text/xhtml":
            urls = parse_capability_links(res.read())

    caps = []
    for url in urls:
        cap = get_mplane_message(url)
        if cap is not None:
            caps.append(cap)

    return caps

def post_message(url, msg):
    req = urllib.request.Request(url, 
            data=mplane.json.unparse(msg),
            headers={"Content-Type", "application/x-mplane+json"}, 
            method="POST")
    return get_mplane_message(req)

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
        print("%4u capabilities" % len(self._defaults))
        for cap, i in enumerate(self._caps):
            print ("%4u: %s" % i, repr(cap))

    def do_listmeas(self, arg):
        """List running/completed measurements by number"""
        print("%4u measurements" % len(self._defaults))
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
        # Retrieve a capability and create a specification
        try:
            spec = mplane.model.Specification(capability=self._caps[int(arg.split()[0])])
        except:
            print ("No such capability "+arg)
            return

        # Fill in parameter values
        for param in cap.parameter_names():
            # WORK POINTER
            pass


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

    def do_EOF(self, arg):
        """Exit the shell by typing ^D"""
        print("Ciao!")
        return True

if __name__ == "__main__":
    ClientShell().cmdloop()
