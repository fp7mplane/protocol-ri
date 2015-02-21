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
from mplane import model
from mplane import utils
import configparser
from os import path
import sys

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


def setup():
    print("Starting tests...")


''' Set up test fixtures '''

conf_dir = path.dirname(__file__)


''' Utils Module Tests '''

utils_test_file = 'utils-test.conf'
utils_test_path = path.join(conf_dir, utils_test_file)


def test_read_setting():
    res = utils.read_setting(utils_test_path, 'true_param')
    assert_true(res)
    res = utils.read_setting(utils_test_path, 'false_param')
    assert_false(res)
    res = utils.read_setting(utils_test_path, 'other_param')
    assert_equal(res, 'other')
    res = utils.read_setting(utils_test_path, 'missing_param')
    assert_equal(res, None)


@raises(ValueError)
def test_search_path():
    root_path = '/var'
    assert_equal(utils.search_path(root_path), root_path)
    existing_input_path = 'mplane'
    output_path = path.abspath('mplane')
    assert_equal(utils.search_path(existing_input_path), output_path)
    unexisting_input_path = 'missing'
    assert_equal(utils.search_path(unexisting_input_path), '')


@raises(ValueError)
def test_check_file():
    utils.check_file('missing')


def test_normalize_path():
    another_root_path = '/conf'
    assert_equal(utils.normalize_path(another_root_path), another_root_path)
    another_existing_input_path = 'conf'
    another_output_path = path.abspath('conf')
    assert_equal(utils.normalize_path(another_existing_input_path),
                 another_output_path)


def test_print_then_prompt():
    expected = "a row\n|mplane|"
    utils.print_then_prompt("a row")
    try:
        output = sys.stdout.getvalue().strip()
        assert_equal(output, expected)
    except:
        print("\nThis test need to run in buffered mode!\n")
        assert False


def test_add_value_to():
    d = {1: ['one']}
    utils.add_value_to(d, 1, 'One')
    assert_equal(d, {1: ['one', 'One']})
    utils.add_value_to(d, 2, 'two')
    assert_equal(d, {1: ['one', 'One'], 2: ['two']})


def test_split_stmt_list():
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
    capjson = model.unparse_json(cap)
    res = utils.split_stmt_list('['+capjson+']')
    caps = []
    caps.append(cap)
    # using repr as no __eq__ methos is implemented fot capability objects
    assert_equal(repr(res[0]), repr(caps[0]))
