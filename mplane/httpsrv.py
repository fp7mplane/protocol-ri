#
# mPlane Protocol Reference Implementation
# Tornado web server bindings
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

import tornado.web
import mplane.model
import mplane.json

SLEEP_QUANTUM = 0.250
CAPABILITY_PATH_ELEM = "capability"

class DiscoveryHandler(tornado.web.RequestHandler):

    def initialize(self, scheduler):
        self.scheduler = scheduler

    def get(self):
        # capabilities
        path = self.request.path.split("/")[1:]
        print("DiscoveryHandler path is "+repr(path))
        if path[0] == CAPABILITY_PATH_ELEM:
            if (len(path) == 1 or path[1] is None):
                self._respond_capability_links()
            else:
                self._respond_capability(path[1])
        else:
            # FIXME how do we tell tornado we don't want to handle this?
            raise ValueError("I only know how to handle /"+CAPABILITY_PATH_ELEM+" URLs via HTTP GET")

    def _respond_capability_links(self):
        self.set_status(200)
        self.set_header("Content-Type", "text/html")
        self.write("<html><head><title>Capabilities</title></head><body>")
        self.write("available mplane capabilities:<br/>")
        for key in self.scheduler.capability_keys:
            self.write("<a href='/capability/" + key + "'>" + key + "</a><br/>")
            self.write(key)
            self.write("'>")
            self.write(key)
        self.write("</body></html>")
        self.finish()

    def _respond_capability(self, key):
        self._respond_message(self.scheduler.capability_for_key(key))

class MessagePostHandler(tornado.web.RequestHandler):

    def initialize(self, scheduler, immediate_ms = 5000):
        self.scheduler = scheduler
        self.immediate_ms = immediate_ms

    def post(self):
        # unwrap json message from body
        if (self.request.headers["Content-Type"] == "application/x-mplane+json"):
            msg = mplane.json.parse(self.request.body)
        else:
            # FIXME how do we tell tornado we don't want to handle this?
            raise ValueError("I only know how to handle mPlane JSON messages via HTTP POST")

        # hand message to scheduler
        reply = self.scheduler.receive_message(msg)

        # wait for immediate delay
        if immediate_ms > 0 and \
           isinstance(msg, mplane.model.Specification) and \
           isinstance(reply, mplane.model.Receipt):
            job = self.scheduler.job_for_message(reply)
            wait_start = datetime.utcnow()
            while (datetime.utcnow() - wait_start).total_seconds() * 1000 < immediate_ms:
                time.sleep(SLEEP_QUANTUM)
                if job.finished():
                    reply = job.get_reply()
                    break

        # return reply
        _respond_message(reply)

    def _respond_message(self, msg):
        if isinstance(msg, mplane.model.Exception):
            self.set_status(500)
        else:
            self.set_status(200)

        self.set_header("Content-Type", "application/x-mplane+json")
        self.write(mplane.json.unparse(msg))
        self.finish()

def runloop(scheduler, port=8888):
    application = tornado.web.Application([
            (r"/", mplane.httpsrv.MessagePostHandler, {'scheduler': scheduler}),
            (r"/"+CAPABILITY_PATH_ELEM, mplane.httpsrv.DiscoveryHandler, {'scheduler': scheduler}),
            (r"/"+CAPABILITY_PATH_ELEM+"/.*", mplane.httpsrv.DiscoveryHandler, {'scheduler': scheduler})
        ])
    application.listen(port)
    tornado.ioloop.IOLoop.instance().start()
