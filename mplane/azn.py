#
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
##
# mPlane Protocol Reference Implementation
# Authorization context for mPlane components
#
# (c) 2014 mPlane Consortium (http://www.ict-mplane.eu)
#     Author: Stefano Pentassuglia <stefano.pentassuglia@ssbprogetti.it>
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

# FIXME grab most of this from sec.py, which then goes away.

import mplane.model

class AlwaysAuthorized(object):
	def check(self, cap, identity):
		return True

always_authorized = AlwaysAuthorized()

class Authorization(object):
	def __init__(self, config_file=None):
		pass

	def check(self, cap, identity):
		pass