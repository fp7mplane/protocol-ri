# mPlane Protocol Reference Implementation
# tStat component code
#
# (c) 2013-2014 mPlane Consortium (http://www.ict-mplane.eu)
#               Author: Stefano Pentassuglia
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.

import mplane.model

def tcp_flows_capability():
    cap = mplane.model.Capability(label="tstat-log_tcp_complete-core", when = "now + inf ... future")
    cap.add_result_column("initiator.ip4")
    cap.add_result_column("initiator.port")
    cap.add_result_column("packets.forward")
    cap.add_result_column("packets.forward.syn")
    cap.add_result_column("packets.forward.fin")
    cap.add_result_column("packets.forward.rst")
    cap.add_result_column("packets.forward.ack")
    cap.add_result_column("packets.forward.pure_ack")
    cap.add_result_column("packets.forward.with_payload")
    cap.add_result_column("packets.forward.rxmit")
    cap.add_result_column("packets.forward.outseq")
    cap.add_result_column("bytes.forward")
    cap.add_result_column("bytes.forward.unique")
    cap.add_result_column("bytes.forward.rxmit")
    
    cap.add_result_column("responder.ip4")
    cap.add_result_column("responder.port")
    cap.add_result_column("packets.backward")
    cap.add_result_column("packets.backward.syn")
    cap.add_result_column("packets.backward.fin")
    cap.add_result_column("packets.backward.rst")
    cap.add_result_column("packets.backward.ack")
    cap.add_result_column("packets.backward.pure_ack")
    cap.add_result_column("packets.backward.with_payload")
    cap.add_result_column("packets.backward.rxmit")
    cap.add_result_column("packets.backward.outseq")
    cap.add_result_column("bytes.backward")
    cap.add_result_column("bytes.backward.unique")
    cap.add_result_column("bytes.backward.rxmit")
    
    cap.add_result_column("start")
    cap.add_result_column("end")
    cap.add_result_column("duration.ms")
    cap.add_result_column("initiator.TTFP.ms")
    cap.add_result_column("responder.TTFP.ms")
    cap.add_result_column("initiator.TTLP.ms")
    cap.add_result_column("responder.TTLP.ms")
    cap.add_result_column("initiator.TTFA.ms")
    cap.add_result_column("responder.TTFA.ms")
    cap.add_result_column("initiator.ip4.isinternal")
    cap.add_result_column("responder.ip4.isinternal")
    cap.add_result_column("tstat.flow.class.conn")
    cap.add_result_column("tstat.flow.class.p2p")
    cap.add_result_column("tstat.flow.class.http")
    return cap

def e2e_tcp_flows_capability():
    cap = mplane.model.Capability(label="tstat-log_tcp_complete-end_to_end", when = "now + inf ... future")
    cap.add_result_column("rtt.average.ms")
    cap.add_result_column("rtt.min.ms")
    cap.add_result_column("rtt.max.ms")
    cap.add_result_column("rtt.stddev")
    cap.add_result_column("rtt.samples")
    cap.add_result_column("ttl.min")
    cap.add_result_column("ttl.max")
    return cap
    
def tcp_options_capability():
    cap = mplane.model.Capability(label="tstat-log_tcp_complete-tcp_options", when = "now + inf ... future")
    cap.add_result_column("initiator.RFC1323.ws")
    cap.add_result_column("initiator.RFC1323.ts")
    cap.add_result_column("initiator.win_scale")
    cap.add_result_column("initiator.SACK_set")
    cap.add_result_column("initiator.SACK")
    cap.add_result_column("initiator.MSS.bytes")
    cap.add_result_column("initiator.segment.max.bytes")
    cap.add_result_column("initiator.segment.min.bytes")
    cap.add_result_column("initiator.window.max.bytes")
    cap.add_result_column("initiator.window.min.bytes")
    cap.add_result_column("initiator.window.zero")
    cap.add_result_column("initiator.cwin.max.bytes")
    cap.add_result_column("initiator.cwin.min.bytes")
    cap.add_result_column("initiator.cwin.first.bytes")
    cap.add_result_column("initiator.rxmit.RTO")
    cap.add_result_column("initiator.rxmit.RTO.unnecessary")
    cap.add_result_column("initiator.rxmit.FR")
    cap.add_result_column("initiator.rxmit.FR.unnecessary")
    cap.add_result_column("initiator.reordering")
    cap.add_result_column("initiator.net_dup")
    cap.add_result_column("initiator.unknown")
    cap.add_result_column("initiator.flow_control")
    cap.add_result_column("initiator.SYN.equal_seqno")
    
    cap.add_result_column("responder.RFC1323.ws")
    cap.add_result_column("responder.RFC1323.ts")
    cap.add_result_column("responder.win_scale")
    cap.add_result_column("responder.SACK_set")
    cap.add_result_column("responder.SACK")
    cap.add_result_column("responder.MSS.bytes")
    cap.add_result_column("responder.segment.max.bytes")
    cap.add_result_column("responder.segment.min.bytes")
    cap.add_result_column("responder.window.max.bytes")
    cap.add_result_column("responder.window.min.bytes")
    cap.add_result_column("responder.window.zero")
    cap.add_result_column("responder.cwin.max.bytes")
    cap.add_result_column("responder.cwin.min.bytes")
    cap.add_result_column("responder.cwin.first.bytes")
    cap.add_result_column("responder.rxmit.RTO")
    cap.add_result_column("responder.rxmit.RTO.unnecessary")
    cap.add_result_column("responder.rxmit.FR")
    cap.add_result_column("responder.rxmit.FR.unnecessary")
    cap.add_result_column("responder.reordering")
    cap.add_result_column("responder.net_dup")
    cap.add_result_column("responder.unknown")
    cap.add_result_column("responder.flow_control")
    cap.add_result_column("responder.SYN.equal_seqno")
    return cap
    
def tcp_p2p_stats_capability():
    cap = mplane.model.Capability(label="tstat-log_tcp_complete-p2p_stats", when = "now + inf ... future")
    cap.add_result_column("p2p.subtype")
    cap.add_result_column("ed2k.data")
    cap.add_result_column("ed2k.signaling")
    cap.add_result_column("ed2k.i2r")
    cap.add_result_column("ed2k.r2i")
    cap.add_result_column("ed2k.chat")
    return cap    

def tcp_layer7_capability():
    cap = mplane.model.Capability(label="tstat-log_tcp_complete-layer7", when = "now + inf ... future")
    cap.add_result_column("initiator.psh_separated")
    cap.add_result_column("responder.psh_separated")
    cap.add_result_column("ssl.hello.client")
    cap.add_result_column("ssl.hello.server")
    return cap

def check_cap(cap):   
    if cap._label == "tstat-log_tcp_complete-core":   
        if not(cap.has_result_column("initiator.ip4") or
                cap.has_result_column("initiator.port") or
                cap.has_result_column("packets.forward") or
                cap.has_result_column("packets.forward.syn") or
                cap.has_result_column("packets.forward.fin") or
                cap.has_result_column("packets.forward.rst") or
                cap.has_result_column("packets.forward.ack") or
                cap.has_result_column("packets.forward.pure_ack") or
                cap.has_result_column("packets.forward.with_payload") or
                cap.has_result_column("packets.forward.rxmit") or
                cap.has_result_column("packets.forward.outseq") or
                cap.has_result_column("bytes.forward") or
                cap.has_result_column("bytes.forward.unique") or
                cap.has_result_column("bytes.forward.rxmit") or
                
                cap.has_result_column("responder.ip4") or
                cap.has_result_column("responder.port") or
                cap.has_result_column("packets.backward") or
                cap.has_result_column("packets.backward.syn") or
                cap.has_result_column("packets.backward.fin") or
                cap.has_result_column("packets.backward.rst") or
                cap.has_result_column("packets.backward.ack") or
                cap.has_result_column("packets.backward.pure_ack") or
                cap.has_result_column("packets.backward.with_payload") or
                cap.has_result_column("packets.backward.rxmit") or
                cap.has_result_column("packets.backward.outseq") or
                cap.has_result_column("bytes.backward") or
                cap.has_result_column("bytes.backward.unique") or
                cap.has_result_column("bytes.backward.rxmit") or
                
                cap.has_result_column("start") or
                cap.has_result_column("end") or
                cap.has_result_column("duration.ms") or
                cap.has_result_column("initiator.TTFP.ms") or
                cap.has_result_column("responder.TTFP.ms") or
                cap.has_result_column("initiator.TTLP.ms") or
                cap.has_result_column("responder.TTLP.ms") or
                cap.has_result_column("initiator.TTFA.ms") or
                cap.has_result_column("responder.TTFA.ms") or
                cap.has_result_column("initiator.ip4.isinternal") or
                cap.has_result_column("responder.ip4.isinternal") or
                cap.has_result_column("tstat.flow.class.conn") or
                cap.has_result_column("tstat.flow.class.p2p") or
                cap.has_result_column("tstat.flow.class.http")):
            raise ValueError("capability not acceptable")
    elif cap._label == "tstat-log_tcp_complete-end_to_end":   
        if not(cap.has_result_column("rtt.average.ms") or
                cap.has_result_column("rtt.min.ms") or
                cap.has_result_column("rtt.max.ms") or
                cap.has_result_column("rtt.stddev") or
                cap.has_result_column("rtt.samples") or
                cap.has_result_column("ttl.min") or
                cap.has_result_column("ttl.max")):
            raise ValueError("capability not acceptable")
    elif cap._label == "tstat-log_tcp_complete-tcp_options":   
        if not(cap.has_result_column("initiator.RFC1323.ws") or
                cap.has_result_column("initiator.RFC1323.ts") or
                cap.has_result_column("initiator.win_scale") or
                cap.has_result_column("initiator.SACK_set") or
                cap.has_result_column("initiator.SACK") or
                cap.has_result_column("initiator.MSS.bytes") or
                cap.has_result_column("initiator.segment.max.bytes") or
                cap.has_result_column("initiator.segment.min.bytes") or
                cap.has_result_column("initiator.window.max.bytes") or
                cap.has_result_column("initiator.window.min.bytes") or
                cap.has_result_column("initiator.window.zero") or
                cap.has_result_column("initiator.cwin.max.bytes") or
                cap.has_result_column("initiator.cwin.min.bytes") or
                cap.has_result_column("initiator.cwin.first.bytes") or
                cap.has_result_column("initiator.rxmit.RTO") or
                cap.has_result_column("initiator.rxmit.RTO.unnecessary") or
                cap.has_result_column("initiator.rxmit.FR") or
                cap.has_result_column("initiator.rxmit.FR.unnecessary") or
                cap.has_result_column("initiator.reordering") or
                cap.has_result_column("initiator.net_dup") or
                cap.has_result_column("initiator.unknown") or
                cap.has_result_column("initiator.flow_control") or
                cap.has_result_column("initiator.SYN.equal_seqno") or
                
                cap.has_result_column("responder.RFC1323.ws") or
                cap.has_result_column("responder.RFC1323.ts") or
                cap.has_result_column("responder.win_scale") or
                cap.has_result_column("responder.SACK_set") or
                cap.has_result_column("responder.SACK") or
                cap.has_result_column("responder.MSS.bytes") or
                cap.has_result_column("responder.segment.max.bytes") or
                cap.has_result_column("responder.segment.min.bytes") or
                cap.has_result_column("responder.window.max.bytes") or
                cap.has_result_column("responder.window.min.bytes") or
                cap.has_result_column("responder.window.zero") or
                cap.has_result_column("responder.cwin.max.bytes") or
                cap.has_result_column("responder.cwin.min.bytes") or
                cap.has_result_column("responder.cwin.first.bytes") or
                cap.has_result_column("responder.rxmit.RTO") or
                cap.has_result_column("responder.rxmit.RTO.unnecessary") or
                cap.has_result_column("responder.rxmit.FR") or
                cap.has_result_column("responder.rxmit.FR.unnecessary") or
                cap.has_result_column("responder.reordering") or
                cap.has_result_column("responder.net_dup") or
                cap.has_result_column("responder.unknown") or
                cap.has_result_column("responder.flow_control") or
                cap.has_result_column("responder.SYN.equal_seqno")):
            raise ValueError("capability not acceptable")
    elif cap._label == "tstat-log_tcp_complete-p2p_stats":   
        if not (cap.has_result_column("p2p.subtype") or
                cap.has_result_column("ed2k.data") or
                cap.has_result_column("ed2k.signaling") or
                cap.has_result_column("ed2k.i2r") or
                cap.has_result_column("ed2k.r2i") or
                cap.has_result_column("ed2k.chat")):
            raise ValueError("capability not acceptable")
    elif cap._label == "tstat-log_tcp_complete-layer7":   
        if not (cap.has_result_column("initiator.psh_separated") or
                cap.has_result_column("responder.psh_separated") or
                cap.has_result_column("ssl.hello.client") or
                cap.has_result_column("ssl.hello.server")):
            raise ValueError("capability not acceptable")          
    else:
        raise ValueError("capability doesn't exist")
