# mPlane Protocol Reference Implementation
# Supervisor HTTP handlers to server GUI
#
# (c) 2013-2014 mPlane Consortium (http://www.ict-mplane.eu)
#               Author: Attila Bokor
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

"""
   This module contains HTTP request handlers for the GUI.
   It always communicates in JSONs. Response "{}" means OK, for modifications,
   otherwise response {ERROR: 'some complaints'} should be sent to the client.
   
   If there is no user signed in, the answer should be a HTTP redirect to all the request.  
"""

import copy
import json
import tornado
import os
import mplane.model
import datetime
from _operator import contains

CONFIGFILE = "guiconf.json"
DIRECTORY_USERSETTINGS = "usersettings"

GUI_LISTCAPABILITIES_PATH = "gui/list/capabilities"
GUI_RUNCAPABILITY_PATH = "gui/run/capability"

GUI_LISTPENDINGS_PATH = "gui/list/pendings"

GUI_LISTRESULTS_PATH = "gui/list/results"
GUI_GETRESULT_PATH = "gui/get/result"

GUI_LOGIN_PATH = "gui/login"
GUI_USERSETTINGS_PATH = "gui/settings"
GUI_STATIC_PATH = "gui/static"

class ForwardHandler(tornado.web.RequestHandler):
    """
    This handler implements a simple static HTTP redirect.
    """
    def initialize(self, forwardUrl):
        self._forwardUrl = forwardUrl

    def get(self):
        self.redirect( self._forwardUrl )

    def post(self):
        self.redirect( self._forwardUrl )

class LoginHandler(tornado.web.RequestHandler):
    """
    Implements authentication.
    
    GET: redirect to the login page.
    
    POST: checks the posted user credentials, and set a secure cookie named "user", if credentials are valid. Required content type is application/x-www-form-urlencoded,
    username and password parameters are required. Response code is always 200. Body is {} for successful login, or {ERROR: "some complaints"} in all other cases.     
    """
    def initialize(self, supervisor):
        self._supervisor = supervisor

    def get(self):
        self.redirect("/gui/static/login.html")

    def post(self):
        configfile = open(CONFIGFILE, "r")
        guiconfig = json.load( configfile )
        configfile.close()
        userTry = self.get_body_argument("username", strip=True)
        pwdTry = self.get_body_argument("password", strip=True)

        if userTry in guiconfig['users'].keys() and guiconfig['users'][userTry]['password'] == pwdTry:            
            self.set_secure_cookie("user", userTry, 1)
            self.set_status(200);
            self.set_header("Content-Type", "text/json")
            self.write("{}")
        else:
            self.clear_cookie("user")
            self.set_status(200);
            self.set_header("Content-Type", "text/json")
            self.write("{ERROR:\"Authentication failed for user " + userTry + "\"}")

        self.finish()

class UserSettingsHandler(tornado.web.RequestHandler):
    """
    Stores and gives back user-specific settings. Signed-in user defined by secure cookie named "user".
    Content-type is always text/json.
    
    GET: answers the settings JSON of the current user (initially it's "{}").

    POST: stores the posted settings JSON for the current user (it must be a valid JSON).
    """
    def initialize(self, supervisor):
        self._supervisor = supervisor

    def get(self):
        user = self.get_secure_cookie("user")
        if user is None:
            self.redirect("/gui/static/login.html")
        else:
            try:
                self.set_status(200)
                self.set_header("Content-Type", "text/json")
                f = open(DIRECTORY_USERSETTINGS + os.sep + user.decode('utf-8'), "r")
                self.write( f.read() )
                f.close()
            except Exception as e:
                self.write( "{ERROR:\"" + str(e) + "\"}" )
            self.finish()

    def post(self):
        user = self.get_secure_cookie("user")
        if user is None:
            self.redirect("/gui/static/login.html")
        else:
            try:
                f = open(DIRECTORY_USERSETTINGS + os.sep + user.decode('utf-8'), "w")
                f.write( self.request.body.decode("utf-8") )
                self.set_status(200)
                self.set_header("Content-Type", "text/json")
                self.write("{}\n")
                f.close()
            except Exception as e:
                self.write( "{ERROR:\"" + str(e) + "\"}" )
            self.finish()
            

class ListCapabilitiesHandler(tornado.web.RequestHandler):
    """
    Lists the capabilites, registered in the Supervisor. Response is in mplane JSON format.

    GET: capabilites can be filtered by GET parameters named label, and names of parameters of the capability. Response is in mplane JSON format.

    POST is not supported.
    """
    def initialize(self, supervisor):
        self._supervisor = supervisor

    def get(self):
        if self.get_secure_cookie("user") is None:
            self.redirect("/gui/static/login.html")
            return
        
        self.set_status(200);
        self.set_header("Content-Type", "text/json")
        try:
            msg = ""
            for key in self._supervisor._capabilities:
                found = False
                for cap in self._supervisor._capabilities[key]:
                    keep = True
                    print( "checking " + cap.get_label() )
                    for paramname in cap.parameter_names():
                        print( "    param: " + paramname )
                        print( "      constraint: " + str( cap._params[paramname]._constraint ) + " type: "+ str( type(cap._params[paramname]._constraint)))
    
                        paramfilter = self.get_argument(paramname, default=None)
                        if paramfilter is not None:
                            print( "      filter: " + paramfilter )
                            constr = cap._params[paramname]._constraint                        
                            if ( (isinstance(constr, mplane.model.SetConstraint) and str(constr).find(paramfilter) < 0)
                                    or (not isinstance(constr, mplane.model.SetConstraint) and not constr.met_by(paramfilter)) ):
                                keep = False
                                print( "      SKIPPED" )
    
                    if keep:
                        cap_id = cap.get_label() + ", " + key
                        if found == False:
                            msg = msg + "\"" + key + "\":["
                            found = True
                        msg = msg + mplane.model.unparse_json(cap) + ","
                    
                if found == True:
                    msg = msg[:-1].replace("\n","") + "],"
            
            msg = "{" + msg[:-1].replace("\n","") + "}"
            self.write(msg)
            self.finish()
        except Exception as e:
            self.write( "{ERROR:\"" + str(e) + "\"}" )

    def post(self):
        self.set_status(405, GUI_LISTCAPABILITIES_PATH + " is a read-only GET function")

class ListResultsHandler(tornado.web.RequestHandler):
    """
    Lists the results from Supervisor.
    
    GET: lists results from the supervisor in a JSON array, format is as follows:
      [ { result:'measure', label:'CAPABILITY_LABEL',  when:'WHEN_OF_RESULT', token:'TOKEN_OF_RESULT',
          parameters: { specificationParam1:"value1", specificationParam2:"value2", ... }, ... ]
      Filtering can be done by GET parameters called label, and names of parameters of the capability.

    POST: not supported
    """
    def initialize(self, supervisor):
        self._supervisor = supervisor

    def get(self):
        if self.get_secure_cookie("user") is None:
            self.redirect("/gui/static/login.html")
            return

        try:
            self.set_status(200);
            self.set_header("Content-Type", "text/json")
    
            msg = ""
            for key in self._supervisor._results:
                found = False
                dnMsg = ""
                for res in self._supervisor._results[key]:
                    keep = True
                    print( "checking " + res.get_label() )
                    for paramname in res.parameter_names():
                        print( "    param: " + paramname )
                        print( "      constraint: " + str( res._params[paramname]._constraint ) + " type: "+ str( type(res._params[paramname]._constraint)))
    
                        paramfilter = self.get_argument(paramname, default=None)
                        if paramfilter is not None:
                            print( "      filter: " + paramfilter )
                            # TODO implement filtering                        
    
                    if keep:
    #                    res_id = res.get_label() + ", " + key
                        if found == False:
                            dnMsg = dnMsg + "\"" + key + "\":["
                            found = True
    
                        paramStr = ""
                        for paramname in res.parameter_names():
                            paramStr = paramStr + "'" + paramname + "': '" + str(res.get_parameter_value(paramname)) + "',"
    
                        dnMsg = dnMsg + "{ result:'measure', label:'" + res.get_label() + "',  when:'" + str(res.when()) + "', token:'" + res.get_token() + "', parameters: {" + paramStr[:-1] + "} },"
    
                if found == True:
                    msg = msg + dnMsg[:-1] + "],"
            
            msg = "{" + msg[:-1].replace("\n","") + "}"
            
            self.set_status(200);
            self.set_header("Content-Type", "text/json")
            self.write(msg)
            self.finish()
        except Exception as e:
            self.write( "{ERROR:\"" + str(e) + "\"}" )

    def post(self):
        self.set_status(405, GUI_LISTCAPABILITIES_PATH + " is a read-only GET function")

class ListPendingsHandler(tornado.web.RequestHandler):
    """
    Lists all the pending measurement (specifications and receipts) from supervisor.
    
    GET compose mplane json representations of pending specifications and receipts, in the following format:
        { DN1: [ receipt1, receipt2 ], DN2: [ specification1, receipt3, ... ], ... }
    
    POST is not supported.
    """
    def initialize(self, supervisor):
        self._supervisor = supervisor

    def get(self):
        if self.get_secure_cookie("user") is None:
            self.redirect("/gui/static/login.html")
            return

        self.set_status(200)
        self.set_header("Content-Type", "application/x-mplane+json")
        msg = ""

        try:
            for dn in dict( self._supervisor._specifications, **self._supervisor._receipts ).keys():
                dnMsg = ""            
                for spec in self._supervisor._specifications.get(dn, []):
                    dnMsg = dnMsg + mplane.model.unparse_json(spec) + ","
                for receipt in self._supervisor._receipts.get(dn, []):
                    dnMsg = dnMsg + mplane.model.unparse_json(receipt) + ","
                    
                if len(dnMsg) > 0:
                    msg = msg + '"' + dn + '": [' + dnMsg[:-1] + "],"
                        
            msg = "{" + msg[:-1].replace("\n","") + "}"
            self.write(msg)
        except Exception as e:
            self.write( "{ERROR:\"" + str(e) + "\"}" )

        self.finish()

    def post(self):
        self.set_status(405, GUI_LISTCAPABILITIES_PATH + " is a read-only GET function")


class GetResultHandler(tornado.web.RequestHandler):
    """
    GET: Get result for specified token.
    
    POST: Get results for a filter like a specification.
        Posted JSON is like
            { capability:ping-detail-ip4, parameters:{"source.ip4":"192.168.96.1", "destination.ip4":"217.20.130.99" },
            "resultName":"delay.twoway.icmp.us", from: 1421539200000, to: 1421625600000 }

            - timestamps are in ms
            - capability is the label of the capability
            - no component DN is defined, results of different components can be merged
            - resultName: only one result column is required -> one line will be drawn from the response.
          
        The response is like as follows:

        { "result":"measure", "version":0, "registry": "http://ict-mplane.eu/registry/core", "label": ping-detail-ip4, "when": "2015-01-18 17:25:50.785761 ... 2015-01-18 17:28:00.785367",
            "parameters":{"source.ip4":"192.168.96.1", "destination.ip4":"217.20.130.99" }, "results": ["time", "delay.twoway.icmp.us"],
            "resultvalues": [["2015-01-18 17:25:50.785761", 20], ["2015-01-18 17:25:51.785761", 37], ["2015-01-18 17:28:00.785761", 31], ...] }

            - when: shows times between results are found
            - resultvalues: it has always 2 columns, first is time, second is requested by client in  "resultName"
    """
    def initialize(self, supervisor):
        self._supervisor = supervisor

    def get(self):
        if self.get_secure_cookie("user") is None:
            self.redirect("/gui/static/login.html")
            return
        try:
            self.set_status(200);
            self.set_header("Content-Type", "text/json")
            token = self.get_argument("token")

            for dn in self._supervisor._results.keys():
                for res in self._supervisor._results[dn]:
                    if res.get_token() == token:
                        self.write( mplane.model.unparse_json(res) )
                        self.finish()
                        return
            
            self.write("{ERROR: \"result for token " + token + " is not found\"}")
        except Exception as e:
            self.write( "{ERROR:\"" + str(e) + "\"}" )

        self.finish()

    def post(self):
        queryJson = json.loads( self.request.body.decode("utf-8") )
        fromTS = datetime.datetime.fromtimestamp( queryJson["from"] / 1000 )
        toTS = datetime.datetime.fromtimestamp( queryJson["to"] / 1000 )        
        print( 'query time: ' + str(fromTS) + " - " + str(toTS))
        
        selectedResults = []
        for dn in self._supervisor._results.keys():
            for res in self._supervisor._results[dn]:
                skip = res.get_label() != queryJson["capability"]
                for paramname in res.parameter_names():
                    if str(res.get_parameter_value(paramname)) != queryJson["parameters"][paramname]:
                        skip = True
                (resstart,resend) = res.when().datetimes()
                print( '   result time: ' + str(resstart) + " - " + str(resend) + ": " + str(resend < fromTS or resstart > toTS))

                skip = skip or resend < fromTS or resstart > toTS
                if not skip:
                    selectedResults.append(res)
        
        if len(selectedResults) == 0:
            self.write("{ERROR:\"No result was found\"}");
            self.finish()
            return;
        
        resultvalues = []
        response = { "result":"measure", "version":0, "registry": "http://ict-mplane.eu/registry/core", 
            "label": queryJson["capability"], "when": str(mplane.model.When(a=fromTS, b=toTS)), "parameters": queryJson["parameters"],
            "results": ["time", queryJson["result"]], "resultvalues": resultvalues }
                
        for res in selectedResults:
            resultvalues.extend( res._result_rows() )

        sorted( resultvalues, key=lambda resultrow: resultrow[0] )

        self.write( json.dumps(response) )
        self.finish()

class RunCapabilityHandler(tornado.web.RequestHandler):
    """
      It runs a capability.    
      
      POST: URI should be gui/run/capability?DN=Probe.Distinguished.Name 
      Posted data is a fulfilled capability, not a specification. Fulfilled means field when has a concrete value, and every parameter has a value as well.
    """

    def initialize(self, supervisor):
        self._supervisor = supervisor

    def get(self):
        self.set_status(405, GUI_LISTCAPABILITIES_PATH + " supports POST only")
        self.finish();

    def post(self):
        try:
            dn = self.get_query_argument("DN", strip=True)
            posted = self.request.body.decode("utf-8")
            
            filledCapability = mplane.model.parse_json( posted )           
            spec = mplane.model.Specification( capability=filledCapability )
            
            # Capability posted by GUI contains parameter values as constraints allowing single value only
            for paramname in spec.parameter_names():
                spec._params[paramname].set_single_value()
            
            if self._supervisor.add_spec( spec, dn ):
                self.write( "{}" )
            else:
                self.write( "{ERROR: \"Specification can't be queued.\"}" )
        except Exception as e:
            self.write( "{ERROR:\"" + str(e) + "\"}" )
        self.finish()

