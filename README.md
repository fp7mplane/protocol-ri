# protocol-ri Introduction

*[**Editor's Note**: this readme is under construction]*

This module contains the mPlane Software Development Kit.

The draft protocol specification is available in [doc/protocol-spec.md](https://github.com/fp7mplane/protocol-ri/blob/sdk/doc); current work is in the `sdk` branch.

The mPlane Protocol provides control and data interchange for passive and active network measurement tasks. It is built around a simple workflow in which __Capabilities__ are published by __Components__, which can accept __Specifications__ for measurements based on these Capabilities, and provide __Results__, either inline or via an indirect export mechanism negotiated using the protocol. 

Measurement statements are fundamentally based on schemas divided into Parameters, representing information required to run a measurement or query; and Result Columns, the information produced by the measurement or query. Measurement interoperability is provided at the element level; that is, measurements containing the same Parameters and Result Columns are considered to be of the same type and therefore comparable.

# Using the mPlane SDK

## Prerequisites

The mPlane SDK requires Python 3.3 and the following additional packages:

- pyyaml
- tornado
- urllib3

## Contents

The SDK is made up of the several modules. The core classes are documented using Sphinx. Reasonably current Sphinx documentation can be read online [here](https://fp7mplane.github.io/protocol-ri).

- `mplane.model`: Information model and JSON representation of mPlane messages. 
- `mplane.scheduler`: Component specification scheduler. Maps capabilities to Python code that implements them (in `Service`) and keeps track of running specifications and associated results (`Job` and `MultiJob`). 
- `mplane.tls`: Handles TLS, mapping local and peer certificates to identities and providing TLS connectivity over HTTPS.
- `mplane.azn`: Handles access control, mapping identities to roles and authorizing roles to use specific services.
- `mplane.client`: mPlane client framework. Handles client-initiated (`HttpClient`) and component-initiated (`ListenerHttpClient`) workflows.
- `mplane.clientshell`: Simple command-line shell for debugging.
- `mplane.component`: mPlane component framework. Handles client-initiated and component-initiated workflows.

## mPlane SDK Configuration Files

The TLS state, access control, client and component frameworks use a unified configuration file in Windows INI file format (as supported by the Python standard library `configparser` module).

## Implementing a Component

## mPlane Client Shell

# Differences between the Reference Implementation and the Protocol Specification

The following classes and features are *not yet implemented* in the reference implementation:

- Indirection messages
- Withdrawal messages
- mplane.model support for repeating measurements (assigned to FHA)
- mplane.model support for prefix constraints
- mplane.model support for the registry section (esp. default)
- Callback control as specified in the protocol spec

# Testing and Developing the SDK

## Testing

Unit testing is done with the nose package. To run:

`nosetests --with-doctest mplane.model`
