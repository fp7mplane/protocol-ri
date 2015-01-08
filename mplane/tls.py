#
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
##
# mPlane Protocol Reference Implementation
# TLS context for mPlane clients and components
#
# (c) 2014 mPlane Consortium (http://www.ict-mplane.eu)
#     Author: Stefano Pentassuglia <stefano.pentassuglia@ssbprogetti.it>
#             Brian Trammell <brian@trammell.ch>
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


# ## Common TLS Configuration

# Clients and components should be able to load a configuration file 
# (`tls.conf`) which refers to CA, private key, and certificate files, 
# for setting up a TLS context. This TLS context should be common to 
# all other code (`mplane/tls.py`). When the TLS configuration file 
# is not present, `https://` URLs will not be supported; when present, 
# the use of TLS will be selected based on the URL used.

# - SSB will pull this out of existing utils.py and stepenta/RI code.

import urllib3
import configparser

def search_path(path):
    #path normalization as in utils goes here...
    pass

def extract_local_identity(cert_file):
    """
    Extract an identity from the designated name in an X.509 certificate 
    file with an ASCII preamble (as used in mPlane)
    """
    dn = ""
    with open(cert_file) as f:
        for line in f.readlines():
            line = line.rstrip().replace(" ", "")
            if line.startswith("Subject:"):
                fields = line[len("Subject:"):].split(",")
                for field in fields:
                    if dn == "":
                        dn = dn + field.split('=')[1]
                    else: 
                        dn = dn + "." + field.split('=')[1]
    return dn

def extract_peer_identity(peer_cert):
    """
    Extract an identity from Tornado's 
    RequestHandler.get_ssl_certificate()
    """
    # FIXME take this from sv_handlers.py
    subject = peer_cert.get("subject")
    return None

class TlsState:
    def __init__(self, config_file=None, forged_identity=None):
        if config_file:
            # Read the configuration file
            config = configparser.ConfigParser()
            config.read(config_file)

            # get paths to CA, cert, and key
            self._cafile = search_path(config["TLS"]["ca-chain"])
            self._certfile = search_path(config["TLS"]["cert"])
            self._keyfile = search_path(config["TLS"]["key"])

            # load cert and get DN
            self._identity = extract_local_identity(self._certfile)
        else:
            self._cafile = None
            self._certfile = None
            self._keyfile = None
            self._identity = forged_identity 

    def pool_for(self, url):
        """
        Given a URL (from which a scheme and host can be extracted),
        return a connection pool (potentially with TLS state) 
        which can be used to connect to the URL.
        """

        if url.instanceof(str):
            url = urllib3.util.parse_url(url)
        if url.schema == "http":
            return urllib3.HTTPConnectionPool(url.host, url.port) 
        elif url.schema == "https":
            if self._keyfile:
                return urllib3.HTTPSConnectionPool(url.host, url.port, 
                                                    key_file=self._keyfile, 
                                                    cert_file=self._certfile, 
                                                    ca_certs=self._cafile) 
            else:
                return urllib3.HTTPSConnectionPool(url.host, url.port)
        elif url.schema == "file":
            # FIXME what to do here?
            raise ValueError("Unsupported schema "+url.schema)            
        else:
            raise ValueError("Unsupported schema "+url.schema)

    def forged_identity(self):
        if not self._keyfile:
            return self._identity
        else:
            return None

    def get_ssl_options(self):
        """
        Get an ssl_options dictionary for this TLS context suitable
        for passing to tornado.httpserver.HTTPServer().
        """
        if self._keyfile:
            return dict(certfile=self._certfile,
                         keyfile=self._keyfile,
                        ca_certs=self._cafile, 
                       cert_reqs=ssl.CERT_REQUIRED)
        else:
            return None