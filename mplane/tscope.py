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
this code will be integrated into model.py.

"""

TIME_PAST = "past"
TIME_NOW = "now"
TIME_FUTURE = "future"

_iso8601_pat = '(\d+-\d+-\d+)(\s+\d+:\d+(:\d+)?)?(\.\d+)?'
_iso8601_re = re.compile(_iso8601_pat)
_iso8601_fmt = { 'us': '%Y-%m-%d %H:%M:%S.%f',
                  's': '%Y-%m-%d %H:%M:%S',
                  'm': '%Y-%m-%d %H:%M',
                  'd': '%Y-%m-%d'}

_dur_pat = '((\d+)d)((\d+)h)((\d+)m)((\d+)s)'
_dur_re = re.compile(_dur_pat)
_dur_seclabel = ( (86400, 'd'),
                  ( 3600, 'h'),
                  (   60, 'm'),
                  (    1, 's') )

_dow_label = ('so', 'mo', 'tu', 'we', 'th', 'fr', 'sa')

class PastTime:
    """
    Class representing the indeterminate past. 
    Do not instantiate; use the time_past instance of this class.

    """
    def __str__(self):
        return TIME_PAST

    def __repr__(self):
        return "mplane.tscope.time_past"

    def strftime(self, ign):
        return str(self)


time_past = PastTime()

class NowTime:
    """
    Class representing the present.
    Do not instantiate; use the time_now instance of this class.
    
    """
    def __str__(self):
        return TIME_NOW

    def __repr__(self):
        return "mplane.tscope.time_now"

    def strftime(self, ign):
        return str(self)

time_now = NowTime()

class FutureTime:
    """
    Class representing the indeterminate future.
    Do not instantiate; use the time_future instance of this class.

    """
    def __str__(self):
        return TIME_FUTURE

    def __repr__(self):
        return "mplane.tscope.time_future"

    def strftime(self, ign):
        return str(self)

time_future = FutureTime()

def parse_time(valstr):
    if valstr is None:
        return None
    elif valstr == TIME_PAST:
        return time_past
    elif valstr == TIME_FUTURE:
        return time_future
    elif valstr == TIME_NOW:
        return time_now
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
    
def unparse_time(valts, precision="us"):    
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
    single measurement specifications.

    """
    def __init__(self, valstr=None, a=None, b=None, d=None, p=None):
        super(When, self).__init__()
        self._a = a
        self._b = b
        self._d = d
        self._p = p

        if valstr is not None:
            self._parse(valstr)
        
    def _parse(self, valstr):
        # First separate the period from the value and parse it
        valsplit = valstr.split(PERIOD_SEP)
        if len(valsplit) > 1:
            (valstr, perstr) = valsplit
            self._p = parse_dur(perstr)
        else:
            self._p = None

        # then try to split duration or range
        valsplit = valstr.split(DURATION_SEP)
        if len(valsplit) > 1:
            (valstr, durstr) = valsplit
            self._d = parse_dur(durstr)
            valsplit = [valstr]
        else:
            self._d = None
            valsplit = valstr.split(RANGE_SEP)
        
        self._a = parse_time(valsplit[0])
        if len(valsplit) > 1:
            self._b = parse_time(valsplit[1])
        else:
            self._b = None

    def __str__(self):
        valstr = unparse_time(self._a)

        if self._b is not None:
            valstr = " ".join(valstr, RANGE_SEP, unparse_time(self._b))
        elif self._d is not None:
            valstr = " ".join(valstr, DURATION_SEP, unparse_dur(self._d))

        if (self._p) is not None:
            valstr = " ".join(valstr, PERIOD_SEP, unparse_dur(self._p))


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
