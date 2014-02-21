#
# mPlane Protocol Reference Implementation
# Time and Schedule Specification
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

"""
Temporal scoping -- when a measurement can be, should be, or was run -- is handled
by two sections of mPlane messages.

The "when" section defines when a capability, specification, or result is
valid. The "schedule" section defines, for specifications, when a specified
measurement should be repeated.

This file holds the classes implementing this during development and experimentation;
this code will be integrated into model.py

"""

_iso8601_re = re.compile('(\d+-\d+-\d+)(\s+\d+:\d+(:\d+)?)?(\.\d+)?')
_iso8601_fmt = { 'us': '%Y-%m-%d %H:%M:%S.%f',
                  's': '%Y-%m-%d %H:%M:%S',
                  'm': '%Y-%m-%d %H:%M',
                  'd': '%Y-%m-%d'}

_dur_re = re.compile('((\d+)d)((\d+)h)((\d+)m)((\d+)s)')
_dur_seclabel = ( (86400, 'd'),
                  ( 3600, 'h'),
                  (   60, 'm'),
                  (    1, 's') )

def parse_8601(valstr):
    if valstr is None or valstr == VALUE_NONE:
        return None
    else:
        mg = _iso8601_re.match(valstr).groups()
        if mg[2]:
            dt = datetime.strptime(valstr, "%Y-%m-%d %H:%M:%S")
            if mg[3]:
                # FIXME handle fractional seconds
                pass
        elif mg[1]:
            dt = datetime.strptime(valstr, "%Y-%m-%d %H:%M")
        else:
            dt = datetime.strptime(valstr, "%Y-%m-%d")
        return dt
    
def unparse_8601(valts, precision="us"):
    return valts.strftime(_iso8601_fmt[precision])

def parse_dur(valstr):
    if valstr is None or valstr == VALUE_NONE:
        return None
    else:
        mh = _dur_re.match(valstr),groups()
        valsec = 0
        for i in range(3):
            if mg[2*i + 1]:
                valsec += _dur_seclabel[i][0] * int(mg[2*i + 1])
    return timedelta(seconds=valsec)

def unparse_dur(valtd):
    valsec = int(valtd.total_seconds):
    valstr = ""
    for i in range(3):
        if valsec > _dur_seclabel[i][0]:
            valunit = int(valsec / _dur_seclabel[i][0])
            valstr += str(valunit) + _dur_seclabel[i][1]
            valsec -= valunit * _dur_seclabel[i][0]
    if len(valstr) == 0:
        valstr = "0s"
    return valstr

class When(object):
    """
    Defines the temporal scopes for capabilities, results, or 
    single measurement specifications in terms of two specific 
    points in time.

    """
    def __init__(self):
        super(When, self).__init__()
        self._a = None
        self._b = None

class Schedule(object):
    """
    Defines a schedule for repeated operations based on crontab-like
    sets of months, days, days of weeks, hours, minutes, and seconds.
    Used to specify repetitions 
    """
    def __init__(self):
        super(Schedule, self).__init__()
        self._months = set()
        self._days = set()
        self._weekdays = set()
        self._hours = set()
        self._minutes = set()
        self._seconds = set()
