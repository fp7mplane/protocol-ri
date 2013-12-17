#
# mPlane Protocol Reference Implementation
# Information Model and Element Registry
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
the component:

This would be transformed into JSON and made available to clients:

[work pointer]

"""

from ipaddress import ip_address
from datetime import datetime, timezone
import collections
import functools
import re

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

KIND_CAPABILITY = "capability"
KIND_SPECIFICATION = "specification"
KIND_RESULT = "result"
KIND_RECEIPT = "receipt"
KIND_REDEMPTION = "redemption"
KIND_INDIRECTION = "indirection"
KIND_WITHDRAWAL = "withdrawal"
KIND_INTERRUPT = "interrupt"

#######################################################################
# Special Timestamp Values
#######################################################################

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
        return datetime.utcnow() < rval;
    
    def __eq__(self, rval):
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
    """ensure special timestamps order correctly"""
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

    >>> import mplane.model
    >>> mplane.model.prim_string.parse("foo")
    'foo'
    >>> mplane.model.prim_string.unparse("foo")
    'foo'
    >>> mplane.model.prim_string.parse("*")
    >>> mplane.model.prim_string.unparse(None)
    '*'

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

    >>> import mplane.model
    >>> mplane.model.prim_natural.parse("42")
    42
    >>> mplane.model.prim_natural.unparse(27)
    '27'

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

    >>> import math
    >>> import mplane.model
    >>> mplane.model.prim_real.unparse(math.pi)
    '3.141592653589793'
    >>> mplane.model.prim_real.parse("4.2e6")
    4200000.0

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
 
    >>> import mplane.model   
    >>> mplane.model.prim_boolean.unparse(False)
    'False'
    >>> mplane.model.prim_boolean.parse("True")
    True

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
    If necessary, use the prim_address instance of this class;
    in general, however, this is used internally by Element.

    >>> from ipaddress import ip_address
    >>> import mplane.model   
    >>> mplane.model.prim_address.parse("10.0.27.101")
    IPv4Address('10.0.27.101')
    >>> mplane.model.prim_address.unparse(ip_address("10.0.27.101"))
    '10.0.27.101'
    >>> mplane.model.prim_address.parse("2001:db8:1:33::c0:ffee")
    IPv6Address('2001:db8:1:33::c0:ffee')
    >>> mplane.model.prim_address.unparse(ip_address("2001:db8:1:33::c0:ffee"))
    '2001:db8:1:33::c0:ffee'

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

    >>> from datetime import datetime
    >>> import mplane.model   
    >>> mplane.model.prim_time.parse("2013-07-30 23:19:42")
    datetime.datetime(2013, 7, 30, 23, 19, 42)
    >>> mplane.model.prim_time.unparse(datetime(2013, 7, 30, 23, 19, 42))
    '2013-07-30 23:19:42.000000'
    >>> mplane.model.prim_time.parse("now")
    mplane.model.time_present
    >>> mplane.model.prim_time.parse("-inf")
    mplane.model.time_past
    >>> mplane.model.prim_time.parse("whenever")
    mplane.model.time_whenever

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
            dt.replace(tzinfo=timezone.utc)
            return dt
    
    def unparse(self, val):
        if val is None:
            return VALUE_NONE
        if isinstance(val, datetime):
            val.replace(tzinfo=timezone.utc)
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
            _element_registry[elem.name] = elem

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

    def met_by(self, val):
        """Determine if this constraint is met by a given value."""
        return True

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

def parse_constraint(prim, sval):
    if sval == CONSTRAINT_ALL:
        return constraint_all
    elif sval.find(CONSTRAINT_RANGESEP) > 0:
        return RangeConstraint(prim=prim, sval=sval)
    else:
        return SetConstraint(prim=prim, sval=sval)

def test_constraints():
    """test range and set constraints"""

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
    assert str(sc) == "10.0.27.100,10.0.28.103"


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
        self._constraint = constraint_all
        if val is not None:
            self.set_value(val)

    def __repr__(self):
        return "<Parameter "+str(self)+" "+repr(self._prim)+\
               " constraint "+str(self._constraint)+\
               " value "+repr(self._val)+" >"

    def has_value(self):
        return self._val is not None

    def set_value(self, val):
        if instanceof(val, str):
            val = self._prim.parse(val)

        if self._constraint.met_by(val):
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

class Metavalue(Element):
    """
    A Metavalue is an element which can take an unconstrained value.
    Metavalues are used in statement metadata sections.

    """
    def __init__(self, parent_element, val):
        super(Metavalue, self).__init__(parent_element._name, parent_element._prim)
        self._constraint = constraint_all
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
        super(Parameter, self).__init__(parent_element._name, parent_element._prim)
        self._vals = []

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
    Common implementation superclass of all mPlane Statements.
    Use Capability, Specification, and ResultSet instead.

    """
    def __init__(self, dictval=None, verb=VERB_MEASURE):
        super(Statement, self).__init__()
        #Make a blank statement
        self._params = collections.OrderedDict()
        self._metadata = collections.OrderedDict()
        self._resultcolumns = collections.OrderedDict()
        if dictval is not None:
            self.from_dict(dictval)
        else:
            self._verb = verb;
 
    def kind_str(self):
        raise NotImplementedError("Cannot instantiate a raw Statement")

    def validate(self):
        raise NotImplementedError("Cannot instantiate a raw Statement")

    def add_parameter(self, elem_name, constraint_str=CONSTRAINT_ALL, val=None):
        """Programatically add a parameter to this statement."""
        self._params[elem_name] = Parameter(element(elem_name), 
                                  constraint=parse_constraint(constraint_str),
                                  val = val)

    def add_metadata(self, elem_name, val):
        """Programatically add a metadata element to this statement."""
        self._metadata[elem_name] = Metavalue(element(elem_name), val)

    def add_result_column(self, elem_name):
        """Programatically add a result column to this Statement."""
        self._resultcolumns[elem_name] = ResultColumn(element(elem_name))

    def count_parameters(self):
        """Return the number of parameters in this Statement"""
        return len(self._parameters)

    def count_metadata(self):
        """Return the number of metavalues in this Statement"""
        return len(self._metadata)

    def count_result_columns(self):
        """Return the number of result columns in this Statement"""
        return len(self._resultcolumns)

    def count_result_rows(self):
        """Return the number of result rows in this Statement"""
        return functools.reduce(max, 
                   [len(col) for col in self.results._resultcolumns()], 0)

    def _result_rows(self):
        rows = []
        for row_index in range(count_result_rows()):
            row = []
            rows.append(row)
            for col in self.results.values():
                try:
                    valstr = col.prim.unparse(col[row_index])
                except IndexError:
                    valstr = NULLVALUE
                row.append(valstr)
        return rows

    def to_dict(self):
        """
        Convert a Statement to a dictionary 
        (for further conversion to JSON or YAML)

        """
        d = {}
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

        return d

    def _params_from_dict(self, d):
        """
        Fill in parameters from a dictionary; used internally.
        The default implementation interprets dictionary values
        as parameter values.
        """
        for (k, v) in d.items():
            self.add_parameter(k, val=v)

    def from_dict(self, d):
        """
        Fill in this Statement with values from a dictionary
        produced with to_dict (i.e., as taken from JSON or YAML).

        """
        self._verb = d[self.kind_str()]

        if SECTION_PARAMETERS in d:
            self._params_from_dict(d[SECTION_PARAMETERS])

        if SECTION_METADATA in d:
            for (k, v) in d[SECTION_METADATA].items():
                self.add_metadata(k, v)

        if SECTION_RESULTS in d:
            for (k, v) in d[SECTION_RESULTS].items():
                self.add_result_column()

        
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
        if dictval is not None:
            super(Capability, self).__init__(dictval=dictval)
        else:
            super(Capability, self).__init__(verb=verb)

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
            self.add_parameter(k, constraint_str=v)

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
        if dictval is not None:
            super(Specification, self).__init__(dictval=dictval)
        else:
            super(Specification, self).__init__(verb=verb)
            if capability is not None:
                self._verb = capability._verb
                self._params = capability._params
                self._metadata = capability._metadata
                self._resultcolumns = capability._resultcolumns

    def kind_str(self):
        return KIND_SPECIFICATION

    def validate(self):
        pval = functools.reduce(operator.__and__, 
                        (p.has_value() for p in self._params.values()),
                        True)

        if (not pval) or (self.count_result_rows() > 0):
            raise ValueError("Specifications must have parameter values.")

    def set_parameter_value(self, elem_name, value):
        """
        Programatically set a value for a parameter on this Specification.
        Used to fill values in on Specifications derived from Capabilities.

        """
        elem = self._params[elem_name]
        elem.set_value(value)

class Result(Statement):
    """docstring for Result"""
    def __init__(self, dictval=None, statement=None, verb=VERB_MEASURE):
        if dictval is not None:
            super(Result, self).__init__(dictval=dictval)
        else:
            super(Result, self).__init__(verb=verb)
            if statement is not None:
                self._verb = statement._verb
                self._params = statement._params
                self._metadata = statement._metadata
                self._resultcolumns = statement._resultcolumns

    def kind_str(self):
        return KIND_SPECIFICATION

    def validate(self):
        pval = functools.reduce(operator.__and__, 
                        (p.has_value() for p in self._params.values()),
                        True)

        if (not pval) or (self.count_result_rows() > 0):
            raise ValueError("Specifications must have parameter values.")

    def from_dict(self, d):
        """
        Fill in this Statement with values from a dictionary
        produced with to_dict (i.e., as taken from JSON or YAML).
        Result's version also fills in result values.

        """
        super(Result,self).from_dict(d)

        column_key = list(self.results.keys())

        if SECTION_RESULTVALUES in d:
            for i, row in enumerate(d[SECTION_RESULTVALUES]):
                for j, val in enumerate(row):
                    self._resultcolumns[column_key[j]][i] = val

#######################################################################
# Notifications
#######################################################################

class Notification(object):
    """docstring for Notification"""
    def __init__(self, arg):
        super(Notification, self).__init__()
        self.arg = arg

class Receipt(Notification):
    """docstring for Receipt"""
    def __init__(self, dictval=None, statement=None):
        super(Receipt, self).__init__()
        self.arg = arg

class Redemption(Notification):
    """docstring for Redemption"""
    def __init__(self, dictval=None, receipt=None):
        super(Redemption, self).__init__()
        self.arg = arg

class Indirection(Notification):
    """docstring for Indirection"""
    def __init__(self, arg):
        super(Indirection, self).__init__()
        self.arg = arg

class Withdrawal(Notification):
    """docstring for Withdrawal"""
    def __init__(self, dictval=None, capability=None):
        super(Withdrawal, self).__init__()
        self.arg = arg
        
class Interrupt(Notification):
    """docstring for Interrupt"""
    def __init__(self, arg):
        super(Interrupt, self).__init__()
        self.arg = arg