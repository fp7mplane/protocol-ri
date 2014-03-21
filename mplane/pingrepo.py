
# mPlane Protocol Reference Implementation
# ICMP Ping collector component code
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

"""
Implements a repository for ICMP ping (delay.twoway.icmp), for 
integration into the mPlane reference implementation.

"""

import mplane.model
import mplane.httpsrv
import tornado.web
import sqlite3

def _dt2epoch(dt):
    return (dt - datetime(1970,1,1,0,0)).total_seconds()

def ping4_singleton_collect_capability(resposturl):
    cap = mplane.model.Capability(verb="collect", label="ping-detail-ip4-collect")
    cap.set_link(resposturl)
    cap.add_parameter("source.ip4")
    cap.add_parameter("destination.ip4")
    cap.add_result_column("time")
    cap.add_result_column("delay.twoway.icmp.us")
    return cap    

class IndirectPingPostHandler(tornado.web.RequestHandler):

    def inititalize(self, sl3file):
        self._conn = sqlite3.connect(sl3file)
        self._cap = ping4_singleton_collect_capability(resposturl)

    def post(self):
       # unwrap json message from body
        if (self.request.headers["Content-Type"] == "application/x-mplane+json"):
            msg = mplane.model.parse_json(self.request.body.decode("utf-8"))
        else:
            # FIXME how do we tell tornado we don't want to handle this?
            raise ValueError("I only know how to handle mPlane JSON messages via HTTP POST")

        # We expect an asynchronous Result.
        if not isinstance(msg, mplane.model.Result):
            raise ValueError("Collection via HTTP POST requires Results")

        # And we expect it to have the columns we want
        if msg.schema_hash() != self._cap.schema_hash():
            raise ValueError("Collection via HTTP POST requires ping results")

        # Extract values and insert them into the DB
        c = self._conn.cursor()

        for d in msg.schema_dict_iterator():
            c.execute("INSERT INTO pings (stamp, sip4, dip4, usdelay) VALUES ?,?,?,?",
                (dt2epoch(d["time"]), 
                int(d["source.ip4"], 
                int(d["destination.ip4"]), 
                d["delay.twoway.icmp.us"])))

        c.commit()
        
    
