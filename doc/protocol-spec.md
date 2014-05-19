
# mPlane Protocol Specification

- - -
__ed. Brian Trammell <trammell@tik.ee.ethz.ch>, revision in progress of 19 May 2014__
- - -

This document defines the present revision of the mPlane architecture for
coordination of heterogeneous network measurement components: probes and
repositories that measure, analyze, and store aspects of the network. The
architecture is defined in terms of a single protocol, described in this
document, used between __clients__ (which request measurements and analyses)
and __components__ (which perform them). 

Sets of components are organized
into measurement infrastructures by association with a __supervisor__, which
acts as both a client (to the components it supervises) and a component (to the
clients it serves), and provides application-specific decomposition of specifications and composition of results. This arrangement is shown below, 
and further described in the rest of the document. The _capability - specification - result_ cycle in this diagram comprises the mPlane protocol.

![Figure 1](./arch-overview.png)

This document borrows heavily from mPlane project [Deliverable 1.3](https://www.ict-mplane.eu/sites/default/files//public/public-page/public-deliverables//697mplane-d13.pdf), of 31 October 2013, by B. Trammell, M. Mellia, A. Finamore, S. Traverso, T. Szemethy, B. Szabó, R. Winter, M. Faath, D. Rossi, B. Donnet, F. Invernizzi, and D. Papadimitriou. Updates to the present state of the mPlane protocol are in progress.

## mPlane Architecture

### Principles

First, considering the wide variety of measurement tools we'd like to 
integrate into the mPlane platform, we realised relatively early that distinctions 
among types of tools at an architectural level are somewhat artificial. The set of
capabilities that advertise what a tool can do define what that tool is. Therefore, 
_anything_ that publishes capabilities and makes services available according to 
them using the protocol described in this document is a __component__ and _anything_ 
that uses those capabilities is a __client__.

Given the heterogeneity of the measurement tools and techniques applied, and the
heterogeneity of component management, especially in large-scale measurement 
infrastructures, reliably stateful management and control would imply 
significant overhead at the supervisors and/or significant measurement control 
overhead on the wire to maintain connectivity among components and to resynchronize 
the system after a partial disconnection event or component failure.

A second architectural principle is therefore __state distribution__: by
explicitly acknowledging that each control interaction is best-effort in any
case, and keeping explicit information about each measurement in all messages
relevant to that measurement, the state of the measurements is in effect
distributed among all components, and resynchronization happens implicitly as
part of message exchange. The failure of a component during a large scale
measurement can therefore be accounted for after the fact. Concretely, this i
mplies that each capability, specification, and result must contain enough 
information to intepret in isolation.

This emphasis on distributed state and heterogeneity, along with the
flexibility of the representations and session protocols used with the
platform, makes the mPlane protocol applicable to a wide range of scales,
from resource- and connectivity-limited probes such as smartphones and
customer-premises equipment (CPE) like home routers up to large-scale backbone
measurement devices and repositories backed by database and compute clusters.

mPlane defines a self-describing, error- and delay-tolerant remote
procedure call protocol: each capability exposes an entry point in the API
provided by the component; each statement embodies an API call; and each result
returns the results of an API call. The final key principle in the mPlane
architecture, which allows it to be applied to the problem of heterogeneous
measurement interoperability, is __type primacy__. A measurement is
completely described by the type of data it produces, in terms of schemas
composed of elements. The key to measurement interoperability in mPlane is
therefore the definition of a type __registry__.

### Components and Clients

A component is any entity which implements the mPlane protocol specified
within this document, advertises its capabilities and accepts 
specifications which request the use of those capabilities. The measurements,
analyses, storage facilities and other services provided by a component are
completely defined by its capabilities.

Conversely, a client is any entity which implements the mPlane protocol, 
receives capabilities published by one or more components, and sends 
specifications to those component(s) to those components to perform measurements
and analysis.

### Supervisors and Federation

An entity which implements both the client and component interfaces can be used to build and federate infrastructures of mPlane components. The supervisor is responsible for collecting capabilities from a set of components, and providing
capabilities based on these to its clients. Application-specific algortihms at the supervisor aggregate the lower-level capabilities provided by these components into
higher-level capabilities exposed to its clients. 

Since a supervisor allows the aggregation of control, it is in the general case expected to implement access control based on the identity information provided by the secure session protocol (HTTPS or TLS) used for communication between the supervisor and its clients.

The set of components which respond to specifications from a single supervisor
is referred to as an mPlane __domain__. Interdomain measurement is supported
by federation among supervisors: a local supervisor delegates measurements in a remote domain to that domain's supervisor. 

## Protocol Information Model: Type Registry

A type registry makes up the vocabulary by which mPlane components and clients can express the meaning of parameters, metadata, and result columns for mPlane statements. A registry is represented as a JSON object with the following keys:

- __registry-format__: currently `mplane-0`, determines the revision of the registry format.
- __registry-uri__: the URI identifying the registry. The URI must be dereferenceable to retrieve the canonical version of this registry
- __registry-revision__: a serial number starting with 0 and incremented with each revision, 
- __includes__: a list of URLs to retrieve additional registries from. Included registries will be evaluated in depth-first order, and elements with identical names will be replaced by registries parsed later.
- __elements__: a list of objects, each of which has the following three keys:
    - __name__: The name of the element
    - __prim__: The name of the primitive type of the element, from the list of primitives below
    - __desc__: An English-language description of the meaning of the element.

An example registry with two elements and no includes follows:

```
{ "registry-format": "mplane-0",
  "registry-uri", "http://ict-mplane.eu/registry/0",
  "registry-revision": 0,
  "includes": [],
  "elements": [
      { "name": "full.structured.name",
        "prim": "string",
        "desc": "A representation of foo..."
      },
      { "name": "another.structured.name",
        "prim": "string",
        "desc": "A representation of bar..."
      },
  ]
}
```

__Fully qualified__ element names consist of the element's name as an anchor after the URI from which the element came, e.g. `http://ict-mplane.eu/registry/0#full.structured.name`. Elements within the type registry are considered globally equal based on their fully qualified names. However, within a given mPlane message, elements are considered equal based on unqualified names.

### Structured Element Names

To ease understanding of mPlane type registries, element names are by default _structured_; that is, an element name is made up of the following structural parts in order, separated by the dot ('.') character:

- __basename__: exactly one, the name of the property the element specifies or measures. All elements with the same basename measure the describe the same basic property. For example, `source` represents the source address of a packet, flow, etc, and `delay` represents the measured delay of an operation.
- __modifier__: zero or more, additional information differentiating elements with the same basename from each other. Modifiers may associate the element with a protocol layer, or a particular variety of the property named in the basename. All elements with the same basename and modifiers refer to exactly the same property. Examples for the `delay` basename include `oneway` and `twoway`, differentiating whether a delay refers to the path from the source to the destination or from the source to the source via the destination; and `icmp` and `tcp`, describing the protocol used to measure the delay.
- __units__: zero or one. Present if the quantity can be measured in different units.
- __aggregation__: zero or one, if the property is a metric derived from multiple singleton measurements. Supported aggregations are:
  - `min`: minimum value
  - `max`: maximum value
  - `mean`: mean value
  - `sum`: sum of values
  - `NNpct` (where NN is a two-digit number 01-99): percentile
  - `median`: shorthand for and equivalent to `50pct`.
  - `count`: count of values aggregated

When mapping mPlane structured names into contexts in which dots have special meaning, the dots may be replaced by underscores ('_'). When using external type registries (e.g. the IPFIX Information Element Registry), element names are not necessarily structured.

We anticipate the development of an `mplane-1` revision of the registry format which directly supports simpler expression of structured names.


### Primitive Types

The mPlane protocol supports the following primitive types for elements in the type registry:

- __string__: a sequence of UTF-8 encoded characters
- __natural__: an unsigned integer
- __real__: a real (floating-point) number
- __bool__: a true or false (boolean) value
- __time__: a timestamp, expressed in terms of UTC. The precision of the timestamp is taken to be unambiguous based on its representation.
- __address__: an identifier of a network-level entity, including an address family. The address family is presumed to be 
- __url__: a uniform resource locator

## Protocol Information Model: Message Types

### Statement

Workflows in mPlane are built around the _capability - specification - result_ cycle. Capabilities, specifications, and results are kinds of __statements__: a capability is a statement that a component can perform some action (generally a measurement); a specification is a statement that a client would like a component to perform the action advertised in a capability; and a result is a statement that a component measured a given set of values at a given point in time according to a specification.

See the following subsection for details of the __sections__ of each statement.

### Capability

A __capability__ is a statement of a component's ability to perform a specific operation, conveyed from a component to a client. It does not represent a guarantee that the specific operation can or will be performed at a specific point in time.

### Withdrawal *(not yet implemented)*


### Specification

A __specification__ is a statement that a component should perform a specific
operation, conveyed from a client to a component. It can be
conceptually viewed as a capability whose parameters have been filled in with
values.

### Result

A __result__ is a statement produced by a component that a particular measurement
was taken and the given values were observed, or that a particular operation or
analysis was performed and a the given values were produced. It can be
conceptually viewed as a specification whose result columns have been filled in with
values. Note that, in keeping with the stateless nature of the mPlane protocol, a
result contains the full set of parameters from which it was derived.

### Receipt

A __receipt__ is returned by a component in response to specification which either:

- will never return results, as it initiated an indirect export, or 
- will not return results immediately, as the operation producing the results will have a long run time.

Receipts contain the same sections as the specification they are returned for,
with identical values and verb. A component may optionally add a __token__
section, which can be used in future redemptions and interruptions by the
client. The content of the token is an opaque string generated by the component.

### Redemption

A __redemption__ is sent from a client to a component for a previously received receipt to attempt to retrieve delayed results. It may contain only the __token__ section, or all sections of the received receipt.

### Interrupt *(not yet implemented)*

### Indirection *(not yet implemented)*

## Protocol Information Model: Message Sections

### Kind and Verb

The __verb__ is the action to be performed by the component. The following verbs are supported by the base mPlane protocol, but arbitrary verbs may be specified by applications:

- `measure`: Perform a measurement
- `query`: Query a database about a past measurement
- `collect`: Receive results via indirect export
	
In the JSON and YAML representations of mPlane messages, the verb is the value of the key corresponding to the statement's __kind__, represented as a lowercase string (e.g. `capability`, `specification`, `result` and so on.)

### Temporal Scope (When)

The `when` section of a statement contains its __temporal scope__.

A temporal scope refers to when a measurement can be run (in a Capability), when it should be run (in a Specification), or when it was run (in a Result). Temporal scopes can be either absolute or relative, and may have an optional period. They are built from ISO8601 timestamps (for absolute times), duration specifiers, and the special times ```past```, ```now```, and ```future```.

The general form of a temporal scope (in BNF-like syntax) is as follows:

```
when = <singleton> |            # A single point in time
       <range> |                # A range between two points in time
       <range> ' / ' <duration> # A range with a period

singleton = <iso8601> | # absolute singleton
            'now'       # relative singleton

range = <iso8601> ' ... ' <iso8601> | # absolute range
        <iso8601> ' + ' <duration> |  # relative range
        'now' ' ... ' <iso8061> |     # definite future
        'now' ' + ' <duration> |      # relative future
        <iso8601> ' ... ' 'now' |     # definite past
        'past ... now' |              # indefinite past
        'now ... future' |            # indefinite future
        <iso8601> ' ... ' 'future' |  # absolute indefinite future
        'past ... future' |           # forever

duration = [ <n> 'd' ] # days
           [ <n> 'h' ] # hours
           [ <n> 'm' ] # minute
           [ <n> 's' ] # seconds 

iso8601 = <n> '-' <n> '-' <n> [' ' <n> ':' <n> ':' <n> [ '.' <n> ]
```

All absolute times are __always__ given in UTC and expressed in ISO8601 format with variable precision.

In Capabilities, if a period is given it represents the _minumum_ period supported by the measurement; this is done to allow large-granularity rate limiting. If no period is given, the measurement is not periodic. Capabilities with periods can only be fulfilled by Specifications with periods.

Only absolute range temporal scopes are allowed for Results.

So, for example, an absolute range in time might be expressed as: 

`when: 2009-02-20 13:02:15 ... 2014-04-04 04:27:19`

A relative range covering three and a half days might be:
 
`when: 2009-04-04 04:00:00 + 3d12h`

In a Specification for running an immediate measurement for three hours every seven and a half minutes: 

`when: now + 3h / 7m30s` 

In a Capability noting that a Repository can answer questions about the past: 

`when: past ... now`. 

In a Specification requesting that a measurement run from a specified point in time until interrupted: 

`when: 2017-11-23 18:30:00 ... future`

### Schedule *(not yet implemented)*

### Parameters

### Result Columns

### Metadata

### Export

### Link

### Label

### Token

### Version

## Session Protocols

### JSON representation

### mPlane over HTTPS

### mPlane over SSH

## Workflows in mPlane

### Component Push

### Component Pull

## The Role of the Supervisor

### Component Registration

### Client Authentication

### Capability Composition