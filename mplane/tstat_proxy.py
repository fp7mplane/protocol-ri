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
#

"""
Implements tStat prototype for integration into 
the mPlane reference implementation.

"""

from datetime import datetime
from time import sleep
import mplane.model
import mplane.scheduler
import mplane.httpsrv
import mplane.tstat_caps
import argparse
import sys

class tStatService(mplane.scheduler.Service):
    def __init__(self, cap, fileconf):
        # verify the capability is acceptable
        mplane.tstat_caps.check_cap(cap)
        super(tStatService, self).__init__(cap)
        #self._logdir = logdir
        self._fileconf = fileconf

    def change_conf(self, cap_label, enable):
        newlines = []
        f = open(self._fileconf, 'r')
        for line in f:

            if (line[0] != '[' and line[0] != '#' and
                line[0] != '\n' and line[0] != ' '):    # discard useless lines
                param = line.split('#')[0]
                param_name = param.split(' = ')[0]
                
                if enable == True:
                    if (cap_label == "tstat-log_tcp_complete-core" and param_name == 'log_tcp_complete'):
                        newlines.append(line.replace('0', '1'))

                    # in order to activate optional sets, the basic set (log_tcp_complete) must be active too
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
                    else:
                        newlines.append(line)
                else:
                    if (cap_label == "tstat-log_tcp_complete-end_to_end" and param_name == 'tcplog_end_to_end'):
                        print('AAA')
                        newlines.append(line.replace('1', '0'))

                    elif (cap_label == "tstat-log_tcp_complete-tcp_options" and param_name == 'tcplog_options'):
                        newlines.append(line.replace('1', '0'))

                    elif (cap_label == "tstat-log_tcp_complete-p2p_stats" and param_name == 'tcplog_p2p'):
                        newlines.append(line.replace('1', '0'))

                    elif (cap_label == "tstat-log_tcp_complete-layer7" and param_name == 'tcplog_layer7'):
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

        # derive a result from the specification
        res = mplane.model.Result(specification=spec)

        # put actual start and end time into result
        res.set_when(mplane.model.When(a = start, b = end))
        
        return res

    def run(self, spec, check_interrupt):
        start_time = datetime.utcnow()

        #change runtime.conf
        self.change_conf(spec._label, True)

        # wait for specification execution
        wait_time = spec._when.timer_delays()
        wait_seconds = wait_time[1]
        if wait_seconds != None:
            sleep(wait_seconds)
        end_time = datetime.utcnow()

        # fill result message from tStat log
        self.change_conf(spec._label, False)
        print("specification " + spec._label + ": start = " + str(start_time) + ", end = " + str(end_time))
        res = self.fill_res(spec, start_time, end_time)
        return res

#def parse_args():
#    global args
#    #parser = argparse.ArgumentParser(description="Run a tStat probe")
#    #parser.add_argument('--logdir', metavar="log-directory",
#    #                    help="Directory from where tStat log files are retrieved")
#    #parser.add_argument('--fileconf', metavar="conf-file",
#    #                    help="runtime.conf file path")
#    #args = parser.parse_args()


# For right now, start a Tornado-based ping server
if __name__ == "__main__":
    global args

    parser = argparse.ArgumentParser(description='run a Tstat mPlane proxy')
    ## service options
    parser.add_argument('-p', '--service-port', metavar='port', dest='SERVICE_PORT', default=mplane.httpsrv.DEFAULT_LISTEN_PORT, type=int, \
                        help = 'run the service on the specified port [default=%s]' % mplane.httpsrv.DEFAULT_LISTEN_PORT)
    parser.add_argument('-H', '--service-ipaddr', metavar='ip', dest='SERVICE_IP', default=mplane.httpsrv.DEFAULT_LISTEN_IP4, \
                        help = 'run the service on the specified IP address [default=%s]' % mplane.httpsrv.DEFAULT_LISTEN_IP4)
    parser.add_argument('--disable-sec', action='store_true', default=False, dest='DISABLE_SEC',
                        help='Disable secure communication')
    parser.add_argument('-c', '--certfile', metavar="path", dest='CERTFILE', default = None,
                        help="Location of the configuration file for certificates")

    ## Tstat options
    ## this option will be used when the async export will be developed
    #parser.add_argument('-s', '--tstat-logsdir', metavar = 'path', dest = 'TSTAT_LOGSDIR', default = None, required = True,
    #                    help = 'Tstat output logs directory path')
    parser.add_argument('-T', '--tstat-runtimeconf', metavar = 'path', dest = 'TSTAT_RUNTIMECONF', default = None, required = True,
                        help = 'Tstat runtime.conf configuration file path')
    args = parser.parse_args()

    ## check for the basic arguments
    #if not args.TSTAT_LOGSDIR:
    #    print('error: missing -s|--tstat-logsdir\n')
    #    parser.print_help()
    #    sys.exit(1)

    if not args.TSTAT_RUNTIMECONF:
        print('error: missing -T|--tstat-runtimeconf\n')
        parser.print_help()
        sys.exit(1)

    if args.DISABLE_SEC == False and not args.CERTFILE:
        print('error: missing -C|--certfile\n')
        parser.print_help()
        sys.exit(1)
        #raise ValueError("Need --logdir and --fileconf as parameters")


    security = not args.DISABLE_SEC
    if security:
        mplane.utils.check_file(args.CERTFILE)

    mplane.model.initialize_registry()

    scheduler = mplane.scheduler.Scheduler(security)
    scheduler.add_service(tStatService(mplane.tstat_caps.tcp_flows_capability(), args.TSTAT_RUNTIMECONF))
    scheduler.add_service(tStatService(mplane.tstat_caps.e2e_tcp_flows_capability(), args.TSTAT_RUNTIMECONF))
    scheduler.add_service(tStatService(mplane.tstat_caps.tcp_options_capability(), args.TSTAT_RUNTIMECONF))
    scheduler.add_service(tStatService(mplane.tstat_caps.tcp_p2p_stats_capability(), args.TSTAT_RUNTIMECONF))
    scheduler.add_service(tStatService(mplane.tstat_caps.tcp_layer7_capability(), args.TSTAT_RUNTIMECONF))

    mplane.httpsrv.runloop(scheduler, security, args.CERTFILE, address = args.SERVICE_IP, port = args.SERVICE_PORT)
