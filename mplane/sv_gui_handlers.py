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

import json
import tornado
import os

CONFIGFILE = "guiconf.json"
DIRECTORY_USERSETTINGS = "usersettings"

GUI_LISTCAPABILITIES_PATH = "gui/list/capabilites"
GUI_RUNCAPABILITY_PATH = "gui/run/capability"

GUI_LISTSPECIFICATIONS_PATH = "gui/list/specifications"
GUI_LISTRECEIPT_PATH = "gui/list/receipts"

GUI_LISTRESULTS_PATH = "gui/list/results"
GUI_GETRESULT_PATH = "gui/get/result"

GUI_LOGIN_PATH = "gui/login"
GUI_USERSETTINGS_PATH = "gui/settings"
GUI_STATIC_PATH = "gui/static"

class LoginHandler(tornado.web.RequestHandler):
    def initialize(self, supervisor):
        self._supervisor = supervisor

    def get(self, repeat):
        self.write('<html><body>')
        if repeat:
            self.write('Login failed. Try again!<br /><br />')

        self.write('<form action="/gui/login" method="post">'
                   'User: <input type="text" name="userid"><br />'
                   'Password: <input type="password" name="password"><br />'
                   '<input type="submit" value="Sign in">'
                   '</form></body></html>')

    def post(self):
        configfile = open(CONFIGFILE, "r")
        guiconfig = json.load( configfile )
        configfile.close()
        userTry = self.get_body_argument("userid", strip=True)
        if userTry in guiconfig['users'].keys():
            print("OK, userID found: " + userTry )
            self.set_secure_cookie("user", userTry)
            self.redirect( "/gui/static/index.html" )
        else:
            print("Auth error, user is not found: " + self.get_argument("userid"))
            self.get(repeat=True) 


class UserSettingsHandler(tornado.web.RequestHandler):
    """
    """
    def initialize(self, supervisor):
        self._supervisor = supervisor

    def get(self):
        user = self.get_secure_cookie("user").decode('utf-8')
        if user is None:
            self.redirect("/gui/login")
        else:
            self.set_status(200)
            self.set_header("Content-Type", "text/json")
            f = open(DIRECTORY_USERSETTINGS + os.sep + user, "r")
            self.write( f.read() )
            f.close()

    def post(self):
        user = self.get_secure_cookie("user").decode('utf-8')
        if user is None:
            self.redirect("/gui/login")
        else:            
            f = open(DIRECTORY_USERSETTINGS + os.sep + user, "w")
            f.write( self.request.body.decode("utf-8") )
            self.set_status(200)
            self.set_header("Content-Type", "text/json")
            self.write("{}\n")
            f.close()

class ListCapabilitiesHandler(tornado.web.RequestHandler):
    """
    """
    def initialize(self, supervisor):
        self._supervisor = supervisor

    def get(self):
        user = self.get_secure_cookie("user").decode('utf-8')
        if user is None:
            self.redirect("/gui/login")
            return
        
        print( "Request URI: " + self.request.uri );
        self.set_status(204, "Not yet implemented");
        self.set_header("Content-Type", "text/json")

    def post(self):
        self.set_status(405, GUI_LISTCAPABILITIES_PATH + " is a read-only GET function")

class ListResultsHandler(tornado.web.RequestHandler):
    """
    """
    def initialize(self, supervisor):
        self._supervisor = supervisor

    def get(self):
        user = self.get_secure_cookie("user").decode('utf-8')
        if user is None:
            self.redirect("/gui/login")
            return
        
        print( "Request URI: " + self.request.uri );
        self.set_status(204, "Not yet implemented");
        self.set_header("Content-Type", "text/json")

    def post(self):
        self.set_status(405, GUI_LISTCAPABILITIES_PATH + " is a read-only GET function")

class ListSpecificationsHandler(tornado.web.RequestHandler):
    """
    """
    def initialize(self, supervisor):
        self._supervisor = supervisor

    def get(self):
        user = self.get_secure_cookie("user").decode('utf-8')
        if user is None:
            self.redirect("/gui/login")
            return
        
        print( "Request URI: " + self.request.uri );
        self.set_status(204, "Not yet implemented");
        self.set_header("Content-Type", "text/json")

    def post(self):
        self.set_status(405, GUI_LISTCAPABILITIES_PATH + " is a read-only GET function")

class ListReceiptsHandler(tornado.web.RequestHandler):
    """
    """
    def initialize(self, supervisor):
        self._supervisor = supervisor

    def get(self):
        user = self.get_secure_cookie("user").decode('utf-8')
        if user is None:
            self.redirect("/gui/login")
            return
        
        print( "Request URI: " + self.request.uri );
        self.set_status(204, "Not yet implemented");
        self.set_header("Content-Type", "text/json")

    def post(self):
        self.set_status(405, GUI_LISTCAPABILITIES_PATH + " is a read-only GET function")

class GetResultHandler(tornado.web.RequestHandler):
    """
    """
    def initialize(self, supervisor):
        self._supervisor = supervisor

    def get(self):
        user = self.get_secure_cookie("user").decode('utf-8')
        if user is None:
            self.redirect("/gui/login")
            return
        
        print( "Request URI: " + self.request.uri );
        self.set_status(204, "Not yet implemented");
        self.set_header("Content-Type", "text/json")

    def post(self):
        self.set_status(405, GUI_LISTCAPABILITIES_PATH + " is a read-only GET function")
        
class RunCapabilityHandler(tornado.web.RequestHandler):
    """
    """
    def initialize(self, supervisor):
        self._supervisor = supervisor

    def get(self):
        user = self.get_secure_cookie("user").decode('utf-8')
        if user is None:
            self.redirect("/gui/login")
            return
        
        print( "Request URI: " + self.request.uri );
        self.set_status(204, "Not yet implemented");
        self.set_header("Content-Type", "text/json")

    def post(self):
        self.set_status(405, GUI_LISTCAPABILITIES_PATH + " is a read-only GET function")
