
## mPlane SDK Configuration Files

The client framework, component framework and the supervisor, use three configuration files in JSON format: `client.json`, `component.json` and `supervisor.json`.


Below there is a description of all the sections and keys needed in each configuration file

- `TLS` section: certificate configuration. Needed by component, client and supervisor to support HTTPS URLs. Has the following keys:

    - `ca-chain`: path to file containing PEM-encoded certificates for the valid certificate authorities.
    - `cert`: path to file containing decoded and PEM-encoded certificate identifying this component/client. Must contain the decoded certificate as well, from which the distinguished name can be extracted.
    - `key`: path to file containing (decrypted) PEM-encoded secret key associated with this component/client's certificate.

- `Access` section: this section groups the `Roles` and the `Authorizations` sections, that provide informations for Authentication and Authorization. Used by component and supervisor.

	- `Roles` section: maps identities to roles for access control. Each key in this section is an arbitrary role name, and the value is a list of identities (Distinguished Names) mapped to the role.
	- `Authorizations` section: authorizes defined roles to invoke services associated with capabilities by capability label or token. Each key is a capability label or token, and the value is a list of arbitrary role names (the ones defined in the roles section) which may invoke the capability. The use of labels is recommended for authorizations, as it makes authorization configuration more auditable. If authorizations are present, _only_ those capabilities which are explicitly authorized to a given client identity will be invocable.

- `Registries` section: used by component, client and supervisor. Contains informations about the registry initialization. There are 2 keys:

	- `default`: URI of the base registry to use for all services handled by the component/supervisor/client. Components with more specialized registries will transmit this information inside the 'registry' field in the capabilities, and the supervisor/client will dinamically load the additional registry keys needed.
	- `preload`: path to a JSON file containing a private registry to preload on startup. Preloaded registry files will not be fetched from their canonical URL when referenced.

- `Component` section: required by component, contains the global configuration for the component framework. There are 3 possible sections (and one key), but two of them (`Initiator` and `Listener`) are mutually exclusive:

	- `Modules` section: **this section is mandatory, otherwise the component will not load any service!** Each key is a component module to be loaded at runtime. The key name itself identifies the Python module to load by name, while the list of values associated to the key is passed to the module's `services()` function as keyword arguments.
	- `Initiator` section: **this section is mutually exclusive with `Listener` section.** If this section is present, the component will adopt the component-initiated workflow. Contains the URLs used to register capabilities, retrieve specifications and return results. If the URLs are coincident, only one `url` key is needed in this section. Otherwise, if the URLs are different, three keys are needed:

		- `capability-url`: URL to post capabilities to
		- `specification-url`: URL to get specifications from.
		- `result-url`: URL to post results to

	- `Listener` section: **this section is mutually exclusive with `Initiator` section.** If this section is present, the component will adopt the client-initiated workflow. Contains the following keys:

		- `port`: port to listen on
		- `interfaces`: list of IPs to listen on. If empty, the component will listen on all the available IPs

	- `scheduler-max-results`: max number of results returned for a repeated measurement

- `Client` section: required by client, contains the global configuration for the client framework. There are 2 mutually exclusive possible sections:

	- `Initiator` section: **this section is mutually exclusive with `Listener` section.** If this section is present, the client will adopt the client-initiated workflow. Contains the URLs used to register capabilities, retrieve specifications and return results. If the URLs are coincident, only one `url` key is needed in this section. Otherwise, if the URLs are different, three keys are needed:

		- `capability-url`: URL to get capabilities from, and to which specifications will be sent (unless the `link` section in the received capabilities indicates a different URL)

	- `Listener` section: **this section is mutually exclusive with `Initiator` section.** If this section is present, the client will adopt the component-initiated workflow. Contains the following keys:

		- `port`: port to listen on
		- `interfaces`: list of IPs to listen on. If empty, the client will listen on all the available IPs
		- `capability-path`: path to accept capabilities on
		- `specification-path`: path to make specifications available on
		- `result-path`: path to accept results on

- The supervisor contains both the `Client` and the `Component` sections:

	- the `Client` section configures the client part of the supervisor, in other words **the part that communicates with the component**
	- the `Component` section configures the component part of the supervisor, in other words **the part that communicates with the client**


### Identities

Identities in the mPlane SDK (for purposes of configuration) are represented as a dot-separated list of elements of the Distinguished Name appearing in the certificate associated with the identity. So, for example, a certificate issued to `DC=ch, DC=ethz, DC=csg, OU=clients, CN=client-33` would be represented in the Roles section of a component configuration as `ch.ethz.csg.clients.client-33`.
