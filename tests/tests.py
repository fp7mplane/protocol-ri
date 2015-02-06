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
import configparser
from os import path


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


''' Authorization Module Tests '''


def setup():
    print("Starting tests...")


''' Set up test fixtures '''

conf_dir = path.dirname(__file__)
conf_file = 'component-test.conf'
config_path = path.join(conf_dir, conf_file)
config_path_no_tls = path.join(conf_dir, "component-test-no-tls.conf")

# build up the capabilities' label

model.initialize_registry()
cap = model.Capability(label="test-log_tcp_complete-core")

# set the identity

id_true_role = "org.mplane.Test.Clients.Client-1"
id_false_role = "Dummy"


def test_Authorization():
    res_none = azn.Authorization(None)
    assert_true(isinstance(res_none, azn.AuthorizationOff))
    res_auth = azn.Authorization(config_path)
    assert_true(isinstance(res_auth, azn.AuthorizationOn))
    res_no_tls = azn.Authorization(config_path_no_tls)
    assert_true(isinstance(res_no_tls, azn.AuthorizationOff))


def test_AuthorizationOn():
    res = azn.AuthorizationOn(config_path)
    assert_true(isinstance(res, azn.AuthorizationOn))
    assert_true(res.check(cap, id_true_role))
    assert_false(res.check(cap, id_false_role))


def test_AuthorizationOff():
    res = azn.AuthorizationOff()
    assert_true(isinstance(res, azn.AuthorizationOff))
    assert_true(res.check(cap, id_true_role))


''' TLS module tests '''

cert = utils.search_path(path.join(conf_dir, "Component-SSB.crt"))
key = utils.search_path(path.join(conf_dir, "Component-SSB-plaintext.key"))
ca_chain = utils.search_path(path.join(conf_dir, "root-ca.crt"))

identity = "org.mplane.SSB.Components.Component-1"
forged_identity = "org.example.test"

host = "127.0.0.1"
port = 8080

# No forged_identity
tls_with_file = tls.TlsState(config=get_config(config_path))
# No TLS sections but with forged_identity
tls_with_file_no_tls = tls.TlsState(config=get_config(config_path_no_tls),
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
    import urllib3
    http_pool = tls_with_file.pool_for("http", host, port)
    assert_true(isinstance(http_pool, urllib3.HTTPConnectionPool))
 
    https_pool = tls_with_file.pool_for("https", host, port)
    assert_true(isinstance(https_pool, urllib3.HTTPSConnectionPool))
    

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


def test_TLSState_get_ssl_options():
    import ssl
    output = dict(certfile=cert,
                  keyfile=key,
                  ca_certs=ca_chain,
                  cert_reqs=ssl.CERT_REQUIRED)
    assert_equal(tls_with_file.get_ssl_options(), output)


import tornado.httpserver
import tornado.ioloop
import tornado.web
import threading
import urllib3
import time
import ssl

s_cert = utils.search_path(path.join(conf_dir, "Supervisor-SSB.crt"))
s_key = utils.search_path(path.join(conf_dir, "Supervisor-SSB-plaintext.key"))
s_ca_chain = utils.search_path(path.join(conf_dir, "root-ca.crt"))
url = urllib3.util.url.parse_url(
    "https://127.0.0.1:8888")

s_identity = "org.mplane.SSB.Supervisors.Supervisor-1"


class getToken(tornado.web.RequestHandler):
    def get(self):
        self.write("It works!")

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


def startTornado():
    http_server.listen(8888)
    tornado.ioloop.IOLoop.instance().start()


def stopTornado():
    tornado.ioloop.IOLoop.instance().stop()


threading.Thread(target=startTornado).start()


def test_extract_peer_identity():
    assert_equal(tls_with_file.extract_peer_identity(url), s_identity)


def test_extract_peer_identity_no_tls():
    assert_equal(tls_with_file_no_tls.extract_peer_identity(url), tls.DUMMY_DN)


def test_extract_peer_identity_invalid():
    try:
        tls_with_file.extract_peer_identity('break me!')
    except ValueError as e:
        assert_true(isinstance(e, ValueError))
        stopTornado()
        print("\nWaiting for Tornado to stop...")
        time.sleep(0.5)
