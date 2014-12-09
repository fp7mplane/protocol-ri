# mPlane Protocol Reference Implementation
# Supervisor HTTP handlers
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

import tornado.web
import mplane.model
import mplane.utils
import copy
import json
from collections import OrderedDict

REGISTRATION_PATH = "register/capability"
SPECIFICATION_PATH = "show/specification"
RESULT_PATH = "register/result"
S_CAPABILITY_PATH = "show/capability"
S_SPECIFICATION_PATH = "register/specification"
S_RESULT_PATH = "show/result"

"""
Set of HTTP handlers used by the supervisor to communicate 
with the components or with the client

"""

def get_dn(supervisor, request):
    """
    Extracts the DN from the request object. 
    If SSL is disabled, returns a dummy DN
    
    """
    if supervisor._sec == True:
        dn = ""
        for elem in request.get_ssl_certificate().get('subject'):
            if dn == "":
                dn = dn + str(elem[0][1])
            else: 
                dn = dn + "." + str(elem[0][1])
    else:
        dn = "org.mplane.Test PKI.Test Clients.mPlane-Client"
    return dn
    
class MPlaneHandler(tornado.web.RequestHandler):
    """
    Abstract tornado RequestHandler that allows a 
    handler to respond with an mPlane Message.

    """
    
    def _respond_message(self, msg):
        """
        Returns an HTTP response containing a JSON message
    
        """
        self.set_status(200)
        self.set_header("Content-Type", "application/x-mplane+json")
        self.write(mplane.model.unparse_json(msg))
        self.finish()
    
    def _respond_plain_text(self, code, text = None):
        """
        Returns an HTTP response containing a plain text message
        
        """
        self.set_status(code)
        if text is not None:
            self.set_header("Content-Type", "text/plain")
            self.write(text)
        self.finish()
    
    def _respond_json_text(self, code, text = None):
        """
        Returns an HTTP response containing a plain text message
        
        """
        self.set_status(code)
        if text is not None:
            self.set_header("Content-Type", "application/x-mplane+json")
            self.write(text)
        self.finish()
                
class RegistrationHandler(MPlaneHandler):
    """
    Handles the probes that want to register to this supervisor
    Each capability is registered indipendently

    """
    def initialize(self, supervisor):
        self._supervisor = supervisor
        self.dn = get_dn(self._supervisor, self.request)
        self._supervisor._dn_to_ip[self.dn] = self.request.remote_ip
        

    def post(self):
        
        # check the class of the certificate (Client, Component, Supervisor).
        # this function can only be used by components
        if self.dn.find("Components") == -1:
            self._respond_plain_text(401, "Not Authorized. Only Components can use this function")
            return
        
        # unwrap json message from body
        if (self.request.headers["Content-Type"] == "application/x-mplane+json"):
            new_caps = mplane.utils.split_stmt_list(self.request.body.decode("utf-8"))
        else:
            self._respond_plain_text(400, "Invalid format")
            return
        
        # register capabilities
        response = ""
        for new_cap in new_caps:
            if isinstance(new_cap, mplane.model.Capability):
                found = False
                if new_cap.get_label() in self._supervisor._label_to_dn:
                    for dn in self._supervisor._label_to_dn[new_cap.get_label()]:
                        if dn == self.dn:
                            mplane.utils.print_then_prompt(self.dn + " tried to register an already registered Capability: " + new_cap.get_label())
                            response = response + "\"" + new_cap.get_label() + "\":{\"registered\":\"no\", \"reason\":\"Capability already registered\"},"
                            found = True
                if found is False:
                    self._supervisor.register(new_cap, self.dn)
                    mplane.utils.print_then_prompt("Capability " + new_cap.get_label() + " received from " + self.dn)
                    response = response + "\"" + new_cap.get_label() + "\":{\"registered\":\"ok\"},"
            else:
                response = response + "\"" + new_cap.get_label() + "\":{\"registered\":\"no\", \"reason\":\"Not a capability\"},"
        response = "{" + response[:-1].replace("\n", "") + "}"
        
        # reply to the component
        self._respond_json_text(200, response)
        return
    
class SpecificationHandler(MPlaneHandler):
    """
    Exposes the specifications, that will be periodically pulled by the
    components

    """
    def initialize(self, supervisor):
        self._supervisor = supervisor
        self.dn = get_dn(self._supervisor, self.request)
        self._supervisor._dn_to_ip[self.dn] = self.request.remote_ip

    def get(self):
        
        # check the class of the certificate (Client, Component, Supervisor).
        # this function can only be used by components
        if self.dn.find("Components") == -1:
            self._respond_plain_text(401, "Not Authorized. Only Components can use this function")
            return
        
        # check if the component is registered or not
        if self.dn not in self._supervisor._registered_dn:
            self._respond_plain_text(428)
            
        specs = self._supervisor._specifications.pop(self.dn, [])
        self.set_status(200)
        self.set_header("Content-Type", "application/x-mplane+json")
        msg = ""
        for spec in specs:
                msg = msg + mplane.model.unparse_json(spec) + ","
                mplane.utils.add_value_to(self._supervisor._receipts, self.dn, mplane.model.Receipt(specification=spec))
                mplane.utils.print_then_prompt("Specification " + spec.get_label() + " successfully pulled by " + self.dn)
        msg = "[" + msg[:-1].replace("\n","") + "]"
        self.write(msg)
        self.finish()
        
class ResultHandler(MPlaneHandler):
    """
    Receives results of specifications

    """

    def initialize(self, supervisor):
        self._supervisor = supervisor
        self.dn = get_dn(self._supervisor, self.request)
        self._supervisor._dn_to_ip[self.dn] = self.request.remote_ip

    def post(self):
        
        # check the class of the certificate (Client, Component, Supervisor).
        # this function can only be used by components
        if self.dn.find("Components") == -1:
            self._respond_plain_text(401, "Not Authorized. Only Components can use this function")
            return
        
        # unwrap json message from body
        if (self.request.headers["Content-Type"] == "application/x-mplane+json"):
            msg = mplane.model.parse_json(self.request.body.decode("utf-8"))
        else:
            self._respond_plain_text(400, "Invalid format")
            return
            
        if isinstance(msg, mplane.model.Result):
            
            # hand message to supervisor
            if self._supervisor.add_result(msg, self.dn):
                mplane.utils.print_then_prompt("Result received by " + self.dn)
                self._respond_plain_text(200)
                return
            else:
                self._respond_plain_text(403, "Unexpected result")
                return
        elif isinstance(msg, mplane.model.Exception):
            
            # hand message to supervisor
            self._supervisor._handle_exception(msg)
            self._respond_plain_text(200)
            mplane.utils.print_then_prompt("Exception Received! (instead of Result)")
            return
        else:
            self._respond_plain_text(400, "Not a result (or exception)")
            return

class S_CapabilityHandler(MPlaneHandler):
    """
    Exposes to a client the capabilities registered to this supervisor. 
    
    """

    def initialize(self, supervisor):
        self._supervisor = supervisor
        self.dn = get_dn(self._supervisor, self.request)

    def get(self):
        """
        Returns a list of all the available capabilities 
        (filtered according to the privileges of the client)
        in the form of a JSON array of Capabilities
        
        """
        
        # check the class of the certificate (Client, Component, Supervisor).
        # this function can only be used by clients
        if self.dn.find("Clients") == -1:
            self._respond_plain_text(401, "Not Authorized. Only Clients can use this function")
            return
        
        # set HTML headers
        self.set_status(200)
        self.set_header("Content-Type", "application/x-mplane+json")
        msg = ""
        
        # list capabilities
        for key in self._supervisor._capabilities:
            found = False
            for cap in self._supervisor._capabilities[key]:
                cap_id = cap.get_label() + ", " + key
                if self._supervisor.ac.check_azn(cap_id, self.dn):
                    if found == False:
                        msg = msg + "\"" + key + "\":["
                        found = True
                    msg = msg + mplane.model.unparse_json(cap) + ","
            if found == True:
                msg = msg[:-1].replace("\n","") + "],"
        
        msg = "{" + msg[:-1].replace("\n","") + "}"
        self.write(msg)
        self.finish()

class S_SpecificationHandler(MPlaneHandler):
    """
    Receives specifications from a client. If the client is
    authorized to run the spec, this supervisor forwards it 
    to the probe.

    """

    def initialize(self, supervisor):
        self._supervisor = supervisor
        self.dn = get_dn(self._supervisor, self.request)
    
    def post(self):
        
        # check the class of the certificate (Client, Component, Supervisor).
        # this function can only be used by clients
        if self.dn.find("Clients") == -1:
            self._respond_plain_text(401, "Not Authorized. Only Clients can use this function")
            return
            
        # unwrap json message from body
        if (self.request.headers["Content-Type"] == "application/x-mplane+json"):
            j_spec = json.loads(self.request.body.decode("utf-8"))
            
            # get DN and specification (only one, then this for cycle breaks)
            for key in j_spec:
                probe_dn = key
                spec = mplane.model.parse_json(json.dumps(j_spec[probe_dn]))
                
                if isinstance(spec, mplane.model.Specification):
                    receipt = mplane.model.Receipt(specification=spec)
                    
                    if spec.get_label() not in self._supervisor._label_to_dn:
                        self._respond_plain_text(403, "This measure doesn't exist")
                        return
                    if probe_dn not in self._supervisor._dn_to_ip:
                        self._respond_plain_text(503, "Specification is unavailable. The component for the requested measure was not found")
                        return
                        
                    # enqueue the specification
                    if not self._supervisor.add_spec(spec, probe_dn):
                        self._respond_plain_text(503, "Specification is temporarily unavailable. Try again later")
                        return
                                                
                    # return the receipt to the client        
                    self._respond_message(receipt)
                    return
                else:
                    self._respond_plain_text(400, "Invalid format")
                    return

class S_ResultHandler(MPlaneHandler):
    """
    Receives receipts from a client. If the corresponding result
    is ready, this supervisor sends it to the probe.

    """

    def initialize(self, supervisor):
        self._supervisor = supervisor
        self.dn = get_dn(self._supervisor, self.request)
    
    def post(self):
        
        # check the class of the certificate (Client, Component, Supervisor).
        # this function can only be used by clients
        if self.dn.find("Clients") == -1:
            self._respond_plain_text(401, "Not Authorized. Only Clients can use this function")
            return
            
        # unwrap json message from body
        if (self.request.headers["Content-Type"] == "application/x-mplane+json"):
            rec = mplane.model.parse_json(self.request.body.decode("utf-8"))
            if isinstance(rec, mplane.model.Redemption):    
                # check if result is ready. if so, return it to client
                for dn in self._supervisor._results:
                    for r in self._supervisor._results[dn]:
                        if str(r.get_token()) == str(rec.get_token()):
                            self._respond_message(r)
                            self._supervisor._results[dn].remove(r)
                            return
                meas = self._supervisor.measurements()
                
                # if result is not ready, return the receipt
                for dn in meas:
                    for r in meas[dn]:
                        if str(r.get_token()) == str(rec.get_token()):
                            self._respond_message(r)
                            return
                      
                # if there is no measurement and no result corresponding to the redemption, it is unexpected
                self._respond_plain_text(403, "Unexpected Redemption")
                return
            else:
                self._respond_plain_text(400, "Invalid format")   
                return