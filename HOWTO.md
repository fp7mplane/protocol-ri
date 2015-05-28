### HOWTO

#### Run Supervisor, Component and Client
To run the Supervisor, from the protocol-ri directory, run:

```python3 -m mplane.supervisor --config ./conf/supervisor.conf```

To run the Component:

```python3 -m mplane.component --config ./conf/component.conf```

At this point, the Component will automatically register its capabilities to the Supervisor. Now launch the Client:

```python3 -m mplane.clientshell --config ./conf/client.conf```

As soon as it's launched, the Client connects to the Supervisor and retrieves the capabilities. To get a list of commands available, type ```help```.
The minimum sequence of commands to run a capability and retrieve results is:

1. ```listcap``` will show all the available capabilities.
2. ```runcap <name_or_token>``` runs a capability from the ```listcap``` list. You will be asked to insert parameter values for that capability.
3. ```listmeas``` shows all pending receipts and received measures.
4. ```showmeas <name_or_token>``` shows the measure (or pending receipt) in detail.

While executing these operations, the supervisor and the component will print some status udate messages, giving information about the communications going on.

#### Configuration Files
They are located in ```protocol-ri/conf/```.

##### component.conf
*\[TLS\]* - paths to the certificate and key of the component, and to the root-ca certificate (or ca-chain)
*\[Roles\]* - bindings between Distinguished Names (of supervisors and clients) and Roles
*\[Authorizations\]* - for each capability, there is a list of Roles that are authorized to see that capability
*\[module_<name>\]* - parameters needed by specific component modules (e.g. ping, tStat, etc). If you don't need a module, remove the related section. If you add a module that needs parameters, add the corresponding section.

*\[component\]* - miscellaneous settings:
- registry_uri: link to the registry.json file to be used
- workflow: type of interaction between component and client/supervisor. Can be component-initiated or client-initiated. This must be the same both for the component and the client/supervisor, otherwise they will not be able to talk to each other.

To be properly set only if component-initiated workflow is selected:
- client_host: IP address of the client/supervisor to which the component must connect
- client_port: port number of the client/supervisor
- registration _ path: path to which capability registration messages will be sent (see [register capability] (https://github.com/finvernizzi/mplane_http_transport#capability))
- specification _ path: path from which retrieve specifications (see [retrieve specification] (https://github.com/finvernizzi/mplane_http_transport#specification))
- result _ path: path to which results of specifications are returned (see [return result] (https://github.com/finvernizzi/mplane_http_transport#result))

To be properly set only if client-initiated workflow is selected:
- listen_port: port number on which the component starts listening for mplane messages

##### client.conf
*\[TLS\]* - paths to the certificate and key of the client, and to the root-ca certificate (or ca-chain)
*\[client\]* - miscellaneous settings:
- registry_uri: link to the registry.json file to be used
- workflow: type of interaction between client and component/supervisor. Can be component-initiated or client-initiated. This must be the same both for the client and the component/supervisor, otherwise they will not be able to talk to each other.

To be properly set only if component-initiated workflow is selected:
- listen_host: IP address where the client starts listening for mplane messages
- listen_port: port number on which the client starts listening
- registration _ path: path to which capability registration messages will be received (see [register capability] (https://github.com/finvernizzi/mplane_http_transport#capability))
- specification _ path: path where specifications will be exposed to components/supervisors (see [retrieve specification] (https://github.com/finvernizzi/mplane_http_transport#specification))
- result _ path: path where results of specifications will be received (see [return result] (https://github.com/finvernizzi/mplane_http_transport#result))

To be properly set only if client-initiated workflow is selected:
- capability _ url: path from which capabilities will be retrieved

##### supervisor.conf
Since the Supervisor is just a composition of component and client, its configuration file is just a union of the file described above. 
*\[client\]* section regards the configuration of the part of the supervisor facing the component, in other words its "client part"
*\[component\]* section erregards the configuration of the part of the supervisor facing the client, in other words its "component part"
