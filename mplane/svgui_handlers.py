#
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
##
# mplane supervisor GUI
# (c) 2014-2015 mPlane Consortium (http://www.ict-mplane.eu)
#               Author: Janos Bartok-Nagy <jnos.bartok-nagy@netvisor.hu>,
#                       Attila Bokor ;attila.bokor@netvisor.hu>
#
# based on mPlane Protocol Reference Implementation:
#
# (c) 2013-2015 mPlane Consortium (http://www.ict-mplane.eu)
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
import mplane.client
import mplane.svgui

from datetime import datetime
import html.parser
import urllib3
import json
import collections
import sys
import os

from threading import Thread
import queue

import tornado.web
import tornado.httpserver
import tornado.ioloop
import logging

GUI_HISTSIZE = 15
GUI_HISTFILE = "www/history.json"
GUI_PORTLETS_DIR = "www/test/json/nisz-en/"	# TODO: fix for a normal dir
GUI_PORTLETS_PATH = "gui/portlets"

logging.basicConfig(stream=sys.stderr, level=logging.debug)

# FIXME HACK
# some urllib3 versions let you disable warnings about untrusted CAs,
# which we use a lot in the project demo. Try to disable warnings if we can.
try:
	urllib3.disable_warnings()
except:
	pass

	
def get_dn(supervisor, request):
	"""
	Extracts the DN from the request object. 
	If SSL is disabled, returns a dummy DN
	
	"""
	# if supervisor._sec == True:
	if supervisor._tls_state._keyfile:
		dn = supervisor._tls_state._identity
		# dn = ""
		# for elem in request.get_ssl_certificate().get('subject'):
			# if dn == "":
				# dn = dn + str(elem[0][1])
			# else: 
				# dn = dn + "." + str(elem[0][1])
	else:
		if "Forged-Mplane-Identity" in request.headers.keys():
			dn = request.headers["Forged-Mplane-Identity"]
		else:
			dn = DUMMY_DN
	# self._tls_state = mplane.tls.TlsState(supervisor.config)
	# dn = self._tls.extract_peer_identity(supervisor, request)
	# logging.debug(">>> sv_handlers.py:get_dn(): dn = " + dn)
	return dn
			   
			   
def guiregistry(supervisor):
# def guiregistry(supervisor, reguri=None, outfile=None):
	"""
	Dynamically creates a json file for GUI. 
	Probes: dynamic list of registered probes ( gui/list/probes.json )
	Labels: dynamic list of registered capabilities' labels ( gui/i/labels )
	Parameters: dynamic list of parameters of the registered capabilities ( gui/i/params )

	"""
	
	# read registry.json
	_supervisor = supervisor
	_uri = _supervisor._reguri
	_outfile = _supervisor._guiregfile
	_r = mplane.model.Registry(_uri)
	
	_new = collections.OrderedDict()
	#_new["registry-format"] = "mplane-0"
	#_new["registry-revision"] = int(_r._revision)
	#_new["registry-uri"] = _r._uri
	_new["elements"] = []
	_new["elements"].append( collections.OrderedDict([ ("name","filter.probe"), ("label","Component DN"), ("prim","list"), ("url","/gui/list/probes"), ("desc","List of registered probes") ] ) )
	_new["elements"].append( collections.OrderedDict( [ ("name","filter.label"), ("label","Label"), ("prim","string"), ("desc","List of registered capabilities") ] ) )
	_parlist = paramlist(_supervisor)
	for elem in _r._elements.values():
		if elem._name in _parlist:
			copy_regelem(elem, _new["elements"] )
	# print(">>> guiregistry: new JSON: \n" + mplane.model.json.dumps(_new) )
	f = open( _outfile, 'w' )
	f.write( mplane.model.json.dumps(_new) )
	f.close
	return _new

	
def paramlist(supervisor):
	_supervisor = supervisor
	parlist = []

	for token in _supervisor._capabilities:
		cap = _supervisor._capabilities[token]
		d = cap.to_dict()
		for section in ("parameters", "results"):
			if section in d:
				for element in d[section]:
					if element not in parlist:
						parlist.append(element) 
	# print("total parlist: " + str(parlist))
	return parlist


def copy_regelem(self, dst):
	"""
	copies elements from _src element to _dst element
	"""
	# _src = src
	_dst = dst
	ed = collections.OrderedDict()
	name = self.name()
	ed["name"] = "filter." + self.name()
	ed["label"] = name
	ed["prim"] = self.primitive_name()
	desc = self.desc()
	if desc is not None:
		ed["desc"] = desc
	_dst.append( ed )               


def filterlist(self, guiregistry=None):
	"""
	Returns dict of {filtername, filtervalue}.
	Gui returns filtereble 'param' as 'filter.param', we cut off the prefix later.
	
	"""

	_filterlist = {}
	_guiregistry = guiregistry
	_qlist = self.request.arguments
	
	for _qname in self.request.arguments:
		# print( ">>> " + _qname + ": " + self.get_query_argument( _qname, None, True ) )
		found = False
		for _key in _guiregistry["elements"]:
			_name = _key['name']
			# print( "    compare " + _qname + " against " + _name )
			if found == False:
				if ( _name == _qname ):
					# should move to msg decoding section(s)
					# _qn = _qname[ len('filter.') : ]
					# print("        found, strip " + _qname + " to " + _qn )
					_filterlist.update( { _qname: self.get_argument( _qname, default=None ) } )
					found = True
		# TERRIBLE_HACK: since GUI returns 'DN' instead 'filter.probe' and it is not worth to change it
		if ( _qname == "DN" ):
			_filterlist.update( { 'filter.probe': self.get_argument( _qname, default=None ) } )
			found = True
		
	print(">>> final filterlist: " + str( _filterlist) )
	return _filterlist


def match_filters(self, msg, filterlist):
	"""
	check msg against label and parameters
	if checking against not applicable filters, always return false (eg filtering for IP address with ott-download)
	
	"""
	# TODO: kell a self ide? nem használom sehol...
	
	_matched = True
	_msg = msg
	_filtlist = filterlist
	_filtname = ""
	_filtvalue = ""
	_value = ""
	print(">>> msg = " + mplane.model.unparse_json(_msg))
	
	# print(">>> initial _filtlist: " + str( _filtlist ))

	# Envelope - should be handled before, only singletons allowed
	# if isinstance(_msg,mplane.model.Envelope):
		# raise ValueError("Only Capability, Receipt and Result can be filtered.")
		
	if isinstance(_msg,mplane.model.Exception):
		# print(">>> SKIPPED because of Exception")
		# changed to True - it is not to be filtered, at least not here
		return True

	# print(">>> new _filtlist: " + str( _filtlist ))
	for _filtname in _filtlist:
		_filtvalue = _filtlist[ _filtname ]
		# print(">>> filter: " + _filtname + " = " + str( _filtvalue ))
		
		if ( _filtname == "filter.label" ):
			_label = _msg.get_label()
			if ( _label.find(_filtvalue) <0 ):
				# print(">>> SKIPPED because of label mismatch: label " + _label + " does not contains filter " + _filtvalue)
				return False
		
		elif ( _filtname == "filter.probe" ):
			# Just for testing here
			if ( isinstance( _msg, mplane.model.Capability ) or isinstance( _msg, mplane.model.Receipt )):
				_dn = mplane.client.BaseClient.identity_for(self._supervisor, token_or_label=_msg.get_token(), receipt=isinstance( _msg, mplane.model.Receipt ))
			# elif isinstance( _msg, mplane.model.Result ):
			elif isinstance( _msg, mplane.model.Result ) or isinstance (_msg, mplane.model.Envelope):
				_dn = get_dn(self._supervisor, self.request)
			else:
				raise ValueError("Only Capability, Receipt and Result can be filtered.")
			_probe = _dn + "," + _msg.get_token()
			# print(">>> component DN = " + _dn + "  , probe ID = " + _probe )
			if ( _probe.find(_filtvalue) <0 ):
				# print(">>> SKIPPED because of mismatch: _probe " + _probe + " does not contains filter " + _filtvalue)
				return False
		
		elif isinstance( _msg, mplane.model.Capability ):
			_fn = _filtname[ len('filter.') : ]
			if ( _fn not in _msg.parameter_names() ):
				# print(">>> SKIPPED because of msg has no filtered attribute " + _fn )
				return False
			else:
				_value = _msg._params[_fn]._constraint
				if ( (isinstance( _value, mplane.model._SetConstraint ) and str( _value ).find( _filtvalue ) < 0)
						or (not isinstance( _value, mplane.model._SetConstraint ) and not _value.met_by( _filtvalue )) ):
					# print(">>> SKIPPED because of constraint " + str( _value ) + "is not equal to filter " + _filtvalue )
					return False
		
		elif ( isinstance( _msg, mplane.model.Result ) or isinstance( _msg, mplane.model.Receipt ) ):
			_fn = _filtname[ len('filter.') : ]
			if ( _fn not in _msg.parameter_names() ):
				# print(">>> SKIPPED because of msg has no filtered attribute " + _fn )
				return False
			else:
				_value = _msg.get_parameter_value( _fn )
				# print(">>> _value = " + str(_value) + ", _filtvalue = " + _filtvalue)
				# TODO: context sensitive checking would be better
				if ( str( _value ).find( _filtvalue ) <0 ) :
					# print(">>> SKIPPED because of msg value " + str(_value) + " does not contains filter value " + _filtvalue )
					return False

		elif ( isinstance( _msg, mplane.model.Envelope )):
			# at this point returns true since cannot be filtered against params
			return True
			
		else:
			raise ValueError("Only Capability, Receipt and Result can be filtered.")
		
		# print(">>> removing _filtlist[" + _filtlist[ _filtname ] + "]")
		# _filtlist.remove( _filtname )
		# print(">>> new _filtlist: " + str( _filtlist ))

	if _matched == False :
		raise NotImplementedError("should not be there - unhandled branch.")
	# print(">>> MATCHED")
	# print(">>> MATCHED " + _filtname + " paramvalue = " + str( _value ) + ", filtervalue = " + _filtvalue )
	return _matched


def addtohistory(hist, when, params):
	"""
		
	TODO: filter to add only input params
	"""
	for paramname in params:
		hist.add( paramname, str( params.get(paramname) ))
	val = str( when )
	hist.add( 'when', val )

	
class History(list):
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
		self.size = GUI_HISTSIZE
		self._histfile = GUI_HISTFILE
		x = []

	def add(self, key, val ):
		if key not in self._h:
			self._h[key] = collections.deque('', self.size)
		if val not in self._h[key]:
			self._h[key].appendleft(val)
		s = self.list_deque( self._h )
		# print( "history = " + s )
		f = open( self._histfile, 'w' )
		f.write( s )
		f.close
		return self._h
		
	def list_deque(self, h):
		msg = ''
		for key in h:
			msg = msg + "'" + key + "':" + str( list( h[key] )) + ',\n'
		msg = "{" + msg[:-2] + "}"
		return msg


###########################################################
# sv_gui_handlers
###########################################################


class S_CapabilityHandler(mplane.client.MPlaneHandler):
	"""
	Exposes to a client the capabilities registered to this supervisor. 
	
	"""

	def initialize(self, supervisor, tlsState):
		self._supervisor = supervisor
		self._tls = tlsState
		self.dn = get_dn(self._supervisor, self.request)
		# print("\n>>> S_CapabilityHandler(): self = " + str(self) + " self.dn = " + str(self.dn) + " self._supervisor =" + str(self._supervisor))
	
	def get(self):
		"""
		Returns a list of all the available capabilities 
		(filtered according to the privileges of the client)
		in the form of a JSON array of Capabilities
		
		"""
		# # check the class of the certificate (Client, Component, Supervisor).
		# # this function can only be used by clients
		if (self.dn.find("Clients") == -1 and self.dn != DUMMY_DN):
			self._respond_plain_text(401, "Not Authorized. Only Clients can use this function")
			return
		
		try:
			msg = ""
		
			# list capabilities
			# print("\n>>> S_CapabilityHandler: _supervisor._capabilities = \n" + str(self._supervisor._capabilities))
			for key in self._supervisor._capabilities:
				found = False
				# print(">>> key= " + key)
				cap = self._supervisor._capabilities[key]
				# print("      cap = " + str(cap))
				cap_id = cap.get_label() + ", " + key
				# 2FIX: would be better to do without raise error so that continue even in case of problems
				if self._supervisor.identity_for(cap.get_token()):
				# if self._supervisor._capabilities.check_azn(cap_id, self.dn):
					if found == False:
						msg = msg + "\"" + key + "\":["
						found = True
					msg = msg + mplane.model.unparse_json(cap) + ","
				if found == True:
					msg = msg[:-1].replace("\n","") + "],"
			msg = "{" + msg[:-1].replace("\n","") + "}"
			# print("\n>>> S_CapabilityHandler.get: msg = \n" + msg)
			self._respond_json_text(200, msg)
		
		except Exception as e:
			self.write( "{ERROR:\"" + str(e) + "\"}" )

		
class S_SpecificationHandler(mplane.client.MPlaneHandler):
	"""
	Receives specifications from a (GUI)client. If the client is
	authorized to run the spec, this supervisor forwards it 
	to the probe.

	"""

	def initialize(self, supervisor, tlsState):
		self._supervisor = supervisor
		self._tls = tlsState
		self.dn = get_dn(self._supervisor, self.request)
		print("\n>>> S_SpecificationHandler:init(): self.dn = " + self.dn)
	
	def post(self):
		
		# check the class of the certificate (Client, Component, Supervisor).
		# this function can only be used by clients
		if (self.dn.find("Clients") == -1 and self.dn != DUMMY_DN):
			self._respond_plain_text(401, "Not Authorized. Only Clients can use this function")
			return
			
		# unwrap json message from body
		if (self.request.headers["Content-Type"] == "application/x-mplane+json"):
			j_spec = json.loads(self.request.body.decode("utf-8"))
			
			# get DN and specification (only one, then this for cycle breaks)
			for key in j_spec:
				probe_dn = key
				spec = mplane.model.parse_json(json.dumps(j_spec[probe_dn]))
				
				if isinstance(spec, mplane.model.Specification):
					receipt = mplane.model.Receipt(specification=spec)
					
					if spec.get_label() not in self._supervisor._label_to_dn:
						self._respond_plain_text(403, "This measure doesn't exist")
						return
					if probe_dn not in self._supervisor._dn_to_ip:
						self._respond_plain_text(503, "Specification is unavailable. The component for the requested measure was not found")
						return
						
					# enqueue the specification
					if not self._supervisor.add_spec(spec, probe_dn):
						self._respond_plain_text(503, "Specification is temporarily unavailable. Try again later")
						return
												
					# return the receipt to the client        
					self._respond_message(receipt)
					return
				else:
					self._respond_plain_text(400, "Invalid format")
					return

					
class S_ResultHandler(mplane.client.MPlaneHandler):
	"""
	Receives receipts from a client. If the corresponding result
	is ready, this supervisor sends it to the probe.
	bnj: ???? 
	"""

	def initialize(self, supervisor, tlsState):
		self._supervisor = supervisor
		self._tls = tlsState
		self.dn = get_dn(self._supervisor, self.request)
		print("\n>>> S_ResultHandler:init(): self.dn = " + self.dn)
	
	def get(self):
	# def post(self):
		
		# check the class of the certificate (Client, Component, Supervisor).
		# this function can only be used by clients
		if (self.dn.find("Clients") == -1 and self.dn != DUMMY_DN):
			self._respond_plain_text(401, "Not Authorized. Only Clients can use this function")
			return
			
		# unwrap json message from body
		if (self.request.headers["Content-Type"] == "application/x-mplane+json"):
			rec = mplane.model.parse_json(self.request.body.decode("utf-8"))
			if isinstance(rec, mplane.model.Redemption):    
				# check if result is ready. if so, return it to client
				for dn in self._supervisor._results:
					for r in self._supervisor._results[dn]:
						if str(r.get_token()) == str(rec.get_token()):
							self._respond_message(r)
							self._supervisor._results[dn].remove(r)
							return
				meas = self._supervisor.measurements()
				
				# if result is not ready, return the receipt
				for dn in meas:
					for r in meas[dn]:
						if str(r.get_token()) == str(rec.get_token()):
							self._respond_message(r)
							return
				# if there is no measurement and no result corresponding to the redemption, it is unexpected
				self._respond_plain_text(403, "Unexpected Redemption")
				return
		else:
			if (self.request.headers["Content-Type"]):
				self._respond_plain_text(400, "Not in  'application/x-mplane+json' format")
			else:
				self._respond_plain_text(400, "No Content-Type defined")
		return

		
class ForwardHandler(tornado.web.RequestHandler):
	"""
	This handler implements a simple static HTTP redirect.
	"""
	def initialize(self, forwardUrl):
		self._forwardUrl = forwardUrl

	def get(self):
		self.redirect( self._forwardUrl )

	def post(self):
		self.redirect( self._forwardUrl )

		
class LoginHandler(tornado.web.RequestHandler):
	"""
	Implements authentication.
	
	GET: redirect to the login page.
	
	POST: checks the posted user credentials, and set a secure cookie named "user", if credentials are valid. Required content type is application/x-www-form-urlencoded,
	username and password parameters are required. Response code is always 200. Body is {} for successful login, or {ERROR: "some complaints"} in all other cases.     
	"""
	def initialize(self, supervisor, guicfgfile):
		self._supervisor = supervisor
		self._guicfgfile = guicfgfile

	def get(self):
		self.redirect("/gui/static/login.html")

	def post(self):
		f = open( self._guicfgfile, "r" )
		guiconf = json.load( f )
		f.close()
		userTry = self.get_body_argument("username", strip=True)
		pwdTry = self.get_body_argument("password", strip=True)

		if userTry in guiconf['users'].keys() and guiconf['users'][userTry]['password'] == pwdTry:            
			self.set_secure_cookie("user", userTry, 1)
			self.set_status(200);
			self.set_header("Content-Type", "text/json")
			self.write("{}")
		else:
			self.clear_cookie("user")
			self.set_status(200);
			self.set_header("Content-Type", "text/json")
			self.write("{ERROR:\"Authentication failed for user " + userTry + "\"}")

		self.finish()

		
class UserSettingsHandler(tornado.web.RequestHandler):
	"""
	Stores and gives back user-specific settings. Signed-in user defined by secure cookie named "user".
	Content-type is always text/json.
	
	GET: answers the settings JSON of the current user (initially it's "{}").

	POST: stores the posted settings JSON for the current user (it must be a valid JSON).
	"""
	def initialize(self, supervisor, guiusrdir):
		self._supervisor = supervisor
		self._guiusrdir = guiusrdir

	def get(self):
		user = self.get_secure_cookie("user")
		if user is None:
			self.redirect("/gui/static/login.html")
		else:
			try:
				self.set_status(200)
				self.set_header("Content-Type", "text/json")
				f = open( self._guiusrdir + os.sep + user.decode('utf-8'), "r" )
				self.write( f.read() )
				f.close()
			except Exception as e:
				self.write( "{ERROR:\"" + str(e) + "\"}" )
			self.finish()

	def post(self):
		user = self.get_secure_cookie("user")
		if user is None:
			self.redirect("/gui/static/login.html")
		else:
			try:
				f = open(self._guiusrdir + os.sep + user.decode('utf-8'), "w")
				f.write( self.request.body.decode("utf-8") )
				self.set_status(200)
				self.set_header("Content-Type", "text/json")
				self.write("{}\n")
				f.close()
			except Exception as e:
				self.write( "{ERROR:\"" + str(e) + "\"}" )
			self.finish()
			

class ListCapabilitiesHandler(mplane.client.MPlaneHandler):
	"""
	Lists the capabilites, registered in the Supervisor. Response is in mplane JSON format.

	GET: capabilites can be filtered by GET parameters named label, and names of parameters of the capability. Response is in mplane JSON format.

	POST is not supported.
	"""
	def initialize(self, supervisor, tlsState):
		self._supervisor = supervisor
		self._tls = tlsState
		_flist = {}

	def get(self):
		if self.get_secure_cookie("user") is None:
			self.redirect("/gui/static/login.html")
			return
		
		self._guiregistry = mplane.svgui_handlers.guiregistry( self._supervisor )
		_flist = filterlist(self, self._guiregistry)

		try:
			msg = ""
			for token in sorted(self._supervisor.capability_tokens()):
				cap = self._supervisor.capability_for(token)
				label = cap.get_label()
				# print("\n>>> cap = " + str(cap))
				
				found = False
				keep = True
				keep = match_filters( self, cap, _flist )

				# paramfilter = self.get_argument("label", default=None)
					
				if keep:
					id = mplane.client.BaseClient.identity_for(self._supervisor, token_or_label=token, receipt=False)
					id = id + "," + token
					if found == False:
						msg = msg + "\"" + id + "\":["
						found = True
					# print( id + " " + label + " " + token + "MATCHED")
					msg = msg + mplane.model.unparse_json(cap) + ","
				# else:
					# print( id + " " + label + " " + token + "SKIPPED")
					
				if found == True:
					msg = msg[:-1].replace("\n","") + "],"
			
			msg = "{" + msg[:-1].replace("\n","") + "}"
			# print("\n>>> (filtered) capabilities: msg = \n" + msg)
			self._respond_json_text(200, msg)
			
		except Exception as e:
			self.write( "{ERROR:\"" + str(e) + "\"}" )

	def post(self):
		self.set_status(405, GUI_LISTCAPABILITIES_PATH + " is a read-only GET function")

 
class ListPendingsHandler(mplane.client.MPlaneHandler):
	"""
	Lists all the pending measurement (specifications and receipts) from supervisor.
	
	GET compose mplane json representations of pending specifications and receipts, in the following format:
		{ DN1: [ receipt1, receipt2 ], DN2: [ specification1, receipt3, ... ], ... }
	
	POST is not supported.
	
	"""
	
	def initialize(self, supervisor, tlsState):
		self._supervisor = supervisor
		self._tls = tlsState
		_flist = {}

	def get(self):
		if self.get_secure_cookie("user") is None:
			self.redirect("/gui/static/login.html")
			return

		# TODO: Envelope handling!!!
		
		self._guiregistry = mplane.svgui_handlers.guiregistry(self._supervisor)
		_flist = filterlist(self, self._guiregistry)
		# print("_flist = " + str( _flist ))
		try:
			msg = ""
			for token in self._supervisor.receipt_tokens():
				rec = self._supervisor._receipts[token]
				# print("rec (in json) = " + mplane.model.unparse_json(rec))
				dnMsg = ""
				found = False
				keep = True
				keep = match_filters( self, rec, _flist )

				if keep:
					id = mplane.client.BaseClient.identity_for(self._supervisor, token_or_label=token, receipt=True)
					id = id + "," + token
					if found == False:
						dnMsg = dnMsg + "\"" + id + "\":["
						found = True
					paramStr = ""
					for paramname in rec.parameter_names():
						paramStr = paramStr + "\"" + paramname + "\": \"" + str(rec.get_parameter_value(paramname)) + "\","
					dnMsg = dnMsg + "{ \"receipt\":\"measure\", \"label\":\"" + rec.get_label() + "\",  \"when\":\"" + str(rec.when()) + "\", \"token\":\"" + rec.get_token() + "\", \"parameters\": {" + paramStr[:-1] + "} },"
				# else:
					# print("        SKIPPED")

				if found == True:
					msg = msg + dnMsg[:-1] + "],"
			
			msg = "{" + msg[:-1].replace("\n","") + "}"
			self._respond_json_text(200,msg)
			
		except Exception as e:
			self.write( "{ERROR:\"" + str(e) + "\"}" )

	def post(self):
		self.set_status(405, GUI_LISTPENDINGS_PATH + " is a read-only GET function")

		
def write_imsg( handler, res, filterlist, msgtype ):
	_imsg = ""
	found = False
	keep = True
	label = ""
	keep = match_filters( handler, res, filterlist )
	print(">>> match_filters = " + str(keep) )
	if keep:
		# envelope's token should be use for the individual messages as well
		id = handler.dn + "," + res.get_token()
		if found == False:
			_imsg = _imsg + "\"" + id + "\":["
			found = True
		paramStr = ""
		if msgtype == "Envelope":
			# label = "< " + res.get_label() + " >"
			label = "[><] " + res.get_label()
		elif msgtype == "Result":
			label = res.get_label()
			for paramname in res.parameter_names():
				paramStr = paramStr + "\"" + paramname + "\": \"" + str(res.get_parameter_value(paramname)) + "\","
		elif msgtype == "Exception":
			return _imsg
		print(">>>>>>>>> label = " + label)
		_imsg = _imsg + "{ \"result\":\"measure\", \"label\":\"" + label + "\",  \"when\":\"" + str(res.when()) + "\", \"token\":\"" + res.get_token() + "\", \"parameters\": {" + paramStr[:-1] + "} },"
	else:
		print("        SKIPPED")
	if found == True:
		_imsg = _imsg[:-1] + "],"
	print(">>>>> write_imsg: " + _imsg )
	return _imsg


class ListResultsHandler(mplane.client.MPlaneHandler):
# class ListResultsHandler(tornado.web.RequestHandler):
	"""
	Lists the results from Supervisor.
	
	GET: lists results from the supervisor in a JSON array, format is as follows:
	  [ { result:'measure', label:'CAPABILITY_LABEL',  when:'WHEN_OF_RESULT', token:'TOKEN_OF_RESULT',
		  parameters: { specificationParam1:"value1", specificationParam2:"value2", ... }, ... ]
	  Filtering can be done by GET parameters called label, and names of parameters of the capability.

	POST: not supported
	"""

	def initialize(self, supervisor, tlsState):
		# print(">>> sv_gui_handlers.py:ListResultsHandler.initialize():")
		self._supervisor = supervisor
		self._tls = tlsState
		# TODO: this gives back supervisor's identity, not the client's
		self.dn = get_dn(self._supervisor, self.request)
		# peer_dn = self._tls.extract_peer_identity(self._supervisor, self.request)
		# print("self.dn = " + self.dn + ", peer_dn = " + peer_dn )
		_flist = {}

	def get(self):
		if self.get_secure_cookie("user") is None:
			self.redirect("/gui/static/login.html")
			return

		self._guiregistry = mplane.svgui_handlers.guiregistry(self._supervisor)
		_flist = filterlist(self, self._guiregistry)
		print(">>> _flist = " + str( _flist ))
		try:
			msg = ""
			# nr = []
			for token in self._supervisor._results:
				res = self._supervisor.result_for(token)
				imsg = ""
				print(">>> processing token " + str(token) + " of type " + str(type(res)) + "...")
				if isinstance( res, mplane.model.Exception):
					# msg = msg + write_imsg( self, res, _flist, "Exception" )
					# msg = msg + imsg
					pass
				elif isinstance( res,mplane.model.Result ):
					msg = msg + write_imsg( self, res, _flist, "Result" )
					# msg = msg + imsg
				elif isinstance ( res, mplane.model.Envelope ):
					msg = msg + write_imsg( self, res, _flist, "Envelope" )
					# msg = msg + imsg
					for ires in res.messages():
						if isinstance( ires, mplane.model.Result ):
							msg = msg + write_imsg( self, ires, _flist, "Result" )
						else:
							# msg = msg + write_imsg( self, ires, _flist, "Exception" )
							pass
						# msg = msg + imsg
				else:
					# print(">>> neither Result nor Envelope: " + str(res))
					raise NotImplementedError("only Results and Envelope allowed")
					# pass
				# msg = msg + imsg
			# msg = "{" + msg + imsg[:-1].replace("\n","") + "}"
			msg = "{" + msg[:-1].replace("\n","") + "}"
				
			# print("\n-------------------------------\n>>> results msg = \n" + msg)
			self._respond_json_text(200,msg)
			
		except Exception as e:
			self.write( "{ERROR:\"" + str(e) + "\"}" )

	def post(self):
		print(">>> sv_gui_handlers.py:ListResultsHandler.get():")
		self.set_status(405, GUI_LISTCAPABILITIES_PATH + " is a read-only GET function")
	

class GetResultHandler(mplane.client.MPlaneHandler):
	"""
	GET: Get result for specified token.
	
	POST: Get results for a filter like a specification.
		Posted JSON is like
			{ capability:ping-detail-ip4, parameters:{"source.ip4":"192.168.96.1", "destination.ip4":"217.20.130.99" },
			"resultName":"delay.twoway.icmp.us", from: 1421539200000, to: 1421625600000 }

			- timestamps are in ms
			- capability is the label of the capability
			- no component DN is defined, results of different components can be merged
			- resultName: only one result column is required -> one line will be drawn from the response.
		  
		The response is like as follows:

		{ "result":"measure", "version":0, "registry": "http://ict-mplane.eu/registry/core", "label": ping-detail-ip4, "when": "2015-01-18 17:25:50.785761 ... 2015-01-18 17:28:00.785367",
			"parameters":{"source.ip4":"192.168.96.1", "destination.ip4":"217.20.130.99" }, "results": ["time", "delay.twoway.icmp.us"],
			"resultvalues": [["2015-01-18 17:25:50.785761", 20], ["2015-01-18 17:25:51.785761", 37], ["2015-01-18 17:28:00.785761", 31], ...] }

			- when: shows times between results are found
			- resultvalues: it has always 2 columns, first is time, second is requested by client in  "resultName"
	"""
	def initialize(self, supervisor, tlsState):
		print("\n>>> sv_gui_handlers.py:GetResultHandler.initialize():")  
		self._supervisor = supervisor
		self._tls = tlsState
		self.dn = get_dn(self._supervisor, self.request)
		print(">>> GetResultsHandler.initialize: self.dn = " + self.dn + "\n" + str(self._supervisor._results))

	def get(self):
		if self.get_secure_cookie("user") is None:
			self.redirect("/gui/static/login.html")
			return
			
		try:
			token = self.get_argument("token")
			res = self._supervisor.result_for(token)
			if isinstance(res, mplane.model.Envelope):
				# we should merge the result values (if coming from the same capability)
				nres = mplane.model.Result()
				resval = []
				for ires in res.messages():
					nres = ires
					resval.append( ires._result_rows())
					# params.append(ires.get_params)
					# resval.append(ires.resultvalues)
				
				
				# nres = "{\"label\": \"" + res.get_label() + "\", \"parameters\": {"
				# nres = nres + res._params + "}, \"registry\": \"" + registry 
				# nres = nres + "\", \"result\": \"measure\", \"results\": [" + results + "],"
				# nres = nres + "\"resultvalues\": [" + resval + "], \"token\": \"" + res.get_token() 
				# nres = nres + "\", \"version\": 1, \"when\": \"" + res.when() + "\" }"
			else:
				mplane.model.render_text(res)
				self._respond_json_text(200, mplane.model.unparse_json(res))

		except Exception as e:
			self.write( "{ERROR:\"" + str(e) + "\"}" )

	def post(self):
		# used in the 'On-Demand Chart View menu I think
		return
		queryJson = json.loads( self.request.body.decode("utf-8") )
		print("\n******\n\n queryJson = " + queryJson)
		fromTS = datetime.datetime.fromtimestamp( queryJson["from"] / 1000 )
		toTS = datetime.datetime.fromtimestamp( queryJson["to"] / 1000 )        
		print( 'query time: ' + str(fromTS) + " - " + str(toTS))
		
		selectedResults = []
		for dn in self._supervisor._results.keys():
			for res in self._supervisor._results[dn]:
				skip = res.get_label() != queryJson["capability"]
				for paramname in res.parameter_names():
					if str(res.get_parameter_value(paramname)) != queryJson["parameters"][paramname]:
						skip = True
				(resstart,resend) = res.when().datetimes()
				print( '   result time: ' + str(resstart) + " - " + str(resend) + ": " + str(resend < fromTS or resstart > toTS))

				skip = skip or resend < fromTS or resstart > toTS
				if not skip:
					selectedResults.append(res)
		
		if len(selectedResults) == 0:
			self.write("{ERROR:\"No result was found\"}");
			self.finish()
			return;
		
		resultvalues = []
		response = { "result":"measure", "version":0, "registry": "http://ict-mplane.eu/registry/core", 
			"label": queryJson["capability"], "when": str(mplane.model.When(a=fromTS, b=toTS)), "parameters": queryJson["parameters"],
			"results": ["time", queryJson["result"]], "resultvalues": resultvalues }
				
		for res in selectedResults:
			resultvalues.extend( res._result_rows() )

		sorted( resultvalues, key=lambda resultrow: resultrow[0] )
		print("\n------------->>> sortedresult : " + response + "\n<<<<<<<<<<<<<")
		self.write( json.dumps(response) )
		self.finish()

		
class RunCapabilityHandler(mplane.client.MPlaneHandler):
	"""
	  It runs a capability.    
	  
	  POST: URI should be gui/run/capability?DN=Probe.Distinguished.Name 
	  Posted data is a fulfilled capability, not a specification. Fulfilled means field when has a concrete value, and every parameter has a value as well.
	"""

	def initialize(self, supervisor, tlsState):
		# print("\n>>> sv_gui_handlers.py:RunCapabilityHandler.initialize():")
		self._supervisor = supervisor
		self._tls = tlsState

	def get(self):
		self.set_status(405, GUI_LISTCAPABILITIES_PATH + " supports POST only")
		self.finish()

	def post(self):
		try:
			dn = self.get_query_argument("DN", strip=True)
			# token = self.get_query_argument("token")
			posted = self.request.body.decode("utf-8")
			
			filledCapability = mplane.model.parse_json( posted )           
			spec = mplane.model.Specification( capability=filledCapability )
			# print(">>> spec (1) = " + str(spec))
			cap_label = spec.get_label()
			if cap_label:
				cap = mplane.client.BaseClient.capability_for(self._supervisor,cap_label)
			else:
				raise KeyError("no such token or label "+cap_label)
			# print(">>> RunCapabilityHandler DN = " + dn + ", cap_label = " + cap_label)
			# Capability posted by GUI contains parameter values as constraints allowing single value only
			for paramname in spec.parameter_names():
				spec._params[paramname].set_single_value()
			spec.validate()
			mplane.svgui.ClientGui.invoke_capability(self._supervisor, cap_label, spec._when, spec.parameter_values())
			addtohistory(self._supervisor._history, spec._when, spec.parameter_values()  )
			self.write("{}")
			self.finish()

		except Exception as e:
			self.write( "{ERROR:\"" + str(e) + "\"}" )

			
class ListProbesHandler(mplane.client.MPlaneHandler):
	"""
	From class ListCapabilitiesHandler
	Lists the probes registered in the Supervisor. Response is in pure JSON format.

	"""
	def initialize(self, supervisor, tlsState):
		self._supervisor = supervisor
		self._tls = tlsState
		_flist = {}

	def get(self):
		if self.get_secure_cookie("user") is None:
			self.redirect("/gui/static/login.html")
			return

		try:
			msg = ""
			for token in sorted(self._supervisor.capability_tokens()):
				id = mplane.client.BaseClient.identity_for(self._supervisor, token_or_label=token, receipt=False)
				msg = msg + "\"" + id + "," + token + "\"," 
			# msg = "{ list:[ " + msg[:-1].replace("\n","") + "]}"
			msg = "{ list: [ " + msg[:-1] + " ] }"
			# print("\n>>> probelist: " + msg)
			self._respond_json_text(200, msg)
			
		except Exception as e:
			self.write( "{ERROR:\"" + str(e) + "\"}" )

	def post(self):
		self.set_status(405, GUI_PROBES_PATH + " is a read-only GET function")

			
class StopPendingHandler(mplane.client.MPlaneHandler):
	"""
	  It stops a pending measurement.    
	  
	  POST: URI should be gui/stop/capability?DN=SpecificationID (ProbeDN,<token>) 
	  Posted data is a fulfilled capability, not a specification. Fulfilled means field when has a concrete value, and every parameter has a value as well.
	"""

	def initialize(self, supervisor, tlsState):
		print("\n>>> StopPendingHandler.initialize():")
		self._supervisor = supervisor
		self._tls = tlsState

	def get(self):
		self.set_status(405, GUI_STOPPENDING_PATH + " supports POST only")
		self.finish();

	def post(self):
		print("\n>>> StopPendingHandler.post():")
		try:
			dn = self.get_query_argument("DN", strip=True)
			# dn = self.get_argument("DN", strip=True)
			meas_tol = dn.split(',')[1]
			# cap_label = spec.get_label()
			# print(">>> interrupting meas token = " + meas_tol + ", label = " + cap_label )
			print(">>> interrupting meas token = " + meas_tol )
			self._supervisor.interrupt_capability(meas_tol)
			self.write("{}")
			self.finish()

		except Exception as e:
			self.write( "{ERROR:\"" + str(e) + "\"}" )
		self.set_status(405, GUI_STOPPENDING_PATH + " supports GET only")
		self.finish();


class PortletsHandler(mplane.client.MPlaneHandler):
	"""
	get an url <host>:<port>/gui/portlets?objectId=<name> and returns <name>.json from GUI_PORTLETS_DIR ("www/test/json/nisz-en")

	"""
	def initialize(self, supervisor, tlsState):
		print("\n>>> sv_gui_handlers.py:PortletsHandler.initialize():")
		self._supervisor = supervisor
		self._tls = tlsState

	def get(self):
		try:
			ObjectId = self.get_query_argument("objectId", strip=True)
			portletfile = GUI_PORTLETS_DIR + ObjectId + "-def.json"
			print(">>> file to return = " + portletfile )		
			f = open( portletfile, "r" )
			self.set_status(200, GUI_PORTLETS_PATH + " found something")
			self.write( f.read() )
			f.close()
			self.finish()
		except Exception as e:
			self.write( "{ERROR:\"" + str(e) + "\"}" )

	def post(self):
		self.set_status(405, GUI_PORTLETS_PATH + " supports POST only")
		self.finish()
