
## mPlane SDK Configuration Files

The TLS state, access control, client framework, command-line client, and component runtime use a unified configuration file in Windows INI file format (as supported by the Python standard library `configparser` module).

The following sections and keys are supported/required by each module:

- `TLS` section: Certificate configuration. Required by component and client to support HTTPS URLs. Has the following keys:
    - `ca-chain`: path to file containing PEM-encoded certificates for the valid certificate authorities.
    - `cert`: path to file containing decoded and PEM-encoded certificate identifying this component/client. Must contain the decoded certificate as well, from which the distinguished name can be extracted.
    - `key`: path to file containing (decrypted) PEM-encoded secret key associated with this component/client's certificate
- `Roles` section: Maps identities to roles for access control. Used by component.py. Each key in this section is an mPlane identity (see below), and the value is a comma-separated list of arbitrary role names assigned to the identity.
- `Authorizations` section: Authorizes defined roles to invoke services associated with capabilities by capability label or token. Each key is a capability label or token, and the value is a comma-separated list of arbitrary role names which may invoke the capability. The use of labels is recommended for authorizations, as it makes authorization configuration more auditable. If authorizations are present, _only_ those capabilities which are explicitly authorized to a given client identity will be invocable.
- `Component` section: Global configuration for the component framework.
- `Client` section: Global configuration for the client framework.
- `ClientShell` section: Contains defaults for the mPlane client shell (see mPlane Client Shell below for details).

### Component Modules

In addition, any section in a configuration file given to component.py which begins with the substring `module_` will cause a component module to be loaded at runtime and that modules services to be made available (see Implementing a Component below). The `module` key in this section identifies the Python module to load by name. All other keys in this section are passed to the module's `services()` function as keyword arguments.

### Identities

Identities in the mPlane SDK (for purposes of configuration) are represented as a dot-separated list of elements of the Distinguished Name appearing in the certificate associated with the identity. So, for example, a certificate issued to `DC=ch, DC=ethz, DC=csg, OU=clients, CN=client-33` would be represented in the Roles section of a component configuration as `ch.ethz.csg.clients.client-33`.
