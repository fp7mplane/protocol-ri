# mPlane Protocol Reference Implementation
# example component code
#
# (c) 2013-2015 mPlane Consortium (http://www.ict-mplane.eu)
#               Author: Brian Trammell
#               (based on an example by Stefano Pentassuglia)
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

import mplane.model
import mplane.scheduler
import mplane.utils

"""
Implements service capabilities and services

"""

def services(param):
    # the parameter is passed to this function by component-py,
    # that reads it from the [module_exampleServiceName] section
    # in the config file
    services = [IntegrationTestService()]
    if param is not None:
        services.append(exampleService(example_capability_with_param(), param))
        services.append(exampleService(example_capability_without_param()))
    else:
        raise ValueError("Missing parameter for capability")
    return services

def integration_test_registry():
    pass

def integration_test_capability():
    return mplane.model.parse_json(
        """
        {
          "capability": "measure",
          "version":    0,
          "registry":   "http://corvid.ch/mplane/integration-test-registry",
          "label":      "test-integration",
          "when":       "now ... future / 1s",
          "parameters": {
                          "test.input" : "*"
                        },
          "results":    ["test.output"]
        }
        """
    )

def example_capability_with_param(param):
    cap = mplane.model.Capability(label="example-capability1", when = "now + inf ... future / 1s")
    cap.add_metadata("System_version", "0.1")
    cap.add_parameter("source.ip4", param)
    cap.add_parameter("destination.ip4")
    cap.add_result_column("time")
    cap.add_result_column("bytes.forward")
    return cap

def example_capability_without_param():
    cap = mplane.model.Capability(label="example-capability2", when = "now + inf ... future")
    cap.add_metadata("System_version", "0.1")
    cap.add_parameter("source.ip4")
    cap.add_parameter("destination.ip4")
    cap.add_result_column("time")
    cap.add_result_column("bytes.forward")
    return cap

class IntegrationTestService(mplane.scheduler.Service):
    """
    This class handles the capabilities exposed by the component:
    executes them, and fills the results

    """

    def __init__(self, cap, fileconf):
        super(exampleService, self).__init__(cap)
        self._fileconf = fileconf

    def run(self, spec, check_interrupt):
        """ Execute this Service """

        # Run measurements here

        res = mplane.model.Result(specification=spec)
        # fill the Result here
        return res
