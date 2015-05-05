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


def create_test_capability():
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


def create_test_specification():
    spec = model.Specification(capability=cap)
    spec.set_parameter_value("destination.ip4", "10.0.37.2")
    spec.set_when("2017-12-24 22:18:42 + 1m / 1s")
    return spec


def create_test_results():
    res = model.Result(specification=spec)
    res.set_when("2017-12-24 22:18:42.993000 ... " +
                 "2017-12-24 22:19:42.991000")
    res.set_result_value("delay.twoway.icmp.us.min", 33155)
    res.set_result_value("delay.twoway.icmp.us.mean", 55166)
    res.set_result_value("delay.twoway.icmp.us.max", 192307)
    res.set_result_value("delay.twoway.icmp.count", 58220)
    return res


class TestService(scheduler.Service):
    def run(self, specification, check_interrupt):
        return res
   
# Scheduler module tests

cap = create_test_capability()
spec = create_test_specification()
receipt = model.Receipt(specification=spec)
res = create_test_results()

service = scheduler.Service(cap)
test_service = TestService(cap)

# Class Service tests:


def test_Service_init():
    assert_true(isinstance(service, scheduler.Service))
    # check parameter assignment
    assert_equal(service._capability, cap)


def test_Service_run():
    try:
        service.run(None, None)
    except NotImplementedError as e:
        assert_true(isinstance(e, NotImplementedError))


def test_TestService_run():
    assert_equal(test_service.run(None, None), res)


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


# Class Job tests:

job = scheduler.Job(test_service, spec)


def test_Job_init():
    assert_true(isinstance(job, scheduler.Job))
    # check parameter assignment
    assert_equal(job.service, test_service)
    assert_equal(job.specification, spec)
    assert_equal(job.session, None)
    assert_equal(job._callback, None)
    assert_true(isinstance(job.receipt, model.Receipt))
    assert_true(isinstance(job._interrupt, threading.Event))


def test_Job__repr__():
    assert_equal(repr(job),
                 "<Job for "+repr(spec)+">")


def test_Job_check_interrupt():
    # Interrupt is not set since job has not run (yet).
    assert_false(job._interrupt.is_set())

    
def test_Job_set_interrupt():
    # Set interrupt
    job.interrupt()
    assert_true(job._interrupt.is_set())


def test_Job_finished_false():
    # Job has not run (yet).
    assert_false(job.finished())


def test_Job_get_reply_receipt():
    # Job has not run (yet).
    assert_true(isinstance(job.get_reply(), model.Receipt))


def test_Job_run():
    assert_equal(job.result, None)
    job._run()
    assert_equal(job.result, res)


def test_Job_finished_true():
    # Job has run.
    assert_true(job.finished())


def test_Job_get_reply_result():
    # Job has run.
    assert_true(isinstance(job.get_reply(), model.Result))

# Create a job that fails
job_failure = scheduler.Job(service, spec)


def test_Job_failed():
    # Making job to fail.
    job_failure._run()
    assert_true(job_failure.failed)


def test_Job_get_reply_failed():
    # Job has failed.
    assert_true(isinstance(job_failure.get_reply(), model.Exception))
