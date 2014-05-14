#
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
##
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
import tornado.httpserver
import ssl
import os.path
import mplane.model
import mplane.sec
import mplane.utils
from datetime import datetime
import time

SLEEP_QUANTUM = 0.250
CAPABILITY_PATH_ELEM = "capability"

DEFAULT_LISTEN_PORT = 8888
DEFAULT_LISTEN_IP4 = '127.0.0.1'

class MPlaneHandler(tornado.web.RequestHandler):
    """
    Abstract tornado RequestHandler that allows a 
    handler to respond with an mPlane Message.

    """
    def _respond_message(self, msg):
        self.set_status(200)
        self.set_header("Content-Type", "application/x-mplane+json")
        self.write(mplane.model.unparse_json(msg))
        self.finish()

class DiscoveryHandler(MPlaneHandler):
    """
    Exposes the capabilities registered with a given scheduler. 
    URIs ending with "capability" will result in an HTML page 
    listing links to each capability. 

    """

    def initialize(self, scheduler):
        if scheduler.ac.security == True:
            for elem in self.request.get_ssl_certificate().get('subject'):
                if elem[0][0] == 'commonName':
                   self.user = elem[0][1]
        else:
            self.user = None
        self.scheduler = scheduler

    def get(self):
        # capabilities
        path = self.request.path.split("/")[1:]
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
        for key in self.scheduler.capability_keys():
            if self.scheduler.ac.check_azn(self.scheduler.capability_for_key(key)._label, self.user):
            	self.write("<a href='/capability/" + key + "'>" + key + "</a><br/>")
        self.write("</body></html>")
        self.finish()

    def _respond_capability(self, key):
        self._respond_message(self.scheduler.capability_for_key(key))

class MessagePostHandler(MPlaneHandler):
    """
    Receives mPlane messages POSTed from a client, and passes them to a 
    scheduler for processing. After waiting for a specified delay to see 
    if a Result is immediately available, returns a receipt for future
    redemption.

    """
    def initialize(self, scheduler, immediate_ms = 5000):
        if scheduler.ac.security == True:
            for elem in self.request.get_ssl_certificate().get('subject'):
                if elem[0][0] == 'commonName':
                   self.user = elem[0][1]
        else:
            self.user = None
        self.scheduler = scheduler
        self.immediate_ms = immediate_ms

    def get(self):
        # message
        self.set_status(200)
        self.set_header("Content-Type", "text/html")
        self.write("<html><head><title>mplane.httpsrv</title></head><body>")
        self.write("This is an mplane.httpsrv instance. POST mPlane messages to this URL to use.<br/>")
        self.write("<a href='/"+CAPABILITY_PATH_ELEM+"'>Capabilities</a> provided by this server:<br/>")
        for key in self.scheduler.capability_keys():
            if self.scheduler.ac.check_azn(self.scheduler.capability_for_key(key)._label, self.user):
                self.write("<br/><pre>")
                self.write(mplane.model.unparse_json(self.scheduler.capability_for_key(key)))
        self.write("</body></html>")
        self.finish()

    def post(self):
        # unwrap json message from body
        if (self.request.headers["Content-Type"] == "application/x-mplane+json"):
            msg = mplane.model.parse_json(self.request.body.decode("utf-8"))
        else:
            # FIXME how do we tell tornado we don't want to handle this?
            raise ValueError("I only know how to handle mPlane JSON messages via HTTP POST")

        # hand message to scheduler
        reply = self.scheduler.receive_message(self.user, msg)

        # wait for immediate delay
        if self.immediate_ms > 0 and \
           isinstance(msg, mplane.model.Specification) and \
           isinstance(reply, mplane.model.Receipt):
            job = self.scheduler.job_for_message(reply)
            wait_start = datetime.utcnow()
            while (datetime.utcnow() - wait_start).total_seconds() * 1000 < self.immediate_ms:
                time.sleep(SLEEP_QUANTUM)
                if job.failed() or job.finished():
                    reply = job.get_reply()
                    break

        # return reply
        self._respond_message(reply)

# FIXME build a class that wraps a scheduler and a runloop (and maybe a command line interpreter)

def runloop(scheduler, security, certfile, address=DEFAULT_LISTEN_IP4, port=DEFAULT_LISTEN_PORT):
    application = tornado.web.Application([
            (r"/", mplane.httpsrv.MessagePostHandler, {'scheduler': scheduler}),
            (r"/"+CAPABILITY_PATH_ELEM, mplane.httpsrv.DiscoveryHandler, {'scheduler': scheduler}),
            (r"/"+CAPABILITY_PATH_ELEM+"/.*", mplane.httpsrv.DiscoveryHandler, {'scheduler': scheduler})
        ])
    if security == True:
        cert = mplane.utils.normalize_path(mplane.utils.read_setting(certfile, "cert"))
        key = mplane.utils.normalize_path(mplane.utils.read_setting(certfile, "key"))
        ca = mplane.utils.normalize_path(mplane.utils.read_setting(certfile, "ca-chain"))
        mplane.utils.check_file(cert)
        mplane.utils.check_file(key)
        mplane.utils.check_file(ca)
        http_server = tornado.httpserver.HTTPServer(application, ssl_options=dict(certfile=cert, keyfile=key, cert_reqs=ssl.CERT_REQUIRED, ca_certs=ca))
    else:
        http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(port, address = address)
    tornado.ioloop.IOLoop.instance().start()
