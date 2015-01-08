# Components of the mPlane Development Kit

This document lists components of the mPlane Development Kit, to be integrated in Torino in January 2015 and released publicly before the deadline for presentations at RIPE (i.e., sometime in March 2015).

## Information Model and Scheduler

Let's start with what works:

- `mplane/model.py`: Data model. Basically complete, needs crontab support in `mplane.model.When`, coverage and docs.
- `mplane/scheduler.py`: Component scheduler. Binds capabilities to code, and specifications to threads. Handles scheduling of work based on `mplane.model.When`. Basically complete, needs crontab support in `mplane.scheduler.MultiJob`, coverage and docs.

For these two modules:

- FHA will complete crontab support. 
- ETH will handle documentation and testing coverage.
- SSB will merge the `fp7mplane/protocol-ri` version of these two modules into `stepenta/RI`.

## Common TLS Configuration

Clients and components should be able to load a configuration file (`tls.conf`) which refers to CA, private key, and certificate files, for setting up a TLS context. This TLS context should be common to all other code (`mplane/tls.py`). When the TLS configuration file is not present, `https://` URLs will not be supported; when present, the use of TLS will be selected based on the URL used.

- SSB will pull this out of existing utils.py and stepenta/RI code.

## Component Frameworks

We need a new module that implements a framework for two types of components: a client-initiated component, including an HTTPS server, and a component-initiated component, which uses an HTTP client and callback control.

All components will consist of the following components:

- a Scheduler with
    - a mapping of capabilities to Python classes to handle them
- access control logic based on 
    - a mapping of capabilities to roles for RBAC
    - a mapping of roles to higher-level identities (e.g. client cert CNs)

The mappings will be drawn from a unified configuration file (`component.conf`). When no authentication information is available (i.e., because HTTPS is not used), a `default` role is assumed. When no component configuration file is available, the module must come from the command-line, the capabilities supported are those declared by the module's `capabilities` method (see below), and all capabilities are authorized to be used by the `default` role. Capabilities are identified in this file by label or by full token.

Client-initiated components will additionally consist of:

- a Tornado HTTPS web server for handling POSTed messages

Component-initiated components will additionally consist of:

- bootstrap logic to retrieve the first callback control specification

The component framework will use Python classes for implementing component operation. The MPI is inherited from the existing reference implementation: component implementation classes extend `mplane.scheduler.Service`, and implement the following method:

```
def run(self, specification, check_interrupt):
    """
    Run this component given an mplane.model.Specification.
    Returns an mplane.model.Result or raises an exception.
    Receipts are handled by the component framework if 
    run() does not return in time.

    check_interrupt is a function which returns True if
    the scheduler has been interrupted; long-running components
    should check the return value of this function periodically
    and clean up if interrupted.

    """
    pass
```

The class should also provide (in contrast to the existing pattern) an entry point returning the capability/capabilities for which the module will be invoked:

```
def capabilities(self):
    """
    returns a list of mplane.model.Capability objects
    representing the capabilities of this component
```

To build the component framework:

- SSB will merge its fork back into fp7mplane/protocol-ri
- ETH will modify the merged fork (along with the split TLS configuration) to match this API
- ULG will move existing proxy code in fp7mplane/protocol-ri branches to the new interface (primarily, this should only involve implementing the `capabilities` method and slight refactoring of existing code)

## Client API

`mplane\client.py` should become a programmatic mPlane client (roughly the state-management parts of the current HttpClient class), allowing applications to "use" an mPlane client endpoint. The base client should support HTTP client-initiated workflows, along with component-initiated workflows with an Tornado HTTP server in a separate thread.

The Client API looks something like the following:

```
class Client:

    def __init__(self, default_url=None, tls_state=None):
    """
    initialize a client with a given 
    default URL an a given TLS state
    """
    pass

    def send_message(self, destination_url=None):
    """
    send a message, store any result in client state
    follows the link in the message, if present; 
    otherwise uses dst_url, otherwise default_url
    """
    pass

    def result_for(self, token_or_label):
    """
    return a result for the token if available;
    attempt to redeem the receipt for the token otherwise.
    """
    pass

    def retrieve_capabilities(self, url):
    """
    connect to the given URL, retrieve and process the capabilities/withdrawals found there
    """

    def forget(self, token_or_label):
    """
    forget all capabilities, receipts and results for the given token or label
    """

    def receipt_tokens(self):
    """
    list all tokens for outstanding receipts
    """

    def receipt_labels(self):
    """
    list all labels for outstanding receipts
    """

    def result_tokens(self):
    """
    list all tokens for stored results
    """

    def result_labels(self):
    """
    list all labels for stored results
    """

    def capability_tokens(self):
    """
    list all tokens for stored capabilities
    """

    def capability_labels(self):
    """
    list all labels for stored capabilities
    """

```

To realize the new programmatic client API:

- ETH will derive a new client module from existing `client.py` code; the primary API changes involve indexing state by token and index rather than by arrival order.

## Generic Client

Adding HTML renderers (with the Tornado templating framework) to this programmatic client would allow us to build a generic client with a Web interface. Here, the main view would be a tree of capabilities. The generic client would support only client-initiated workflows, as it would be intended for debugging purposes only, and used in concert with the stub supervisor for component-initiated workflows.

```
+- capability
 +- (new specification)
 +- receipt
 +- receipt
 +- result
```

To realize the new generic client:

- ETH will factor the command-line interface out of the existing `client.py` code.
- ??? will write a new web-based UI based on the new programmatic client interface.

## Stub Supervisor

A stub supervisor will consist of a client-initiated component interface bound to the programmatic client interface. Capabilities made available to the client interfaced will be republished directly by the component interface without aggregation or modification. This allows the generic client-initiated client above to be used with comoponent-initiated components for debug purposes, and provides a stub supervisor against which component registration can be tested.

- ??? will write the stub supervisor (SSB already has code for this, no?)
