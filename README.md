# protocol-ri Introduction

This document describes the mPlane Protocol reference implementation in this module, as well as the protocol it implements. 

The mPlane Protocol provides control and data interchange for passive and active network measurement tasks. It is built around a simple workflow in which Capabilities are published by Components, which can accept Specifications for measurements based on these Capabilities, and provide Results, either inline or via an indirect export mechanism negotiated using the protocol. 

The reference impelementation in the module is the normative reference for the mPlane protocol until such time as it is deemed stable by the mPlane consortium (presently scheduled for November 2014), at which time the document derived from this README will contain the normative reference for the protocol.

Measurement statements are fundamentally based on schemas divided into Parameters, representing information required to run a measurement or query; and Result Columns, the information produced by the measurement or query. Measurement interoperability is provided at the element level; that is, measurements containing the same Parameters and Result Columns are considered to be of the same type and therefore comparable.

This document is under construction. 

# Using the Reference Implementation

## Core Classes

The core classes are documented using Sphinx. Sphinx documentation can be read [here](https://fp7mplane.github.io/protocol-ri).

## Designing a Component

The first step in determining how to build an mPlane component for a given measurement is determining its schema. The best way to do this is probably to look at the _output_ the component produces, together with the configuration parameters necessary to make it work.

## Building HTTP Server Components

## mPlane Client Shell

The mPlane Client Shell is a quick and dirty command line interface around a generic mPlane HTTP client. ```help``` provides low quality help. To use it:

1. ```connect <url>``` Connect to a component at the given URL; currently supported schema is ```http```. Tries to load capabilities from a list of links at the ```/capabilities``` path relative to this URL. 
2. ```listcap``` will show capablities available at the connected component, prefaced by capability indexes.
3. ```when <temporal-scope>``` sets a temporal scope for subsequent invocations; ```when``` on its own shows the current one
4. ```set <parameter> <value>``` sets a default value for parameters for subsequent invocations; ```show``` shows all current defaults with values
5. ```runcap <number>``` runs a capability by number in the ```listcap``` list. Any parameters not yet filled in by ```set``` will be prompted for. This will return either a result or receipt, depending on what the component decides to return.
6. ```redeem``` sends all pending receipts back to the component for results, if available.

Note that this is all very prerelease and nearly guaranteed to change.

# mPlane Protocol Specification

## mPlane Architecture

### Principles

### Components and Clients

### Supervisors and Federation

## Protocol Information Model: Message Types

### Statements

### Capabilities

### Specifications

### Results

### Receipts and Redemptions

### Indirections (not yet implemented)

## Protocol Information Model: Message Sections

### Type and Verb

### Temporal Scope (When)

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

All absolute times are __always__ given in UTC.

In Capabilities, if a period is given it represents the _minumum_ period supported by the measurement; this is done to allow large-granularity rate limiting. If no period is given, the measurement is not periodic. Capabilities with periods can only be fulfilled by Specifications with periods.

Only absolute range temporal scopes are allowed for Results.

So, for example, an absolute range in time might be expressed as: ```when: 2009-02-20 13:02:15 ... 2014-04-04 04:27:19```. A relative range covering three and a half days might be ```when: 2009-04-04 04:00:00 + 3d12h```. In a Specification for running an immediate measurement for three hours every seven and a half minutes: ```when: now + 3h / 7m30s```. In a Capability noting that a Repository can answer questions about the past: ```when: past ... now```. In a Specification requesting that a measurement run from a specified point in time until interrupted: ```when: 2017-11-23 18:30:00 ... future```. 

### Schedule

### Parameters

### Result Columns

### Metadata

### Export

### Link

### Label

### Version

## Session Protocols

### JSON representation

### mPlane over HTTPS

### mPlane over SSH

## Workflows in mPlane

### Component Push

### Component Pull
