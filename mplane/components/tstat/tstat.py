# mPlane Protocol Reference Implementation
# tStat component code
#
# (c) 2013-2014 mPlane Consortium (http://www.ict-mplane.eu)
#               Author: Stefano Pentassuglia
#               Author: Ali Safari Khatouni
#               Author: Stefano Traverso
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
#

from datetime import *
from time import sleep
import os
import configparser
import mplane.model
import mplane.scheduler
import mplane.utils
from multiprocessing import Process
import psutil

import subprocess
from mplane.components.tstat.tstat_exporters import tstat_rrd_exporter
from mplane.components.tstat.tstat_exporters import tstat_streaming_exporter

rrd_exporter_process = None

"""
Implements tStat capabilities and services

"""

def services(runtimeconf, tstat_rrd_path, config_path, math_path, System_ID):
    services = []
    if runtimeconf is not None:
        services.append(tStatExporterService(tcp_flows_capability(System_ID), mplane.utils.search_path(runtimeconf)))
        services.append(tStatExporterService(e2e_tcp_flows_capability(System_ID), mplane.utils.search_path(runtimeconf)))
        services.append(tStatExporterService(tcp_options_capability(System_ID), mplane.utils.search_path(runtimeconf)))
        services.append(tStatExporterService(tcp_p2p_stats_capability(System_ID), mplane.utils.search_path(runtimeconf)))
        services.append(tStatExporterService(tcp_layer7_capability(System_ID), mplane.utils.search_path(runtimeconf)))
        services.append(tStatExporterService(rrd_capability(System_ID), mplane.utils.search_path(runtimeconf), tstat_rrd_path))
        services.append(tStatExporterService(exporter_rrd_capability(System_ID), mplane.utils.search_path(runtimeconf), tstat_rrd_path, config_path))
        services.append(tStatExporterService(http_trans_capability(System_ID), mplane.utils.search_path(runtimeconf)))
        services.append(tStatExporterService(exporter_streaming_capability(System_ID), mplane.utils.search_path(runtimeconf)))
        services.append(tStatExporterService(exporter_log_capability(System_ID), mplane.utils.search_path(runtimeconf), config_path, math_path=math_path))
    else:
        raise ValueError("missing 'runtimeconf' parameter for tStat capabilities")
    return services


def tcp_flows_capability(System_ID = None):
    cap = mplane.model.Capability(label="tstat-log_tcp_complete-core", when = "now ... future")
    cap.add_parameter("System_ID",System_ID)
    cap.add_metadata("System_type", "tStat")
    cap.add_metadata("System_ID", "tStat-Proxy-111")
    cap.add_metadata("System_version", "0.1")
    cap.add_result_column("source.ip4")
    cap.add_result_column("source.port")
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

    cap.add_result_column("destination.ip4")
    cap.add_result_column("destination.port")
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
    cap.add_result_column("source.TTFP.ms")
    cap.add_result_column("destination.TTFP.ms")
    cap.add_result_column("source.TTLP.ms")
    cap.add_result_column("destination.TTLP.ms")
    cap.add_result_column("source.TTFA.ms")
    cap.add_result_column("destination.TTFA.ms")
    cap.add_result_column("source.ip4.isinternal")
    cap.add_result_column("destination.ip4.isinternal")
    cap.add_result_column("tstat.flow.class.conn")
    cap.add_result_column("tstat.flow.class.p2p")
    cap.add_result_column("tstat.flow.class.http")
    return cap

def e2e_tcp_flows_capability(System_ID = None):
    cap = mplane.model.Capability(label="tstat-log_tcp_complete-end_to_end", when = "now ... future")
    cap.add_parameter("System_ID",System_ID)
    cap.add_metadata("System_type", "tStat")
    cap.add_metadata("System_ID", "tStat-Proxy-111")
    cap.add_metadata("System_version", "0.1")
    cap.add_result_column("rtt.average.ms")
    cap.add_result_column("rtt.min.ms")
    cap.add_result_column("rtt.max.ms")
    cap.add_result_column("rtt.stddev")
    cap.add_result_column("rtt.samples")
    cap.add_result_column("ttl.min")
    cap.add_result_column("ttl.max")
    return cap

def tcp_options_capability(System_ID = None):
    cap = mplane.model.Capability(label="tstat-log_tcp_complete-tcp_options", when = "now ... future")
    cap.add_parameter("System_ID",System_ID)
    cap.add_metadata("System_type", "tStat")
    cap.add_metadata("System_ID", "tStat-Proxy-111")
    cap.add_metadata("System_version", "0.1")
    cap.add_result_column("source.RFC1323.ws")
    cap.add_result_column("source.RFC1323.ts")
    cap.add_result_column("source.win_scale")
    cap.add_result_column("source.SACK_set")
    cap.add_result_column("source.SACK")
    cap.add_result_column("source.MSS.bytes")
    cap.add_result_column("source.segment.max.bytes")
    cap.add_result_column("source.segment.min.bytes")
    cap.add_result_column("source.window.max.bytes")
    cap.add_result_column("source.window.min.bytes")
    cap.add_result_column("source.window.zero")
    cap.add_result_column("source.cwin.max.bytes")
    cap.add_result_column("source.cwin.min.bytes")
    cap.add_result_column("source.cwin.first.bytes")
    cap.add_result_column("source.rxmit.RTO")
    cap.add_result_column("source.rxmit.RTO.unnecessary")
    cap.add_result_column("source.rxmit.FR")
    cap.add_result_column("source.rxmit.FR.unnecessary")
    cap.add_result_column("source.reordering")
    cap.add_result_column("source.net_dup")
    cap.add_result_column("source.unknown")
    cap.add_result_column("source.flow_control")
    cap.add_result_column("source.SYN.equal_seqno")

    cap.add_result_column("destination.RFC1323.ws")
    cap.add_result_column("destination.RFC1323.ts")
    cap.add_result_column("destination.win_scale")
    cap.add_result_column("destination.SACK_set")
    cap.add_result_column("destination.SACK")
    cap.add_result_column("destination.MSS.bytes")
    cap.add_result_column("destination.segment.max.bytes")
    cap.add_result_column("destination.segment.min.bytes")
    cap.add_result_column("destination.window.max.bytes")
    cap.add_result_column("destination.window.min.bytes")
    cap.add_result_column("destination.window.zero")
    cap.add_result_column("destination.cwin.max.bytes")
    cap.add_result_column("destination.cwin.min.bytes")
    cap.add_result_column("destination.cwin.first.bytes")
    cap.add_result_column("destination.rxmit.RTO")
    cap.add_result_column("destination.rxmit.RTO.unnecessary")
    cap.add_result_column("destination.rxmit.FR")
    cap.add_result_column("destination.rxmit.FR.unnecessary")
    cap.add_result_column("destination.reordering")
    cap.add_result_column("destination.net_dup")
    cap.add_result_column("destination.unknown")
    cap.add_result_column("destination.flow_control")
    cap.add_result_column("destination.SYN.equal_seqno")
    return cap

def tcp_p2p_stats_capability(System_ID = None):
    cap = mplane.model.Capability(label="tstat-log_tcp_complete-p2p_stats", when = "now ... future")
    cap.add_parameter("System_ID",System_ID)
    cap.add_metadata("System_type", "tStat")
    cap.add_metadata("System_ID", "tStat-Proxy-111")
    cap.add_metadata("System_version", "0.1")
    cap.add_result_column("p2p.subtype")
    cap.add_result_column("ed2k.data")
    cap.add_result_column("ed2k.signaling")
    cap.add_result_column("ed2k.i2r")
    cap.add_result_column("ed2k.r2i")
    cap.add_result_column("ed2k.chat")
    return cap    

def tcp_layer7_capability(System_ID = None):
    cap = mplane.model.Capability(label="tstat-log_tcp_complete-layer7", when = "now ... future")
    cap.add_parameter("System_ID",System_ID)
    cap.add_metadata("System_type", "tStat")
    cap.add_metadata("System_ID", "tStat-Proxy-111")
    cap.add_metadata("System_version", "0.1")
    cap.add_result_column("source.psh_separated")
    cap.add_result_column("destination.psh_separated")
    cap.add_result_column("ssl.hello.client")
    cap.add_result_column("ssl.hello.server")
    return cap

def http_trans_capability(System_ID = None):
    cap = mplane.model.Capability(label="tstat-log_http_complete", when = "now ... future")
    cap.add_parameter("System_ID",System_ID)
    cap.add_metadata("System_type", "tStat")
    cap.add_metadata("System_ID", "tStat-Proxy-111")
    cap.add_metadata("System_version", "0.1")
    cap.add_result_column("source.ip4")
    cap.add_result_column("source.port")
    cap.add_result_column("destination.ip4")
    cap.add_result_column("destination.port")
    cap.add_result_column("time")

    cap.add_result_column("request.method")
    cap.add_result_column("request.hostname")
    cap.add_result_column("request.fqdn")
    cap.add_result_column("request.path")
    cap.add_result_column("request.referer")
    cap.add_result_column("request.user_agent")

    cap.add_result_column("response.http")
    cap.add_result_column("response.code")
    cap.add_result_column("response.content_len")
    cap.add_result_column("response.content_type")
    cap.add_result_column("response.content_range")
    cap.add_result_column("response.location")

    return cap

def exporter_streaming_capability(System_ID = None):
    cap = mplane.model.Capability(label="tstat-exporter_streaming", when = "now ... future")
    cap.add_parameter("System_ID",System_ID)
    cap.add_metadata("System_type", "tStat")
    cap.add_metadata("System_ID", "tStat-Proxy-111")
    cap.add_metadata("System_version", "0.1")
    cap.add_parameter("repository.url")
    cap.add_parameter("log.folder")
    cap.add_parameter("log.type")
    cap.add_parameter("log.time")
    return cap

def rrd_capability(System_ID = None):
    cap = mplane.model.Capability(label="tstat-log_rrds", when = "now ... future")
    cap.add_parameter("System_ID",System_ID)
    cap.add_metadata("System_type", "tStat")
    cap.add_metadata("System_ID", "tStat-Proxy-111")
    cap.add_metadata("System_version", "0.1")

    cap.add_result_column("Ethernet.Related.metrics")
    cap.add_result_column("IP.Related.metrics")
    cap.add_result_column("TCP.Related.metrics")
    cap.add_result_column("UDP.Related.metrics")
    cap.add_result_column("MMedia.Related.metrics")
    cap.add_result_column("Classifier.Related.metrics")
    cap.add_result_column("P2P-TV.Related.metrics")
    cap.add_result_column("Video.Related.metrics")
    cap.add_result_column("Profile.Related.metrics")

    return cap

def exporter_rrd_capability(System_ID = None):
    cap = mplane.model.Capability(label="tstat-exporter_rrd", when = "past ... future")
    cap.add_parameter("System_ID",System_ID)
    cap.add_metadata("System_type", "tStat")
    cap.add_metadata("System_ID", "tStat-Proxy-111")
    cap.add_metadata("System_version", "0.1")
    cap.add_parameter("repository.url")    
    cap.add_result_column("rrdtimestamp")
    cap.add_result_column("rrdMetirc")
    cap.add_result_column("rrdValue")
    #cap.add_result_column("repository.capability.token")
    return cap

def exporter_log_capability(System_ID = None):
    cap = mplane.model.Capability(label="tstat-exporter_log", when = "past ... future")
    cap.add_parameter("System_ID",System_ID)
    cap.add_metadata("System_type", "tStat")
    cap.add_metadata("System_ID", "tStat-Proxy-111")
    cap.add_metadata("System_version", "0.1")
    cap.add_parameter("repository.url")
    return cap

class tStatExporterService(mplane.scheduler.Service):
    """
    This class handles the capabilities exposed by the proxy:
    executes them, and fills the results

    """

    def __init__(self, cap, fileconf, tstat_rrd_path = None, config_path = None, math_path = None):
        super(tStatExporterService, self).__init__(cap)
        if config_path is not None:
            # Read the configuration file
            self.config = configparser.ConfigParser()
            self.config.optionxform = str
            self.config.read(mplane.utils.search_path(config_path))
        else:
            self.config = None
        self._fileconf = fileconf
        self.rrd_path = tstat_rrd_path
        self.math_path = math_path

    def wait_and_stop(self, end_time, check_interrupt, spec, process):
        while (datetime.utcnow() <= end_time):
            if check_interrupt():
                break
            sleep(0.5)
        if process is not None:
            parent = psutil.Process(process.pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()

        return

    def run(self, spec, check_interrupt):
        """
        Execute this Service

        """
        global rrd_exporter_process

        (start_time , end_time) = spec._when.datetimes()
        duration = spec.when().duration().total_seconds()

        # crate the math code time format
        time_format = start_time.strftime("%Y-%m-%dT%H:%M:%S")

        process = None
        # check which capability family 
        if "tstat-log" in spec.get_label():
            # start measurement changing the tstat conf file
            self.change_conf(spec.get_label(), True)

        elif "tstat-exporter_rrd" in spec.get_label():
            if rrd_exporter_process is not None:
                parent = psutil.Process(rrd_exporter_process.pid)
                for child in parent.children(recursive=True):
                    child.kill()
                parent.kill()
            print ("kill already existing tstat-exporter_rrd !!!")
            process = tstat_rrd_exporter.run(self, self.config, self.rrd_path, spec,  start_time )

        elif "tstat-exporter_log" in spec.get_label():
            #The math executable for export log
            repository_url = str(spec.get_parameter_value("repository.url"))
            curr_dir = os.getcwd()
            os.chdir(self.math_path)
            shell_command = 'exec ./math_probe --config math_probe.xml --repoUrl %s --startTime %s' % (repository_url,time_format)
            print ("Command : %s" %shell_command)
            process = subprocess.Popen(shell_command, stdout=subprocess.PIPE, shell=True)#, preexec_fn=os.setsid)
            os.chdir(curr_dir)

        elif "tstat-exporter_streaming" in spec.get_label():
            print(spec.get_label(), spec.get_parameter_value("repository.url"),
                spec.get_parameter_value("log.type"),
                spec.get_parameter_value("log.time"),
                spec.get_parameter_value("log.folder"))

            repoip = spec.get_parameter_value("repository.url").split(":")[-2]
            repoport = spec.get_parameter_value("repository.url").split(":")[-1]

            process = Process(target=tstat_streaming_exporter.run, args=[repoip, repoport, 
                spec.get_parameter_value("log.type"),
                spec.get_parameter_value("log.time"),
                spec.get_parameter_value("log.folder"),
                start_time,
                duration])
            process.start()
        else:
            raise ValueError("Capability family doesn't exist")

        rrd_exporter_process = process
        
        self.wait_and_stop(end_time, check_interrupt, spec, process)

        # wait for specification execution
        if "tstat-log" in spec.get_label():
            # terminate measurement changing the tstat conf file
            self.change_conf(spec.get_label(), False)
        elif "tstat-exporter_streaming" in spec.get_label() :
            print("tstat-exporter_streaming Disabled \n")
        elif "tstat-exporter_rrd" in spec.get_label() :
            print("tstat-exporter_rrd Disabled \n")
        elif "tstat-exporter_log" in spec.get_label() :
            print("tstat-exporter_log Disabled \n")

        res = self.fill_res(spec, start_time, end_time)

        return res

    def change_conf(self, cap_label, enable):
        """
        Changes the needed flags in the tStat runtime.conf file

        """
        newlines = []
        f = open(self._fileconf, 'r')
        for line in f:

            # read parameter names and values (discard comments or empty lines)
            if (line[0] != '[' and line[0] != '#' and
                line[0] != '\n' and line[0] != ' '):    
                param = line.split('#')[0]
                param_name = param.split(' = ')[0]

                # change flags according to the measurement requested
                if enable == True:

                    # in order to activate optional sets, the basic set (log_tcp_complete) must be active too
                    if (cap_label == "tstat-log_tcp_complete-core" and param_name == 'log_tcp_complete'):
                        newlines.append(line.replace('0', '1'))

                    elif (cap_label == "tstat-log_tcp_complete-end_to_end" and (
                        param_name == 'tcplog_end_to_end' 
                        or param_name == 'log_tcp_complete')):
                        newlines.append(line.replace('0', '1'))

                    elif (cap_label == "tstat-log_tcp_complete-tcp_options" and (
                        param_name == 'tcplog_options' or
                        param_name == 'log_tcp_complete')):
                        newlines.append(line.replace('0', '1'))

                    elif (cap_label == "tstat-log_tcp_complete-p2p_stats" and (
                        param_name == 'tcplog_p2p' or
                        param_name == 'log_tcp_complete')):
                        newlines.append(line.replace('0', '1'))

                    elif (cap_label == "tstat-log_tcp_complete-layer7" and (
                        param_name == 'tcplog_layer7' or
                        param_name == 'log_tcp_complete')):
                        newlines.append(line.replace('0', '1'))

                    elif (cap_label == "tstat-log_rrds" and 
                        param_name == 'rrd_engine'):
                        newlines.append(line.replace('0', '1'))

                    elif (cap_label == "tstat-log_http_complete" and param_name == 'log_http_complete'):
                        newlines.append(line.replace('0', '1'))

                    else:
                        newlines.append(line)
                else:
                    if (cap_label == "tstat-log_tcp_complete-end_to_end" and param_name == 'tcplog_end_to_end'):
                        newlines.append(line.replace('1', '0'))

                    elif (cap_label == "tstat-log_tcp_complete-tcp_options" and param_name == 'tcplog_options'):
                        newlines.append(line.replace('1', '0'))

                    elif (cap_label == "tstat-log_tcp_complete-p2p_stats" and param_name == 'tcplog_p2p'):
                        newlines.append(line.replace('1', '0'))

                    elif (cap_label == "tstat-log_tcp_complete-layer7" and param_name == 'tcplog_layer7'):
                        newlines.append(line.replace('1', '0'))

                    elif (cap_label == "tstat-log_rrds" and param_name == 'rrd_engine'):
                        newlines.append(line.replace('1', '0'))

                    elif (cap_label == "tstat-log_http_complete" and param_name == 'log_http_complete'):
                        newlines.append(line.replace('1', '0'))

                    else:
                        newlines.append(line) 
            else:
                newlines.append(line)
        f.close()

        f = open(self._fileconf, 'w')
        f.writelines(newlines)
        f.close

    def fill_res(self, spec, start, end):
        """
        Create a Result statement, fill it and return it

        """

        # derive a result from the specification
        res = mplane.model.Result(specification=spec)

        # put actual start and end time into result
        res.set_when(mplane.model.When(a = start, b = end))

        # fill result columns with DUMMY values
        for column_name in res.result_column_names():
            prim = res._resultcolumns[column_name].primitive_name()
            if prim == "natural":
                res.set_result_value(column_name, 0)
            elif prim == "string":
                res.set_result_value(column_name, "hello")
            elif prim == "real":
                res.set_result_value(column_name, 0.0)
            elif prim == "boolean":
                res.set_result_value(column_name, True)
            elif prim == "time":
                res.set_result_value(column_name, start)
            elif prim == "address":
                res.set_result_value(column_name, "192.168.0.1")
            elif prim == "url":
                res.set_result_value(column_name, "www.google.com")
        return res