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
- `mplane.clientshell`: Simple command-line shell for client debugging.
- `mplane.component`: mPlane component framework. Handles client-initiated and component-initiated workflows.

## mPlane SDK Configuration Files

The TLS state, access control, client and component frameworks use a unified configuration file in Windows INI file format (as supported by the Python standard library `configparser` module).

The following sections and keys are supported/required by each module:

- `TLS` section: Certificate configuration. Required by component.py and client.py to support HTTPS URLs. Has the following keys:
    - `ca-chain`: path to file containing PEM-encoded certificates for the valid certificate authorities.
    - `cert`: path to file containing decoded and PEM-encoded certificate identifying this component/client. Must contain the decoded certificate as well, from which the distinguished name can be extracted.
    - `key`: path to file containing (decrypted) PEM-encoded secret key associated with this component/client's certificate
- `Roles` section: Maps identities to roles for access control. Used by component.py. Each key in this section is an mPlane identity (see below), and the value is a comma-separated list of arbitrary role names assigned to the identity.
- `Authorizations` section: Authorizes defined roles to invoke services associated with capabilities by capability label or token. Each key is a capability label or token, and the value is a comma-separated list of arbitrary role names which may invoke the capability. The use of labels is recommended for authorizations, as it makes authorization configuration more auditable. If authorizations are present, _only_ those capabilities which are explicitly authorized to a given client identity will be invocable. 
- `Component` section: *[**Editor's Note:** write this once it's clear what belongs in this section]*
- `Client` section: *[**Editor's Note:** write this once it's clear what belongs in this section]*
- `ClientShell` section: Contains defaults for the mPlane client shell (see mPlane Client Shell below for details).


### Component Modules

In addition, any section in a component.py configuration file beginning with the substring `module_` will cause a component module to be loaded at runtime and that modules services to be made available (see Implementing a Component below). The `module` key in this section identifies the Python module to load by name. All other keys in this section are passed to the module's `services()` function as keyword arguments.

### Identities

Identities in the mPlane SDK (for purposes of configuration) are represented as a dot-separated list of elements of the Distinguished Name appearing in the certificate associated with the identity. So, for example, a certificate issued to `DC=ch, DC=ethz, DC=csg, OU=clients, CN=client-33` would be represented in the Roles section of a component configuration as `ch.ethz.csg.clients.client-33`.

## Implementing a Component

The component.py module provides a framework for building components for both component-initiated and client-initiated 

## mPlane Client Shell

The mPlane Client Shell is a simple client intended for debugging of mPlane infrastructures. 

*[**Editor's Note**: as this is basically final now, document the client shell]*

# Testing and Developing the SDK

## Testing

Unit testing is done with the nose package. To run:

`nosetests --with-doctest mplane.model`

## Documentation

API documentation on [github](https://fp7mplane.github.io/protocol-ri) is autogenerated from Python docstrings with sphinx. Regenerating the documentation requires the sphinx package; once this is installed, use the following command from the sphinx directory to rebuild the documentation.

`PYTHONPATH=.. make html`
