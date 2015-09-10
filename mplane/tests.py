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


from nose.tools import assert_equal, assert_true, assert_false, raises
import mplane.azn
import mplane.tls
import mplane.utils
import mplane.model
import mplane.scheduler
import tornado.httpserver
import tornado.ioloop
import tornado.web
import configparser
import threading
import urllib3
import time
import ssl
import sys
import os
import io

# FIXME: this entire module abuses package-level variables.
#        fixing this would be nice but is relatively low priority.

###
### mplane.azn.py tests
###

conf_dir = os.path.abspath(os.path.join(os.path.dirname(__file__),"..","testdata"))
conf_file = 'component-test.conf'
config_path = os.path.join(conf_dir, conf_file)
config_path_no_tls = os.path.join(conf_dir, "component-test-no-tls.conf")
id_true_role = "org.mplane.Test.Clients.Client-1"
id_false_role = "Dummy"

def test_Authorization():
    res_none = mplane.azn.Authorization(None)
    assert_true(isinstance(res_none, mplane.azn.AuthorizationOff))
    res_auth = mplane.azn.Authorization(mplane.utils.get_config(config_path))
    assert_true(isinstance(res_auth, mplane.azn.AuthorizationOn))
    res_no_tls = mplane.azn.Authorization(mplane.utils.get_config(config_path_no_tls))
    assert_true(isinstance(res_no_tls, mplane.azn.AuthorizationOff))


def test_AuthorizationOn():
    mplane.model.initialize_registry()
    cap = mplane.model.Capability(label="test-log_tcp_complete-core")
    res = mplane.azn.AuthorizationOn(mplane.utils.get_config(config_path))
    assert_true(isinstance(res, mplane.azn.AuthorizationOn))
    assert_true(res.check(cap, id_true_role))
    assert_false(res.check(cap, id_false_role))


def test_AuthorizationOff():
    mplane.model.initialize_registry()
    cap = mplane.model.Capability(label="test-log_tcp_complete-core")
    res = mplane.azn.AuthorizationOff()
    assert_true(isinstance(res, mplane.azn.AuthorizationOff))
    assert_true(res.check(cap, id_true_role))

###
### mplane.tls.py tests
###

cert = mplane.utils.search_path(os.path.join(conf_dir, "Component-SSB.crt"))
key = mplane.utils.search_path(os.path.join(conf_dir, "Component-SSB-plaintext.key"))
ca_chain = mplane.utils.search_path(os.path.join(conf_dir, "root-ca.crt"))

identity = "org.mplane.SSB.Components.Component-1"
forged_identity = "org.example.test"

host = "127.0.0.1"
port = 8080

# No forged_identity
tls_with_file = mplane.tls.TlsState(config=mplane.utils.get_config(config_path))
# No TLS sections but with forged_identity
tls_with_file_no_tls = mplane.tls.TlsState(config=mplane.utils.get_config(config_path_no_tls),
                                           forged_identity=forged_identity)

def test_TLSState_init():
    assert_equal(tls_with_file._cafile, ca_chain)
    assert_equal(tls_with_file._certfile, cert)
    assert_equal(tls_with_file._keyfile, key)
    assert_equal(tls_with_file._identity, identity)

    assert_equal(tls_with_file_no_tls._cafile, None)
    assert_equal(tls_with_file_no_tls._certfile, None)
    assert_equal(tls_with_file_no_tls._keyfile, None)
    assert_equal(tls_with_file_no_tls._identity, forged_identity)


def test_TLSState_pool_for():
    http_pool = tls_with_file.pool_for("http", host, port)
    assert_true(isinstance(http_pool, urllib3.HTTPConnectionPool))
    https_pool = tls_with_file.pool_for("https", host, port)
    assert_true(isinstance(https_pool, urllib3.HTTPSConnectionPool))


def test_TLSState_pool_for_no_scheme():
    https_pool = tls_with_file.pool_for(None, host, port)
    assert_true(isinstance(https_pool, urllib3.HTTPSConnectionPool))
    http_pool = tls_with_file_no_tls.pool_for(None, host, port)
    assert_true(isinstance(http_pool, urllib3.HTTPConnectionPool))


@raises(ValueError)
def test_TLSState_pool_for_fallback():
    fallback_http_pool = tls_with_file_no_tls.pool_for("https", host, port)
    assert_false(isinstance(fallback_http_pool, urllib3.HTTPSConnectionPool))
    assert_true(isinstance(fallback_http_pool, urllib3.HTTPConnectionPool))


@raises(ValueError)
def test_TLSState_pool_for_file_scheme():
    tls_with_file.pool_for("file", host, port)


@raises(ValueError)
def test_TLSState_pool_for_unsupported_scheme():
    tls_with_file.pool_for("break me!", host, port)


def test_TLSState_forged_identity():
    assert_equal(tls_with_file.forged_identity(), None)
    assert_equal(tls_with_file_no_tls.forged_identity(), forged_identity)


def test_TLSState_get_ssl_options():
    import ssl
    output = dict(certfile=cert,
                  keyfile=key,
                  ca_certs=ca_chain,
                  cert_reqs=ssl.CERT_REQUIRED)
    assert_equal(tls_with_file.get_ssl_options(), output)
    assert_equal(tls_with_file_no_tls.get_ssl_options(), None)


def test_TLSState_extract_local_identity():
    local_identity = tls_with_file.extract_local_identity()
    assert_equal(local_identity, identity)
    local_identity = tls_with_file_no_tls.extract_local_identity()
    assert_equal(local_identity, mplane.tls.DUMMY_DN)
    local_identity = tls_with_file_no_tls.extract_local_identity(
        forged_identity)
    assert_equal(local_identity, forged_identity)


s_cert = mplane.utils.search_path(os.path.join(conf_dir, "Supervisor-SSB.crt"))
s_key = mplane.utils.search_path(os.path.join(conf_dir, "Supervisor-SSB-plaintext.key"))
s_ca_chain = mplane.utils.search_path(os.path.join(conf_dir, "root-ca.crt"))
url = urllib3.util.url.parse_url("https://127.0.0.1:8888")

s_identity = "org.mplane.SSB.Supervisors.Supervisor-1"


class getToken(tornado.web.RequestHandler):
    def get(self):
        self.write("It works!")

def runTornado():
    application = tornado.web.Application([
        (r'/', getToken),
    ], debug=True)

    http_server = tornado.httpserver.HTTPServer(application,
                                            ssl_options={
                                                "certfile": s_cert,
                                                "keyfile": s_key,
                                                "ca_certs": s_ca_chain,
                                                "cert_reqs": ssl.CERT_REQUIRED
                                            })

    http_server.listen(8888)
    tornado.ioloop.IOLoop.instance().start()

def stopTornado():
    tornado.ioloop.IOLoop.instance().stop()

def test_peer_identity():
    threading.Thread(target=runTornado).start()
    print("\nWaiting for Tornado to start...")
    time.sleep(0.5)

    assert_equal(tls_with_file.extract_peer_identity(url), s_identity)
    assert_equal(tls_with_file_no_tls.extract_peer_identity(url), mplane.tls.DUMMY_DN)
    try:
        tls_with_file.extract_peer_identity('break me!')
    except ValueError as e:
        assert_true(isinstance(e, ValueError))
        stopTornado()
        print("\nWaiting for Tornado to stop...")
        time.sleep(0.5)

#
# mplane.scheduler tests
#

def create_test_capability():
    mplane.model.initialize_registry()
    cap = mplane.model.Capability()
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
    spec = mplane.model.Specification(capability=st_cap)
    spec.set_parameter_value("destination.ip4", "10.0.37.2")
    spec.set_when("2017-12-24 22:18:42 + 1m / 1s")
    return spec

def create_test_results():
    res = mplane.model.Result(specification=st_spec)
    res.set_when("2017-12-24 22:18:42.993000 ... " +
                 "2017-12-24 22:19:42.991000")
    res.set_result_value("delay.twoway.icmp.us.min", 33155)
    res.set_result_value("delay.twoway.icmp.us.mean", 55166)
    res.set_result_value("delay.twoway.icmp.us.max", 192307)
    res.set_result_value("delay.twoway.icmp.count", 58220)
    return res

class SchedulerTestService(mplane.scheduler.Service):
    def run(self, specification, check_interrupt):
        return st_res

st_cap = create_test_capability()
st_spec = create_test_specification()
st_receipt = mplane.model.Receipt(specification=st_spec)
st_res = create_test_results()

service = mplane.scheduler.Service(st_cap)
test_service = SchedulerTestService(st_cap)


# Class Service tests:

def test_Service_init():
    assert_true(isinstance(service, mplane.scheduler.Service))
    # check parameter assignment
    assert_equal(service._capability, st_cap)


def test_Service_run():
    try:
        service.run(None, None)
    except NotImplementedError as e:
        assert_true(isinstance(e, NotImplementedError))


def test_TestService_run():
    assert_equal(test_service.run(None, None), st_res)


def test_Service_capability():
    assert_equal(service.capability(), st_cap)


# Is this method really needed? Why can't we use
# set_link method of mplane.model.Statement class?
def test_Service_capability_link():
    link = "http://dummy/link.json"
    service.set_capability_link(link)
    assert_equal(st_cap.get_link(), link)


def test_Service__repr__():
    assert_equal(repr(service),
                 "<Service for "+repr(st_cap)+">")


# Class Job tests:

job = mplane.scheduler.Job(test_service, st_spec)

def test_Job_init():
    assert_true(isinstance(job, mplane.scheduler.Job))
    # check parameter assignment
    assert_equal(job.service, test_service)
    assert_equal(job.specification, st_spec)
    assert_equal(job.session, None)
    assert_equal(job._callback, None)
    assert_true(isinstance(job.receipt, mplane.model.Receipt))
    assert_true(isinstance(job._interrupt, threading.Event))


def test_Job__repr__():
    assert_equal(repr(job),
                 "<Job for "+repr(st_spec)+">")


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
    assert_true(isinstance(job.get_reply(), mplane.model.Receipt))


def test_Job_run():
    assert_equal(job.result, None)
    job._run()
    assert_equal(job.result, st_res)


def test_Job_finished_true():
    # Job has run.
    assert_true(job.finished())


def test_Job_get_reply_result():
    # Job has run.
    assert_true(isinstance(job.get_reply(), mplane.model.Result))

# Create a job that fails
job_failure = mplane.scheduler.Job(service, st_spec)


def test_Job_failed():
    # Making job to fail.
    job_failure._run()
    assert_true(job_failure.failed)


def test_Job_get_reply_failed():
    # Job has failed.
    assert_true(isinstance(job_failure.get_reply(), mplane.model.Exception))

#
# mplane.utils tests
#

utils_conf_file = 'utils-test.conf'
utils_test_path = os.path.join(conf_dir, utils_conf_file)

def test_read_setting():
    res = mplane.utils.read_setting(utils_test_path, 'true_param')
    assert_true(res)
    res = mplane.utils.read_setting(utils_test_path, 'false_param')
    assert_false(res)
    res = mplane.utils.read_setting(utils_test_path, 'other_param')
    assert_equal(res, 'other')
    res = mplane.utils.read_setting(utils_test_path, 'missing_param')
    assert_equal(res, None)


@raises(ValueError)
def test_search_path():
    root_path = '/var'
    assert_equal(mplane.utils.search_path(root_path), root_path)
    existing_input_path = 'mplane'
    output_path = os.path.abspath('mplane')
    assert_equal(mplane.utils.search_path(existing_input_path), output_path)
    unexisting_input_path = 'missing'
    assert_equal(mplane.utils.search_path(unexisting_input_path), '')


@raises(ValueError)
def test_check_file():
    mplane.utils.check_file('missing')


def test_print_then_prompt():
    line = "this is a test"
    old_stdout = sys.stdout
    result = io.StringIO()
    sys.stdout = result
    mplane.utils.print_then_prompt(line)
    sys.stdout = old_stdout
    result_string = result.getvalue()
    assert_equal(result_string,
                 line+"\n|mplane| ")

def test_normalize_path():
    another_root_path = '/conf'
    assert_equal(mplane.utils.normalize_path(another_root_path), another_root_path)
    another_existing_input_path = 'conf'
    another_output_path = os.path.abspath('conf')
    assert_equal(mplane.utils.normalize_path(another_existing_input_path),
                 another_output_path)

def test_add_value_to():
    d = {1: ['one']}
    mplane.utils.add_value_to(d, 1, 'One')
    assert_equal(d, {1: ['one', 'One']})
    mplane.utils.add_value_to(d, 2, 'two')
    assert_equal(d, {1: ['one', 'One'], 2: ['two']})


def test_split_stmt_list():
    mplane.model.initialize_registry()
    cap = mplane.model.Capability()
    cap.set_when("now ... future / 1s")
    cap.add_parameter("source.ip4", "10.0.27.2")
    cap.add_parameter("destination.ip4")
    cap.add_result_column("delay.twoway.icmp.us.min")
    cap.add_result_column("delay.twoway.icmp.us.max")
    cap.add_result_column("delay.twoway.icmp.us.mean")
    cap.add_result_column("delay.twoway.icmp.count")
    cap.add_result_column("packets.lost")
    capjson = mplane.model.unparse_json(cap)
    res = mplane.utils.split_stmt_list('['+capjson+']')
    caps = []
    caps.append(cap)
    # using repr as no __eq__ methos is implemented fot capability objects
    assert_equal(repr(res[0]), repr(caps[0]))


def test_parse_url():
    scheme="http"
    host="www.mplane.org"
    port="8080"
    path="/test"
    url_str = scheme + "://" + host + ":" + port + path
    mplane_url = urllib3.util.Url(scheme=scheme,
                                  host=host,
                                  port=port,
                                  path=path)
    assert_equal(mplane.utils.parse_url(mplane_url), url_str)
    path = "test"
    mplane_url = urllib3.util.Url(scheme=scheme,
                                  host=host,
                                  port=port,
                                  path=path)
    assert_equal(mplane.utils.parse_url(mplane_url), url_str)
