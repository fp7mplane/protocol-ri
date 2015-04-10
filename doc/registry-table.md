| Name | Primitive | Desciption                                  |
| ---- | --------- | ------------------------------------------- |
| start | time | Start time of an event/flow that may have a non-zero duration |
| end | time | End time of an event/flow that may have a non-zero duration |
| time | time | Time at which an single event occurred |
| duration.s | natural | Duration of an event/flow in seconds |
| duration.ms | natural | Duration of an event/flow in milliseconds |
| duration.us | natural | Duration of an event/flow in microseconds |
| duration.ns | natural | Duration of an event/flow in nanoseconds |
| source.ip4 | address | Source IPv4 address of an event/flow, or the IPv4 address from which an active measurement was taken |
| source.ip6 | address | Source IPv6 address of an event/flow, or the IPv6 address from which an active measurement was taken |
| source.port | natural | Source layer 4 port of an event/flow, or the port from which packets were sent when an active measurement was taken |
| source.interface | string | A locally-scoped identifier of an interface to which the source of an event/flow is attached, or from which an active measurement was taken |
| source.device | string | A locally-scoped identifier of a source device of an event/flow, or from which an active measurement was taken |
| source.as | natural | BGP AS number of the source of an event/flow, or AS originating an active measurement |
| destination.ip4 | address | The destination IPv4 address of an event/flow, or the IPv4 address of the target of an active measurement |
| destination.ip6 | address | The destination IPv6 address of an event/flow, or the IPv6 address of the target of an active measurement |
| destination.port | natural | The destination layer 4 port of an event/flow, or the port to which packets were sent when an active measurement was taken |
| destination.interface | string | A locally-scoped identifier of an interface to which the destination of an event/flow is attached, or the target interface of an active measurement |
| destination.device | string | A locally-scoped identifier of a destination device of an event/flow, or the target of an active measurement |
| destination.as | natural | BGP AS number of the destination of an event/flow, or AS target of an active measurement |
| destination.url | url | A URL identifying a target of an active measurement |
| observer.ip4 | address | The IPv4 address of the observation point of a passive measurement |
| observer.ip6 | address | The IPv6 address of the observation point of a passive measurement |
| observer.link | string | A locally-scoped identifier of the link on which a passive measurement was observed |
| observer.interface | string | A locally-scoped identifier of the interface on which a passive measurement was observed |
| observer.device | string | A locally-scoped identifier of the device on which a passive measurement was observed |
| observer.as | natural | BGP AS number of the observer of a passive measurement or looking glass |
| intermediate.ip4 | address | IPv4 address of a given entity along the path of a measurement; often scoped by hops.ip |
| intermediate.ip6 | address | IPv6 address of a given entity along the path of a measurement; often scoped by hops.ip |
| intermediate.port | natural | Layer 4 port on which a flow/event was observed on a given entity along the path; used for NAPT applications |
| intermedate.as | natural | BGP AS number of a given entity along the path of a measurement; often scoped by hops.as |
| octets.ip | natural | Count of octets at layer 3 (including IP headers) associated with a flow, event, or measurement |
| octets.tcp | natural | Count of octets at layer 4 (including TCP headers) associated with a flow, event, or measurement |
| octets.udp | natural | Count of octets at layer 4 (including UDP headers) associated with a flow, event, or measurement |
| octets.transport | natural | Count of octets at layer 4 (including all sub-network-layer headers) associated with a flow, event, or measurement |
| octets.layer5 | natural | Count of octets at layer 5 (i.e., excluding network and transport layer headers) associated with a flow, event, or measurement |
| octets.layer7 | natural | Count of octets at layer 7 (i.e., passed up to the application, excluding network and transport layer headers and octets in retransmitted packets) associated with a flow, event, or measurement |
| packets.ip | natural | Count of IP packets associated with flow, event, or measurement |
| packets.tcp | natural | Count of TCP segments associated with flow, event, or measurement |
| packets.udp | natural | Count of UDP segments associated with flow, event, or measurement |
| packets.transport | natural | Count of packets with a transport-layer header associated with a flow, event, or measurement |
| packets.layer5 | natural | Count of packets with non-empty transport-layer payload associated with a flow, event, or measurement |
| packets.layer7 | natural | Count of packets carrying unique data at layer 7 (i.e., packets.layer5 minus retransmissions) associated with a flow, event, or measurement |
| packets.duplicate | natural | Count of duplicated packets observed in a flow, event, or measurement |
| packets.outoforder | natural | Count of out-of-order packets observed in a flow, event, or measurement |
| packets.lost | natural | Count of packets observed or inferred as lost in a flow, event, or measurement |
| packets.unobserved | natural | Count of packets observed or inferred as delivered but unobserved in a flow, event, or measurement |
| flows | natural | Count of unidirectional flows (see RFC 7011) associated with an event or measurement |
| flows.bidirectional | natural | Count of bidirectional flows (see RFC 7011 and 5103) associated with an event or measurement |
| delay.twoway.icmp.us | natural | Singleton two-way delay in microseconds as measured by ICMP Echo Request/Reply (see RFC 792) |
| delay.twoway.icmp.us.min | natural | Minimum two-way delay in microseconds as measured by ICMP Echo Request/Reply (see RFC 792) |
| delay.twoway.icmp.us.mean | natural | Mean two-way delay as in microseconds measured by ICMP Echo Request/Reply (see RFC 792) |
| delay.twoway.icmp.us.50pct | natural | Median two-way delay in microseconds as measured by ICMP Echo Request/Reply (see RFC 792) |
| delay.twoway.icmp.us.max | natural | Maximum two-way delay in microseconds as measured by ICMP Echo Request/Reply (see RFC 792) |
| delay.twoway.icmp.count | natural | Count of valid ICMP Echo Replies received when measuring two-way delay using ICMP Echo Request/Reply (see RFC 792) |
| delay.oneway.owamp.us | natural | Singleton one-way delay along a path as measured by OWAMP (see RFC 3763) in microseconds |
| delay.oneway.owamp.us.min | natural | Minimum one-way delay along a path as measured by OWAMP (see RFC 3763) in microseconds |
| delay.oneway.owamp.us.mean | natural | Mean one-way delay along a path as measured by OWAMP (see RFC 3763) in microseconds |
| delay.oneway.owamp.us.50pct | natural | Median one-way delay along a path as measured by OWAMP (see RFC 3763) in microseconds |
| delay.oneway.owamp.us.max | natural | Maximum one-way delay along a path as measured by OWAMP (see RFC 3763) in microseconds |
| delay.oneway.owamp.count | natural | Count of samples for one-way delay measurements using OWAMP (see RFC 3763) |
| delay.queue.us | natural | Singleton measured or inferred delay attributable to queueing along a path in microseconds |
| delay.queue.us.min | natural | Minimum measured or inferred delay attributable to queueing along a path in microseconds |
| delay.queue.us.mean | natural | Mean measured or inferred delay attributable to queueing along a path in microseconds |
| delay.queue.us.50pct | natural | Median measured or inferred delay attributable to queueing along a path in microseconds |
| delay.queue.us.max | natural | Maximum measured or inferred delay attributable to queueing along a path in microseconds |
| delay.buffer.us | natural | Delay attributable to buffering at an endpoint in microseconds |
| delay.resolution.ms | natural | Delay from transaction start to completion of resolution of a name or URL to an address, in milliseconds |
| delay.firstbyte.ms | natural | Delay from transaction start to receipt of first byte of content at the initiator, in milliseconds |
| rtt.ms | natural | Round-trip time as measured or estimated at the sender in milliseconds |
| rtt.us | natural | Round-trip time as measured or estimated at the sender in microseconds |
| iat.ms | natural | Packet interarrival or event interoccurance time in milliseconds |
| iat.us | natural | Packet interarrival or event interoccurance time in microseconds |
| connectivity.ip | boolean | Assertion (or negation) that layer 3 connectivity between the identified source and destination is available |
| connectivity.as | boolean | Assertion (or negation) that control plane connectivity (i.e. BGP routability) between the identified source and destination is available |
| hops.ip | natural | Count of layer 3 hops or subhops along the identified path |
| hops.as | natural | Count of control-plane hops or subhops along the identified path |
| bandwidth.nominal.bps | natural | Nominal (advertised) bandwidth at a point or along a path in bits per second |
| bandwidth.nominal.kbps | natural | Nominal (advertised) bandwidth at a point or along a path in kilobits per second |
| bandwidth.nominal.Mbps | natural | Nominal (advertised) bandwidth at a point or along a path in megabits per second |
| bandwidth.partial.bps | natural | Partial bandwidth attributable to a given flow in bits per second |
| bandwidth.partial.kbps | natural | Partial bandwidth attributable to a given flow in kilobits per second |
| bandwidth.partial.Mbps | natural | Partial bandwidth attributable to a given flow in megabits per second |
| bandwidth.imputed.bps | natural | Bandwidth assumed to be available along a path according to measurement and heuristics in bits per second |
| bandwidth.imputed.kbps | natural | Bandwidth assumed to be available along a path according to measurement and heuristics in kilobits per second |
| bandwidth.imputed.Mbps | natural | Bandwidth assumed to be available along a path according to measurement and heuristics in megabits per second |
| content.url | url | A URL identifying some content, access to which is passively or actively measured |
| fps.nominal | float | Nominal frame rate in frames per second of the identified audio/video content |
| fps.achieved | float | Achieved frame rate in frames per second of the identified audio/video content |
| fps.achieved.min | float | Minumum achieved frame rate in frames per second of the identified audio/video content |
| fps.achieved.mean | float | Mean achieved frame rate in frames per second of the identified audio/video content |
| fps.achieved.max | float | Maximum achieved frame rate in frames per second of the identified audio/video content |
| sessions.transport | natural | Count of transport-layer sessions associated with an event |
| sessions.layer7 | natural | Count of application-layer sessions associated with an event |
| cpuload | real | Normalized CPU load on the identified device |
| memload | real | Normalized memory load on the identified device |
| linkload | real | Normalized link load on the identified interface or link |
| bufferload | real | Normalized buffer load on the identified device |
| bufferstalls | natural | Count of buffer stalls (imputed playback quality degradation) associated with a flow/event |
| snr | real | Signal to noise ratio in decibels, either in a radio access network or in an audio transmission context |
| measurement.identifier | string | Free-form string identifying the implementation of the measurement on the component; often the name of the external program |
| measurement.revision | natural | Release or deployment serial number of the implementation of the measurement on the component |
| measurement.algorithm | string | Free-form string identifying the algorithm used for the measurement on the component |
| location.latitude | float | The latitude of the component expressed as a floating point number of degrees north of the equator |
| location.longitude | float | The longitude of the component expressed as a floating point number of degrees east of the standard meridian (on Earth, the Prime Meridian at Greenwich) |
| location.altitude | float | The altitude of the component expressed as a floating point number of meters above the standard zero altitude (on Earth, mean sea level) |
| location.civil | string | A free-form identifier of the civil location (postal address, city name, building name, etc) of the component |
