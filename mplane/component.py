#
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
##
# mPlane Protocol Reference Implementation
# Authorization context for mPlane components
#
# (c) 2015 mPlane Consortium (http://www.ict-mplane.eu)
#     Author: Stefano Pentassuglia <stefano.pentassuglia@ssbprogetti.it>
#             Brian Trammell <brian@trammell.ch>
#
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

import mplane.utils
import mplane.model
import importlib
import configparser

class Component(object):
    
    def __init__(self, config_file):
        mplane.model.initialize_registry()
        self.config = config_file
    
    def services(self):
        # Read the configuration file
        config = configparser.ConfigParser()
        config.optionxform = str
        config.read(mplane.utils.search_path(self.config))
        services = []
        for section in config.sections():
            if section.startswith("module_"):
                module = importlib.import_module(config[section]["module"])
                kwargs = {}
                for arg in config[section]:
                    if not arg.startswith("module"):
                        kwargs[arg] = config[section][arg]
                for service in module.services(**kwargs):
                    services.append(service)
        return services

if __name__ == "__main__":
    
    # ONLY FOR TEST PURPOSES
    comp = Component("./conf/component.conf")
    print(comp.services())