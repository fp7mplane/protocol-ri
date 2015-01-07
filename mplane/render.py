#
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
##
# mPlane Protocol Reference Implementation
# mPlane message renderers (to text and html)
#
# This file is incomplete.
#
# (c) 2013-2014 mPlane Consortium (http://www.ict-mplane.eu)
#               Author: Brian Trammell <brian@trammell.ch>
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

def render_text(msg):    
    d = msg.to_dict()
    out = "%s: %s\n" % (msg.kind_str(), msg.verb())

    for section in (KEY_LABEL, KEY_LINK, KEY_EXPORT, KEY_TOKEN, KEY_WHEN):
        if section in d:
            out += "    %-12s: %s\n" % (section, d[section])

    for section in (KEY_PARAMETERS, KEY_METADATA):
        if section in d:
            out += "    %-12s(%2u): \n" % (section, len(d[section]))
            for element in d[section]:
                out += "        %32s: %s\n" % (element, d[section][element])

    if KEY_RESULTVALUES in d:
        out += "    %-12s(%2u):\n" % (KEY_RESULTVALUES, len(d[KEY_RESULTVALUES]))
        for i, row in enumerate(d[KEY_RESULTVALUES]):
            out += "          result %u:\n" % (i)
            for j, val in enumerate(row):
                out += "            %32s: %s\n" % (d[KEY_RESULTS][j], val)
    elif KEY_RESULTS in d:
        out += "    %-12s(%2u):\n" % (KEY_RESULTS, len(d[KEY_RESULTS]))
        for element in d[KEY_RESULTS]:
            out += "        %s\n" % (element)

    return out

