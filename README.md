# Tstat mPlane interface

This document quickly describes how to configure and run the Tstat mPlane interface.

This component rely on the draft protocol specification available in [doc/protocol-spec.md](https://github.com/fp7mplane/protocol-ri/blob/develop/doc); current work is in the `develop` branch.

Given the early stage of the mPlane project, the Tstat interface for now only provides a mechanism to modify the ```log_tcp_complete``` schema, 
i.e., changing the set of columns provided in the log file collecting statistics related to TCP connections. 
Tstat in fact can extract more than 100 features from each TCP connection.
Depending on the type of measurement ongoing, it is not so uncommon that only a subset of these features are actually useful.

Tstat groups TCP connection information in 5 groups
* **Core**: this set represent the minimum amount of information one should be interested into when considerin TCP connections.
  It contains the classic IPs/ports tuple, some timestamps related to the observation of the TCP SYN and
  first data packets exchanged, total number of bytes/packets and other few statistics.
* **End-to-end**: this set contains statistics related to RTT and TTL
* TCP options: this set contains several stats related to dynamics of the TCP protocol (e.g., receiver window, congestion window, 
  window scaling, etc.)
* **P2P**: this set contains stats specific to E2DK 
* **Layer7**: this set contains stats related to the dynamic of the application layer related to the TCP connection.
For more details about the format, please refer to the [official documentation](http://tstat.polito.it/svn/software/tstat/branches/mplane/doc/log_tcp_complete_mplane_descr.txt)

Such groups can be activated/disactivated acting on the `runtime.conf`, i.e., the Tstat configuration file
that can be used to modify the runtime behavior of Tstat.
In particular, the mentioned groups are related to the `[option]` section of the configuration file

```
[options]
tcplog_end_to_end = 0         # Enable the logging of the End_to_End set of measures (RTT, TTL)
tcplog_layer7 = 0             # Enable the logging of the Layer7 set of measures (SSL cert., message counts)
tcplog_p2p = 0                # Enable the logging of the P2P set of measures (P2P subtype and ED2K data)
tcplog_options = 0            # Enable the logging of the TCP Options set of measures
httplog_full_url = 0          # Enable the logging of the full URLs in log_http_complete
```

The Core set is implicitly activated when any of the other groups is activated, or when enabling the collection of
`log_tcp_complete` without specifying any more specific group of stats.

Essentially the Tstat mPlane interface acts on the `runtime.conf` changing the value of its internal values
to alter the runtime behaviour of Tstat.

In the following is reported a complete example of usage of the Tstat mPlane interface.

## Step 1: run Tstat

We need first to download and compile Tstat

```
svn co http://tstat.polito.it/svn/software/tstat/branches/mplane tstat_mplane
cd tstat_mplane
./autogen.sh
./configure
make
```

Then we execute Tstat (with root privileges)
```
sudo tstat/tstat -l -i eth0 -s tstat_output_logs -T tstat-conf/runtime.conf
```

This commands ask to Tstat to live capture (`-l`) traffic from the `eth0` interface (`-i`) and to
save the output logs in the `tstat_output_logs` directory (`-s`).

This creates the following output

```
[-] Disabling histo engine logs
[-] Disabling log_tcp_nocomplete
[-] Disabling log_udp_complete
[-] Disabling log_mm_complete
[-] Disabling log_skype_complete
[-] Disabling log_chat_complete
[-] Disabling log_chat_messages
[-] Disabling log_video_complete
[-] Disabling log_streaming_complete
[-] TCP log level set to 0 (Core)
[-] Disabling dump engine
pcap_openlive: 
Live capturing on: en0 - snaplen = 550
[Wed May 14 23:42:24 2014] created new outdir tstat_output_logs/2014_05_14_23_42.out
```

In this configuration, Tstat is running with the Core set of columns activated.



## Step 2: run the Tstat mPlane interface 

Download the software

```
>>> git clone https://github.com/fp7mplane/protocol-ri.git tstat_proxy
>>> cd tstat_proxy
>>> git checkout tstat
```

To run the software you need to set up two environment variables
* `PYTHONPATH` has to point to the `tstat\_proxy` directory just created
* `MPLANE\_CONF\_DIR` has to should point to `tstat\_proxy/conf`

From within the `tstat\_proxy` folder

```
$ python3 mplane/tstat_proxy.py -T path/to/tstat/runtime.conf -c conf/client-certs.conf
Added <Service for <capability: measure (tstat-log_tcp_complete-core) when now + 0s token 341cdfb9 schema 74a63d03 p/m/r 0/0/42>>
Added <Service for <capability: measure (tstat-log_tcp_complete-end_to_end) when now + 0s token dc350c33 schema 3c68adb1 p/m/r 0/0/7>>
Added <Service for <capability: measure (tstat-log_tcp_complete-tcp_options) when now + 0s token 8a4d81a7 schema 5785fd2e p/m/r 0/0/46>>
Added <Service for <capability: measure (tstat-log_tcp_complete-p2p_stats) when now + 0s token 0ff7e40a schema b48affa1 p/m/r 0/0/6>>
Added <Service for <capability: measure (tstat-log_tcp_complete-layer7) when now + 0s token 571efbcc schema 08bb2e08 p/m/r 0/0/4>>
```

The input arguments specify the Tstat runtime.conf (`-T`) and the client certificates used for HTTPS authentication (`-c`).
As result, the system is running a simple web server listening on `127.0.0.1` and port `8888` which is capable of handling
5 mPlane capabilities, each related to a different group of `log_tcp_complete` columns as previously described.

## Step 3: run the mPlane client

From within the `tstat\_proxy` folder

```
>>> tstat_proxy finamore$ python3 mplane/client.py -c conf/client-certs.conf 
```

This will switch the control to the mPlane prompt.

```
|mplane| 
```

We need then to connect to the Tstat proxy web server

```
|mplane| connect https://locahost:8888 
```

This will trigger a request for listing the registered capabilities.
If everything is working properly, the capabilities are printed on standard output

```
new client: https://localhost:8888 /capability
getting capabilities from /capability
get_mplane_reply /capability/341cdfb9d3ec020b6019a4772a7a889c 200 Content-Type application/x-mplane+json
parsing json
got message:
capability: measure
label: tstat-log_tcp_complete-core
results:
- initiator.ip4
- initiator.port
- packets.forward
- packets.forward.syn
- packets.forward.fin
- packets.forward.rst
- packets.forward.ack

...

capability: measure
label: tstat-log_tcp_complete-layer7
results:
- initiator.psh_separated
- responder.psh_separated
- ssl.hello.client
- ssl.hello.server
token: 571efbcc018bf7e8fb9d23f0fe0fd263
version: 0
when: now + 0s
```

To have a compact view of the registered capabilities run

```
|mplane| listcap
  0: <capability: measure (tstat-log_tcp_complete-core) when now + 0s token 341cdfb9 schema 74a63d03 p/m/r 0/0/42>
  1: <capability: measure (tstat-log_tcp_complete-end_to_end) when now + 0s token dc350c33 schema 3c68adb1 p/m/r 0/0/7>
  2: <capability: measure (tstat-log_tcp_complete-tcp_options) when now + 0s token 8a4d81a7 schema 5785fd2e p/m/r 0/0/46>
  3: <capability: measure (tstat-log_tcp_complete-p2p_stats) when now + 0s token 0ff7e40a schema b48affa1 p/m/r 0/0/6>
  4: <capability: measure (tstat-log_tcp_complete-layer7) when now + 0s token 571efbcc schema 08bb2e08 p/m/r 0/0/4>
```

## 4: run an experiment

Now that we are connected, we can schedule plan a data collection. By default, Tstat run with the **Core** set already activated
but we can schedule to expand it by adding the **end-to-end** set of columns.

For this purpose we need first to define the duration of the experiment.

```
|mplane| when now + 5m
```

This will ask to the to run an experiment as soon as the request is seen and keep collecting data for 5 minutes.
To perform the actual request

```
|mplane| runcap 1
<specification: measure (tstat-log_tcp_complete-end_to_end) when now + 5m token 81b1a75c schema 3c68adb1 p(v)/m/r 0(0)/0/7>
get_mplane_reply / 200 Content-Type application/x-mplane+json
parsing json
got message:
receipt: measure
results:
- rtt.average.ms
- rtt.min.ms
- rtt.max.ms
- rtt.stddev
- rtt.samples
- ttl.min
- ttl.max
token: 81b1a75cba1060170a35ebdeb82b9e14
version: 0
when: now + 5m

ok
```

This is saying that the request has been scheduled, and is confirmed by the output of the Tstat proxy

```
<Service for <capability: measure (tstat-log_tcp_complete-end_to_end) when now + 0s token dc350c33 schema 3c68adb1 p/m/r 0/0/7>> matches <specification: measure (tstat-log_tcp_complete-end_to_end) when now + 5m token 81b1a75c schema 3c68adb1 p(v)/m/r 0(0)/0/7>
Will interrupt <Job for <specification: measure (tstat-log_tcp_complete-end_to_end) when now + 5m token 81b1a75c schema 3c68adb1 p(v)/m/r 0(0)/0/7>> after 300.0 sec
Scheduling <Job for <specification: measure (tstat-log_tcp_complete-end_to_end) when now + 5m token 81b1a75c schema 3c68adb1 p(v)/m/r 0(0)/0/7>> immediately
Returning <receipt: 81b1a75cba1060170a35ebdeb82b9e14>
```

After 1 minute from the modification of `runtime.conf`, Tstat reacts adn enforce the new configuration.
Similarly, when the Tstat proxy will disable the acquisition of the **End-to-end** set, Tstat will react restoring
the previous set up. These modification can be observed on the Tstat standard output

```
[Wed May 14 23:44:14 2014] TCP log level set to 1 (Core + End_to_end)
[Wed May 14 23:44:14 2014] created new outdir tstat_output_logs/2014_05_14_23_44.out
[Wed May 14 23:49:30 2014] TCP log level set to 0 (Core)
[Wed May 14 23:49:30 2014] created new outdir tstat_output_logs/2014_05_14_23_49.out
```

as well as inspecting the content of the created files

```
>>> head tstat_output_logs/2014_05_14_23_44.out/log_tcp_complete
#01#c_ip:1 c_port:2 c_pkts_all:3 c_rst_cnt:4 c_ack_cnt:5 c_ack_cnt_p:6 c_bytes_uniq:7 c_pkts_data:8 c_bytes_all:9 c_pkts_retx:10 c_bytes_retx:11 c_pkts_ooo:12 c_syn_cnt:13 c_fin_cnt:14 s_ip:15 s_port:16 s_pkts_all:17 s_rst_cnt:18 s_ack_cnt:19 s_ack_cnt_p:20 s_bytes_uniq:21 s_pkts_data:22 s_bytes_all:23 s_pkts_retx:24 s_bytes_retx:25 s_pkts_ooo:26 s_syn_cnt:27 s_fin_cnt:28 first:29 last:30 durat:31 c_first:32 s_first:33 c_last:34 s_last:35 c_first_ack:36 s_first_ack:37 c_isint:38 s_isint:39 con_t:40 p2p_t:41 http_t:42 c_rtt_avg:43 c_rtt_min:44 c_rtt_max:45 c_rtt_std:46 c_rtt_cnt:47 c_ttl_min:48 c_ttl_max:49 s_rtt_avg:50 s_rtt_min:51 s_rtt_max:52 s_rtt_std:53 s_rtt_cnt:54 s_ttl_min:55 s_ttl_max:56
192.168.1.2 55513 21 0 20 9 7300 9 7300 1 1 0 1 2 74.125.232.142 443 19 0 19 8 5782 9 5782 0 0 0 1 1 1400103796934.199951 1400103878699.169922 81764.970000 109.372000 198.890000 81715.928000 48302.295000 108.198000 196.288000 1 1 8192 0 0 103.862373 47.609000 174.678000 43.637202 7 64 64 0.151598 0.064000 0.340000 0.088741 10 55 55
192.168.1.2 55526 30 1 28 17 2826 9 2826 1 1 0 1 2 ...


>>> head tstat_output_logs/2014_05_14_23_49.out/log_tcp_complete 
#00#c_ip:1 c_port:2 c_pkts_all:3 c_rst_cnt:4 c_ack_cnt:5 c_ack_cnt_p:6 c_bytes_uniq:7 c_pkts_data:8 c_bytes_all:9 c_pkts_retx:10 c_bytes_retx:11 c_pkts_ooo:12 c_syn_cnt:13 c_fin_cnt:14 s_ip:15 s_port:16 s_pkts_all:17 s_rst_cnt:18 s_ack_cnt:19 s_ack_cnt_p:20 s_bytes_uniq:21 s_pkts_data:22 s_bytes_all:23 s_pkts_retx:24 s_bytes_retx:25 s_pkts_ooo:26 s_syn_cnt:27 s_fin_cnt:28 first:29 last:30 durat:31 c_first:32 s_first:33 c_last:34 s_last:35 c_first_ack:36 s_first_ack:37 c_isint:38 s_isint:39 con_t:40 p2p_t:41 http_t:42
192.168.1.2 55571 17 0 16 7 2679 7 2679 1 1 0 1 2 74.125.232.142 443 13 0 13 4 5173 7 5173 0 0 0 1 1 1400104176174.389893 1400104176772.221924 597.832000 50.176000 103.471000 547.508000 546.291000 48.619000 99.656000 1 1 8192 0 0
192.168.1.2 55572 24 0 23 9 4881 12 4881 1 1 0 1 ...
```

