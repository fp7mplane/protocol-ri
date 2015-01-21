# Test cases / Troubleshooting

This guide contains descriptions/troubleshooting methods for the various mPlane protocol component implementations.

The core classes in the `mplane.model` and `mplane.scheduler` packages are documented using Sphinx; reasonably current Sphinx documentation can be read online [here](https://fp7mplane.github.io/protocol-ri).

The draft protocol specification is available in [doc/protocol-spec.md](https://github.com/fp7mplane/protocol-ri/blob/develop/doc); current work is in the `develop` branch.

All the modules are supporting so secure as non-secure tunnel for communication. All the examples and test cases should be done via HTTPS.

When using a secure tunnel for the communication the certificates must be given via the ```--certfile``` option. Otherwise the disabled security must be indicated with the ```--disable-ssl```.

# Client 

Implementations for the client:

*  `client.py` 
* `client-RI.py`

# Components
This section contains a short HOWTO for each component.

## Component-initiated workflow - general discussion
Please note,  that a ```supervisor``` must operate as a prerequisite during the ```client initiated``` testing. For both cases the ```MPLANE_CONF_DIR``` needs to be exported.

The aforementioned prerequisites can be stated by executing

    export MPLANE_CONF_DIR=./conf
    python3 -m mplane.supervisor -c ./conf/supervisor-certs.conf

After the supervisor is running and the compoent is started the successfull login is indicated by the capability registration.

    |mplane| Capability <capability name> received from <component name>

## Client-initiated workflow - general discussion

## Ping
### Component-initiated
The component-initiated ping  is avaible via `ping_ci.py`.

### Client-initiated
The component-initiated ping  is avaible via `ping.py`.

## Tstat proxy
Tstat-proxy is implemented in ``tstat_proxy.py``. A detailed description to Tstat can be found here: ``https://www.ict-mplane.eu/public/tstat``

### Component-initiated
    python3 -m mplane.tstat_proxy -T ./conf/runtime.conf --certfile ./conf/CI-component-certs.conf

After the components are registered, we are ready to assembly a specification

    |mplane| Capability tstat-log_tcp_complete-end_to_end received from org.mplane.SSB.Components.Component-1
    |mplane| Capability tstat-log_tcp_complete-tcp_options received from org.mplane.SSB.Components.Component-1
    |mplane| Capability tstat-log_tcp_complete-layer7 received from org.mplane.SSB.Components.Component-1
    |mplane| Capability tstat-log_tcp_complete-p2p_stats received from org.mplane.SSB.Components.Component-1
    |mplane| Capability tstat-log_tcp_complete-core received from org.mplane.SSB.Components.Component-1
    |mplane| runcap 1
    |when| = now + 5s / 1s
    |mplane| Specification tstat-log_tcp_complete-end_to_end successfully pulled by org.mplane.SSB.Components.Component-1

The specification is downloaded by the component, and after the successfull traffic sniffing the result and the receipt is returned.

    <Service for <capability: measure (tstat-log_tcp_complete-end_to_end) when now + 0s token 3ded966a schema c172877f p/m/r 0/3/7>> matches <specification: measure (tstat-log_tcp_complete-end_to_end) when now + 5s / 1s token 750e9fef schema c172877f p(v)/m/r 0(0)/3/7>
    Will interrupt <Job for <specification: measure (tstat-log_tcp_complete-end_to_end) when now + 5s / 1s token 750e9fef schema c172877f p(v)/m/r 0(0)/3/7>> after 5.0 sec
    Scheduling <Job for <specification: measure (tstat-log_tcp_complete-end_to_end) when now + 5s / 1s token 750e9fef schema c172877f p(v)/m/r 0(0)/3/7>> immediately
    Returning <receipt: 750e9feffd1c0d49926848c522e2890c>
    specification tstat-log_tcp_complete-end_to_end: start = 2015-01-12 13:22:08.891687, end = 2015-01-12 13:22:13.906295

Check that the result is received by the supervisor.

    |mplane| Result received by org.mplane.SSB.Components.Component-1


### Client-initiated

## OTT probe

The fully operational OTT probe setup consists of two main parts:

  * Python interface implementing the ``mplane-protocol`` ``ott.py``
  * C++ measurement module

Prerequisite for the C++ module:

  * ``libcurl.so.4`` 
  * ``boost_program_options``
  * ``libpthread``
  * ``libz``
  * ``libssl``
  * ``libreactor`` -  published by NETvisor Ltd.
  * ``probe-ott`` published by NETvisor Ltd.

The published modules are avaible via this URL:

    http://tufaweb.netvisor.hu/ottdemo/mplane-ottmodule.tar.gz

To speed up testing there is no need to compile it from source it is already avaible via various platforms:

  * ar71xx (tested on OpenWRT 12.04)
  * x86_64 (tested on Ubuntu 14.04)
  * i386 (tested on CentOS release 6.5)

If there is any problem (or a new platform is requested) please contact <gabor.molnar@netvisor.hu>.

Copy probe-ott to your PATH ( ``/usr/bin`` ) and add libreactor to ``LD_LIBRARY_PATH``
The easiest way to check that all the libraries are installed is to run the object file:

    probe-ott
    the option '--slot' is required but missing

If it fails with the aforementioned error, the measurement module is configured well.

Using the python module:

The used IPv4 address can be specified via the ``-4`` argument. If it is not given the modules uses the first non-loopback IP address.

Tested protocols:

  * HLS - HTTP Live streaming
   * http://devimages.apple.com/iphone/samples/bipbop/bipbopall.m3u8
   * http://skylivehls.cdnlabs.fastweb.it/217851/tg24/index.m3u8
  * IIS - Smooth streaming
   * http://skylivehss.cdnlabs.fastweb.it/227324/tg24.isml/Manifest

### Component-initiated

    python3 -m mplane.ott --certfile ./conf/CI-component-certs.conf

After the components are registered, we are ready to assembly a ``specification``

Supervisor side:

    |mplane| Capability ott-download received from org.mplane.SSB.Components.Component-1
    |mplane| runcap 1
    |when| = now + 10s / 10s
    |param| content.url = http://skylivehls.cdnlabs.fastweb.it/217851/tg24/index.m3u8
    |param| source.ip4 = 192.168.25.107
    |mplane| Specification ott-download successfully pulled by org.mplane.SSB.Components.Component-1

The specification is received on the component side, and the measurement is starting. The process is finished with an assembled result, which is returned accompanied by the receipt to the supervisor.

    Checking for Specifications...
    <Service for <capability: measure (ott-download) when now ... future / 10s token 702484e7 schema 33a0f637 p/m/r 2/0/8>> matches <specification: measure (ott-download) when now + 10s / 10s token a7c86828 schema 33a0f637 p(v)/m/r 2(2)/0/8>
    Will interrupt <Job for <specification: measure (ott-download) when now + 10s / 10s token a7c86828 schema 33a0f637 p(v)/m/r 2(2)/0/8>> after 10.0 sec
    Scheduling <Job for <specification: measure (ott-download) when now + 10s / 10s token a7c86828 schema 33a0f637 p(v)/m/r 2(2)/0/8>> immediately
    running probe-ott --slot -1 --mplane 10 --url http://skylivehls.cdnlabs.fastweb.it/217851/tg24/index.m3u8
    Returning <receipt: a7c8682814bca1294f673c6686e0743b>
    Result for ott-download successfully returned!

The result can be viewved via the supervisor.

    |mplane| Result received by org.mplane.SSB.Components.Component-1
    |mplane| listmeas
    1 - <result: measure (ott-download) when 2015-01-12 11:37:35.341956 token a7c86828 schema 33a0f637 p/m/r(r) 2/0/8(1)>
    |mplane| showmeas 1
    label: ott-download
    parameters:
        content.url: http://skylivehls.cdnlabs.fastweb.it/217851/tg24/index.m3u8
        source.ip4: 192.168.25.107
    registry: http://ict-mplane.eu/registry/core
    result: measure
    results:
    - time
    - bandwidth.nominal.kbps
    - http.code.max
    - http.redirectcount.max
    - qos.manifest
    - qos.content
    - qos.aggregate
    - qos.level
    resultvalues:
    -   - '2015-01-12 11:37:35.341956'
        - '2842'
        - '200'
        - '1'
        - '100'
        - '100'
        - '100'
        - '100'
    token: a7c8682814bca1294f673c6686e0743b
    version: 1
    when: '2015-01-12 11:37:35.341956'

### Client-initiated
Not tested yet.
