
# mPlane Protocol Specification

- - -
__ed. Brian Trammell <trammell@tik.ee.ethz.ch>, revision in progress of 7 July 2014__
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

This document borrows heavily from mPlane project [Deliverable 1.3](https://www.ict-mplane.eu/sites/default/files//public/public-page/public-deliverables//697mplane-d13.pdf), of 31 October 2013, by B. Trammell, M. Mellia, A. Finamore, S. Traverso, T. Szemethy, B. Szabó, R. Winter, M. Faath, D. Rossi, B. Donnet, F. Invernizzi, and D. Papadimitriou. It will be the basis of mPlane project Deliverable 1.4. Updates to the present state of the mPlane protocol are in progress.

# mPlane Architecture

## Principles

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

## Components and Clients

A __component__ is any entity which implements the mPlane protocol specified
within this document, advertises its capabilities and accepts 
specifications which request the use of those capabilities. The measurements,
analyses, storage facilities and other services provided by a component are
completely defined by its capabilities.

Conversely, a __client__ is any entity which implements the mPlane protocol, 
receives capabilities published by one or more components, and sends 
specifications to those component(s) to those components to perform measurements
and analysis.

### Probes and Repositories

*[**Editor's Note:** define probes and repositories in general; later we can define these in terms of verbs]*

## Supervisors and Federation

An entity which implements both the client and component interfaces can be used to build and federate infrastructures of mPlane components. This __supervisor__ is responsible for collecting capabilities from a set of components, and providing
capabilities based on these to its clients. Application-specific algortihms at the supervisor aggregate the lower-level capabilities provided by these components into
higher-level capabilities exposed to its clients. 

Since a supervisor allows the aggregation of control, it is in the general case expected to implement access control based on the identity information provided by the secure session protocol (HTTPS or TLS) used for communication between the supervisor and its clients.

The set of components which respond to specifications from a single supervisor
is referred to as an mPlane __domain__. Interdomain measurement is supported
by federation among supervisors: a local supervisor delegates measurements in a remote domain to that domain's supervisor. 

Note that, since the logic for aggregating control and data for a given application is very specific to that application, there is no _generic_ supervisor implementation provided with the mPlane Reference Implementation.

# Protocol Information Model

The mPlane protocol is message-oriented, built on the representation- and session-protocol-independent exchange of messages between clients and components. 

## Element Registry

An element registry makes up the vocabulary by which mPlane components and clients can express the meaning of parameters, metadata, and result columns for mPlane statements. A registry is represented as a JSON object with the following keys:

- __registry-format__: currently `mplane-0`, determines the revision and supported features of the registry format.
- __registry-uri__: the URI identifying the registry. The URI must be dereferenceable to retrieve the canonical version of this registry
- __registry-revision__: a serial number starting with 0 and incremented with each revision to the content of the registry, 
- __includes__: a list of URLs to retrieve additional registries from. Included registries will be evaluated in depth-first order, and elements with identical names will be replaced by registries parsed later.
- __elements__: a list of objects, each of which has the following three keys:
    - __name__: The name of the element
    - __prim__: The name of the primitive type of the element, from the list of primitives below
    - __desc__: An English-language description of the meaning of the element.

An example registry with two elements and no includes follows:

```
{ "registry-format": "mplane-0",
  "registry-uri", "http://ict-mplane.eu/registry/core",
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

__Fully qualified__ element names consist of the element's name as an anchor after the URI from which the element came, e.g. `http://ict-mplane.eu/registry/core#full.structured.name`. Elements within the type registry are considered globally equal based on their fully qualified names. However, within a given mPlane message, elements are considered equal based on unqualified names.

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
- __address__: an identifier of a network-level entity, including an address family. The address family is presumed to be implicit in the format of the message, or explicitly stored.
- __url__: a uniform resource locator

## Message Types

Workflows in mPlane are built around the _capability - specification - result_ cycle. Capabilities, specifications, and results are kinds of __statements__: a capability is a statement that a component can perform some action (generally a measurement); a specification is a statement that a client would like a component to perform the action advertised in a capability; and a result is a statement that a component measured a given set of values at a given point in time according to a specification.

Messages outside this nominal cycle are referred to as __notifications__, as they notify clients or components of conditions within the measurement infrastructure itself, as opposed to containing informations about measurements or observations.

Messages may also be grouped together into a single message, referred to as an __envelope__.

The following types of messages are supported by the mPlane protocol.

### Capability

A __capability__ is a statement of a component's ability and willingness to perform a specific operation, conveyed from a component to a client. It does not represent a guarantee that the specific operation can or will be performed at a specific point in time.

### Withdrawal *(not yet implemented)*

A __withdrawal__ is a statement of a component's inability or unwillingness to perform a specific operation. It cancels a previously advertised capability.

### Specification

A __specification__ is a statement that a component should perform a specific
operation, conveyed from a client to a component. It can be
conceptually viewed as a capability whose parameters have been filled in with
values.

### Interrupt

An __interrupt__ is a statement that a component should stop performing a specific operation, conveyed from client to component. It cancels a previously sent specification.

### Result

A __result__ is a statement produced by a component that a particular measurement
was taken and the given values were observed, or that a particular operation or
analysis was performed and a the given values were produced. It can be
conceptually viewed as a specification whose result columns have been filled in with
values. Note that, in keeping with the stateless nature of the mPlane protocol, a
result contains the full set of parameters from which it was derived.

### Receipt

A __receipt__ is returned instead of a result by a component in response to a specification which either:

- will never return results, as it initiated an indirect export, or 
- will not return results immediately, as the operation producing the results will have a long run time.

Receipts contain the same sections as the specification they are returned for,
with identical values and verb. A component may optionally add a __token__
section, which can be used in future redemptions and interruptions by the
client. The content of the token is an opaque string generated by the component.

### Redemption

A __redemption__ is sent from a client to a component for a previously received receipt to attempt to retrieve delayed results. It may contain only the __token__ section, or all sections of the received receipt.

### Indirection *(not yet implemented)*

An __indirection__ is returned instead of a result by a component to indicate that the client should contact another component for the desired result.

### Exception

An __exception__ is sent from a client to a component or from a component to a client to signal an exceptional condition within the infrastructure itself.

### Envelope

An __envelope__ is used to contain other messages. Currently, envelopes are intended to be used for two distinct purposes:

- To return multiple Results for a single receipt or specification if appropriate (e.g., if a specification has run repeated instances of a measurement on a schedule).
- To group multiple capabilities together within a single message (e.g., all the capabilities a given component has).

However, it is legal to group any kind of message in an envelope.

## Message Sections

Each message is made up of sections, as described in the subsection below. The following table shows the presence of each of these sections in each of the message types supported by mPlane: "req." means the section is required, "opt." means it is optional; see the subsection on each message section for details.

| Section         | Capability | Specification | Result | Receipt     | Envelope |
|                 | Withdrawal |               |        | Redemption  |          |
|                 |            |               |        | Interrupt   |          |
|-----------------|------------|---------------|--------|-------------|----------|
| Verb            | req.       | req.          | req.   | req.        |          |
| Content Type    |            |               |        |             | req.     |
| `version:`      | req.       | req.          | req.   | req.        | req.     |
| `registry:`     | req.       | req.          | req.   | opt.        |          |
| `label:`        | opt.       | opt.          | opt.   | opt.        | opt.     |
| `when:`         | req.       | req.          | req.   | req.        |          |
| `schedule:`     |            | opt.          |        |             |          |
| `parameters:`   | req./token | req.          | req.   | opt./token  |          |
| `metadata:`     | opt./token | opt.          | opt.   | opt./token  |          |
| `results:`      | req./token | req.          | req.   | opt./token  |          |
| `resultvalues:` |            |               | req.   |             |          |
| `export:`       | opt.       | opt.          | opt.   | opt.        |          |
| `link:`         | opt.       |               |        |             |          |
| `token:`        | opt.       | opt.          | opt.   | opt.        |          |
| `contents:`     |            |               |        |             | req.     |

### Kind and Verb

The __verb__ is the action to be performed by the component. The following verbs are supported by the base mPlane protocol, but arbitrary verbs may be specified by applications:

- `measure`: Perform a measurement
- `query`: Query a database about a past measurement
- `collect`: Receive results via indirect export
	
In the JSON and YAML representations of mPlane messages, the verb is the value of the key corresponding to the statement's __kind__, represented as a lowercase string (e.g. `capability`, `specification`, `result` and so on).

Within the Reference Implementation, the primary difference between `measure` and `query` is that the temporal scope of a `measure` specification is taken to refer to when the measurement should be scheduled, while the temporal scope of a  `query` specification is taken to refer to the time window (in the past) of a query.

Envelopes have no verb; instead, the value of the `envelope` key is the kind of messages the envelope contains, or `message` if the envelope contains a mixture of kinds of messages.

### Version

The `version` section contains the version of the mPlane protocol to which the message conforms, as an integer serially incremented with each new protocol revision. This section is required in all messages. This document describes version 0 of the protocol; the final revision of this document will describe version 1.

### Registry

The `registry` section contains the URL identifying the element registry used by this message, and from which the registry can be retrieved. This section is required in all messages containing element names (statements, and receipts/redemptions/interrupts not using tokens for identification; see the `token` section below). The default core registry for mPlane is identified by `http://ict-mplane.eu/registry/core`. *[**Editor's Note**: this is not yet the case, get the core registry done and make sure it's available there.]*

### Label

The `label` section of a statement contains a human-readable label identifying it, intended solely for use when displaying information about messages in user interfaces. Results, receipts, redemptions, and interrupts inherit their label from the specification from which they follow; otherwise, client and component software can arbitrarily assign labels . The use of labels is optional in all messages, but as labels do greatly ease human-readability of arbitrary messages within user interfaces, their use is recommended.

mPlane clients and components should __never__ use the label as a unique identifier for a message, or assume any semantic meaning in the label -- the test of message equality and relatedness is always based upon the schema and values as in the section on message uniqueness and idempotence below.

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

*[**Editor's Note**: determine which definition to use for this before writing this section; we need a contribution from FHA here.]*

### Parameters

The `parameters` section of a message contains an ordered list of the __parameters__ for a given measurement: values which must be provided by a client to a component in a specification to convey the specifics of the measurement to perform. Each parameter in an mPlane message is a key-value pair, where the key is the name of an element from the element registry. In specifications and results, the value is the value of the parameter. In capabilities, the value is a __constraint__ on the possible values the component will accept for the parameter in a subsequent specification.

Four kinds of constraints are currently supported for mPlane parameters:

- No constraint: all values are allowed. This is signified by the special constraint string '`*`'.
- Single value constraint: only a single value is allowed. This is intended for use for capabilities which are conceivably configurable, but for which a given component only supports a single value for a given parameter due to its own out-of-band configuration or the permissions of the client for which the capability is valid.
- Set constraint: multiple values are allowed, and are explicitly listed, separated by the '`,`' character.
- Range constraint: multiple values are allowed, between two ordered values, separated by the special string '`...`'. Range constraints are inclusive.

Future versions of the protocol may support additional types or combinations constraints. *[**Editor's Note**: we should also support networks with netmasks as an implicit range, but we don't yet.]*

Values and values in constraints must be a representation of an instance of the primitive type of the associated element.

### Result Columns

The `results` section contains an ordered list of __result columns__ for a given measurement: values which will be returned by the measurement. The result columns are identified the names of the elements from the element registry.

### Result Values

The `resultvalues` section contains an ordered list of ordered lists (or, rather, a two dimensional array) of values of results for a given measurement, in row-major order. The columns in the result values appear in the same order as the columns in the `results` section. Result values appear only in result messages.

Values for each column must be a representation of an instance of the primitive type of the associated result column element.

### Metadata

The `metadata` section contains message __metadata__: key-value pairs associated with a capability inherited by its specification and results. Metadata can also be thought of as immutable parameters. This is intended to represent information which can be used to make decisions at the client as to the applicability of a given capability (e.g. details of algorithms used or implementation-specific information) as well as to make adjustments at post-measurement analysis time when contained within results.

### Export

The `export` section contains a URL or partial URL for __indirect export__. Its meaning depends on the kind and verb of the message: 

- For capabilities with the `collect` verb, the `export` section contains the URL of the collector which can accept indirect export for the schema defined by the `parameters` and `results` sections of the capability, using the protocol identified by the URL's schema. If the URL schema is `mplane-http`, result messages matching the capability can be directly sent to the collector at the given URL via HTTP `POST`. Otherwise, the binding between elements in the capability's registry and representations of these elements in the export protocol is protocol-specific.
- For capabilities with any verb other than `collect`, the `export` section contains either the URL of a collector to which the component can indirectly export results, or a URL schema identifying a protocol over which the component can export to arbitrary collectors.
- For specifications with any verb other than `collect`, the `export` section contains the URL of a collector to which the component should indirectly export results. A receipt will be returned for such specifiations.

Capabilities with an `export` section can only be used by specifications with a matching `export` section. If a component can indirectly export or indirectly collect using multiple protocols, each of those protocols must be identified by its own capability.

*[**Editor's Note**: This text implies that the export section of a statement is part of the statement's unique hash; this is not the case in the implementation. Fix this.]*

### Link

The `link` section contains the URL to which messages in the next step in the workflow can be send, providing __indirection__ in capability and indirection messages. The link URL must currently have the schema `mplane-http`, and refers to posting of messages via HTTP `POST`.

If present in a capability, the client should `POST` specifications for the given capability to the component at the URL given in order to use the capability.

An indirection message can be returned for a specification by a component, directing the client to send the specification to the component at the URL given in the link in order to retrieve results or initiate measurement.

### Token

*[**Editor's Note:** the reference implementation does not yet handle tokens as described here. Fix this.]*

The `token` section contains an arbitrary string by which a message may be identified in subsequent communications in an abbreviated fashion. Unlike labels, tokens are not necessarily intended to be human-readable; instead, they provide a way to reduce redundancy on the wire by replacing the parameters, metadata, and results sections in messages within a workflow, at the expense of requiring more state at clients and components. Their use is optional. 

Tokens are scoped to the association between the component and client in which they are first created.

If a capability contains a token, it may be subsequently withdrawn by the same component using a withdrawal containing the token instead of the parameters, metadata, and results sections.

If a specification contains a token, it must be retained by the component, and all results and receipts following from the specification must contain the same token. A specification containing a token may be answered by the component with a receipt containing the token instead of the parameters, metadata, and results sections. A specification containing a token may likewise be interrupted by the client with an interrupt containing the token.

If a receipt contains a token, it may be redeemed by the same client using a redemption containing the token instead of the parameters, metadata, and results sections.

### Contents

The `contents` section appears only in envelopes, and is an ordered list of messages. If the envelope's kind identifies a message kind, the contents may contain only messages of the specified kind, otherwise if the kind is `message`, the contents may contain a mix of any kind of message.

## Message Uniqueness and Idempotence

*[**Editor's Note:** Verify that this is what the RI does, and fix the RI to comply.]*

Messages in the mPlane protocol are intended to support __state distribution__: capabilities, specifications, and results are meant to be complete declarations of the state of a given measurement. In order for this to hold, it must be possible for messages to be uniquely identifiable, such that duplicate messages can be recognized. With one important exception, messages are _idempotent_: the receipt of a duplicate message at a client or component is a null operation.

### Message Schema

The combination of elements in the `parameters` and `results` sections, together with the registry from which these elements are drawn, is referred to as a message's __schema__. The schema of a measurement can be loosely thought of as the definition of the table that the message defines.

### Message Identity

A message's identity is composed of its schema, together with its temporal scope, metadata, parameter values, and indirect export properties. Concretely, the full content of the `registry`, `when`, `parameters`, `metadata` `results`, and `export` sections taken together comprise the message's identity. 

One convenience feature complicates this somewhat: when the temporal scope is not absolute, multiple specifications may have the same literal temporal scope but refer to different measurements. In this case, the current time at the client or component can be taken as part of the message's identity as well.

Implementations may use hashes over the values of the message's identity sections to uniquely identify messages.

# Representations and Session Protocols

The mPlane protocol is defined as an abstract data model in order to support multiple representations and session protocols. The canonical representation supported by the present reference implementation involves JSON objects transported via HTTP over TLS (HTTPS). 

## JSON representation

In the JSON representation, an mPlane message is a JSON object, mapping sections by name to their contents. The name of the message type is a special section key, which maps to the message's verb, or to the message's content type in the case of an envelope.

Each section name key in the object has a value represented in JSON as follows:

- `version` : an integer identifying the mPlane message version.
- `registry` : a URL identifying the registry from which element names are taken.
- `label` : an arbitrary string.
- `when` : a string containing a temporal scope, as described in the "Temporal Scope" subsection above.
- `schedule` : a schedule object, as described in the "Schedule" subsection above.
- `parameters` : a JSON object mapping (non-qualified) element names, either to constraints or to parameter values, as appropriate, and as described in the "Parameters" subsection above.
- `metadata` : a JSON object mapping (non-qualified) element names to metadata values.
- `results` : an array of element names.
- `resultvalues` : an array of arrays of element values in row major order, where each row array contains values in the same order as the element names in the `results` section.
- `export` : a URL for indirect export
- `link` : a URL for message indirection
- `token` : an arbitrary string
- `contents` : an array of objects containing messages

### Textual representations of element values

Each primitive type is represented as a value in JSON as follows, following the [Textual Representation of IPFIX Abstract Data Types](http://tools.ietf.org/html/draft-ietf-ipfix-text-adt-06).

Natural and real values are represented in JSON using native JSON representation for numbers.

Booleans are represented by the reserved words `true` and `false`. 

Strings and URLs are represented as JSON strings subject to JSON escaping rules.

Addresses are represented as dotted quads for IPv4 addresses as they would be in URLs, and canonical IPv6 textual addresses as in section 2.2 of [RFC 4291](http://tools.ietf.org/html/4291) as updated by section 4 of [RFC 5952](http://tools.ietf.org/html/4291). When representing networks, addresses may be suffixed as in CIDR notation, with a '`/`' character followed by the mask length in bits n, provided that the least significant 32 − n or 128 − n bits of the address are zero, for IPv4 and IPv6 respectively.

Timestamps are represented in [RFC 3339](http://tools.ietf.org/html/3339) and ISO 8601, with two important differences. First, all mPlane timestamps are are expressed in terms of UTC, so time zone offsets are neither required nor supported, and are always taken to be 0. Second, fractional seconds are represented with a variable number of digits after an optional decimal point after the fraction.

## mPlane over HTTPS

The default session protocol for mPlane messages is HTTP over TLS with mutual authentication. An mPlane component may act either as a TLS server or a TLS client, depending on the workflow. When an mPlane client initiates a connection to a component, it acts as a TLS client, and must present a client certificate, which the component will verify against its allowable peers before proceeding; and the component acts as a TLS server, and must present a server certificate, which the client will verify against its allowable peers before proceeding. When an mPlane component initiates a connection to a client (or, more commonly, the client interface of a supervisor), this arragmenent is reversed: the component acts as a TLS client, the client as a TLS server, and mutual authentication is still mandatory.

For components with simple authorization policies, the ability to establish a connection
may imply authorization to continue with any capability offered by the component.
For components with more complex policies, the identity of the peer's
certificate may be mapped to an internal identity on which access control
decisions can be made. Details are given in the Authentication and Authorization section below.

Since HTTPS is not a bidirectional protocol (i.e., clients send requests, while
servers send responses), while mPlane envisions a bidirectional message channel, it is necessary to specify mappings between this bidirectional message channel and the sequence of HTTPS requests and responses for each deployment scenario. These mappings are given in the Workflows section below.Note that in a given mPlane domain, any or all of these mappings may be used simultaneously.

When sending mPlane messages over HTTPS, the Content-Type of the message indicates the message representation. The MIME Content-Type for mPlane messages using JSON representation over HTTPS is `application/x-mplane+json`. When sending exception notifications in HTTP response bodies, the response should contain an appropriate 400 (Client Error) or 500 (Server Error) response code. When sending indirections, the response should contain an appropriate 300 (Redirection) response code. Otherwise, the response should contain response code 200 OK.

## mPlane over SSH

Though not presently implemented by the reference implementation, the mPlane protocol specification is designed such that it can also use the Secure Shell (SSH) protocol as a session layer. In the SSH binding, a connection initiator (SSH client) identifies itself with an RSA, DSA, or ECDSA public key, which is bound to a specific identity, and the connection responder (SSH server) identifies itself with a host public key. As with TLS certificates, these are mapped to an internal identity on which access control decisions can be made.

Once an SSH connection is established, mPlane messages can be exchanged bidirectionally over the channel.

Implementation and further specification of SSH as a session layer is a matter for future work.

# Authentication and Authorization

*[**Editor's Note**: we need a contribution from SSB here]*

# Workflows

*[**Editor's Note**: frontmatter]*

## Client-Initiated

*[**Editor's Note**: describe]*

![Figure 2](./client-initiated.png)

### Capability Discovery

*[**Editor's Note**: describe]*

![Figure 3](./client-initiated-discovery.png)

## Component-Initiated

*[**Editor's Note**: describe]*

![Figure 4](./component-initiated.png)

## Indirect Export

*[**Editor's Note**: describe]*

![Figure 5](./indirect-export.png)

# The Role of the Supervisor

From the point of view of the mPlane protocol, a supervisor is merely a combined component and client. The logic binding client and component interfaces within the supervisor is application-specific, as it involves the following operations according to the semantics of each application:

- translating lower-level capabilities from subordinate components into higher-level (composed) capabilities, according to the application's semantics
- translating higher-level specifications from subordinate components into lower-level (decomposed) specifications
- relaying or aggregating results from 

The workflows on each side of the supervisor are independent; indeed, the supervisor itself will generally respond to client-initiated exhanges, and An example combination of workflows at a supervisor is shown below:

![Figure 6](./supervisor-example.png)

Here, *[**Editor's Note** discuss this]*

## Component Registration

## Client Authentication

## Capability Composition and Specification Decomposition

*[**Editor's Note**: describe]*

An example is shown below. Here,  *[**Editor's Note** discuss this]*

![Figure 7](./comp-decomp-example.png)