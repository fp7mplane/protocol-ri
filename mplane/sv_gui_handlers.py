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

import tornado

GUI_LISTCAPABILITIES_PATH = "gui/list/capabilites"

GUI_LISTSPECIFICATIONS_PATH = "gui/list/specifications"
GUI_LISTRECEIPT_PATH = "gui/list/receipts"

GUI_LISTRESULTS_PATH = "gui/list/results"
GUI_GETRESULT_PATH = "gui/get/result"

GUI_LOGIN_PATH = "gui/login"
GUI_USERSETTINGS_PATH = "gui/user"
GUI_STATIC_PATH = "gui/static"

class LoginHandler(tornado.web.RequestHandler):
    def initialize(self, supervisor):
        self._supervisor = supervisor

    def get(self):
        self.write('<html><body><form action="/gui/login" method="post">'
                   'Name: <input type="text" name="name">'
                   '<input type="submit" value="Sign in">'
                   '</form></body></html>')

    def post(self):
        self.set_secure_cookie("user", self.get_argument("name"))
        self.redirect( "/" )

