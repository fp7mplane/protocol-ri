# (c) 2013-2014 mPlane Consortium (http://www.ict-mplane.eu)
#               Author: Ali Safari Khatouni
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

from datetime import datetime, timedelta
from time import sleep, time, mktime


from socket import socket
import sys
import mplane

import multiprocessing
from os import listdir,rename
from os.path import isfile, join, isdir

import json
import rrdtool
from dateutil import tz

import pickle
import gzip


DEFAULT_RRD_INTERVAL = 300
RESULT_PATH_INDIRECT = "register/result/indirect_export"


"""
Hint:

In the rrd export we assume that each recieving time expressed in UTC timezone (according to mplane time format)
before fetching the data we chnage the utc time to the machine local timezone


"""

def change_to_local_tzone(start_zone):

    from_zone = tz.tzutc()
    to_zone = tz.tzlocal()
    start_utc = start_zone.replace(tzinfo=from_zone)
    start_local = start_utc.astimezone(to_zone)

    return start_local

def connect_to_repository(self, tls, repository_ip4, repository_port):
    """
    connect to repository for Indirect export RRD files
    repository address extract from the specification parameters
    it can support HTTPS and HTTP  

    """
    self.repo_pool = tls.pool_for(None, host=repository_ip4, port=repository_port)
    return

def read_latest_fetched_data(self, path,interface):
    if ( isdir (join(path,interface) ) and isfile(join(path,interface,"latest_fetched_data.txt")) ) :
        fp = open (join(path,interface,"latest_fetched_data.txt"), "r")
        latest_time = fp.readline()
        if (latest_time.isdigit()):
            return  latest_time
    return 0

def write_latest_fetched_data(self, path,interface,last_fetched_time):
    if ( isdir (join(path,interface)) ) :
        fp = open (join(path,interface,"latest_fetched_data.txt"), "w")
        fp.write(str(last_fetched_time))

# change the start time from begining
def indirect_export(self, tls, path, spec, start,interval):
    """
    
    Indirect Export the RRD metrics to repository
    first connect then fetch finally send result to Repository
    it runs until the process stops

    """
    # Check the repository URL but it is better to check in Client !
    if (len(spec.get_parameter_value("repository.url").split(":")) < 2):
        return False

    repository_ip = str(spec.get_parameter_value("repository.url").split(":")[-2])
    repository_port = int(spec.get_parameter_value("repository.url").split(":")[-1])

    connect_to_repository(self, tls, repository_ip, repository_port)

    # change the time expressed in UTC to local timezone 
    start_local = change_to_local_tzone(start)

    print ("local start time :" + str(start_local))
    print ("UTC start time :" + str(start))
    while True:

        if ( not isdir (path)):
            print ("RRD directory does not exist !\n ")
            exit()
        in_path=path
        Node_list = [ d for d in listdir(in_path) if isdir(join(in_path,d)) ]

        for node in Node_list:
            in_path=join(path,node)

            Interface_list = [ d for d in listdir(in_path) if isdir(join(in_path,d)) ]
            for interface in Interface_list:
                in_path=join(path,node,interface)

                rrd_file_list = [ d for d in listdir(in_path) if (isfile(join(in_path,d)) and d.endswith(".pickle.gz") ) ]
                rrd_file_list.sort(reverse=False)

                for f in rrd_file_list:
                    result_list=[]
                    try:
                        with gzip.open(join(in_path,f) , "rb") as fp: 
                            binary_content=fp.read()
                            result_list=pickle.loads(binary_content)
                            result_list.insert(0,(node,interface))
                        rename(join(in_path,f),join(in_path,f.replace("pickle","exported")))
                        if (len (result_list) > 0):
                            print ("result list size :    " + str(len (result_list)))
                            while ( not return_results_to_repository(self, result_list) ):
                                connect_to_repository(self, tls, repository_ip, repository_port)
                                sleep (10)
                            sleep(10)
                    except:
                        print("Unexpected error:", sys.exc_info()[0])
                        break        
                sleep(10)

def return_results_to_repository(self, res):
    """
    It returns the fetched data with POST to
    repository proxy    

    """
    url = "/" + RESULT_PATH_INDIRECT

    # send result to the Repository
    rec_res = self.repo_pool.urlopen('POST', url, retries = 10,
    body=json.dumps(res).encode("utf-8"), 
    headers={"content-type": "application/json"})

    # handle response
    if rec_res.status == 200:
        print("RRD logs successfully returned!")
        return True
    else:
        print("Error returning Result for " )
        print("Repository said: " + str(rec_res.status) + " - " + rec_res.data.decode("utf-8"))
        return False



def run(self, config, path, spec, start):

    """
    The actual Indirect RRD Export execute here 
    with creating a new process here  

    """

    tls = mplane.tls.TlsState(config)

    proc = multiprocessing.Process(target=indirect_export, args=[self, tls, path, spec, start, DEFAULT_RRD_INTERVAL])
    proc.deamon = True
    print("tstat-exporter_rrd Enabled \n")
    proc.start()
    return proc
