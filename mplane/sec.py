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

import os.path
import mplane.model

class Authorization(object):

	def __init__(self, security):
		self.ur = self.load_roles("conf/users.conf")
		self.cr = self.load_roles("conf/caps.conf")
		self.security = security
		
	def load_roles(self, path):
		r = {}
		with open(os.path.join(os.path.dirname(__file__), path),'r') as f:
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
