#
# mPlane Protocol Reference Implementation
# Authorization APIs
#
# (c) 2013-2014 mPlane Consortium (http://www.ict-mplane.eu)
#               Author: Stefano Pentassuglia <stefano.pentassuglia@ssbprogetti.it>
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

import os
import os.path

class Authorization(object):

	def __init__(self, security):
    		self.security = security
    		if self.security == True:
    			self.ur = self.load_roles("users.conf")
    			self.cr = self.load_roles("caps.conf")
		
	def load_roles(self, filename):
         r = {}
         if os.path.isfile(os.path.join("/etc/mplane/", filename)):
            filepath = os.path.join("/etc/mplane/", filename)
         elif os.path.isfile(os.path.join(os.environ['HOME'], filename)):
            filepath = os.path.join(os.environ['HOME'], filename)
         elif ((os.getenv('MPLANE_CONF_DIR', default=None) is not None) and 
         (os.path.isfile(os.path.join(os.getenv('MPLANE_CONF_DIR', default=None), filename)))):
             filepath = os.path.join(os.getenv('MPLANE_CONF_DIR', default=None), filename)
         else:
            raise OSError("File " + filename + " not found. Retry setting $MPLANE_CONF_DIR")
            
         with open(filepath) as f:
             for line in f.readlines():
                 line = line.rstrip('\n')
                 user = line.split(': ')[0]
                 roles = set(line.split(': ')[1].split(', '))
                 r[user] = roles
         return r

	def check_azn(self, cap_name, user_name):
		""" Checks if the user is allowed to use a given capability """
		if self.security == True:
			if ((cap_name in self.cr) and (user_name in self.ur)): # Deny unless explicitly allowed in .conf files
				intersection = self.cr[cap_name] & self.ur[user_name]
				if len(intersection) > 0:
					print ("Capability " + str(cap_name) + " allowed for " + user_name + " as " + str(intersection))
					return True
			print ("Capability " + str(cap_name) + " denied for " + user_name)
			return False
		else:
			return True
