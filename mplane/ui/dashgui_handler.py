#
# vim: tabstop=4 shiftwidth=4 softtabstop=4
##
# mplane SVGUI Dashboard
# (c) 2014-2015 mPlane Consortium (http://www.ict-mplane.eu)
#               Authors: A Bakay,
#                       B.Szabo
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


import json
import os
import io
import zipfile
import re

import tornado.web
import tornado.httpserver


class DashboardHandler(tornado.web.RequestHandler):
	"""
	POST: 
         URI should be gui/dashboard?command=xxxx&dashboard=<dashboardname>&key=<dashboardkey>&target=<targetspec>
         commands:  
		createNew	target is optional and ignored
		uploadConfig    target may be: "all", "dashboard" or any portletID
		uploadData	target may be any portletID
	 targets:
		"allzipped" -       used for uploadng a ZIP with all configs
		"dashboard" - used to upload dashboard.json
		portletID   - used to upload portletID-def.json  or portletID-data.json 
	"""
	def initialize(self, supervisor, guicfgfile):
		pass

	def get(self):
		try:
			command = self.get_query_argument("command", strip=True)
			if self.get_secure_cookie("user") is None:
				raise HTTPError(401, reason="Login required")
			if command == "list":
				dirname = "dashboards/"
				self.set_status(200);
				self.set_header("Content-Type", "text/json")
				try:
					self.write(json.dumps(sorted(os.listdir(dirname))));
				except:
					raise HTTPError(404, reason="cannot list dashboard store")
			elif command == "getConfig" or command == "getData" or command == "getResource":
				dash = self.get_query_argument("dashboard", strip=True)
				dirname = "dashboards/" + dash
				readmode="r"	
				if command == "getResource":
					resource = self.get_query_argument("resource", strip=True);
					if re.search("\.png$",resource, flags=re.I): self.set_header("Content-Type", "image/png")
					if re.search("\.jpg$",resource, flags=re.I): self.set_header("Content-Type", "image/jpeg")
					fn= dirname + '/' + resource
					readmode="rb"
				else:
					self.set_header("Content-Type", "text/json")
					try: 
						target = self.get_query_argument("target", strip=True)
					except: 
						target = self.get_query_argument("objectId", strip=True)
					fn= dirname + '/' + target + ("-def" if command == "getConfig" else "-data") + ".json";
					if target == 'dashboard' :
						if command != "getConfig" : raise HTTPError(500, reason="invalid target for getData")
						fn= dirname + '/dashboard.json';
				try:
					f = open(fn, readmode)
					self.write(f.read())
				except BaseException as e:
					print("DASHGUI CATCH %s \n" % type(e))
					raise HTTPError(404, reason="error reading file %s" % fn)
			else:
				raise HTTPError(400, reason="Unknown command: '" + command + "'")
			self.write('\n');
		except tornado.web.HTTPError as e: 	
			print("DASHGUI CATCH %s, %s \n" % ( type(e), vars(e)))
			self.set_status(e.status_code);
			self.set_header("Content-Type", "text/json")
			self.write("{\"errorDescription\":\"Execution error: %s\"}\n" % e.reason)
		self.finish()
			


	def post(self):
		try:
			command = self.get_query_argument("command", strip=True)
			dash = self.get_query_argument("dashboard", strip=True)
			key = self.get_query_argument("key", strip=True)
			dirname = "dashboards/" + dash
			if command == "createNew":
				if self.get_secure_cookie("user") is None:
					raise HTTPError(401, reason="Login required")
				if os.path.exists(dirname) :
					raise HTTPError(403, reason="Dashboard '" + dash + "' exists")
				os.makedirs(dirname)
				f = open(dirname + "/settings.json", 'w')
				json.dump({ "secretkey": key }, f)
				f.write("\n")
				f.close()
			else:
				if not os.path.exists(dirname) :
					raise HTTPError(404, reason="Dashboard '" + dash +"' not found")
				f = open(dirname + "/settings.json", 'r')
				settings=json.load(f);
				f.close()
				if settings["secretkey"] != key:
					raise HTTPError(401, reason="Invalid key")
				fn=None
				portletconf=False;
				if command == "uploadConfig":
					target = self.get_query_argument("target", strip=True)
					fn= dirname + '/' + target + "-def.json";
					if target == 'dashboard':
						fn= dirname + '/dashboard.json';
					elif target == 'allzipped':
						bytes = io.BytesIO(self.request.body);
						try:
							zip = zipfile.ZipFile(bytes);
							if "dashboard.json" not in zip.namelist(): raise HTTPError(406, reason="dashboard.json missing from ZIP")
							for fn in zip.namelist():
								if not re.fullmatch("(dashboard|.*-def|.*-data).json|resources/.*",fn): 
									raise HTTPError(406, reason="forbidden file in ZIP: "+ fn)
							try:
								shutil.rmtree(dirname)
								os.makedirs(dirname)
								f = open(dirname + "/settings.json", 'w')
								json.dump(settings,f)
								zip.extractAll(dirname)
							except: raise HTTPError(500, reason="cannot create files") 
						except zipfile.BadZipFile:
								raise HTTPError(406, reason="Invalid ZIP uploaded") 
					else:
						portletconf=True;
				elif command == "uploadData":				
					target = self.get_query_argument("target", strip=True)
					fn= dirname + '/' + target + "-data.json";
				elif command == "uploadResource":
					resourcename = self.get_query_argument("resource", strip=True)
					if re.match("resources/", resourcename) is None: raise HTTPError(406, reason="Invalid resource specified") 
					try: 
						f = open(dirname + '/' + resourcename,"wb")
						f.write(io.BytesIO(self.request.body).read())
						f.close()
					except  BaseException as e:
						print("MYLOG  CATCHE1 %s" % type(e), vars(e), "\n")
						raise HTTPError(406, reason="Invalid resource uploaded")							
				else:
					raise HTTPError(400, reason="Unknown command: '" + command + "'")
				if fn is not None: 
					f = open(fn,"w")
					try:
						bodystr=self.request.body.decode('utf-8')
						newobj=json.loads(bodystr)
						if portletconf:
							if "measurements" in newobj["list"][0]["content"]:
								uu=self.request.uri.replace("uploadConfig","getData")
								newobj["list"][0]["content"]["measurements"][0]["dataUrl"]=uu
							bodystr=json.dumps(newobj)
							bodystr=bodystr.replace("${DASHBOARD_RESOURCE}",self.request.uri.replace("uploadConfig","getResource")+"&resource=resources")
					except  BaseException as e:
						print("MYLOG  CATCHE1 %s \n" % type(e))
						raise HTTPError(406, reason="Invalid JSON uploaded")		
					f.write(bodystr)
					if not bodystr.endswith("\n"): 
						f.write("\n")
					f.close()
			self.set_status(200);
			self.set_header("Content-Type", "text/json")
			self.write("{}")
		except tornado.web.HTTPError as e: 	
			print("MYLOG  CATCH %s, %s \n" % ( type(e), vars(e)))
			self.set_status(e.status_code);
			self.set_header("Content-Type", "text/json")
			self.write("{\"errorDescription\":\"Execution error: %s \"}\n" % e.reason)
		self.finish()

		
