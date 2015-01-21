#
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
##
# mPlane Protocol Reference Implementation
# mPlane message renderers (to text and html)
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
import tornado.template

def render_text(msg):
    if msg.isinstance(mplane.model.Capability):
        return render_text_cap(msg.to_dict())
    elif msg.isinstance(mplane.model.Specification):
        return render_text_spec(msg.to_dict())
    elif msg.isinstance(mplane.model.Receipt):
        return render_text_rec(msg.to_dict())
    elif msg.isinstance(mplane.model.Result):
        return render_text_res(msg.to_dict())
    else:
        raise ValueError("Unrenderable message type")

# Capability "label" (token)
#   N parameters:
#     key: constraint
#   N metadata
#     key: constraint
#   N results:
#     key
#   export: url

def render_html(msg, cssid):
    if msg.isinstance(mplane.model.Capability):
        return render_html_cap(msg.to_dict(), cssid)
    elif msg.isinstance(mplane.model.Specification):
        return render_html_spec(msg.to_dict(), cssid)
    elif msg.isinstance(mplane.model.Receipt):
        return render_html_rec(msg.to_dict(), cssid)
    elif msg.isinstance(mplane.model.Result):
        return render_html_res(msg.to_dict(), cssid)
    elif msg.isinstance(mplane.model.Exception):
        return render_html_exc(msg.to_dict(), cssid)
    else:
        raise ValueError("Unrenderable message type")

