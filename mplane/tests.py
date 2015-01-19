from nose.tools import *
from mplane import azn
from mplane import model
from os import path

''' Authorization module tests '''


" set up test fixtures "

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

