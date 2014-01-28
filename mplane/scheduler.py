#
# mPlane Protocol Reference Implementation
# Component and Client Job Scheduling
#
# (c) 2013 mPlane Consortium (http://www.ict-mplane.eu)
#          Author: Brian Trammell <brian@trammell.ch>
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
Implements the dynamics of capabilities, specifications, and 
results within the mPlane reference component.

"""

class Service(object):
	"""
	A Service is a binding of some runnable code to an 
	mplane.model.Capability provided by a component.

	To use services with an mPlane scheduler, inherit from 
	mplane.scheduler.Service or one of its subclasses 
	and implement run().

	"""
	def __init__(self, capability):
		super(Service, self).__init__()
		self.capability = capability

	def run(self, spec):
		"""
		Run this service given a specification which matches the capability.
		This is called by the scheduler, and should be implemented by
		a concrete subclass of Service.

		"""
		raise NotImplementedError("Cannot instantiate an abstract Service")

class Job(object):
	"""
	A Job is a binding of some running code to an
	mPlane.model.Specification within a component. A Job can
	be thought of as a specific instance of a service presently
	running at a 

	"""
	def __init__(self, service, specification):
		super(Job, self).__init__()
		self.service = service
		self.specification = specification
		
		
		