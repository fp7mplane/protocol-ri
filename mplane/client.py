#
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
##
# mPlane Protocol Reference Implementation
# Client SDK API implementation
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
import mplane.utils
import sys
import cmd
import traceback
import readline
import html.parser
import urllib3
import os.path
import argparse
import sys

from datetime import datetime, timedelta

CAPABILITY_PATH_ELEM = "capability"


class Client(object):
    """
    Core implementation of an mPlane JSON-over-HTTP(S) client.
    Supports client-initiated workflows. Intended for building 
    client UIs and bots.

    """

    def __init__(self, default_url=None, tls_state=None):
        """
        initialize a client with a given 
        default URL an a given TLS state
        """
        
        self._default_url = default_url
        self._tls_state = tls_state
        self._capabilities = {}
        self._capability_label = {}
        self._receipts = {}
        self._receipt_labels = {}
        self._results = {}
        self._result_labels = {}

    def send_message(self, dst_url=None):
        """
        send a message, store any result in client state
        follows the link in the message, if present; 
        otherwise uses dst_url, otherwise default_url.
        
        """
        pass

    def handle_message(self, msg):
        """
        Handle a message. Used internally to process 
        mPlane messages received from 


    def result_for(self, token_or_label):
        """
        return a result for the token if available;
        attempt to redeem the receipt for the token otherwise.
        """
        pass

    def retrieve_capabilities(self, url):
        """
        connect to the given URL, retrieve and process the capabilities/withdrawals found there
        """

    def forget(self, token_or_label):
        """
        forget all capabilities, receipts and results for the given token or label
        """

    def receipt_tokens(self):
        """
        list all tokens for outstanding receipts
        """

    def receipt_labels(self):
        """
        list all labels for outstanding receipts
        """

    def result_tokens(self):
        """
        list all tokens for stored results
        """

    def result_labels(self):
        """
        list all labels for stored results
        """

    def capability_tokens(self):
        """
        list all tokens for stored capabilities
        """

    def capability_labels(self):
        """
        list all labels for stored capabilities
        """


class ListenerClient(object):
    """
    Core implementation of an mPlane JSON-over-HTTP(S) client.
    Supports component-initiated workflows. Intended for building 
    supervisors.

    """
    pass

class CrawlParser(html.parser.HTMLParser):
    """
    HTML parser class to extract all URLS in a href attributes in
    an HTML page. Used to extract links to Capabilities exposed
    as link collections.

    """
    def __init__(self, **kwargs):
        super(CrawlParser, self).__init__(**kwargs)
        self.urls = []

    def handle_starttag(self, tag, attrs):
        attrs = {k: v for (k,v) in attrs}
        if tag == "a" and "href" in attrs:
            self.urls.append(attrs["href"])

class HttpClient(object):
    """
    Implements an mPlane HTTP client endpoint for client-initiated workflows. 
    This client endpoint can retrieve capabilities from a given URL, then post 
    Specifications to the component and retrieve Results or Receipts; it can
    also present Redeptions to retrieve Results.

    Caches retrieved Capabilities, Receipts, and Results.

    """
    def __init__(self, posturl, capurl=None, tlsconfig=None):
        # store urls
        self._posturl = posturl
        if capurl is not None:
            if capurl[0] != "/": 
                self._capurl = "/" + capurl 
            else: 
                self._capurl = capurl 
        else: 
            self._capurl = "/" + CAPABILITY_PATH_ELEM 
        url = urllib3.util.parse_url(posturl) 

        if tlsconfig: 
            cert = mplane.utils.normalize_path(mplane.utils.read_setting(tlsconfig, "cert"))
            key = mplane.utils.normalize_path(mplane.utils.read_setting(tlsconfig, "key"))
            ca = mplane.utils.normalize_path(mplane.utils.read_setting(tlsconfig, "ca-chain"))
            mplane.utils.check_file(cert)
            mplane.utils.check_file(key)
            mplane.utils.check_file(ca)
            self.pool = urllib3.HTTPSConnectionPool(url.host, url.port, key_file=key, cert_file=cert, ca_certs=ca) 
        else: 
            self.pool = urllib3.HTTPConnectionPool(url.host, url.port) 

        print("new client: "+self._posturl+" "+self._capurl)

        # empty capability and measurement lists
        self._capabilities = []
        self._receipts = []
        self._results = []

        # empty capability label index
        self._caplabels = {}

    def get_mplane_reply(self, url=None, postmsg=None):
        """
        Given a URL, parses the object at the URL as an mPlane 
        message and processes it.

        Given a message to POST, sends the message to the given 
        URL and processes the reply as an mPlane message.

        """
        if postmsg is not None:
            print(postmsg)
            if url is None:
                url = "/"
            res = self.pool.urlopen('POST', url, 
                    body=mplane.model.unparse_json(postmsg).encode("utf-8"), 
                    headers={"content-type": "application/x-mplane+json"})
        else:
            res = self.pool.request('GET', url)
        print("get_mplane_reply "+url+" "+str(res.status)+" Content-Type "+res.getheader("content-type"))
        if res.status == 200 and \
           res.getheader("content-type") == "application/x-mplane+json":
            print("parsing json")
            return mplane.model.parse_json(res.data.decode("utf-8"))
        else:
            print("giving up")
            return None

    def handle_message(self, msg):
        """
        Processes a message. Caches capabilities, receipts, 
        and results, opens Envelopes, and handles Exceptions.

        """
        print("got message:")
        print(mplane.model.unparse_yaml(msg))

        if isinstance(msg, mplane.model.Capability):
            self.add_capability(msg)
        elif isinstance(msg, mplane.model.Receipt):
            self.add_receipt(msg)
        elif isinstance(msg, mplane.model.Result):
            self.add_result(msg)
        elif isinstance(msg, mplane.model.Exception):
            self._handle_exception(msg)
        elif isinstance(msg, mplane.model.Envelope):
            for imsg in msg.messages():
                self.handle_message(imsg)
        else:
            raise ValueError("Internal error: unknown message "+repr(msg))

    def capabilities(self):
        """Iterate over capabilities"""
        yield from self._capabilities

    def capability_at(self, index):
        """Retrieve a capability at a given index"""
        return self._capabilities[index]

    def capability_by_label(self, label):
        """Retrieve a capability with a given label"""
        return self._caplabels[label]

    def add_capability(self, cap):
        """Add a capability to the capability cache"""
        print("adding "+repr(cap))
        self._capabilities.append(cap)
        if cap.get_label():
            self._caplabels[cap.get_label()] = cap

    def clear_capabilities(self):
        """Clear the capability cache"""
        self._capabilities.clear()
        self._caplabels.clear()

    def retrieve_capabilities(self, listurl=None):
        """
        Given a URL, retrieves an object, parses it as an HTML page, 
        extracts links to capabilities, and retrieves and processes them
        into the capability cache.

        """
        if listurl is None:
            listurl = self._capurl
            self.clear_capabilities()

        print("getting capabilities from "+self._capurl)
        res = self.pool.request('GET', self._capurl)
        if res.status == 200:
            ctype = res.getheader("content-type")
            if ctype == "application/x-mplane+json":
                # Probably an envelope. Process the message.
                self.handle_message(
                    mplane.model.parse_json(res.data.decode("utf-8")))
            elif ctype == "text/html":
                # Treat as a list of links to capability messages.
                parser = CrawlParser(strict=False)
                parser.feed(res.data.decode("utf-8"))
                parser.close()
                for capurl in parser.urls:
                    self.handle_message(self.get_mplane_reply(url=capurl))
        else:
            print(listurl+": "+str(res.status))
       
    def receipts(self):
        """Iterate over receipts (pending measurements)"""
        yield from self._receipts

    def add_receipt(self, msg):
        """Add a receipt. Check for duplicates."""
        if msg.get_token() not in [receipt.get_token() for receipt in self.receipts()]:
            self._receipts.append(msg)

    def redeem_receipt(self, msg):
        self.handle_message(
            self.get_mplane_reply(
                postmsg=mplane.model.Redemption(receipt=msg)))

    def redeem_receipts(self):
        """
        Send all pending receipts to the Component,
        attempting to retrieve results.

        """
        for receipt in self.receipts():
            self.redeem_receipt(receipt)

    def _delete_receipt_for(self, token):
        self._receipts = list(filter(lambda msg: msg.get_token() != token, self._receipts))

    def results(self):
        """Iterate over receipts (pending measurements)"""
        yield from self._results

    def add_result(self, msg):
        """Add a result. Check for duplicates."""
        if msg.get_token() not in [result.get_token() for result in self.results()]:
            self._results.append(msg)
            self._delete_receipt_for(msg.get_token())

    def measurements(self):
        """Iterate over all measurements (receipts and results)"""
        yield from self._results
        yield from self._receipts

    def measurement_at(index):
        """Retrieve a measurement at a given index"""
        if index >= len(self._results):
            index -= len(self._results)
            return self._receipts[index]
        else:
            return self._results[index]

    def _handle_exception(self, exc):
        print(repr(exc))


 