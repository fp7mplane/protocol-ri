
# mPlane Protocol Reference Implementation
# ICMP Ping component code
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
Implements ICMP ping (delay.twoway.icmp) for integration into 
the mPlane reference implementation.

"""

import re
import ipaddress
import threading
import subprocess
import collections
from datetime import datetime
import mplane.model
import mplane.scheduler

_pingline_re = re.compile("icmp_seq=(\d+)\s+ttl=(\d+)\s+time=([\d\.]+)\s+ms")

_ping4cmd = "ping"
_ping6cmd = "ping6"
_pingopts = ["-n"]
_pingopt_period = "-i"
_pingopt_count = "-c"

PingValue = collections.namedtuple("PingValue", ["time", "seq", "ttl", "usec"])

def _parse_ping_line(line):
	m = _pingline_re.search(line)
	if m is None:
		return None
	mg = m.groups()
	return PingValue(datetime.utcnow(), int(mg[0]), int(mg[1]), int(float(mg[2]) * 1000))

def _ping4_process(ipaddr, period, count):
	pass

def _ping6_process(ipaddr, period, count):
	pass

class PingService(mplane.scheduler.Service):

	def __init__(self, capability):
		# verify the capability is acceptable
		if not ((capability.has_parameter("source.ip4") or 
			     capability.has_parameter("source.ip6")) and
		        (capability.has_parameter("destination.ip4") or 
			     capability.has_parameter("destination.ip6")) and
		        capability.has_parameter("period.s") and
		        (capability.has_result_column("delay.twoway.icmp.us") or
		         capability.has_result_column("delay.twoway.icmp.us.min") or
		         capability.has_result_column("delay.twoway.icmp.us.mean") or		    	
		         capability.has_result_column("delay.twoway.icmp.us.max"))):
			raise ValueError("capability not acceptable")

		super(PingService, self).__init__(capability)

	def run(self, specification, check_interrupt):
		# verify specification and unpack parameters

		# FIXME work pointer

		# build a ping command line
		ping_argv = []
		if (self.ipaddr.version == 4):
			ping_argv.append(_ping4cmd)
		elif (self.ipaddr.version == 6):
			ping_argv.append(_ping6cmd)
		else:
			raise ValueError("Unsupported IP version " + str(self.ipaddr.version))

		ping_argv += _pingopts
		ping_argv.append(_pingopt_period)
		ping_argv.append(str(self.period))
		ping_argv.append(_pingopt_count)
		ping_argv.append(str(self.count))
		ping_argv.append(str(self.ipaddr))

		# start the ping process
		print("running " + " ".join(ping_argv))

		self.reset()
		with subprocess.Popen(ping_argv, stdout=subprocess.PIPE) as ping_proc:
			for line in ping_proc.stdout:
				line = line.decode("utf-8")
				if self.interrupted:
					return
				result = parse_ping_line(line)
				if result is not None:
					print("got %u usec at %s" % (result.usec, str(result.time)))
					self.results.append(result)

class AsyncPing(threading.Thread):
	"""A thread which will ping count times every period seconds"""


	def interrupt(self):
		self.interrupted = True

	def reset(self):
		self.interrupted = False
		self.results = []
		self.result_min = None
		self.result_mean = None
		self.result_median = None
		self.result_max = None

	def run(self):
		# build a ping command line
		ping_argv = []
		if (self.ipaddr.version == 4):
			ping_argv.append(_ping4cmd)
		elif (self.ipaddr.version == 6):
			ping_argv.append(_ping6cmd)
		else:
			raise ValueError("Unsupported IP version " + str(self.ipaddr.version))

		ping_argv += _pingopts
		ping_argv.append(_pingopt_period)
		ping_argv.append(str(self.period))
		ping_argv.append(_pingopt_count)
		ping_argv.append(str(self.count))
		ping_argv.append(str(self.ipaddr))

		# start the ping process
		print("running " + " ".join(ping_argv))

		self.reset()
		with subprocess.Popen(ping_argv, stdout=subprocess.PIPE) as ping_proc:
			for line in ping_proc.stdout:
				line = line.decode("utf-8")
				if self.interrupted:
					return
				result = parse_ping_line(line)
				if result is not None:
					print("got %u usec at %s" % (result.usec, str(result.time)))
					self.results.append(result)

	def min_delay(self):
		if self.result_min is None:
			self.result_min = min(map(lambda x: x.usec, self.results))
		return self.result_min

	def mean_delay(self):
		if self.result_mean is None:
			self.result_mean = sum(map(lambda x: x.usec, self.results)) / len(self.results)
		return self.result_mean

	def median_delay(self):
		if self.result_median is None:
			self.result_median = sorted(map(lambda x: x.usec, self.results))[int(len(self.results) / 2)]
		return self.result_median

	def max_delay(self):
		if self.result_max is None:
			self.result_max = max(map(lambda x: x.usec, self.results))
		return self.result_max

	def delay_count(self):
		return len(self.results)

	def start_time(self):
		return self.results[0].time

	def end_time(self):
		return self.results[-1].time

