#
# mPlane Protocol Reference Implementation
# Information Model and Element Registry
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
Information model and element registry for the mPlane protocol.

This module implements Statements and Notifications, the core
messages used by the mPlane protocol, the Elements these
use to describe measurement and query schemas, and various
other classes to support them.

There are three kinds of Statement:

    - Capability represents something a component can do
    - Specification tells a component to do something it
      advertised a Capability for 
    - Result returns the results for a Specification in-band

Notifications are used to transfer other information between
components and clients. There are four kinds of Notification:

    - Receipt notifies that a Result is not yet ready or
      that the results of an operation will be indirectly exported.
    - Redemption is a subsequent attempt to redeem a Receipt.
    - Withdrawal notifies that a Capability is no longer available.
    - Interrupt notifies that a running Specification should be stopped.

To see how all this fits together, let's simulate the message exchange
in a simple ping measurement. First, we load the registry and 
programatically create a new Capability, as would be advertised by
the component. First, we initialize the registry and create a new 
empty Capability:

>>> import mplane
>>> import json
>>> mplane.model.initialize_registry()
>>> cap = mplane.model.Capability()

Probe components generally advertise a temporal scope from the
present stretching into the indeterminate future:

>>> cap.add_parameter("start", "now...+inf")
>>> cap.add_parameter("end", "now...+inf")

We can only ping from one IPv4 address, to any IPv4 address. 
Adding a parameter without a constraint makes it unconstrained:

>>> cap.add_parameter("source.ip4", "10.0.27.2")
>>> cap.add_parameter("destination.ip4")

We'll allow the client to set a period between one second and one hour,
which allows relatively long running measurements as well as more
immediate ones, without allowing an individual probe to be used for
flooding or DoS attacks:

>>> cap.add_parameter("period.s", "1...3600")

Then we define the result columns this measurement can produce. Here,
we want quick reporting of min, max, and mean delays, as well as a
total count of singleton measurements taken and packets lost:

>>> cap.add_result_column("delay.twoway.icmp.ms.min")
>>> cap.add_result_column("delay.twoway.icmp.ms.max")
>>> cap.add_result_column("delay.twoway.icmp.ms.mean")
>>> cap.add_result_column("delay.twoway.icmp.ms.count")
>>> cap.add_result_column("packets.lost")

Now we have a capability we could transform into JSON and make 
available to clients via the mPlane protocol, or via static 
download or configuration:

>>> capjson = json.dumps(cap.to_dict())
>>> capjson # doctest: +SKIP
'{"capability": "measure", 
  "parameters": {"end": "now...+inf", 
                 "period.s": "1...3600", 
                 "source.ip4": "10.0.27.2", 
                 "destination.ip4": "*", 
                 "start": "now...+inf"}, 
  "results": ["delay.twoway.icmp.ms.min", 
              "delay.twoway.icmp.ms.max", 
              "delay.twoway.icmp.ms.mean", 
              "delay.twoway.icmp.ms.count", 
              "packets.lost"]}'

On the client side, we'd receive this capability as a JSON object and turn it
into a capability, from which we generate a specification:

>>> clicap = mplane.model.message_from_dict(json.loads(capjson))
>>> spec = mplane.model.Specification(capability=clicap)
>>> spec
<Specification: measure b7e78ecade6929e549e169bd12030182 with 0/5 params, 0 metadata, 5 columns>

Here we have a specification with 0 of 5 parameters filled in. 

.. note:: The long hexadecimal number in statement representations is the 
          schema hash, which identifies the parameter and result columns.
          Statements with identical sets of parameters and columns
          (schemas) will have identical schema hashes.

So let's fill in some parameters; note that strings are accepted and
automatically parsed using each parameter's primitive type:

>>> spec.set_parameter_value("start", "2014-12-24 22:18:42")
>>> spec.set_parameter_value("end", "2014-12-24 22:19:42")
>>> spec.set_parameter_value("period.s", 1)
>>> spec.set_parameter_value("source.ip4", "10.0.27.2")
>>> spec.set_parameter_value("destination.ip4", "10.0.37.2")

.. note:: Presently, the protocol only supports absolute temporal scopes. 
          We almost certainly need relative scopes ("now + 1m") as well,
          to make it easier to state a specification has a duration as
          opposed to hard limits. This functionality will be added concurrently
          with the scheduling features in mplane.component, which themselves
          should follow current work in the LMAP WG.

And now we can transform this specification and send it back to
the component from which we got the capability:

>>> specjson = json.dumps(spec.to_dict())
>>> specjson # doctest: +SKIP
'{"specification": "measure", 
  "parameters": {"source.ip4": "10.0.27.2", 
                 "period.s": "1", 
                 "end": "2014-12-24 22:19:42.000000", 
                 "start": "2014-12-24 22:18:42.000000", 
                 "destination.ip4": "10.0.37.2"}, 
  "results": ["delay.twoway.icmp.ms.min", 
              "delay.twoway.icmp.ms.max", 
              "delay.twoway.icmp.ms.mean", 
              "delay.twoway.icmp.ms.count", 
              "packets.lost"]}'

On the component side, likewise, we'd receive this specification as a JSON
object and turn it back into a specification:

>>> comspec = mplane.model.message_from_dict(json.loads(specjson))

The component would determine the measurement, query, or other operation to
run by the specification, then extract the necessary parameter values, e.g.:

>>> comspec.get_parameter_value("destination.ip4")
IPv4Address('10.0.37.2')
>>> comspec.get_parameter_value("period.s")
1

After running the measurement, the component would return the results
by assigning values to parameters which changed and result columns
measured:

>>> res = mplane.model.Result(specification=comspec)
>>> res.set_parameter_value("start", "2014-12-24 22:18:42.993000")
>>> res.set_parameter_value("end", "2014-12-24 22:19:42.991000")
>>> res.set_result_value("delay.twoway.icmp.ms.min", 33)
>>> res.set_result_value("delay.twoway.icmp.ms.mean", 55)
>>> res.set_result_value("delay.twoway.icmp.ms.max", 192)
>>> res.set_result_value("delay.twoway.icmp.ms.count", 58)
>>> res.set_result_value("packets.lost", 2)

The result can then be serialized and sent back to the client:

>>> resjson = json.dumps(res.to_dict())
>>> resjson # doctest: +SKIP
'{"result": "measure", 
  "parameters": {"source.ip4": "10.0.27.2", 
                 "period.s": "1", 
                 "end": "2014-12-24 22:19:42.000000", 
                 "start": "2014-12-24 22:18:42.000000", 
                 "destination.ip4": "10.0.37.2"}, 
  "results": ["delay.twoway.icmp.ms.min", 
              "delay.twoway.icmp.ms.max", 
              "delay.twoway.icmp.ms.mean", 
              "delay.twoway.icmp.ms.count", 
              "packets.lost"], 
  "resultvalues": [["33", "192", "55", "58", "2"]]}'

which can transform them back to a result and extract the values:

>>> clires = mplane.model.message_from_dict(json.loads(resjson))
>>> clires
<Result: measure b7e78ecade6929e549e169bd12030182 with 5 params, 0 metadata, 5 columns, 1 rows>

If the component cannot return results immediately (for example, because
the measurement will take some time), it can return a receipt instead:

>>> rcpt = mplane.model.Receipt(specification=comspec)

This receipt contains all the information in the specification, as well as a token
which can be used to quickly identify it in the future. 

>>> rcpt.get_token()
'c4a88bccc437f538778549129af50897'

.. note:: The mPlane protocol specification allows components to assign tokens
          however they like. In the reference implementation, the default token
          is based on a hash like the schema hash: statements with the same verb,
          schema, parameter values, and metadata will have identical default tokens.
          A component could, however, assign serial-number based tokens, or tokens
          mapping to structures in its own filesystem, etc.

>>> jsonrcpt = json.dumps(rcpt.to_dict())
>>> jsonrcpt # doctest: +SKIP
'{"receipt": "measure", 
  "parameters": {"period.s": "1", 
                 "destination.ip4": "10.0.37.2", 
                 "source.ip4": "10.0.27.2", 
                 "end": "2014-12-24 22:19:42.000000", 
                 "start": "2014-12-24 22:18:42.000000"}, 
  "results": ["delay.twoway.icmp.ms.min", 
              "delay.twoway.icmp.ms.max", 
              "delay.twoway.icmp.ms.mean", 
              "delay.twoway.icmp.ms.count", 
              "packets.lost"], 
  "token": "c4a88bccc437f538778549129af50897"}'

The component keeps the receipt, keyed by token, and returns it to the
client in a message. The client then which generates a future redemption 
referring to this receipt to retrieve the results:

>>> clircpt = mplane.model.message_from_dict(json.loads(jsonrcpt))
>>> clircpt
<Receipt: c4a88bccc437f538778549129af50897>
>>> rdpt = mplane.model.Redemption(receipt=clircpt)
>>> rdpt
<Redemption: c4a88bccc437f538778549129af50897>

Note here that the redemption has the same token as the receipt; 
just the token may be sent back to the component to retrieve the 
results:

>>> json.dumps(rdpt.to_dict(token_only=True))
'{"redemption": "measure", "token": "c4a88bccc437f538778549129af50897"}'

.. note:: We should document and test interrupts and withdrawals, as well.

"""

from ipaddress import ip_address
from datetime import datetime, timedelta, timezone
from copy import copy, deepcopy
import collections
import functools
import operator
import hashlib
import json
import yaml
import re
import os

#######################################################################
# String constants
#######################################################################

ELEMENT_SEP = "."

CONSTRAINT_ALL = "*"
CONSTRAINT_RANGESEP = "..."
CONSTRAINT_SETSEP = ","

VALUE_NONE = "*"

TIME_PAST = "-inf"
TIME_NOW = "now"
TIME_FUTURE = "+inf"
TIME_WHENEVER = "whenever"
TIME_ONCE = "once"

VERB_MEASURE = "measure"
VERB_QUERY = "query"
VERB_COLLECT = "collect"
VERB_STORE = "store"

SECTION_PARAMETERS = "parameters"
SECTION_METADATA = "metadata"
SECTION_RESULTS = "results"
SECTION_RESULTVALUES = "resultvalues"
SECTION_TOKEN = "token"
SECTION_MESSAGE = "message"
SECTION_LINK = "link"
SECTION_WHEN = "when"

KIND_CAPABILITY = "capability"
KIND_SPECIFICATION = "specification"
KIND_RESULT = "result"
KIND_RECEIPT = "receipt"
KIND_REDEMPTION = "redemption"
KIND_INDIRECTION = "indirection"
KIND_WITHDRAWAL = "withdrawal"
KIND_INTERRUPT = "interrupt"
KIND_EXCEPTION = "exception"

PARAM_START = "start"
PARAM_END = "end"

REPHL = 8

#######################################################################
# Special Timestamp Values
#######################################################################

# FIXME we need magic timestamp values representing durations 
# (for end timestamp) or some special handling of start/end/duration
# parameters

@functools.total_ordering
class PastTime:
    """
    Class representing the indeterminate past. 
    Will compare as less than any other datetime.
    Do not instantiate; use the time_past instance of this class.

    """
    def __lt__(self, rval):
        return not (self is rval)
    
    def __eq__(self, rval):
        return self is rval

    def __str__(self):
        return TIME_PAST

    def __repr__(self):
        return "mplane.model.time_past"

time_past = PastTime()

@functools.total_ordering
class PresentTime:
    """
    Class representing the present.
    Do not instantiate; use the time_present instance of this class.
    
    """
    def __lt__(self, rval):
        if isinstance(rval, PresentTime):
            return False
        else:
          return datetime.utcnow() < rval;
    
    def __eq__(self, rval):
        if isinstance(rval, PresentTime):
            return True
        return datetime.utcnow() == rval;

    def __str__(self):
        return TIME_NOW

    def __repr__(self):
        return "mplane.model.time_present"

time_present = PresentTime()

@functools.total_ordering
class FutureTime:
    """
    Class representing the indeterminate future; 
    used for comparison with datetimes. 
    Use the time_future instance of this class.

    """
    def __lt__(self, rval):
        return False
    
    def __eq__(self, rval):
        return self is rval

    def __str__(self):
        return TIME_FUTURE

    def __repr__(self):
        return "mplane.model.time_future"

time_future = FutureTime()

class WheneverTime(PresentTime):
    """
    Class representing an intederminate time near the 
    present time. Only valid as the start time in a Specification
    where the end time is time_once, and is equivalent to PresentTime
    with an implicit lower priority. Do not instantiate; 
    use the time_whenever instance of this class.

    """
    def __str__(self):
        return TIME_WHENEVER

    def __repr__(self):
        return "mplane.model.time_whenever"

time_whenever = WheneverTime()

class OnceTime(PastTime):
    """
    Class representing a special timestamp, valid as the end time in a
    Specification, signifying that a measurement should run (natually)
    once then stop. Sorts as PastTime. Do not instantiate; use the 
    time_once instance of this class.

    """
    def __str__(self):
        return TIME_ONCE

    def __repr__(self):
        return "mplane.model.time_once"

time_once = OnceTime()

def test_weird_times():
    """Ensure special timestamps order correctly."""
    assert time_past < time_present
    assert time_present < time_future
    assert time_past < time_future
    assert time_once < time_present
    assert time_whenever < time_future

#######################################################################
# Primitive Types
#######################################################################

class Primitive(object):
    """
    Represents a primitive mPlane data type. Primitive types define
    textual and native representations for data elements, and convert
    between the two.

    In general, client code will not need to interact with Primitives;
    conversion between strings and values is handled automatically by
    the Statement and Notification classes.

    """
    def __init__(self, name):
        super(Primitive, self).__init__()
        self.name = name

    def __str__(self):
        """Primitive's string representation is its name"""
        return self.name

    def __repr__(self):                
        """Primitive's repr string is the name of its instance"""
        return "<special mplane primitive "+self.name+">"

    def parse(self, sval):
        """
        Convert a string to a value; default implementation
        returns the string directly, returning None for the
        special string "*", which represents "all values" in 
        mPlane.

        """
        if sval is None or sval == VALUE_NONE:
            return None
        else:
            return sval

    def unparse(self, val):
        """
        Convert a value to a string; default implementation
        uses native __str__ representation, replaces None with a
        the special string "*", representing all values.

        """
        if val is None:
            return VALUE_NONE
        else:
            return str(val)

class StringPrimitive(Primitive):
    """
    Represents a string. Uses the default implementation.
    If necessary, use the prim_string instance of this class;
    in general, however, this is used internally by Element.

    """
    def __init__(self):
        super().__init__("string")

    def __repr__(self):                
        return "mplane.model.prim_string"

class NaturalPrimitive(Primitive):
    """
    Represents a natural number (unsigned integer).

    Uses a Python int as the native representation.
    If necessary, use the prim_natural instance of this class;
    in general, however, this is used internally by Element.

    """
    def __init__(self):
        super(NaturalPrimitive, self).__init__("natural")

    def __repr__(self):                
        return "mplane.model.prim_natural"

    def parse(self, sval):
        """Convert a string to a natural value."""
        if sval is None or sval == VALUE_NONE:
            return None
        else:
            return int(sval)

class RealPrimitive(Primitive):
    """
    Represents a real number (floating point).

    Uses a Python float as the native representation.
    If necessary, use the prim_real instance of this class;
    in general, however, this is used internally by Element.

    """
    def __init__(self):
        super(RealPrimitive, self).__init__("real")
    
    def __repr__(self):                
        return "mplane.model.prim_real"

    def parse(self, sval):
        """Convert a string to a floating point value."""
        if sval is None or sval == VALUE_NONE:
            return None
        else:
            return float(sval)

class BooleanPrimitive(Primitive):
    """ 
    Represents a real number (floating point).

    Uses a Python bool as the native representation.
    If necessary, use the prim_boolean instance of this class;
    in general, however, this is used internally by Element.

    """
    def __init__(self):
        super().__init__("boolean")

    def __repr__(self):                
        return "mplane.model.prim_boolean"
    
    def parse(self, sval):
        """Convert a string to a boolean value."""
        if sval is None or sval == VALUE_NONE:
            return None
        elif sval == 'True':
            return True
        elif sval == 'False':
            return False
        else:
            raise ValueError("Invalid boolean value "+sval)

class AddressPrimitive(Primitive):
    """
    Represents a IPv4 or IPv6 host or network address.

    Uses the Python standard library ipaddress module
    for the native representation. 

    """
    def __init__(self):
        super(AddressPrimitive, self).__init__("address")
    
    def __repr__(self):                
        return "mplane.model.prim_address"

    def parse(self, sval):
        """Convert a string to an address value."""
        if sval is None or sval == VALUE_NONE:
            return None
        else:
            return ip_address(sval)

class URLPrimitive(Primitive):
    """
    Represents a URL. For now, URLs are implemented only as strings,
    without any parsing or validation.

    """
    def __init__(self):
        super().__init__("url")

    def __repr__(self):                
        return "mplane.model.prim_url"

_timestamp_re = re.compile('(\d+-\d+-\d+)(\s+\d+:\d+(:\d+(\.\d+)?)?)?')

class TimePrimitive(Primitive):
    """
    Represents a UTC timestamp with arbitrary precision.
    Also handles special-purpose mPlane timestamps.

    """
    def __init__(self):
        super().__init__("time")
    
    def __repr__(self):                
        return "mplane.model.prim_time"

    def parse(self, valstr):
        if valstr is None or valstr == VALUE_NONE:
            return None
        elif valstr == TIME_PAST:
            return time_past
        elif valstr == TIME_NOW:
            return time_present
        elif valstr == TIME_FUTURE:
            return time_future
        elif valstr == TIME_ONCE:
            return time_once
        elif valstr == TIME_WHENEVER:
            return time_whenever
        else:
            mg = _timestamp_re.match(valstr).groups()
            if mg[3]:
                dt = datetime.strptime(valstr, "%Y-%m-%d %H:%M:%S.%f")
            elif mg[2]:
                dt = datetime.strptime(valstr, "%Y-%m-%d %H:%M:%S")
            elif mg[1]:
                dt = datetime.strptime(valstr, "%Y-%m-%d %H:%M")
            else:
                dt = datetime.strptime(valstr, "%Y-%m-%d")
            return dt
    
    def unparse(self, val):
        if val is None:
            return VALUE_NONE
        if isinstance(val, datetime):
            return val.strftime("%Y-%m-%d %H:%M:%S.%f")
        else:
            return str(val)

prim_string = StringPrimitive()
prim_natural = NaturalPrimitive()
prim_real = RealPrimitive()
prim_boolean = BooleanPrimitive()
prim_time = TimePrimitive()
prim_address = AddressPrimitive()
prim_url = URLPrimitive()

_prim = {x.name: x for x in [prim_string, 
                             prim_natural, 
                             prim_real, 
                             prim_boolean,
                             prim_time,
                             prim_address, 
                             prim_url]}

def test_primitives():
    """Test primitive parsing and unparsing"""
    import math
    assert prim_string.parse("foo") == 'foo'
    assert prim_string.unparse("foo") == 'foo'
    assert prim_string.parse("*") is None
    assert prim_string.unparse(None) == '*'
    assert prim_natural.parse("42") == 42
    assert prim_natural.unparse(27) == '27'
    assert prim_real.unparse(math.pi) == '3.141592653589793'
    assert prim_real.parse("4.2e6") == 4200000.0
    assert prim_boolean.unparse(False) == 'False'
    assert prim_boolean.parse("True") == True
    assert prim_address.parse("10.0.27.101") == ip_address('10.0.27.101')
    assert prim_address.unparse(ip_address("10.0.27.101")) == '10.0.27.101'
    assert prim_address.parse("2001:db8:1:33::c0:ffee") == \
           ip_address('2001:db8:1:33::c0:ffee')
    assert prim_address.unparse(ip_address("2001:db8:1:33::c0:ffee")) == \
           '2001:db8:1:33::c0:ffee'
    assert prim_time.parse("2013-07-30 23:19:42") == \
           datetime(2013, 7, 30, 23, 19, 42)
    assert prim_time.unparse(datetime(2013, 7, 30, 23, 19, 42)) == \
           '2013-07-30 23:19:42.000000'
    assert prim_time.parse("now") is time_present
    assert prim_time.parse("-inf") is time_past
    assert prim_time.parse("+inf") is time_future
    assert prim_time.parse("once") is time_once
    assert prim_time.parse("whenever") is time_whenever
    assert prim_time.unparse(time_present) == "now"
    assert prim_time.unparse(time_past) == "-inf"
    assert prim_time.unparse(time_future) == "+inf"
    assert prim_time.unparse(time_once) == "once"
    assert prim_time.unparse(time_whenever) == "whenever"

#
# Element classes
#
class Element(object):
    """
    An Element represents a name for a particular type of data with 
    a specific semantic meaning; it is analogous to an IPFIX Information 
    Element, or a named column in a relational database.

    An Element has a Name by which it can be compared to other Elements,
    and a primitive type, which it uses to convert values to and from
    strings.

    The mPlane reference implementation includes a default registry of
    elements; use initialize_registry() to use these.

    """
    def __init__(self, name, prim, desc=None):
        super(Element, self).__init__()
        self._name = name
        self._prim = prim
        self.desc = desc

    def __str__(self):
        return self._name

    def __repr__(self):
        return "<Element "+str(self)+" "+repr(self._prim)+" >"

    def parse(self, sval):
        """
        Convert a string to a value for this Element; delegates to primitive.
        """
        return self._prim.parse(sval)

    def unparse(self, val):
        """
        Convert a value to a string for this Element; delegates to primitive.
        """
        return self._prim.unparse(val)

    def compatible_with(self, rval):
        """
        Determine based on naming rules if this element is compatible with
        element rval; that is, if transformation_to will return a function
        for turning a value of this element to the other. Compatibility based
        on name structure is a future feature; this method currently checks for
        name equality only.

        """
        return self._name == rval._name

    def transformation_to(self, rval):
        """
        Returns a function which will transform values of this element
        into values of element rval; used to support unit conversions.
        This is a future feature, and is currently a no-op. 
        Only valid if compatible_with returns True.

        """
        return lambda x: x

_typedef_re = re.compile('^([a-zA-Z0-9\.\_]+)\s*\:\s*(\S+)')
_desc_re = re.compile('^\s+([^#]+)')
_comment_re = re.compile('^\s*\#')

def parse_element(line):
    m = _typedef_re.match(line)
    if m:
        return Element(m.group(1), _prim[m.group(2)])
    else:
        return None

def _parse_elements(lines):
    """
    Given an iterator over lines from a file or stream describing
    a set of Elements, returns a list of Elements. This file should 
    contain element names and primitive names separated by ":" in the 
    leftmost column, followed by zero or more indented lines of 
    description. Used to initialize the mPlane element registry from a file;
    call initialize_registry instead
       
    """
    elements = []
    desclines = []

    for line in lines:
        m = _typedef_re.match(line)
        if m:
            if len(elements) and len(desclines):
                elements[-1].desc = " ".join(desclines)
                desclines.clear()
            elements.append(Element(m.group(1), _prim[m.group(2)]))
        else:
            m = _desc_re.match(line)
            if m:
                desclines.append(m.group(1))

    if len(elements) and len(desclines):
        elements[-1].desc = "".join(desclines)

    return elements

_element_registry = {}

def initialize_registry(filename=None):
    """
    Initializes the mPlane registry from a file; if no filename is given,
    initializes the registry from the internal set of Elements.
    """
    _element_registry.clear()

    if filename is None:
        filename = os.path.join(os.path.dirname(__file__), "registry.txt")

    with open(filename, mode="r") as file:
        for elem in _parse_elements(file):
            _element_registry[elem._name] = elem

def element(name):
    return _element_registry[name]

#######################################################################
# Constraints
#######################################################################

class Constraint(object):
    """
    Represents a set of acceptable values for an element.
    The default constraint accepts everything; use
    the special instance constraint_all for this.

    Clients and components will generally interact with the 
    Constraint classes through Parameters.

    """
    def __init__(self, prim):
        super(Constraint, self).__init__()
        self._prim = prim

    def __str__(self):
        """Represent this Constraint as a string"""
        return CONSTRAINT_ALL

    def __repr__(self):
        return "mplane.model.constraint_all"

    def met_by(self, val):
        """Determine if this constraint is met by a given value."""
        return True

    def single_value(self):
        return None

constraint_all = Constraint(None)

class RangeConstraint(Constraint):
    """Represents acceptable values for an element as an inclusive range"""

    def __init__(self, prim, sval=None, a=None, b=None):
        super(RangeConstraint, self).__init__(prim)
        if sval is not None:
            (astr, bstr) = sval.split(CONSTRAINT_RANGESEP)
            self.a = prim.parse(astr)
            self.b = prim.parse(bstr)
        elif a is not None and b is not None:
            self.a = a
            self.b = b
        else:
            raise "RangeConstraint needs either a string "+\
                  "or an explicit range"

        if (self.a > self.b):
            (self.a, self.b) = (self.b, self.a)

    def __str__(self):
        """Represent this RangeConstraint as a string."""
        return self._prim.unparse(self.a) + \
               CONSTRAINT_RANGESEP + \
               self._prim.unparse(self.b)

    def __repr__(self):
        return "mplane.model.RangeConstraint("+repr(self._prim)+\
                                             ", "+repr(str(self))+")"

    def met_by(self, val):
        """Determine if the value is within the range"""
        return (val >= self.a) and (val <= self.b)

    def single_value(self):
        if self.a == self.b:
            return self.a
        else:
            return None

class SetConstraint(Constraint):
    """Represents acceptable values as a discrete set."""
    def __init__(self, prim, sval=None, vs=None):
        super(SetConstraint, self).__init__(prim)
        if sval is not None:
            self.vs = set(map(self._prim.parse, sval.split(CONSTRAINT_SETSEP)))
        elif vs is not None:
            self.vs = vs
        else:
            self.vs = set()

    def __str__(self):
        """Represent this SetConstraint as a string."""
        return CONSTRAINT_SETSEP.join(map(self._prim.unparse, self.vs))

    def __repr__(self):
        return "mplane.model.SetConstraint("+repr(self._prim)+\
                                             ", "+repr(str(self))+")"

    def met_by(self, val):
        """Determine if the value is a mamber of the set"""
        return val in self.vs

    def single_value(self):
        if len(self.vs) == 1:
            return list(self.vs)[0]
        else:
            return None

def parse_constraint(prim, sval):
    if sval == CONSTRAINT_ALL:
        return constraint_all
    elif sval.find(CONSTRAINT_RANGESEP) > 0:
        return RangeConstraint(prim=prim, sval=sval)
    else:
        return SetConstraint(prim=prim, sval=sval)

def test_constraints():
    """Test range and set constraints"""

    assert constraint_all.met_by("whatever")
    assert constraint_all.met_by(None)

    rc = parse_constraint(prim_natural,"0...99")
    assert not rc.met_by(-1)
    assert rc.met_by(0)
    assert rc.met_by(33)
    assert rc.met_by(99)
    assert not rc.met_by(100)
    assert str(rc) == "0...99"

    sc = parse_constraint(prim_address,"10.0.27.100,10.0.28.103")
    assert sc.met_by(ip_address('10.0.28.103'))
    assert not sc.met_by(ip_address('10.0.27.103'))

#######################################################################
# Statements
#######################################################################

class Parameter(Element):
    """
    A Parameter is an element which can take a constraint and a value. 
    In Capabilities, Parameters have constraints and no value; in
    Specifications and Results, Parameters have both constraints and
    values.

    """
    def __init__(self, parent_element, constraint=constraint_all, val=None):
        super(Parameter, self).__init__(parent_element._name, parent_element._prim)
        if isinstance(constraint, str):
            self._constraint = parse_constraint(self._prim, constraint)
        else:
            self._constraint = constraint

        self.set_value(val)

    def __repr__(self):
        return "<Parameter "+str(self)+" "+repr(self._prim)+\
               str(self._constraint)+" value "+repr(self._val)+">"

    def has_value(self):
        return self._val is not None

    def set_single_value(self):
        self._val = self._constraint.single_value()

    def set_value(self, val):
        if isinstance(val, str):
            val = self._prim.parse(val)

        if (val is None) or self._constraint.met_by(val):
            self._val = val
        else:
            raise ValueError(repr(self) + " cannot take value " + repr(val))

    def get_value(self):
        return self._val

    def as_tuple(self):
        if self._val is not None:
            return (self._name, self._prim.unparse(self._val))
        else:
            return (self._name, str(self._constraint))

    def _clear_constraint(self):
        self._constraint = constraint_all

class Metavalue(Element):
    """
    A Metavalue is an element which can take an unconstrained value.
    Metavalues are used in statement metadata sections.

    """
    def __init__(self, parent_element, val):
        super(Metavalue, self).__init__(parent_element._name, parent_element._prim)
        self.set_value(val)

    def __repr__(self):
        return "<Metavalue "+str(self)+" "+repr(self._prim)+\
               " value "+repr(self._val)+" >"

    def set_value(self, val):
        if instanceof(val, str):
            val = self._prim.parse(val)
        self._val = val

    def get_value(self):
        return self._val

    def as_tuple(self):
        return (self._name, self._prim.unparse(self._val))


class ResultColumn(Element):
    """
    A ResultColumn is an element which can take an array of values. 
    In Capabilities and Specifications, this array is empty, while in
    Results it has one or more values, such that all the ResultColumns
    in the Result have the same number of values.

    """
    def __init__(self, parent_element):
        super(ResultColumn, self).__init__(parent_element._name, parent_element._prim)
        self._vals = []

    def __repr__(self):
        return "<ResultColumn "+str(self)+" "+repr(self._prim)+\
               " with "+str(len(self))+" values>"

    def __len__(self):
        return len(self._vals)

    def __getitem__(self, key):
        return self._vals[key]

    def __setitem__(self, key, val):
        # Automatically parse strings
        if isinstance(val, str):
            val = self._prim.parse(val)

        # Automatically extend column to fit
        while len(self) < key:
            self._vals.append(None)

        # Append or replace value
        if len(self) == key:
            self._vals.append(val)
        else:
            self._vals[key] = val

    def __delitem__(self, key):
        del(self._vals[key])

    def __iter__(self):
        return iter(self._vals)

    def clear(self):
        self._vals.clear()

class Statement(object):
    """
    A Statement is an assertion about the properties of a measurement
    or other action performed by an mPlane component. This class 
    contains common implementation for the three kinds of mPlane
    statement. Clients and components should use the
    :class:`mplane.model.Capability`, :class:`mplane.model.Specification`, 
    and :class:`mplane.model.Result` classes instead.

    """

    # FIXME, move token into Statement, generate it from parameters, and carry it forward into Result.

    def __init__(self, dictval=None, verb=VERB_MEASURE):
        super(Statement, self).__init__()
        #Make a blank statement
        self._params = collections.OrderedDict()
        self._metadata = collections.OrderedDict()
        self._resultcolumns = collections.OrderedDict()
        self._link = None
        if dictval is not None:
            self._from_dict(dictval)
        else:
            self._verb = verb;

    def __repr__(self):
        return "<Statement "+self.kind_str()+": "+self._verb+\
               " token "+self.get_token(REPHL)+" schema "+self.schema_hash(REPHL)+">"

    def kind_str(self):
        raise NotImplementedError("Cannot instantiate a raw Statement")

    def validate(self):
        raise NotImplementedError("Cannot instantiate a raw Statement")

    def add_parameter(self, elem_name, constraint=constraint_all, val=None):
        """Programatically add a parameter to this statement."""
        self._params[elem_name] = Parameter(element(elem_name), 
                                  constraint=constraint,
                                  val = val)

    def has_parameter(self, elem_name):
        """Return True if the statement has a parameter with the given name"""
        return elem_name in self._params

    def parameter_names(self):
        """Iterate over the names of parameters in this Statement"""
        yield from self._params.keys()

    def count_parameters(self):
        """Return the number of parameters in this Statement"""
        return len(self._params)

    def count_parameter_values(self):
        """Return the number of parameters with values in this Statement"""
        return sum(map(lambda p: p.has_value(), self._params.values()))

    def get_parameter_value(self, elem_name):
        """Return the value for a named parameter on this Statement."""
        return self._params[elem_name].get_value()

    def set_parameter_value(self, elem_name, value):
        """Programatically set a value for a parameter on this Statement."""
        elem = self._params[elem_name]
        elem.set_value(value)

    def add_metadata(self, elem_name, val):
        """Programatically add a metadata element to this statement."""
        self._metadata[elem_name] = Metavalue(element(elem_name), val)

    def has_metadata(self, elem_name):
        """Return True if the statement has a metadata element with the given name"""
        return elem_name in self._metadata

    def metadata_names(self):
        """Iterate over the names of metadata elements in this Statement"""
        yield from self._metadata.keys()

    def count_metadata(self):
        """Return the number of metavalues in this Statement"""
        return len(self._metadata)

    def add_result_column(self, elem_name):
        """Programatically add a result column to this Statement."""
        self._resultcolumns[elem_name] = ResultColumn(element(elem_name))

    def has_result_column(self, elem_name):
        return elem_name in self._resultcolumns

    def result_column_names(self):
        """Iterate over the names of result columns in this statement"""
        yield from self._resultcolumns.keys()

    def count_result_columns(self):
        """Return the number of result columns in this Statement"""
        return len(self._resultcolumns)

    def count_result_rows(self):
        """Return the number of result rows in this Statement"""
        return functools.reduce(max, 
                   [len(col) for col in self._resultcolumns.values()], 0)

    def get_link(self):
        return self._link

    def set_link(self, link):
        self._link = link

    def schema_hash(self, lim=None):
        """
        Return a hex string uniquely identifying the set of parameters
        and result columns (the schema) of this statement.

        """
        sstr = "p " + " ".join(sorted(self._params.keys())) + \
               " r " + " ".join(sorted(self._resultcolumns.keys()))
        hstr = hashlib.md5(sstr.encode('utf-8')).hexdigest()
        if lim is not None:
            return hstr[:lim]
        else:
            return hstr

    def pv_hash(self, lim=None):
        """
        Return a hex string uniquely identifying the set of parameters,
        parameter values, and result columns of this statement. Used as
        a specification key.

        """
        spk = sorted(self._params.keys())
        spv = [self._params[k].unparse(self._params[k].get_value()) for k in spk]
        tstr = self._verb + \
               " pk " + " ".join(spk) + \
               " pv " + " ".join(spv) + \
               " r " + " ".join(sorted(self._resultcolumns.keys()))
        hstr = hashlib.md5(tstr.encode('utf-8')).hexdigest()
        if lim is not None:
            return hstr[:lim]
        else:
            return hstr        

    def pcv_hash(self, lim=None):
        """
        Return a hex string uniquely identifying the set of parameters,
        parameter constraints, parameter values, and result columns 
        of this statement. Used as a capability key.

        """
        spk = sorted(self._params.keys())
        spc = [str(self._params[k]._constraint) for k in spk]
        spv = [self._params[k].unparse(self._params[k].get_value()) for k in spk]
        tstr = self._verb + \
               " pk " + " ".join(spk) + \
               " pc " + " ".join(spc) + " pv " + " ".join(spv) + \
               " r " + " ".join(sorted(self._resultcolumns.keys()))
        hstr = hashlib.md5(tstr.encode('utf-8')).hexdigest()
        if lim is not None:
            return hstr[:lim]
        else:
            return hstr

    def mpcv_hash(self, lim=None):
        """
        Return a hex string uniquely identifying the set of parameters,
        parameter constraints, parameter values, metadata, metadata values, 
        and result columns (the extended specification) of this statement.
        Used as a complete token for statements.

        """
        spk = sorted(self._params.keys())
        spc = [str(self._params[k]._constraint) for k in spk]
        spv = [self._params[k].unparse(self._params[k].get_value()) for k in spk]
        smk = sorted(self._metadata.keys())
        smv = [self._metadata[k].unparse(self._metadata[k].get_value()) for k in smk]
        tstr = self._verb + \
               " pk " + " ".join(spk) + \
               " pc " + " ".join(spc) + " pv " + " ".join(spv) + \
               " mk " + " ".join(smk) + " mv " + " ".join(smv) + \
               " r " + " ".join(sorted(self._resultcolumns.keys()))
        hstr = hashlib.md5(tstr.encode('utf-8')).hexdigest()
        if lim is not None:
            return hstr[:lim]
        else:
            return hstr

    def get_token(self, lim=None):
        return self.mpcv_hash(lim)

    def _result_rows(self):
        rows = []
        for row_index in range(self.count_result_rows()):
            row = []
            rows.append(row)
            for col in self._resultcolumns.values():
                try:
                    valstr = col._prim.unparse(col[row_index])
                except IndexError:
                    valstr = VALUE_NONE
                row.append(valstr)
        return rows

    def to_dict(self):
        """
        Convert a Statement to a dictionary (for further conversion 
        to JSON or YAML), which can be passed as the dictval
        argument of the appropriate statement constructor.

        """
        self.validate()
        d = collections.OrderedDict()
        d[self.kind_str()] = self._verb

        if self.count_parameters() > 0:
            d[SECTION_PARAMETERS] = {t[0] : t[1] for t in [v.as_tuple() 
                                        for v in self._params.values()]}

        if self.count_metadata() > 0:
            d[SECTION_METADATA] = {t[0] : t[1] for t in [v.as_tuple() 
                                        for v in self._metadata.values()]}

        if self.count_result_columns() > 0:
            d[SECTION_RESULTS] = [k for k in self._resultcolumns.keys()]
            if self.count_result_rows() > 0:
                d[SECTION_RESULTVALUES] = self._result_rows()

        if self._link is not None:
          d[SECTION_LINK] = self._link

        return d

    def _params_from_dict(self, d):
        """
        Fill in parameters from a dictionary; used internally.
        The default implementation interprets dictionary values
        as parameter values.
        """
        for (k, v) in d.items():
            self.add_parameter(k, val=v)

    def _from_dict(self, d):
        """
        Fill in this Statement with values from a dictionary
        produced with to_dict (i.e., as taken from JSON or YAML).
        Ignores result values; these are handled by :func:`Result._from_dict()

        """
        self._verb = d[self.kind_str()]

        if SECTION_PARAMETERS in d:
            self._params_from_dict(d[SECTION_PARAMETERS])

        if SECTION_METADATA in d:
            for (k, v) in d[SECTION_METADATA].items():
                self.add_metadata(k, v)

        if SECTION_RESULTS in d:
            for v in d[SECTION_RESULTS]:
                self.add_result_column(v)

        if SECTION_LINK in d:
          self._link = d[SECTION_LINK]

    def _clear_constraints(self):
        for param in self._params.values():
            param._clear_constraint()

class Capability(Statement):
    """
    A Capability represents something an mPlane component can do.
    Capabilities contain verbs (strings identifying the thing the
    component can do), parameters (which must be given by a client
    in a Specification in order for the component to do that thing),
    metadata (additional information about the process used to do
    that thing), and result columns (the data that thing will return).

    Capabilities can either be created programatically, using the
    add_parameter(), add_metadata(), and add_result_column()
    methods, or by reading from a JSON or YAML object [FIXME document
    how this works once it's written]

    """

    def __init__(self, dictval=None, verb=VERB_MEASURE):
        super(Capability, self).__init__(dictval=dictval, verb=verb)

    def __repr__(self):
        return "<Capability: "+self._verb+\
               " token "+self.get_token(REPHL)+" schema "+self.schema_hash(REPHL)+\
               " p/m/r "+str(self.count_parameters())+"/"+\
               str(self.count_metadata())+"/"+\
               str(self.count_result_columns())+">"

    def kind_str(self):
        return KIND_CAPABILITY

    def validate(self):
        pval = functools.reduce(operator.__or__, 
                                (p.has_value() for p in self._params.values()),
                                False)

        if pval or (self.count_result_rows() > 0):
            raise ValueError("Capabilities must have neither parameter nor "+
                             "result values.")

    def _params_from_dict(self, d):
        """
        Fill in parameters from a dictionary; used internally.
        The Capability implementation interprets dictionary values
        as constraints.
        """
        for (k, v) in d.items():
            self.add_parameter(k, constraint=v)

class Specification(Statement):
    """
    A Specification represents a request for an mPlane component to do 
    something it has advertised in a Capability.  
    Capabilities contain verbs (strings identifying the thing the
    component can do), parameters (which must be given by a client
    in a Specification in order for the component to do that thing),
    metadata (additional information about the process used to do
    that thing), and result columns (the data that thing will return). 

    Specifications are created either by passing a Capability the
    Specification is intended to use as the capability= argument of
    the constructor, or by reading from a JSON or YAML object 
    [FIXME document how this works once it's written]

    """
    def __init__(self, dictval=None, capability=None, verb=VERB_MEASURE):
        super(Specification, self).__init__(dictval=dictval, verb=verb)
        if dictval is None and capability is not None:
            self._verb = capability._verb
            self._metadata = capability._metadata
            self._params = deepcopy(capability._params)
            self._resultcolumns = deepcopy(capability._resultcolumns)
            # set values that are constrained to a single choice
            for param in self._params.values():
                param.set_single_value()

    def __repr__(self):
        return "<Specification: "+self._verb+\
               " token "+self.get_token(REPHL)+" schema "+self.schema_hash(REPHL)+\
               " p(v)/m/r "+str(self.count_parameters())+"("+\
               str(self.count_parameter_values())+")/"+\
               str(self.count_metadata())+"/"+\
               str(self.count_result_columns())+">"

    def kind_str(self):
        return KIND_SPECIFICATION

    def validate(self):
        pval = functools.reduce(operator.__and__, 
                        (p.has_value() for p in self._params.values()),
                        True)

        if (not pval) or (self.count_result_rows() > 0):
            raise ValueError("Specifications must have parameter values.")

    def job_delay(self):
        """
        Return the current delay required before running this 
        specification, in seconds.

        Returns 0 if the specification should start immediately. 
        """
        start = self.get_parameter_value(PARAM_START)
        if start is time_present or start is time_whenever:
            return 0
        elif isinstance(start, datetime):
            return max(0, (start - datetime.utcnow()).total_seconds())
        else:
            raise ValueError("Invalid "+PARAM_START+" value")

    def job_duration(self):
        """
        Return the duration of this specification, in seconds.

        Returns 0 if the specification should run once, 
        and None if the specification should run forever.

        """
        start = self.get_parameter_value(PARAM_START)
        end = self.get_parameter_value(PARAM_END)

        if end is time_once:
            return 0
        elif end is time_future:
            return None
        elif not isinstance(end, datetime):
            raise ValueError("Invalid "+PARAM_END+" value")

        if start is time_present or start is time_whenever:
            start = datetime.utcnow()

        return (end - start).total_seconds()

    def job_once(self):
        """
        Return True if the specification should only 
        run a single measurement.

        """
        return self.get_parameter_value(PARAM_END) is time_once

    def fulfills(self, cap):
        """
        Determine whether this specification fulfills a given capability
        (i.e. that the schemas match and that the parameter values match
        the constraints)

        """
        #FIXME maybe do this without schema hashing?
        return self.schema_hash() == cap.schema_hash()

class Result(Statement):
    """docstring for Result"""
    def __init__(self, dictval=None, specification=None, verb=VERB_MEASURE):
        super(Result, self).__init__(dictval=dictval, verb=verb)
        if dictval is None and specification is not None:
            self._verb = specification._verb
            self._metadata = specification._metadata
            self._params = deepcopy(specification._params)
            self._resultcolumns = deepcopy(specification._resultcolumns)
            # allow parameters to take values 
            self._clear_constraints()

    def __repr__(self):
        return "<Result: "+self._verb+\
               " token "+self.get_token(REPHL)+" schema "+self.schema_hash(REPHL)+\
               " p/m/r(r) "+str(self.count_parameters())+"/"+\
               str(self.count_metadata())+"/"+\
               str(self.count_result_columns())+"("+\
               str(self.count_result_rows())+")>"

    def kind_str(self):
        return KIND_RESULT

    def validate(self):
        pval = functools.reduce(operator.__and__, 
                        (p.has_value() for p in self._params.values()),
                        True)

        if (not pval):
            raise ValueError("Results must have parameter values.")

    def _from_dict(self, d):
        """
        Fill in this Result with values from a dictionary
        produced with to_dict().

        """
        super(Result,self)._from_dict(d)

        column_key = list(self._resultcolumns.keys())

        if SECTION_RESULTVALUES in d:
            for i, row in enumerate(d[SECTION_RESULTVALUES]):
                for j, val in enumerate(row):
                    self._resultcolumns[column_key[j]][i] = val

    def set_result_value(self, elem_name, val, row_index=0):
        self._resultcolumns[elem_name][row_index] = val

#######################################################################
# Notifications
#######################################################################

class BareNotification(object):
    """
    Notifications are used to send additional information between
    mPlane clients and components other than measurement statements.
    Notifications can either be part of a normal measurement workflow
    (as Receipts and Redemptions) or signal exceptional conditions
    (as Withdrawals and Interrupts).

    This class contains implementation common to all Notifications
    which do not contain any information from a related Capability
    or Specification.

    """
    def __init__(self, dictval=None, token=None):
        super(BareNotification, self).__init__()
        if dictval is not None:
            self._from_dict(dictval)

        self._token = token

class Exception(BareNotification):
    """
    A Component sends an Exception to a Client, or a Client to a 
    Component, to present a human-readable message about a failure
    or non-nominal condition 

    """
    def __init__(self, dictval=None, token=None, errmsg=None):
        super(Exception, self).__init__(dictval=dictval, token=token)
        if errmsg is None and dictval is None:
            errmsg = "Unspecified exception"
        self._errmsg = errmsg

    def __repr__(self):
        return "<Exception: "+self._token+" "+self._errmsg+">"

    def get_token(self):
        return self._token

    def to_dict(self):
        d = collections.OrderedDict()
        d[KIND_EXCEPTION] = self._token
        d[SECTION_MESSAGE] = self._errmsg
        return d

    def _from_dict(self, d):
        self._token = d[KIND_EXCEPTION]
        self._errmsg = d[SECTION_MESSAGE]

class StatementNotification(Statement):
    """
    Common implementation superclass for notifications that 
    may contain all or part of a related Capability or Specification.

    Clients and components should use :class:`mplane.model.Receipt`,
    :class:`mplane.model.Redemption`, and :class:`mplane.model.Withdrawal`
    directly

    """
    def __init__(self, dictval=None, statement=None, token=None, verb=VERB_MEASURE):
        super(StatementNotification, self).__init__(dictval=dictval, verb=verb)
        if dictval is None and statement is not None:
            self._verb = statement._verb
            self._metadata = statement._metadata
            self._params = deepcopy(statement._params)
            self._resultcolumns = deepcopy(statement._resultcolumns)

        self._token = token

    def _default_token(self):
        return self.mpcv_hash()

    def get_token(self):
        if self._token is None:
            self._token = self._default_token()
        return self._token

    def to_dict(self, token_only=False):
        d = super(StatementNotification, self).to_dict()
        if token_only and self._token is not None:
            for sk in (SECTION_PARAMETERS, SECTION_METADATA, SECTION_RESULTS):
                try:
                    del(d[sk])
                except KeyError:
                    pass

        d[SECTION_TOKEN] = self.get_token()

        return d

    def _from_dict(self, d):
        super(StatementNotification,self)._from_dict(d)

        if SECTION_TOKEN in d:
            self._token = d[SECTION_TOKEN]

class Receipt(StatementNotification):
    """
    A component presents a receipt to a Client in lieu of a result, when the
    result will not be available in a reasonable amount of time; or to confirm
    a Specification """
    def __init__(self, dictval=None, specification=None, token=None):
        super(Receipt,self).__init__(dictval=dictval, statement=specification, token=token)

    def __repr__(self):
        return "<Receipt: "+self.get_token()+">"

    def kind_str(self):
        return KIND_RECEIPT

    def validate(self):
        Specification.validate(self)

class Redemption(StatementNotification):
    """
    A client presents a Redemption to a component from which it has received
    a Receipt in order to get the associated Result.

    """
    def __init__(self, dictval=None, receipt=None, token=None):
        super(Redemption,self).__init__(dictval=dictval, statement=receipt, token=token)
        if receipt is not None and token is None:
            self._token = receipt.get_token()

    def __repr__(self):
        return "<Redemption: "+self.get_token()+">"

    def kind_str(self):
        return KIND_REDEMPTION

    def validate(self):
        Specification.validate(self)

class Withdrawal(StatementNotification):
    """A Withdrawal cancels a Capability"""
    def __init__(self, dictval=None, capability=None, token=None):
        super(Withdrawal,self).__init__(dictval=dictval, statement=capability, token=token)

    def __repr__(self):
        return "<Withdrawal: "+self.get_token()+">"

    def kind_str(self):
        return KIND_WITHDRAWAL

    def validate(self):
        Capability.validate(self)

class Interrupt(StatementNotification):
    """An Interrupt cancels a Specification"""
    def __init__(self, dictval=None, specification=None, token=None):
        super(Receipt,self).__init__(dictval=dictval, statement=specification, token=token)

    def __repr__(self):
        return "<Interrupt: "+self.get_token()+">"

    def kind_str(self):
        return KIND_INTERRUPT

    def validate(self):
        Specification.validate(self)

def message_from_dict(d):
    """
    Given a dictionary returned from to_dict(), return a decoded
    mPlane message (statement or notification).

    """
    classmap = { KIND_CAPABILITY : Capability,
                 KIND_SPECIFICATION : Specification,
                 KIND_RESULT : Result,
                 KIND_RECEIPT : Receipt,
                 KIND_REDEMPTION : Redemption,
                 KIND_WITHDRAWAL : Withdrawal,
                 KIND_INTERRUPT : Interrupt,
                 KIND_EXCEPTION : Exception}

    for k in classmap.keys():
        if k in d:
            return classmap[k](dictval = d)
    raise ValueError("Cannot determine message type from "+repr(d))

def parse_json(jstr):
    return message_from_dict(json.loads(jstr))

def unparse_json(msg):
    return json.dumps(msg.to_dict(), 
                      sort_keys=True, indent=2, separators=(',',': '))

def parse_yaml(ystr):
    return mplane.model.message_from_dict(yaml.load(ystr))

def unparse_yaml(msg):
    return yaml.dump(dict(msg.to_dict()), default_flow_style=False, indent=4)

