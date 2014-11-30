# Components of the mPlane Development Kit

## Information Model and Scheduler

Let's start with what works:

- `mplane/model.py`: Data model. Basically complete, needs crontab support in `mplane.model.When`, coverage and docs.
- `mplane/scheduler.py`: Component scheduler. Binds capabilities to code, and specifications to threads. Handles scheduling of work based on `mplane.model.When`. Basically complete, needs crontab support in `mplane.scheduler.MultiJob`, coverage and docs.

For these two modules:

- FHA will complete crontab support. 
- ETH will handle documentation and testing coverage.
- SSB will merge the `fp7mplane/protocol-ri` version of these two modules into `stepenta/RI`.

## Common TLS Configuration

Clients and components should be able to load a tls.conf file which refers to CA, private key, and certificate files, for setting up a TLS context. This TLS context should be common to all other code (`mplane/tls.py`). 

- SSB will pull this out of existing utils.py and stepenta/RI code.

## Component Frameworks

We need a new module that implements a framework for two types of components: a client-initiated component, including an HTTPS server, and a component-initiated component, which uses an HTTP client and callback control.

All components will consist of the following components:

- a Scheduler with
    - a mapping of capabilities to Python classes to handle them
- access control logic based on 
    - a mapping of capabilities to roles for RBAC
    - a mapping of roles to higher-level identities (e.g. client cert CNs)

The mappings will be drawn from a unified configuration file (component.conf).

Client-initiated components will additionally consist of:

- a Tornado HTTPS web server

Component-initiated components will additionally consist of:

- bootstrap logic to retrieve the first callback control specification

## Client API

`mplane\client.py` should become a programmatic mPlane client (roughly the state-management parts of the current HttpClient class), allowing applications to "use" an mPlane client endpoint. The base client should support HTTP client-initiated workflows, along with component-initiated workflows with an Tornado HTTP server in a separate thread.

The Client API looks something like the following:

```
class Client:

    def __init__(default_url=None, tls_state=None):
    """
    initialize a client with a given 
    default URL an a given TLS state
    """
    pass

    def send_message(destination_url=None):
    """
    send a message, store any result in client state
    follows the link in the message, if present; 
    otherwise uses dst_url, otherwise default_url
    """
    pass

    def result_for(token_or_label):
    """
    return a result for the token if available;
    attempt to redeem the receipt for the token otherwise.
    """
    pass

    def forget(token_or_label):
    """
    forget all results for the given token or label
    """

    def retrieve_capabilities(url):
    """
    connect to the given URL, retrieve and process the capabilities/withdrawals found there
    """
```

## Generic Client

Adding HTML renderers (with the Tornado templating framework) to this programmatic client would allow us to build a generic client with a Web interface. Here, the main view would be a tree of capabilities. The generic client would support only client-initiated

```
+- capability
 +- (new specification)
 +- receipt
 +- receipt
 +- result
```

## Stub Supervisor

TBD
