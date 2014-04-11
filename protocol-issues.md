# Open Issues in the mPlane Protocol

## Indirect Export

The D1.3 revision of the protocol presumes that each individual collection in indirect export will need to be pre-authorized (i.e., that indirect export causes Specifications to be sent to both exporter and collector). This does allow a supervisor to apply access control to indirect export, but is not really in keeping with the architectural principle of state distribution. Especially as indirect export must in any case be secured with a protocol that binds each connection to a verifiable identity, this arrangement adds unnecessary complexity to the protocol.

I therefore propose to change the sense of the ```collect``` verb in an mPlane capability to mean "this collector will accept information of the given type over the given protocol (with the type binding specified for that protocol)." The ```link:``` section of such a capability will contain a URL describing the protocol and the location to which connections may be made and/or messages may be sent; it is presumed in this case that the client additionally has credentials with which it can connect using this protocol. When using the mPlane over HTTPS or mPlane over SSH protocols for indirect export, Results matching the Capability can be POSTed or send directly to the given location.

(A still open issue here is how to handle credentials for allowing such connections.)

The new proposed method for indirect export is as follows:

1. Client gets verb:measure capability from exporter with export:"schema" or export:"schema://single-target"
2. Client gets verb:collect capability from collector with export:"schema://target"
3. Client invokes exporter capability with Specification with target in the export: section
4. Exporter starts exporting
5. Export ends when either
    - the temporal scope of the Specification ends
    - the Client sends an interrupt to the Exporter
    - the collector terminates (and signals this to the Exporter via the given protocol)

Note that this arrangement does not support pull-based export. Is this an issue?

## Registry Flexibility

The registry is presently hardcoded into the RI. This does not allow the registry to be expanded at all, and does not allow e.g. the direct use of the IPFIX IE registry when doing so would be appropriate. Taking a page from LMAP, we should allow the registry used by a message to be expressed explicitly by URL, from which a JSON registry file can be downloaded.

## Registry Definition

The current mechanism for defining the registry (based on text files) is not adequate. First, a JSON format should be defined for this (see Fabrizio's work on the subject, and above). Second, to avoid combinatoric explosion in structured names, modifiers, units, and aggregates should be assignable by class. Registry definition work should probably predate registry flexibility work in the RI.

## Multiple messages

Multiple messages should be able to show up in an single object; this is used now to retrieve multiple results at once.

I propose a new message type, envelope, to be added to the information model. It has a single field, content:, consisting of a list of other messages. The envelope verb is currently ignored. 