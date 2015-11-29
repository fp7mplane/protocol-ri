#
# vim: tabstop=4 shiftwidth=4 softtabstop=4
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
import mplane.ui.svgui

from datetime import datetime
import html.parser
import urllib3
import json
import collections
import sys
import os
import io
import zipfile
import re

from threading import Thread
import queue

import tornado.web
import tornado.httpserver
import tornado.ioloop
import logging
from tornado.web import HTTPError

GUI_PORTLETS_DIR = "www/test/json/nisz-en/"	# TODO: fix for a normal dir
GUI_PORTLETS_PATH = "gui/portlets"

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

# FIXME HACK
# some urllib3 versions let you disable warnings about untrusted CAs,
# which we use a lot in the project demo. Try to disable warnings if we can.
try:
	urllib3.disable_warnings()
except:
	pass

	
def get_dn(client, request):
	"""
	Extracts the DN from the request object. 
	If SSL is disabled, returns a dummy DN
	
	"""
	if client._tls_state._keyfile:
		dn = client._tls_state._identity
	else:
		if "Forged-Mplane-Identity" in request.headers.keys():
			dn = request.headers["Forged-Mplane-Identity"]
		else:
			dn = DUMMY_DN
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
	_r = mplane.model.registry_for_uri(None)
	_outfile = _supervisor._gui_regfile
	
	_new = collections.OrderedDict()
	#_new["registry-format"] = "mplane-0"
	#_new["registry-revision"] = int(_r._revision)
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

	for token in _supervisor._client.capability_tokens():
		cap = _supervisor._client.capability_for(token)
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
		
	#logging.debug(">>> final filterlist: " + str( _filterlist) )
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
				_dn = get_dn(self._client, self.request)
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
		hist.add( paramname, str( params.get(paramname) ), False)
	val = str( when )
	hist.add( 'when', val )


###########################################################
# sv_gui_handlers
###########################################################

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
		self._client = supervisor._client
		self._tls = tlsState

	def get(self):
		if self.get_secure_cookie("user") is None:
			self.redirect("/gui/static/login.html")
			return
		self._guiregistry = guiregistry( self._supervisor )
		flist = filterlist(self, self._guiregistry)
        
		try:
			msg = "{ \n"
			for token in sorted(self._client.capability_tokens()):
				cap = self._client.capability_for(token)
				# logging.debug("============filterig cap %s result %r" % (cap.get_label(),keep))
				# paramfilter = self.get_argument("label", default=None)
					
				if match_filters( self, cap, flist ):
					id = self._client.identity_for(token_or_label=token, receipt=False)
					msg += '"%s,%s":[%s],\n' % (id, token, mplane.model.unparse_json(cap))
			msg=msg[:-2] + '}'
			#logging.debug("Returning caps: %s" % msg)
			self._respond_json_text(200, msg)
			
		except Exception as e:
			e.traceback()
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
		self._client = supervisor._client
		self._tls = tlsState

	def get(self):
		if self.get_secure_cookie("user") is None:
			self.redirect("/gui/static/login.html")
			return

		# TODO: Envelope handling!!!
		
		self._guiregistry = guiregistry( self._supervisor )
		flist = filterlist(self, self._guiregistry)

		try:
			msg = "{ \n"
			for token in self._client.receipt_tokens():
				rec = self._client._receipts[token]
				# print("rec (in json) = " + mplane.model.unparse_json(rec))
				if match_filters( self, rec, flist ):
					id = self._client.identity_for(token_or_label=token, receipt=True)
					id = id + "," + token
					msg += '"%s,%s":[%s],\n' % (id, token, mplane.model.unparse_json(rec))
			msg = msg[:-2] + "\n}"
			#logging.debug("Returning specs: %s" % msg)
			self._respond_json_text(200, msg)
			
		except Exception as e:
			self.write( "{ERROR:\"" + str(e) + "\"}" )

	def post(self):
		self.set_status(405, GUI_LISTPENDINGS_PATH + " is a read-only GET function")

		
def write_imsg( handler, res, filterlist, msgtype ):
	"""
	process messages according to their type:
	Result		- give back message
	Envelope	- give back message with result counter and envelope icon
	Exception	- give back message with 
	"""
	_imsg = ""
	label = ""
	paramStr = ""
	found = False
	keep = True
	keep = match_filters( handler, res, filterlist )
	# print(">>> match_filters = " + str(keep) )
	if keep:
		#print(">>> orig res = " + mplane.model.unparse_json(res))
		nres = res
		if msgtype == "Result":
			# nres = mplane.model.Result()
			# nres = res
			# TODO: server side trims leading whitespace
			label = nres.get_label()
			label = label.rjust( len(label)+4 )
			nres.set_label(label)
			# for paramname in res.parameter_names():
				# paramStr = paramStr + "\"" + paramname + "\": \"" + str(res.get_parameter_value(paramname)) + "\","
		elif msgtype == "Envelope":
			# nres = mplane.model.Envelope()
			# nres = res
			msgcount = mplane.model.Envelope.__len__(nres)
			label = "[><] (" + msgcount + ")" + nres.get_label()
			nres.set_label(label)
		elif msgtype == "Exception":
			# label = "!   " + nres.get_token()
			# nres.set_label(label)
			pass
		else:
			raise NotImplementedError("only Results, Envelopes or Exceptions allowed")
		#print(">>> new res = " + mplane.model.unparse_json(res))
		return mplane.model.unparse_json(nres)
	else:
		return _imsg
		
		""""
		# envelope's token should be use for the individual messages as well
		id = handler.dn + "," + res.get_token()
		if found == False:
			_imsg = "\"" + id + "\":["
			found = True
		label = res.get_label()
		if msgtype == "Envelope":
			label = "[><] " + res.get_label()
		elif msgtype == "Result":
			# TODO: server side trims leading whitespace
			label = label.rjust(len(label)+4)
			for paramname in res.parameter_names():
				paramStr = paramStr + "\"" + paramname + "\": \"" + str(res.get_parameter_value(paramname)) + "\","
		elif msgtype == "Exception":
			return _imsg
		# print(">>>>>>>>> label = " + label)
		_imsg = _imsg + "{ \"result\":\"measure\", \"label\":\"" + label + "\",  \"when\":\"" + str(res.when()) + "\", \"token\":\"" + res.get_token() + "\", \"parameters\": {" + paramStr[:-1] + "} },"
	# else:
		# print("        SKIPPED")
	if found == True:
		_imsg = _imsg[:-1] + "],"
	print(">>> new res = " + mplane.model.unparse_json(_imsg))
	return _imsg
	"""


class ListResultsHandler(mplane.client.MPlaneHandler):
	"""
	Lists the results from Supervisor.
	
	GET: lists results from the supervisor in a JSON array, format is as follows:
	  [ { result:'measure', label:'CAPABILITY_LABEL',  when:'WHEN_OF_RESULT', token:'TOKEN_OF_RESULT',
		  parameters: { specificationParam1:"value1", specificationParam2:"value2", ... }, ... ]
	  Filtering can be done by GET parameters called label, and names of parameters of the capability.

	POST: not supported
	"""

	def initialize(self, supervisor, tlsState):
		self._supervisor = supervisor
		self._client = supervisor._client
		self._tls = tlsState

	def get(self):
		if self.get_secure_cookie("user") is None:
			self.redirect("/gui/static/login.html")
			return

		self._guiregistry = guiregistry( self._supervisor )
		flist = filterlist(self, self._guiregistry)


		try:
			msg = "{ \n"
			# nr = []
			for token in self._client._results:
				res = self._client.result_for(token)
				imsg = ""
				# print(">>> processing token " + str(token) + " of type " + str(type(res)) + "...")
				if isinstance( res, mplane.model.Result ):
					id = self._client.identity_for(token_or_label=token, receipt=True)
					id = id + "," + token
					msg += '"%s,%s":[%s],\n' % (id, token, mplane.model.unparse_json(res))

				elif isinstance( res, mplane.model.Exception):
					msg += write_imsg( self, res, flist, "Exception" )
				elif isinstance ( res, mplane.model.Envelope ):
					msg += '"aaaaa,bbbb":' + write_imsg( self, res, flist, "Envelope" )
				else:
					raise NotImplementedError("only Results, Envelopes or Exceptions allowed")
			msg = msg[:-2] + "\n}"
				
			#logging.debug("Returning results: %s" % msg)
			self._respond_json_text(200,msg)
			
		except Exception as e:
			self.write( "{ERROR:\"" + str(e) + "\"}" )

	def post(self):
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
		self._client = supervisor._client
		self._tls = tlsState
		self.dn = get_dn(self._client, self.request)
		print(">>> GetResultsHandler.initialize: self.dn = " + self.dn + "\n" + str(self._client._results.keys()) +  str(self._client._result_labels.keys()))

	def get(self):
		if self.get_secure_cookie("user") is None:
			self.redirect("/gui/static/login.html")
			return
			
		try:
			token = self.get_argument("token")
			logging.debug("token searched: %s" % token)
			res = self._client.result_for(token)
			if isinstance(res, mplane.model.Envelope):
				# we should merge the result values (if coming from the same capability)
				nres = mplane.model.Result()
				resval = []
				for ires in res.messages():
					nres = ires
					if isinstance(ires, Result):
						resval.append( ires._result_rows())
						# params.append(ires.get_params)
						# resval.append(ires.resultvalues)
					else:
						# TODO: do we need handling of Exceptions?
						pass
				
				
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
		for dn in self._client._results.keys():
			for res in self._client._results[dn]:
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
		self._client = supervisor._client
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
			#logging.debug("Posted CAPABILITY %s " + posted)			
			#logging.debug("Posted CAPABILITY TOK %s " % filledCapability.get_token())			
			spec = mplane.model.Specification( capability=filledCapability )
			#logging.debug("Created SPEC %s Values: %s %s %s" % (repr(spec), spec.parameter_values(), spec.get_label(),spec.get_token()))			
			# print(">>> spec (1) = " + str(spec))
			
			if filledCapability.get_token:
				cap = self._client.capability_for(filledCapability.get_token())
			else:
				raise KeyError("no such token or label %s" % filledCapability.get_token())
			#print("CAPABILITY SELECTED %s" % cap)
			# print(">>> RunCapabilityHandler DN = " + dn + ", cap_label = " + cap_label)
			# Capability posted by GUI contains parameter values as constraints allowing single value only
			for paramname in spec.parameter_names():
				spec._params[paramname].set_single_value()
			spec.validate()
			self._client.invoke_capability(filledCapability.get_token(), spec._when, spec.parameter_values())
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
			for token in sorted(self._supervisor._client.capability_tokens()):
				id = self._supervisor._client.identity_for(self, token_or_label=token, receipt=False)
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
			# print(">>> file to return = " + portletfile )		
			f = open( portletfile, "r" )
			self.set_status(200, GUI_PORTLETS_PATH)
			self.write( f.read() )
			f.close()
			self.finish()
		except Exception as e:
			self.write( "{ERROR:\"" + str(e) + "\"}" )

	def post(self):
		self.set_status(405, GUI_PORTLETS_PATH + " supports GET only")
		self.finish()
