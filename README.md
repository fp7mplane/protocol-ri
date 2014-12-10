## Supervisor Implementation and Component-Initiated workflow

### Description

This branch has been forked on 9 Dec 2014 from `develop`, in order to merge back [this implementation](https://github.com/stepenta/RI) into the RI.
The two main changes from the original RI are the implementation of the Component-Initiated workflow (capabilty push, specification pull), and the addition of the Supervisor (for CI workflows).

The components using the CI workflow are:
- the tstat probe (`tstat_proxy`,`tstat_caps`) - HTTP client;
- the supervisor (`supervisor`,`sv_handlers`) - HTTP server;
- the client (`client`)- HTTP client.
The interactions between these components follow [these guidelines](https://github.com/finvernizzi/mplane_http_transport), that are based on the protocol specification defined in the WP1 deliverables.

The workflow implemented in the original RI, let's call it Supervisor-Initiated (capability pull, specification push), has been mantained in:
- the ping probe (`ping`, `httpsrv`) - HTTP server;
- the client (`client-RI`) - HTTP client;
- the supervisor reference code for this setup is still missing, hence the client connects directly to the probe.

The internals (`model`, `scheduler`) have undergone just little changes regarding the Access Control logic, that now is based on the Distinguished Name (instead of the Common Name) and can also handle multiple probes with the same capabilities without confusion.
The registry (`registry.json`) has been extended to cover the capabilities from tStat and DATI (TI probe).
The PKI has been extended, and since we are still in develop and test phases, all the PKI keys are publicly available.
The scripts in the PKI folder allow you to generate your own certificates, both for CI and SI workflows (they differ because HTTP client and server are reversed in the two workflows, and the certificates change accordingly). It is strongly recommended to use the provided root-ca, and only generate your own client, component and supervisor certificates, so that we avoid several self-signed certificates that cannot cooperate.
You will need the root-ca passphrase to generate certificates: send me a mail at stefano.pentassuglia@ssbprogetti.it and I'll tell you that.

### HOWTO

To run the CI components (with SSL), from the protocol-ri directory, run:

```export MPLANE_CONF_DIR=./conf
python3 -m mplane.supervisor -c ./conf/supervisor-certs.conf```

This will launch the supervisor. Then:

```python3 -m mplane.tstat_proxy -T ./conf/runtime.conf -c ./conf/CI-component-certs.conf```

At this point, the tstat proxy will automatically register its capabilities to the Supervisor. Now launch the client:

```python3 -m mplane.client -c ./conf/CI-client-certs.conf```

From now on, the commands are the same from the original RI, so from the client:

1. ```connect``` the client Connects to the Supervisor and receives the capabilities of the probes registered to it
2. ```listcap``` will show capablities available
3. ```runcap <number>``` runs a capability by number in the ```listcap``` list. Any parameters not yet filled in by ```set``` will be prompted for.
4. ```redeem``` sends all pending receipts back to the component for results, if available.

While executing these operations, the supervisor and the probe will print some status udate messages, related to the comminucations going on.
(the Supervisor provides the same shell of the client, from which it is possible to launch capabilities and see results. This should be out of the mPlane scope, and is only for debug purposes)


The commands to run the SI workflow setup are:

```export MPLANE_CONF_DIR=./conf
python3 -m mplane.ping --ip4addr 127.0.0.1 --ssl 0 --certfile ./conf/SI-component-certs.conf
python3 -m mplane.client-RI --tlsconfig ./conf/SI-client-certs.conf```

and then the same shell commands as above.
