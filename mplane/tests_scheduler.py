#
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
#
# mPlane Protocol Reference Implementation
# Information Model and Element Registry
#
# (c) 2015 mPlane Consortium (http://www.ict-mplane.eu)
#          Author: Ciro Meregalli
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

from nose.tools import *
from mplane import azn
from mplane import tls
from mplane import model
from mplane import utils
from mplane import scheduler
import configparser
from os import path

import tornado.httpserver
import tornado.ioloop
import tornado.web
import threading
import urllib3
import time
import ssl



''' HELPERS '''


# FIXME: the following helper should be moved in mplane.utils module.

def get_config(config_file):
    """
    Open a config file, parse it and return a config object.
    """
    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(utils.search_path(config_file))
    return config


def create_capability():
    model.initialize_registry()
    cap = model.Capability()
    cap.set_when("now ... future / 1s")
    cap.add_parameter("source.ip4", "10.0.27.2")
    cap.add_parameter("destination.ip4")
    cap.add_result_column("delay.twoway.icmp.us.min")
    cap.add_result_column("delay.twoway.icmp.us.max")
    cap.add_result_column("delay.twoway.icmp.us.mean")
    cap.add_result_column("delay.twoway.icmp.count")
    cap.add_result_column("packets.lost")
    return cap


# Scheduler module tests

# Class service tests:

cap = create_capability()
service = scheduler.Service(cap)


def test_Service_init():
    assert_equal(service._capability, cap)


def test_Service_run():
    try:
        service.run(None, None)
    except NotImplementedError as e:
        assert_true(isinstance(e, NotImplementedError))


def test_Service_capability():
    assert_equal(service.capability(), cap)


# Is this method really needed? Why can't we use
# set_link method of model.Statement class?
def test_Service_capability_link():
    link = "http://dummy/link.json"
    service.set_capability_link(link)
    assert_equal(cap.get_link(), link)


def test_Service__repr__():
    assert_equal(repr(service),
                 "<Service for "+repr(cap)+">")


