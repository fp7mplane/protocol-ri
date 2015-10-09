#
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
##
# mPlane Protocol Reference Implementation
# Simple mPlane Supervisor (JSON over HTTP)
#
# (c) 2013-2015 mPlane Consortium (http://www.ict-mplane.eu)
#               Author: Stefano Pentassuglia <stefano.pentassuglia@ssbprogetti.it>
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
import mplane.client
import mplane.component
import mplane.utils
import mplane.tls

import queue
import re
import tornado.web
from time import sleep
import threading
from threading import Thread

class RelayService(mplane.scheduler.Service):
    """
    This class is used by the supervisor as a wrapper for capabilities received by the components.

    When a capability is received by a component, a new RelayService is created and stored by the Supervisor
    When a client asks for capabilities, the supervisor exposes its RelayServices
    When a specification is received by a client, the run() method is called:
        - it creates a new specification requesting the corresponding capability on the component
        - waits for results from the component, and when receives them basically forwards them to the client

    """

    def __init__(self, cap, identity, client, lock, messages):
        self.relay = True
        self._identity = identity
        self._client = client
        self._lock = lock
        self._messages = messages
        super(RelayService, self).__init__(cap)

    def run(self, spec, check_interrupt):
        """
        Forward the specification to the corresponding component, and wait for results

        """

        # forge the specification and send it to the component
        pattern = re.compile("-\d+$")
        trunc_pos = pattern.search(spec.get_label())
        trunc_label = spec.get_label()[:trunc_pos.start()]
        fwd_spec = self._client.invoke_capability(trunc_label, spec.when(), spec.parameter_values())

        # wait for results from the component
        result = None
        pending = False
        while result is None:

            # periodically check for interrupts from the client
            if check_interrupt() and not pending:
                self._client.interrupt_capability(fwd_spec.get_token())
                pending = True
            sleep(1)

            # check if the expected result is among the messages coming from the component
            with self._lock:
                if self._identity in self._messages:
                    for msg in self._messages[self._identity]:
                        if msg.get_token() == fwd_spec.get_token():
                            if (isinstance(msg, mplane.model.Result) or
                                isinstance(msg, mplane.model.Envelope)):
                                print("Received result for " + trunc_label + " from " + self._identity)
                            elif isinstance(msg, mplane.model.Exception):
                                print("Received exception for " + trunc_label + " from " + self._identity)
                            result = msg
                            self._messages[self._identity].remove(msg)
                            break

        # return result
        if (not isinstance(result, mplane.model.Exception)
           and not isinstance(result, mplane.model.Envelope)):
            result.set_label(spec.get_label())  # Envelopes and Exceptions don't have labels
        result.set_token(spec.get_token())
        return result

class BaseSupervisor(object):
    
    def __init__(self, config):
        self._caps = []
        self.config = config

        # registry initialization phase (preload + fetch from URI)
        if config is not None:
            if "Registries" in config:
                if "preload" in config["Registries"]:
                    for reg in config["Registries"]["preload"]:
                        mplane.model.preload_registry(reg)
                if "default" in config["Registries"]:
                    registry_uri = config["Registries"]["default"]
                else:
                    registry_uri = None
            else:
                registry_uri = None
        else:
            registry_uri = None
        mplane.model.initialize_registry(registry_uri)

        tls_state = mplane.tls.TlsState(config)

        # initialize thread-safe structures for message exchange with client thread
        self.from_cli = queue.Queue()
        self._lock = threading.RLock()
        self._spec_messages = dict()
        self._io_loop = tornado.ioloop.IOLoop.instance()

        # generate the Client and the Component instances
        if config is None:
            # if no config file is provided, use default settings: ListenerClient and ListenerComponent
            self._client = mplane.client.HttpListenerClient(config=config,
                                                            tls_state=tls_state, supervisor=True,
                                                            exporter=self.from_cli,
                                                            io_loop=self._io_loop)

            self._component = mplane.component.ListenerHttpComponent(config,
                                                                     io_loop=self._io_loop)
        else:
            if ("Initiator" in self.config["Client"]
                    and "Listener" in self.config["Client"]):
                raise ValueError("The supervisor client-side cannot be 'Initiator' and 'Listener' simultaneously. "
                                 "Remove one of them from " + self.config + "[\"Client\"]")

            # ListenerClient
            elif "Listener" in self.config["Client"]:
                self._client = mplane.client.HttpListenerClient(config=self.config,
                                                                tls_state=tls_state, supervisor=True,
                                                                exporter=self.from_cli,
                                                                io_loop=self._io_loop)

            # InitiatorClient
            elif "Initiator" in self.config["Client"]:
                self._client = mplane.client.HttpInitiatorClient(tls_state=tls_state, supervisor=True,
                                                                 exporter=self.from_cli)
                self._urls = self.config["Client"]["capability-url"]
            else:
                raise ValueError("Need either a 'Initiator' or 'Listener' object under 'Client' in config file")

            if ("Initiator" in self.config["Component"]
                and "Listener" in self.config["Component"]):
                raise ValueError("The supervisor component-side cannot be 'Initiator' and 'Listener' simultaneously. "
                                 "Remove one of them from " + args.config + "[\"Component\"]")

            # InitiatorComponent
            elif "Initiator" in self.config["Component"]:
                self._component = mplane.component.InitiatorHttpComponent(self.config,
                                                                          supervisor=True)

            # ListenerComponent
            elif "Listener" in self.config["Component"]:
                self._component = mplane.component.ListenerHttpComponent(self.config,
                                                                         io_loop=self._io_loop)
            else:
                raise ValueError("Need either a 'Initiator' or 'Listener' object under 'Component' in config file")

        self.run()

    def run(self):
        """
        Run the Component and Client threads, start listening or polling (depending on the configuration),
        and periodically check for received messages

        """
        if self.config is not None:

            # start listening if Client or Component are Listeners
            if (("Client" in self.config and "Listener" in self.config["Client"]) or
                ("Component" in self.config and "Listener" in self.config["Component"])):
                t_listen = Thread(target=self.listen_in_background)
                t_listen.daemon = True
                t_listen.start()

            # start polling if Client is Initiator (InitiatorComponent is handled in handle_message())
            if "Initiator" in self.config["Client"]:
                t_poll = Thread(target=self.poll_in_background)
                t_poll.daemon = True
                t_poll.start()
        else:

            # default: both Client and Component are listeners
            t_listen = Thread(target=self.listen_in_background)
            t_listen.daemon = True
            t_listen.start()

        # check for messages received from Client thread
        while True:
            if not self.from_cli.empty():
                [msg, identity] = self.from_cli.get()
                self.handle_message(msg, identity)
            sleep(0.1)

    def handle_message(self, msg, identity):
        """
        Handle messages received from the Client thread

        """
        if isinstance(msg, mplane.model.Capability):
            if [msg.get_label(), identity] not in self._caps:
                self._caps.append([msg.get_label(), identity])

                # create a new RelayService and store it
                serv = RelayService(msg, identity, self._client,
                                    self._lock, self._spec_messages)
                self._component.scheduler.add_service(serv)

                if self.config is not None:
                    if "Listener" in self.config["Component"]:
                        if "interfaces" in self.config["Component"]["Listener"] and \
                                self.config["Component"]["Listener"]["interfaces"]:

                            # 'link' construction: if there are multiple IPs to listen on,
                            # we have no way to determine which will be the correct URI for a client.
                            # In this case, let's delegate the construction to the request handlers
                            # (see DiscoveryHandler._respond_capability() in component.py)
                            if len(self.config["Component"]["Listener"]["interfaces"]) != 1:
                                serv.set_capability_link("")
                            else:
                                if "TLS" in self.config:
                                    link = "https://"
                                else:
                                    link = "http://"
                                link = link + self.config["Component"]["Listener"]["interfaces"][0] + ":"
                                link = link + self.config["Component"]["Listener"]["port"] + "/"
                                serv.set_capability_link(link)
                        else:
                            serv.set_capability_link("")
                else:
                    serv.set_capability_link("")

                # if the Component part is Initiator, register the new capability to the client
                if self.config is not None and "Initiator" in self.config["Component"] and \
                        not msg.get_label() == "callback":
                    self._component.register_to_client([serv.capability()])

        elif isinstance(msg, mplane.model.Receipt):
            # receipts are handled by the RelayService, nothing to do here
            pass
            
        elif isinstance(msg, mplane.model.Result) \
                or isinstance(msg, mplane.model.Exception):

            # hand result (or exception) to the RelayService
            with self._lock:
                mplane.utils.add_value_to(self._spec_messages, identity, msg)
            
        elif isinstance(msg, mplane.model.Withdrawal):
            # remove capability from internal state
            if not msg.get_label() == "callback":
                self._component.remove_capability(self._component.scheduler.capability_for_key(msg.get_token()))
                self._caps.remove([msg.get_label(), identity])

        elif isinstance(msg, mplane.model.Envelope):
            # if the envelope contains results, hand it to the RelayService, otherwise handle each message separately
            for imsg in msg.messages():
                if isinstance(imsg, mplane.model.Result):
                    mplane.utils.add_value_to(self._spec_messages, identity, msg)
                    break
                else:
                    self.handle_message(imsg, identity)
        else:
            raise ValueError("Internal error: unknown message "+repr(msg))

    def listen_in_background(self):
        """ Start the listening server """
        self._io_loop.start()

    def poll_in_background(self):
        """ Periodically poll components """
        while True:
            for url in self._urls:
                try:
                    self._client.retrieve_capabilities(url)
                except:
                    print(str(url) + " unreachable. Retrying in 5 seconds")

            # poll for results
            for label in self._client.receipt_labels():
                self._client.result_for(label)

            for token in self._client.receipt_tokens():
                self._client.result_for(token)

            for label in self._client.result_labels():
                self._client.result_for(label)

            for token in self._client.result_tokens():
                self._client.result_for(token)

            sleep(5)
