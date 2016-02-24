#!/usr/bin/env python3
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
##
# mPlane Protocol Reference Implementation
# Simple client command-line interface
#
# (c) 2013-2014 mPlane Consortium (http://www.ict-mplane.eu)
#               Author: Brian Trammell <brian@trammell.ch>
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or (at your
# option) any later version. This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details. You should have received a copy
# of the GNU General Public License along with this program.  If not, see
# <http://www.gnu.org/licenses/>.

import sys
import cmd
import traceback
import json
import urllib3
import argparse
import configparser
from time import sleep

import queue
import re
import tornado.web
from time import sleep
import threading
from threading import Thread
import logging
import collections

import mplane.model
import mplane.tls
import mplane.utils
import mplane.client
import mplane.component
import mplane.ui.svgui_handlers
import mplane.ui.dashgui_handler

DUMMY_DN = "Identity.Unauthenticated.Default"

GUI_PORT = '8899'
GUI_CONFIG = "gui/gui-config.json"
GUI_USERSETTINGSDIR = "conf/gui/usersettings"
GUI_REGISTRY = "www/guiregistry.json"
GUI_LOGIN_PATH = "gui/login"
GUI_DASHBOARD_PATH = "gui/dashboard"
GUI_USERSETTINGS_PATH = "gui/settings"
GUI_STATIC_PATH = "gui/static"

GUI_LISTCAPABILITIES_PATH = "gui/list/capabilities"
GUI_RUNCAPABILITY_PATH = "gui/run/capability"
GUI_LISTPENDINGS_PATH = "gui/list/pendings"
GUI_LISTRESULTS_PATH = "gui/list/results"
GUI_GETRESULT_PATH = "gui/get/result"
GUI_STOPPENDINGS_PATH = "gui/stop/capability"

GUI_PROBES_PATH = "gui/list/probes"
# GUI_CAPLABELS_PATH = "gui/list/caplabels"
# GUI_PARAMS_PATH = "gui/list/params" # will be written into guiregistry.json directly
GUI_PORTLETS_PATH = "gui/portlets"
GUI_PORTLETS_DIR = "www/test/json/nisz-en"

logging.basicConfig(stream=sys.stderr, level=logging.INFO)

# FIXME HACK
# some urllib3 versions let you disable warnings about untrusted CAs,
# which we use a lot in the project demo. Try to disable warnings if we can.
try:
	urllib3.disable_warnings()
except:
	pass



class Gui(mplane.client.BaseClient):
	"""
	Based on: mplane.client.HttpListenerClient.
	Core implementation of an mPlane JSON-over-HTTP(S) client.
	Supports component-initiated workflows. Intended for building
	supervisors.

	"""
	def __init__(self, config, supervisor, tls_state=None, exporter=None, io_loop=None):
		super().__init__(tls_state, supervisor=supervisor,
						exporter=exporter)

		self._supervisor = supervisor
		self._tls_state = tls_state
		
		supconfig = config["supervisor"]
		listen_port = GUI_PORT
		if "gui-port" in supconfig:
			listen_port = int(supconfig["gui-port"])

		gui_cfgfile = GUI_CONFIG
		if "gui-config" in supconfig:
			gui_cfgfile = supconfig["gui-config"]

		self._supervisor._gui_regfile = GUI_REGISTRY
		if "gui-registry" in supconfig:
			self._supervisor._gui_regfile = supconfig["gui-registry"]

		guiusrdir = GUI_USERSETTINGSDIR
		if "gui-usrdir" in supconfig:
			guiusrdir = supconfig["gui-usrdir"]

		# link to which results must be sent
		self._link = config["client"]["listen-spec-link"]
		logging.debug(">>> CGui.__init__: self._link = " + str(self._link))

		# Outgoing messages per component identifier
		self._outgoing = {}

		# specification serial number
		# used to create labels programmatically
		self._ssn = 0

		# Capability
		self._callback_capability = {}
		
		# Create a request handler pointing at this client
		self._tornado_application = tornado.web.Application([
			(r"/" + GUI_LOGIN_PATH, mplane.ui.svgui_handlers.LoginHandler, {'supervisor': self._supervisor, 'guicfgfile': gui_cfgfile }),
			(r"/" + GUI_DASHBOARD_PATH, mplane.ui.dashgui_handler.DashboardHandler, {'supervisor': self._supervisor, 'guicfgfile': gui_cfgfile }),
			(r"/" + GUI_USERSETTINGS_PATH, mplane.ui.svgui_handlers.UserSettingsHandler, { 'supervisor': self._supervisor, 'guiusrdir': guiusrdir }),
			(r"/" + GUI_LISTCAPABILITIES_PATH, mplane.ui.svgui_handlers.ListCapabilitiesHandler, { 'supervisor': self._supervisor, 'tlsState': self._tls_state }),
			(r"/" + GUI_LISTPENDINGS_PATH, mplane.ui.svgui_handlers.ListPendingsHandler, { 'supervisor': self._supervisor, 'tlsState': self._tls_state }),
			(r"/" + GUI_LISTRESULTS_PATH, mplane.ui.svgui_handlers.ListResultsHandler, { 'supervisor': self._supervisor, 'tlsState': self._tls_state }),
			(r"/" + GUI_GETRESULT_PATH, mplane.ui.svgui_handlers.GetResultHandler, { 'supervisor': self._supervisor, 'tlsState': self._tls_state }),
			(r"/" + GUI_RUNCAPABILITY_PATH, mplane.ui.svgui_handlers.RunCapabilityHandler, { 'supervisor': self._supervisor, 'tlsState': self._tls_state }),
			(r"/" + GUI_PROBES_PATH, mplane.ui.svgui_handlers.ListProbesHandler, { 'supervisor': self._supervisor, 'tlsState': self._tls_state }),
			(r"/" + GUI_STOPPENDINGS_PATH, mplane.ui.svgui_handlers.StopPendingHandler, { 'supervisor': self._supervisor, 'tlsState': self._tls_state }),
			(r"/" + GUI_PORTLETS_PATH, mplane.ui.svgui_handlers.PortletsHandler, { 'supervisor': self._supervisor, 'tlsState': self._tls_state }),
			(r"/", mplane.ui.svgui_handlers.ForwardHandler, { 'forwardUrl': '/gui/static/login.html' }),
			(r"/gui", mplane.ui.svgui_handlers.ForwardHandler, { 'forwardUrl': '/gui/static/login.html' })
		], cookie_secret="123456789-TODO-REPLACE", static_path=r"www/", static_url_prefix=r"/" + GUI_STATIC_PATH + "/")
		# ssl_options=tls_state.get_ssl_options() removed for GUI access
		http_server = tornado.httpserver.HTTPServer(self._tornado_application)

		# run the server
		logging.debug(">>> Gui running on port " + str(listen_port))
		http_server.listen(listen_port)
		if io_loop is None:
			cli_t = Thread(target=self.listen_in_background)
			cli_t.daemon = True
			cli_t.start()

	def listen_in_background(self, io_loop):
		"""
		The server listens for requests in background, while
		the supervisor console remains accessible
		"""
		tornado.ioloop.IOLoop.instance().start()

	
GUI_HISTSIZE = 15
GUI_HISTFILE = "www/history.json"

class History():
	"""
	Maintains a list of entry field values parameter[value] pairs when used in filling input fields
	{'when':['now + 30s / 5s', 'now + 1d / 10s'],
	'content.url':['http://skylivehss.cdnlabs.fastweb.it/227324/tg24.isml/Manifest',
	 'http://skylivehls.cdnlabs.fastweb.it/217851/tg24/index.m3u8', 'http://devimages.apple.com/iphone/samples/bipbop/bipbopall.m3u8'],
	'destination.ip4':['193.6.200.94', '79.120.193.114', '188.36.160.134', '8.8.8.8'],
	'source.ip4':['91.227.139.40']}

	"""
	def __init__(self):
		self._h = {}
		self._max_size = GUI_HISTSIZE
		self._histfile = GUI_HISTFILE
		try:
			with open(self._histfile) as data_file:    
				self._h = json.load(data_file)
				print("after load" ,self._h)
		except:
			print("Could not load history") 

	def add(self, key, val, save=True):
		if key not in self._h:
			self._h[key] = []
		l=self._h[key]
		print("L1:",self._h)
		if val in l:
			del l[l.index(val)]
		else:
			del l[self._max_size:]
		print("L2:",self._h)
		l.insert(0,val)
		print("L3:",self._h)
		if save:
			with open( self._histfile, 'w' ) as f:
				json.dump(self._h, f)
		return self._h
		

    
