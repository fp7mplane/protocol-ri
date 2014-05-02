# protocol-ri Introduction

This module contains the mPlane protocol reference implementation.

The core classes in the `mplane.model` and `mplane.scheduler` packages are documented using Sphinx; reasonably current Sphinx documentation can be read online [here](https://fp7mplane.github.io/protocol-ri).

The draft protocol specification is available in [doc/protocol-spec.md](https://github.com/fp7mplane/protocol-ri/blob/develop/doc); current work is in the `develop` branch.

The mPlane Protocol provides control and data interchange for passive and active network measurement tasks. It is built around a simple workflow in which __Capabilities__ are published by __Components__, which can accept __Specifications__ for measurements based on these Capabilities, and provide __Results__, either inline or via an indirect export mechanism negotiated using the protocol. 

Measurement statements are fundamentally based on schemas divided into Parameters, representing information required to run a measurement or query; and Result Columns, the information produced by the measurement or query. Measurement interoperability is provided at the element level; that is, measurements containing the same Parameters and Result Columns are considered to be of the same type and therefore comparable.

# Using the Reference Implementation

## Core Classes

The core classes are documented using Sphinx. Sphinx documentation can be read [here](https://fp7mplane.github.io/protocol-ri).

## Designing a Component

The first step in determining how to build an mPlane component for a given measurement is determining its schema. The best way to do this is to look at the _output_ the component produces, together with the configuration parameters necessary to make it work.

## mPlane Client Shell

The mPlane Client Shell is a quick and dirty command line interface around a generic mPlane HTTP client. ```help``` provides low quality help. To use it:

1. ```connect <url>``` Connect to a component at the given URL; currently supported schema is ```http```. Tries to load capabilities from a list of links at the ```/capabilities``` path relative to this URL. 
2. ```listcap``` will show capablities available at the connected component, prefaced by capability indexes.
3. ```when <temporal-scope>``` sets a temporal scope for subsequent invocations; ```when``` on its own shows the current one
4. ```set <parameter> <value>``` sets a default value for parameters for subsequent invocations; ```show``` shows all current defaults with values
5. ```runcap <number>``` runs a capability by number in the ```listcap``` list. Any parameters not yet filled in by ```set``` will be prompted for. This will return either a result or receipt, depending on what the component decides to return.
6. ```redeem``` sends all pending receipts back to the component for results, if available.

Note that this is all very prerelease and nearly guaranteed to change.


## Building HTTP Server Components

_this will probably change when moving to a CLI-based httpsrv.py, so write this then_ 

