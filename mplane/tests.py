from nose.tools import *
from mplane import azn
from mplane import tls
from mplane import model
from os import path

''' Authorization module tests '''


" set up test fixtures "
# FIXME maybe is better to write a test config file.
conf_path = path.abspath('conf')
conf_file = 'component.conf'
config_file = path.join(conf_path, conf_file)

" build up the capabilities' label"

model.initialize_registry()
cap = model.Capability(label="tstat-log_tcp_complete-core")

" set the identity "

id_true_role = "org.mplane.SSB.Clients.Client-1"
id_false_role = "dummy"


def test_Authorization():
    res_none = azn.Authorization(None)
    assert_true(isinstance(res_none, azn.AuthorizationOff))
    res_auth = azn.Authorization(config_file)
    assert_true(isinstance(res_auth, azn.AuthorizationOn))


def test_AuthorizationOn():
    res = azn.AuthorizationOn(config_file)
    assert_true(isinstance(res, azn.AuthorizationOn))
    assert_true(res.check(cap, id_true_role))
    assert_false(res.check(cap, id_false_role))


def test_AuthorizationOff():
    res = azn.AuthorizationOff()
    assert_true(isinstance(res, azn.AuthorizationOff))
    assert_true(res.check(cap, id_true_role))


''' TLS module tests '''

# FIXME maybe is better to write a test config file.
cert = "PKI/ca/certs/SI/Component-SSB.crt"
key = "PKI/ca/certs/SI/Component-SSB-plaintext.key"
ca_chain = "PKI/ca/root-ca/root-ca.crt"
identity = "org.mplane.SSB.Components.Component-2"
forged_identity = "org.example.test"

# with config file and without forged_identity
tls_with_file = tls.TlsState(config_file=config_file)
# without config file and with forged_identity
tls_without_file = tls.TlsState(forged_identity=forged_identity)


@raises(ValueError)
def test_search_path():
    root_path = '/conf'
    assert_equal(tls.search_path(root_path), root_path)
    existing_input_path = 'conf'
    output_path = path.abspath('conf')
    assert_equal(tls.search_path(existing_input_path, output_path))
    unexisting_input_path = 'conf'
    assert_equal(tls.search_path(unexisting_input_path), '')


def test_TLSState_init():
    assert_equal(tls_with_file._cafile, tls.search_path(ca_chain))
    assert_equal(tls_with_file._certfile, tls.search_path(cert))
    assert_equal(tls_with_file._keyfile, tls.search_path(key))
    assert_equal(tls_with_file._identity, identity)

    assert_equal(tls_without_file._cafile, None)
    assert_equal(tls_without_file._certfile, None)
    assert_equal(tls_without_file._keyfile, None)
    assert_equal(tls_without_file._identity, forged_identity)


def test_TLSState_forged_identity():
    assert_equal(tls_with_file.forged_identity(), None)
    assert_equal(tls_without_file.forged_identity(), forged_identity)


def test_TLSState_get_ssl_options():
    import ssl
    output = dict(certfile=tls.search_path(cert),
                  keyfile=tls.search_path(key),
                  ca_certs=tls.search_path(ca_chain),
                  cert_reqs=ssl.CERT_REQUIRED)
    assert_equal(tls_with_file.get_ssl_options(), output)
    assert_equal(tls_without_file.get_ssl_options(), None)
