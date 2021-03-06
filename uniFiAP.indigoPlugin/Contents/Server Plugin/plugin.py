#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# uniFi Plugin
# Developed by Karl Wachs
# karlwachs@me.com

import datetime
import simplejson as json
import subprocess
import fcntl
import os
import sys
import pwd
import time
import Queue
import random
import socket
import getNumber as GT
import MAC2Vendor
import threading
import logging
import copy
import json
import requests
import inspect

requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

import cProfile
import pstats


dataVersion = 2.0

## Static parameters, not changed in pgm
_GlobalConst_numberOfAP	 = 5
_GlobalConst_numberOfSW	 = 13

_GlobalConst_numberOfGroups = 20
_GlobalConst_groupList		= [u"Group"+unicode(i) for i in range(_GlobalConst_numberOfGroups)]
_GlobalConst_dTypes			= ["UniFi","gateway","DHCP","SWITCH","Device-AP","Device-SW-8","Device-SW-10","Device-SW-18" ,"Device-SW-26","Device-SW-52","neighbor"]
################################################################################
# noinspection PyUnresolvedReferences,PySimplifyBooleanCheck,PySimplifyBooleanCheck
class Plugin(indigo.PluginBase):
	####-----------------			  ---------
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

		#pfmt = logging.Formatter('%(asctime)s.%(msecs)03d\t%(levelname)-12s\t%(name)s.%(funcName)-25s %(msg)s', datefmt='%Y-%m-%d %H:%M:%S')
		#self.plugin_file_handler.setFormatter(pfmt)

		self.pluginShortName 	= "UniFi"
		self.unifiApiWebPage			=  self.pluginPrefs.get(u"unifiApiWebPage", "/api/s/")

		self.UDMPro = "False"
		self.apiLoginPath = "/api/login"
		if self.unifiApiWebPage == "/proxy/network/api/s/":
			self.UDMPro = "True"
			self.apiLoginPath = "/api/auth/login"
		
		
		self.quitNow					= ""
		self.getInstallFolderPath		= indigo.server.getInstallFolderPath()+"/"
		self.indigoPath					= indigo.server.getInstallFolderPath()+"/"
		self.indigoRootPath 			= indigo.server.getInstallFolderPath().split("Indigo")[0]
		self.pathToPlugin 				= self.completePath(os.getcwd())

		major, minor, release 			= map(int, indigo.server.version.split("."))
		self.indigoRelease				= release
		self.indigoVersion 				= float(major)+float(minor)/10.
		if self.indigoVersion < 7.3:
			import versionCheck as VS

		self.pluginVersion				= pluginVersion
		self.pluginId					= pluginId
		self.pluginName					= pluginId.split(".")[-1]
		self.myPID						= os.getpid()
		self.pluginState				= "init"

		self.myPID 						= os.getpid()
		self.MACuserName				= pwd.getpwuid(os.getuid())[0]

		self.MAChome					= os.path.expanduser(u"~")
		self.userIndigoDir				= self.MAChome + "/indigo/"
		self.indigoPreferencesPluginDir = self.getInstallFolderPath+"Preferences/Plugins/"+self.pluginId+"/"
		self.indigoPluginDirOld			= self.userIndigoDir + self.pluginShortName+"/"
		self.PluginLogFile				= indigo.server.getLogsFolderPath(pluginId=self.pluginId) +"/plugin.log"


		formats=	{   logging.THREADDEBUG: "%(asctime)s %(msg)s",
						logging.DEBUG:       "%(asctime)s %(msg)s",
						logging.INFO:        "%(asctime)s %(msg)s",
						logging.WARNING:     "%(asctime)s %(msg)s",
						logging.ERROR:       "%(asctime)s.%(msecs)03d\t%(levelname)-12s\t%(name)s.%(funcName)-25s %(msg)s",
						logging.CRITICAL:    "%(asctime)s.%(msecs)03d\t%(levelname)-12s\t%(name)s.%(funcName)-25s %(msg)s" }

		date_Format = { logging.THREADDEBUG: "%d %H:%M:%S",
						logging.DEBUG:       "%d %H:%M:%S",
						logging.INFO:        "%H:%M:%S",
						logging.WARNING:     "%H:%M:%S",
						logging.ERROR:       "%Y-%m-%d %H:%M:%S",
						logging.CRITICAL:    "%Y-%m-%d %H:%M:%S" }
		formatter = LevelFormatter(fmt="%(msg)s", datefmt="%Y-%m-%d %H:%M:%S", level_fmts=formats, level_date=date_Format)

		self.plugin_file_handler.setFormatter(formatter)
		self.indiLOG = logging.getLogger("Plugin")  
		self.indiLOG.setLevel(logging.THREADDEBUG)

		self.indigo_log_handler.setLevel(logging.WARNING)
		indigo.server.log("initializing	 ... ")

		indigo.server.log(  u"path To files:          =================")
		indigo.server.log(  u"indigo                  {}".format(self.indigoRootPath))
		indigo.server.log(  u"installFolder           {}".format(self.indigoPath))
		indigo.server.log(  u"plugin.py               {}".format(self.pathToPlugin))
		indigo.server.log(  u"Plugin params           {}".format(self.indigoPreferencesPluginDir))

		if self.UDMPro == "True":
			indigo.server.log(  u"UDM Pro Detected")
		self.indiLOG.log( 0, "logger  enabled for     0 ==> TEST ONLY ")
		self.indiLOG.log( 5, "logger  enabled for     THREADDEBUG    ==> TEST ONLY ")
		self.indiLOG.log(10, "logger  enabled for     DEBUG          ==> TEST ONLY ")
		self.indiLOG.log(20, "logger  enabled for     INFO           ==> TEST ONLY ")
		self.indiLOG.log(30, "logger  enabled for     WARNING        ==> TEST ONLY ")
		self.indiLOG.log(40, "logger  enabled for     ERROR          ==> TEST ONLY ")
		self.indiLOG.log(50, "logger  enabled for     CRITICAL       ==> TEST ONLY ")
		indigo.server.log(  u"check                   {}  <<<<    for detailed logging".format(self.PluginLogFile))
		indigo.server.log(  u"Plugin short Name       {}".format(self.pluginShortName))
		indigo.server.log(  u"my PID                  {}".format(self.myPID))	 
		indigo.server.log(  u"set params for indigo V {}".format(self.indigoVersion))	 


		
####

	####-----------------			  ---------
	def __del__(self):
		indigo.PluginBase.__del__(self)

	###########################		INIT	## START ########################

	####----------------- @ startup set global parameters, create directories etc ---------
	def startup(self):
		if self.pathToPlugin.find("/"+self.pluginName+".indigoPlugin/")==-1:
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"The pluginname is not correct, please reinstall or rename")
				self.errorLog(u"It should be   /Libray/....../Plugins/"+self.pluginName+".indigPlugin")
				p=max(0,self.pathToPlugin.find("/Contents/Server"))
				self.errorLog(u"It is: "+self.pathToPlugin[:p])
				self.errorLog(u"please check your download folder, delete old *.indigoPlugin files or this will happen again during next update")
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.sleep(100000)
				self.quitNOW="wrong plugin name"
				return

		if not self.checkPluginPath(self.pluginName,  self.pathToPlugin):
			exit()

		if not self.moveToIndigoPrefsDir(self.indigoPluginDirOld, self.indigoPreferencesPluginDir):
			exit()

		self.pythonPath					= u"/usr/bin/python2.6"
		if os.path.isfile(u"/usr/bin/python2.7"):
			self.pythonPath				= u"/usr/bin/python2.7"


		self.checkcProfile()


		self.debugLevel = []
		for d in ["Logic","Log","Dict","LogDetails","DictDetails","Connection","Expect","Video","Fing","BC","Ping","all","Special"]:
			if self.pluginPrefs.get(u"debug"+d, False): self.debugLevel.append(d)


		self.logFile		 = ""
		self.logFileActive	 = self.pluginPrefs.get("logFileActive2", "standard")
		self.maxLogFileSize	 = 1*1024*1024
		self.lastCheckLogfile= time.time()
		self.setLogfile(unicode(self.pluginPrefs.get("logFileActive2", "standard")))


		self.varExcludeSQLList = ["Unifi_New_Device","Unifi_With_IPNumber_Change","Unifi_With_Status_Change"]

		self.expectCmdFile	= {	  "APtail": "execLog.exp",
					 "GWtail": "execLog.exp",
					 "SWtail": "execLog.exp",
					 "VDtail": "execLogVideo.exp",
					 "GWdict": "dictLoop.exp",
					 "SWdict": "dictLoop.exp",
					 "APdict": "dictLoop.exp",
					 "GWctrl": "simplecmd.exp",
					 "VDdict": "simplecmd.exp"}
		self.commandOnServer= {	  "APtail": "/usr/bin/tail -F /var/log/messages",
					 "GWtail": "/usr/bin/tail -F /var/log/messages",
					 "SWtail": "/usr/bin/tail -F /var/log/messages",
					 "VDtail": "/usr/bin/tail -F /var/lib/unifi-video/logs/motion.log",
					 "VDdict": "not implemented ",
					 "GWdict": "mca-dump | sed -e 's/^ *//'",
					 "SWdict": "mca-dump | sed -e 's/^ *//'",
					 "GWctrl": "mca-ctrl -t dump-cfg | sed -e 's/^ *//'",
					 "APdict": "mca-dump | sed -e 's/^ *//'"}
		self.promptOnServer = {	  "APtail": "BZ.v",
					 "GWtail": ":~",
					 "GWctrl": ":~",
					 "SWtail": "US.v",
					 "VDtail": "VirtualBox",
					 "VDdict": "VirtualBox",
					 "GWdict": ":~",
					 "SWdict": "US.v",
					 "APdict": "BZ.v"}
		self.startDictToken = {	  "APtail": "x",
					 "GWtail": "x",
					 "SWtail": "x",
					 "VDtail": "x",
					 "GWdict": "mca-dump | sed -e 's/^ *//'",
					 "SWdict": "mca-dump | sed -e 's/^ *//'",
					 "APdict": "mca-dump | sed -e 's/^ *//'"}
		self.endDictToken	= {	  "APtail": "x",
					 "GWtail": "x",
					 "VDtail": "x",
					 "GWdict": "xxxThisIsTheEndTokenxxx",
					 "SWdict": "xxxThisIsTheEndTokenxxx",
					 "APdict": "xxxThisIsTheEndTokenxxx"}
		self.numberOfPortsInSwitch=[8,10,18,26,52]

		self.promptOnServer["GWtail"]  = self.pluginPrefs.get(u"gwPrompt",u":~")
		self.promptOnServer["GWdict"]  = self.pluginPrefs.get(u"gwPrompt",u":~")
		self.promptOnServer["VDdict"]  = self.pluginPrefs.get(u"vdPrompt",u"VirtualBox")
		self.promptOnServer["VDtail"]  = self.pluginPrefs.get(u"vdPrompt",u"VirtualBox")

		self.commandOnServer["VDtail"]	= self.pluginPrefs.get(u"VDtailCommand",  self.commandOnServer["VDtail"])
		self.commandOnServer["VDdict"]	= self.pluginPrefs.get(u"VDdictCommand",  self.commandOnServer["VDdict"])

		self.commandOnServer["GWtail"]	= self.pluginPrefs.get(u"GWtailCommand",  self.commandOnServer["GWtail"])
		self.commandOnServer["GWdict"]	= self.pluginPrefs.get(u"GWdictCommand",  self.commandOnServer["GWdict"])

		self.commandOnServer["APtail"]	= self.pluginPrefs.get(u"APtailCommand",  self.commandOnServer["APtail"])
		self.commandOnServer["APdict"]	= self.pluginPrefs.get(u"APdictCommand",  self.commandOnServer["APdict"])

		self.commandOnServer["SWtail"]	= self.pluginPrefs.get(u"SWtailCommand",  self.commandOnServer["SWtail"])
		self.commandOnServer["SWdict"]	= self.pluginPrefs.get(u"SWdictCommand",  self.commandOnServer["SWdict"])

		self.vboxPath					= self.completePath(self.pluginPrefs.get(u"vboxPath",    "/Applications/VirtualBox.app/Contents/MacOS/"))
		self.changedImagePath			= self.completePath(self.pluginPrefs.get(u"changedImagePath", "/Users/karlwachs/indio/unifi/"))
		self.videoPath					= self.completePath(self.pluginPrefs.get(u"videoPath",    "/Volumes/data4TB/Users/karlwachs/video/"))
		self.unifiNVRSession			= ""
		self.nvrVIDEOapiKey				= self.pluginPrefs.get(u"nvrVIDEOapiKey","")


		self.vmMachine					= self.pluginPrefs.get(u"vmMachine",  "")
		self.vboxPath					= self.completePath(self.pluginPrefs.get(u"vboxPath",    "/Applications/VirtualBox.app/Contents/MacOS/"))
		self.vmDisk						= self.pluginPrefs.get(u"vmDisk",  "/Volumes/data4TB/Users/karlwachs/VirtualBox VMs/ubuntu/NewVirtualDisk1.vdi")
		self.changedImagePath			= self.completePath(self.pluginPrefs.get(u"changedImagePath", "/Users/karlwachs/indigo/unifi/"))
		self.mountPathVM				= self.pluginPrefs.get(u"mountPathVM", "/home/yourid/osx")
		self.videoPath					= self.completePath(self.pluginPrefs.get(u"videoPath",    "/Volumes/data4TB/Users/karlwachs/video/"))
		self.unifiNVRSession			= ""


		self.menuXML					= json.loads(self.pluginPrefs.get(u"menuXML", "{}"))
		self.pluginPrefs["menuXML"]		= json.dumps(self.menuXML)
		self.restartRequest				= {}

		self.blockAccess = []
		self.waitForMAC2vendor = False
		self.enableMACtoVENDORlookup	= int(self.pluginPrefs.get(u"enableMACtoVENDORlookup","21"))
		if self.enableMACtoVENDORlookup != "0":
			self.M2V = MAC2Vendor.MAP2Vendor(refreshFromIeeAfterDays = self.enableMACtoVENDORlookup )
			self.waitForMAC2vendor = self.M2V.makeFinalTable()


		self.updateDescriptions			= self.pluginPrefs.get(u"updateDescriptions", True)
		self.ignoreNeighborForFing		= self.pluginPrefs.get(u"ignoreNeighborForFing", True)
		self.useUNIFIdevices			= True
		self.ignoreNewNeighbors			= self.pluginPrefs.get(u"ignoreNewNeighbors", False)
		self.enableFINGSCAN				= self.pluginPrefs.get(u"enableFINGSCAN", False)
		self.sendUpdateToFingscanList	= {}
		self.enableBroadCastEvents		= self.pluginPrefs.get(u"enableBroadCastEvents", "0")
		self.sendBroadCastEventsList	= []
		self.unifiCloudKeySiteName		= self.pluginPrefs.get(u"unifiCloudKeySiteName", "default")
		self.unifiCloudKeyIP			= self.pluginPrefs.get(u"unifiCloudKeyIP", "")
		self.unifiCloudKeyPort			= self.pluginPrefs.get(u"unifiCloudKeyPort", "8443")
		self.unifiCloudKeyMode			= self.pluginPrefs.get(u"unifiCloudKeyMode", "ON")
		self.unifiCONTROLLERUserID		= self.pluginPrefs.get(u"unifiCONTROLLERUserID", "")
		self.unifiCONTROLLERPassWd		= self.pluginPrefs.get(u"unifiCONTROLLERPassWd", "")
		try: self.readBuffer			= int(self.pluginPrefs.get(u"readBuffer",32767))
		except: self.readBuffer			= 32767
		self.pluginPrefs[u"createUnifiDevicesCounter"] =	 int(self.pluginPrefs.get(u"createUnifiDevicesCounter",0))
		self.unifigetBlockedClientsDeltaTime		 = int(self.pluginPrefs.get(u"unifigetBlockedClientsDeltaTime",999999999))
		self.lastCheckForcheckForBlockedClients		= time.time()
		self.lastCheckForCAMERA			= 0
		self.saveCameraEventsLastCheck	= 0
		self.cameraEventWidth			= int(self.pluginPrefs.get(u"cameraEventWidth", "720"))
		self.imageSourceForEvent		= self.pluginPrefs.get(u"imageSourceForEvent", "noImage")
		self.imageSourceForSnapShot		= self.pluginPrefs.get(u"imageSourceForSnapShot", "noImage")

		self.listenStart				= {}
		self.unifiUserID				= self.pluginPrefs.get(u"unifiUserID", "")
		self.unifiPassWd				= self.pluginPrefs.get(u"unifiPassWd", "")
		self.unifiControllerSession		= ""
										
		self.unfiCurl					= self.pluginPrefs.get(u"unfiCurl", "/usr/bin/curl")
		if self.unfiCurl == "curl" or len(self.unfiCurl) < 4:
			self.unfiCurl = "/usr/bin/curl"
			self.pluginPrefs["unfiCurl"] = self.unfiCurl

		self.restartIfNoMessageSeconds	= int(self.pluginPrefs.get(u"restartIfNoMessageSeconds", 600))
		self.expirationTime				= int(self.pluginPrefs.get(u"expirationTime", 120) )
		self.expTimeMultiplier			= float(self.pluginPrefs.get(u"expTimeMultiplier", 2))

		self.loopSleep					= float(self.pluginPrefs.get(u"loopSleep", 4))
		self.timeoutDICT				= unicode(int(self.pluginPrefs.get(u"timeoutDICT", 10)))
		self.folderNameCreated			= self.pluginPrefs.get(u"folderNameCreated",   "UNIFI_created")
		self.folderNameNeighbors		= self.pluginPrefs.get(u"folderNameNeighbors", "UNIFI_neighbors")
		self.folderNameSystem			= self.pluginPrefs.get(u"folderNameSystem",	   "UNIFI_system")
		self.fixExpirationTime			= self.pluginPrefs.get(u"fixExpirationTime",	True)
		self.MACignorelist				= {}
		self.MACSpecialIgnorelist		= {}
		self.HANDOVER					= {}
		self.lastUnifiCookieCurl		= 0
		self.lastUnifiCookieRequests	= 0
		self.lastNVRCookie				= 0
		self.pendingCommand				= []
		self.groupStatusList			= {"Group"+str(i):{"members":{},"allHome":False,"allAway":False,"oneHome":False,"oneAway":False,"nHome":0,"nAway":0} for i in range(_GlobalConst_numberOfGroups )}
		self.groupStatusListALL			= {"nHome":0,"nAway":0,"anyChange":False}

		self.triggerList				= []
		self.statusChanged				= 0
		self.msgListenerActive			= {}


		self.updateStatesList			= {}
		self.logCount					= {}
		self.ipNumbersOfAPs				= ["" for nn in range(_GlobalConst_numberOfAP)]
		self.APsEnabled					= [False for nn in range(_GlobalConst_numberOfAP)]

		self.ipNumbersOfSWs				= ["" for nn in range(_GlobalConst_numberOfSW)]
		self.SWsEnabled					= [False for nn in range(_GlobalConst_numberOfSW)]

		self.devNeedsUpdate				= []

		self.MACloglist					= {}

		self.readDictEverySeconds={}
		self.readDictEverySeconds[u"AP"]= unicode(int(self.pluginPrefs.get(u"readDictEverySecondsAP", 120) ))
		self.readDictEverySeconds[u"GW"]= unicode(int(self.pluginPrefs.get(u"readDictEverySecondsGW", 120) ))
		self.readDictEverySeconds[u"SW"]= unicode(int(self.pluginPrefs.get(u"readDictEverySecondsSW", 120) ))
		self.devStateChangeList			= {}
		self.APUP						= {}
		self.SWUP						= {}
		self.GWUP						= {}
		self.VDUP						= {}

		self.version			 = self.getParamsFromFile(self.indigoPreferencesPluginDir+"dataVersion", default=0)


		#####  check AP parameters
		self.NumberOFActiveAP =0
		for i in range(_GlobalConst_numberOfAP):
			ip0 = self.pluginPrefs.get(u"ip"+unicode(i), "")
			ac	= self.pluginPrefs.get(u"ipON"+unicode(i), "")
			if not self.isValidIP(ip0): ac = False
			self.APUP[ip0]=time.time()
			self.ipNumbersOfAPs[i]=ip0
			if ac:
				self.APsEnabled[i]=True
				self.NumberOFActiveAP += 1

		#####  check switch parameters
		self.NumberOFActiveSW =0
		for i in range(_GlobalConst_numberOfSW):
			ip0 = self.pluginPrefs.get(u"ipSW" + unicode(i), "")
			ac = self.pluginPrefs.get(u"ipSWON" + unicode(i), "")
			if not self.isValidIP(ip0): ac = False
			self.SWUP[ip0] = time.time()
			self.ipNumbersOfSWs[i] = ip0
			if ac:
				self.SWsEnabled[i] = True
				self.NumberOFActiveSW += 1

		#####  check UGA parameters
		ip0 = self.pluginPrefs.get(u"ipUGA",  "")
		ac	= self.pluginPrefs.get(u"ipUGAON",False)

		if self.isValidIP(ip0) and ac:
			self.ipnumberOfUGA = ip0
			self.UGAEnabled = True
			self.GWUP[ip0] = time.time()
		else:
			self.ipnumberOfUGA = ""
			self.UGAEnabled = False

		#####  check video parameters
		self.nvrUNIXUserID				= self.pluginPrefs.get(u"nvrUNIXUserID", "")
		self.nvrUNIXPassWd				= self.pluginPrefs.get(u"nvrUNIXPassWd", "")
		self.nvrWebUserID				= self.pluginPrefs.get(u"nvrWebUserID", "")
		self.nvrWebPassWd				= self.pluginPrefs.get(u"nvrWebPassWd", "")
		self.enableVideoSwitch			= self.pluginPrefs.get(u"enableVideoSwitch", False)

		try:	self.unifiVIDEONumerOfEvents = int(self.pluginPrefs.get(u"unifiVIDEONumerOfEvents", 1000))
		except: self.unifiVIDEONumerOfEvents = 1000
		self.cameras						 = {}
		self.saveCameraEventsStatus			 = False

		ip0 = self.pluginPrefs.get(u"nvrIP", "192.168.1.x")

		self.VIDEOEnabled  = False
		self.ipnumberOfNVR = ""
		self.VIDEOEnabled = False
		self.VIDEOUP	  = 0
		if self.enableVideoSwitch:
			if self.isValidIP(ip0) and self.nvrUNIXUserID != "" and self.nvrUNIXPassWd != "":
				self.ipnumberOfNVR = ip0
				self.VIDEOEnabled = True
				self.VIDEOUP	  = time.time()

		self.lastCheckForNVR = 0

		self.getFolderId()

		self.readSuspend()

		self.stop = []
		self.stopCTRLC = False


		for ll in range(len(self.ipNumbersOfAPs)):
			self.killIfRunning(self.ipNumbersOfAPs[ll],u"")
		self.killIfRunning(self.ipnumberOfUGA, "")


		self.readDataStats()  # must come before other dev/states updates ...

		self.groupStatusINIT()
		self.setGroupStatus(init=True)
		self.readCamerasStats()
		self.readMACdata()
		self.checkDisplayStatus()

		self.pluginStartTime = time.time()+150


		self.checkforUnifiSystemDevicesState = "start"

		self.killIfRunning("", "")
		self.buttonConfirmGetAPDevInfoFromControllerCALLBACK()

		return


	####-----------------	 ---------
	def checkDisplayStatus(self):
		try:
			for dev in indigo.devices.iter(self.pluginId):
				if u"displayStatus" not in dev.states: continue

				if "MAC" in dev.states and dev.deviceTypeId == u"UniFi" and self.testIgnoreMAC(dev.states[u"MAC"]):
					if dev.states[u"displayStatus"].find(u"ignored") ==-1:
						dev.updateStateOnServer("displayStatus",self.padDisplay(u"ignored")+datetime.datetime.now().strftime(u"%m-%d %H:%M:%S"))
						if unicode(dev.displayStateImageSel) !="PowerOff":
							dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
				else:
					self.exeDisplayStatus(dev, dev.states["status"], force =False)


				old = dev.states[u"displayStatus"].split(u" ")
				if len(old) ==3:
					new = self.padDisplay(old[0].strip())+dev.states[u"lastStatusChange"][5:]
					if dev.states[u"displayStatus"] != new:
						dev.updateStateOnServer(u"displayStatus",new)
				else:
					dev.updateStateOnServer(u"displayStatus",self.padDisplay(old[0].strip())+dev.states[u"lastStatusChange"][5:])
		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


		return



	####-----------------	 ---------
	def isValidIP(self, ip0):
		ipx = ip0.split(u".")
		if len(ipx) != 4:
			return False
		else:
			for ip in ipx:
				try:
					if int(ip) < 0 or  int(ip) > 255: return False
				except:
					return False
		return True


####-------------------------------------------------------------------------####
	def getParamsFromFile(self,newName, oldName="", default ={}): # called from read config for various input files
			out = default
			if os.path.isfile(newName):
				try:
					f = open(newName, u"r")
					out	 = json.loads(f.read())
					f.close()
					if oldName !="" and os.path.isfile(oldName):
						os.system("rm "+oldName)
				except	Exception, e:
					self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					out ={}
			else:
				out = default
			if oldName !="" and os.path.isfile(oldName):
				try:
					f = open(oldName, u"r")
					out	 = json.loads(f.read())
					f.close()
					os.system("rm "+oldName)
				except	Exception, e:
					self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					out = default
			return out


####-------------------------------------------------------------------------####
	def writeJson(self, data, fName="", sort = True, doFormat=False ):
		try:

			if format:
				out = json.dumps(data, sort_keys=sort, indent=2)
			else:
				out = json.dumps(data, sort_keys=sort)

			if fName !="":
				f=open(fName,u"w")
				f.write(out)
				f.close()
			return out

		except	Exception, e:
			self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return ""



	####-----------------  update state lists ---------
	def deviceStartComm(self, dev):
		if self.decideMyLog(u"Logic"): self.indiLOG.log(20,u"starting device:  " + dev.name+"  "+unicode(dev.id)+"  "+dev.states[u"MAC"])

		if	self.pluginState == "init":
			dev.stateListOrDisplayStateIdChanged()

			if self.version < 2.0:
				props = dev.pluginProps
				self.indiLOG.log(20,u"Checking for deviceType Update: "+ dev.name )
				if "SupportsOnState" not in props:
					self.indiLOG.log(20," processing: "+ dev.name )
					dev = indigo.device.changeDeviceTypeId(dev, dev.deviceTypeId)
					dev.replaceOnServer()
					dev = indigo.devices[dev.id]
					props = dev.pluginProps
					props["SupportsSensorValue"] 		= False
					props["SupportsOnState"] 			= True
					props["AllowSensorValueChange"] 	= False
					props["AllowOnStateChange"] 		= False
					props["SupportsStatusRequest"] 		= False
					self.indiLOG.log(20,unicode(dev.pluginProps))
					dev.replacePluginPropsOnServer(props)
					dev= indigo.devices[dev.id]
					#self.myLog( text=unicode(dev.pluginProps))
					#self.myLog( text=unicode(dev.states))

					if (dev.states["status"].lower()).lower() in ["up","rec","ON"]:
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
					elif (dev.states["status"].lower()).find("down")==0:
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
					else:
						dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
					dev.replaceOnServer()
					#dev= indigo.devices[dev.id]
					dev.updateStateOnServer("onOffState",value= (dev.states["status"].lower()) in["up","rec","ON"], uiValue=dev.states["displayStatus"] )
					self.indiLOG.log(20,"SupportsOnState after replacePluginPropsOnServer")

			isType={"UniFi":"isUniFi","camera":"isCamera","gateway":"isGateway","Device-SW":"isSwitch","Device-AP":"isAP","neighbor":"isNeighbor","NVR":"isNVR"}
			props = dev.pluginProps
			devTid = dev.deviceTypeId
			##if dev.name.find("SW") > -1: self.myLog( text=u"deviceStartComm checking on "+dev.name+" "+devTid)
			for iT in isType:
				testId = devTid[0:min( len(iT),len(devTid) ) ]
				if iT == testId:
					##if dev.name.find("SW") > -1:	self.myLog( text= iT+ u" == "+testId+ " props"+ unicode(props))
					isT = isType[iT]
					if isT not in props or props[isT] != True:
						props[isT] = True
						dev.replacePluginPropsOnServer(props)
						##if dev.name.find("SW") > -1:	self.myLog( text= u" updateing")
					break

			if "enableBroadCastEvents" not in props:
				props = dev.pluginProps
				props["enableBroadCastEvents"] = "0"
				dev.replacePluginPropsOnServer(props)





		elif self.pluginState == "run":
			self.devNeedsUpdate.append(unicode(dev.id))

		return

	####-----------------	 ---------
	def deviceStopComm(self, dev):
		if	self.pluginState != "stop":
			self.devNeedsUpdate.append(unicode(dev.id))
			if self.decideMyLog(u"Logic"): self.indiLOG.log(20,u"stopping device:  " + dev.name+"  "+unicode(dev.id) )

	####-----------------	 ---------
	def didDeviceCommPropertyChange(self, origDev, newDev):
		#if origDev.pluginProps['xxx'] != newDev.pluginProps['address']:
		#	 return True
		return False
	###########################		INIT	## END	 ########################


	####-----------------	 ---------
	def getFolderId(self):

			self.folderNameIDCreated		= 0
			self.folderNameIDSystemID	   = 0
			try:
				self.folderNameIDCreated = indigo.devices.folders.getId(self.folderNameCreated)
			except:
				pass
			if self.folderNameIDCreated ==0:
				try:
					ff = indigo.devices.folder.create(self.folderNameCreated)
					self.folderNameIDCreated = ff.id
				except:
					self.folderNameIDCreated = 0

			try:
				self.folderNameIDSystemID = indigo.devices.folders.getId(self.folderNameSystem)
			except:
				pass
			if self.folderNameIDSystemID ==0:
				try:
					ff = indigo.devices.folder.create(self.folderNameSystem)
					self.folderNameIDSystemID = ff.id
				except:
					self.folderNameIDSystemID = 0

			try:
				self.folderNameIDNeighbors = indigo.devices.folders.getId(self.folderNameNeighbors)
			except:
				pass
			if self.folderNameIDNeighbors ==0:
				try:
					ff = indigo.devices.folder.create(self.folderNameNeighbors)
					self.folderNameIDNeighbors = ff.id
				except:
					self.folderNameIDNeighbors = 0


			return

	####-----------------	 ---------
	def validateDeviceConfigUi(self, valuesDict, typeId, devId):
		try:
			if self.decideMyLog(u"Logic"): self.indiLOG.log(20,u"Validate Device dict:" +unicode(valuesDict) )
			self.devNeedsUpdate.append(devId)

			dev = indigo.devices[int(devId)]
			if "groupMember" in dev.states:
				gMembers =""
				for group in  _GlobalConst_groupList:
					if group in valuesDict:
						if unicode(valuesDict[group]).lower() =="true":
							gMembers += group+","
							self.groupStatusList[group]["members"][unicode(devId)] = True
					elif unicode(devId) in	self.groupStatusList[group]["members"]: del self.groupStatusList[group]["members"][unicode(devId)]
				self.updateDevStateGroupMembers(dev,gMembers)
			return (True, valuesDict)
		except	Exception, e:
			self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		errorDict = valuesDict
		return (False, valuesDict, errorDict)


	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine returns the XML for the PluginConfig.xml by default; you probably don't
	# want to use this unless you have a need to customize the XML (again, uncommon)
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getPrefsConfigUiXml(self):
		return super(Plugin, self).getPrefsConfigUiXml()

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine returns the UI values for the configuration dialog; the default is to
	# simply return the self.pluginPrefs dictionary. It can be used to dynamically set
	# defaults at run time
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getPrefsConfigUiValues(self):
		return super(Plugin, self).getPrefsConfigUiValues()

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called once the user has exited the preferences dialog
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def closedPrefsConfigUi(self, valuesDict, userCancelled):
		# if the user saved his/her preferences, update our member variables now
		if userCancelled == False:
			pass
		return

	####-----------------  set the geneeral config parameters---------
	def validatePrefsConfigUi(self, valuesDict):


		rebootRequired								= ""
		self.lastUnifiCookieCurl					= 0
		self.lastUnifiCookieRequests				= 0

		self.lastNVRCookie							= 0
		self.checkforUnifiSystemDevicesState		= "validateConfig"
		self.enableFINGSCAN							= valuesDict[u"enableFINGSCAN"]
		self.enableBroadCastEvents					= valuesDict[u"enableBroadCastEvents"]
		self.sendBroadCastEventsList				= []
		self.ignoreNewNeighbors						= valuesDict[u"ignoreNewNeighbors"]
		self.loopSleep								= float(valuesDict[u"loopSleep"])
		self.unifiCONTROLLERUserID					= valuesDict[u"unifiCONTROLLERUserID"]
		self.unifiCONTROLLERPassWd					= valuesDict[u"unifiCONTROLLERPassWd"]
		try:	self.unifigetBlockedClientsDeltaTime =  int(valuesDict[u"unifigetBlockedClientsDeltaTime"])
		except: self.unifigetBlockedClientsDeltaTime = 999999999
		self.cameraEventWidth						= int(valuesDict[u"cameraEventWidth"])
		self.imageSourceForEvent					= valuesDict[u"imageSourceForEvent"]
		self.imageSourceForSnapShot					= valuesDict[u"imageSourceForSnapShot"]
		try: self.readBuffer						= int(valuesDict[u"readBuffer"])
		except: self.readBuffer						= 32767


		if self.unifiUserID	 != valuesDict[u"unifiUserID"]:				rebootRequired += " unifiUserID changed;"
		if self.unifiPassWd	 != valuesDict[u"unifiPassWd"]:				rebootRequired += " unifiPassWd changed;"

		self.unifiUserID							= valuesDict[u"unifiUserID"]
		self.unifiPassWd							= valuesDict[u"unifiPassWd"]
		self.unifiApiWebPage						= valuesDict[u"unifiApiWebPage"]
		self.unfiCurl								= valuesDict[u"unfiCurl"]
		self.unifiCloudKeyIP						= valuesDict[u"unifiCloudKeyIP"]
		self.unifiCloudKeyPort						= valuesDict[u"unifiCloudKeyPort"]
		self.unifiCloudKeyMode						= valuesDict[u"unifiCloudKeyMode"]
		self.unifiCloudKeySiteName					= valuesDict[u"unifiCloudKeySiteName"]
		self.ignoreNeighborForFing					= valuesDict[u"ignoreNeighborForFing"]
		self.updateDescriptions						= valuesDict[u"updateDescriptions"]
		self.folderNameCreated						= valuesDict[u"folderNameCreated"]
		self.folderNameNeighbors					= valuesDict[u"folderNameNeighbors"]
		self.folderNameSystem						= valuesDict[u"folderNameSystem"]
		self.getFolderId()
		if self.enableMACtoVENDORlookup != valuesDict[u"enableMACtoVENDORlookup"] and self.enableMACtoVENDORlookup == "0":
			rebootRequired							+= " MACVendor lookup changed; "
		self.enableMACtoVENDORlookup				= valuesDict[u"enableMACtoVENDORlookup"]


		xx											= unicode(int(valuesDict[u"timeoutDICT"]))
		if xx != self.timeoutDICT:
			rebootRequired	+= " timeoutDICT  changed; "
			self.timeoutDICT						= xx

		##
		self.debugLevel = []
		for d in ["Logic","Log","Dict","LogDetails","DictDetails","Connection","Expect","Video","Fing","BC","Ping","all","Special"]:
			if valuesDict[u"debug"+d]: self.debugLevel.append(d)
		self.setLogfile(unicode(valuesDict[u"logFileActive2"]))

		for TT in[u"AP",u"GW",u"SW"]:
			try:	xx			 = unicode(int(valuesDict[u"readDictEverySeconds"+TT]))
			except: xx			 = u"120"
			if xx != self.readDictEverySeconds[TT]:
				self.readDictEverySeconds[TT]				  = xx
				valuesDict[u"readDictEverySeconds"+TT]		  = xx
				rebootRequired	+= " readDictEverySeconds  changed; "


		try:	xx			 = int(valuesDict[u"restartIfNoMessageSeconds"])
		except: xx			 = 500
		if xx != self.restartIfNoMessageSeconds:
			self.restartIfNoMessageSeconds					 = xx
			valuesDict[u"restartIfNoMessageSeconds"]		 = xx

		try:	self.expirationTime					= int(valuesDict[u"expirationTime"])
		except: self.expirationTime					= 120
		valuesDict[u"expirationTime"]				= self.expirationTime
		try:	self.expTimeMultiplier				= int(valuesDict[u"expTimeMultiplier"])
		except: self.expTimeMultiplier				= 2.
		valuesDict[u"expTimeMultiplier"]			= self.expTimeMultiplier

		self.fixExpirationTime						= valuesDict[u"fixExpirationTime"]



		self.promptOnServer["GWtail"], rebootRequired		= self.getNewValusDictField("gwPrompt",		 valuesDict, self.promptOnServer["GWtail"], rebootRequired)
		self.promptOnServer["APtail"], rebootRequired		= self.getNewValusDictField("apPrompt",		 valuesDict, self.promptOnServer["APtail"], rebootRequired)
		self.promptOnServer["SWtail"], rebootRequired		= self.getNewValusDictField("swPrompt",		 valuesDict, self.promptOnServer["SWtail"], rebootRequired)
		self.promptOnServer["VDtail"], rebootRequired		= self.getNewValusDictField("vdPrompt",		 valuesDict, self.promptOnServer["VDtail"], rebootRequired)

		self.promptOnServer["GWdict"] = self.promptOnServer["GWtail"]
		self.promptOnServer["APdict"] = self.promptOnServer["APtail"]
		self.promptOnServer["SWdict"] = self.promptOnServer["SWtail"]
		self.promptOnServer["VDdict"] = self.promptOnServer["VDtail"]
		self.promptOnServer["GWctrl"] = self.promptOnServer["GWtail"]

		self.commandOnServer["GWtailCommand"], rebootRequired = self.getNewValusDictField("GWtailCommand", valuesDict, self.commandOnServer["GWtail"], rebootRequired)
		self.commandOnServer["GWdictCommand"], rebootRequired = self.getNewValusDictField("GWdictCommand", valuesDict, self.commandOnServer["GWdict"], rebootRequired)
		self.commandOnServer["SWtailCommand"], rebootRequired = self.getNewValusDictField("SWtailCommand", valuesDict, self.commandOnServer["SWtail"], rebootRequired)
		self.commandOnServer["SWdictCommand"], rebootRequired = self.getNewValusDictField("SWdictCommand", valuesDict, self.commandOnServer["SWdict"], rebootRequired)
		self.commandOnServer["APtailCommand"], rebootRequired = self.getNewValusDictField("APtailCommand", valuesDict, self.commandOnServer["APtail"], rebootRequired)
		self.commandOnServer["APdictCommand"], rebootRequired = self.getNewValusDictField("APdictCommand", valuesDict, self.commandOnServer["APdict"], rebootRequired)
		self.commandOnServer["VDtailCommand"], rebootRequired = self.getNewValusDictField("VDtailCommand", valuesDict, self.commandOnServer["VDtail"], rebootRequired)
		self.commandOnServer["VDdictCommand"], rebootRequired = self.getNewValusDictField("VDdictCommand", valuesDict, self.commandOnServer["VDdict"], rebootRequired)




		## AP parameters
		acNew = [False for i in range(_GlobalConst_numberOfAP)]
		ipNew = ["" for i in range(_GlobalConst_numberOfAP)]
		for i in range(_GlobalConst_numberOfAP):
			ip0 = valuesDict[u"ip"+unicode(i)]
			ac	= valuesDict[u"ipON"+unicode(i)]
			if not self.isValidIP(ip0): ac = False
			acNew[i]			 = ac
			ipNew[i]			 = ip0
			if ac: acNew[i] = True
			if acNew[i] != self.APsEnabled[i]:
				rebootRequired	+= " enable/disable AP changed; "
			if ipNew[i] != self.ipNumbersOfAPs[i]:
				rebootRequired	+= " Ap ipNumber  changed; "
				self.APUP[ipNew[i]] = time.time()
		self.ipNumbersOfAPs = copy.copy(ipNew)
		self.APsEnabled		= copy.copy(acNew)

		## SWitch parameters
		acNew = [False for i in range(_GlobalConst_numberOfSW)]
		ipNew = ["" for i in range(_GlobalConst_numberOfSW)]
		for i in range(_GlobalConst_numberOfSW):
			ip0 = valuesDict[u"ipSW"+unicode(i)]
			ac	= valuesDict[u"ipSWON"+unicode(i)]
			if not self.isValidIP(ip0): ac = False
			acNew[i]			 = ac
			ipNew[i]			 = ip0
			if ac: acNew[i] = True
			if acNew[i] != self.SWsEnabled[i]:
				rebootRequired	+= " enable/disable SW  changed; "
			if ipNew[i] != self.ipNumbersOfSWs[i]:
				rebootRequired	+= " SW ipNumber   changed; "
				self.SWUP[ipNew[i]] = time.time()
		self.ipNumbersOfSWs = copy.copy(ipNew)
		self.SWsEnabled		= copy.copy(acNew)



		## UGA parameters
		ip0			= valuesDict[u"ipUGA"]
		if self.ipnumberOfUGA != ip0:
			rebootRequired	+= " GW ipNumber   changed; "

		ac			= valuesDict[u"ipUGAON"]
		if not self.isValidIP(ip0): ac = False
		if self.UGAEnabled != ac:
			rebootRequired	+= " enable/disable GW  changed; "

		self.UGAEnabled	   = ac
		self.ipnumberOfUGA = ip0



		## video parameters
		if self.nvrUNIXUserID	 != valuesDict[u"nvrUNIXUserID"]:	  rebootRequired += " nvrUNIXUserID changed;"
		if self.nvrUNIXPassWd	 != valuesDict[u"nvrUNIXPassWd"]:	  rebootRequired += " nvrUNIXPassWd changed;"

		self.unifiVIDEONumerOfEvents	= int(valuesDict[u"unifiVIDEONumerOfEvents"])
		self.nvrUNIXUserID				= valuesDict[u"nvrUNIXUserID"]
		self.nvrUNIXPassWd				= valuesDict[u"nvrUNIXPassWd"]
		self.nvrWebUserID				= valuesDict[u"nvrWebUserID"]
		self.nvrWebPassWd				= valuesDict[u"nvrWebPassWd"]
		self.vmMachine					= valuesDict["vmMachine"]
		self.mountPathVM				= valuesDict[u"mountPathVM"]
		self.videoPath					= self.completePath(valuesDict[u"videoPath"])
		self.vboxPath					= self.completePath(valuesDict["vboxPath"])
		self.changedImagePath			= self.completePath(valuesDict[u"changedImagePath"])
		self.vmDisk						= valuesDict["vmDisk"]
		self.enableVideoSwitch			= valuesDict[u"enableVideoSwitch"]

		ip0			= valuesDict[u"nvrIP"]
		if self.ipnumberOfNVR != ip0:
			rebootRequired	+= " VIDEO ipNumber   changed; "


		ac = self.VIDEOEnabled
		if not self.isValidIP(ip0) or self.nvrUNIXUserID == "" or self.nvrUNIXPassWd == "" or (not self.enableVideoSwitch): ac = False
		if self.VIDEOEnabled != ac:
			rebootRequired	+= " enable/disable VIDEO changed; "

		self.VIDEOEnabled	= ac
		self.ipnumberOfNVR	= ip0

		if rebootRequired != "":
			self.indiLOG.log(30,u"restart " + rebootRequired)
			self.quitNow = u"config changed"
		return True, valuesDict




	####-----------------	 ---------
	def completePath(self,inPath):
		if len(inPath) == 0: return ""
		if inPath == " ":	 return ""
		if inPath[-1] !="/": inPath +="/"
		return inPath

	####-----------------	 ---------
	def getNewValusDictField(self,item,	 valuesDict, old, rebootRequired):
		xxx	   = valuesDict[item]
		if xxx != old:
			rebootRequired += " "+item+" changed"
		return	 xxx, rebootRequired

	####-----------------  config setting ----	END	   ----------#########

	####-----------------	 ---------
	def getCPU(self,pid):
		ret = subprocess.Popen("ps -ef | grep " + unicode(pid) + " | grep -v grep", stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()
		lines = ret[0].strip("\n").split("\n")
		for line in lines:
			if len(line) < 100: continue
			items = line.split()
			if items[1] != unicode(pid): continue
			if len(items) < 6: continue
			return (items[6])
		return ""

	####-----------------	 ---------
	def printConfigMenu(self,  valuesDict=None, typeId="", devId=0):
		try:
			self.myLog( text=u" ",mType=" ")
			self.myLog( text=u"UniFi   =============plugin config Parameters========",mType=" ")

			self.myLog( text=u"debugLevel".ljust(40)						+	unicode(self.debugLevel).ljust(3) )
			self.myLog( text=u"logFile".ljust(40)							+	unicode(self.logFile) )
			self.myLog( text=u"enableFINGSCAN".ljust(40)					+	unicode(self.enableFINGSCAN) )
			self.myLog( text=u"enableBroadCastEvents".ljust(40)				+	unicode(self.enableBroadCastEvents) )
			self.myLog( text=u"ignoreNeighborForFing".ljust(40)				+	unicode(self.ignoreNeighborForFing))
			self.myLog( text=u"expirationTime".ljust(40)					+	unicode(self.expirationTime).ljust(3)+u" [sec]" )
			self.myLog( text=u"sleep in main loop  ".ljust(40)				+	unicode(self.loopSleep).ljust(3)+u" [sec]" )
			self.myLog( text=u"use curl or request".ljust(40)				+	self.unfiCurl )
			self.myLog( text=u"cpu used since restart: ".ljust(40) 			+	self.getCPU(self.myPID) )
			self.myLog( text=u"" ,mType=" ")
			self.myLog( text=u"====== used in ssh userid@switch-IP, AP-IP, USG-IP to get DB dump and listen to events",mType=" " )
			self.myLog( text=u"UserID".ljust(40)							+	self.unifiUserID)
			self.myLog( text=u"PassWd".ljust(40)							+	self.unifiPassWd)
			self.myLog( text=u"read buffer size ".ljust(40)					+	unicode(self.readBuffer) )
			self.myLog( text=u"promptOnServer -GW dict".ljust(40)			+	self.promptOnServer["GWdict"] )
			self.myLog( text=u"promptOnServer -AP dict".ljust(40)			+	self.promptOnServer["APdict"] )
			self.myLog( text=u"promptOnServer -SW dict".ljust(40)			+	self.promptOnServer["SWdict"] )
			self.myLog( text=u"promptOnServer -GW ctrl".ljust(40)			+	self.promptOnServer["GWctrl"] )
			self.myLog( text=u"promptOnServer -AP tail".ljust(40)			+	self.promptOnServer["APtail"] )
			self.myLog( text=u"promptOnServer -GW tail".ljust(40)			+	self.promptOnServer["GWtail"] )
			self.myLog( text=u"promptOnServer -SW tail".ljust(40)			+	self.promptOnServer["SWtail"] )
			self.myLog( text=u"GW tailCommand".ljust(40)					+	self.commandOnServer["GWtail"] )
			self.myLog( text=u"GW dictCommand".ljust(40)					+	self.commandOnServer["GWdict"] )
			self.myLog( text=u"SW tailCommand".ljust(40)					+	self.commandOnServer["SWtail"] )
			self.myLog( text=u"SW dictCommand".ljust(40)					+	self.commandOnServer["SWdict"] )
			self.myLog( text=u"AP tailCommand".ljust(40)					+	self.commandOnServer["APtail"] )
			self.myLog( text=u"AP dictCommand".ljust(40)					+	self.commandOnServer["APdict"] )
			self.myLog( text=u"read DB Dict every".ljust(40)				+	unicode(self.readDictEverySeconds).replace("'","").replace("u","").replace(" ","")+u" [sec]" )
			self.myLog( text=u"restart listeners if NoMessage for".ljust(40)+unicode(self.restartIfNoMessageSeconds).ljust(3)+u"[sec]" )
			self.myLog( text=u"" ,mType=" ")
			self.myLog( text=u"====== CONTROLLER WEB ACCESS , set parameters and reporting",mType=" " )
			self.myLog( text=u"  curl data={WEB-UserID:..,WEB-PassWd:..} https://controllerIP: ..--------------",mType=" " )
			self.myLog( text=u"Mode: off, ON, reports only".ljust(40)		+	self.unifiCloudKeyMode )
			self.myLog( text=u"WEB-UserID".ljust(40)						+	self.unifiCONTROLLERUserID )
			self.myLog( text=u"WEB-PassWd".ljust(40)						+	self.unifiCONTROLLERPassWd )
			self.myLog( text=u"Controller port#".ljust(40)					+	self.unifiCloudKeyPort )
			self.myLog( text=u"Controller site Name#".ljust(40)				+	self.unifiCloudKeySiteName )
			self.myLog( text=u"Controller API WebPage".ljust(40)			+	self.unifiApiWebPage )
			self.myLog( text=u"get blocked client info from Cntr every".ljust(40) +	unicode(self.unifigetBlockedClientsDeltaTime)+"[sec]" )
			self.myLog( text=u"" ,mType=" ")
			self.myLog( text=u"====== VIDEO / camera NVR stuff ----------------------",mType=" " )
			self.myLog( text=u"=  get camera DB config and listen to recording event logs",mType=" " )
			self.myLog( text=u"  ssh NVR-UNIXUserID@NVR-IP ",mType=" ")
			self.myLog( text=u"NVR-VIDEO enabled".ljust(40)					+	unicode(self.VIDEOEnabled) )
			self.myLog( text=u"NVR-UNIXUserID".ljust(40)					+	self.nvrUNIXUserID )
			self.myLog( text=u"NVR-UNIXpasswd".ljust(40)					+	self.nvrUNIXPassWd )
			self.myLog( text=u"promptOnServer -VD dict".ljust(40)			+	self.promptOnServer["VDdict"] )
			self.myLog( text=u"promptOnServer -VD tail".ljust(40)			+	self.promptOnServer["VDtail"] )
			self.myLog( text=u"VD tailCommand".ljust(40)					+	self.commandOnServer["VDtail"] )
			self.myLog( text=u"VD dictCommand".ljust(40)					+	self.commandOnServer["VDdict"] )
			self.myLog( text=u"= getting snapshots and reading and changing parameters",mType=" " )
			self.myLog( text=u"  curl data={WEB-UserID:..,WEB-PassWd:..} https://NVR-IP#:  ....   for commands and read parameters ",mType=" " )
			self.myLog( text=u"  requests(http://IP-NVR:7080/api/2.0/snapshot/camera/**camApiKey**?force=true&width=1024&apiKey=nvrAPIkey,stream=True)  for snap shots",mType=" " )
			self.myLog( text=u"imageSourceForSnapShot".ljust(40)			+	self.imageSourceForSnapShot )
			self.myLog( text=u"imageSourceForEvent".ljust(40)				+	self.imageSourceForEvent )
			self.myLog( text=u"NVR-WEB-UserID".ljust(40)					+	self.nvrWebUserID )
			self.myLog( text=u"NVR-WEB-passWd".ljust(40)					+	self.nvrWebPassWd )
			self.myLog( text=u"NVR-API Key".ljust(40)						+	self.nvrVIDEOapiKey )
			self.myLog( text=u"",mType=" ")
			self.myLog( text=u"AP ip#			  enabled / disabled")
			for ll in range(len(self.ipNumbersOfAPs)):
				self.myLog( text=self.ipNumbersOfAPs[ll].ljust(20) 			+	unicode(self.APsEnabled[ll]) )


			self.myLog( text=u"SW ip#")
			for ll in range(len(self.ipNumbersOfSWs)):
				self.myLog( text=self.ipNumbersOfSWs[ll].ljust(20) 			+	unicode(self.SWsEnabled[ll]) )
			self.myLog( text=u"",mType=" ")
			self.myLog( text=self.ipnumberOfUGA.ljust(20) 					+	unicode(self.UGAEnabled)+"  USG/UGA  gateway/router " )

			self.myLog( text=self.unifiCloudKeyIP.ljust(20) 				+	u"      Controller / cloud Key IP#" )
			self.myLog( text=self.ipnumberOfNVR.ljust(20)					+	u"      Video NVR-IP#" )
			self.myLog( text=u"----------------------------------------------------",mType="  ")

			self.myLog( text=u"")

			self.myLog( text=u"UniFi    =============plugin config Parameters========  END ", mType=" " )
			self.myLog( text=u" ", mType=" ")

		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e) )

		return


	####-----------------	 ---------
	def printMACs(self,MAC=""):
		try:

			self.myLog( text=u"===== UNIFI device info =========",  mType="    " )
			for dev in indigo.devices.iter(self.pluginId):
				if dev.deviceTypeId == u"client":		  continue
				if MAC !="" and dev.states[u"MAC"] != MAC: continue
				self.myLog( text=dev.name+ u"  id: "+unicode(dev.id).ljust(12)+ u";	 type:"+ dev.deviceTypeId,	mType="device info")
				self.myLog( text=u"props:",	mType=u" ")
				props = dev.pluginProps
				for p in props:
					self.myLog( text=unicode(props[p]),	mType=p)

				self.myLog( text=u"states:",	 mType=u" ")
				for p in dev.states:
					self.myLog( text=unicode(dev.states[p]),	 mType=p)

			self.myLog( text=u"counters, timers etc:",  mType=u" ")
			if MAC in self.MAC2INDIGO[u"UN"]:
				self.myLog( text=unicode(self.MAC2INDIGO[u"UN"][MAC]), mType="UniFi")

			if MAC in self.MAC2INDIGO[u"AP"]:
				self.myLog( text=unicode(self.MAC2INDIGO[u"AP"][MAC]), mType="AP")

			if MAC in self.MAC2INDIGO[u"SW"]:
				self.myLog( text=unicode(self.MAC2INDIGO[u"SW"][MAC]), mType="SWITCH")

			if MAC in self.MAC2INDIGO[u"GW"]:
				self.myLog( text=unicode(self.MAC2INDIGO[u"GW"][MAC]), mType="GATEWAY")

			if MAC in self.MAC2INDIGO[u"NB"]:
				self.myLog( text=unicode(self.MAC2INDIGO[u"NB"][MAC]), mType="NEIGHBOR")


			self.myLog( text=u"===== UNIFI device info ========= END ",	mType="device info")

		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	####-----------------	 ---------
	def printALLMACs(self):
		try:

			self.myLog( text=u"===== UNIFI device info =========",  mType="")

			for dev in indigo.devices.iter(self.pluginId):
				if dev.deviceTypeId == u"client": continue
				self.myLog( text=u"id:      "+unicode(dev.id).ljust(12)+ u";     type:"+ dev.deviceTypeId, mType=dev.name)
				line=u"props: "
				props = dev.pluginProps
				for p in props:
					line+= unicode(p)+u":"+ unicode(props[p])+u";  "
				self.myLog( text=line,  mType=u" ")
				line=u"states: "
				for p in dev.states:
					line += unicode(p) + u":" + unicode(dev.states[p]) + u";  "
				self.myLog( text=line,  mType=u" ")

				self.myLog( text=u"temp data, counters, timer etc", mType=u" ")
			for dd in self.MAC2INDIGO[u"UN"]:
				self.myLog( text=unicode(self.MAC2INDIGO[u"UN"][dd]), mType="UNIFI    "+dd)
			for dd in self.MAC2INDIGO[u"AP"]:
				self.myLog( text=unicode(self.MAC2INDIGO[u"AP"][dd]), mType="AP        "+dd)
			for dd in self.MAC2INDIGO[u"SW"]:
				self.myLog( text=unicode(self.MAC2INDIGO[u"SW"][dd]), mType="SWITCH    "+dd)
			for dd in self.MAC2INDIGO[u"GW"]:
				self.myLog( text=unicode(self.MAC2INDIGO[u"GW"][dd]), mType="GATEWAY "+dd)
			for dd in self.MAC2INDIGO[u"NB"]:
				self.myLog( text=unicode(self.MAC2INDIGO[u"NB"][dd]), mType="NEIGHB    "+dd)

			self.myLog( text=u"===== UNIFI device info ========= END ", mType="")



		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


	####-----------------     ---------
	def printALLUNIFIsreduced(self):
		try:

			self.myLog( text=u"===== UniFi device info =========",  mType="")

			dType ="UniFi"
			line =u"                                 curr.;   exp;  use ping  ; use WOL;     use what 4;       WiFi;WiFi-max;    DHCP;  SW-UPtm; lastStatusChge;                              reason;     member of;"
			self.myLog( text=line,  mType=u" ")
			line =u"id:         MAC#             ;  status; time;    up;  down;   [sec];         Status;     Status;  idle-T; max-AGE;    chged;               ;                          for change;        groups;"
			lineI = []
			lineE = []
			lineD = []
			self.myLog( text=line,  mType=u"dev Name")
			for dev in indigo.devices.iter("props.isUniFi"):
				props = dev.pluginProps
				mac = dev.states[u"MAC"]
				if u"useWhatForStatus" in props and props[u"useWhatForStatus"] == u"WiFi": wf = True
				else:																	   wf = False

				if True:											line  = unicode(dev.id).ljust(12)+mac+"; "

				if mac in self.MACignorelist and self.MACignorelist[mac]:
																	line += ("IGNORED").rjust(7)+u"; "
				elif u"status" in dev.states:						line += (dev.states[u"status"]).rjust(7)+u"; "
				else:												line += ("-------").rjust(7)+u"; "

				if u"expirationTime" in props :						line += (unicode(props[u"expirationTime"]).split(".")[0]).rjust(4)+u"; "
				else:												line += " ".ljust(4)+"; "

				if u"usePingUP" in props :							line += (unicode(props[u"usePingUP"])).rjust(5)+u"; "
				else:												line += " ".ljust(5)+"; "

				if u"usePingDOWN" in props :						line += (unicode(props[u"usePingDOWN"])).rjust(5)+u"; "
				else:												line += " ".ljust(5)+"; "

				if u"useWOL" in props :
					if props[u"useWOL"] =="0":
																	line += ("no").ljust(7)+u"; "
					else:
																	line += (unicode(props[u"useWOL"])).rjust(7)+u"; "
				else:												line += "no".ljust(7)+"; "

				if u"useWhatForStatus" in props :					line += (unicode(props[u"useWhatForStatus"])).rjust(14)+u"; "
				else:												line += " ".ljust(14)+"; "

				if u"useWhatForStatusWiFi" in props and wf:			line += (unicode(props[u"useWhatForStatusWiFi"])).rjust(10)+u"; "
				else:												line += " ".ljust(10)+"; "

				if u"idleTimeMaxSecs" in props and wf:				line += (unicode(props[u"idleTimeMaxSecs"])).rjust(7)+u"; "
				else:												line += " ".ljust(7)+"; "

				if u"useAgeforStatusDHCP" in props and not wf:		line += (unicode(props[u"useAgeforStatusDHCP"])).rjust(7)+u"; "
				else:												line += " ".ljust(7)+"; "

				if u"useupTimeforStatusSWITCH" in props and not wf: line += (unicode(props[u"useupTimeforStatusSWITCH"])).rjust(8)+u"; "
				else:												line += " ".ljust(8)+"; "

				if u"lastStatusChange" in dev.states:				line += (unicode(dev.states[u"lastStatusChange"])[5:]).rjust(14)+u"; "
				else:												line += " ".ljust(14)+"; "
				if u"lastStatusChangeReason" in dev.states:			line += (unicode(dev.states[u"lastStatusChangeReason"])[0:35]).rjust(35)+u"; "
				else:												line += " ".ljust(35)+"; "

				if u"groupMember" in dev.states:			   line += (  (unicode(dev.states[u"groupMember"]).replace("Group","")).strip(",")	).rjust(13)+u"; "
				else:												line += " ".ljust(13)+"; "

				devName = dev.name
				if len(devName) > 25: devName = devName[:23]+".." # max len of 25 indicate cutoff if > 25 with ..
				if line.find("IGNORED;") >-1:
					lineI.append([line,devName])
				elif line.find("expired;") >-1:
					lineE.append([line,devName])
				elif line.find("down;") >-1:
					lineD.append([line,devName])
				else:
					self.myLog( text=line,  mType=devName)

			if lineD !=[]:
				for xx in lineD:
					self.myLog( text=xx[0], mType=xx[1])
			if lineE !=[]:
				for xx in lineE:
					self.myLog( text=xx[0], mType=xx[1])
			if lineI !=[]:
				for xx in lineI:
					self.myLog( text=xx[0], mType=xx[1])

			self.myLog( text=u"===== UniFi device info ========= END ", mType="")



		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	####-----------------  printGroups	  ---------
	def printGroups(self):
		try:

			self.myLog( text=u"-------MEMBERS ---------------", mType="GROUPS----- ")
			for group in _GlobalConst_groupList:
				xList = "\n            "
				lineNumber =0
				memberNames =[]
				for member in self.groupStatusList[group]["members"]:
					if len(member) <2: continue
					try:
						ID = int(member)
						dev = indigo.devices[ID]
					except: continue
					memberNames.append(dev.name)

				for member in sorted(memberNames):
					try:
						dev = indigo.devices[member]
						xList += (member+"/"+dev.states["status"][0].upper()).ljust(29)+", "
						if len(xList)/180  > lineNumber:
							lineNumber +=1
							xList +="\n            "
					except	Exception, e:
						if len(unicode(e)) > 5:
							self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				if	xList != "\n             ":
					gName = group
					homeaway =""
					try:
						gg =  indigo.variables["Unifi_Count_"+group+"_name"].value
						if gg.find("me to what YOU like") == -1:
							gName = group+"-"+gg
						homeaway += "    Home: " + indigo.variables["Unifi_Count_"+group+"_Home"].value
						homeaway += ";    away: " + indigo.variables["Unifi_Count_"+group+"_Away"].value
					except: pass
					self.myLog( text=u"members (/Up/Down/Expired/Ignored) "+homeaway+xList.strip(","), mType=gName)
			self.myLog( text=u"-------MEMBERS ----------------- END",mType="GROUPS----- ")

			self.myLog( text=u" ", mType=" ")

			xList = u"-------MEMBERS      ----------------\n          "
			lineNumber =0
			for member in sorted(self.MACignorelist):
				xList += member+", "
				if len(xList)/180  > lineNumber:
					lineNumber +=1
					xList +="\n            "
			self.myLog( text=xList.strip(","), mType="IGNORED ----- ")
			self.myLog( text=u"-------MEMBERS  -- -------------- END", mType="IGNORED ---")


		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



	####-----------------  data stats menu items	---------
	def buttonRestartVDListenerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		self.restartRequest["VDtail"] = "VD"
		return

	def buttonRestartGWListenerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		self.restartRequest["GWtail"] = "GW"
		self.restartRequest["GWdict"] = "GW"
		return


	def buttonRestartAPListenerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		self.restartRequest["APtail"] = valuesDict["pickAP"]
		self.restartRequest["APdict"] = valuesDict["pickAP"]
		return

	def buttonRestartSWListenerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		self.restartRequest["SWdict"] = valuesDict["pickSW"]
		return


	def buttonstopVideoServiceCALLBACKaction (self, valuesDict=None, filter="", typeId="", devId=""):
		self.execVideoAction(" \"service unifi-video stop\"")
		return
	def buttonstopVideoServiceCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		self.execVideoAction(" \"service unifi-video stop\"")
		return

	def buttonstartVideoServiceCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		self.execVideoAction(" \"service unifi-video start\"")
		return
	def buttonstartVideoServiceCALLBACKaction (self, valuesDict=None, filter="", typeId="", devId=""):
		self.execVideoAction(" \"service unifi-video start\"")
		return

	def buttonMountOSXDriveOnVboxCALLBACKaction(self, valuesDict=None, filter="", typeId="", devId=""):
		self.execVideoAction(" \"sudo mount -t vboxsf -o uid=unifi-video,gid=unifi-video video "+self.mountPathVM+"\"")
		return
	def buttonMountOSXDriveOnVboxCALLBACK(self, valuesDict=None, filter="", typeId="", devId="",returnCmd=False):
		return self.execVideoAction(" \"sudo mount -t vboxsf -o uid=unifi-video,gid=unifi-video video "+self.mountPathVM+"\"", returnCmd=returnCmd)

	def execVideoAction(self,cmdIN,returnCmd=False):
		uType = "VDdict"
		userid, passwd =  self.getUidPasswd(uType)
		if userid == "":
			self.indiLOG.log(20,"CameraInfo  Video Action : userid not set")
			return

		cmd = "/usr/bin/expect '" + \
			  self.pathToPlugin + "videoServerAction.exp' " + \
			" '"+userid + "' '"+passwd + "' " + \
			  self.ipnumberOfNVR + " " + \
			  self.promptOnServer[uType] + cmdIN
		if self.decideMyLog(u"Expect"):  self.indiLOG.log(20,"CameraInfo "+ cmd)

		if returnCmd: return cmd

		subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

		return


	####-----------------	 ---------
	####-----send commd parameters to cameras through VNR ------
	####-----------------	 ---------
	def buttonSendCommandToNVRLEDCALLBACKaction (self, action1=None, filter="", typeId="", devId=""):
		return self.buttonSendCommandToNVRLEDCALLBACK(valuesDict= action1.props)
	def buttonSendCommandToNVRLEDCALLBACK(self, valuesDict=None, filter="", typeId="", devId="",returnCmd=False):
		self.addToMenuXML(valuesDict)
		valuesDict["retCodeCam"],x =  self.setupNVRcmd(valuesDict["cameraDeviceSelected"],{"enableStatusLed":valuesDict["camLED"] == "1"})
		return valuesDict

	####-----------------	 ---------
	def buttonSendCommandToNVRSoundsCALLBACKaction (self, action1=None, filter="", typeId="", devId=""):
		return self.buttonSendCommandToNVRSoundsCALLBACK(valuesDict= action1.props)
	def buttonSendCommandToNVRSoundsCALLBACK(self, valuesDict=None, filter="", typeId="", devId="",returnCmd=False):
		self.addToMenuXML(valuesDict)
		valuesDict["retCodeCam"],x =  self.setupNVRcmd(valuesDict["cameraDeviceSelected"],{"systemSoundsEnabled":valuesDict["camSounds"] == "1"} )
		return valuesDict

	####-----------------	 ---------
	def buttonSendCommandToNVRenableSpeakerCALLBACKaction (self, action1=None, filter="", typeId="", devId=""):
		return self.buttonSendCommandToNVRenableSpeakerCALLBACK(valuesDict= action1.props)
	def buttonSendCommandToNVRenableSpeakerCALLBACK(self, valuesDict=None, filter="", typeId="", devId="",returnCmd=False):
		self.addToMenuXML(valuesDict)
		valuesDict["retCodeCam"],x =  self.setupNVRcmd(valuesDict["cameraDeviceSelected"],{"enableSpeaker":valuesDict["enableSpeaker"] == "1", "speakerVolume":int(valuesDict["enableSpeaker"])} )
		return valuesDict

	####-----------------	 ---------
	def buttonSendCommandToNVRmicVolumeCALLBACKaction (self, action1=None, filter="", typeId="", devId=""):
		return self.buttonSendCommandToNVRmicVolumeCALLBACK(valuesDict= action1.props)
	def buttonSendCommandToNVRmicVolumeCALLBACK(self, valuesDict=None, filter="", typeId="", devId="",returnCmd=False):
		self.addToMenuXML(valuesDict)
		valuesDict["retCodeCam"] = self.setupNVRcmd(valuesDict["cameraDeviceSelected"],{"micVolume":int(valuesDict["micVolume"])} )
		return valuesDict

	####-----------------	 ---------
	def buttonSendCommandToNVRRecordCALLBACKaction (self, action1=None, filter="", typeId="", devId=""):
		return self.buttonSendCommandToNVRRecordCALLBACK(valuesDict= action1.props)
	def buttonSendCommandToNVRRecordCALLBACK(self, valuesDict=None, filter="", typeId="", devId="",returnCmd=False):
		self.addToMenuXML(valuesDict)
		if valuesDict["postPaddingSecs"] =="-1" and valuesDict["prePaddingSecs"] =="-1":
			valuesDict["retCodeCam"],x =  self.setupNVRcmd(valuesDict["cameraDeviceSelected"],
					{"recordingSettings":{"motionRecordEnabled": valuesDict["motionRecordEnabled"] == "1","fullTimeRecordEnabled": valuesDict["fullTimeRecordEnabled"] == "1", 'channel': valuesDict["channel"]}
					} )
		elif valuesDict["postPaddingSecs"] !="-1" and valuesDict["prePaddingSecs"] !="-1":
			valuesDict["retCodeCam"],x =  self.setupNVRcmd(valuesDict["cameraDeviceSelected"],
					{"recordingSettings":{"motionRecordEnabled": valuesDict["motionRecordEnabled"] == "1","fullTimeRecordEnabled": valuesDict["fullTimeRecordEnabled"] == "1", 'channel': valuesDict["channel"],
					"postPaddingSecs": int(valuesDict["postPaddingSecs"]),
					"prePaddingSecs": int(valuesDict["prePaddingSecs"]) }
					} )
		elif valuesDict["postPaddingSecs"] !="-1":
			valuesDict["retCodeCam"],x =  self.setupNVRcmd(valuesDict["cameraDeviceSelected"],
					{"recordingSettings":{"motionRecordEnabled": valuesDict["motionRecordEnabled"] == "1","fullTimeRecordEnabled": valuesDict["fullTimeRecordEnabled"] == "1", 'channel': valuesDict["channel"],
					"postPaddingSecs": int(valuesDict["postPaddingSecs"]) }
					} )
		elif valuesDict["prePaddingSecs"] !="-1":
			valuesDict["retCodeCam"],x =  self.setupNVRcmd(valuesDict["cameraDeviceSelected"],
					{"recordingSettings":{"motionRecordEnabled": valuesDict["motionRecordEnabled"] == "1","fullTimeRecordEnabled": valuesDict["fullTimeRecordEnabled"] == "1", 'channel': valuesDict["channel"],
					"prePaddingSecs": int(valuesDict["prePaddingSecs"]) }
					} )
		else:
			valuesDict["retCodeCam"]="bad selection for recording"
		return valuesDict

	####-----------------	 ---------
	def buttonSendCommandToNVRIRCALLBACKaction (self, action1=None, filter="", typeId="", devId=""):
		return self.buttonSendCommandToNVRIRCALLBACK(valuesDict= action1.props)
	def buttonSendCommandToNVRIRCALLBACK(self, valuesDict=None, filter="", typeId="", devId="",returnCmd=False):
		self.addToMenuXML(valuesDict)
		xxx = valuesDict["irLedMode"]
		if xxx.find("auto") >-1:
			valuesDict["retCodeCam"],x =  self.setupNVRcmd(valuesDict["cameraDeviceSelected"],{"ispSettings":{"enableExternalIr": int(valuesDict["enableExternalIr"]),"irLedMode":"auto" }} )
		else:# for manual 0/100/255 level
			xxx = xxx.split("-")
			valuesDict["retCodeCam"],x =  self.setupNVRcmd(valuesDict["cameraDeviceSelected"],{"ispSettings":{"enableExternalIr": int(valuesDict["enableExternalIr"]),"irLedMode":xxx[0], "irLedLevel": int(xxx[1])}  } )
		return valuesDict
	####-----------------	 ---------
	def buttonSendCommandToNVRvideostreamingCALLBACKaction (self, action1=None, filter="", typeId="", devId=""):
		return self.buttonSendCommandToNVRIRCALLBACK(valuesDict= action1.props)
	def buttonSendCommandToNVRvideostreamingCALLBACK(self, valuesDict=None, filter="", typeId="", devId="",returnCmd=False):
		self.addToMenuXML(valuesDict)

		# first we need to get the current values
		error, ret = self.setupNVRcmd(valuesDict["cameraDeviceSelected"],"", cmdType="get")
		if "channels" not in ret[0] or len(ret[0]["channels"]) !=3 : # something went wrong
			self.indiLOG.log(40,"videostreaming error: "+error+ "     \n>>"+ unicode(ret)+"<<")
			valuesDict["retCodeCam"]=error
			return valuesDict

		# modify the required ones
		channels = ret[0]["channels"]
		channel	 = int(valuesDict["channelS"])
		channels[channel]["isRtmpEnabled"]	= valuesDict["isRtmpEnabled"]=="1"
		channels[channel]["isRtmpsEnabled"] = valuesDict["isRtmpsEnabled"]=="1"
		channels[channel]["isRtspEnabled"]	= valuesDict["isRtspEnabled"]=="1"
		# send back
		error, data=  self.setupNVRcmd(valuesDict["cameraDeviceSelected"], {"channels":channels}, cmdType="put")
		valuesDict["retCodeCam"]=error
		return valuesDict

	####-----------------	 ---------
	def buttonSendCommandToNVRgetSnapshotCALLBACKaction (self, action1=None, filter="", typeId="", devId=""):
		return self.buttonSendCommandToNVRgetSnapshotCALLBACK(valuesDict= action1.props)
	def buttonSendCommandToNVRgetSnapshotCALLBACK(self, valuesDict=None, filter="", typeId="", devId="",returnCmd=False):
		self.addToMenuXML(valuesDict)
		if   self.imageSourceForSnapShot == "imageFromNVR": 	valuesDict["retCodeCam"] = self.getSnapshotfromNVR(valuesDict["cameraDeviceSelected"], valuesDict["widthOfImage"], valuesDict["fileNameOfImage"] )
		elif self.imageSourceForSnapShot == "imageFromCamera":	valuesDict["retCodeCam"] = self.getSnapshotfromCamera(valuesDict["cameraDeviceSelected"],                          valuesDict["fileNameOfImage"] )
		return valuesDict

	####-----------------	 ---------
	def setupNVRcmd(self, devId, payload,cmdType="put"):

		dev = indigo.devices[int(devId)]
		try:
			if not self.isValidIP(self.ipnumberOfNVR): 		return "error IP",""
			if not self.VIDEOEnabled:					 	return "error enabled",""
			if not self.VIDEOEnabled:					 	return "error enabled",""
			if len(self.nvrVIDEOapiKey) < 5:				return "error apikey",""

			if payload !="":  payload['name']= dev.states["nameOnNVR"]
			ret = self.executeCMDonNVR(payload, dev.states["apiKey"],  cmdType=cmdType)
			self.fillCamerasIntoIndigo(ret, calledFrom="setupNVRcmd")
			return "ok",ret
		except	Exception, e:
			self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



	####-----------------	 ---------
	def executeCMDonNVR(self, data, cameraKey,	cmdType="put"):

		try:
			if cameraKey !="":
				url = "https://"+self.ipnumberOfNVR+ ":7443/api/2.0/camera/"+ cameraKey+ "?apiKey=" + self.nvrVIDEOapiKey

			else:
				url = "https://"+self.ipnumberOfNVR+ ":7443/api/2.0/camera/"+"?apiKey=" + self.nvrVIDEOapiKey

			if self.unfiCurl.find("curl") > -1:
				cmdL  = self.unfiCurl+" --insecure -c /tmp/nvrCookie -H \"Content-Type: application/json\" --data '"+json.dumps({"username":self.nvrWebUserID,"password":self.nvrWebPassWd})+"' 'https://"+self.unifiCloudKeyIP+":"+self.unifiCloudKeyPort+self.apiLoginPath+"'"
				if data =={} or data =="": dataDict = ""
				else:					   dataDict = " --data '"+json.dumps(data)+"' "
				if	 cmdType == "put":	  cmdTypeUse= " -X PUT "
				elif cmdType == "post":	  cmdTypeUse= " -X post "
				elif cmdType == "get":	  cmdTypeUse= "     "
				else:					  cmdTypeUse= " "
				cmdR = self.unfiCurl+" --insecure -b /tmp/nvrCookie  --header \"Content-Type: application/json\" "+cmdTypeUse +  dataDict + "'" +url+ "'"

				try:
					try:
						if time.time() - self.lastNVRCookie > 100: # re-login every 90 secs
							if self.decideMyLog(u"Video"): self.indiLOG.log(20,"Video cmd "+ cmdL )
							ret = subprocess.Popen(cmdL, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()
							if ret[1].find("error") >-1:
								self.indiLOG.log(40,u"error: (wrong UID/passwd, ip number?) ...>>"+ unicode(ret[0]) +"<<\n"+unicode(ret[1])+" Video error")
								return {}
							self.lastNVRCookie =time.time()
					except	Exception, e:
						self.indiLOG.log(40,"in Line {} has error={}    Video error".format(sys.exc_traceback.tb_lineno, e) )


					try:
						if self.decideMyLog(u"Video"): self.indiLOG.log(20,"Video " + cmdR )
						ret = subprocess.Popen(cmdR, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()
						try:
							jj = json.loads(ret[0])
						except :
							self.indiLOG.log(20,u"UNIFI Video error  executeCMDonNVR has error, no json object returned: " + unicode(ret))
							return []
						if "rc" in jj["meta"] and unicode(jj["meta"]["rc"]).find("error")>-1:
							self.indiLOG.log(40,u"error: data:>>"+ unicode(ret[0]) +"<<\n>>"+unicode(ret[1])+"<<\n" +" UNIFI Video error")
							return []
						elif self.decideMyLog(u"Video"):
							self.indiLOG.log(20,"UNIFI Video executeCMDonNV- camera Data:\n" +json.dumps(jj["data"], sort_keys=True, indent=2) )

						return jj["data"]
					except	Exception, e:
						self.indiLOG.log(40,"in Line {} has error={}  Video error".format(sys.exc_traceback.tb_lineno, e) )
				except	Exception, e:
					self.indiLOG.log(40,"in Line {} has error={}  Video error".format(sys.exc_traceback.tb_lineno, e))


			#############does not work on OSX  el capitan ssl lib too old  ##########
			elif self.unfiCurl =="requests":
				if self.unifiNVRSession =="" or (time.time() - self.lastNVRCookie) > 300:
					self.unifiNVRSession  = requests.Session()
					urlLogin  = "https://"+self.ipnumberOfNVR+":7443/api/login"
					dataLogin = json.dumps({"username":self.nvrWebUserID,"password":self.nvrWebPassWd})
					resp  = self.unifiNVRSession.post(urlLogin, data = dataLogin, verify=False)
					self.lastNVRCookie =time.time()
					#if self.decideMyLog(u"Video"): self.myLog( text="executeCMDonNVR  cmdType: post ;     urlLogin: "+urlLogin +";  dataLogin: "+ dataLogin+";  resp.text: "+ resp.text+"<<",mType="Video")


				if data =={}: dataDict = ""
				else:		  dataDict = json.dumps(data)

				if self.decideMyLog(u"Video"): self.indiLOG.log(20,"Video executeCMDonNVR  cmdType: "+cmdType+";  url: "+url +";  dataDict: "+ dataDict+"<<")
				try:
						if	 cmdType == "put":	 resp = self.unifiNVRSession.put(url,data  = dataDict, headers={'content-type': 'application/json'})
						elif cmdType == "post":	 resp = self.unifiNVRSession.post(url,data = dataDict, headers={'content-type': 'application/json'})
						elif cmdType == "get":	 resp = self.unifiNVRSession.get(url,data  = dataDict)
						else:					 resp = self.unifiNVRSession.get(url,data  = dataDict)
						jj = json.loads(resp.text)
						if "rc" in jj["meta"] and unicode(jj["meta"]["rc"]).find("error") >-1:
							self.indiLOG.log(40,u"executeCMDonNVR requests error: >>"+ unicode(resp.status_code) +"<<>>"+ unicode(resp.text) )
							return []
						elif self.decideMyLog(u"Video"):
							self.indiLOG.log(20, "Video executeCMDonNVR requests "+unicode(jj["data"]) )
						return jj["data"]
				except	Exception, e:
					self.indiLOG.log(40,"in Line {} has error={}\n resp.status_code >>{}<<  resp.text{}".format(sys.exc_traceback.tb_lineno, e, unicode(resp.status_code) , unicode(resp.text)) )


		except	Exception, e:
			self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return []



	####-----------------  VBOX ACTIONS	  ---------
	def execVboxAction(self,action,action2=""):
		testCMD = "ps -ef | grep '/vboxAction.py ' | grep -v grep"
		if len(subprocess.Popen( testCMD, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()[0]) > 10:
			try:   self.indiLOG.log(20,"CameraInfo VBOXAction: still runing, not executing: "+unicode(action)+"  "+ unicode(action2) )
			except:self.indiLOG.log(20,"CameraInfo VBOXAction: still runing, not executing: ")
			return False
		cmd = self.pythonPath + " \"" + self.pathToPlugin + "vboxAction.py\" '"+action+"'"
		if action2 !="":
			cmd += " '"+action2+"'"
		cmd +=" &"
		if self.decideMyLog(u"Video"): self.indiLOG.log(20,"CameraInfo  VBOXAction: "+cmd )
		subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		return

	####-----------------  Stop	   ---------
	def buttonVboxActionStopCALLBACKaction(self, action1=None, filter="", typeId="", devId=""):
		self.buttonVboxActionStopCALLBACK(valuesDict= action1.props)
	def buttonVboxActionStopCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		cmd = json.dumps({"action":["stop"], "vmMachine":self.vmMachine, "vboxPath":self.vboxPath, "logfile":self.logFile})
		if not self.execVboxAction(cmd): return
		ip = self.ipnumberOfNVR
		for dev in indigo.devices.iter("props.isUniFi"):
			if ip == dev.states["ipNumber"]:
				self.setSuspend(ip,time.time()+1000000000)
				break
		return


	####-----------------  Start	---------
	def buttonVboxActionStartCALLBACKaction(self, action1=None, filter="", typeId="", devId=""):
		self.buttonVboxActionStartCALLBACK(valuesDict= action1.props)
	def buttonVboxActionStartCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		cmd = {"action":["start","mountDisk"], "vmMachine":self.vmMachine, "vboxPath":self.vboxPath, "logfile":self.logFile,"vmDisk":self.vmDisk }
		mountCmd  = self.buttonMountOSXDriveOnVboxCALLBACK(returnCmd=True)
		self.execVboxAction(json.dumps(cmd),action2=json.dumps(mountCmd))
		return

	####-----------------  compress	   ---------
	def buttonVboxActionCompressCALLBACKaction(self, action1=None, filter="", typeId="", devId=""):
		self.buttonVboxActionCompressCALLBACK(valuesDict= action1.props)
	def buttonVboxActionCompressCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		cmd = {"action":["stop","compress","start","mountDisk"], "vmMachine":self.vmMachine, "vboxPath":self.vboxPath, "logfile":self.logFile,"vmDisk":self.vmDisk }
		mountCmd  = self.buttonMountOSXDriveOnVboxCALLBACK(returnCmd=True)
		if not self.execVboxAction(json.dumps(cmd),action2=json.dumps(mountCmd)): return
		ip = self.ipnumberOfNVR
		for dev in indigo.devices.iter("props.isUniFi"):
			if ip == dev.states["ipNumber"]:
				self.setSuspend(ip, time.time()+300.)
				break
		return

	####-----------------  backup	 ---------
	def buttonVboxActionBackupCALLBACKaction(self, action1=None, filter="", typeId="", devId=""):
		self.buttonVboxActionBackupCALLBACK(valuesDict= action1.props)
	def buttonVboxActionBackupCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		cmd = {"action":["stop","backup","start","mountDisk"], "vmMachine":self.vmMachine, "vboxPath":self.vboxPath, "logfile":self.logFile,"vmDisk":self.vmDisk }
		mountCmd  = self.buttonMountOSXDriveOnVboxCALLBACK(returnCmd=True)
		if not self.execVboxAction(json.dumps(cmd),action2=json.dumps(mountCmd)): return
		ip = self.ipnumberOfNVR
		for dev in indigo.devices.iter("props.isUniFi"):
			if ip == dev.states["ipNumber"]:
				self.setSuspend(ip, time.time()+220.)
				break
		return




	####-----------------  data stats menu items	---------
	def buttonPrintStatsCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		self.buttonPrintTcpipStats()
		self.printUpdateStats()


	####-----------------	 ---------
	def buttonPrintTcpipStats(self):

		if len(self.dataStats["tcpip"]) ==0: return
		nMin	= 0
		nSecs	= 0
		totByte = 0
		totMsg	= 0
		totErr	= 0
		totRes	= 0
		totAli	= 0
		out		= ""
		for uType in sorted(self.dataStats["tcpip"].keys()):
			for ipNumber in sorted(self.dataStats["tcpip"][uType].keys()):
				if nSecs ==0:
					self.myLog( text=u"=== data stats for received messages ====     collection started at "+ time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(self.dataStats["tcpip"][uType][ipNumber]["startTime"])), mType="data stats === START" )
					self.myLog( text=u"ipNumber            msgcount;    msgBytes;  errCount;   restarts;aliveCount;  msg/min; bytes/min;   err/min; aliveC/min", mType="dev type")
				nSecs = time.time() - self.dataStats["tcpip"][uType][ipNumber]["startTime"]
				nMin  = nSecs/60.
				out	 =ipNumber.ljust(18)
				out +="%10d"%(self.dataStats["tcpip"][uType][ipNumber]["inMessageCount"]) +";"
				out +="%12d"%(self.dataStats["tcpip"][uType][ipNumber]["inMessageBytes"]) +";"
				out +="%10d"%(self.dataStats["tcpip"][uType][ipNumber]["inErrorCount"]) +";"
				out +="%10d"%(self.dataStats["tcpip"][uType][ipNumber]["restarts"]) +";"
				out +="%10d"%(self.dataStats["tcpip"][uType][ipNumber]["aliveTestCount"]) +";"
				out +="%10.3f"%(self.dataStats["tcpip"][uType][ipNumber]["inMessageCount"]/nMin) +";"
				out +="%10.1f"%(self.dataStats["tcpip"][uType][ipNumber]["inMessageBytes"]/nMin) +";"
				out +="%10.7f"%(self.dataStats["tcpip"][uType][ipNumber]["inErrorCount"]/nMin) +";"
				out +="%10.3f"%(self.dataStats["tcpip"][uType][ipNumber]["aliveTestCount"]/nMin) +";"
				totByte += self.dataStats["tcpip"][uType][ipNumber]["inMessageBytes"]
				totMsg	+= self.dataStats["tcpip"][uType][ipNumber]["inMessageCount"]
				totErr	+= self.dataStats["tcpip"][uType][ipNumber]["inErrorCount"]
				totRes	+= self.dataStats["tcpip"][uType][ipNumber]["restarts"]
				totAli	+= self.dataStats["tcpip"][uType][ipNumber]["aliveTestCount"]

				self.myLog( text=out, mType="  "+uType+"-"+self.dataStats["tcpip"][uType][ipNumber]["APN"])
		self.myLog( text=u"total                "+ "%10d"%totMsg+";%12d"%totByte+";%10d"%totErr+ ";%10d"%totRes+u";%10d"%totAli+ ";%10.3f"%(totMsg/nMin) + ";%10.1f"%(totByte/nMin)+ ";%10.7f"%(totErr/nMin)+ ";%10.3f"%(totAli/nMin)+";", mType="T O T A L S")
		self.myLog( text=u"===  total time measured: %d "%(nSecs/(24*60*60)) +time.strftime("%H:%M:%S", time.gmtime(nSecs)), mType="data stats === END" )


	####-----------------	 ---------
	def printUpdateStats(self):
		if len(self.dataStats["updates"]) ==0: return
		nSecs = max(1,(time.time()-	 self.dataStats["updates"]["startTime"]))
		nMin  = nSecs/60.
		self.myLog( text=u" ", mType=" " )
		self.myLog( text=u"===  measuring started at: " +time.strftime("%H:%M:%S",time.localtime(self.dataStats["updates"]["startTime"])), mType="indigo update stats === " )
		self.myLog( text=u"updates: %10d"%self.dataStats["updates"]["devs"]	+";     updates/sec: %10.2f"%(self.dataStats["updates"]["devs"]  /nSecs)+";  updates/minute: %10.2f"%(self.dataStats["updates"]["devs"]  /nMin),  mType="     device ")
		self.myLog( text=u"updates: %10d"%self.dataStats["updates"]["states"]+";     updates/sec: %10.2f"%(self.dataStats["updates"]["states"]/nSecs)+";  updates/minute: %10.2f"%(self.dataStats["updates"]["states"]/nMin),  mType="     states ")
		self.myLog( text=u"===  total time measured: %d "%(nSecs/(24*60*60)) +time.strftime(" %H:%M:%S", time.gmtime(nSecs)),  mType="indigo update stats === END" )
		return


	####-----------------	 ---------
	def addToMenuXML(self, valuesDict):
		if valuesDict:
			for item in valuesDict:
				self.menuXML[item] = copy.copy(valuesDict[item])
			self.pluginPrefs["menuXML"]	 = json.dumps(self.menuXML)
		return

	####-----------------	 ---------
	def buttonprintCameraEventsCALLBACK(self,valuesDict, typeId="", devId=""):
		maxEvents= int(valuesDict["maxEvents"])
		totEvents= 0
		for MAC in self.cameras:
			totEvents += len(self.cameras[MAC]["events"])

		self.addToMenuXML(valuesDict)

		out = "\n======= Camera Events ======"
		out += "\nDev MAC             dev.id        Name "
		out += "\n           Ev#    start                   end        dur[secs]\n"
		for MAC in self.cameras:
			out += MAC+" %11d"%self.cameras[MAC]["devid"]+" "+self.cameras[MAC]["cameraName"].ljust(25)+"  # events total: "+str(len(self.cameras[MAC]["events"]))+"\n"
			evList=[]
			for evNo in self.cameras[MAC]["events"]:
				dateStart = time.strftime(u"%Y-%m-%d %H:%M:%S",time.localtime(self.cameras[MAC]["events"][evNo]["start"]))
				dateStop  = time.strftime(u" .. %H:%M:%S",time.localtime(self.cameras[MAC]["events"][evNo]["stop"]))
				delta  = self.cameras[MAC]["events"][evNo]["stop"]
				delta -= self.cameras[MAC]["events"][evNo]["start"]
				evList.append("     "+ str(evNo).rjust(10)+"  "+dateStart+dateStop+"  %8.1f"%delta+"\n")
			evList= sorted(evList, reverse=True)
			count =0
			for o in evList:
				count+=1
				if count > maxEvents: break
				out += o
		out += "====== Camera Events ======;                         all # events total: " +str(totEvents) +"\n"

		self.myLog( text=out, mType=" " )
		return

	####-----------------	 ---------
	def buttonresetCameraEventsCALLBACK(self,valuesDict, typeId="", devId=""):
		for dev in indigo.devices.iter("props.isCamera"):
			dev.updateStateOnServer("eventNumber",0)
			self.indiLOG.log(20,"reset event number for "+dev.name)
		self.resetCamerasStats()
		self.addToMenuXML(valuesDict)
		return
	####-----------------	 ---------


	####-----------------	 ---------
	def buttonPrintCameraSystemCALLBACK(self,valuesDict, typeId="", devId=""):
		self.pendingCommand.append("getCamerasFromNVR-print")

	####-----------------	 ---------
	def buttonrefreshCameraSystemCALLBACK(self,valuesDict, typeId="", devId=""):
		self.pendingCommand.append("getConfigFromNVR")



	####-----------------	 ---------
	def getCamerasFromNVR(self,doPrint = False, action=[]):
		try:
			timeElapsed = time.time()
			info	= {"users":{}, "cameras":[],"NVR":{}}
			USERs	= []
			ACCOUNTs= []
			cmdstr	= ["\"mongo 127.0.0.1:7441/av --quiet --eval  'db.", ".find().forEach(printjsononeline)'  | sed 's/^\s*//' \"" ]

			#self.myLog( text=" into getCamerasFromNVR "+unicode(action))
			if "system" in action:
				USERs			= self.getMongoData(cmdstr[0]+"user"   +cmdstr[1])
				ACCOUNTs		= self.getMongoData(cmdstr[0]+"account"+cmdstr[1])

				if len(USERs)>0 and len(ACCOUNTs) >0:
					for account in ACCOUNTs:
						##self.myLog( text="getCamerasFromNVR account dict: "+unicode(account))
						if "_id" in account and "username" in account and "name" in account:
							ID =  account["_id"]
							info["users"][ID] ={"userName":account["username"], "name":account["name"]}
							for user in USERs:
								##self.myLog( text="getCamerasFromNVR user dict: "+unicode(user))
								if "accountId" in user and ID == user["accountId"]:
									##self.myLog( text="getCamerasFromNVR accountId ok and id found:"+ID)
									if "apiKey" in user and "enableApiAccess" in user:
										##self.myLog( text="getCamerasFromNVR apiKey found <<"+ user["apiKey"]+"<<    enableApiAccess>>"+unicode(user["enableApiAccess"]))
										info["users"][ID]["apiKey"]			 = user["apiKey"]
										info["users"][ID]["enableApiAccess"] = user["enableApiAccess"]
									else:
										if "enableApiAccess" in user and user["enableApiAccess"]: # its enabled, but no api key
											self.indiLOG.log(40,"getCamerasFromNVR camera users   bad enableApiAccess / apiKey info for id:"+ str(ID)+"\n"+ unicode(USERs)+ " UNIFI error")
										else:
											if self.decideMyLog(u"Video"): self.indiLOG.log(20,"UNIFI error  getCamerasFromNVR camera users   enableApiAccess disabled info for id:"+ str(ID)+"\n"+ unicode(USERs))
						else:
										self.indiLOG.log(40,"getCamerasFromNVR camera ACCOUNT bad _id / username / name info:\n"+ unicode(ACCOUNTs))

				server = self.getMongoData(cmdstr[0]+"server" +cmdstr[1])
				if len(server) >0:
					info["NVR"]		= server[0]

			if "cameras" in action:
				info["cameras"]	 = self.executeCMDonNVR( {}, "",  cmdType="get")
				if len(info["cameras"]) <1:
					info["cameras"] = self.getMongoData(cmdstr[0]+"camera" +cmdstr[1])
				if len(info["cameras"]) >0: self.fillCamerasIntoIndigo(info["cameras"], calledFrom="getCamerasFromNVR")


			##self.myLog( text=unicode(info))

			if doPrint:
				self.printCameras(info)
			return info


		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return {}

	####-----------------	 ---------
	def printCameras(self, info):
		keepList = ["name","uuid","host","model","_id","firmwareVersion","systemInfo","mac","controllerHostAddress","controllerHostPort","deviceSettings","networkStatus","status","analyticsSettings","channels","ispSettings" ]
		out =""
		try:
			if "NVR" in info:
				self.myLog( text="--====================++++++++++++++++++++++++++++++++++++++++====================--",mType="System info-NVR:")
				for key in info["NVR"]:
					self.myLog( text=unicode(info["NVR"][key]),mType="  "+key )

				self.myLog( text="---====================++++++++++++++++++++++++++++++++++++++++====================--", mType="== System info- users:")
			if "users" in info:
				nn = 0
				for user in info["users"]:
					out = ""
					for item in ["name","apiKey","enableApiAccess"] :
						out+=(item+":"+str(info["users"][user][item])+"; ").ljust(30)
					self.myLog( text=out.strip("; "),mType= (info["users"][user]["userName"]).ljust(18)+" # "+ str(nn))
					nn+=1


			if "cameras" in info:
				self.myLog( text="---====================++++++++++++++++++++++++++++++++++++++++====================--", mType="== System info- cameras:")
				for camera in info["cameras"]:
					self.myLog( text="--===============--" , mType=camera["name"])
					for item in camera:
						if item =="name": continue
						if item in keepList or keepList == ["*"]:
							if item == "channels":
								nn = 0
								for channel in camera[item]:
									out = ("bitrates: "+str(channel["minBitrate"])+".."+str(channel["maxBitrate"])) .ljust(30)
									for	 prop in ["enabled","isRtmpsEnabled","isRtspEnabled"]:
										if prop in channel:
											out+= prop+": "+str(channel[prop])+";  "
									out = out.strip(";....")
									self.myLog( text=out, mType="              channel#"+str(nn) )
									nn+=1
							elif item == "status":
								status = camera[item]
								out = ""
								for	 prop in ["remotePort","remoteHost"]:
									if prop in status:
										out+= prop+":"+str(status[prop])+"; "
								out = out.strip("; ")
								self.myLog( text=out, mType="              status" )
								for nn in range(len(status["recordingStatus"])):
									out	 =	("motionRecordingEnabled: "+str(status["recordingStatus"][str(nn)]["motionRecordingEnabled"])).ljust(30)
									out += "; fullTimeRecordingEnabled: "+str(status["recordingStatus"][str(nn)]["fullTimeRecordingEnabled"])
									self.myLog( text=out, mType="           recordingSt:#"+str(nn) )
							else:
								self.myLog( text=(item+":").ljust(25)+json.dumps(camera[item]) )

		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}\n printCameras camera system info:\n{}".format(sys.exc_traceback.tb_lineno, e, json.dumps(out,sort_keys=True, indent=2)) )
		return

	####-----------------	 ---------
	def getMongoData(self, cmdstr, uType="VDdict"):
		ret =["",""]
		try:
			userid, passwd =  self.getUidPasswd(uType)
			if userid == "": return {}

			cmd = "/usr/bin/expect	'" + \
				  self.pathToPlugin + self.expectCmdFile[uType] + "' " + \
				  "'"+userid + "' '"+passwd + "' " + \
				  self.ipnumberOfNVR + " " + \
				  self.promptOnServer[uType] + " " + \
				  " XXXXsepXXXXX " + \
				  cmdstr
			if self.decideMyLog(u"Expect"): self.indiLOG.log(20,"UNIFI getMongoData cmd " +cmd )
			ret = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()
			dbJson, error= self.makeJson(ret[0], "XXXXsepXXXXX")
			if self.decideMyLog(u"Video"): self.indiLOG.log(20,"UNIFI getMongoData return"+ ret[0]+"\n"+ret[1] )
			if error !="":
				self.indiLOG.log(40,"getMongoData camera system (dump, no json conversion)	info:\n>>"+error+"    " + cmd+"<<\n>>"+unicode(ret[0]) )
				return []
			return	dbJson
		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				if self.decideMyLog(u"Video"): self.indiLOG.log(40,ret[0]+"\n"+ret[1] +"   getMongoData error")
		return []

	####-----------------	 ---------
	def makeJson(self, dumpIN, sep):  ## {} separated by \n
		try:
			out =[]
			temp = "empty"
			temp2 = "empty"
			begStr,endStr ="{","}"
			dump		 = dumpIN.split(sep)
			lDump = len(dump)
			if lDump <3: return "","error len(split):"+str(lDump)
			if lDump >3:
				dump = dump[lDump-3:]
			dump  = dump[1].strip("\n").strip("\r")
			s1 = dump.find(begStr)
			dump = dump[s1:]
			s2 = dump.rfind(endStr)
			dump = dump[:s2+1].strip("\n").strip("\r")
			dumpSplit = dump.split("\n")
			for line in dumpSplit:
				if len(line) < 5: continue
				nnn1   = line.find(begStr)
				temp   = line[nnn1:]
				nnn2   = temp.rfind(endStr)
				temp   = temp[0:nnn2+1]
				temp2	= self.replaceFunc(temp).strip()
				if len(temp2) >2:
					try:
						o =json.loads(temp2)
						out.append(o)
					except:
						self.indiLOG.log(40,"makeJson error , trying to fix:\ntemp2>>>>>"+ unicode(temp2)+"<<<<<\n>>>>"+unicode(dumpIN)+"<<<<<" )
						try:
							o=json.loads(temp2+"}")
							out.append(o)
							self.indiLOG.log(40,"makeJson error fixed " )
						except	Exception, e:
							self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

			return out, ""
		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,"makeJson error :\ndump>>>>"+unicode(dumpIN)+"<<<<<" )
		return dump, "error"
	####-----------------	 ---------
	def makeJson2(self, dump, sep):
		try:
			out={}
			begStr,endStr ="{","}"
			dump		 = dump.split(sep)
			if len(dump) !=3: return ""
			dump  = dump[1].replace("\n","").replace("\r","")
			s1 = dump.find(begStr)
			dump = dump[s1:]
			s2 = dump.rfind(endStr)
			out=json.loads(dump[:s2+1])
			return out, ""
		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}\nmakeJson2 error :\n>>>>>{}<<<<<".format(sys.exc_traceback.tb_lineno, e, unicode(dump) ) )
		return dump, "error"

	####-----------------	 ---------
	def replaceFunc(self, dump):
		try:
			for ii in range(500):  # remove binData(xxxxx)
				nn = dump.find("BinData(")
				if nn ==-1: break
				endst = dump[nn:].find(")")
				dump = dump[0:nn-1]+'"xxx"'+ dump[nn+endst+1:]

			for kk in range(1000):	# loop over func Names, max 30
				ss = 0
				for ll in range(100): # remove " (xxx) from targest only abc(xx)
					nn = dump[ss:].find("(")
					if nn ==-1: break
					if dump[ss+nn-1] != " ":
						nn+=ss
						break
					ss = nn+1


				if nn ==-1: break
				startSt= dump[0:nn].rfind(" ")
				replString= dump[startSt+1:nn+1]
				lenrepString = len(replString)
				for ii in range(100):  # loop of all occurance of func replacements
					nn = dump.find(replString)
					if nn == -1: break
					pp = dump[nn:].find(")")
					dump = dump[0:nn] + dump[nn+lenrepString:nn+pp] + dump[nn+pp+1:]
			return dump
		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return ""

	####-----------------	 ---------
	def buttonZeroStatsCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		self.zeroDataStats()
		return
	####-----------------	 ---------
	def buttonResetStatsCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		self.resetDataStats(calledFrom="buttonResetStatsCALLBACK")
		return

	####-----------------  reboot unifi device	 ---------

	####-----------------	 ---------
	def filterUnifiDevices(self, filter="", valuesDict=None, typeId="", devId=""):
		xlist = []
		for ll in range(_GlobalConst_numberOfAP):
			if self.APsEnabled[ll]:
				xlist.append((self.ipNumbersOfAPs[ll]+"-APdict","AP -"+self.ipNumbersOfAPs[ll]))
		for ll in range(_GlobalConst_numberOfSW):
			if self.SWsEnabled[ll]:
				xlist.append((self.ipNumbersOfSWs[ll]+"-SWtail","SW -"+self.ipNumbersOfSWs[ll]))
		if self.UGAEnabled:
				xlist.append((self.ipnumberOfUGA+"-GWtail","GW -"+self.ipnumberOfUGA))
		return xlist

	####-----------------	 ---------
	def buttonConfirmrebootCALLBACKaction(self, action1=None, filter="", typeId="", devId=""):
		return self.buttonConfirmrebootCALLBACK(valuesDict=action1.props)

	####-----------------	 ---------
	def buttonConfirmrebootCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		ip_type	 =	valuesDict["rebootUNIFIdeviceSelected"].split("-")
		ipNumber = ip_type[0]
		dtype	 = ip_type[1]
		cmd = "/usr/bin/expect "
		cmd+= "'"+self.pathToPlugin + "rebootUNIFIdeviceAP.exp" + "' "
		cmd+= "'"+self.unifiUserID + "' '"+self.unifiPassWd + "' "
		cmd+= ipNumber + " "
		cmd+= self.promptOnServer[dtype] + " &"
		if self.decideMyLog(u"Expect"): self.indiLOG.log(20,"REBOOT: "+cmd )
		ret = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()
		if self.decideMyLog(u"Connection"): self.indiLOG.log(20,"REBOOT: "+unicode(ret) )
		self.addToMenuXML(valuesDict)

		return


	####-----------------  set properties for all devices	---------
	def buttonConfirmSetWifiOptCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		for MAC in self.MAC2INDIGO["UN"]:
			try:
				dev = indigo.devices[self.MAC2INDIGO["UN"][MAC]["devId"]]
				props = dev.pluginProps
				self.indiLOG.log(20,u"doing "+ dev.name)
				if props["useWhatForStatus"] == "WiFi":
					props["useWhatForStatusWiFi"]	= "Optimized"
					props[u"idleTimeMaxSecs"]		= u"30"
					dev.replacePluginPropsOnServer(props)

					dev = indigo.devices[self.MAC2INDIGO["UN"][MAC]["devId"]]
					props = dev.pluginProps
					self.indiLOG.log(20,u"done "+ dev.name+" "+ unicode(props))
			except	Exception, e:
					self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		self.printALLUNIFIsreduced()
		return
	####-----------------	 ---------
	def buttonConfirmSetWifiIdleCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		for MAC in self.MAC2INDIGO["UN"]:
			try:
				dev = indigo.devices[self.MAC2INDIGO["UN"][MAC]["devId"]]
				props = dev.pluginProps
				if props["useWhatForStatus"] == "WiFi":
					props["useWhatForStatusWiFi"]	= "IdleTime"
					props[u"idleTimeMaxSecs"]		= u"30"
					dev.replacePluginPropsOnServer(props)
			except:
				pass
		self.printALLUNIFIsreduced()
		return
	####-----------------	 ---------
	def buttonConfirmSetWifiUptimeCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		for MAC in self.MAC2INDIGO["UN"]:
			try:
				dev = indigo.devices[self.MAC2INDIGO["UN"][MAC]["devId"]]
				props = dev.pluginProps
				if props["useWhatForStatus"] == "WiFi":
					props["useWhatForStatusWiFi"]	= "UpTime"
					dev.replacePluginPropsOnServer(props)
			except:
				pass
		self.printALLUNIFIsreduced()
		return
	####-----------------	 ---------
	def buttonConfirmSetNonWifiOptCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		for MAC in self.MAC2INDIGO["UN"]:
			try:
				dev = indigo.devices[self.MAC2INDIGO["UN"][MAC]["devId"]]
				props = dev.pluginProps
				if props["useWhatForStatus"] != "WiFi":
					props["useWhatForStatus"]			= "OptDhcpSwitch"
					props[u"useAgeforStatusDHCP"]		= u"60"
					props[u"useupTimeforStatusSWITCH"]	= True
					dev.replacePluginPropsOnServer(props)
			except:
				pass
		self.printALLUNIFIsreduced()
		return
	####-----------------	 ---------
	def buttonConfirmSetNonWifiToSwitchCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		for MAC in self.MAC2INDIGO["UN"]:
			try:
				dev = indigo.devices[self.MAC2INDIGO["UN"][MAC]["devId"]]
				props = dev.pluginProps
				if props["useWhatForStatus"] != "WiFi":
					props["useWhatForStatus"]			= "SWITCH"
					props[u"useupTimeforStatusSWITCH"]	= True
					dev.replacePluginPropsOnServer(props)
			except:
				pass
		self.printALLUNIFIsreduced()
		return
	def buttonConfirmSetNonWifiToDHCPCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		for MAC in self.MAC2INDIGO["UN"]:
			try:
				dev = indigo.devices[self.MAC2INDIGO["UN"][MAC]["devId"]]
				props = dev.pluginProps
				if props["useWhatForStatus"] != "WiFi":
					props["useWhatForStatus"]			= "DHCP"
					props[u"useAgeforStatusDHCP"]		= u"60"
					dev.replacePluginPropsOnServer(props)
			except:
				pass
		self.printALLUNIFIsreduced()
		return
	####-----------------	 ---------
	def buttonConfirmSetUsePingUPonCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		for MAC in self.MAC2INDIGO["UN"]:
			try:
				dev = indigo.devices[self.MAC2INDIGO["UN"][MAC]["devId"]]
				props = dev.pluginProps
				props["usePingUP"]			 = True
				dev.replacePluginPropsOnServer(props)
			except:
				pass
		self.printALLUNIFIsreduced()
		return
	####-----------------	 ---------
	def buttonConfirmSetUsePingUPoffCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		for MAC in self.MAC2INDIGO["UN"]:
			try:
				dev = indigo.devices[self.MAC2INDIGO["UN"][MAC]["devId"]]
				props = dev.pluginProps
				props["usePingUP"]			 = False
				dev.replacePluginPropsOnServer(props)
			except:
				pass
		self.printALLUNIFIsreduced()
		return
	####-----------------	 ---------
	def buttonConfirmSetUsePingDOWNonCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		for MAC in self.MAC2INDIGO["UN"]:
			try:
				dev = indigo.devices[self.MAC2INDIGO["UN"][MAC]["devId"]]
				props = dev.pluginProps
				props["usePingDOWN"]		   = True
				dev.replacePluginPropsOnServer(props)
			except:
				pass
		self.printALLUNIFIsreduced()
		return
	####-----------------	 ---------
	def buttonConfirmSetUsePingDOWNoffCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		for MAC in self.MAC2INDIGO["UN"]:
			try:
				dev = indigo.devices[self.MAC2INDIGO["UN"][MAC]["devId"]]
				props = dev.pluginProps
				props["usePingDOWN"]		   = False
				dev.replacePluginPropsOnServer(props)
			except:
				pass
		self.printALLUNIFIsreduced()
		return
	####-----------------	 ---------
	def buttonConfirmSetExpTimeCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		for MAC in self.MAC2INDIGO["UN"]:
			try:
				dev = indigo.devices[self.MAC2INDIGO["UN"][MAC]["devId"]]
				props = dev.pluginProps
				props["expirationTime"]			  =int(valuesDict["expirationTime"])
				dev.replacePluginPropsOnServer(props)
			except:
				pass
		self.printALLUNIFIsreduced()
		return

	####-----------------	 ---------
	def buttonConfirmSetExpTimeMinCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		for MAC in self.MAC2INDIGO["UN"]:
			try:
				dev = indigo.devices[self.MAC2INDIGO["UN"][MAC]["devId"]]
				props = dev.pluginProps
				try:
					if int(props["expirationTime"]) < int(valuesDict["expirationTime"]):
						props["expirationTime"]		  =int(valuesDict["expirationTime"])
				except:
					props["expirationTime"]			  =int(valuesDict["expirationTime"])
				dev.replacePluginPropsOnServer(props)
			except:
				pass
		self.printALLUNIFIsreduced()
		return


	####-----------------	 ---------
	def inpDummy(self, valuesDict=None, filter="", typeId="", devId=""):
		return valuesDict

	####-----------------  filter specific MAC number	---------


	####-----------------	 ---------
	def filterWiFiDevice(self, filter="", valuesDict=None, typeId="", devId=""):

		xList = []
		for dev in indigo.devices.iter("props.isUniFi"):
			if "AP" not	 in dev.states:		  continue
			if len(dev.states["AP"]) < 5:	  continue
			xList.append([dev.states["MAC"].lower(),dev.name+"--"+ dev.states["MAC"] +"-- AP:"+dev.states["AP"]])
		return sorted(xList, key=lambda x: x[1])

	####-----------------	 ---------
	def filterUNIFIsystemDevice(self, filter="", valuesDict=None, typeId="", devId=""):

		xList = []
		for dev in indigo.devices.iter("props.isSwitch,props.isGateway,props.isAP"):
			xList.append([dev.states["MAC"].lower(),dev.name+"--"+ dev.states["MAC"] ])
		return sorted(xList, key=lambda x: x[1])
	####-----------------	 ---------
	def filterCameraDevice(self, filter="", valuesDict=None, typeId="", devId=""):

		xList = []
		for dev in indigo.devices.iter("props.isCamera"):
			xList.append([dev.id,dev.name])
		return sorted(xList, key=lambda x: x[1])


	####-----------------	 ---------
	def filterUNIFIsystemDeviceSuspend(self, filter="", valuesDict=None, typeId="", devId=""):

		xList = []
		for dev in indigo.devices.iter("props.isSwitch,props.isGateway,props.isAP"):
			xList.append([dev.id,dev.name])
		return sorted(xList, key=lambda x: x[1])

	####-----------------	 ---------
	def filterUNIFIsystemDeviceSuspended(self, filter="", valuesDict=None, typeId="", devId=""):

		xList = []
		for dev in indigo.devices.iter("props.isSwitch,props.isGateway,props.isAP"):
			xList.append([dev.id,dev.name])
		return sorted(xList, key=lambda x: x[1])

	####-----------------	 ---------
	def filterAPdevices(self, filter="", valuesDict=None, typeId="", devId=""):

		xList = []
		for dev in indigo.devices.iter("props.isAP"):
			xList.append([dev.id,dev.name])
		return sorted(xList, key=lambda x: x[1])



	####-----------------	 ---------
	def filterMACNoIgnored(self, filter="", valuesDict=None, typeId="", devId=""):
		xlist = []
		for dev in indigo.devices.iter(self.pluginId):
			if u"MAC" in dev.states:
				if "displayStatus" in dev.states and   dev.states["displayStatus"].find("ignored") >-1: continue
				xlist.append([dev.states[u"MAC"],dev.states[u"MAC"] + " - "+dev.name])
		return sorted(xlist, key=lambda x: x[1])

	####-----------------	 ---------
	def filterMAC(self, filter="", valuesDict=None, typeId="", devId=""):
		xlist = []
		for dev in indigo.devices.iter(self.pluginId):
			if u"MAC" in dev.states:
				xlist.append([dev.states[u"MAC"],dev.states[u"MAC"] + " - "+dev.name])
		return sorted(xlist, key=lambda x: x[1])

	####-----------------	 ---------
	def filterMACunifiOnly(self, filter="", valuesDict=None, typeId="", devId=""):
		xlist = []
		for dev in indigo.devices.iter("props.isUniFi"):
			if u"MAC" in dev.states:
				xlist.append([dev.states[u"MAC"],dev.name+u"--"+dev.states[u"MAC"] ])
		return sorted(xlist, key=lambda x: x[1])

	####-----------------	 ---------
	def filterMACunifiAndCameraOnly(self, filter="", valuesDict=None, typeId="", devId=""):
		xlist = []
		maclist =[]
		for dev in indigo.devices.iter("props.isUniFi"):
			if u"MAC" in dev.states:
				if dev.deviceTypeId not in [u"UniFi"] : continue
				if u"status" in dev.states and dev.states[u"status"].find(u"up") >-1:
					xlist.append([dev.states[u"MAC"],dev.name+u"--"+dev.states[u"MAC"] ])
					maclist.append(dev.states[u"MAC"])
		for dev in indigo.devices.iter("props.isCamera"):
			if u"MAC" in dev.states:
				if dev.deviceTypeId not in [u"camera"] : continue
				if dev.states[u"MAC"] in maclist: continue
				xlist.append([dev.states[u"MAC"],dev.name+u"--"+dev.states[u"MAC"] ])
		return sorted(xlist, key=lambda x: x[1])

	####-----------------	 ---------
	def filterMACunifiOnlyUP(self, filter="", valuesDict=None, typeId="", devId=""):
		xlist = []
		for dev in indigo.devices.iter("props.isUniFi"):
			if u"MAC" in dev.states:
				if u"status" in dev.states and dev.states[u"status"].find(u"up") >-1:
					xlist.append([dev.states[u"MAC"],dev.name+u"--"+dev.states[u"MAC"] ])
		return sorted(xlist, key=lambda x: x[1])

	####-----------------	 ---------
	def filterMAConlyAP(self, filter="", valuesDict=None, typeId="", devId=""):
		xlist = []
		for dev in indigo.devices.iter("props.isAP"):
			if u"MAC" in dev.states:
				if u"status" in dev.states and dev.states[u"status"].find(u"up") >-1:
					xlist.append([dev.states[u"MAC"],dev.name+u"--"+dev.states[u"MAC"] ])
		return sorted(xlist, key=lambda x: x[1])


	####-----------------	 ---------
	def filterMACunifiIgnored(self, filter="", valuesDict=None, typeId="", devId=""):
		xlist = []
		for MAC in self.MACignorelist:
				textMAC = MAC
				for dev in indigo.devices.iter("props.isUniFi,props.isCamera"):
					if "MAC" in dev.states and MAC == dev.states["MAC"]:
						textMAC = dev.name+" - "+MAC
						break
				xlist.append([MAC,textMAC])
		return sorted(xlist, key=lambda x: x[1])

	####-----------------  logging for specific MAC number	 ---------
	####-----------------	 ---------
	def filterMACspecialUNIgnore(self, filter="", valuesDict=None, typeId="", devId=""):
		xlist = []
		for MAC in self.MACSpecialIgnorelist:
			xlist.append([MAC,MAC])
		return sorted(xlist, key=lambda x: x[1])

	####-----------------  logging for specific MAC number	 ---------



	####-----------------	 ---------
	def buttonConfirmStartLoggingCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		self.MACloglist[valuesDict[u"MACdeviceSelected"]]=True
		self.indiLOG.log(20,u"start track-logging for MAC# "+valuesDict[u"MACdeviceSelected"])
		return
	####-----------------	 ---------
	def buttonConfirmStopLoggingCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		self.MACloglist={}
		self.indiLOG.log(20,u" stop logging ")
		return

	####-----------------  device info	 ---------
	def buttonConfirmPrintMACCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		self.printMACs(MAC=valuesDict[u"MACdeviceSelected"])
		return
	####-----------------	 ---------
	def buttonprintALLMACsCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		self.printALLMACs()
		return
	####-----------------	 ---------
	def printALLUNIFIsreducedMenue(self, valuesDict=None, filter="", typeId="", devId=""):
		self.printALLUNIFIsreduced()
		return
	####-----------------	 ---------




	####-----------------  GROUPS START	   ---------
	####-----------------	 ---------

	def printGroupsCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		self.printGroups()
		return


	####-----------------  add devices to groups  menu	 ---------
	def buttonConfirmAddDevGroupCALLBACK(self, valuesDict=None, typeId="", devId=0):
		try:
			newGroup =	valuesDict["addRemoveGroupsWhichGroup"]
			devtypes =	valuesDict["addRemoveGroupsWhichDevice"]
			types	 =""; lanWifi=""
			if	 devtypes == "system":	 types ="props.isGateway,props.isSwitch,props.isAP"
			elif devtypes == "neighbor": types ="props.isNeighbor"
			elif devtypes == "LAN":		 types ="props.isUniFi" ; lanWifi ="LAN"
			elif devtypes == "wifi":	 types ="props.isUniFi" ; lanWifi ="wifi"
			if types !="":
				for dev in indigo.devices.iter(types):
					if lanWifi == "wifi" and "AP" in dev.states:
						if ( dev.states["AP"] =="" or
							 dev.states["signalWiFi"]	  =="" ): continue
					if lanWifi == "LAN" and "AP" in dev.states:
						if not	( dev.states["AP"] =="" or
								  dev.states["signalWiFi"]	   =="" ): continue
					props = dev.pluginProps
					props[newGroup] = True
					dev.replacePluginPropsOnServer(props)
					gMembers = self.makeGroupMemberstring(props)
					dev = indigo.devices[dev.id]
					self.updateDevStateGroupMembers(dev,gMembers)
				self.statusChanged = 2

		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return valuesDict

	####-----------------	  ---------
	def updateDevStateGroupMembers(self,dev,gMembers):
		if dev.states["groupMember"] != gMembers:
			dev.updateStateOnServer("groupMember",gMembers)
		return

	####-----------------	  ---------
	def	 makeGroupMemberstring(self,inputDict):
		gMembers=""
		for group in _GlobalConst_groupList:
			if group in inputDict and unicode(inputDict[group]).lower() =="true" :
				gMembers+=group+u","
		return gMembers.strip(",")



	####-----------------  remove devices to groups	 menu	---------
	def buttonConfirmRemDevGroupCALLBACK(self, valuesDict=None, typeId="", devId=0):
		try:
			self.indiLOG.log(20,u" valuesDict "+unicode(_GlobalConst_groupList)+"  "+ unicode(valuesDict))
			newGroup =	valuesDict["addRemoveGroupsWhichGroup"]
			devtypes =	valuesDict["addRemoveGroupsWhichDevice"]
			types	 =""; lanWifi=""
			if	 devtypes == "system":	 types =",props.isGateway,props.isSwitch,props.isAP"
			elif devtypes == "neighbor": types =",props.isNeighbor"
			elif devtypes == "LAN":		 types =",props.isUniFi" ; lanWifi ="LAN"
			elif devtypes == "wifi":	 types =",props.isUniFi" ; lanWifi ="wifi"
			for dev in indigo.devices.iter(self.pluginId+types):
				if lanWifi == "wifi" and "AP" in dev.states:
					if ( dev.states["AP"] =="" or
						 dev.states["signalWiFi"]	  =="" ): continue
				if lanWifi == "LAN" and "AP" in dev.states:
					if not	( dev.states["AP"] =="" or
							  dev.states["signalWiFi"]	   =="" ): continue

				props = dev.pluginProps
				if newGroup in props:
					del props[newGroup]
				dev.replacePluginPropsOnServer(props)
				gMembers = self.makeGroupMemberstring(props)
				self.updateDevStateGroupMembers(dev,gMembers)

			self.statusChanged = 2
		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return valuesDict


	####-----------------	 ---------
	def filterGroupNoName(self, valuesDict=None, filter="", typeId="", devId=""):
		xList=[]
		for ii in range(_GlobalConst_numberOfGroups):
			memberMAC = ""
			group = str(ii)
			gName = group
			try:
				gg =  indigo.variables["Unifi_Count_Group"+group+"_name"].value
				if gg.find("me to what YOU like") == -1:
					gName= group+"-"+gg
			except: pass
			xList.append(["Group"+group, gName])
		return xList
	####-----------------	 ---------
	def filterGroups(self, valuesDict=None, filter="", typeId="", devId=""):

		xList=[]
		for ii in range(_GlobalConst_numberOfGroups):
			members = self.groupStatusList["Group"+str(ii)]["members"]
			#self.myLog( text="members: "+unicode(members))
			gName = str(ii)
			#try:
			gg =  indigo.variables["Unifi_Count_Group"+gName+"_name"].value
			if gg.find("me to what YOU like") == -1:
				gName += "-"+gg[0:20]
			#except: pass
			memberMAC = ""
			nn = 0
			for id in members:
				nn +=1
				if nn > 6:
					memberMAC +="..."
				try:
					dev = indigo.devices[int(id)]
					MAC = dev.states["MAC"]
				except	Exception, e:
					self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					continue
				memberMAC += dev.name[0:10]+";"
			xList.append([str(ii), gName+"=="+ memberMAC.strip("; ")])
		#self.myLog( text=unicode(xList))
		return xList

	####-----------------	 ---------
	def buttonConfirmgroupCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		self.selectedGroup		  = valuesDict["selectedGroup"]
		return valuesDict

	####-----------------	 ---------
	def filterGroupMembers(self, valuesDict=None, filter="", typeId="", devId=""):
		xList=[]
		try: sg = int(self.selectedGroup)
		except: return xList
		for mm in self.groupStatusList["Group"+str(sg)]["members"]:
			#self.myLog( text=unicode(mm))
			try:
				dev = indigo.devices[int(mm)]
			except: continue
			xList.append([mm,dev.name + "- "+ dev.states["MAC"]])
		#self.myLog( text="group members: "+unicode(xList))
		return xList

	####-----------------	 ---------
	def buttonConfirmremoveGroupMemberCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		mm	= valuesDict["selectedGroupMemberIndigoIdremove"]
		gpN = "Group"+str(self.selectedGroup)
		try:
			dev = indigo.devices[int(mm)]
		except:
			self.indiLOG.log(30," bad dev id: "+str(mm) )
			return
		props = dev.pluginProps
		if mm in self.groupStatusList[gpN]["members"]:
			del self.groupStatusList[gpN]["members"][mm]
		if gpN in props and props[gpN]:
			props[gpN] = False
			dev.replacePluginPropsOnServer(props)
			gMembers = self.makeGroupMemberstring(props)
			self.updateDevStateGroupMembers(dev,gMembers)
		return valuesDict


	####-----------------	 ---------
	def buttonConfirmremoveALLGroupMembersCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		gpN = "Group"+str(self.selectedGroup)
		self.groupStatusList[gpN]["members"] ={}
		for dev in indigo.devices.iter(self.pluginId):
			props=dev.pluginProps
			if gpN in props and props[gpN]:
				props[gpN] = False
				gMembers = self.makeGroupMemberstring(props)
				dev.replacePluginPropsOnServer(props)
				gMembers = self.makeGroupMemberstring(props)
				self.updateDevStateGroupMembers(dev,gMembers)

		#self.myLog( text=" after	: "+str(self.groupStatusList[gpN]["members"]) )
		#self.myLog( text="        : "+unicode(props) )
		return valuesDict



	####-----------------	 ---------
	def filterDevicesToAddToGroup(self, valuesDict=None, filter="", typeId="", devId=""):
		xList=[]
		try: sg = int(self.selectedGroup)
		except: return xList
		for dev in indigo.devices.iter("props.isUniFi"):
			props = dev.pluginProps
			if str(dev.id) in  self.groupStatusList["Group"+str(sg)]["members"]: continue
			xList.append([str(dev.id),dev.name + "- "+ dev.states["MAC"]])
		#self.myLog( text="group members: "+unicode(xList))
		return xList

	####-----------------	 ---------
	def buttonConfirmADDGroupMemberCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		mm	= valuesDict["selectedGroupMemberIndigoIdadd"]
		gpN = "Group"+str(self.selectedGroup)
		try:
			dev = indigo.devices[int(mm)]
		except:
			self.indiLOG.log(30," bad dev id: "+str(mm) )
			return
		props = dev.pluginProps
		#self.myLog( text=" add to	 from group#:"+str(self.selectedGroup)+"  member: "+ dev.name+"     "+ dev.states["MAC"]+"     "+unicode(props) )
		if mm not in self.groupStatusList[gpN]["members"]:
			self.groupStatusList[gpN]["members"][mm]=True
		props[gpN] =True
		dev.replacePluginPropsOnServer(props)
		gMembers = self.makeGroupMemberstring(props)
		self.updateDevStateGroupMembers(dev,gMembers)
		#self.printMACs(dev.states["MAC"])
		return valuesDict



	####-----------------  GROUPS END	 ---------
	####-----------------	 ---------


	####-----------------  Ignore special MAC info	 ---------
	def buttonConfirmStartIgnoringSpecialMACCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		MAC = valuesDict[u"MACspecialIgnore"].split(":")
		if len(MAC) !=6:
			valuesDict[u"MSG"] ="bad MAC.. must be 12:xx:23:xx:45:aa"
			return valuesDict
		self.MACSpecialIgnorelist[valuesDict[u"MACspecialIgnore"]]=1
		self.indiLOG.log(20,u"start ignoring  MAC# "+valuesDict[u"MACspecialIgnore"])
		self.saveMACdata(force=True)
		valuesDict[u"MSG"] ="ok"
		return valuesDict
	####-----------------  UN- Ignore special MAC info	 ---------
	####----------------- ---------
	def buttonConfirmStopIgnoringSpecialMACCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):

		try: del self.MACSpecialIgnorelist[valuesDict[u"MACspecialUNIgnored"]]
		except: pass
		self.indiLOG.log(20,u" stop ignoring  MAC# " +valuesDict[u"MACspecialUNIgnored"])
		self.saveMACdata(force=True)
		valuesDict[u"MSG"] ="ok"
		return valuesDict




	####-----------------  Ignore MAC info	 ---------
	def buttonConfirmStartIgnoringCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		self.MACignorelist[valuesDict[u"MACdeviceSelected"]]=1
		self.indiLOG.log(20,u"start ignoring  MAC# "+valuesDict[u"MACdeviceSelected"])
		for dev in indigo.devices.iter("props.isUniFi,props.isCamera"):
			if u"MAC" in dev.states	 and dev.states[u"MAC"] == valuesDict[u"MACdeviceSelected"]:
				if u"displayStatus" in dev.states:
					dev.updateStateOnServer(u"displayStatus",self.padDisplay(u"ignored")+datetime.datetime.now().strftime(u"%m-%d %H:%M:%S"))
					dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
				dev.updateStateOnServer(u"status",value="ignored", uiValue=self.padDisplay(u"ignored")+datetime.datetime.now().strftime(u"%m-%d %H:%M:%S"))
		self.saveMACdata(force=True)
		return valuesDict
	####-----------------  UN- Ignore MAC info	 ---------
	####-----------------	 ---------
	def buttonConfirmStopIgnoringCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):

		for dev in indigo.devices.iter("props.isUniFi,props.isCamera"):
			if u"MAC" in dev.states	 and dev.states[u"MAC"] == valuesDict[u"MACdeviceIgnored"]:
				if u"displayStatus" in dev.states:
					dev.updateStateOnServer(u"displayStatus",self.padDisplay(u"")+datetime.datetime.now().strftime(u"%m-%d %H:%M:%S"))
					dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
				dev.updateStateOnServer(u"status","")
				dev.updateStateOnServer(u"onOffState", value=False, uiValue=self.padDisplay(u"")+datetime.datetime.now().strftime(u"%m-%d %H:%M:%S"))
		try: del self.MACignorelist[valuesDict[u"MACdeviceIgnored"]]
		except: pass
		self.saveMACdata(force=True)
		self.indiLOG.log(20,u" stop ignoring  MAC# " +valuesDict[u"MACdeviceIgnored"])
		return valuesDict



	####-----------------  powercycle switch port	---------
	####-----------------	 ---------
	def filterUnifiSwitchACTION(self, valuesDict=None, filter="", typeId="", devId=""):
		return self.filterUnifiSwitch(valuesDict)

	####-----------------	 ---------
	def filterUnifiSwitch(self, filter="", valuesDict=None, typeId="", devId=""):
		xList = []
		for dev in indigo.devices.iter("props.isSwitch"):
			swNo = int(dev.states[u"switchNo"])
			if self.SWsEnabled[swNo]:
				xList.append((unicode(swNo)+u"-SWtail-"+unicode(dev.id),unicode(swNo)+"-"+self.ipNumbersOfSWs[swNo]+u"-"+dev.name))
		return xList

	def buttonConfirmSWCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		self.unifiSwitchSelectedID =  valuesDict[u"selectedUnifiSwitch"].split("-")[2]
		return

	####-----------------	 ---------
	def filterUnifiSwitchPort(self, filter="", valuesDict=None, typeId="", devId=""):

		xList = []
		try:	int(self.unifiSwitchSelectedID)
		except: return xList

		dev = indigo.devices[int(self.unifiSwitchSelectedID)]
		snNo = unicode(dev.states[u"switchNo"] )
		for port in range(99):
			if u"port_%02d"%port not in dev.states: continue
			if	dev.states[u"port_%02d"%port].find("poe") >-1:
				if	dev.states[u"port_%02d"%port].find("poeX") >-1:
					name = " - empty"
				else:
					name =""
					for dev2 in indigo.devices.iter("props.isUniFi"):
						if "SW_Port" in dev2.states and len(dev2.states["SW_Port"]) > 2:
							sw	 = dev2.states["SW_Port"].split(":")
							if sw[0] == snNo:
								if sw[1].find("poe") >-1:
									if unicode(port) == sw[1].split("-")[0]:
										name = " - "+dev2.name
										break
				xList.append([port,u"port#"+unicode(port)+name])
		return xList

	####-----------------	 ---------
	def filterUnifiClient(self, filter="", valuesDict=None, typeId="", devId=""):

		xList = []
		for dev2 in indigo.devices.iter("props.isUniFi"):
			if "SW_Port" in dev2.states and len(dev2.states["SW_Port"]) > 2:
				sw	 = dev2.states["SW_Port"].split(":")
				if sw[1].find("poe") >-1:
					port = sw[1].split("-")[0]
					xList.append([sw[0]+"-"+port,u"sw"+sw[0]+"-"u"port#"+unicode(port)+" - "+dev2.name])
		return xList


	####-----------------	 ---------
	def buttonConfirmpowerCycleCALLBACKaction(self, action1=None, filter="", typeId="", devId=""):
		return self.buttonConfirmpowerCycleCALLBACK(valuesDict=action1.props)

	####-----------------	 ---------
	def buttonConfirmpowerCycleClientsCALLBACKaction(self, action1=None, filter="", typeId="", devId=""):
		return self.buttonConfirmpowerCycleClientsCALLBACK(valuesDict=action1.props)

	####-----------------	 ---------
	def buttonConfirmpowerCycleCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		onOffCycle	= valuesDict[u"onOffCycle"]
		ip_type		=  valuesDict[u"selectedUnifiSwitch"].split(u"-")
		ipNumber	= self.ipNumbersOfSWs[int(ip_type[0])]
		dtype		= ip_type[1]
		port		= unicode(valuesDict[u"selectedUnifiSwitchPort"])
		cmd = u"/usr/bin/expect "
		if onOffCycle == "CYCLE":
			cmd+= "'"+self.pathToPlugin + u"cyclePort.exp" + "' "
		elif  onOffCycle =="ON":
			cmd+= "'"+self.pathToPlugin + u"onPort.exp" + "' "
		elif  onOffCycle =="OFF":
			cmd+= "'"+self.pathToPlugin + u"offPort.exp" + "' "
		cmd+= "'"+self.unifiUserID + u"' '"+self.unifiPassWd + u"' "
		cmd+= ipNumber + " "
		cmd+= port + u" "
		cmd+= self.promptOnServer[dtype] +u" &"
		if self.decideMyLog(u"Expect"): self.indiLOG.log(20,"RECYCLE: "+cmd )
		ret = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()
		if self.decideMyLog(u"Connection"): self.indiLOG.log(20,"RECYCLE: "+unicode(ret))
		self.addToMenuXML(valuesDict)
		return valuesDict

	####-----------------	 ---------
	def buttonConfirmpowerCycleClientsCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		ip_type	 =	valuesDict[u"selectedUnifiClientSwitchPort"].split(u"-")
		valuesDict[u"selectedUnifiSwitch"]		= ip_type[0]+u"-SWtail"
		valuesDict[u"selectedUnifiSwitchPort"]	= ip_type[1]
		self.buttonConfirmpowerCycleCALLBACK(valuesDict)
		return valuesDict


	####-----------------  suspend / activate unifi devices	   ---------
	def buttonConfirmsuspendCALLBACKaction(self, action1=None, filter="", typeId="", devId=""):
		self.buttonConfirmsuspendCALLBACKbutton(valuesDict=action1.props)

	####-----------------  suspend / activate unifi devices	   ---------
	def buttonConfirmactivateCALLBACKaction(self, action1=None, filter="", typeId="", devId=""):
		self.buttonConfirmactivateCALLBACKbutton(valuesDict=action1.props)

	 ####-----------------	suspend / activate unifi devices	---------
	def buttonConfirmsuspendCALLBACKbutton(self, valuesDict=None, filter="", typeId="", devId=""):
		try:
			ID = int(valuesDict["selectedDevice"])
			dev= indigo.devices[ID]
			ip = dev.states["ipNumber"]
		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			return
		self.indiLOG.log(20,u"suspending Unifi system device "+dev.name+"  "+ip)
		self.setSuspend(ip, time.time()+9999999)
		self.exeDisplayStatus(dev,"susp")
		self.addToMenuXML(valuesDict)
		return valuesDict

	def buttonConfirmactivateCALLBACKbutton(self, valuesDict=None, filter="", typeId="", devId=""):
		try:
			ID = int(valuesDict["selectedDevice"])
			dev= indigo.devices[ID]
			ip = dev.states["ipNumber"]
			try:
				self.delSuspend(ip)
				self.exeDisplayStatus(dev,"up")
				self.indiLOG.log(20,u"reactivating Unifi system device "+dev.name+"     "+ip)
			except: pass
		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		self.addToMenuXML(valuesDict)
		return valuesDict



	####-----------------  Unifi api calls	  ---------


######## block / unblock reconnect
	####-----------------	 ---------
	def buttonConfirmReconnectCALLBACKaction(self, action1=None, filter="", typeId="", devId=""):
		return self.buttonConfirmReconnectCALLBACK(valuesDict=action1.props)

	####-----------------	 ---------
	def buttonConfirmReconnectCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		return self.executeCMDOnController(data={"cmd":"kick-sta","mac":valuesDict["selectedDevice"]},pageString="/cmd/stamgr",cmdType="post")


	####-----------------	 ---------
	def buttonConfirmBlockCALLBACKaction(self, action1=None, filter="", typeId="", devId=""):
		return self.buttonConfirmBlockCALLBACK(valuesDict=action1.props)

	####-----------------	 ---------
	def buttonConfirmBlockCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		ret = self.executeCMDOnController(data={"cmd":"block-sta","mac":valuesDict["selectedDevice"]},pageString="/cmd/stamgr",cmdType="post")
		self.lastCheckForcheckForBlockedClients = time.time() - self.unifigetBlockedClientsDeltaTime
		return ret


	####-----------------	 ---------
	def buttonConfirmUnBlockCALLBACKaction(self, action1=None, filter="", typeId="", devId=""):
		return self.buttonConfirmUnBlockCALLBACK(valuesDict=action1.props)

	####-----------------	 ---------
	def buttonConfirmUnBlockCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		ret = self.executeCMDOnController(data={"cmd":"unblock-sta","mac":valuesDict["selectedDevice"]}, pageString="/cmd/stamgr",cmdType="post")
		self.lastCheckForcheckForBlockedClients = time.time() - self.unifigetBlockedClientsDeltaTime
		return ret

######## block / unblock reconnec  end

######## reports for specific stations / devices
	def buttonConfirmGetAPDevInfoFromControllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		for dev in indigo.devices.iter("props.isAP"):
			MAC = dev.states["MAC"]
			if "MAClan" in dev.states: 
				props = dev.pluginProps
				if "useWhichMAC" in props and props["useWhichMAC"] == "MAClan":
					MAC = dev.states["MAClan"]
			self.indiLOG.log(20,"unifi-Report getting _id for AP "+dev.name+ "  "+"/stat/device/"+MAC )
			jData= self.executeCMDOnController(data={}, pageString="/stat/device/"+MAC, jsonAction="returnData", cmdType="get")
			for dd in jData:
				if "_id" not in dd:
					self.myLog( text="_id not in data  ", mType="unifi-Report")
					continue
				self.indiLOG.log(20,"unifi-Report  _id in data  :"+ dd["_id"])
				dev.updateStateOnServer("ap_id",dd["_id"])
				break
		self.addToMenuXML(valuesDict)
		return

	####-----------------	 ---------
	####-----------------	 ---------
	def buttonConfirmPrintDevInfoFromControllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		MAC = valuesDict["MACdeviceSelectedsys"]
		for dev in indigo.devices.iter("props.isAP,props.isSwitch,props.isGateway"):
			if "MAC" in dev.states and dev.states[u"MAC"] != MAC: continue
			if "MAClan" in dev.states and dev.states[u"MAClan"] != MAC:
				props = dev.pluginProps
				if "useWhichMAC" in props and props["useWhichMAC"] == "MAClan":
					MAC = dev.states["MAClan"]
			break	
		self.executeCMDOnController(data={}, pageString="/stat/device/"+MAC, jsonAction="print",startText="== Device print: /stat/device/"+MAC+" ==", cmdType="get")
		return

	####-----------------	 ---------
	def buttonConfirmPrintClientInfoFromControllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		MAC = valuesDict["MACdeviceSelectedclient"]
		self.executeCMDOnController(data={}, pageString="/stat/sta/"+MAC, jsonAction="print",startText="== Client print: /stat/sta/"+MAC+" ==")
		return

######## reports all devcies
	####-----------------	 ---------
	def buttonConfirmPrintalluserInfoFromControllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		data = self.executeCMDOnController(data={"type":"all","conn":"all"}, pageString="/stat/alluser/", jsonAction="returnData", cmdType="get")
		self.unifsystemReport3(data, "== ALL USER report ==")
		return

	####-----------------	 ---------
	def buttonConfirmPrintuserInfoFromControllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		data = self.executeCMDOnController(data={}, pageString="/list/user/", jsonAction="returnData", cmdType="get")
		self.unifsystemReport3(data, "== USER report ==")

####   general reports
	####-----------------	 ---------
	def buttonConfirmPrintHealthInfoFromControllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		data = self.executeCMDOnController(data={}, pageString="/stat/health/", jsonAction="returnData", cmdType="get")
		out ="== HEALTH report ==\n"
		ii=0
		for item in data:
			ii+=1
			ll =unicode(ii).ljust(3)
			ll+=(item["subsystem"]+":").ljust(10)
			ll+=(item["status"]+";").ljust(10)
			if "rx_bytes-r" in item:
				ll+="rx_B:"+(unicode(item["rx_bytes-r"])+";").ljust(9)
			if "tx_bytes-r" in item:
				ll+="tx_B:"+(unicode(item["tx_bytes-r"])+";").ljust(9)

			for item2 in item:
				if item2 =="subsystem":	  continue
				if item2 =="status":	  continue
				if item2 =="tx_bytes-r":  continue
				if item2 =="rx_bytes-r":  continue
				ll+=unicode(item2)+":"+unicode(item[item2])+";    "
			out+=ll+("\n")
		self.indiLOG.log(20,u"unifi-Report ")
		self.indiLOG.log(20,"unifi-Report  "+out)
		return

	####-----------------	 ---------
	def buttonConfirmPrintPortForWardInfoFromControllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		data =self.executeCMDOnController(data={}, pageString="/stat/portforward/", jsonAction="returnData", cmdType="get")
		out ="== PortForward report ==\n"
		out+= "##".ljust(4) + "name".ljust(20) + "protocol".ljust(10) + "source".ljust(16)	+ "fwd_port".ljust(9)+ "dst_port".ljust(9)+ "fwd_ip".ljust(17)+ "rx_bytes".ljust(10)+ "rx_packets".ljust(17)+"\n"
		ii=0
		for item in data:
			ii+=1
			ll = unicode(ii).ljust(4)
			ll+= item["name"].ljust(20)
			ll+= item["proto"].ljust(10)
			ll+= item["src"].ljust(16)
			ll+= item["fwd_port"].ljust(9)
			ll+= item["dst_port"].ljust(9)
			ll+= item["fwd"].ljust(17)
			ll+= unicode(item["rx_bytes"]).ljust(10)
			ll+= unicode(item["rx_packets"]).ljust(10)
			out+=ll+("\n")
		self.indiLOG.log(20,u"unifi-Report ")
		self.indiLOG.log(20,"unifi-Report  "+out)
		return
	####-----------------	 ---------
	def buttonConfirmPrintAlarmInfoFromControllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		data = self.executeCMDOnController(data={}, pageString="/list/alarm/", jsonAction="returnData", cmdType="get")
		self.unifsystemReport1(data,True,"    ==AlarmReport==",limit=99999)
		self.addToMenuXML(valuesDict)
		return


	####-----------------	 ---------
	def buttonConfirmPrintEventInfoFromControllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):

		limit					  = 100
		if "PrintEventInfoMaxEvents" in valuesDict:
			try:	limit = int(valuesDict["PrintEventInfoMaxEvents"])
			except: pass

		PrintEventInfoLoginEvents = False
		if "PrintEventInfoLoginEvents" in valuesDict:
			try:	PrintEventInfoLoginEvents = valuesDict["PrintEventInfoLoginEvents"]
			except: pass


		if PrintEventInfoLoginEvents:
			ltype = "WITH"
			useLimit = limit
		else:
			ltype = "Skipping"
			useLimit = 5*limit

		data = self.executeCMDOnController(data={"_sort":"+time", "within":999,"_limit":useLimit}, pageString="/stat/event/", jsonAction="returnData")
		self.unifsystemReport1(data,False,"     ==EVENTs ..;  last "+str(limit)+" events ;     -- "+ltype+" login events ==",limit,PrintEventInfoLoginEvents=PrintEventInfoLoginEvents)
		self.addToMenuXML(valuesDict)

		return

	####-----------------	 ---------
	def buttonConfirmPrint5MinutesInfoFromControllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		en = int( time.time() - (time.time() % 3600) ) * 1000
		st = en - 43200000 # 86400000/2 = 1/2 day
		data = self.executeCMDOnController(data={"attrs": ["bytes", "num_sta", "time"], "start": st, "end": en}, pageString="/stat/report/5minutes.ap", jsonAction="returnData")

		out ="== 5 minutes AP stst report =="+"\n"
		out+= "##".ljust(4)
		out+= "timeStamp".ljust(21)
		out+= "num_sta".rjust(8)
		out+= "Bytes".rjust(12)
		out+= "\n"
		ii=0
		lastap = ""
		for item in data:
			ii+=1
			if lastap != item["ap"]:
				out+="AP MAC #:"+item["ap"]+"\n"
			lastap = item["ap"]

			ll =unicode(ii).ljust(4)
			if "time" in item:
				ll+= time.strftime(u"%Y-%m-%d %H:%M:%S",time.localtime(item["time"]/1000)).ljust(21)
			else:				  ll+= (" ").ljust(21)

			if "num_sta" in item:
				ll+= unicode(item["num_sta"]).rjust(8)
			else:				  ll+= (" ").rjust(8)

			if "bytes" in item:
				ll+= ("{0:,d}".format(int(item["bytes"]))).rjust(12)
			else:				  ll+= (" ").rjust(12)

			out+=ll+("\n")
		self.indiLOG.log(20,u"unifi-Report ")
		self.indiLOG.log(20,"unifi-Report  "+out)
		return


	####-----------------	 ---------
	def buttonConfirmPrint48HourInfoFromControllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		en = int( time.time() - (time.time() % 3600) ) * 1000
		st = en - 2*86400000
		data = self.executeCMDOnController(data={"attrs": ["bytes","wan-tx_bytes","wan-rx_bytes","wan-tx_bytes", "num_sta", "wlan-num_sta", "lan-num_sta", "time"], "start": st, "end": en}, pageString="/stat/report/hourly.site", jsonAction="returnData")
		self.unifsystemReport2(data,"== 48 HOUR report ==")

	####-----------------	 ---------
	def buttonConfirmPrint7DayInfoFromControllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		en = int( time.time() - (time.time() % 3600) ) * 1000
		st = en - 7*86400000
		data = self.executeCMDOnController(data={"attrs": ["bytes","wan-tx_bytes","wan-rx_bytes","wan-tx_bytes", "num_sta", "wlan-num_sta", "lan-num_sta", "time"], "start": st, "end": en}, pageString="/stat/report/daily.site", jsonAction="returnData")
		self.unifsystemReport2(data,"== 7 DAY report ==")



	####-----------------	 ---------
	def buttonConfirmPrintWlanConfInfoFromControllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		data = self.executeCMDOnController(data={}, pageString="list/wlanconf", jsonAction="returnData")
		out ="==WLan Report =="+"\n"
		out+=" ".ljust(4+20+6+20)+"bc_filter...".ljust(6+15) +"dtim .......".ljust(8+3+3)+"MAC_filter ........".ljust(6+20+8)+" ".ljust(15+8)+"wpa......".ljust(6+6)+"\n"
		out+= "##".ljust(4)
		out+= "name".ljust(20)
		out+= "passphrase".ljust(20)
		out+= "enble".ljust(6)
		out+= "enble".ljust(6)
		out+= "list".ljust(15)
		out+= "mode".ljust(8)
		out+= "na".ljust(3)
		out+= "ng".ljust(3)
		out+= "enble".ljust(6)
		out+= "list".ljust(20)
		out+= "policy".ljust(8)
		out+= "schedule".ljust(15)
		out+= "secrty".ljust(8)
		out+= "enc".ljust(6)
		out+= "mode".ljust(6)
		out+= "\n"
		ii=0
		for item in data:
			ii+=1
			ll =unicode(ii).ljust(4)
			if "name" in item:
				ll+= unicode(item["name"]).ljust(20)
			else:
				ll+= (" ").ljust(20)

			if "x_passphrase" in item:
				ll+= unicode(item["x_passphrase"]).ljust(20)
			else:
				ll+= (" ").ljust(16)

			if "enabled" in item:
				ll+= unicode(item["enabled"]).ljust(6)
			else:				  ll+= (" ").ljust(6)

			if "bc_filter_enabled" in item:
				ll+= unicode(item["bc_filter_enabled"]).ljust(6)
			else:				 ll+= (" ").ljust(6)

			if "bc_filter_list" in item:
				ll+= unicode(item["bc_filter_list"]).ljust(15)
			else:				 ll+= (" ").ljust(15)

			if "dtim_mode" in item:
				ll+= unicode(item["dtim_mode"]).ljust(8)
			else:				 ll+= (" ").ljust(8)

			if "dtim_na" in item:
				ll+= unicode(item["dtim_na"]).ljust(3)
			else:				 ll+= (" ").ljust(3)

			if "dtim_ng" in item:
				ll+= unicode(item["dtim_ng"]).ljust(3)
			else:				 ll+= (" ").ljust(3)

			if "mac_filter_enabled" in item:
				ll+= unicode(item["mac_filter_enabled"]).ljust(6)
			else:				 ll+= (" ").ljust(6)

			if "mac_filter_list" in item:
				ll+= unicode(item["mac_filter_list"]).ljust(20)
			else:				 ll+= (" ").ljust(20)

			if "mac_filter_policy" in item:
				ll+= unicode(item["mac_filter_policy"]).ljust(8)
			else:				 ll+= (" ").ljust(8)

			if "schedule" in item:
				ll+= unicode(item["schedule"]).ljust(15)
			else:				 ll+= (" ").ljust(15)

			if "security" in item:
				ll+= unicode(item["security"]).ljust(8)
			else:				 ll+= (" ").ljust(8)

			if "wpa_enc" in item:
				ll+= unicode(item["wpa_enc"]).ljust(6)
			else:				 ll+= (" ").ljust(6)

			if "wpa_mode" in item:
				ll+= unicode(item["wpa_mode"]).ljust(6)
			else:				 ll+= (" ").ljust(6)


			out+=ll+("\n")
		self.indiLOG.log(20,u"unifi-Report ")
		self.indiLOG.log(20,"unifi-Report  "+out)
		return


	####-----------------	 ---------
	def unifsystemReport1(self,data,useName, start,limit, PrintEventInfoLoginEvents= False):
		out =start+"\n"
		if useName:
			out+= "##### datetime------".ljust(21+6) + "name---".ljust(30) + "subsystem--".ljust(12) + "key--------".ljust(30)    + "msg-----".ljust(50)+"\n"
		else:
			out+= "##### datetime------".ljust(21+6)                       + "subsystem--".ljust(12) + "key--------".ljust(30)    + "msg-----".ljust(50)+"\n"
		nn = 0
		for item in data:
			if not PrintEventInfoLoginEvents and item["msg"].find("log in from ")> -1: continue
			nn+=1
			if nn > limit: break
			## convert from UTC to local datetime string
			dd = datetime.datetime.strptime(item["datetime"],u"%Y-%m-%dT%H:%M:%SZ")
			xx = (dd - datetime.datetime(1970,1,1)).total_seconds()
			ll = unicode(nn).ljust(6)
			ll += time.strftime(u"%Y-%m-%d %H:%M:%S",time.localtime(xx)).ljust(21)
			if useName:
				found = False
				for	 xx in ["ap_name","gw_name","sw_name","ap_name"]:
					if xx in item:
						ll+= item[xx].ljust(30)
						found = True
						break
				if not found:
						ll+= " ".ljust(30)
			ll +=item["subsystem"].ljust(12) + item["key"].ljust(30) + item["msg"].ljust(50)
			out+= ll.replace("\n","")+"\n"
		self.indiLOG.log(20,u"unifi-Report ")
		self.indiLOG.log(20,"unifi-Report  "+out)
		return

	####-----------------	 ---------
	def unifsystemReport2(self,data, start):
		out =start+"\n"
		out+= "##".ljust(4)
		out+= "timeStamp".ljust(21)
		out+= "lanNumSta".ljust(11)
		out+= "num_sta".ljust(11)
		out+= "wlanNumSta".ljust(11)
		out+= "rx-WanBytes".rjust(20)
		out+= "tx-WanBytes".rjust(20)
		out+= "\n"
		ii=0
		for item in data:
			ii+=1
			ll =unicode(ii).ljust(4)
			if "time" in item:
				ll+= time.strftime(u"%Y-%m-%d %H:%M:%S",time.localtime(item["time"]/1000)).ljust(21)
			else:
				ll+= (" ").ljust(21)

			if "lan-num_sta" in item:
				ll+= unicode(item["lan-num_sta"]).ljust(11)
			else:
				ll+= (" ").ljust(10)

			if "num_sta" in item:
				ll+= unicode(item["num_sta"]).ljust(11)
			else:
				ll+= (" ").ljust(11)

			if "wlan-num_sta" in item:
				ll+= unicode(item["wlan-num_sta"]).ljust(11)
			else:
				ll+= (" ").ljust(11)

			if "wan-rx_bytes" in item:
				ll+= ("{0:,d}".format(int(item["wan-rx_bytes"]))).rjust(20)
			else:
				ll+= (" ").ljust(17)

			if "wan-tx_bytes" in item:
				ll+= ("{0:,d}".format(int(item["wan-tx_bytes"]))).rjust(20)
			else:
				ll+= (" ").ljust(17)

			for item2 in item:
				if item2 =="lan-num_sta":	continue
				if item2 =="wlan-num_sta":	continue
				if item2 =="num_sta":		continue
				if item2 =="wan-rx_bytes":	continue
				if item2 =="wan-tx_bytes":	continue
				if item2 =="time":			continue
				if item2 =="oid":			continue
				if item2 =="site":			continue
				ll+=unicode(item2)+":"+unicode(item[item2])+";...."

			out+=ll+("\n")
		self.indiLOG.log(20,u"unifi-Report ")
		self.indiLOG.log(20,"unifi-Report  "+out)
		return

	####-----------------	 ---------
	def unifsystemReport3(self,data, start):
		out =start+"\n"
		out+= "##".ljust(4) + "mac".ljust(18)
		out+= "hostname".ljust(21) + "name".ljust(21)
		out+= "first_seen".ljust(21)+ "last_seen".ljust(21)
		out+= "vendor".ljust(10)
		out+= "fixedIP".ljust(16)
		out+= "us_f-ip".ljust(8)
		out+= "wired".ljust(6)
		out+= "blckd".ljust(6)
		out+= "guest".ljust(6)
		out+= "durationMin".rjust(12)
		out+= "rx_KBytes".rjust(16)
		out+= "rx_Packets".rjust(15)
		out+= "rx_KBytes".rjust(16)
		out+= "tx_Packets".rjust(15)
		out+="\n"
		ii=0
		for item in data:
			ii+=1
			ll =unicode(ii).ljust(4)
			if "mac" in item:
				ll+= item["mac"].ljust(18)
			else:
				ll+= (" ").ljust(18)

			if "hostname" in item:
				ll+= (item["hostname"][0:20]).ljust(21)
			else:
				ll+= (" ").ljust(21)

			if "name" in item:
				ll+= (item["name"][0:20]).ljust(21)
			else:
				ll+= (" ").ljust(21)

			if "first_seen" in item:
				ll+= time.strftime(u"%Y-%m-%d %H:%M:%S",time.localtime(item["first_seen"])).ljust(21)
			else:
				ll+= (" ").ljust(21)

			if "last_seen" in item:
				ll+= time.strftime(u"%Y-%m-%d %H:%M:%S",time.localtime(item["last_seen"])).ljust(21)
			else:
				ll+= (" ").ljust(21)

			if "oui" in item:
				ll+= (item["oui"][0:20]).ljust(10)
			else:
				ll+= (" ").ljust(10)

			if "fixed_ip" in item:
				ll+= (item["fixed_ip"]).ljust(16)
			else:
				ll+= (" ").ljust(16)

			if "use_fixedip" in item:
				ll+= unicode(item["use_fixedip"]).ljust(8)
			else:
				ll+= (" ").ljust(8)

			if "is_wired" in item:
				ll+= unicode(item["is_wired"]).ljust(6)
			else:
				ll+= (" ").ljust(6)

			if "blocked" in item:
				ll+= unicode(item["blocked"]).ljust(6)
			else:
				ll+= (" ").ljust(6)

			if "is_guest" in item:
				ll+= unicode(item["is_guest"]).ljust(6)
			else:
				ll+= (" ").ljust(6)

			if "duration" in item:
				ll+= ("{0:,d}".format(int(item["duration"])/60)).rjust(12)
			else:
				ll+= (" ").rjust(12)

			if "rx_bytes" in item:
				ll+= ("{0:,d}".format(int(item["rx_bytes"]/1024.))).rjust(16)
			else:
				ll+= (" ").rjust(16)

			if "rx_packets" in item:
				ll+= ("{0:,d}".format(int(item["rx_packets"]))).rjust(15)
			else:
				ll+= (" ").rjust(15)

			if "tx_bytes" in item:
				ll+= ("{0:,d}".format(int(item["tx_bytes"]/1024.))).rjust(16)
			else:
				ll+= (" ").rjust(16)

			if "tx_packets" in item:
				ll+= ("{0:,d}".format(int(item["tx_packets"]))).rjust(15)
			else:
				ll+= (" ").ljust(15)

			for item2 in item:
				if item2 =="hostname":	   continue
				if item2 =="mac":		   continue
				if item2 =="first_seen":   continue
				if item2 =="last_seen":	   continue
				if item2 =="site_id":	   continue
				if item2 =="_id":		   continue
				if item2 =="network_id":   continue
				if item2 =="usergroup_id": continue
				if item2 =="noted":		   continue
				if item2 =="name":		   continue
				if item2 =="is_wired":	   continue
				if item2 =="oui":		   continue
				if item2 =="blocked":	   continue
				if item2 =="fixed_ip":	   continue
				if item2 =="use_fixedip":  continue
				if item2 =="is_guest":	   continue
				if item2 =="duration":	   continue
				if item2 =="rx_bytes":	   continue
				if item2 =="tx_bytes":	   continue
				if item2 =="tx_packets":   continue
				if item2 =="rx_packets":   continue
				ll+=unicode(item2)+":"+unicode(item[item2])+";...."
			out+=ll+("\n")


		self.indiLOG.log(20,u"unifi-Report ")
		self.indiLOG.log(20,"unifi-Report  "+out)
		return


######## reports end



######## actions and menu set leds on /off
	####-----------------	 ---------
	def buttonConfirmAPledONControllerCALLBACKaction(self, action1=None, filter="", typeId="", devId=""):
		return self.buttonConfirmAPledONControllerCALLBACK(valuesDict=action1.props)
	####-----------------	 ---------
	def buttonConfirmAPledONControllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		self.executeCMDOnController(data={"led_enabled":True}, pageString="/set/setting/mgmt")
		return

	####-----------------	 ---------
	def buttonConfirmAPledOFFControllerCALLBACKaction(self, action1=None, filter="", typeId="", devId=""):
		return self.buttonConfirmAPledOFFControllerCALLBACK(valuesDict=action1.props)
	####-----------------	 ---------
	def buttonConfirmAPledOFFControllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		self.executeCMDOnController(data={"led_enabled":False,"mac":False}, pageString="/set/setting/mgmt")
		return

	####-----------------	 ---------
	def buttonConfirmAPxledONControllerCALLBACKaction(self, action1=None, filter="", typeId="", devId=""):
		return self.buttonConfirmAPxledONControllerCALLBACK(valuesDict=action1.props)
	####-----------------	 ---------
	def buttonConfirmAPxledONControllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		self.executeCMDOnController(data={"cmd":"set-locate","mac":valuesDict["selectedAPDevice"]}, pageString="/cmd/devmgr")
		return valuesDict

	####-----------------	 ---------
	def buttonConfirmAPxledOFFControllerCALLBACKaction(self, action1=None, filter="", typeId="", devId=""):
		return self.buttonConfirmAPxledOFFControllerCALLBACK(valuesDict=action1.props)
	####-----------------	 ---------
	def buttonConfirmAPxledOFFControllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		self.executeCMDOnController(data={"cmd":"unset-locate","mac":valuesDict["selectedAPDevice"]}, pageString="/cmd/devmgr")
		return valuesDict

	####-----------------	 ---------
	def buttonConfirmEnableAPConllerCALLBACKaction(self, action1=None, filter="", typeId="", devId=""):
		self.execDisableAP(action1.props,False)
	def buttonConfirmEnableAPConllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		self.execDisableAP(valuesDict, False)
		return valuesDict

	####-----------------	 ---------
	def buttonConfirmDisableAPConllerCALLBACKaction(self, action1=None, filter="", typeId="", devId=""):
		self.execDisableAP(action1.props, True)
	def buttonConfirmDisableAPConllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
		self.execDisableAP(valuesDict, True)
		return valuesDict

	def execDisableAP(self, valuesDict,disable): #( true if disable )
		dev = indigo.devices[int(valuesDict["apDeviceSelected"])]
		ID = dev.states["ap_id"]
		ip = dev.states["ipNumber"]
		if disable: self.setSuspend(ip, time.time() + 99999999)
		else	  : self.delSuspend(ip)
		self.executeCMDOnController(data={"disabled":disable}, pageString="/rest/device/"+ID, cmdType="put")
		return valuesDict


######## set leds on /off  END

######## set defaults for action and menu screens
	#/////////////////////////////////////////////////////////////////////////////////////
	# Actions Configuration
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine returns the actions for the plugin; you normally don't need to
	# override this as the base class returns the actions from the Actions.xml file
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getActionsDict(self):
		return super(Plugin, self).getActionsDict()

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine obtains the callback method to execute when the action executes; it
	# normally just returns the action callback specified in the Actions.xml file
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getActionCallbackMethod(self, typeId):
		return super(Plugin, self).getActionCallbackMethod(typeId)

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine returns the configuration XML for the given action; normally this is
	# pulled from the Actions.xml file definition and you need not override it
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getActionConfigUiXml(self, typeId, devId):
		return super(Plugin, self).getActionConfigUiXml(typeId, devId)

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine returns the UI values for the action configuration screen prior to it
	# being shown to the user
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	####-----------------	 ---------
	def getActionConfigUiValues(self, pluginProps, typeId, devId):
		#self.myLog( text=unicode(pluginProps)+"  typeId;"+unicode(typeId)+"  devId:"+unicode(devId))
		if "fileNameOfImage" in pluginProps:
			if len(self.changedImagePath) > 5:
				pluginProps["fileNameOfImage"] = self.changedImagePath+"nameofCamera.jpeg"
			else:
				pluginProps["fileNameOfImage"] = self.indigoPreferencesPluginDir+"nameofCamera.jpeg"
		return super(Plugin, self).getActionConfigUiValues(pluginProps, typeId, devId)


	#/////////////////////////////////////////////////////////////////////////////////////
	# Menu Item Configuration
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine returns the menu items for the plugin; you normally don't need to
	# override this as the base class returns the menu items from the MenuItems.xml file
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getMenuItemsList(self):
		return super(Plugin, self).getMenuItemsList()

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine returns the configuration XML for the given menu item; normally this is
	# pulled from the MenuItems.xml file definition and you need not override it
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getMenuActionConfigUiXml(self, menuId):
		return super(Plugin, self).getMenuActionConfigUiXml(menuId)

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine returns the initial values for the menu action config dialog, if you
	# need to set them prior to the GUI showing
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	####-----------------	 ---------
	def getMenuActionConfigUiValues(self, menuId):
		valuesDict = indigo.Dict()
		if menuId == "CameraActions" and ("fileNameOfImage" not in self.menuXML or len(self.menuXML["fileNameOfImage"]) <10 ):
			if len(self.changedImagePath) > 5:
				self.menuXML["fileNameOfImage"] = self.changedImagePath+"nameofCamera.jpeg"
			else:
				self.menuXML["fileNameOfImage"] = self.indigoPreferencesPluginDir+"nameofCamera.jpeg"
		self.menuXML["snapShotTextMethod"] = self.imageSourceForSnapShot

		for item in self.menuXML:
			valuesDict[item] = self.menuXML[item]
		errorsDict = indigo.Dict()
		return (valuesDict, errorsDict)


########  check if we have blocked/ unblocked devices
	####-----------------	 ---------
	def addFirstSeenToStates(self):
		try:
			if self.unifiCloudKeyMode != "ON":														 return
			listOfClients={}
			# get data from conroller
			data =	  self.executeCMDOnController(data={"type": "all", "conn": "all"}, pageString="stat/alluser", jsonAction="returnData", cmdType="get")
			if data == {}:
				self.indiLOG.log(20,u"addFirstSeenToStates  "+"No data returned from controller")
				return
			for client in data:
				if len(client) ==0: continue
				if "mac" not in client: continue
				listOfClients[client["mac"]] = {}
				if "first_seen" in client:
					try: listOfClients[client["mac"]]["first_seen"] = datetime.datetime.fromtimestamp(client["first_seen"]).strftime(u"%Y-%m-%d %H:%M:%S")
					except: pass

				if "use_fixedip" in client:
						listOfClients[client["mac"]]["use_fixedip"] = client["use_fixedip"]
				else:
						listOfClients[client["mac"]]["use_fixedip"] = False

			for dev in indigo.devices.iter("props.isUniFi"):
				MAC = dev.states["MAC"]
				if	MAC in listOfClients:
					if "first_seen" in listOfClients[MAC]:
						if "firstSeen" in dev.states and dev.states["firstSeen"] != listOfClients[MAC]["first_seen"]:
							dev.updateStateOnServer("firstSeen",listOfClients[MAC]["first_seen"])

					if "use_fixedip" in listOfClients[MAC]:
						if "useFixedIP" in dev.states and dev.states["useFixedIP"] != listOfClients[MAC]["use_fixedip"]:
							dev.updateStateOnServer("useFixedIP",listOfClients[MAC]["use_fixedip"])

		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		return

########  check if we have blocked/ unblocked devices
	####-----------------	 ---------
	def checkForBlockedClients(self, force= False):
		try:
			if self.unifiCloudKeyMode.find("ON") == -1:																	   return
			if time.time() - self.lastCheckForcheckForBlockedClients < self.unifigetBlockedClientsDeltaTime and not force: return
			self.lastCheckForcheckForBlockedClients = time.time()
			listOfBlockedClients={}

			# get data from conroller
			data =	  self.executeCMDOnController(data={"type": "all", "conn": "all"}, pageString="stat/alluser", jsonAction="returnData", cmdType="get")
			if data == {}:
				self.indiLOG.log(20,"No data returned from controller")#,mType="Connection")
				return
			for client in data:
				if len(client) ==0: continue
				#self.myLog( text=unicode(client)[0:100])
				if "mac" not in client: continue
				if "blocked" in client:
					listOfBlockedClients[client["mac"]] = client["blocked"]

			for dev in indigo.devices.iter("props.isUniFi"):
				MAC = dev.states["MAC"]
				if	MAC in listOfBlockedClients:
					if "blocked" in dev.states:
						if dev.states["blocked"] != listOfBlockedClients[MAC]:
							dev.updateStateOnServer("blocked",listOfBlockedClients[MAC])
				else:
					if force:
						if "blocked" in dev.states and dev.states["blocked"]:
							dev.updateStateOnServer("blocked",False)

		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}    Connection".format(sys.exc_traceback.tb_lineno, e))

		return






########  check if we have new unifi system devces, if yes: litt basic variables and request a reboot
	####-----------------	 ---------
	def checkForNewUnifiSystemDevices(self):
		try:
			if self.checkforUnifiSystemDevicesState =="": return
			self.checkforUnifiSystemDevicesState  = ""
			if self.unifiCloudKeyMode != "ON"			: return
			newDeviceFound =[]

			deviceDict =		self.executeCMDOnController(data={}, pageString="/stat/device/", jsonAction="returnData", cmdType="get")
			if deviceDict =={}: return
			for item in deviceDict:
				ipNumber = ""
				MAC		 = ""
				if "type"   not in item: continue
				uType	 = item["type"]

				if uType == "ugw":
					if "network_table" in item:
						#self.myLog( text=u"network_table:"+json.dumps(item["network_table"], sort_keys=True, indent=2)	,mType="test" )
						for nwt in item["network_table"]:
							if "mac" in nwt and "ip"  in nwt and "name" in nwt and nwt["name"].lower() =="lan":
								ipNumber = nwt["ip"]
								MAC		 = nwt["mac"]
								break
				else:
					if "mac" in item and "ip" in item:
						ipNumber = item["ip"]
						MAC		 = item["mac"]

				if MAC =="" or ipNumber == "":
					#self.myLog( text=unicode(item),mType="test" )
					continue

				found = False
				name = "--"

				for dev in indigo.devices.iter("props.isAP,props.isSwitch,props.isGateway"):
					#self.myLog( text= dev.name ,mType="test" )
					if "MAClan" in dev.states and dev.states[u"MAClan"] == MAC:
						found = True
						name = dev.name
						break
					if "MAC" in dev.states and dev.states[u"MAC"] == MAC:
						found = True
						name = dev.name
						break
						## found devce no action

				if not found:

					if uType.find("uap") >-1:
						for i in range(len(self.ipNumbersOfAPs)):
							if	not self.isValidIP(self.ipNumbersOfAPs[i]):
								newDeviceFound.append("uap:	 , new {}     existing: {}".format(ipNumber, self.ipNumbersOfAPs[i]) )
								self.ipNumbersOfAPs[i]						= ipNumber
								self.pluginPrefs[u"ip"+unicode(i)]			= ipNumber
								self.pluginPrefs[u"ipON"+unicode(i)]		= True
								self.checkforUnifiSystemDevicesState		= "reboot"
								newDeviceFound.append("uap: "+unicode(i)+", "+ipNumber)
								break
							else:
								if self.ipNumbersOfAPs[i]	 == ipNumber:
									if not self.APsEnabled[i]: break # we know this one but it is disabled on purpose
									newDeviceFound.append("uap:	 , new {}     existing: {}".format(ipNumber, self.ipNumbersOfAPs[i] ) )
									self.ipNumbersOfAPs[i]					= ipNumber
									#self.APsEnabled[i]						= True # will be enabled after restart
									self.pluginPrefs[u"ipON"+unicode(i)]	= True
									self.checkforUnifiSystemDevicesState	= "reboot"
									newDeviceFound.append("uap: "+unicode(i)+", "+ipNumber)
									break

					elif uType.find("usw") >-1:
						for i in range(len(self.ipNumbersOfSWs)):
							if	not self.isValidIP(self.ipNumbersOfSWs[i] ):
								newDeviceFound.append("usw:	 , new {}     existing: {}".format(ipNumber, self.ipNumbersOfSWs[i]) )
								self.ipNumbersOfSWs[i]						= ipNumber
								self.pluginPrefs[u"ipSW"+unicode(i)]		= ipNumber
								self.pluginPrefs[u"ipSWON"+unicode(i)]		= True
								self.checkforUnifiSystemDevicesState		= "reboot"
								break
							else:
								if self.ipNumbersOfSWs[i] == ipNumber:
									if not self.SWsEnabled[i]: break # we know this one but it is disabled on purpose
									newDeviceFound.append("usw:	 , new {}     existing: {}".format(ipNumber, self.ipNumbersOfSWs[i]) )
									self.ipNumbersOfSWs[i]					= ipNumber
									#self.SWsEnabled[i]						= True # will be enabled after restart
									self.pluginPrefs[u"ipSWON"+unicode(i)]	= True
									self.checkforUnifiSystemDevicesState	= "reboot"
									break

					elif uType.find("ugw") >-1:
							#### "ip" in the dict is the ip number of the wan connection NOT the inernal IP for the gateway !!
							#### using 2 other places instead to get the LAN IP
							if	not self.isValidIP(self.ipnumberOfUGA):
								newDeviceFound.append("ugw:	 , new {}     existing: {}".format(ipNumber, self.ipnumberOfUGA) )
								self.ipnumberOfUGA							= ipNumber
								self.pluginPrefs[u"ipUGA"]					= ipNumber
								self.pluginPrefs[u"ipUGAON"]				= True
								self.checkforUnifiSystemDevicesState		= "reboot"
							else:
								if not self.UGAEnabled: break # we know this one but it is disabled on purpose
								if self.ipnumberOfUGA != ipNumber:
									newDeviceFound.append("ugw:	 , new {}     existing: {}".format(ipNumber, self.ipnumberOfUGA) )
									self.ipnumberOfUGA						= ipNumber
									self.pluginPrefs[u"ipUGA"]				= ipNumber
									self.pluginPrefs[u"ipUGAON"]			= True
									self.checkforUnifiSystemDevicesState	= "reboot"
								else:
									newDeviceFound.append("ugw:	 , new {}     existing: {}".format(ipNumber, self.UGAEnabled) )
									self.pluginPrefs[u"ipUGAON"]			= True
									self.checkforUnifiSystemDevicesState	= "reboot"

			if self.checkforUnifiSystemDevicesState =="reboot":
				try:
					self.pluginPrefs[u"createUnifiDevicesCounter"] = int(self.pluginPrefs[u"createUnifiDevicesCounter"] ) +1
					if int(self.pluginPrefs[u"createUnifiDevicesCounter"] ) > 1: # allow only 1 unsucessful try, then wait 10 minutes
						self.checkforUnifiSystemDevicesState		   = ""
					else:
						self.indiLOG.log(20,u"Connection   reboot required due to new UNIFI system device found:{}".format(newDeviceFound))
				except:
						self.checkforUnifiSystemDevicesState		   = ""
			try:	indigo.server.savePluginPrefs()
			except: pass

			if self.checkforUnifiSystemDevicesState =="":
				self.pluginPrefs[u"createUnifiDevicesCounter"] = 0

		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}   Connection".format(sys.exc_traceback.tb_lineno, e))

		return




	####-----------------	 ---------
	def executeMCAconfigDumpOnGW(self, valuesDict={},typeId="" ):
		keepList=["vpn","port-forward","service:radius-server","service:dhcp-server"]
		jsonAction="print"
		ret =[]
		if self.commandOnServer["GWctrl"].find("off") ==0: return valuesDict
		try:
			cmd = "/usr/bin/expect	'" + \
				  self.pathToPlugin + self.expectCmdFile["GWctrl"] + "' " + \
				  "'"+self.unifiUserID+ "' '"+self.unifiPassWd+ "' " + \
				  self.ipnumberOfUGA + " " + \
				  self.promptOnServer["GWctrl"] + " " + \
				  " XXXXsepXXXXX " + " " + \
				  "\""+self.commandOnServer["GWctrl"] +"\""
			if self.decideMyLog(u"Expect"): self.indiLOG.log(20," UGA EXPECT CMD: "+ unicode(cmd))
			ret = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()
			dbJson, error= self.makeJson2(ret[0], "XXXXsepXXXXX")
			if jsonAction == "print":
				for xx in keepList:
					if xx.find(":") >-1:
						yy = xx.split(":")
						if yy[0] in dbJson and yy[1] in dbJson[yy[0]]:
							short = dbJson[yy[0]][yy[1]]
							if yy[1] =="dhcp-server":
								for z in short:
									if z =="shared-network-name":
										for zz in short[z]:
											#self.myLog( text=" in "+zz)
											for zzz in short[z][zz]: # net_LAN_192.168.1.0-24"
												if zzz =="subnet":
													for zzzz in short[z][zz][zzz]:	# "192.168.1.0/24"
														for zzzzz in short[z][zz][zzz][zzzz]:
															if zzzzz =="static-mapping":
																s0 = short[z][zz][zzz][zzzz][zzzzz]
																## need to sort
																u =[]
																v =[]
																for t in s0:
																	u.append((s0[t]["mac-address"],s0[t]["ip-address"]))
																	v.append((self.fixIP(s0[t]["ip-address"]),s0[t]["ip-address"],s0[t]["mac-address"]))

																sortMacKey = sorted(u)
																sortIPKey  = sorted(v)
																out ="     static DHCP mappings:\n"
																for m in range(len(sortMacKey)):
																	out += sortMacKey[m][0]+" --> "+ sortMacKey[m][1].ljust(20)+"        " +sortIPKey[m][1].ljust(18)+"--> "+ sortIPKey[m][2]+"\n"
																self.myLog( text= out, mType="==== UGA-setup ====")
							else:
								self.myLog( text="    " +xx+":\n"+json.dumps(short,sort_keys=True,indent=2), mType="==== UGA-setup ====")
						else:
							self.myLog( text=xx+" not in json returned from UGA ", mType="UGA-setup")
					else:
						if xx in dbJson:
							self.myLog( text="    " +xx+":\n"+json.dumps(dbJson[xx],sort_keys=True,indent=2), mType="==== UGA-setup ====")
						else:
							self.myLog( text=xx+" not in json returned from UGA ", mType="==== UGA-setup ====")
			else:
				return valuesDict


		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}\n system info:\n>>{}<<".format(sys.exc_traceback.tb_lineno, e, unicode(ret)[0:100]) )
		return valuesDict

	####-----------------	 ---------
	def executeCMDOnController(self, data={},pageString="",jsonAction="",startText="", cmdType="put"):

		try:
			if not self.isValidIP(self.unifiCloudKeyIP): return {}
			if self.unifiCloudKeyMode.find("ON")   ==-1: return {}


			if self.unfiCurl.find("curl") > -1:
				cmdL  = self.unfiCurl+" --insecure -c /tmp/unifiCookie -H \"Content-Type: application/json\" --data '"+json.dumps({"username":self.unifiCONTROLLERUserID,"password":self.unifiCONTROLLERPassWd})+"' 'https://"+self.unifiCloudKeyIP+":"+self.unifiCloudKeyPort+self.apiLoginPath+"'"
				if data =={}: dataDict = ""
				else:		  dataDict = " --data '"+json.dumps(data)+"' "
				if	 cmdType == "put":	  cmdTypeUse= " -X PUT "
				elif cmdType == "post":	  cmdTypeUse= " -X POST "
				elif cmdType == "get":	  cmdTypeUse= " -X GET "
				else:					  cmdTypeUse= " "
				cmdR  = self.unfiCurl+" --insecure -b /tmp/unifiCookie " +dataDict+cmdTypeUse+ "'https://"+self.unifiCloudKeyIP+":"+self.unifiCloudKeyPort+self.unifiApiWebPage+self.unifiCloudKeySiteName+"/"+pageString.strip("/")+"'"


				if self.decideMyLog(u"Connection"): self.indiLOG.log(20,"Connection: "+cmdL )
				try:
					if time.time() - self.lastUnifiCookieCurl > 100: # re-login every 90 secs
						ret = subprocess.Popen(cmdL, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()
						try: jj = json.loads(ret[0])
						except:
							self.indiLOG.log(40,"UNIFI executeCMDOnController error no json object: (wrong UID/passwd, ip number?) ...>>"+ unicode(ret[0]) +"<<\n"+unicode(ret[1])+" Connection")
							return []
						if self.UDMPro == "True":
							if 'username' not in jj:
								self.indiLOG.log(40,u"UNIFI executeCMDOnController error: (wrong UID/passwd, ip number?) ...>>"+ unicode(ret[0]) +"<<\n"+unicode(ret[1])+" Connection")
								return []
						elif jj["meta"]["rc"] !="ok":
							self.indiLOG.log(40,u"UNIFI executeCMDOnController error: (wrong UID/passwd, ip number?) ...>>"+ unicode(ret[0]) +"<<\n"+unicode(ret[1])+" Connection")
							return []
						elif self.decideMyLog(u"Connection"):	 self.indiLOG.log(20,"Connection: "+ret[0] )
						self.lastUnifiCookieCurl =time.time()


					if self.decideMyLog(u"Connection"):	self.indiLOG.log(20,"Connection: "+cmdR )
					if startText !="":					self.indiLOG.log(20,"Connection: "+startText)
					try:
						ret = subprocess.Popen(cmdR, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()
						try:
							jj = json.loads(ret[0])
						except :
							self.indiLOG.log(40,"UNIFI executeCMDOnController has error, no json object returned: " + unicode(ret))
							return []

						if jj["meta"]["rc"] !="ok":
							self.indiLOG.log(40,u" Connection error: >>"+ unicode(ret[0]) +"<<\n"+unicode(ret[1]))
							return []

						if self.decideMyLog(u"Connection"):	self.indiLOG.log(20,"Connection: "+ret[0] )

						if  jsonAction=="print":
							self.indiLOG.log(20,u" Connection  info\n"+ json.dumps(jj["data"],sort_keys=True, indent=2))
							return []

						if  jsonAction=="returnData":
							self.writeJson(jj["data"], fName=self.indigoPreferencesPluginDir+"dict-Controller-"+pageString.replace("/","_").replace(" ","-").replace(":","=").strip("_")+".txt", sort=True, doFormat=True )
							return jj["data"]

						return []
					except	Exception, e:
						self.indiLOG.log(40,"Connection: in Line {} has error={}   Connection".format(sys.exc_traceback.tb_lineno, e) )
				except	Exception, e:
					self.indiLOG.log(40,"Connection: in Line {} has error={}   Connection".format(sys.exc_traceback.tb_lineno, e) )


			############# does not work on OSX	el capitan ssl lib too old	##########
			elif self.unfiCurl =="requests":
				if self.unifiControllerSession =="" or (time.time() - self.lastUnifiCookieRequests) > 100: # every 90 secs refresh cert
					self.unifiControllerSession	 = requests.Session()
					url	 = "https://"+self.unifiCloudKeyIP+":"+self.unifiCloudKeyPort+"/api/login"
					dataLogin = json.dumps({"username":self.unifiUserID,"password":self.unifiPassWd})
					resp  = self.unifiControllerSession.post(url, data = dataLogin, verify=False)
					if self.decideMyLog(u"Connection"): self.indiLOG.log(20,"Connection: "+ resp.text)
					self.lastUnifiCookieRequests =time.time()


				if data =={}: dataDict = ""
				else:		  dataDict = json.dumps(data)
				url = "https://"+self.unifiCloudKeyIP+":"+self.unifiCloudKeyPort+self.unifiApiWebPage+self.unifiCloudKeySiteName+"/"+pageString.strip("/")

				if self.decideMyLog(u"Connection"): self.indiLOG.log(20,"Connection: requests: "+url +"  "+ dataDict)
				if startText !="":					self.indiLOG.log(20,"Connection: requests: "+startText )
				try:
						if	 cmdType == "put":	 resp = self.unifiControllerSession.put(url,data = dataDict)
						elif cmdType == "post":	 resp = self.unifiControllerSession.post(url,data = dataDict)
						elif cmdType == "get":	 resp = self.unifiControllerSession.get(url,data = dataDict, stream=True)
						else:					 resp = self.unifiControllerSession.put(url,data = dataDict)
  
						try:

							jj = json.loads(resp.text)
						except :
							self.indiLOG.log(40,"executeCMDOnController has error, no json object returned: " + unicode(ret))
							return []
 

						if jj["meta"]["rc"] !="ok" :
							self.indiLOG.log(40,u"error:>> "+ unicode(resp) +" Reconnect")
							return []

						if self.decideMyLog(u"Connection"):	
							self.indiLOG.log(20,"Reconnect: executeCMDOnController resp.text:>>"+ resp.text[0:500]+".... <<" )

						if  jsonAction =="print":
							self.indiLOG.log(20,"Reconnect: executeCMDOnController info\n"+ json.dumps(jj["data"],sort_keys=True, indent=2) )
							return []

						if jsonAction =="returnData":
							self.writeJson(jj["data"], fName=self.indigoPreferencesPluginDir+"dict-Controller-"+pageString.replace("/","_").replace(" ","-").replace(":","=").strip("_")+".txt", sort=True, doFormat=True )
							return jj["data"]

						return []
				except	Exception, e:
					self.indiLOG.log(40,"in Line {} has error={}   Connection".format(sys.exc_traceback.tb_lineno, e) )


		except	Exception, e:
			self.indiLOG.log(40,"in Line {} has error={}   Connection".format(sys.exc_traceback.tb_lineno, e))
		return []


	####-----------------	   ---------
	def getSnapshotfromCamera(self, indigoCameraId, fileName):
		try:
			dev		= indigo.devices[int(indigoCameraId)]
			cmdR	= self.unfiCurl +" 'http://"+dev.states["ip"] +"/snap.jpeg' > "+ fileName
			if self.decideMyLog(u"Video"): self.indiLOG.log(20,"Video: getSnapshotfromNVR with: "+cmdR)
			ret 	= subprocess.Popen(cmdR, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()
			if self.decideMyLog(u"Video"): self.indiLOG.log(20,"Video: getSnapshotfromCamera response: "+str(ret))
			return "ok"
		except	Exception, e:
			self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			return "error:"+unicode(e)
		return " error"


	####-----------------	   ---------
	def getSnapshotfromNVR(self, indigoCameraId, width, fileName):

		try:
			camApiKey = indigo.devices[int(indigoCameraId)].states["apiKey"]
			url			= "http://"+self.ipnumberOfNVR +":7080/api/2.0/snapshot/camera/"+camApiKey+"?force=true&width="+str(width)+"&apiKey="+self.nvrVIDEOapiKey
			if self.unfiCurl.find("curl") > -1:
				cmdR	= self.unfiCurl+" -o '" + fileName +"'  '"+ url+"'"
				try:
					if self.decideMyLog(u"Video"): self.indiLOG.log(20,"Video: "+cmdR )
					ret = subprocess.Popen(cmdR, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()[1]
					try:
						fs1	 = ""
						fs	 = 0
						fs0	 = ""
						unit = ""
						if ret.find("\r")> -1: ret = ret.split("\r")
						else:                  ret = ret.split("\n")
						fs0  = ret[-1] # last line
						fs1  = fs0.split()[-1] # last number
						unit = fs1[-1] # strip last char
						fs  = int(fs1.strip("k").strip("m").strip("M"))
					except: fs = 0
					if fs == 0:
						self.indiLOG.log(40,u"getSnapshotfromNVR has error, no file returned: \n"+unicode(ret[1])+"  "+cmdR + "  Video error")
						return "error, no file returned"
					return "ok, bytes transfered: "+str(fs)+unit
				except	Exception, e:
					self.indiLOG.log(40,"in Line {} has error={}  Video error".format(sys.exc_traceback.tb_lineno, e))
				return "error:"+unicode(e)

			else:
				session = requests.Session()

				if self.decideMyLog(u"Video"): self.indiLOG.log(20,"Video: getSnapshotfromNVR login with: "+url)

				resp	= session.get(url, stream=True)
				if self.decideMyLog(u"Video"): self.indiLOG.log(20,"Video: getSnapshotfromNVR response: "+str(resp.status_code)+";   %d"%(len(resp.content)/1024)+"[kB]" )
				if str(resp.status_code) == "200":
					f = open(fileName,"wb")
					f.write(resp.content)
					f.close()
					unit=""
					try:
						ll = int(len(resp.content))
						if ll > 1024:
							ll /=1024
							unit="k"
							if ll > 1024:
								ll /=1024
								unit="M"
					except: ll = ""
					return "ok, bytes transfered: "+ str(ll)+unit
				return "error "+str(resp.status_code)
		except	Exception, e:
			self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return "error:"+unicode(e)



	####-----------------	   ---------
	def groupStatusINIT(self):
		try:	fID = indigo.variables["Unifi_Count_ALL_Home"].folderId
		except: fID = 0
		for group in  _GlobalConst_groupList:
			for tType in ["Home","Away","lastChange","name"]:
				varName="Unifi_Count_"+group+"_"+tType
				if varName not in self.varExcludeSQLList: self.varExcludeSQLList.append(varName)
				try:
					var = indigo.variables[varName]
				except:
					if varName.find("name")>-1: indigo.variable.create(varName,group+" change me to what YOU like",folder=fID)
					else:						indigo.variable.create(varName,"0",folder=fID)

		for tType in ["Home","Away","lastChange"]:
			varName="Unifi_Count_ALL_"+tType
			if varName not in self.varExcludeSQLList: self.varExcludeSQLList.append(varName)
			try:
				var = indigo.variables[varName]
			except:
				indigo.variable.create(varName,"0",folder=fID)

		try:	indigo.variable.create("Unifi_With_Status_Change",value="", folder=fID)
		except: pass
		try:	indigo.variable.create("Unifi_With_IPNumber_Change",value="", folder=fID)
		except: pass
		try:	indigo.variable.create("Unifi_New_Device",value="", folder=fID)
		except: pass

	####-----------------	   ---------
	def setGroupStatus(self, init=False):
		self.statusChanged = 0
		try:
			try:	fID = indigo.variables["Unifi_Count_ALL_Home"].folderId
			except: fID = 0

			triggerGroup= {}
			for group in self.groupStatusList:
				triggerGroup[group]={"allHome":False,"allWay":False,"oneHome":False,"oneAway":False}

			for group in  _GlobalConst_groupList:
				self.groupStatusList[group]["nAway"] = 0
				self.groupStatusList[group]["nHome"] = 0
			self.groupStatusListALL["nHome"] = 0
			self.groupStatusListALL["nAway"] = 0

			okList =[]


			for dev in indigo.devices.iter(self.pluginId):
				if "groupMember" not in dev.states: continue

				if dev.states["status"]=="up":
					self.groupStatusListALL["nHome"]	 +=1
				else:
					self.groupStatusListALL["nAway"]	 +=1

				if dev.states["groupMember"] == "": continue
				if not dev.enabled:	 continue
				okList.append(unicode(dev.id))
				props= dev.pluginProps
				gMembers = (dev.states["groupMember"].strip(",")).split(",")
				for group in _GlobalConst_groupList:
					if group in gMembers:
						self.groupStatusList[group]["members"][unicode(dev.id)] = True
						if dev.states["status"]=="up":
							if self.groupStatusList[group]["oneHome"] =="0":
								triggerGroup[group]["oneHome"] = True
								self.groupStatusList[group]["oneHome"]	 = "1"
							self.groupStatusList[group]["nHome"]	 +=1
						else:
							if self.groupStatusList[group]["oneAway"] =="0":
								triggerGroup[group]["oneAway"] = True
							self.groupStatusList[group]["oneAway"]	 = "1"
							self.groupStatusList[group]["nAway"]	 +=1

			for group in  _GlobalConst_groupList:
				removeList=[]
				for member in self.groupStatusList[group]["members"]:
					if member not in okList:
						removeList.append(member)
				for member in  removeList:
					del self.groupStatusList[group]["members"][member]


			for group in  _GlobalConst_groupList:
				if self.groupStatusList[group]["nAway"] == len(self.groupStatusList[group]["members"]):
					if self.groupStatusList[group]["allAway"] =="0":
						triggerGroup[group]["allAway"] = True
					self.groupStatusList[group]["allAway"]	 = "1"
					self.groupStatusList[group]["oneHome"]	 = "0"
				else:
					self.groupStatusList[group]["allAway"]	 = "0"

				if self.groupStatusList[group]["nHome"] == len(self.groupStatusList[group]["members"]):
					if self.groupStatusList[group]["allHome"] =="0":
						triggerGroup[group]["allHome"] = True
					self.groupStatusList[group]["allHome"]	 = "1"
					self.groupStatusList[group]["oneAway"]	 = "0"
				else:
					self.groupStatusList[group]["allHome"]	 = "0"


			# now extra variables
			for group in  _GlobalConst_groupList:
				if	not init:
					#try:
						varName="Unifi_Count_"+group+"_"
						varHomeV = indigo.variables[varName+"Home"].value
						varAwayV = indigo.variables[varName+"Away"].value
						if	varHomeV != unicode(self.groupStatusList[group]["nHome"]) or varAwayV != unicode(self.groupStatusList[group]["nAway"]) or len(indigo.variables["Unifi_Count_"+group+"_lastChange"].value) == 0 :
								indigo.variable.updateValue("Unifi_Count_"+group+"_lastChange", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
					#except:pass

				for tType in ["Home","Away"]:
					varName="Unifi_Count_"+group+"_"+tType
					gName="n"+tType
					try:
						var = indigo.variables[varName]
					except:
						indigo.variable.create(varName,"0",folder=fID)
						var = indigo.variables[varName]
					if var.value !=	 unicode(self.groupStatusList[group][gName]):
						indigo.variable.updateValue(varName,unicode(self.groupStatusList[group][gName]))


			if	not init:
				try:
					varName="Unifi_Count_ALL_"
					varHomeV = indigo.variables[varName+"Home"].value
					varAwayV = indigo.variables[varName+"Away"].value
					if varHomeV != unicode(self.groupStatusListALL["nHome"]) or varAwayV != unicode(self.groupStatusListALL["nAway"]) or len(indigo.variables["Unifi_Count_ALL_lastChange"].value) == 0:
						indigo.variable.updateValue("Unifi_Count_ALL_lastChange", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
				except:
					self.groupStatusINIT()

			for tType in ["Home","Away"]:
				varName="Unifi_Count_ALL_"+tType
				gName="n"+tType
				try:
					var = indigo.variables[varName]
				except:
					indigo.variable.create(varName,"0",folder=fID)
					var = indigo.variables[varName]
				if var.value != unicode(self.groupStatusListALL[gName]):
					indigo.variable.updateValue(varName,unicode(self.groupStatusListALL[gName]))

			#for group in  self.groupStatusList:
			#	 self.myLog( text=group+"  "+ unicode( self.groupStatusList[group]))
			#self.myLog( text="trigger list "+ unicode( self.triggerList))


			if	not init  and len(self.triggerList) > 0:
				for group in triggerGroup:
					for tType in triggerGroup[group]:
						#self.myLog( text=group+"-"+tType+"  trigger:"+unicode(triggerGroup[group][tType]))
						if triggerGroup[group][tType]:
							self.triggerEvent(group+"_"+tType)

		except	Exception, e:
			self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		return

######################################################################################
	# Indigo Trigger Start/Stop
######################################################################################

	####-----------------	 ---------
	def triggerStartProcessing(self, trigger):
#		self.myLog( text=u"BeaconData",u"<<-- entering triggerStartProcessing: %s (%d)" % (trigger.name, trigger.id) )iDeviceHomeDistance
		self.triggerList.append(trigger.id)
#		self.myLog( text=u"BeaconData",u"exiting triggerStartProcessing -->>")

	####-----------------	 ---------
	def triggerStopProcessing(self, trigger):
#		self.myLog( text=u"BeaconData",u"<<-- entering triggerStopProcessing: %s (%d)" % (trigger.name, trigger.id))
		if trigger.id in self.triggerList:
#			self.myLog( text=u"BeaconData",u"TRIGGER FOUND")
			self.triggerList.remove(trigger.id)
#		self.myLog( text=u"BeaconData", u"exiting triggerStopProcessing -->>")

	#def triggerUpdated(self, origDev, newDev):
	#	self.logger.log(4, u"<<-- entering triggerUpdated: %s" % origDev.name)
	#	self.triggerStopProcessing(origDev)
	#	self.triggerStartProcessing(newDev)


######################################################################################
	# Indigo Trigger Firing
######################################################################################

	####-----------------	 ---------
	def triggerEvent(self, eventId):
		#self.myLog( text=u"<<-- entering triggerEvent: %s " % eventId)
		for trigId in self.triggerList:
			trigger = indigo.triggers[trigId]
			#self.myLog( text=u"<<-- trigger "+ unicode(trigger)+"  eventId:"+ eventId)
			if trigger.pluginTypeId == eventId:
				#self.myLog( text=u"<<-- trigger exec")
				indigo.trigger.execute(trigger)
		return




	####-----------------setup empty dicts for pointers	 type, mac --> indigop and indigo --> mac,	type ---------
	def setStateupDown(self, dev):
		update=False
		try:
			upDown = ""
			props=dev.pluginProps
			if u"expirationTime" not in props:
				props[u"expirationTime"] = self.expirationTime
				update=True
			if u"useWhatForStatus" in props:
				if props[u"useWhatForStatus"] == u"WiFi":
					if u"useWhatForStatusWiFi" in props:
						if props[u"useWhatForStatusWiFi"] != "" and props[u"useWhatForStatusWiFi"] != u"Expiration":
							if props[u"useWhatForStatusWiFi"]in [u"IdleTime",u"Optimized",u"FastDown"]:
								if u"idleTimeMaxSecs" not in props:
									props[u"idleTimeMaxSecs"]= u"10"
									update=True
								upDown = u"WiFi" + "/" + props[u"useWhatForStatusWiFi"]+u"-idle:"+props[u"idleTimeMaxSecs"]
							else:
								upDown = u"WiFi" + "/" + props[u"useWhatForStatusWiFi"]
						else:
							upDown =  u"Wifi"
					else:
						upDown =  u"Wifi"

				elif props[u"useWhatForStatus"] == u"DHCP":
					if u"useAgeforStatusDHCP" in props and	props[u"useAgeforStatusDHCP"] != "" and props[u"useAgeforStatusDHCP"] != u"-1":
						upDown = u"DHCP" + "-age:" + props[u"useAgeforStatusDHCP"]
					else:
						upDown = u"DHCP"

				elif props[u"useWhatForStatus"] == u"OptDhcpSwitch":
					upDown ="OPT: "
					if u"useAgeforStatusDHCP" in props and	props[u"useAgeforStatusDHCP"] != "" and props[u"useAgeforStatusDHCP"] != u"-1":
						upDown += u"DHCP" + "-age:" + props[u"useAgeforStatusDHCP"]+"  "
					else:
						upDown += u"DHCP "

					if u"useupTimesforStatusSWITCH" in props and props[u"useupTimeforStatusSWITCH"]:
							upDown += u"SWITCH" + u"/upTime-notchgd"
					else:
							upDown += u"SWITCH"

				elif props[u"useWhatForStatus"] == u"SWITCH":
					if u"useupTimesforStatusSWITCH" in props and props[u"useupTimeforStatusSWITCH"]:
							upDown += u"SWITCH" + u"/upTime-notchgd"
					else:
							upDown += u"SWITCH"

				upDown +=  u"-exp:"+ unicode(self.getexpT(props)).split(".")[0]
				self.addToStatesUpdateList(dev.id,u"upDownSetting", upDown)

			if u"expirationTime" not in props:
				props[u"expirationTime"] = self.expirationTime
				update=True

			if u"AP" in dev.states:
				if dev.states[u"AP"].find("-") ==-1 :
					newAP= dev.states[u"AP"]+"-"
					dev.updateStateOnServer(u"AP",newAP)


		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		if update:
			dev.replacePluginPropsOnServer(props)
		return


	####-----------------setup empty dicts for pointers	 type, mac --> indigop and indigo --> mac,	type ---------
	def setupStructures(self, xType, dev, MAC,init=False):
		devIds =""
		try:
			if xType == u"UN" and self.testIgnoreMAC(MAC):
				if MAC in self.MAC2INDIGO[xType]:
					del self.MAC2INDIGO[xType][MAC]
				return
			devIds = unicode(dev.id)
			if devIds not in self.xTypeMac:
				self.xTypeMac[devIds]={"xType":"", "MAC":""}
			self.xTypeMac[devIds]["xType"] = xType
			self.xTypeMac[devIds][u"MAC"]	= MAC

			if xType not in self.MAC2INDIGO:
				self.MAC2INDIGO[xType]={}

			if MAC not in self.MAC2INDIGO[xType]:
			   self.MAC2INDIGO[xType][MAC] = {}

			self.MAC2INDIGO[xType][MAC]["devId"] = dev.id
			if u"ipNumber" not in self.MAC2INDIGO[xType][MAC]:
				if u"ipNumber" in dev.states:
					self.MAC2INDIGO[xType][MAC][u"ipNumber"] = dev.states[u"ipNumber"]

			try:	self.MAC2INDIGO[xType][MAC][u"lastUp"] == float(self.MAC2INDIGO[xType][MAC][u"lastUp"])
			except: self.MAC2INDIGO[xType][MAC][u"lastUp"] =0.


		except	Exception, e:
			self.indiLOG.log(40,"in Line {} has error={}\n{}    {}     {}   {}".format(sys.exc_traceback.tb_lineno, e, unicode(xType), devIds, unicode(MAC), unicode(self.MAC2INDIGO)) )
			time.sleep(300)

		if xType ==u"UN":
				self.MAC2INDIGO[xType][MAC][u"AP"]			   = dev.states[u"AP"].split("-")[0]
				self.MAC2INDIGO[xType][MAC][u"lastWOL"]		   = 0.

				for item in [u"inListWiFi",u"inListDHCP",]:
					if item not in self.MAC2INDIGO[xType][MAC]:
							self.MAC2INDIGO[xType][MAC][item] = False
				for item in [u"GHz",u"idleTimeWiFi",u"upTimeWifi",u"upTimeDHCP"]:
					if item not in self.MAC2INDIGO[xType][MAC]:
							self.MAC2INDIGO[xType][MAC][item] = ""

				for ii in range(_GlobalConst_numberOfSW):
					for item in [u"inListSWITCH_"]:
						if item+unicode(ii) not in self.MAC2INDIGO[xType][MAC]:
							self.MAC2INDIGO[xType][MAC][item+unicode(ii)] = -1
					for item in [u"ageSWITCH_",u"upTimeSWITCH_"]:
						if item+unicode(ii) not in self.MAC2INDIGO[xType][MAC]:
							self.MAC2INDIGO[xType][MAC][item+unicode(ii)] = ""


		if xType ==u"SW":
			if "ports" not in self.MAC2INDIGO[xType][MAC]:
				self.MAC2INDIGO[xType][MAC][u"ports"] = {}
			if u"upTime" not in self.MAC2INDIGO[xType][MAC]:
				self.MAC2INDIGO[xType][MAC][u"upTime"] = ""

		elif xType ==u"AP":
			pass

		elif xType ==u"GW":
			pass

		elif xType ==u"NB":
			if u"age" not in self.MAC2INDIGO[xType][MAC]:
				self.MAC2INDIGO[xType][MAC][u"age"] = ""



	###########################	   MAIN LOOP  ############################
	####-----------------init  main loop ---------
	def fixBeforeRunConcurrentThread(self):

		nowDT = datetime.datetime.now()
		self.lastMinute		= nowDT.minute
		self.lastHour		= nowDT.hour
		self.logQueue		= Queue.Queue()
		self.logQueueDict	= Queue.Queue()
		self.apDict			= {}
		self.countLoop		= 0
		self.upDownTimers	= {}
		self.xTypeMac		= {}
		self.broadcastIP	= "9.9.9.255"

		self.writeJson(dataVersion, fName=self.indigoPreferencesPluginDir + "dataVersion")

		## if video enabled
		if self.VIDEOEnabled and self.vmMachine !="":
			self.buttonVboxActionStartCALLBACK()

######## this for fixing the change from mac to MAC in states
		self.MacToNamesOK = True
		if self.enableMACtoVENDORlookup:
			self.indiLOG.log(20,u"..getting missing vendor names for MAC #")
		self.MAC2INDIGO = {}
		self.readMACdata()
		delDEV = {}
		for dev in indigo.devices.iter(self.pluginId):
			if dev.deviceTypeId in[u"client",u"camera"]: continue
			if u"status" not in dev.states:
				self.indiLOG.log(20,dev.name + u" has no status")
				continue
			else:
				if "onOffState" in dev.states and  ( (dev.states["status"] in ["up","rec","ON"]) != dev.states["onOffState"] ):
							dev.updateStateOnServer("onOffState", value= dev.states["status"] in ["up","rec","ON"], uiValue=dev.states["displayStatus"])

			props= dev.pluginProps
			goodDevice = True
			devId = unicode(dev.id)

			if u"MAC" in dev.states:
				MAC = dev.states[u"MAC"]
				if dev.states[u"MAC"] == "":
					if dev.address != "":
						try:
							self.addToStatesUpdateList(dev.id,u"MAC", dev.address)
							MAC = dev.address
						except:
							goodDevice = False
							self.indiLOG.log(20,dev.name + u" no MAC # deleting")
							delDEV[devId]=True
							continue
				if dev.address != MAC:
					props["address"] = MAC
					dev.replacePluginPropsOnServer(props)

			if self.MacToNamesOK and u"vendor" in dev.states:
				if (dev.states[u"vendor"] == "" or dev.states[u"vendor"].find("<html>") >-1 ) and goodDevice:
					vendor = self.getVendortName(MAC)
					if vendor != "":
						self.addToStatesUpdateList(dev.id,u"vendor", vendor)
					if	dev.states[u"vendor"].find("<html>") >-1   and	 vendor =="" :
						self.addToStatesUpdateList(dev.id,u"vendor", "")


			if dev.deviceTypeId == u"UniFi":
				#self.myLog( text=u" adding to MAC2INDIGO " + MAC)
				self.setupStructures(u"UN", dev, MAC)


			if dev.deviceTypeId == "Device-AP":
				self.setupStructures(u"AP", dev, MAC)

			if dev.deviceTypeId.find("Device-SW")>-1:
				self.setupStructures(u"SW", dev, MAC)

			if dev.deviceTypeId == u"neighbor":
				self.setupStructures(u"NB", dev, MAC)

			if dev.deviceTypeId == u"gateway":
				self.setupStructures(u"GW", dev, MAC)

			self.setImageAndStatus(dev, dev.states[u"status"], force=True)

			if u"created" in dev.states and dev.states[u"created"] == "":
				self.addToStatesUpdateList(dev.id,u"created", nowDT.strftime(u"%Y-%m-%d %H:%M:%S"))


			self.setStateupDown(dev)

			self.executeUpdateStatesList()

		for devid in delDEV:
			 sself.indiLOG.log(20," deleting , bad mac "+ devid )
			 indigo.device.delete[int(devid)]



		## remove old non exiting MAC / indigo devices
		for xType in self.MAC2INDIGO:
			if "" in self.MAC2INDIGO[xType]:
				del self.MAC2INDIGO[xType][""]
			delXXX = {}
			for MAC in self.MAC2INDIGO[xType]:
				if len(MAC) < 16:
					delXXX[MAC] = True
					continue
				try: indigo.devices[self.MAC2INDIGO[xType][MAC][u"devId"]]
				except	Exception, e:
					self.indiLOG.log(20,"removing indigo id: "+ unicode(self.MAC2INDIGO[xType][MAC][u"devId"])+"  from internal list" )
					time.sleep(1)
					delXXX[MAC] = True
			for MAC in delXXX:
				del self.MAC2INDIGO[xType][MAC]
			# some cleanup it is now upTime xxx  not uptime xxx
			for MAC in self.MAC2INDIGO[xType]:
				delXXX={}
				for yy in self.MAC2INDIGO[xType][MAC]:
					if yy.find("uptime") >-1:
						delXXX[yy]=True
				for yy in delXXX:
					del self.MAC2INDIGO[xType][MAC][yy]
		delXXX = {}

		for devId  in self.xTypeMac:
			try:	 dev = indigo.devices[int(devId)]
			except	Exception, e:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				if unicode(e).find("timeout") >-1:
					self.sleep(20)
					return False
				delXXX[devId]=True
			MAC =  self.xTypeMac[devId]["MAC"]


			if self.xTypeMac[devId]["xType"]=="SW":
				ipN = dev.states["ipNumber"]
				sw	= dev.states["switchNo"]
				try:
					sw = int(sw)
					if ipN != self.ipNumbersOfSWs[sw]:
						dev.updateStateOnServer("ipNumber",self.ipNumbersOfSWs[sw])
				except:
					if self.isValidIP(ipN):
						for ii in range(len(self.ipNumbersOfSWs)):
							if self.ipNumbersOfSWs[ii] == ipN:
								dev.updateStateOnServer("apNo",ii)
								break


			if self.xTypeMac[devId]["xType"]=="AP":
				ipN = dev.states["ipNumber"]
				sw	= dev.states["apNo"]
				try:
					sw = int(sw)
					if ipN != self.ipNumbersOfAPs[sw]:
						dev.updateStateOnServer("ipNumber",self.ipNumbersOfAPs[sw])
				except:
					if self.isValidIP(ipN):
						for ii in range(len(self.ipNumbersOfAPs)):
							if self.ipNumbersOfAPs[ii] == ipN:
								dev.updateStateOnServer("apNo",ii)
								break



		for devId in delXXX:
			del self.xTypeMac[devId]
		delXXX = {}

		self.saveMACdata()

		self.lastSecCheck	= time.time()

		self.readupDownTimers()
		self.saveupDownTimers()

		##start accepting staus = DOWN in 30secs
		self.pluginStartTime = time.time() +30

		self.pluginState   = "run"

		self.checkForBlockedClients(force=True)
		self.addFirstSeenToStates()

		self.getNVRIntoIndigo(force= True)
		self.getCamerasIntoIndigo(force=True)
		self.saveCameraEventsStatus=True; self.saveCamerasStats(force=False)

		###########	 set up threads	 ########

				### start video logfile listening
		self.trVDLog = ""
		if self.VIDEOEnabled:
			self.indiLOG.log(20,u"..starting threads for VIDEO NVR log event capture")
			self.trVDLog  = threading.Thread(name=u'self.getMessages', target=self.getMessages, args=(self.ipnumberOfNVR,u"VD",u"VDtail",500,))
			self.trVDLog.start()
			self.sleep(0.2)


		try:
			self.trAPLog  = {}
			self.trAPDict = {}
			nsleep= 1
			if self.NumberOFActiveAP > 0:
				self.indiLOG.log(20,u"..starting threads for %d APs %d sec apart (MSG-log and db-DICT)" %(self.NumberOFActiveAP,nsleep) )
				for ll in range(_GlobalConst_numberOfAP):
					if self.APsEnabled[ll]:
						ipn = self.ipNumbersOfAPs[ll]
						self.broadcastIP = ipn
						if self.decideMyLog(u"Logic"): self.indiLOG.log(20,u"START: AP Thread # {}   {}".format(ll, ipn) )
						if self.commandOnServer["APtail"].find("off") ==-1: 
							self.trAPLog[unicode(ll)] = threading.Thread(name=u'self.getMessages', target=self.getMessages, args=(ipn,ll,u"APtail",float(self.readDictEverySeconds[u"AP"])*2,))
							self.trAPLog[unicode(ll)].start()
							self.sleep(nsleep)
						self.trAPDict[unicode(ll)] = threading.Thread(name=u'self.getMessages', target=self.getMessages, args=(ipn,ll,u"APdict",float(self.readDictEverySeconds[u"AP"])*2,))
						self.trAPDict[unicode(ll)].start()
						self.sleep(nsleep)


		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.stop = copy.copy(self.ipNumbersOfAPs)
			self.quitNow = u"stop"
			return False



		if self.UGAEnabled:
			self.indiLOG.log(20,u"..starting threads for GW (MSG-log and db-DICT)")
			self.broadcastIP = self.ipnumberOfUGA
			if self.commandOnServer["GWtail"].find("off") ==-1: 
				self.trGWLog  = threading.Thread(name=u'self.getMessages', target=self.getMessages, args=(self.ipnumberOfUGA,u"GW",u"GWtail",float(self.readDictEverySeconds[u"GW"])*2,))
				self.trGWLog.start()
				self.sleep(1)
			self.trGWDict = threading.Thread(name=u'self.getMessages', target=self.getMessages, args=(self.ipnumberOfUGA,u"GW",u"GWdict",float(self.readDictEverySeconds[u"GW"])*2,))
			self.trGWDict.start()


		try:
			self.trSWLog = {}
			self.trSWDict = {}
			if self.NumberOFActiveSW > 0:
				self.sleep(1)
				nsleep = max(1,12 - self.NumberOFActiveSW)
				minCheck = float(self.readDictEverySeconds[u"SW"])*2.
				if self.NumberOFActiveSW > 1:
					minCheck = 2.* float(self.readDictEverySeconds[u"SW"]) / self.NumberOFActiveSW
				else:
					minCheck = 2.* float(self.readDictEverySeconds[u"SW"])
				self.indiLOG.log(20,u"..starting threads for {} SWs {} sec apart (db-DICT only)".format(self.NumberOFActiveSW,nsleep) )
				for ll in range(_GlobalConst_numberOfSW):
					if self.SWsEnabled[ll]:
						ipn = self.ipNumbersOfSWs[ll]
						if self.broadcastIP !="": self.broadcastIP = ipn
						if self.decideMyLog(u"Logic"): self.indiLOG.log(20,u"START SW Thread tr # {}   {}".format(ll, ipn))
	 #					 self.trSWLog[unicode(ll)] = threading.Thread(name='self.getMessages', target=self.getMessages, args=(ipn, ll, "SWtail",float(self.readDictEverySeconds[u"SW"]*2,))
	 #					 self.trSWLog[unicode(ll)].start()
						self.trSWDict[unicode(ll)] = threading.Thread(name=u'self.getMessages', target=self.getMessages, args=(ipn, ll, u"SWdict",minCheck,))
						self.trSWDict[unicode(ll)].start()
						if self.NumberOFActiveSW > 1: self.sleep(nsleep)

		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.stop = copy.copy(self.ipNumbersOfSWs)
			self.quitNow = u"stop"
			return False


		try:
			ip = self.broadcastIP.split(".")
			self.broadcastIP = ip[0]+"."+ip[1]+"."+ip[2]+".255"
		except:
			pass


		return True




	###########################	   cProfile stuff   ############################ START
	####-----------------  ---------
	def getcProfileVariable(self):

		try:
			if self.timeTrVarName in indigo.variables:
				xx = (indigo.variables[self.timeTrVarName].value).strip().lower().split("-")
				if len(xx) ==1:
					cmd = xx[0]
					pri = ""
				elif len(xx) == 2:
					cmd = xx[0]
					pri = xx[1]
				else:
					cmd = "off"
					pri  = ""
				self.timeTrackWaitTime = 20
				return cmd, pri
		except	Exception, e:
			pass

		self.timeTrackWaitTime = 60
		return "off",""

	####-----------------            ---------
	def printcProfileStats(self,pri=""):
		try:
			if pri !="": pick = pri
			else:		 pick = 'cumtime'
			outFile		= self.indigoPreferencesPluginDir+"timeStats"
			indigo.server.log(" print time track stats to: {}.dump / txt  with option:{} ".format(outFile, pick) )
			self.pr.dump_stats(outFile+".dump")
			sys.stdout 	= open(outFile+".txt", "w")
			stats 		= pstats.Stats(outFile+".dump")
			stats.strip_dirs()
			stats.sort_stats(pick)
			stats.print_stats()
			sys.stdout = sys.__stdout__
		except: pass
		"""
		'calls'			call count
		'cumtime'		cumulative time
		'file'			file name
		'filename'		file name
		'module'		file name
		'pcalls'		primitive call count
		'line'			line number
		'name'			function name
		'nfl'			name/file/line
		'stdname'		standard name
		'time'			internal time
		"""

	####-----------------            ---------
	def checkcProfile(self):
		try:
			if time.time() - self.lastTimegetcProfileVariable < self.timeTrackWaitTime:
				return
		except:
			self.cProfileVariableLoaded = 0
			self.do_cProfile  			= "x"
			self.timeTrVarName 			= "enableTimeTracking_"+self.pluginShortName
			indigo.server.log("testing if variable {} is == on/off/print-option to enable/end/print time tracking of all functions and methods (option:'',calls,cumtime,pcalls,time)".format(self.timeTrVarName))

		self.lastTimegetcProfileVariable = time.time()

		cmd, pri = self.getcProfileVariable()
		if self.do_cProfile != cmd:
			if cmd == "on":
				if  self.cProfileVariableLoaded ==0:
					indigo.server.log("======>>>>   loading cProfile & pstats libs for time tracking;  starting w cProfile ")
					self.pr = cProfile.Profile()
					self.pr.enable()
					self.cProfileVariableLoaded = 2
				elif  self.cProfileVariableLoaded >1:
					self.quitNow = " restart due to change  ON  requested for print cProfile timers"
			elif cmd == "off" and self.cProfileVariableLoaded >0:
					self.pr.disable()
					self.quitNow = " restart due to  OFF  request for print cProfile timers "
		if cmd == "print"  and self.cProfileVariableLoaded >0:
				self.pr.disable()
				self.printcProfileStats(pri=pri)
				self.pr.enable()
				indigo.variable.updateValue(self.timeTrVarName,"done")

		self.do_cProfile = cmd
		return

	####-----------------            ---------
	def checkcProfileEND(self):
		if self.do_cProfile in["on","print"] and self.cProfileVariableLoaded >0:
			self.printcProfileStats(pri="")
		return
	###########################	   cProfile stuff   ############################ END

	####-----------------	 ---------
	def setSqlLoggerIgnoreStatesAndVariables(self):
		try:
			if self.indigoVersion <  7.4:                             return 
			if self.indigoVersion == 7.4 and self.indigoRelease == 0: return 
			#tt = ["beacon",              "rPI","rPI-Sensor","BLEconnect","sensor"]

			outOffV = ""
			for v in self.varExcludeSQLList:
					var = indigo.variables[v]
					sp = var.sharedProps
					#self.indiLOG.log(30,"setting /testing off: Var: {} sharedProps:{}".format(var.name.encode("utf8"), sp) )
					if "sqlLoggerIgnoreChanges" in sp and sp["sqlLoggerIgnoreChanges"] == "true": 
						continue
					#self.indiLOG.log(30,"====set to off ")
					outOffV += var.name+"; "
					sp["sqlLoggerIgnoreChanges"] = "true"
					var.replaceSharedPropsOnServer(sp)

			if len(outOffV) > 0: 
				self.indiLOG.log(20," \n")
				self.indiLOG.log(20,"switching off SQL logging for variables\n :{}".format(outOffV.encode("utf8")) )
				self.indiLOG.log(20,"switching off SQL logging for variables END\n")
		except Exception, e:
			self.indiLOG.log(40, u"error in  Line# {} ;  error={}".format(sys.exc_traceback.tb_lineno, e))

		return 



####-----------------   main loop          ---------
	def runConcurrentThread(self):
		### self.indiLOG.log(50,u"CLASS: Plugin")

		self.setSqlLoggerIgnoreStatesAndVariables()

		self.indiLOG.log(20,u"runConcurrentThread.....")

		self.dorunConcurrentThread()
		self.checkcProfileEND()

		self.sleep(1)
		if self.quitNow !="":
			indigo.server.log( u"runConcurrentThread stopping plugin due to:  ::::: {} :::::".format(self.quitNow))
			serverPlugin = indigo.server.getPlugin(self.pluginId)
			serverPlugin.restart(waitUntilDone=False)
		return

####-----------------   main loop            ---------
	def dorunConcurrentThread(self):

		indigo.server.log(u" start   runConcurrentThread, initializing loop settings and threads ..")

		if not self.fixBeforeRunConcurrentThread():
			self.indiLOG.log(40,u"..error in startup")
			self.sleep(10)
			return

		indigo.server.savePluginPrefs()

		self.lastHourCheck		= datetime.datetime.now().hour
		self.lastMinuteCheck	= datetime.datetime.now().minute
		self.lastMinute10Check	= datetime.datetime.now().minute/10
		self.pluginStartTime 	= time.time()
		indigo.server.log( u"initialized ... looping")
		try:
			self.quitNow = ""
			while self.quitNow == "":
				self.sleep(self.loopSleep)
				self.countLoop += 1
				ret = self.doTheLoop()
				if ret !="ok":
					self.indiLOG.log(20,u"LOOP   return break: >>"+ret+"<<")
					break
		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		self.postLoop()

		return


	###########################	   exec the loop  ############################
	####-----------------	 ---------
	def doTheLoop(self):

		if self.checkforUnifiSystemDevicesState == "validateConfig" or \
		  (self.checkforUnifiSystemDevicesState == "start" and (time.time() -self.pluginStartTime) > 30):
			self.checkForNewUnifiSystemDevices()
			if self.checkforUnifiSystemDevicesState == "reboot":
				self.quitNow ="new devices"
				self.checkforUnifiSystemDevicesState =""
				return "new Devices"

		if self.pendingCommand != []:
			if "getCamerasFromNVR-print" in self.pendingCommand: self.getCamerasFromNVR(doPrint = True, action=["system","cameras"])
			if "getCamerasIntoIndigo"	 in self.pendingCommand: self.getCamerasIntoIndigo(force = True)
			if "getConfigFromNVR"		 in self.pendingCommand: self.getNVRIntoIndigo(force = True); self.getCamerasIntoIndigo(force = True)
			if "saveCamerasStats"		 in self.pendingCommand: self.saveCameraEventsStatus = True;  self.saveCamerasStats(force = True)
			self.pendingCommand =[]

		self.getCamerasIntoIndigo(periodCheck = True)
		self.saveCamerasStats()
		self.saveDataStats()
		self.saveMACdata()
		part = u"main"+unicode(random.random()); self.blockAccess.append(part)
		for ii in range(90):
			if len(self.blockAccess) == 0 or self.blockAccess[0] == part: break # "my turn?
			self.sleep(0.1)
		if ii >= 89: self.blockAccess = [] # for safety if too long reset list

		## check for expirations etc

		self.checkOnChanges()
		self.executeUpdateStatesList()

		self.periodCheck()
		self.executeUpdateStatesList()
		self.sendUpdatetoFingscanNOW()
		if	 self.statusChanged ==1:  self.setGroupStatus()
		elif self.statusChanged ==2:  self.setGroupStatus(init=True)


		if len(self.devNeedsUpdate) > 0:
			for devId in self.devNeedsUpdate:
				try:
					##self.myLog( text=" updating devId:"+ unicode(devId))
					dev = indigo.devices[devId]
					self.setStateupDown(dev)
				except:
					pass
			self.devNeedsUpdate = []
			self.saveupDownTimers()
			self.setGroupStatus(init=True)

		self.executeUpdateStatesList()
		if len(self.sendBroadCastEventsList) >0: self.sendBroadCastNOW()

		if len(self.blockAccess)>0:	 del self.blockAccess[0]



		if self.lastMinuteCheck != datetime.datetime.now().minute:
			self.lastMinuteCheck = datetime.datetime.now().minute
			self.statusChanged = max(1,self.statusChanged)

			if self.VIDEOEnabled and self.vmMachine !="":
				if "VDtail" in self.msgListenerActive and time.time() - self.msgListenerActive["VDtail"] > 600: # no recordings etc for 10 minutes, reissue mount command
					self.msgListenerActive["VDtail"] = time.time()
					self.buttonVboxActionStartCALLBACK()

			if self.lastMinute10Check != (datetime.datetime.now().minute)/10:
				self.lastMinute10Check = datetime.datetime.now().minute/10
				self.checkforUnifiSystemDevicesState = "10minutes"
				self.checkForNewUnifiSystemDevices()
				self.checkInListSwitch()

				if self.checkforUnifiSystemDevicesState == "reboot":
					self.quitNow ="new devices"
					self.checkforUnifiSystemDevicesState =""
					return "new devices"


				if self.lastHourCheck != datetime.datetime.now().hour:
					self.lastHourCheck = datetime.datetime.now().hour
					if self.indigoVersion < 7.3:
						VC.versionCheck(self.pluginId,self.pluginVersion,indigo,13,45,printToLog="log")
					self.addFirstSeenToStates()
					self.saveupDownTimers()
					if self.lastHourCheck ==1: # recycle at midnight
						try:
							fID =	indigo.variables["Unifi_Count_ALL_lastChange"].folderId
							try:	indigo.variable.delete("Unifi_With_Status_Change")
							except: pass
							try:	indigo.variable.create("Unifi_With_Status_Change",value="", folder=fID)
							except: pass
						except:		pass
		self.checkForBlockedClients()
		return "ok"

	###########################	   after the loop  ############################
	####-----------------	 ---------
	def postLoop(self):

		self.pluginState   = "stop"

		if self.quitNow == "": self.quitNow = u" restart / self.stop requested "
		if self.quitNow == u"config changed":
			self.resetDataStats(calledFrom="postLoop")

		if True:
			for ll in range(len(self.SWsEnabled)):
				try: 	self.trSWLog[unicode(ll)].join()
				except: pass
				try: 	self.trSWDict[unicode(ll)].join()
				except: pass
			for ll in range(len(self.APsEnabled)):
				try: 	self.trAPLog[unicode(ll)].join()
				except: pass
				try: 	self.trAPDict[unicode(ll)].join()
				except: pass

		try: 	self.trGWLog.join()
		except: pass
		try: 	self.trGWDict.join()
		except: pass
		try: 	self.trVDLog.join()
		except: pass

		## kill all expect "uniFi" programs
		self.killIfRunning("", "")

		self.saveupDownTimers()




	####-----------------	 ---------
	def saveupDownTimers(self):
		try:
			f = open(self.indigoPreferencesPluginDir+"upDownTimers","w")
			f.write(json.dumps(self.upDownTimers))
			f.close()
		except	Exception, e:
			self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	####-----------------	 ---------
	def readupDownTimers(self):
		try:
			f = open(self.indigoPreferencesPluginDir+"upDownTimers","r")
			self.upDownTimers = json.loads(f.read())
			f.close()
		except:
			self.upDownTimers ={}
			try:
				f.close()
			except:
				pass

	####-----------------	 ---------
	def checkOnChanges(self,):
		xType	= u"UN"
		try:
			if self.upDownTimers =={}: return
			deldev={}

			for devid in self.upDownTimers:
				try:
					dev= indigo.devices[int(devid)]
				except	Exception, e:
					if unicode(e).find("timeout waiting") > -1:
						self.indiLOG.log(40,"in Line {} has error={}\ncommunication to indigo is interrupted".format(sys.exc_traceback.tb_lineno, e))
						return
					if unicode(e).find("not found in database") >-1:
						deldev[devid] =1
						continue
					self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					return

				props=dev.pluginProps
				expT =self.getexpT(props)
				dt	= time.time() - expT
				dtDOWN = time.time() -	self.upDownTimers[devid][u"down"]
				dtUP   = time.time() -	self.upDownTimers[devid][u"up"]

				if dev.states[u"status"] !="up": newStat = u"down"
				else:							 newStat = u"up"
				if self.upDownTimers[devid][u"down"] > 10.:
					if dtDOWN < 2: continue # ignore and up-> in the last 2 secs to avoid constant up-down-up
					if self.doubleCheckWithPing(newStat,dev.states["ipNumber"], props,dev.states[u"MAC"],"Logic", "checkOnChanges", "CHAN-WiF-Pg","UN") ==0:
							deldev[devid] = 1
							continue
					if u"useWhatForStatusWiFi" in props and props[u"useWhatForStatusWiFi"] in [u"FastDown",u"Optimized"]:
						if dtDOWN > 10. and dev.states[u"status"] == u"up":
							self.setImageAndStatus(dev, "down", ts=dt - 0.1, fing=True, level=1, text1= dev.name.ljust(30) + u" status was up	changed period WiFi, expT= %4.1f"%expT+"  dt= %4.1f"%dt, iType=u"CHAN-WiFi",reason="FastDown")
							self.MAC2INDIGO[xType][dev.states["MAC"]][u"lastUp"] = time.time() - expT
							deldev[devid] = 1
							continue
					if dtDOWN >4:
						deldev[devid] = 1
				if self.upDownTimers[devid][u"up"] > 10.:
					if dtUP < 2: continue # ingnore and up-> in the last 2 secs to avoid constant up-down-up
					deldev[devid] = 1
				if self.upDownTimers[devid][u"down"] == 0. and self.upDownTimers[devid][u"up"] ==0.:
					deldev[devid] = 1

			for devid in deldev:
				 del self.upDownTimers[devid]

		except	Exception, e:
			self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		return


	####-----------------	 ---------
	def getexpT(self,props):
		try:
			expT = self.expirationTime
			if u"expirationTime" in props and props[u"expirationTime"] != u"-1":
				try:
					expT = float(props[u"expirationTime"])
				except:
					pass
		except:
		   pass
		return expT

		####-----------------  check things every minute / xx minute / hour once a day ..  ---------

	####-----------------	 ---------
	def periodCheck(self):
		try:

			if	self.countLoop < 10:					return
			if time.time() - self.pluginStartTime < 70: return
			changed = False

			if self.countLoop%2000 == 0: self.setSqlLoggerIgnoreStatesAndVariables()

			self.checkcProfile()

			self.getNVRIntoIndigo()
			self.getCamerasIntoIndigo(periodCheck = True)
			self.saveCamerasStats()
			self.saveDataStats()
			self.saveMACdata()

			for dev in indigo.devices.iter(self.pluginId):

				try:
					if dev.deviceTypeId == u"camera": continue
					if dev.deviceTypeId == u"NVR": continue
					if "MAC" not in dev.states: continue

					props = dev.pluginProps
					devid = unicode(dev.id)

					MAC		= dev.states[u"MAC"]
					if dev.deviceTypeId == u"UniFi" and self.testIgnoreMAC(MAC, fromSystem="periodCheck") : continue

					if unicode(devid) not in self.xTypeMac:
						if dev.deviceTypeId == u"UniFi":
							self.setupStructures(u"UN", dev, MAC)
						if dev.deviceTypeId == "Device-AP":
							self.setupStructures(u"AP", dev, MAC)
						if dev.deviceTypeId.find("Device-SW")>-1:
							self.setupStructures(u"SW", dev, MAC)
						if dev.deviceTypeId == u"neighbor":
							self.setupStructures(u"NB", dev, MAC)
						if dev.deviceTypeId == u"gateway":
							self.setupStructures(u"GW", dev, MAC)
					xType	= self.xTypeMac[devid]["xType"]

					expT= self.getexpT(props)
					try:
						lastUpTT   = self.MAC2INDIGO[xType][MAC][u"lastUp"]
					except:
						lastUpTT = time.time()

					if dev.deviceTypeId == u"UniFi":
						ipN = dev.states[u"ipNumber"]



						# check for supended status, if sup : set, if back reset susp status
						if ipN in self.suspendedUnifiSystemDevicesIP:
							## check if we need to reset suspend after 300 secs
							if (time.time() - self.suspendedUnifiSystemDevicesIP[ipN] >10 and self.checkPing(ipN,nPings=2,countPings =2, waitForPing=0.5, calledFrom="PeriodCheck") == 0) :
									self.delSuspend(ipN)
									lastUpTT = time.time()
									self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
									self.indiLOG.log(20,dev.name + u" is back from suspended status")
							else:
								if dev.states[u"status"] != "susp":
									self.setImageAndStatus(dev, "susp", oldStatus=dev.states[u"status"],ts=time.time(), fing=False, level=1, text1= dev.name.ljust(30) + u" status "  + status.ljust(10) +";  set to susp", iType=u"PER-susp",reason=u"Period Check susp "+status)
									self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
									changed = True
								continue


						dt = time.time() - lastUpTT
						if u"useWhatForStatus" in props:
							if props[u"useWhatForStatus"] == "WiFi":
								suffixN = "WiFi"

								######### do WOL / ping	  START ########################
								if "useWOL" in props and props["useWOL"] !="0":
									if "lastWOL" not in self.MAC2INDIGO[xType][MAC]:
										self.MAC2INDIGO[xType][MAC]["lastWOL"]	= 0.
									if time.time() - self.MAC2INDIGO[xType][MAC]["lastWOL"] > float(props["useWOL"]):
										if dt < expT:	# if UP do minimal broadcast
											waitBeforePing = 0 # do a quick ping
											waitForPing	   = 1 # mSecs =  do not wait
											nBC			   = 1 # # of broadcasts
											nPings		   = 0
											waitAfterPing  = 0.0
										elif dt < 2*expT:			# if down wait between BC and ping,	 wait for ping to answer and do 2 BC
											waitBeforePing = 0.3 # secs
											waitForPing	   = 500 # msecs
											waitAfterPing  = 0.3
											nBC			   = 2
											nPings		   = 2
										else:					   # expired, do a quick bc
											waitBeforePing = 0.0 # secs
											waitForPing	   = 10 # msecs
											nBC			   = 1
											nPings		   = 0
											waitAfterPing  = 0.0
										if self.sendWakewOnLanAndPing( MAC, ipN, nBC=nBC, waitForPing=waitForPing, countPings=1, waitAfterPing=waitAfterPing, waitBeforePing=waitBeforePing, nPings=nPings, calledFrom="periodCheck") ==0:
											lastUpTT = time.time()
											self.MAC2INDIGO[xType][MAC][u"lastUp"] = lastUpTT
										self.MAC2INDIGO[xType][MAC]["lastWOL"]	= time.time()
								######### do WOL / ping	  END  ########################

								if u"useWhatForStatusWiFi" not in props or	(u"useWhatForStatusWiFi" in props and props[u"useWhatForStatusWiFi"] != u"FastDown"):

									if (devid in self.upDownTimers	and time.time() -  self.upDownTimers[devid][u"down"] > expT ) or (dt > 1 * expT) :
										if	  dt <						 1 * expT: status = u"up"
										elif  dt <	self.expTimeMultiplier * expT: status = u"down"
										else :				  status = u"expired"
										if not self.expTimerSettingsOK("AP",MAC, dev): continue

										if status != "up":
											if dev.states["status"] == u"up":
												if self.doubleCheckWithPing(status,dev.states["ipNumber"], props,dev.states[u"MAC"],"Logic", "Period check-WiFi", "chk-Time",xType) ==0:
													status	= u"up"
													self.setImageAndStatus(dev, "up", oldStatus=dev.states[u"status"],ts=time.time(), fing=False, level=1, text1= dev.name.ljust(30) + u" status "    + status.ljust(10) +";	set to UP,	reset by ping ", iType=u"PER-AP-Wi-0",reason=u"Period Check Wifi "+status)
													changed = True
													continue
												else:
													self.setImageAndStatus(dev, status, oldStatus=dev.states[u"status"],ts=time.time(), fing=True, level=1, text1= dev.name.ljust(30) + u" status "     + status.ljust(10) +" changed period WiFi, expT= %4.1f"%expT+"     dt= %4.1f"%dt, iType=u"PER-AP-Wi-1",reason=u"Period Check Wifi "+status)
													changed = True
													continue

											if dev.states["status"] == u"down" and status !="down": # to expired
													self.setImageAndStatus(dev, status, oldStatus=dev.states[u"status"],ts=time.time(), fing=True, level=1, text1= dev.name.ljust(30) + u" status "     + status.ljust(10) +" changed period WiFi, expT= %4.1f"%expT+"     dt= %4.1f"%dt, iType=u"PER-AP-Wi-1",reason=u"Period Check Wifi "+status)
													changed = True
													continue

										else:
											if dev.states[u"status"] != status:
												if self.doubleCheckWithPing(status,dev.states["ipNumber"], props,dev.states[u"MAC"],"Logic", "Period check-WiFi", "chk-Time",xType) !=0:
													pass
												else:
													changed = True
													status ="up"
													self.setImageAndStatus(dev, status, oldStatus=dev.states[u"status"],ts=time.time(), fing=True, level=1, text1= dev.name.ljust(30) + u" status "     + status.ljust(10) +" changed period WiFi, expT= %4.1f"%expT+"     dt= %4.1f"%dt, iType=u"PER-AP-Wi-1",reason=u"Period Check Wifi "+status)
												continue


								elif  (u"useWhatForStatusWiFi" in props and props[u"useWhatForStatusWiFi"] == u"FastDown") and dev.states[u"status"] =="down" and (time.time() - lastUpTT > self.expTimeMultiplier * expT):
										if not self.expTimerSettingsOK("AP",MAC, dev): continue
										status = u"expired"
										changed = True
										#self.myLog( text=u" period "+ dev.name+u" changed: old status: "+dev.states[u"status"]+u"; new  "+status)
										self.setImageAndStatus(dev, status, oldStatus=dev.states[u"status"],ts=time.time(), fing=True, level=1, text1= dev.name.ljust(30) + u" status "     + status.ljust(10) +" changed period WiFi, expT= %4.1f"%expT+"     dt= %4.1f"%dt, iType=u"PER-AP-Wi-2",reason=u"Period Check Wifi "+status)


							elif props[u"useWhatForStatus"] ==u"SWITCH":
								suffixN = u"SWITCH"
								dt = time.time() - lastUpTT
								if	 dt <  1 * expT:  status = u"up"
								elif dt <  2 * expT:  status = u"down"
								else :				  status = u"expired"
								if not self.expTimerSettingsOK("SW",MAC, dev): continue
								if dev.states[u"status"] != status:
									if status =="down" and self.doubleCheckWithPing(status,dev.states["ipNumber"], props,dev.states[u"MAC"],"Logic", "Period check-SWITCH", "chk-Time",xType) ==0:
											status = u"up"
									if dev.states[u"status"] != status:
										changed = True
										self.setImageAndStatus(dev, status,oldStatus=dev.states[u"status"], ts=time.time(), fing=True, level=1, text1= dev.name.ljust(30) + u" status " + unicode(status).ljust(10) + " changed period SWITCH ,	 expT= %4.1f"%expT+"  dt= %4.1f"%dt, iType=u"PER-SW-0",reason=u"Period Check SWITCH "+status)



							elif props[u"useWhatForStatus"] == u"DHCP":
								suffixN = u"DHCP"
								dt = time.time() - lastUpTT
								if	 dt <  						1 * expT:  status = u"up"
								elif dt <  self.expTimeMultiplier * expT:  status = u"down"
								else :				  status = u"expired"
								if not self.expTimerSettingsOK("GW",MAC, dev): continue
								if dev.states[u"status"] != status:
									if status == "down" and self.doubleCheckWithPing(status,dev.states["ipNumber"], props,dev.states[u"MAC"],"Logic", "Period check-DHCP", "chk-Time",xType) ==0:
										status = u"up"
									if dev.states[u"status"] != status:
										changed = True
										self.setImageAndStatus(dev, status,oldStatus=dev.states[u"status"], ts=time.time(), fing=True, level=1, text1= dev.name.ljust(30) + u" status " + unicode(status).ljust(10) + " changed period DHCP,  expT= %4.1f"%expT+"  dt= %4.1f"%dt, iType=u"PER-DHCP-0",reason=u"Period Check DHCP "+status)


							else:
								dt = time.time() - lastUpTT
								if	 dt <  						1 * expT:  status = u"up"
								elif dt <  self.expTimeMultiplier * expT:  status = u"down"
								else			   :  status = u"expired"
								if dev.states[u"status"] != status:
									if status =="down" and self.doubleCheckWithPing(status,dev.states["ipNumber"], props,dev.states[u"MAC"],"Logic", "Period check-default", "chk-Time",xType) ==0:
										status = u"up"
									if dev.states[u"status"] != status:
										changed = True
										self.setImageAndStatus(dev, status,oldStatus=dev.states[u"status"], ts=time.time(), fing=True, level=1, text1= dev.name.ljust(30) + u" status " + unicode(status).ljust(10) + " changed period regular expiration expT= %4.1f" % expT + "  dt= %4.1f" % dt+u" useWhatForStatus else "+ props[u"useWhatForStatus"], iType=u"PER-expire",reason=u"Period Check")
						continue


					elif dev.deviceTypeId == u"Device-AP":
						try:
							ipN = dev.states[u"ipNumber"]
							if ipN not in self.APUP:
								continue
								#ipN = self.ipNumbersOfAPs[int(dev.states[u"apNo"])]
								#dev.updateStateOnServer(u"ipNumber", ipN )
							if ipN in self.suspendedUnifiSystemDevicesIP:
								status = "susp"
								self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
								dt	=99
								expT=999
							else:
								dt = time.time() - self.APUP[dev.states[u"ipNumber"]]
								if	 dt <  						1 * expT:  status = u"up"
								elif dt <  self.expTimeMultiplier * expT:  status = u"down"
								else :				  status = u"expired"
							if dev.states[u"status"] != status:
								if status =="down" and self.doubleCheckWithPing(status,dev.states["ipNumber"], props,dev.states[u"MAC"],"Logic", "Period check-dev-AP", "chk-Time",xType) ==0:
									status = u"up"
								if dev.states[u"status"] != status:
									changed = True
									self.setImageAndStatus(dev,status,oldStatus=dev.states[u"status"],ts=time.time(), fing=True, level=1, text1= dev.name.ljust(30) + u" status " + status.ljust(10) + " changed period expT= %4.1f" % expT + "     dt= %4.1f" % dt, reason=u"Period Check", iType=u"PER-DEV-AP")
						except	Exception, e:
							if len(unicode(e)) > 5:
								self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							continue

					elif dev.deviceTypeId.find(u"Device-SW") >-1:
						try:
							ipN = dev.states[u"ipNumber"]
							if ipN not in self.SWUP:
								ipN = self.ipNumbersOfSWs[int(dev.states[u"switchNo"])]
								dev.updateStateOnServer(u"ipNumber", ipN )
							if ipN in self.suspendedUnifiSystemDevicesIP:
								self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
								status = "susp"
								dt =99
								expT=999
							else:

								dt = time.time() - self.SWUP[ipN]
								if	 dt < 						1 * expT: status = u"up"
								elif dt < self.expTimeMultiplier  * expT: status = u"down"
								else:				status = u"expired"
							if dev.states[u"status"] != status:
								if status =="down" and self.doubleCheckWithPing(status,dev.states["ipNumber"], props,dev.states[u"MAC"],"Logic", "Period check-dev-SW", "chk-Time",xType) ==0:
									status = u"up"
								if dev.states[u"status"] != status:
									changed = True
									self.setImageAndStatus(dev,status,oldStatus=dev.states[u"status"],ts=time.time(), fing=True, level=1, text1=dev.name.ljust(30) + u" status " + status.ljust(10) + " changed period expT= %4.1f" % expT + "    dt= %4.1f" % dt,reason=u"Period Check", iType=u"PER-DEV-SW")
						except	Exception, e:
							if len(unicode(e)) > 5:
								self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							continue


					elif dev.deviceTypeId == u"neighbor":
						try:
							dt = time.time() - lastUpTT
							if	 dt < 						1 * expT: status = u"up"
							elif dt < self.expTimeMultiplier  * expT: status = u"down"
							else:				status = u"expired"
							if dev.states[u"status"] != status:
									changed=True
									self.setImageAndStatus(dev,status,oldStatus=dev.states[u"status"],ts=time.time(), fing=self.ignoreNeighborForFing, level=1, text1=dev.name.ljust(30) + u" status " + status.ljust(10) + " changed period expT= %4.1f" % expT + "  dt= %4.1f" % dt,reason=u"Period Check other", iType=u"PER-DEV-NB")
						except	Exception, e:
							if len(unicode(e)) > 5:
								self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							continue
					else:
						try:
							dt = time.time() - lastUpTT
							if dt < 1 * expT:	status = u"up"
							elif dt < 2 * expT: status = u"down"
							else:				status = u"expired"
							if dev.states[u"status"] != status:
								if status =="down" and self.doubleCheckWithPing(status,dev.states["ipNumber"], props,dev.states[u"MAC"],"Logic", "Period check-def", "chk-Time",xType) ==0:
									status = u"up"
								if dev.states[u"status"] != status:
									changed=True
									self.setImageAndStatus(dev,status, oldStatus=dev.states[u"status"],ts=time.time(), fing=True, level=1, text1=dev.name.ljust(30) + u" status " + status.ljust(10) + " changed period expT= %4.1f"%expT+"     dt= %4.1f"%dt+u" devtype else:"+dev.deviceTypeId,reason=u"Period Check other", iType=u"PER-DEV-exp")

						except:
							continue

					self.lastSecCheck = time.time()
				except	Exception, e:
					if len(unicode(e)) > 5:
						self.indiLOG.log(40,"in Line {} has error={}\nlooking at device:  {}".format(sys.exc_traceback.tb_lineno, e, dev.name))


		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return	changed





	###########################	   UTILITIES  #### START #################

	### reset exp timer if it is shorter than the device exp time
	####-----------------	 ---------
	def expTimerSettingsOK(self,xType,MAC,	dev):
		try:
			props = dev.pluginProps
			if u"expirationTime" not in props:
				return True
			if not self.fixExpirationTime: return True

			if float(self.readDictEverySeconds[xType]) <  float(props[u"expirationTime"]): return True
			newExptime	= float(self.readDictEverySeconds[xType])+30
			self.indiLOG.log(20,u"Per-check1    " +MAC+" updating exp time for "+dev.name+" to "+ unicode(newExptime))
			props[u"expirationTime"] = newExptime
			dev.replacePluginPropsOnServer(props)
			return False

		except	Exception, e:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return True

	###	 kill expect pids if running
	####-----------------	 ---------
	def killIfRunning(self,ipNumber,expectPGM):
		cmd = "ps -ef | grep '/uniFiAP.' | grep /usr/bin/expect | grep -v grep"
		if  expectPGM !="":		cmd += " | grep '" + expectPGM + "' "
		if  ipNumber != "":		cmd += " | grep '" + ipNumber  + " ' "  # add space at end of ip# for search string

		if self.decideMyLog(u"Expect"): self.indiLOG.log(20,u"killing request, get list with: "+cmd)
		ret = subprocess.Popen( cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()[0]

		if len(ret) < 5:
			return

		lines = ret.split("\n")
		for line in lines:
			if len(line) < 5:
				continue

			items = line.split()
			if len(items) < 5:
				continue

			pid = items[1]
			try:
				if int(pid) < 100: continue # don't mess with any system processes
				ret = subprocess.Popen("/bin/kill -9  " + pid, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()
				if self.decideMyLog(u"Expect"): self.indiLOG.log(20,u"killing expect "+expectPGM+" w ip# " +ipNumber +"    "  +pid+":\n"+line )
			except:
				pass

		return

	####-----------------	 ---------
	def killPidIfRunning(self,pid):
		cmd = "ps -ef | grep '/uniFiAP.' | grep /usr/bin/expect | grep "+str(pid)+" | grep -v grep"

		if self.decideMyLog(u"Expect"): self.indiLOG.log(20,u"killing request,  for pid: "+str(pid))
		ret = subprocess.Popen( cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()[0]

		if len(ret) < 5:
			return

		lines = ret.split("\n")
		for line in lines:
			if len(line) < 5:
				continue

			items = line.split()
			if len(items) < 5:
				continue

			pidInLine = items[1]
			try:
				if int(pidInLine) != int(pid): continue # don't mess with any system processes
				ret = subprocess.Popen("/bin/kill -9  " + pidInLine, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()
				if self.decideMyLog(u"Expect"): self.indiLOG.log(20,u"killing expect "  +pidInLine+":\n"+line )
			except:
				pass
			break

		return

	### test if AP are up, first ping then check if expect is running
	####-----------------	 ---------
	def testAPandPing(self,ipNumber, type):
		try:
			if self.decideMyLog(u"Connection"): self.indiLOG.log(20,u"CONNtest  testing if " + ipNumber  + "/usr/bin/expect "+self.expectCmdFile[type]+" is running ")
			if os.path.isfile(self.pathToPlugin +self.expectCmdFile[type]):
				if self.decideMyLog(u"Connection"): self.indiLOG.log(20,"CONNtest  "+self.expectCmdFile[type]+" exists, now doing ping" )
			if self.checkPing(ipNumber, nPings=2, waitForPing=1000, calledFrom="testAPandPing") !=0:
				if self.decideMyLog(u"Connection"): self.indiLOG.log(20,u"CONNtest  ping not returned" )
				return False

			cmd = "ps -ef | grep " +self.expectCmdFile[type]+ "| grep " + ipNumber + " | grep /usr/bin/expect | grep -v grep"
			if self.decideMyLog(u"Expect"): self.indiLOG.log(20,u"CONNtest  check if pgm is running "+cmd )
			ret = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()[0]
			if len(ret) < 5: return False
			lines = ret.split("\n")
			for line in lines:
				if len(line) < 5:
					continue

				##self.myLog( text=line )
				items = line.split()
				if len(items) < 5:
					continue

				if self.decideMyLog(u"Connection"): self.indiLOG.log(20,u"CONNtest  expect is running" )
				return True

			if self.decideMyLog(u"Connection"): self.indiLOG.log(20,"CONNtest  "+type+ "    " + ipNumber +u" is NOT running" )
			return False
		except	Exception, e:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))




	####-----------------	 --------- 
	### init,save,write data stats for receiving messages
	def addTypeToDataStats(self,ipNumber, apN, uType):
		try:
			if uType not in self.dataStats["tcpip"]:
				self.dataStats["tcpip"][uType]={}
			if ipNumber not in self.dataStats["tcpip"][uType]:
				self.dataStats["tcpip"][uType][ipNumber]={u"inMessageCount":0,u"inMessageBytes":0,u"inErrorCount":0,u"restarts":0,u"startTime":time.time(),u"APN":unicode(apN), u"aliveTestCount":0}
		except	Exception, e:
			self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	####-----------------	 ---------
	def zeroDataStats(self):
		for uType in self.dataStats["tcpip"]:
			for ipNumber in self.dataStats["tcpip"][uType]:
				self.dataStats["tcpip"][uType][ipNumber][u"inMessageCount"]	  =0
				self.dataStats["tcpip"][uType][ipNumber][u"inMessageBytes"]	  =0
				self.dataStats["tcpip"][uType][ipNumber][u"aliveTestCount"]	  =0
				self.dataStats["tcpip"][uType][ipNumber][u"inErrorCount"]	  =0
				self.dataStats["tcpip"][uType][ipNumber][u"restarts"]		  =0
				self.dataStats["tcpip"][uType][ipNumber][u"startTime"]		  =time.time()
		self.dataStats["updates"]={"devs":0,"states":0,"startTime":time.time()}
	####-----------------	 ---------
	def resetDataStats(self, calledFrom=""):
		indigo.server.log(" resetDataStats called from {}".format(calledFrom) )
		self.dataStats={"tcpip":{},"updates":{"devs":0,"states":0,"startTime":time.time()}}
		self.saveDataStats()

	####-----------------	 ---------
	def saveDataStats(self):
		if time.time() - 60	 < self.lastSaveDataStats: return
		self.lastSaveDataStats = time.time()
		self.writeJson(self.dataStats, fName=self.indigoPreferencesPluginDir+"dataStats", sort=False, doFormat=True )

	####-----------------	 ---------
	def readDataStats(self):
		self.lastSaveDataStats	= time.time() -60
		try:
			f=open(self.indigoPreferencesPluginDir+"dataStats","r")
			self.dataStats= json.loads(f.read())
			f.close()
			if "tcpip" not in self.dataStats:
				self.resetDataStats( calledFrom="readDataStats 1")
			return
		except: pass

		self.resetDataStats( calledFrom="readDataStats 2")
		return
	### init,save,write data stats for receiving messages
	####-----------------	 --------- END

	####-----------------	 --------- START
	####------ camera io ---	-------
	def resetCamerasStats(self):
		self.cameras={}
		self.saveCameraEventsStatus = True
		self.saveCameraEventsLastCheck = 0
		self.saveCamerasStats()

	####-----------------	 ---------
	def saveCamerasStats(self,force=False):
		if	not self.saveCameraEventsStatus: return

		if self.saveCameraEventsStatus == True:
			self.saveCameraEventsLastCheck = 0

		# check if we have deleted devices in cameras
		if time.time() - self.saveCameraEventsLastCheck > 500 or force:

			cameraMacList ={}
			for dev in indigo.devices.iter("props.isCamera"):
				cameraMacList[dev.states["MAC"]] = dev.id

			delList ={}
			for MAC in self.cameras:
				if MAC not in cameraMacList:
					delList[MAC]=True
			for MAC in delList:
				self.cameras[MAC]["devid"]=-1

			self.saveCameraEventsLastCheck = time.time()

		# save cameras to disk
		self.writeJson( self.cameras, fName=self.indigoPreferencesPluginDir+"CamerasStats",  sort=True, doFormat=True )
		self.saveCameraEventsStatus = False

	####-----------------	 ---------
	def readCamerasStats(self):
		try:
			f=open(self.indigoPreferencesPluginDir+"CamerasStats","r")
			self.cameras= json.loads(f.read())
			f.close()
			self.saveCameraEventsStatus = True
			self.saveCamerasStats()
			return
		except: pass

		self.resetCamerasStats()
		return



	####-----------------	 ---------
	def getNVRIntoIndigo(self,force= False):
		try:
			if time.time() - self.lastCheckForNVR < 451 and not force: return
			self.lastCheckForNVR = time.time()
			if not self.isValidIP(self.ipnumberOfNVR): return
			if not self.VIDEOEnabled:				   return


			info =self.getCamerasFromNVR( action=["system"])

			if len(info["NVR"]) < 2:
				for dev in indigo.devices.iter("props.isNVR"):
					self.updateStatewCheck(dev,"status", "down")
					self.executeUpdateStatesList()
					break
				return

			NVR = info["NVR"]
			ipNumber =""
			UnifiDevice = ""
			UnifiMAC	= ""
			UnifiName	= ""
			memoryUsed	= ""
			dirName		= ""
			diskUsed	= ""
			diskFree	= ""
			rtmpsPort	= "off"
			rtspPort	= "off"
			rtmpPort	= "off"
			diskUsed	= ""
			diskAvail	= ""
			diskUsed	= ""
			cpuLoad		= ""
			apiKey		= ""
			apiAccess	= False
			upSince		= ""
			MAC			= ""


			if "host"			   in NVR:								  ipNumber			= NVR["host"]
			if "uptime"			   in NVR:								  upSince			= time.strftime( '%Y-%m-%d %H:%M:%S', time.localtime(float(NVR["uptime"])/1000) )

			if "systemInfo"	   in NVR:
				if "nics"		   in NVR["systemInfo"]:
					for nic		   in NVR["systemInfo"]["nics"]:
						if "ip"	   in nic:								  ipNumber			= nic["ip"]
						if "mac"   in nic:								  MAC				= nic["mac"].lower()
				if "memory"	 in NVR["systemInfo"]:
						if "total" in NVR["systemInfo"]["memory"]:		  memoryUsed		= "%d/%d"%( float(NVR["systemInfo"]["memory"]["used"])/(1024*1024), float(NVR["systemInfo"]["memory"]["total"])/(1024*1024) )+"[GB]"
				if "cpuLoad"	 in NVR["systemInfo"]:					  cpuLoad			= "%.1f"%( float(NVR["systemInfo"]["cpuLoad"]))+"[%]"
				if "disk"		 in NVR["systemInfo"]:
						if "dirName"	 in NVR["systemInfo"]["disk"]:	  dirName			= NVR["systemInfo"]["disk"]["dirName"]
						if "availKb"	 in NVR["systemInfo"]["disk"]:	  diskAvail			= "%d"%( float(NVR["systemInfo"]["disk"]["availKb"])/(1024*1024) )+"[GB]"
						if "usedKb"		 in NVR["systemInfo"]["disk"]:	  diskUsed			= "%d/%d"%( float(NVR["systemInfo"]["disk"]["usedKb"])/(1024*1024) , float(NVR["systemInfo"]["disk"]["totalKb"])/(1024*1024) )	+"[GB]"

			if"livePortSettings"		 in NVR:
				if "rtmpEnabled"		 in NVR["livePortSettings"]:
						if NVR["livePortSettings"]["rtmpEnabled"]:		  rtmpPort			=  str( NVR["livePortSettings"]["rtmpPort"] )
				if "rtmpsEnabled"		  in NVR["livePortSettings"]:
						if NVR["livePortSettings"]["rtmpsEnabled"]:		  rtmpsPort			=  str( NVR["livePortSettings"]["rtmpsPort"] )
				if "rtspEnabled"		 in NVR["livePortSettings"]:
						if NVR["livePortSettings"]["rtspEnabled"]:		  rtspPort			=  str( NVR["livePortSettings"]["rtspPort"] )

			users = info["users"]

			for _id in users:
				if users[_id]["userName"] == self.nvrWebUserID:
					if "apiKey" in users[_id] and "enableApiAccess" in users[_id]:
						if users[_id]["enableApiAccess"] :
							apiKey		= users[_id]["apiKey"]
							apiAccess 	= users[_id]["enableApiAccess"]


			UnifiName	= ipNumber
			for dev in indigo.devices.iter("props.isUniFi"):
				if dev.states["ipNumber"] == ipNumber and MAC == dev.states["MAC"]:
					UnifiName	= dev.name
					break


			dev = ""
			for dd in indigo.devices.iter("props.isNVR"):
				dev = dd
				break

			if dev =="":
				if UnifiName != "": useName= UnifiName
				elif UnifiMAC !="": useName= UnifiMAC
				else:				useName= ipNumber+str(int(time.time()))

				dev = indigo.device.create(
					protocol =		 indigo.kProtocol.Plugin,
					address =		 UnifiMAC,
					name =			 "NVR_" + useName,
					description =	 self.fixIP(ipNumber),
					pluginId =		 self.pluginId,
					deviceTypeId =	 "NVR",
					folder =		 self.folderNameIDSystemID,
					props =			 {"isNVR":True})

			self.updateStatewCheck(dev,"status",		"up")
			self.updateStatewCheck(dev,"ipNumber",		ipNumber)
			self.updateStatewCheck(dev,"memoryUsed",	memoryUsed)
			self.updateStatewCheck(dev,"dirName",		dirName)
			self.updateStatewCheck(dev,"diskUsed",		diskUsed)
			self.updateStatewCheck(dev,"diskAvail",		diskAvail)
			self.updateStatewCheck(dev,"rtmpPort",		rtmpPort)
			self.updateStatewCheck(dev,"rtmpsPort",		rtmpsPort)
			self.updateStatewCheck(dev,"rtspPort",		rtspPort)
			self.updateStatewCheck(dev,"cpuLoad",		cpuLoad)
			self.updateStatewCheck(dev,"apiKey",		apiKey)
			self.updateStatewCheck(dev,"apiAccess",		apiAccess)
			self.updateStatewCheck(dev,"upSince",		upSince)

			self.pluginPrefs["nvrVIDEOapiKey"]		  	= apiKey
			self.nvrVIDEOapiKey						  	= apiKey

			self.executeUpdateStatesList()

		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


	####-----------------	 ---------
	def updateStatewCheck(self,dev, state , value, check = "", NotEq = False):
		if state not in dev.states:		   return False
		if NotEq:
			if dev.states[state] != check: return False
		else:
			if state == check:			   return False
		if dev.states[state]  ==  value:   return False
		self.addToStatesUpdateList(dev.id,state,  value )
		return True

	####-----------------	 ---------
	def getCamerasIntoIndigo(self, force = False, periodCheck = False):
		try:
			if periodCheck: test = 300
			else:			test = 30
			if time.time() - self.lastCheckForCAMERA < test and not force: return
			self.lastCheckForCAMERA = time.time()
			timeElapsed = time.time()
			if not self.isValidIP(self.ipnumberOfNVR): return
			if not self.VIDEOEnabled:					 return
			info =self.getCamerasFromNVR(action=["cameras"])
			if len(info) < 1:
				self.sleep(1)
				info =self.getCamerasFromNVR(action=["cameras"])

		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	####-----------------	 ---------
	def fillCamerasIntoIndigo(self,camJson, calledFrom=""):
		try:
			## self.myLog( text=u"fillCamerasIntoIndigo called from: "+calledFrom)
			if len(camJson) < 1: return
			saveCam= False
			for cam2 in camJson:
				if "mac" in cam2:
					c = cam2["mac"]
					MAC = c[0:2]+":"+c[2:4]+":"+c[4:6]+":"+c[6:8]+":"+c[8:10]+":"+c[10:12]
					MAC = MAC.lower()

					skip = ""
					if self.testIgnoreMAC(MAC):
						skip = "MAC in ignored List"
					else:
						if "authStatus" in cam2 and cam2["authStatus"] != "AUTHENTICATED":
							skip += "authStatus: !=AUTHENTICATED;"
						if "managed" in cam2 and not cam2["managed"]:
							skip += " .. != managed;"
						if "deleted" in cam2 and  cam2["deleted"]:
							skip += " deleted"
						if skip !="":
							if self.decideMyLog(u"Video"): self.indiLOG.log(20,u"skipping camera with MAC # "+MAC +"; because : "+ skip)
					if skip !="":
						continue

					found = False
					for cam in self.cameras:
						if MAC == cam:
							self.cameras[MAC]["uuid"]		= cam2["uuid"]
							self.cameras[MAC]["ip"]			= cam2["host"]
							self.cameras[MAC]["apiKey"]		= cam2["_id"]
							self.cameras[MAC]["nameOnNVR"]	= cam2["name"]
							found = True
							break
					if not found:
						saveCam = True
						self.cameras[MAC]= {"nameOnNVR":cam2["name"], "events":{}, "eventsLast":{"start":0,"stop":0},"devid":-1, "uuid":cam2["uuid"], "ip":cam2["host"], "apiKey":cam2["_id"]}

					devFound = False
					if "devid" in self.cameras[MAC]:
						try:
							dev = indigo.devices[self.cameras[MAC]["devid"]]
							devFound = True
						except: pass

					if	not devFound:
						for dev in indigo.devices.iter("props.isCamera"):
							if "MAC" not in dev.states:	   continue
							if dev.states["MAC"] == MAC:
								devFound = True
								break
					if not devFound:
						try:
							dev = indigo.device.create(
								protocol=indigo.kProtocol.Plugin,
								address=MAC,
								name = "Camera_"+self.cameras[MAC]["nameOnNVR"]+"_"+MAC ,
								description="",
								pluginId=self.pluginId,
								deviceTypeId="camera",
								props={"isCamera":True},
								folder=self.folderNameIDSystemID
								)
							indigo.variable.updateValue("Unifi_New_Device",dev.name+"/"+MAC+"/"+cam2["host"])
						except	Exception, e:
							if unicode(e).find("NameNotUniqueError") >-1:
								dev = indigo.devices["Camera_"+self.cameras[MAC]["nameOnNVR"]+"_"+MAC]
								props = dev.pluginProps
								props["isCamera"] = True
								dev.replacePluginPropsOnServer()
								dev = indigo.devices[dev.id]
							else:
								if len(unicode(e)) > 5:
									self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
								continue
					saveCam or self.updateStatewCheck(dev,"MAC",		 MAC)
					saveCam or self.updateStatewCheck(dev,"apiKey",		 self.cameras[MAC]["apiKey"])
					saveCam or self.updateStatewCheck(dev,"uuid",		 self.cameras[MAC]["uuid"])
					saveCam or self.updateStatewCheck(dev,"ip",			 self.cameras[MAC]["ip"])
					saveCam or self.updateStatewCheck(dev,"nameOnNVR",	 self.cameras[MAC]["nameOnNVR"])
					saveCam or self.updateStatewCheck(dev,"eventNumber", -1,					   check="", NotEq=True)
					saveCam or self.updateStatewCheck(dev,"status",		"ON",					   check="", NotEq=True)
					self.executeUpdateStatesList()
					if not devFound:
						dev = indigo.devices[dev.id]

			if saveCam:
				self.pendingCommand.append("saveCamerasStats")


		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	####------ camera io ---	-------
	####-----------------	 --------- END



	####-----------------	 -----------
	### ----------- save read MAC2INDIGO
	def saveMACdata(self, force=False):
		if not force and  (time.time() - 20 < self.lastSaveMAC2INDIGO): return
		self.lastSaveMAC2INDIGO = time.time()
		self.writeJson(self.MAC2INDIGO, fName=self.indigoPreferencesPluginDir+"MAC2INDIGO", doFormat=True )
		self.writeJson(self.MACignorelist, fName=self.indigoPreferencesPluginDir+"MACignorelist", doFormat=True )
		self.writeJson(self.MACSpecialIgnorelist, fName=self.indigoPreferencesPluginDir+"MACSpecialIgnorelist", doFormat=True )

	####-----------------	 ---------
	def readMACdata(self):
		self.lastSaveMAC2INDIGO	 = time.time() -21
		try:
			f=open(self.indigoPreferencesPluginDir+"MAC2INDIGO","r")
			self.MAC2INDIGO= json.loads(f.read())
			f.close()
		except:
			self.MAC2INDIGO= {"UN":{},u"GW":{},u"SW":{},u"AP":{},u"NB":{}}
		try:
			f=open(self.indigoPreferencesPluginDir+"MACignorelist","r")
			self.MACignorelist= json.loads(f.read())
			f.close()
		except:
			self.MACignorelist ={}
		try:
			f=open(self.indigoPreferencesPluginDir+"MACSpecialIgnorelist","r")
			self.MACSpecialIgnorelist= json.loads(f.read())
			f.close()
		except:
			self.MACSpecialIgnorelist ={}
		return
	### ----------- save read MAC2INDIGO
	####-----------------	 -----------   END


	####-----------------	 -----------   START
	### ----------- manage suspend status
	def setSuspend(self,ip,tt):
		self.suspendedUnifiSystemDevicesIP[ip] = tt
		self.writeSuspend()
	####-----------------	 ---------
	def delSuspend(self,ip):
		if ip in self.suspendedUnifiSystemDevicesIP:
			del self.suspendedUnifiSystemDevicesIP[ip]
			self.writeSuspend()
	####-----------------	 ---------
	def writeSuspend(self):
		try:
			self.writeJson(self.suspendedUnifiSystemDevicesIP, fName=self.indigoPreferencesPluginDir+"suspended", sort=False, doFormat=False)
		except: pass
	####-----------------	 ---------
	def readSuspend(self):
		self.suspendedUnifiSystemDevicesIP={}
		try:
			f=open(self.indigoPreferencesPluginDir+"suspended","r")
			self.suspendedUnifiSystemDevicesIP = json.loads(f.read())
			f.close()
		except: pass
	### ----------- manage suspend status
	####-----------------	 -----------   END




	### here we do the work, setup the logfiles listening and read the logfiles and check if everything is running, if not restart
	####-----------------	 ---------
	def getMessages(self, ipNumber, apN, uType, repeatRead):

		apnS = unicode(apN)
		self.addTypeToDataStats(ipNumber, apnS, uType)
		self.msgListenerActive[uType] = time.time() - 200
		try:
			errorCount =0
			unifiDeviceType = uType[0:2]

			init = True
			#### for ever, until self.stop is set
			total						= ""
			lastTestServer				= time.time()
			lastForcedRestartTimeStamp	= -1
			testServerCount				= -3  # not for the first 3 rounds
			connectErrorCount			= 0
			msgSleep					= 1
			if repeatRead < 0:
				minWaitbeforeRestart 	= 9999999999999999
			else:
				minWaitbeforeRestart	= max(float(self.restartIfNoMessageSeconds), float(repeatRead) )

			while True:
				if self.pluginState == "stop": 
					try:	self.killPidIfRunning(ListenProcessFileHandle.pid)
					except:	pass
					return

				if ipNumber in self.suspendedUnifiSystemDevicesIP:
					self.sleep(20)
					continue

				if len(self.restartRequest) > 0:
					if uType in self.restartRequest:
						if self.restartRequest[uType] == apnS:
							if self.decideMyLog(u"Expect"):
								self.indiLOG.log(20,"getMessages: {}    restart requested ".format(self.restartRequest) )
							lastForcedRestartTimeStamp	= -1
							del self.restartRequest[uType]


				if ( (time.time()- lastForcedRestartTimeStamp) > minWaitbeforeRestart) or lastForcedRestartTimeStamp <0: # init comm
							if lastForcedRestartTimeStamp> 0:
								if self.decideMyLog(u"Expect"):
									self.indiLOG.log(40,"getMessages: forcing restart of listener for: {}   @ {}  after {} sec without message{}".format(self.expectCmdFile[uType], uType, ipNumber, int(time.time() - lastForcedRestartTimeStamp))  )
								self.dataStats["tcpip"][uType][ipNumber]["restarts"]+=1
							else:
								self.indiLOG.log(20,u"getMessages: launching listener for: {}  @ {}".format(uType, ipNumber) )

							try:	self.killPidIfRunning(ListenProcessFileHandle.pid)
							except:	pass

							self.killIfRunning(ipNumber,self.expectCmdFile[uType] )
							if not self.testServerIfOK(ipNumber,uType):
								self.indiLOG.log(40,"getMessages: (1)  error connecting to ip#: {} wrong ip/ password or system down or ssh timed out or ..? ".format(ipNumber) )
								time.sleep(15)
								self.msgListenerActive[uType] = 0
								continue
							if uType=="VDtail":
								self.setAccessToLog(ipNumber,uType)
							ListenProcessFileHandle, msg = self.startConnect(ipNumber,uType)
							if self.decideMyLog(u"Expect"):
								self.indiLOG.log(30,"getMessages: ListenProcess started for uType: {};  ip: {}  pid:{}".format(uType, ipNumber, ListenProcessFileHandle.pid) )


							if msg != "":
								if errorCount%10 == 0:
									self.indiLOG.log(40,u"getMessages: (2)  error in listener {}, connect  @ {}".format(uType, ipNumber) )
								self.sleep(15)
								continue
							self.msgListenerActive[uType] = time.time()

							connectErrorCount = 0
							lastForcedRestartTimeStamp = time.time()


				self.sleep(msgSleep)

				## force restart after xx seconds no matter what?
				if errorCount > 3:
					self.indiLOG.log(40, "{} {} forcing restart of msg after due to error count in json".format(uType, ipNumber))
					errorCount =0
					lastForcedRestartTimeStamp = time.time()
					self.killIfRunning(ipNumber, "")

				## force a logfile respnse by logging in. this is needed to make the tail -f pis send a message to make sure we are still alive
				if (time.time() - lastForcedRestartTimeStamp) > max(30.,minWaitbeforeRestart*0.9):
					if	uType.find("tail") >- 1:
						if (time.time() - lastTestServer) > 30:
							testServerCount +=1
							if testServerCount > 1:
								lastForcedRestartTimeStamp = 0

							else:
								if self.testAPandPing(ipNumber,uType):
									if not self.testServerIfOK(ipNumber,uType):
										if errorCount%10 == 0:
											self.indiLOG.log(40,"getMessage: (2)  error connecting to ip#: {} wrong ip/ password or system down or ssh time out ...?".format(ipNumber))
										continue
								else:
									lastForcedRestartTimeStamp =0
							lastTestServer = time.time()

				## should we stop?, is our IP number listed?
				if ipNumber in self.stop:
					self.indiLOG.log(20,uType+ "getMessage: stop = True for ip# {}".format(ipNumber) )
					while self.stop.count(ipNumber) > 0:
						self.stop.remove(ipNumber)
					return

				## here we actually read the stuff
				try:
					linesFromServer = os.read(ListenProcessFileHandle.stdout.fileno(),self.readBuffer) ## = 32k
					msgSleep = 0.1 # fast read to follow
				except	Exception, e:
					if unicode(e).find("[Errno 35]") > -1:	 # "Errno 35" is the normal response if no data, if other error stop and restart
						msgSleep = 0.4 # nothing new, can wait
					else:
						if len(unicode(e)) > 5:
							out = "os.read(ListenProcessFileHandle.stdout.fileno(),{})  in Line {} has error={}\n ip:{}  type: {}".format(self.readBuffer, sys.exc_traceback.tb_lineno, e, ipNumber,uType)
							try: out+= "fileNo: {}".format(ListenProcessFileHandle.stdout.fileno() )
							except: pass
							if unicode(e).find("[Errno 22]") > -1:  # "Errno 22" is  general read error "wrong parameter"
								out+= " ..      try lowering read buffer parameter in config" 
								self.indiLOG.log(30,out)
							else:
								self.indiLOG.log(40,out)
						lastForcedRestartTimeStamp = 1 # this forces a restart of the listener
				
					continue
					## did we get anything?

				if self.pluginState == "stop": 
					try:	self.killPidIfRunning(ListenProcessFileHandle.pid)
					except:	pass
					return

				if linesFromServer != "":
					if self.decideMyLog(u"Special"):
						msgF = linesFromServer.replace("\n","").replace("\r","")
						self.indiLOG.log(20,"getMessage: data recd from {:<14s},  type: {},  len: {:>5d}: {:<80s} ... {}".format(ipNumber, uType, len(linesFromServer), msgF[0:80],  msgF[-30:] ) )
					self.dataStats["tcpip"][uType][ipNumber]["inMessageCount"]+=1
					self.dataStats["tcpip"][uType][ipNumber]["inMessageBytes"]+=len(linesFromServer)
					lastForcedRestartTimeStamp = time.time()
					lastTestServer	  = time.time()
					testServerCount	  = 0
					## any error messages from OSX?
					pos1 = linesFromServer.find("closed by remote host")
					pos2 = linesFromServer.find("Killed by signal")
					pos3 = linesFromServer.find("Killed -9")
					if (  pos1 >- 1 or pos2 >- 1 or pos3 > -1):
						self.indiLOG.log(             30,"getMessage: {} {} returning: ".format(uType, ipNumber)  )
						if pos1 >-1: self.indiLOG.log(30,"...{}".format(linesFromServer[max(0,pos1 - 100):pos1 + 100]) )
						if pos2 >-1: self.indiLOG.log(30,"...{}".format(linesFromServer[max(0,pos2 - 100):pos2 + 100]) )
						if pos3 >-1: self.indiLOG.log(30,"...{}".format(linesFromServer[max(0,pos3 - 100):pos3 + 100]) )
						self.indiLOG.log(             30,"...: {} we should restart listener on server ".format(uType) )
						lastForcedRestartTimeStamp = time.time() - minWaitbeforeRestart +30 # dont do it immediately
						continue
					##self.myLog( text=unicode(r))


				######### for tail logfile
					if uType.find("dict") ==-1:
						## fill the queue and send to the method that uses it
						if		unifiDeviceType == "AP":
							self.APUP[ipNumber] = time.time()
						elif	unifiDeviceType == "GW":
							self.GWUP[ipNumber] = time.time()
						elif	unifiDeviceType == "VD":
							self.VDUP[ipNumber] = time.time()
							self.msgListenerActive[uType] = time.time()

						errorCount = 0
						if linesFromServer.find("ThisIsTheAliveTestFromUnifiToPlugin") > -1:
							self.dataStats["tcpip"][uType][ipNumber]["aliveTestCount"]+=1
							if self.decideMyLog(u"Connection"): self.indiLOG.log(20,"getMessage: {} {} ThisIsTheAliveTestFromUnifiToPlugin received ".format(uType, ipNumber))
							continue
						self.logQueue.put((linesFromServer,ipNumber,apN, uType,unifiDeviceType))
						self.updateIndigoWithLogData()	#####################  here we call method to do something with the data


					######### for Dicts
					else:
						total += linesFromServer
						ppp = total.split(self.startDictToken[uType])
						if len(ppp) ==2:
							if ppp[1].find(self.endDictToken[uType]) >-1:
								dictData0 = ppp[len(ppp) - 1].lstrip("\r\n")

								try:
									ok = True
									dictData= dictData0.split(self.endDictToken[uType])[0]
									## remove last line
									if dictData[-1] !="}":
										ppp = dictData.rfind("}")
										dictData = dictData[0:ppp+1]
									theDict= json.loads(dictData)
									errorCount = 0
									if	  unifiDeviceType == "AP":
										self.APUP[ipNumber] = time.time()
									elif  unifiDeviceType == "SW":
										self.SWUP[ipNumber] = time.time()
									elif  unifiDeviceType == "GW":
										self.GWUP[ipNumber] = time.time()
									self.logQueueDict.put((theDict,ipNumber,apN,uType, unifiDeviceType))
									self.updateIndigoWithDictData2()  #####################	 here we call method to do something with the data
								except	Exception, e:
									if len(unicode(e)) > 5:
										msgF = total.replace("\n","").replace("\r","")
										self.indiLOG.log(40,"in Line {} has error={},receiving DICTs for {};  check unifi logfile; if this happens to often increase DICT timeout ".format(sys.exc_traceback.tb_lineno, e,ipNumber))
										self.indiLOG.log(40,"... {}  {} error in the JSON data".format(uType, ipNumber))
										self.indiLOG.log(40,"... JSON={:<100s} ... {}".format(msgF[0:100], msgF[:-40]) )
										self.dataStats["tcpip"][uType][ipNumber]["inErrorCount"]+=1

										errorCount+=1
									lastForcedRestartTimeStamp = time.time() - minWaitbeforeRestart*0.91
								total = ""
						else:
							total=""
					if self.statusChanged > 0:
						self.setGroupStatus()

				if len(self.sendUpdateToFingscanList) >0: self.sendUpdatetoFingscanNOW()
				if len(self.sendBroadCastEventsList) >0: self.sendBroadCastNOW()

		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


	### start the expect command to get the logfile
	####-----------------	 ---------
	def startConnect(self, ipNumber, uType):
		try:
			userid, passwd = self.getUidPasswd(uType)
			if userid =="": return

			if self.decideMyLog(u"Expect"): self.indiLOG.log(20,"startConnect: with IP: {:<15};   uType: {};   UID/PWD: {}/{}".format(ipNumber, uType, userid, passwd) )

			if ipNumber not in self.listenStart:
				self.listenStart[ipNumber] = {}
			self.listenStart[ipNumber][uType] = time.time()
			if self.commandOnServer[uType].find("off") == 0: return "",""

			TT= uType[0:2]
			for ii in range(20):
				if uType.find("dict")>-1:
					cmd = "/usr/bin/expect	'" + \
						  self.pathToPlugin + self.expectCmdFile[uType] + "' " + \
						"'"+userid + "' '"+passwd + "' " + \
						  ipNumber + " " + \
						  self.promptOnServer[uType] + " " + \
						  self.endDictToken[uType]+ " " + \
						  unicode(self.readDictEverySeconds[TT])+ " " + \
						  unicode(self.timeoutDICT)+ \
						  " \""+self.commandOnServer[uType]+"\" "
					if uType.find("AP") >-1:
						 cmd += "  /var/log/messages"
					else:
						 cmd += "  doNotSendAliveMessage"

				else:
					cmd = "/usr/bin/expect	'" + \
						  self.pathToPlugin +self.expectCmdFile[uType] + "' " + \
						"'"+userid + "' '"+passwd + "' " + \
						  ipNumber + " " + \
						  self.promptOnServer[uType]  +\
						  " \""+self.commandOnServer[uType]+"\" "

				if self.decideMyLog(u"Expect"): self.indiLOG.log(20,"startConnect: cmd {}".format(cmd) )
				ListenProcessFileHandle = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				##pid = ListenProcessFileHandle.pid
				##self.myLog( text=u" pid= " + unicode(pid) )
				msg = unicode(ListenProcessFileHandle.stderr)
				if msg.find("open file") == -1:	# try this again
					self.indiLOG.log(40,"uType {}; IP#: {}; error connecting {}".formaat(uType, ipNumber, msg) )
					self.sleep(20)
					continue

				# set the O_NONBLOCK flag of ListenProcessFileHandle.stdout file descriptor:
				flags = fcntl.fcntl(ListenProcessFileHandle.stdout, fcntl.F_GETFL)  # get current p.stdout flags
				fcntl.fcntl(ListenProcessFileHandle.stdout, fcntl.F_SETFL, flags | os.O_NONBLOCK)

				return ListenProcessFileHandle, ""
			self.sleep(0.1)
		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"startConnect: in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			return "", "error "+ unicode(e)
		self.indiLOG.log(40,"startConnect timeout, not able to  connect after 20 tries ")
		return "","error connecting"


	####-----------------	 ---------
	def testServerIfOK(self, ipNumber, uType):
		try:
			userid, passwd = self.getUidPasswd(uType)
			if userid =="": return False

			cmd = "/usr/bin/expect '" + self.pathToPlugin +"test.exp' '" + userid + "' '" + passwd + "' " + ipNumber
			if self.decideMyLog(u"Expect"): self.indiLOG.log(20,"testServerIfOK: {}".format(cmd) )
			ret = (subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate())
			test = ret[0].lower()
			tags = ["welcome","unifi","debian","edge","busybox","ubiquiti","ubnt","login"]+[self.promptOnServer[uType]]
			for tag in tags:
				if tag in test:	 return True
			self.indiLOG.log(20,"testServerIfOK: ==========={}  ssh response, tags {} not found : ==> \n{}".format(ipNumber, tags, test) )
		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"testServerIfOK in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return False
	####-----------------	 ---------
	def setAccessToLog(self, ipNumber, uType):
		try:
			userid, passwd = self.getUidPasswd(uType)
			if userid =="": return False

			cmd = "/usr/bin/expect '" + self.pathToPlugin +"setaccessToLog.exp' '" + userid + "' '" + passwd + "' " + ipNumber + " " +self.promptOnServer[uType]
			#if self.decideMyLog(u"Connection"): 
			if self.decideMyLog(u"Expect"): self.indiLOG.log(20,cmd)
			ret = (subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate())
			test = ret[0].lower()
			tags = ["welcome","unifi","debian","edge","busybox","ubiquiti","ubnt","login"]+[self.promptOnServer[uType]]
			for tag in tags:
				if tag in test:	 return True
			self.indiLOG.log(20,"\n==========={}  ssh response, tags {} not found : ==> {}".format(ipNumber, tags, test) )
		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"setAccessToLog in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return False

	####-----------------	 ---------
	def getUidPasswd(self, uType):
		if uType.find("VD") == -1:
			userid = self.unifiUserID
			passwd = self.unifiPassWd
		else:
			userid = self.nvrUNIXUserID
			passwd = self.nvrUNIXPassWd
		if userid == "":
			self.indiLOG.log(20,"Connection: {} login disabled, userid is empty".format(Type) )
		return userid, passwd



	####-----------------	 ---------
	def updateIndigoWithLogData(self):
		try:
			while not self.logQueue.empty():
				item = self.logQueue.get()

				lines			= item[0].split("\r\n")
				ipNumber		= item[1]
				apN				= item[2]
				uType			= item[3]
				xType			= item[4]

				## update device-ap with new timestamp, it is up
				if self.decideMyLog(u"Log"): self.indiLOG.log(20,"MS-----    {}    {}   {}  {} .. {}".format(ipNumber, apN, uType, xType, lines) )

				### update lastup for unifi devices
				if xType in self.MAC2INDIGO:
					for MAC in self.MAC2INDIGO[xType]:
						if xType== u"UN" and self.testIgnoreMAC(MAC, fromSystem="log"): continue
						if ipNumber == self.MAC2INDIGO[xType][MAC][u"ipNumber"]:
							self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
							break

				if	 uType == "APtail":
					self.doAPmessages(lines, ipNumber, apN)
				elif uType == "GWtail":
					self.doGWmessages(lines, ipNumber, apN)
				elif uType == "SWtail":
					self.doSWmessages(lines, ipNumber, apN)
				elif uType == "VDtail":
					self.doVDmessages(lines, ipNumber, apN)

				self.executeUpdateStatesList()

			self.logQueue.task_done()
		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"updateIndigoWithLogData in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



	####-----------------	 ---------
	def doVDmessages(self, lines, ipNumber,apN ):

		part="doVDmessages"+unicode(random.random()); self.blockAccess.append(part)
		for ii in range(90):
				if len(self.blockAccess) == 0 or self.blockAccess[0] == part: break # my turn?
				self.sleep(0.1)
		if ii >= 89: self.blockAccess = [] # for safety if too long reset list

		dateUTC = datetime.datetime.utcnow().strftime("%Y%m%d")
		## self.myLog( text="utc time: " + dateUTC, mType = "MS-VD----")
		uType = "VDtail"

		try:
			for line in lines:
				if len(line) < 10: continue
				##if self.decideMyLog(u"Video"):	 self.myLog( text="msg: "+line,mType = "MS-VD----")
				#self.myLog( text=ipNumber+"     "+ line, mType = "MS-VD----")
				## this is an event tring:
# logversion 1:
###1524837857.747 2018-04-27 09:04:17.747/CDT: INFO   Camera[F09FC2C1967B] type:start event:105 clock:58199223 (UVC G3 Micro) in ApplicationEvtBus-15
###1524837862.647 2018-04-27 09:04:22.647/CDT: INFO   Camera[F09FC2C1967B] type:stop event:105 clock:58204145 (UVC G3 Micro) in ApplicationEvtBus-18
## new format logVersion 2:
#1561518324.741 2019-06-25 22:05:24.741/CDT: INFO   [uv.analytics.motion] [AnalyticsService] [FCECDA1F1532|LivingRoom-Window-Flex] MotionEvent type:start event:1049 clock:111842854 in AnalyticsEvtBus-0

				itemsRaw = (line.strip()).split(" INFO ")
				if len(itemsRaw) < 2:
					#self.myLog( text=" INFO not found ",mType = "MS-VD----")
					continue


				try: timeSt= float(itemsRaw[0].split()[0])
				except:
					if self.decideMyLog(u"Video"):  self.indiLOG.log(20,"MS-VD----  bad float")
					continue

				items= itemsRaw[1].strip().split()
				if len(items) < 5:
					self.indiLOG.log(20,"MS-VD----  less than 5 items, line: "+line)
					continue

				logVersion = 0
				if items[0].find("Camera[") >-1: 			logVersion = 1
				elif itemsRaw[1].find("MotionEvent") >-1:	logVersion = 2
				else:
					if self.decideMyLog(u"Video"): self.indiLOG.log(20,"MS-VD----  no Camera, line: {}".format(line) )
					continue

				if logVersion == 1:
					#Camera[F09FC2C1967B]
					c = items[0].split("[")[1].strip("]").lower()
					# clock:58199223 (UVC G3 Micro) in 
					cameraName	 = " ".join(items[4:]).split("(")[1].split(")")[0].strip()
				if logVersion == 2:
					# [mac|name]
					# [FCECDA1F1532|LivingRoom-Window-Flex] 
					xx = items[2].split("|")
					cameraName = xx[1].strip("]")
					c = xx[0].strip("[").lower()

				if len(c) < 12:
					if self.decideMyLog(u"Video"): self.indiLOG.log(20,"MS-VD----  bad data, line: {}".format(line) )
					continue

				MAC = c[0:2]+":"+c[2:4]+":"+c[4:6]+":"+c[6:8]+":"+c[8:10]+":"+c[10:12]

				if self.testIgnoreMAC(MAC): continue

				evType = itemsRaw[1].split("type:")
				if len(evType) !=2: 
					if self.decideMyLog(u"Video"): self.indiLOG.log(20,"MS-VD----   no    type, line: {}".format(line) )
					continue
				evType = evType[1].split()[0]

				if evType not in ["start","stop"]:
					if self.decideMyLog(u"Video"): self.indiLOG.log(20,"MS-VD----  bad eventType {}".format(evType) )
					continue


				event = itemsRaw[1].split("event:")
				if len(event) !=2: 
					if self.decideMyLog(u"Video"): self.indiLOG.log(20,"MS-VD----   no    event, line: {}".format(line) )
					continue
				evNo = int(event[1].split()[0])


				if self.decideMyLog(u"Video"): self.indiLOG.log(20,"MS-VD----  parsed items: #{:5d}  {}    {:13.1f}  {} {}".format(evNo, evType, timeSt, MAC, cameraName) )


				if MAC not in self.cameras:
					 self.cameras[MAC] = {"cameraName":cameraName,"events":{},"eventsLast":{"start":0,"stop":0},"devid":-1,"uuid":"", "ip":"", "apiKey":""}

				if evNo not in	self.cameras[MAC]["events"]:
					self.cameras[MAC]["events"][evNo] = {"start":0,"stop":0}


				if len(self.cameras[MAC]["events"]) > self.unifiVIDEONumerOfEvents:
					delEvents={}
					for ev in self.cameras[MAC]["events"]:
						try:
							if int(evNo) - int(ev) > self.unifiVIDEONumerOfEvents:
								delEvents[ev]=True
						except:
							self.indiLOG.log(40,u"doVDmessages error in ev# {};	  evNo {};	 maxNumberOfEvents: {}\n to fix:  try to rest event count ".format(ev, evNo, self.unifiVIDEONumerOfEvents) )



					if len(delEvents) >0:
						if self.decideMyLog(u"Video"): self.indiLOG.log(20,"MS-VD----  {} number of events > {}; deleting {} events".format(cameraName, self.unifiVIDEONumerOfEvents, len(delEvents)) )
						for ev in delEvents:
							del	 self.cameras[MAC]["events"][ev]

				self.cameras[MAC]["events"][evNo][evType]  = timeSt
				##if self.decideMyLog(u"Video"): self.myLog( text=unicode(self.cameras[MAC]) , mType = "MS-VD----")


				devFound = False
				if "devid" in self.cameras[MAC]:
					try:
						dev = indigo.devices[self.cameras[MAC]["devid"]]
						devFound = True
					except: pass
				if	not devFound:
					for dev in indigo.devices.iter("props.isCamera"):
						if "MAC" not in dev.states:	   continue
						#self.myLog( text=" testing "+ dev.name+"  "+ dev.states["MAC"] +"    " + MAC)
						if dev.states["MAC"] == MAC:
							devFound = True
							#self.myLog( text="           ... found")
							break

				if not devFound:
					try:
						dev = indigo.device.create(
							protocol=indigo.kProtocol.Plugin,
							address=MAC,
							name = "Camera_"+cameraName+"_"+MAC ,
							description="",
							pluginId=self.pluginId,
							deviceTypeId="camera",
							props={"isCamera":True},
							folder=self.folderNameIDCreated,
							)
						dev.updateStateOnServer("MAC", MAC)
						dev.updateStateOnServer("eventNumber", -1)
						props = dev.pluginProps
						props["isCamera"] = True
						dev.replacePluginPropsOnServer()
						dev = indigo.devices[dev.id]
						self.saveCameraEventsStatus = True
					except	Exception, e:
							if len(unicode(e)) > 5:
								self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							if "NameNotUniqueError" in unicode(e):
								dev = indigo.devices["Camera_"+cameraName+"_"+MAC]
								self.indiLOG.log(20,"states  "+ unicode(dev.states))
								dev.updateStateOnServer("MAC", MAC)
								dev.updateStateOnServer("eventNumber", -1)
								props = dev.pluginProps
								props["isCamera"] = True
								dev.replacePluginPropsOnServer()
								dev = indigo.devices[dev.id]

							continue
					indigo.variable.updateValue("Unifi_New_Device",dev.name+"/"+MAC+"/")
					self.pendingCommand.append("getConfigFromNVR")

				self.cameras[MAC]["devid"] = dev.id

				##if self.decideMyLog(u"Video"): self.myLog( text=ipNumber+"    listenStart: "+ str(self.listenStart), mType = "MS-VD----")
				if dev.states["eventNumber"] > evNo or ( self.cameras[MAC]["events"][evNo][evType] <= self.cameras[MAC]["eventsLast"][evType]) :
					try:
						if time.time() - self.listenStart[ipNumber][uType] > 30:
							self.indiLOG.log(20,"MS-VD----  "+"rejected event number "+ str(evNo)+" resetting event No ; time after listener lauch: %5.1f"%(time.time() - self.listenStart[ipNumber][uType]))
							self.addToStatesUpdateList(dev.id,u"eventNumber", evNo)
					except	Exception, e:
							self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							self.indiLOG.log(40,"rejected event dump  "+ipNumber+"    " + str(self.listenStart))
							self.addToStatesUpdateList(dev.id,u"eventNumber", evNo)


				if self.decideMyLog(u"Video"): self.indiLOG.log(20,"MS-VD----  "+"event # "+ str(evNo)+" accepted ; delta T from listener lauch: %5.1f"%(time.time() - self.listenStart[ipNumber][uType]))
				dateStr = time.strftime(u"%Y-%m-%d %H:%M:%S",time.localtime(timeSt))
				if evType == "start":
					self.addToStatesUpdateList(dev.id,u"lastEventStart", dateStr )
					self.addToStatesUpdateList(dev.id,u"status", "REC")
					if self.imageSourceForEvent == "imageFromNVR":
						if dev.states["eventJpeg"] != self.changedImagePath+dev.name+".jpg": # update only if new
							self.addToStatesUpdateList(dev.id,"eventJpeg",self.changedImagePath+dev.name+"_event.jpg")
						self.getSnapshotfromNVR(dev.id, self.cameraEventWidth, self.changedImagePath+dev.name+"_event.jpg")
					if self.imageSourceForEvent == "imageFromCamera":
						if dev.states["eventJpeg"] != self.changedImagePath+dev.name+".jpg": # update only if new
							self.addToStatesUpdateList(dev.id,"eventJpeg",self.changedImagePath+dev.name+"_event.jpg")
						self.getSnapshotfromCamera(dev.id, self.changedImagePath+dev.name+"_event.jpg")

				elif evType == "stop":
					self.addToStatesUpdateList(dev.id,u"lastEventStop", dateStr )
					self.addToStatesUpdateList(dev.id,u"status", "off" )
					evLength  = float(self.cameras[MAC]["events"][evNo]["stop"]) - float(self.cameras[MAC]["events"][evNo]["start"])
					self.addToStatesUpdateList(dev.id,u"lastEventLength", int(evLength))

					try:
						if self.imageSourceForEvent == "imageFromDirectory":
							if dev.states["uuid"] !="":
								year = dateUTC[0:4]
								mm	 = dateUTC[4:6]
								dd	 = dateUTC[6:8]

								fromDir	   = self.videoPath+dev.states["uuid"]+"/"+year+"/"+mm+"/"+dd+"/meta/"
								toDir	   = self.changedImagePath
								last	   = 0.
								newestFile = ""
								filesInDir = ""

								if not os.path.isdir(fromDir):
										if not os.path.isdir(self.videoPath+dev.states["uuid"]):						os.mkdir(self.videoPath+dev.states["uuid"])
										if not os.path.isdir(self.videoPath+dev.states["uuid"]+"/"+year):				os.mkdir(self.videoPath+dev.states["uuid"]+"/"+year)
										if not os.path.isdir(self.videoPath+dev.states["uuid"]+"/"+year+"/"+mm):		os.mkdir(self.videoPath+dev.states["uuid"]+"/"+year+"/"+mm)
										if not os.path.isdir(self.videoPath+dev.states["uuid"]+"/"+year+"/"+mm+"/"+dd): os.mkdir(self.videoPath+dev.states["uuid"]+"/"+year+"/"+mm+"/"+dd)
										if not os.path.isdir(fromDir):													os.mkdir(fromDir)

								for testFile in os.listdir(fromDir):
									if testFile.find(".jpg") == -1: continue
									timeStampOfFile = os.path.getmtime(os.path.join(fromDir, testFile))
									if	timeStampOfFile > last:
										last = timeStampOfFile
										newestFile = testFile
								if newestFile =="":
									if self.decideMyLog(u"Video"): self.indiLOG.log(20,"MS-VD-EV-  "+dev.name+"  no file found")
									continue

								if dev.states["eventJpeg"] != fromDir+newestFile: # update only if new
									self.addToStatesUpdateList(dev.id,"eventJpeg",fromDir+newestFile)
									if os.path.isdir(toDir): # copy to destination directory
										if os.path.isfile(fromDir+newestFile):
											cmd = "cp '"+fromDir+newestFile+"' '"+toDir+dev.name+"_event.jpg' &"
											if self.decideMyLog(u"Video"): self.indiLOG.log(20,"MS-VD-EV-  copy event file: "+cmd)
											subprocess.Popen(cmd,shell=True)
									else:
										if self.decideMyLog(u"Video"): self.indiLOG.log(20,"MS-VD-EV-  "+"path "+ self.changedImagePath+"     does not exist.. no event files copied")

					except	Exception, e:
							if len(unicode(e)) > 5:
								self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

				self.cameras[MAC]["eventsLast"] = copy.copy(self.cameras[MAC]["events"][evNo])
				self.addToStatesUpdateList(dev.id,u"eventNumber", int(evNo) )
				self.executeUpdateStatesList()

		except	Exception, e:
				if len(unicode(e)) > 5:
					self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		if len(self.blockAccess)>0:	 del self.blockAccess[0]
		return



	####-----------------	 ---------
	def doGWmessages(self, lines,ipNumber,apN):
		try:
			devType	 = u"UniFi"
			isType	 = u"isUniFi"
			devName	 = u"UniFi"
			suffixN	 = u"DHCP"
			xType	 = u"UN"

			part="doGWmessages"+unicode(random.random()); self.blockAccess.append(part)
			for ii in range(90):
				if len(self.blockAccess) == 0 or self.blockAccess[0] == part: break # my turn?
				self.sleep(0.1)
			if ii >= 89: self.blockAccess = [] # for safety if too long reset list

# looking for dhcp refresh requests
#  Oct 26 22:20:00 GW sudo:		root : TTY=unknown ; PWD=/ ; USER=root ; COMMAND=/bin/sh -c echo -e '192.168.1.180\t iPhone.localdomain\t #on-dhcp-event 18:65:90:6a:b9:c' >> /etc/hosts

			tag = "TTY=unknown ; PWD=/ ; USER=root ; COMMAND=/bin/sh -c echo -e '"
			for line in lines:
				if len(line) < 10: continue
				if line.find(tag) ==-1: continue
				if self.decideMyLog(u"LogDetails"): self.indiLOG.log(20,"MS-GW---   "+line )
				items	= line .split(tag)
				if len(items) !=2: continue
				items	= items[1].split("' >> /etc/hosts")
				if len(items) != 2: continue
				items	= items[0].split("\\t")
				if len(items) != 3: continue
				ip		= items[0]
				name	= items[1]
				items	= items[2].split()
				if len(items) != 2: continue

				MAC = self.checkMAC(items[1])# fix a bug in hosts file
				if self.testIgnoreMAC(MAC, fromSystem="GW-msg"): continue

				new = True
				if MAC in self.MAC2INDIGO[xType]:
					try:
						dev = indigo.devices[self.MAC2INDIGO[xType][MAC][u"devId"]]
						if dev.deviceTypeId != devType: 1/0
						new = False
					except:
						if self.decideMyLog(u"LogDetails") or MAC in self.MACloglist: self.indiLOG.log(20,MAC + "  " + unicode(self.MAC2INDIGO[xType][MAC][u"devId"]) + " wrong " + devType)
						for dev in indigo.devices.iter("props."+isType):
							if "MAC" not in dev.states: continue
							if dev.states[u"MAC"] != MAC: continue
							self.MAC2INDIGO[xType][MAC]={}
							self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
							self.MAC2INDIGO[xType][MAC][u"devId"] = dev.id
							new = False
							break
						del self.MAC2INDIGO[xType][MAC]
				if not new:
					props=dev.pluginProps
					new = False
					if dev.states[u"ipNumber"] != ip:
						self.addToStatesUpdateList(dev.id,u"ipNumber", ip)
					## if a device asks for dhcp extension, it must be alive,  good for everyone..
					if True :#	useWhatForStatus" in props and props[u"useWhatForStatus"] == "DHCP":
						if dev.states[u"status"] != "up":
							self.setImageAndStatus(dev, "up",oldStatus= dev.states[u"status"],ts=time.time(), level=1, text1= dev.name.ljust(30) + u" status up        GW msg ", iType=u"STATUS-DHCP",reason=u"MS-DHCP "+u"up")
						else:
							if self.decideMyLog(u"LogDetails") or MAC in self.MACloglist: self.indiLOG.log(20,"MS-GW-   "+" restarting expTimer due to DHCP renew" )
						self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()

					#break

				if new:
					try:
						dev = indigo.device.create(
							protocol=indigo.kProtocol.Plugin,
							address=MAC,
							name=devName+"_" + MAC,
							description=self.fixIP(ip),
							pluginId=self.pluginId,
							deviceTypeId=devType,
							folder=self.folderNameIDCreated,
							props={u"useWhatForStatus":"DHCP","useAgeforStatusDHCP":"-1",isType:True})
					except	Exception, e:
						if len(unicode(e)) > 5:
							self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						continue
					self.setupStructures(xType, dev, MAC)
					self.setupBasicDeviceStates(dev, MAC, "UN", "", "", "", u" status up		 GW msg new device", "STATUS-DHCP")
					indigo.variable.updateValue("Unifi_New_Device",dev.name+"/"+MAC+"/"+ip)

			self.executeUpdateStatesList()
		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		self.executeUpdateStatesList()

		if len(self.blockAccess)>0:	 del self.blockAccess[0]


		return


	####-----------------	 ---------
	def doSWmessages(self, lines, ipNumber,apN ):
		return

		part="doSWmessages"+unicode(random.random()); self.blockAccess.append(part)
		for ii in range(90):
				if len(self.blockAccess) == 0 or self.blockAccess[0] == part: break # my turn?
				self.sleep(0.1)
		if ii >= 89: self.blockAccess = [] # for safety if too long reset list

		try:
			for line in lines:
				if len(line) < 2: continue
				if self.decideMyLog(u"Log"): self.indiLOG.log(20,"MS-SW---   "+ipNumber+"    " + line)


		except	Exception, e:
				if len(unicode(e)) > 5:
					self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		if len(self.blockAccess)>0:	 del self.blockAccess[0]
		return


	####-----------------	 ---------
	def doAPmessages(self, lines, ipNumberAP, apN):

		part="doAPmessages"+unicode(random.random()); self.blockAccess.append(part)
		for ii in range(90):
				if len(self.blockAccess) ==0 or self.blockAccess[0]==part:
					break
				self.sleep(0.1)
		if ii >= 89: self.blockAccess = [] # for safety if too long reset list

		try:
			devType = "UniFi"
			isType	= "isUniFi"
			devName = "UniFi"
			suffixN	 = "WiFi"
			xType	=  u"UN"

			for line in lines:
				if len(line) < 2: continue
				tags = line.split()
				MAC = ""
				if self.decideMyLog(u"Log"): self.indiLOG.log(20,u"MS-AP----  "+unicode(ipNumberAP)+"-"+unicode(apN) + "  " + line)

				ll = line.find("[HANDOVER]") + 10 +1 ## len of [HANDOVER] + one space
				if ll  > 30:
					if ll+17  >=  len(line):	 continue  # 17 = len of MAC address
					lin2 = line.split("[HANDOVER]")[1]
					tags = lin2.split()
					if len(tags) !=5: continue
					MAC = tags[0]
					if MAC.count(":") != 5:		 continue
					if self.testIgnoreMAC(MAC, fromSystem="AP-msg"): continue

					ipNumber = tags[4]	# new IP number of target AP
					self.HANDOVER[MAC] = {"tt":time.time(),"ipNumberNew":ipNumber, "ipNumberOld":tags[2]}
						### handle this: [HANDOVER]
						#13:40:42 AP----	  -192.168.1.4	Apr 16 13:40:41 4-kons daemon.notice hostapd: ath0: IEEE 802.11 UBNT-ROAM.get-sta-data for 18:65:90:6a:b9:0c
						#13:40:42 AP----	  -192.168.1.4	Apr 16 13:40:41 4-kons user.info kernel: [92232.074000] ubnt_roam [BASIC]:[HANDOVER] 18:65:90:6a:b9:0c from 192.168.1.4 to 192.168.1.5
						#13:40:42 AP----	  -192.168.1.4	Apr 16 13:40:41 4-kons daemon.notice hostapd: ath0: IEEE 802.11 UBNT-ROAM.sta-leave: 18:65:90:6a:b9:0c
						#13:40:42 AP----	  -192.168.1.4	Apr 16 13:40:41 4-kons daemon.info hostapd: ath0: STA 18:65:90:6a:b9:0c IEEE 802.11: disassociated
						#13:40:42 MS-AP-WiFi -	AP message received 18:65:90:6a:b9:0c  UniFi-iphone7-karl;	old/new associated 192.168.1.4/192.168.1.4
						#13:40:42 MS-AP-WiFi - 18:65:90:6a:b9:0c UniFi-iphone7-karl				check timer,  down token: disassociated time.time() -upt 1492368042.1

				###	 add test for :
				# 13:22:58 AP----	   -192.168.1.4	 Apr 15 13:22:57 4-kons user.info kernel: [ 4766.438000] ubnt_roam [BASIC]:Presence at AP 192.168.1.5 verified for 18:65:90:6a:b9:0c
				elif line.find("Presence at AP") > -1 and line.find("verified for") > -1:
					MAC = tags[-1]
					if MAC.count(":") != 5:
						 continue
					ipNumberAP = [-4]

				elif line.find("EVENT_STA_JOIN ") > -1 and line.find("verified for") > -1:
						ipNumberAP = [-4]

				else:
					try:
						ll = tags.index("STA")
						if ll+1 >=	len(tags):				   continue
						MAC = tags[ll + 1]
						if MAC.count(":") != 5:
							continue
						if	line.find("Authenticating") > 10:
							continue
						if	line.find("STA Leave!!") != -1 :
							continue
						if	line.find("STA enter") != -1:
							continue
					except Exception, e:
						if unicode(e).find("not in list") >-1: continue
						self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						continue

				if self.testIgnoreMAC(MAC, fromSystem="AP-msg"): continue


				if MAC != "":
					up = True
					GHz = ""
					token = ""
					if line.find("disassociated") > -1:
						token = "disassociated"
						up = False
					elif line.find("DISCONNECTED") > -1:
						token = "DISCONNECTED"
						up = False
					elif line.find(" sta_stats") > -1:
						token = "sta_stats"
						up = False
					if line.find("ath0:") > -1: GHz = "5"
					if line.find("ath1:") > -1: GHz = "2"

					if MAC in self.HANDOVER:
						if time.time()- self.HANDOVER[MAC]["tt"] <1.3: # protect for 1+ secs when in handover mode
							ipNumber = self.HANDOVER[MAC]["ipNumberNew"]
							up=True
						else:
							del self.HANDOVER[MAC]

					new = True
					if MAC in self.MAC2INDIGO[xType]:
						try:
							dev = indigo.devices[self.MAC2INDIGO[xType][MAC][u"devId"]]
							new = False
						except:
							if self.decideMyLog(u"all"): self.indiLOG.log(20,MAC + "     " + unicode(self.MAC2INDIGO[xType][MAC][u"devId"]) + " wrong " + devType)
							for dev in indigo.devices.iter("props."+isType):
								if "MAC" not in dev.states:		 continue
								if dev.states[u"MAC"] != MAC:	 continue
								self.MAC2INDIGO[xType][MAC]={}
								self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
								self.MAC2INDIGO[xType][MAC][u"devId"] = dev.id
								new = False
								break

					if not new:
						props =	 dev.pluginProps
						devId = unicode(dev.id)
						if devId not in self.upDownTimers:
							self.upDownTimers[devId] = {"down": 0, "up": 0}

						oldIP = dev.states[u"AP"]
						if ipNumberAP != oldIP.split("-")[0]:
							if up:
								self.addToStatesUpdateList(dev.id,u"AP", ipNumberAP+"-#"+unicode(apN))
							else:
								if self.decideMyLog(u"LogDetails") or MAC in self.MACloglist: self.indiLOG.log(20,"MS-AP-WF-0 "+u"AP message received "+MAC+"  "+ dev.name+";  old/new associated AP "+oldIP+"/"+unicode(ipNumberAP)+"-"+unicode(apN)  +" ignoring as associated to old AP")
								continue


						if "useWhatForStatus" in props and props[u"useWhatForStatus"] == "WiFi":

							if self.decideMyLog(u"LogDetails") or MAC in self.MACloglist: self.indiLOG.log(20,"MS-AP-WF-0 "+u"AP message received "+MAC+"  "+ dev.name+";  old/new associated "+oldIP+"/"+unicode(ipNumberAP)+"-#"+unicode(apN) )

							if up: # is up now
								self.MAC2INDIGO[xType][MAC][u"idleTime" + suffixN] = 0
								self.upDownTimers[devId][u"down"] = 0
								self.upDownTimers[devId][u"up"] = time.time()
								if dev.states[u"status"] != "up":
									self.setImageAndStatus(dev, "up",oldStatus= dev.states[u"status"], ts=time.time(), level=1, text1= dev.name.ljust(30) + u"status up  AP message received "+ipNumberAP, iType=u"MS-AP-WF-2 ",reason=u"MSG WiFi "+u"up")
								self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()

							else: # is down now
								try:
									if devId not in self.upDownTimers:
										self.upDownTimers[devId] = {"down": 0, "up": 0}

									if ipNumberAP == oldIP.split("-")[0]: # only if its on the same current AP
										dt = (time.time() - self.upDownTimers[devId][u"up"])

										if "useWhatForStatusWiFi" in props and props[u"useWhatForStatusWiFi"] in ["FastDown","Optimized"]:
											if self.decideMyLog(u"Logic") or MAC in self.MACloglist: self.indiLOG.log(20,"MS-AP-WF-3 "+MAC+" "+ dev.name.ljust(30) + u" check timer,    down;  token: " + token + " time.time() -upt %4.1f" % dt)
											if (dt) > 5.0:
												if dev.states[u"status"] == "up":
													#self.myLog( text=u" apmsg dw "+ dev.name+u" changed: old status: "+dev.states[u"status"]+u"; new	down")
													if props[u"useWhatForStatusWiFi"] == "FastDown":  # in fast down set it down right now
														self.setImageAndStatus(dev, "down",oldStatus="up", ts=time.time(), level=1, text1=MAC+" "+ dev.name.ljust(30) + u" status down    AP message received fast down-", iType=u"MS-AP-WF-4 ",reason=u"MSG DHCP "+u"down")
														self.upDownTimers[devId][u"down"] = time.time()
													else:  # in optimized give it 3 more secs
														self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time() - self.getexpT(props)+3
														self.upDownTimers[devId][u"down"] = time.time() +3
													self.upDownTimers[devId][u"up"]	  = 0.

										elif dt > 2.:
											self.upDownTimers[devId][u"down"] =	 time.time()  # this is a down message
											self.upDownTimers[devId][u"up"]	  = 0.
								except	Exception, e:
									if len(unicode(e)) > 5:
										self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


						if self.updateDescriptions:
							if dev.description.find("=WiFi")==-1 and  len(dev.description) >2:
								dev.description = dev.description+"=WiFi"
								dev.replaceOnServer()


					if new:
						try:

							dev = indigo.device.create(
								protocol=indigo.kProtocol.Plugin,
								address=MAC,
								name=devName+"_" + MAC,
								description="",
								pluginId=self.pluginId,
								deviceTypeId=devType,
								folder=self.folderNameIDCreated,
								props={u"useWhatForStatus":"WiFi","useWhatForStatusWiFi":"Expiration",isType:True})
						except Exception, e:
							if len(unicode(e)) > 5:
								self.indiLOG.log(40,"in Line {} has error={}   trying to create: {}_{}".format(sys.exc_traceback.tb_lineno, e, devName,MAC) )
							continue
						self.setupStructures(xType, dev, MAC)
						self.addToStatesUpdateList(dev.id,u"AP", ipNumberAP+"-#"+unicode(apN))
						self.MAC2INDIGO[xType][MAC][u"idleTime" + suffixN] = 0
						if unicode(dev.id) in self.upDownTimers:
							del self.upDownTimers[unicode(dev.id)]
						self.setupBasicDeviceStates(dev, MAC,  "UN", "", "", "", "    " +MAC+u" status up   AP msg new device", "MS-AP-WF-6 ")
						indigo.variable.updateValue("Unifi_New_Device",dev.name+"/"+MAC+"/")

						self.executeUpdateStatesList()
		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		self.executeUpdateStatesList()

		if len(self.blockAccess)>0:	 del self.blockAccess[0]

		return

	####-----------------	 ---------
	### double check up/down with ping
	####-----------------	 ---------
	def doubleCheckWithPing(self,newStatus, ipNumber, props,MAC,debLevel, section, theType,xType):

		if ("usePingUP" in props and props["usePingUP"] and newStatus =="up" ) or ( "usePingDOWN" in props and props["usePingDOWN"] and newStatus !="up") :
			if self.checkPing(ipNumber, nPings=1, waitForPing=500, calledFrom="doubleCheckWithPing") !=0:
				if self.decideMyLog(debLevel) or MAC in self.MACloglist: self.indiLOG.log(20,theType+" "+u" "+MAC+" "+section+" , status changed - not up , ping test failed" )
				return 1
			else:
				if self.decideMyLog(debLevel) or MAC in self.MACloglist: self.indiLOG.log(20,theType+" "+u" "+MAC+" "+section+" , status changed - not up , ping test OK" )
				if xType in self.MAC2INDIGO:
					self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
				return 0
		return -1


	####-----------------	 ---------
	### for the dict,
	####-----------------	 ---------
	def updateIndigoWithDictData2(self):
		try:
			while not self.logQueueDict.empty():
				next = self.logQueueDict.get()
				#self.myLog( text=unicode(next[0])[0:300] ,mType=u"up...Data2" )
				###if self.decideMyLog(u"Connection"): self.myLog( text=unicode(next)[0:1000] + "...." ,mType=u"MESS---")
				self.updateIndigoWithDictData(next[0],next[1],next[2],next[3],next[4])
			self.logQueueDict.task_done()
		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		if len(self.sendUpdateToFingscanList) >0: self.sendUpdatetoFingscanNOW()



	####-----------------	 ---------
	def updateIndigoWithDictData(self, apDict, ipNumber, apNumb, uType, unifiDeviceType):
		if len(apDict) < 1: return

		try:
			self.manageLogfile(apDict,apNumb,unifiDeviceType)

			if self.decideMyLog(u"Dict"): self.indiLOG.log(20,u"DC-----    "+unicode(ipNumber)+"    apNumb: "+unicode(apNumb)+"     uType: "+unicode(uType)+"    unifiDeviceType: "+unicode(unifiDeviceType)+"  "+ unicode(apDict)[0:100] + "...." )


			if unifiDeviceType =="GW":
			### gateway
				self.doGatewaydictSELF(apDict)
				self.doDHCPdictClients(apDict)



			elif unifiDeviceType == "SW":
				if "mac"		 not in apDict: return
				if u"port_table" not in apDict: return
				if u"hostname"	 not in apDict: return
				if u"ip"		 not in apDict: return

				MAC = apDict[u"mac"]
				hostname = apDict[u"hostname"].strip()
				ipNDevice = apDict[u"ip"]

				#################  update SWs themselves
				self.doSWdictSELF(apDict, apNumb, ipNDevice, MAC, hostname)

				#################  now update the devices on switch
				self.doSWITCHdictClients(apDict, apNumb, ipNDevice, MAC, hostname)

			elif unifiDeviceType == "AP":
				if "mac"		 not in apDict: return
				if u"vap_table"	 not in apDict: return
				if u"ip"		 not in apDict: return

				MAC		 = apDict[u"mac"]
				hostname = apDict[u"hostname"].strip()
				ipNDevice= apDict[u"ip"]

				for jj in range(len(apDict[u"vap_table"])):
					if "usage" in apDict[u"vap_table"][jj]: #skip if not wireless
						if apDict[u"vap_table"][jj]["usage"] == "downlink": continue
						if apDict[u"vap_table"][jj]["usage"] == "uplink":	continue
					channel = unicode(apDict[u"vap_table"][jj][u"channel"])
					if int(channel) >= 36:
						GHz = "5"
					else:
						GHz = "2"

	#################  update APs themselves
					self.doAPdictsSELF(apDict, jj, apNumb,	channel, GHz, ipNDevice, MAC, hostname)

	#################  now update the WiFi clients
					self.doWiFiCLIENTSdict(apDict[u"vap_table"][jj][u"sta_table"],	GHz, ipNDevice, apNumb)


	############  update neighbors
				if "radio_table"		 in	 apDict:
					self.doNeighborsdict(apDict[u"radio_table"], apNumb, ipNDevice)


		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


		return


	#################  update APs
	####-----------------	 ---------
	def checkInListSwitch(self):

		xType = u"UN"
		ignore ={}
		try:
			for dev in indigo.devices.iter("props.isSwitch"):
				nn  = int(dev.states["switchNo"])
				if not self.SWsEnabled[nn]:
					ignore[u"inListSwitch_"+str(nn)] = -1
				if  not self.isValidIP(self.ipNumbersOfSWs[nn]):
					ignore[u"inListSwitch_"+str(nn)] = -1

			for nn in range(_GlobalConst_numberOfSW):
				if not self.SWsEnabled[nn]:
					ignore[u"inListSwitch_"+str(nn)] = -1
				if  not self.isValidIP(self.ipNumbersOfSWs[nn]):
					ignore[u"inListSwitch_"+str(nn)] = -1

			if not self.UGAEnabled:
				ignore["inListDHCP"] = 0
				ignore["upTimeDHCP"] = ""
			if  not self.isValidIP(self.ipnumberOfUGA):
				ignore["inListDHCP"] = 0
				ignore["upTimeDHCP"] = ""

			save = False
			if len(ignore) > 0:
				for MAC in self.MAC2INDIGO[xType]:
					for xx in ignore:
						if xx in self.MAC2INDIGO[xType][MAC]:
							if self.MAC2INDIGO[xType][MAC][xx] != ignore[xx]:
								self.MAC2INDIGO[xType][MAC][xx]  = ignore[xx]
								save = True
						else:
								self.MAC2INDIGO[xType][MAC][xx]  = ignore[xx]
								save = True
				if save:
					self.saveMACdata()

		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return


	####-----------------	 ---------
	#################  update APs
	####-----------------	 ---------
	def doInList(self,suffixN,	wifiIP=""):


		suffix = suffixN.split("_")[0]
		try:
			## now check if device is not in dict, if not ==> initiate status --> down
			xType = u"UN"
			delMAC={}
			for MAC in self.MAC2INDIGO[xType]:
				if self.MAC2INDIGO[xType][MAC][u"inList"+suffixN]  == -1: continue	# do not test
				if self.MAC2INDIGO[xType][MAC][u"inList"+suffixN]  ==  1: continue	# is here
				try:
					devId = self.MAC2INDIGO[xType][MAC][u"devId"]
					dev	  = indigo.devices[devId]
					aW	  = dev.states["AP"]
					if wifiIP =="" or aW == wifiIP:
						self.MAC2INDIGO[xType][MAC][u"inList"+suffixN] = 0
					if wifiIP !="" and aW != wifiIP:											 continue
					if dev.states[u"status"] != "up":											 continue

					props= dev.pluginProps
					if "useWhatForStatus" not in props or props[u"useWhatForStatus"] != suffix:	 continue
				except	Exception, e:
					if unicode(e).find("timeout waiting") > -1:
						self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						self.indiLOG.log(40,"communication to indigo is interrupted")
						return
					self.indiLOG.log(40,"in Line {} has error={}  just deleted?.. then ignore message".format(sys.exc_traceback.tb_lineno, e) )
					self.indiLOG.log(40,u"deleting device from internal lists -- MAC:"+ MAC+";  devId:"+unicode(devId))
					delMAC[MAC]=1
					continue

				try:
					lastUpTT   = self.MAC2INDIGO[xType][MAC][u"lastUp"]
				except:
					lastUpTT = time.time() - 1000


				expT = self.getexpT(props)# this should be much faster than normal expiration
				if wifiIP !="" : expTUse  = max(expT/2.,10) # only for non wifi devices
				else:			 expTUse  = expT
				dt = time.time() - lastUpTT
				if dt < 						1 * expT:
					status = "up"
				elif dt < self.expTimeMultiplier  * expT:
					status = "down"
				else:
					status = "expired"


				if dev.states[u"status"] != status and status !="up":
					if "usePingUP" in props and props["usePingUP"]	and status !="up" and self.sendWakewOnLanAndPing(MAC,dev.states["ipNumber"], props=props, nPings=1, calledFrom="inList") == 0:
							if self.decideMyLog(u"Logic") or MAC in self.MACloglist: self.indiLOG.log(20,"List-"+suffix+u"    " +dev.states[u"MAC"]+" check, status changed - not up , ping test ok resetting to up" )
							self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
							continue

					# self.myLog( text=" 4 " +dev.name + " set to "+ status)
					#self.myLog( text=u" inList "+ dev.name+u" changed: old status: "+dev.states[u"status"]+u"; new  "+status)
					self.setImageAndStatus(dev, status,oldStatus=dev.states[u"status"], ts=time.time(), level=1, text1= dev.name.ljust(30) + u" in list status " + status.ljust(10) + " "+suffixN+"     dt= %5.1f" % dt + ";  expT= %5.1f" % expT+ "  wifi:" +wifiIP, iType=u"STATUS-"+suffix,reason=u"NotInList "+suffixN+u" "+wifiIP+u" "+status)
					#self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time() - expT
	   #self.executeUpdateStatesList()

			for MAC in delMAC:
				del	 self.MAC2INDIGO[xType][MAC]

		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return




	####-----------------	 ---------
	#### this does the unifswitch attached devices
	####-----------------	 ---------
	def doSWITCHdictClients(self, apDict, apNumb, ipNDevice, MACSW, hostnameSW):



		part="doSWITCHdict"+unicode(random.random()); self.blockAccess.append(part)
		for ii in range(90):
				if len(self.blockAccess) ==0 or self.blockAccess[0]==part:	break
				self.sleep(0.1)
		if ii >= 89: self.blockAccess = [] # for safety if too long reset list


		try:

			devType = "UniFi"
			isType	= "isUniFi"
			devName = "UniFi"
			suffix	= "SWITCH"
			xType	= u"UN"

			portTable = apDict[u"port_table"]


			if ipNDevice not in self.SWUP:
				if len(self.blockAccess)>0:	 del self.blockAccess[0]
				return

			switchNumber =-1
			for ii in range(_GlobalConst_numberOfSW):
				if not self.SWsEnabled[ii]:				continue
				if ipNDevice !=self.ipNumbersOfSWs[ii]: continue
				switchNumber = ii
				break

			if switchNumber <0:
				if len(self.blockAccess)>0:	 del self.blockAccess[0]
				return

			swN		=	unicode(switchNumber)
			suffixN = suffix+u"_"+swN


			for MAC in self.MAC2INDIGO[xType]:
				if len(MAC) < 16:
					self.MAC2INDIGO[xType][MAC][u"inList"+suffixN] = -1	 # was not here
					continue
				try:
					if self.MAC2INDIGO[xType][MAC][u"inList"+suffixN]  > 0:	 # was here was here , need to test
						self.MAC2INDIGO[xType][MAC][u"inList"+suffixN] = 0
				except:
						self.indiLOG.log(40,"error in doSWITCHdictClients: mac:"+ MAC+"  "+unicode(self.MAC2INDIGO[xType][MAC]) )
						return
				else:
					self.MAC2INDIGO[xType][MAC][u"inList"+suffixN] = -1	 # was not here


			for port in portTable:

				##self.myLog( text="port # "+ unicode(ii)+unicode(portTable[0:100])
				portN = unicode(port[u"port_idx"])
				if "mac_table" not in port: continue
				macTable =	port[u"mac_table"]
				if macTable == []:	continue
				if "port_idx" in port:
					portN = unicode(port[u"port_idx"])
				else:
					portN = ""
				isUpLink = False
				isDownLink = False

				if "is_uplink"	  in port and port["is_uplink"]:			isUpLink   = True
				elif "lldp_table" in port and len(port["lldp_table"]) > 0:	isDownLink = True

				#if isUpLink:		   continue
				#if isDownLink:		   continue

				for switchDevices in macTable:
					MAC = switchDevices[u"mac"]
					if self.testIgnoreMAC(MAC, fromSystem="SW-Dict"): continue

					if "age" in switchDevices:		age	   = switchDevices[u"age"]
					else: age = ""
					if "ip" in switchDevices:
													ip	   = switchDevices[u"ip"]
													try:	self.MAC2INDIGO[xType][MAC][u"ipNumber"] = ip
													except: continue
					else:							ip = ""
					if "uptime" in switchDevices:	newUp  = unicode(switchDevices[u"uptime"])
					else: newUp = ""
					if "hostname" in switchDevices: nameSW = unicode(switchDevices[u"hostname"]).strip()
					else: nameSW = ""


					ipx = self.fixIP(ip)
					new = True
					if MAC in self.MAC2INDIGO[xType]:
						try:
							dev = indigo.devices[self.MAC2INDIGO[xType][MAC][u"devId"]]
							if dev.deviceTypeId != devType: 1 / 0
							self.MAC2INDIGO[xType][MAC][u"inList"+suffixN] = 1 # is here
							new = False
						except:
							if self.decideMyLog(u"Logic") or MAC in self.MACloglist: self.indiLOG.log(20,MAC + "     " + unicode(self.MAC2INDIGO[xType][MAC][u"devId"]) + " wrong " + devType)
							for dev in indigo.devices.iter("props."+isType):
								if "MAC" not in dev.states:			continue
								if dev.states[u"MAC"] != MAC:		continue
								self.setupStructures(xType, dev, MAC, init=False)
								self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
								self.MAC2INDIGO[xType][MAC][u"inList"+suffixN] = 1
								new = False
								break

					if not new:

						self.MAC2INDIGO[xType][MAC][u"inList"+suffixN] = 1
						if self.decideMyLog(u"Dict") or MAC in self.MACloglist: self.indiLOG.log(20,u"DC-SW-00   "+ipNDevice +" "+ MAC+" "+ dev.name+"; IP:"+ip+"; AGE:"+unicode(age)+"; newUp:"+unicode(newUp)+ "; nameSW:"+unicode(nameSW))


						if not ( isUpLink or isDownLink ):	# only the direct switch can change the switch:port #s
							poe=""
							if len(dev.states[u"AP"]) < 5: # do not look for POE for wifi devices
								if MACSW in self.MAC2INDIGO["SW"]:	# do we know the switch
									if portN in self.MAC2INDIGO["SW"][MACSW][u"ports"]: # is the port in the switch
										if u"poe" in self.MAC2INDIGO["SW"][MACSW][u"ports"][portN] and self.MAC2INDIGO["SW"][MACSW][u"ports"][portN][u"poe"]  !="": # if empty dont add "-"
											poe = "-"+self.MAC2INDIGO["SW"][MACSW][u"ports"][portN][u"poe"]

							newPort = swN+":"+portN+poe

							if dev.states[u"SW_Port"] != newPort:
								self.addToStatesUpdateList(dev.id,u"SW_Port", newPort)


						props=dev.pluginProps

						newd = False
						devidd = unicode(dev.id)
						if ip != "":
							if dev.states[u"ipNumber"] != ip:
								self.addToStatesUpdateList(dev.id,u"ipNumber", ip)
							self.MAC2INDIGO[xType][MAC][u"ipNumber"] = ip
						self.MAC2INDIGO[xType][MAC][u"age"+suffixN] = age
						if dev.states[u"name"] != nameSW and nameSW !="":
							self.addToStatesUpdateList(dev.id,u"name", nameSW)

						newStatus = "up"
						oldStatus = dev.states[u"status"]
						oldUp	  = self.MAC2INDIGO[xType][MAC][u"upTime" + suffixN]
						self.MAC2INDIGO[xType][MAC][u"upTime" + suffixN] = unicode(newUp)
						if "useWhatForStatus" in props and props[u"useWhatForStatus"] in ["SWITCH","OptDhcpSwitch"]:
							if self.decideMyLog(u"Dict") or MAC in self.MACloglist: self.indiLOG.log(20,u"DC-SW-0    "+ipNDevice +" "+ MAC+" "+ dev.name+"; oldStatus:"+oldStatus+"; IP:"+ip+"; AGE:"+unicode(age)+"; newUp:"+unicode(newUp)+ "; oldUp:"+unicode(oldUp)+ "; nameSW:"+unicode(nameSW))
							if oldUp ==	 newUp and oldStatus =="up":
								if "useupTimeforStatusSWITCH" in props and props[u"useupTimeforStatusSWITCH"] :
									if "usePingDOWN" in props and props["usePingDOWN"]	and self.sendWakewOnLanAndPing(MAC,dev.states["ipNumber"], props=props, calledFrom ="doSWITCHdictClients") == 0:
										if self.decideMyLog(u"DictDetails") or MAC in self.MACloglist: self.indiLOG.log(20,u"DC-SW-1    "+ MAC+ u" reset timer for status up  notuptime const	but answers ping")
										self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
									else:
										if self.decideMyLog(u"DictDetails") or MAC in self.MACloglist: self.indiLOG.log(20,u"DC-SW-2    "+ MAC+ u"      SW DICT network_table , Uptime not changed, continue expiration timer")
								else: # will only expired if not in list anymore
									if "usePingDOWN" in props and props["usePingDOWN"]	 and status !="up" and self.sendWakewOnLanAndPing(MAC,dev.states["ipNumber"], props=props, calledFrom ="doSWITCHdictClients") != 0:
										if self.decideMyLog(u"DictDetails") or MAC in self.MACloglist: self.indiLOG.log(20,u"DC-SW-3    "+ MAC+ u" SW DICT network_table , but does not answer ping, continue expiration timer")
									else:
										if self.decideMyLog(u"DictDetails") or MAC in self.MACloglist: self.indiLOG.log(20,u"DC-SW-4    "+ MAC+ u" reset timer for status up     answers ping in  DHCP list")
										self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()


							if oldUp != newUp:
								if "usePingUP" in props and props["usePingUP"] and self.sendWakewOnLanAndPing(MAC,dev.states["ipNumber"], props=props, calledFrom ="doSWITCHdictClients") != 0:
									if self.decideMyLog(u"Dict") or MAC in self.MACloglist: self.indiLOG.log(20,u"DC-SW-5    "+  MAC+ u" SW DICT network_table , but does not answer ping, continue expiration timer")
								else:
									self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
									if self.decideMyLog(u"Dict") or MAC in self.MACloglist: self.indiLOG.log(20,u"DC-SW-0    "+  MAC+u" SW DICT network_tablerestart exp timer ")

						if self.updateDescriptions:
							oldIPX = dev.description.split("-")
							if ipx !="" and (oldIPX[0] != ipx or ( (dev.description != ipx + "-" + nameSW or len(dev.description) < 5) and len(nameSW)> 0 and  (dev.description).find("=WiFi") ==-1 )) :
								if oldIPX[0] != ipx and oldIPX[0] !="":
									indigo.variable.updateValue("Unifi_With_IPNumber_Change",dev.name+"/"+dev.states["MAC"]+"/"+oldIPX[0]+"/"+ipx)
								dev.description = ipx + "-" + nameSW
								if self.decideMyLog(u"DictDetails") or MAC in self.MACloglist: self.indiLOG.log(20,u"DC-SW-7    "+u"updating description for "+dev.name+"  to...."+ dev.description)
								dev.replaceOnServer()

						#break

					if new:
						try:
							dev = indigo.device.create(
								protocol=indigo.kProtocol.Plugin,
								address=MAC,
								name=devName+ "_" + MAC,
								description=ipx + "-" + nameSW,
								pluginId=self.pluginId,
								deviceTypeId=devType,
								folder=self.folderNameIDCreated,
								props={u"useWhatForStatus":"SWITCH","useupTimeforStatusSWITCH":"",isType:True})

						except	Exception, e:
							if len(unicode(e)) > 5:
								self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							continue

						self.setupStructures(xType, dev, MAC)
						self.addToStatesUpdateList(dev.id,u"SW_Port", "")
						self.MAC2INDIGO[xType][MAC][u"age"+suffixN] = age
						self.MAC2INDIGO[xType][MAC][u"upTime"+suffixN] = newUp
						self.setupBasicDeviceStates(dev, MAC, xType, ip, "", "", u" status up          SWITCH DICT new Device", "STATUS-SW")
						self.MAC2INDIGO[xType][MAC][u"inList"+suffixN] = 1
						indigo.variable.updateValue("Unifi_New_Device",dev.name+"/"+MAC+"/"+ipx)

			self.doInList(suffixN)
			self.executeUpdateStatesList()



		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		#if time.time()-waitT > 0.001: #self.myLog( text=unicode(self.blockAccess).ljust(28)+part.ljust(18)+"    exectime> %6.3f"%(time.time()-waitT)+ " @ "+datetime.datetime.now().strftime("%M:%S.%f")[:-3])
		if len(self.blockAccess)>0:	 del self.blockAccess[0]

		return

	####-----------------	 ---------
	def doDHCPdictClients(self, gwDict):

		part="doDHCPdictClients"+unicode(random.random()); self.blockAccess.append(part)
		for ii in range(90):
				if len(self.blockAccess) == 0 or self.blockAccess[0] == part: break # my turn?
				self.sleep(0.1)
		if ii >= 89: self.blockAccess = [] # for safety if too long reset list


		try:
			devType = u"UniFi"
			isType	= "isUniFi"
			devName = u"UniFi"
			suffixN = u"DHCP"
			xType	= u"UN"

			###########	 do DHCP devices
			if "network_table" not in gwDict:
				if self.decideMyLog(u"Logic"): self.indiLOG.log(20,u"DC-DHCP-E0 "+u"network_table not in dict "+unicode(gwDict[u"network_table"])[0:100])
				return
			for MAC in self.MAC2INDIGO[xType]:
				self.MAC2INDIGO[xType][MAC][u"inList"+suffixN] = 0


			host_table=""
			for item  in gwDict[u"network_table"]:
				if u"host_table" not in item: continue
				host_table = item["host_table"]
				break
			if host_table == "":
				if u"host_table" not in gwDict[u"network_table"]:
					if self.decideMyLog(u"Logic"): self.indiLOG.log(20,u"DC-DHCP-E1 "+"no DHCP in gwateway ?.. skipping info "+unicode(gwDict[u"network_table"])[0:100])
					return # DHCP not enabled on gateway, no info from GW available

			if "connect_request_ip" in gwDict:
				ipNumber = gwDict["connect_request_ip"]
			else:
				ipNumber = "            "
			##self.myLog( text=" GW dict: lan0" + unicode(lan0)[:100])

			if self.decideMyLog(u"DictDetails") or MAC in self.MACloglist: self.indiLOG.log(20,u"DC-DHCP-0  "+u"host_table len:"+unicode(len(host_table))+"     "+unicode(host_table)[0:100])
			if len(host_table) > 0:
				for item in host_table:

					##self.myLog( text=" nn: "+ unicode(nn)+"; lan: "+ unicode(lan)[0:200] )


					if "ip" in item:  ip = item[u"ip"]
					else:			  ip = ""
					MAC					 = item[u"mac"]
					if self.testIgnoreMAC(MAC, fromSystem="GW-Dict"): continue
					age					 = item[u"age"]
					uptime				 = item[u"uptime"]
					new					 = True
					#self.myLog( text=" GW dict: network_table" + unicode(host_table)[:100])
					if MAC in self.MAC2INDIGO[xType]:
						try:
							dev = indigo.devices[self.MAC2INDIGO[xType][MAC][u"devId"]]
							if dev.deviceTypeId != devType: 1 / 0
							# self.myLog( text=MAC+" "+ dev.name)
							new = False
							self.MAC2INDIGO[xType][MAC][u"inList" + suffixN] = 1
						except:
							if self.decideMyLog(u"Logic") or MAC in self.MACloglist: self.indiLOG.log(20,u"DC-DHCP-E1 "+MAC + "     " + unicode(self.MAC2INDIGO[xType][MAC]) + " wrong " + devType)
							for dev in indigo.devices.iter("props."+isType):
								if "MAC" not in dev.states: continue
								if dev.states[u"MAC"] != MAC: continue
								self.setupStructures(xType, dev, MAC, init=False)
								self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
								self.MAC2INDIGO[xType][MAC][u"inList" + suffixN] = 1
								new = False
								break

					if not new:
							if self.decideMyLog(u"DictDetails") or MAC in self.MACloglist: self.indiLOG.log(20,u"DC-DHCP-1  "+ipNumber+" "+ MAC +" " + dev.name +" ip:" + ip + " age:" + unicode(age) + " uptime:" + unicode(uptime))

							self.MAC2INDIGO[xType][MAC][u"inList"+suffixN] = True

							props = dev.pluginProps
							new = False
							if MAC != dev.states[u"MAC"]:
								self.addToStatesUpdateList(dev.id,u"MAC", MAC)
							if ip != "":
								if ip != dev.states[u"ipNumber"]:
									self.addToStatesUpdateList(dev.id,u"ipNumber", ip)
								self.MAC2INDIGO[xType][MAC][u"ipNumber"] = ip

							newStatus = "up"
							if "useWhatForStatus" in props and props[u"useWhatForStatus"] in ["DHCP","OptDhcpSwitch"]:

								if "useAgeforStatusDHCP" in props and props[u"useAgeforStatusDHCP"] != "-1"     and float(age) > float( props[u"useAgeforStatusDHCP"]):
										if dev.states[u"status"] == "up":
											if "usePingDOWN" in props and props["usePingDOWN"] and self.sendWakewOnLanAndPing(MAC,dev.states["ipNumber"], props=props, calledFrom ="doDHCPdictClients") == 0:  # did  answer
												if self.decideMyLog(u"DictDetails") or MAC in self.MACloglist: self.indiLOG.log(20,u"    "+ MAC+ u" reset exptimer DICT network_table AGE>max, but answers ping " + unicode(props[u"useAgeforStatusDHCP"]))
												self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
												newStatus = "up"
											else:
												if self.decideMyLog(u"DictDetails") or MAC in self.MACloglist: self.indiLOG.log(20,u"    "+ MAC+ u" set timer for status down	 GW DICT network_table AGE>max:" + unicode(props[u"useAgeforStatusDHCP"]))
												newStatus = "startDown"

								else: # good data, should be up
									if "usePingUP" in props and props["usePingUP"] and dev.states[u"status"] =="up" and self.sendWakewOnLanAndPing(MAC,dev.states["ipNumber"], props=props, calledFrom ="doDHCPdictClients") == 1:	# did not answer
											self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time() - self.getexpT(props) # down immediately
											self.setImageAndStatus(dev, "down",oldStatus=dev.states[u"status"], ts=time.time(), level=1, text1= dev.name.ljust(30) + u"set timer for status down    ping does not answer", iType=u"DC-DHCP-4  ",reason=u"DICT "+suffixN+u" up")
											newStatus = "down"
									elif dev.states[u"status"] != "up":
											self.setImageAndStatus(dev, "up",oldStatus=dev.states[u"status"], ts=time.time(), level=1, text1= dev.name.ljust(30) + u" status up  	GW DICT network_table", iType=u"DC-DHCP-4  ",reason=u"DICT "+suffixN+u" up")
											newStatus = "up"

								if newStatus =="up":
									self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()

							self.MAC2INDIGO[xType][MAC][u"age"+suffixN]		= age
							self.MAC2INDIGO[xType][MAC][u"upTime"+suffixN]	= uptime

							if self.updateDescriptions:
								oldIPX = dev.description.split("-")
								ipx = self.fixIP(ip)
								if ipx!="" and oldIPX[0] != ipx and oldIPX[0] !="":
									indigo.variable.updateValue("Unifi_With_IPNumber_Change",dev.name+"/"+dev.states["MAC"]+"/"+oldIPX[0]+"/"+ipx)
									oldIPX[0] = ipx
									dev.description = "-".join(oldIPX)
									if self.decideMyLog(u"DictDetails") or MAC in self.MACloglist: self.indiLOG.log(20,u"updating description for "+dev.name+"  to...."+ dev.description)
									dev.replaceOnServer()


					if new:
						try:
							dev = indigo.device.create(
								protocol=indigo.kProtocol.Plugin,
								address=MAC,
								name=devName + "_" + MAC,
								description=self.fixIP(ip),
								pluginId=self.pluginId,
								deviceTypeId=devType,
								folder=self.folderNameIDCreated,
								props={ "useWhatForStatus":"DHCP","useAgeforStatusDHCP": "-1","useWhatForStatusWiFi":"", isType:True})
						except	Exception, e:
							if len(unicode(e)) > 5:
								self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							continue

						self.setupStructures(xType, dev, MAC)
						self.MAC2INDIGO[xType][MAC][u"age"+suffixN]			= age
						self.MAC2INDIGO[xType][MAC][u"upTime"+suffixN]		= uptime
						self.MAC2INDIGO[xType][MAC][u"inList"+suffixN]		= True
						self.setupBasicDeviceStates(dev, MAC, xType, ip, "", "", u" status up		  GW DICT  new device","DC-DHCP-3   ")
						indigo.variable.updateValue("Unifi_New_Device",dev.name+"/"+MAC+"/"+ip)



			## now check if device is not in dict, if not ==> initiate status --> down
			self.doInList(suffixN)
			self.executeUpdateStatesList()


		except	Exception, e:
					if len(unicode(e)) > 5:
						self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		if len(self.blockAccess)>0:	 del self.blockAccess[0]
		return




	####-----------------	 ---------
	def doWiFiCLIENTSdict(self,adDict, GHz, ipNDevice,apN):

		part="doWiFiCLIENTSdict"+unicode(random.random()); self.blockAccess.append(part)
		for ii in range(90):
				if len(self.blockAccess) == 0 or self.blockAccess[0] == part: break # my turn?
				self.sleep(0.1)
		if ii >= 89: self.blockAccess = [] # for safety if too long reset list

		if len(adDict) ==0:
			if len(self.blockAccess)>0:	 del self.blockAccess[0]
			return

		if self.decideMyLog(u"Dict") : self.indiLOG.log(20,u"DC-WF---   "+unicode(adDict)[0:100] + "...." )
		try:
			devType = "UniFi"
			isType	= "isUniFi"
			devName = "UniFi"
			suffixN = "WiFi"
			xType	= u"UN"
			#self.myLog( text=u"DictDetails", ipNDevice + " GHz" +GHz, mType=u"DICT-WiFi")
			for MAC in self.MAC2INDIGO[xType]:
				if self.MAC2INDIGO[xType][MAC][u"AP"]  != ipNDevice: continue
				if self.MAC2INDIGO[xType][MAC][u"GHz"] != GHz:		 continue
				self.MAC2INDIGO[xType][MAC][u"inList"+suffixN] = 0


			for ii in range(len(adDict)):

				new				= True
				MAC				= unicode(adDict[ii][u"mac"])
				if self.testIgnoreMAC(MAC, fromSystem="WF-Dict"): continue
				ip				= unicode(adDict[ii][u"ip"])
				txRate			= unicode(adDict[ii][u"tx_rate"])
				rxRate			= unicode(adDict[ii][u"rx_rate"])
				rxtx			= rxRate+"/"+txRate+" [Kb]"
				signal			= unicode(adDict[ii][u"signal"])
				noise			= unicode(adDict[ii][u"noise"])
				idletime		= unicode(adDict[ii][u"idletime"])
				try:state		= format(int(adDict[ii][u"state"]), '08b')	## not in controller
				except: state	=""
				newUpTime		= unicode(adDict[ii][u"uptime"])
				try:
					nameCl		= unicode(adDict[ii][u"hostname"]).strip()
				except:
					nameCl		= ""
				powerMgmt = unicode(adDict[ii][u"state_pwrmgt"])
				ipx = self.fixIP(ip)
				#if	 MAC == "54:9f:13:3f:95:25":
				#self.myLog( text=u"DictDetails", ipNDevice+" checking MAC in dict "+MAC	 ,mType=u"DICT-WiFi")

				if MAC in self.MAC2INDIGO[xType]:
					try:
						dev = indigo.devices[self.MAC2INDIGO[xType][MAC][u"devId"]]
						if dev.deviceTypeId != devType: 1/0
						#self.myLog( text=MAC+" "+ dev.name)
						new = False
						self.MAC2INDIGO[xType][MAC][u"AP"]		   = ipNDevice
						self.MAC2INDIGO[xType][MAC][u"inList" + suffixN] = 1
						self.MAC2INDIGO[xType][MAC][u"GHz"]		   = GHz
					except:
						if self.decideMyLog(u"Logic") or MAC in self.MACloglist: self.indiLOG.log(20,MAC + "     " + unicode(self.MAC2INDIGO[xType][MAC]) + " wrong " + devType)
						for dev in indigo.devices.iter("props."+isType):
							if "MAC" not in dev.states: continue
							if dev.states[u"MAC"] != MAC: continue
							self.setupStructures(xType, dev, MAC, init=False)
							self.MAC2INDIGO[xType][MAC][u"lastUp"] =  time.time()
							self.MAC2INDIGO[xType][MAC][u"GHz"] = GHz
							self.MAC2INDIGO[xType][MAC][u"AP"] = ipNDevice
							self.MAC2INDIGO[xType][MAC][u"inList" + suffixN] = 1
							new = False
							break
				else:
					pass


				if not new:
						props=dev.pluginProps
						if self.decideMyLog(u"DictDetails") or MAC in self.MACloglist:
							self.indiLOG.log(20,u"DC-WF-NN   "+(ipNDevice +" " + MAC + " " + dev.name +  " GHz:" + GHz + " ip:" + ip +
											"  txRate:" + txRate + " rxRate:" + rxRate+ " uptime:" + newUpTime +
											"  signal:" + signal + "  name:" + nameCl + "  powerMgmt:" + powerMgmt))
						devidd = unicode(dev.id)

						oldAssociated =	 dev.states[u"AP"].split("-")[0]
						newAssociated =	 ipNDevice
						try:	 oldIdle =	int(self.MAC2INDIGO[xType][MAC][u"idleTime" + suffixN])
						except:	 oldIdle = 0

						# this is for the case when device switches betwen APs and the old one is still sending.. ignore that one
						if dev.states[u"AP"].split("-")[0] != ipNDevice:
							try:
								if oldIdle < 600 and  int(idletime) > oldIdle: continue # oldIdle <600 is to catch expired devices
							except:
								pass

						if dev.states[u"AP"]!= ipNDevice+"-#"+unicode(apN):
							self.addToStatesUpdateList(dev.id,u"AP", ipNDevice+"-#"+unicode(apN))

						self.MAC2INDIGO[xType][MAC][u"inList"+suffixN] = 1

						if ip != "":
							if dev.states[u"ipNumber"] != ip:
								self.addToStatesUpdateList(dev.id,u"ipNumber", ip)
							self.MAC2INDIGO[xType][MAC][u"ipNumber"] = ip

						if dev.states[u"name"] != nameCl and nameCl !="":
							self.addToStatesUpdateList(dev.id,u"name", nameCl)

						if dev.states[u"GHz"] != GHz:
							self.addToStatesUpdateList(dev.id,u"GHz", GHz)

						if dev.states[u"powerMgmt"+suffixN] != powerMgmt:
							self.addToStatesUpdateList(dev.id,u"powerMgmt"+suffixN, powerMgmt)

						if dev.states[u"rx_tx_Rate"+suffixN] != rxtx:
							self.addToStatesUpdateList(dev.id,u"rx_tx_Rate"+suffixN, rxtx)

						if dev.states[u"noise"+suffixN] != noise:
							uD = True
							try:
								if abs(int(dev.states[u"noise"+suffixN])- int(noise)) < 3:
									uD=	 False
							except: pass
							if uD: self.addToStatesUpdateList(dev.id,u"noise"+suffixN, noise)

						if dev.states[u"signal"+suffixN] != signal:
							uD = True
							try:
								if abs(int(dev.states[u"signal"+suffixN])- int(signal)) < 3:
									uD=	 False
							except: pass
							if uD: self.addToStatesUpdateList(dev.id,u"signal"+suffixN, signal)

						try:	oldUpTime = unicode(int(self.MAC2INDIGO[xType][MAC][u"upTime"+suffixN]))
						except: oldUpTime = "0"
						self.MAC2INDIGO[xType][MAC][u"upTime"+suffixN] = newUpTime

						if dev.states[u"state" + suffixN] != state:
							self.addToStatesUpdateList(dev.id,u"state" + suffixN, state)

						if dev.states[u"AP"].split("-")[0] != ipNDevice:
							self.addToStatesUpdateList(dev.id,u"AP", ipNDevice+"-#"+unicode(apN) )

						if idletime != "":
							self.MAC2INDIGO[xType][MAC][u"idleTime" + suffixN] =  idletime

						oldStatus = dev.states[u"status"]

						if self.updateDescriptions:
							oldIPX = dev.description.split("-")
							if oldIPX[0] != ipx or (dev.description != ipx + "-" + nameCl+"=WiFi" or len(dev.description) < 5):
								if oldIPX[0] != ipx and oldIPX[0] !="":
									indigo.variable.updateValue("Unifi_With_IPNumber_Change",dev.name+"/"+dev.states["MAC"]+"/"+oldIPX[0]+"/"+ipx)
								if len(oldIPX) < 2:
									oldIPX.append(nameCl.strip("-"))
								elif len(oldIPX) == 2 and oldIPX[1] == "":
									if nameCl != "":
										oldIPX[1] = nameCl.strip("-")
								oldIPX[0] = ipx
								newDescr = "-".join(oldIPX)
								if (dev.description).find("=WiFi")==-1:
									dev.description = newDescr+"=WiFi"
								else:
									dev.description = newDescr
								dev.replaceOnServer()

						# check what is used to determine up / down, make WiFi a priority
						if ( "useWhatForStatus" not in	props ) or ( "useWhatForStatus"     in props and props[u"useWhatForStatus"] != "WiFi" ):
							try:
								if time.time() - time.mktime(datetime.datetime.strptime(dev.states[u"created"], "%Y-%m-%d %H:%M:%S").timetuple()) <	 60:
									props = dev.pluginProps
									props[u"useWhatForStatus"]		= "WiFi"
									props[u"useWhatForStatusWiFi"]	= "Optimized"
									dev.replacePluginPropsOnServer(props)
									props = dev.pluginProps
							except:
								self.addToStatesUpdateList(dev.id,u"created", datetime.datetime.now().strftime(u"%Y-%m-%d %H:%M:%S"))
								props = dev.pluginProps
								props[u"useWhatForStatus"]		= "WiFi"
								props[u"useWhatForStatusWiFi"]	= "Optimized"
								dev.replacePluginPropsOnServer(props)
								props = dev.pluginProps

						if "useWhatForStatus" in props and props[u"useWhatForStatus"] == "WiFi":

							if "useWhatForStatusWiFi" not in props or ("useWhatForStatusWiFi" in props and	props[u"useWhatForStatusWiFi"] !="FastDown"):

								try:	 newUpTime = int(newUpTime)
								except:	 newUpTime = int(oldUpTime)
								try:
									idleTimeMaxSecs	 = float(props[u"idleTimeMaxSecs"])
								except:
									idleTimeMaxSecs = 5
								if self.decideMyLog(u"Logic") or MAC in self.MACloglist: self.indiLOG.log(20,ipNDevice +" "+MAC+" "+ dev.name+"newUpTime:"+unicode(newUpTime)+"    oldUpTime:"+ unicode(oldUpTime)+"  idletime:"+ unicode(idletime)+"    idleTimeMaxSecs:"+unicode(idleTimeMaxSecs)+"  old/new associated "+unicode(oldAssociated.split("-")[0])+"/"+unicode(newAssociated) )


								if "useWhatForStatusWiFi" in props and ( props[u"useWhatForStatusWiFi"] =="Optimized"):

									if oldStatus == "up":
										expT =self.getexpT(props)
										if (  float(newUpTime) != float(oldUpTime)	) or  (	 float(idletime)  < idleTimeMaxSecs	 ):
												if self.decideMyLog(u"Logic") or MAC in self.MACloglist: self.indiLOG.log(20,u"DC-WF-03-  "+MAC+" "+dev.name.ljust(30) + u" reset exptimer     WiFi DICT use idle...= ")
												self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
										else:
											if ( oldAssociated.split("-")[0] != newAssociated ): # ignore new AP
												if self.decideMyLog(u"Logic") or MAC in self.MACloglist: self.indiLOG.log(20,u"DC-WF-03-  "+MAC+" "+dev.name.ljust(30) + u" reset exptimer, new AP    WiFi DICT")
												self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
											else: # same old
												if self.decideMyLog(u"Logic") or MAC in self.MACloglist: self.indiLOG.log(20,u"DC-WF-03-  "+MAC+" "+dev.name.ljust(30) + u" set timer to expire   WiFi DICT use idle...= ")
												#self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time() - expT
												self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()- self.getexpT(props) + 10

									else: # old = down
										if ( float(newUpTime) != float(oldUpTime) ) or	(  float(idletime)	<= idleTimeMaxSecs	):
											self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
											self.setImageAndStatus(dev, "up",oldStatus=oldStatus,ts=time.time(),reason=u"DICT "+suffixN+u" "+ipNDevice+u" up Optimized")
											if self.decideMyLog(u"Logic") or MAC in self.MACloglist: self.indiLOG.log(20,u"DC-WF-04-  "+MAC+" "+dev.name.ljust(30) + u" status up       WiFi DICT use idle")
										else:
											if ( oldAssociated.split("-")[0] != newAssociated ): # ignore new AP
												if self.decideMyLog(u"Logic") or MAC in self.MACloglist: self.indiLOG.log(20,u"DC-WF-04-  "+MAC+" "+dev.name.ljust(30) + u" status up	new AP     WiFi DICT use idle")
												self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()


								elif "useWhatForStatusWiFi" in props and (props[u"useWhatForStatusWiFi"] =="IdleTime" ):
									if self.decideMyLog(u"Logic") or MAC in self.MACloglist: self.indiLOG.log(20,u"   "+ dev.name+u" IdleTime..  checking IdleTime/max: "+unicode(idletime)+"/"+props[u"idleTimeMaxSecs"] +"  old/new associated "+unicode(oldAssociated.split("-")[0])+"/"+unicode(newAssociated))
									try:
										idleTimeMaxSecs	 = float(props[u"idleTimeMaxSecs"])
									except:
										idleTimeMaxSecs = 5

									if float(idletime)	> idleTimeMaxSecs and oldStatus == "up":
										if ( oldAssociated.split("-")[0] == newAssociated ):
											if "usePingDOWN" in props and props["usePingDOWN"] and self.sendWakewOnLanAndPing(MAC,dev.states["ipNumber"], props=props, calledFrom ="doWiFiCLIENTSdict") ==0:
													if self.decideMyLog(u"Logic"): self.indiLOG.log(20,u"DC-WF-I1-  "+dev.states[u"MAC"]+"  reset exptimer  - , ping test ok" )
													self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
											else:
												self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()- self.getexpT(props) + 10
										else:
											if self.decideMyLog(u"Logic") or MAC in self.MACloglist: self.indiLOG.log(20,u"DC-WF-IS-  "+MAC+" "+dev.name.ljust(30) + u" status up	new AP     WiFi DICT use idle")
											self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()

									elif float(idletime)  <= idleTimeMaxSecs:
										if self.decideMyLog(u"Logic") or MAC in self.MACloglist: self.indiLOG.log(20,u"DC-WF-I3-  "+MAC+" "+dev.name.ljust(30) + u" reset exptimer         WiFi DICT use idle< max: "+unicode(idletime))
										self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
										if oldStatus != "up":
											self.setImageAndStatus(dev, "up",oldStatus=oldStatus,ts=time.time(),reason=u"DICT "+ipNDevice+u" "+suffixN+u" up idle-time")
											if self.decideMyLog(u"Logic") or MAC in self.MACloglist: self.indiLOG.log(20,u"DC-WF-I4-   "+MAC+" "+dev.name.ljust(30) + u" status up     WiFi DICT use idle")


								elif "useWhatForStatusWiFi" in props and (props[u"useWhatForStatusWiFi"] == "UpTime" ):
									if newUpTime == oldUpTime and oldStatus == "up":
										if "usePingUP" in props and props["usePingUP"] and self.sendWakewOnLanAndPing(MAC,dev.states["ipNumber"], props=props, calledFrom ="doWiFiCLIENTSdict") == 0:
												if self.decideMyLog(u"Logic") or MAC in self.MACloglist:self.indiLOG.log(20,u"DC-WF-UT-  "+dev.states[u"MAC"]+" reset exptimer  , ping test ok" )
												self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
										#self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time() - self.getexpT(props)
										else:
											if self.decideMyLog(u"Logic") or MAC in self.MACloglist: self.indiLOG.log(20,u"DC-WF-U1-  "+MAC+" "+dev.name.ljust(30) + u" set timer for status down	   WiFi DICT use Uptime same ")

									elif newUpTime != oldUpTime and oldStatus != u"up":
										self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
										self.setImageAndStatus(dev, u"up",oldStatus=oldStatus, ts=time.time(), level=1, text1=dev.name.ljust(30) + " "+MAC+u" status up		WiFi DICT use uptime",iType=u"DC-WF-U2",reason=u"DICT "+ipNDevice+u" "+suffixN+u" up time")

									elif oldStatus == u"up":
										if self.decideMyLog(u"Logic") or MAC in self.MACloglist: self.indiLOG.log(20,u"DC-WF-03-  "+dev.states[u"MAC"]+" reset exptimer  , normal extension" )
										self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()


								else:
									self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
									if oldStatus != "up":
										self.setImageAndStatus(dev, "up", oldStatus=oldStatus,level=1, text1=dev.name.ljust(30) + " "+MAC+u" status up    WiFi DICT general", iType=u"DC-WF-UE   ",reason=u"DICT "+suffixN+u" "+ipNDevice+u" up else")
							continue

							#break

				if new:
					try:
						dev = indigo.device.create(
							protocol=indigo.kProtocol.Plugin,
							address=MAC,
							name=devName + u"_" + MAC,
							description=ipx + u"-" + nameCl+"=Wifi",
							pluginId=self.pluginId,
							deviceTypeId=devType,
							folder=self.folderNameIDCreated,
							props={u"useWhatForStatus":u"WiFi", u"useWhatForStatusWiFi":u"Expiration",isType:True})
					except	Exception, e:
						if len(unicode(e)) > 5:
							self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						try:
							devName += u"_"+( unicode(time.time() - int(time.time())) ).split(".")[1] # create random name
							self.indiLOG.log(30,u"trying again to create device with differnt name "+devName)
							dev = indigo.device.create(
								protocol=indigo.kProtocol.Plugin,
								address=MAC,
								name=devName + u"_" + MAC,
								description=ipx + u"-" + nameCl+"=Wifi",
								pluginId=self.pluginId,
								deviceTypeId=devType,
								folder=self.folderNameIDCreated,
								props={u"useWhatForStatus":u"WiFi", u"useWhatForStatusWiFi":u"Expiration",isType:True})
						except	Exception, e:
							if len(unicode(e)) > 5:
								self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							continue


					self.setupStructures(xType, dev, MAC)
					self.setupBasicDeviceStates(dev, MAC, xType, ip, ipNDevice, "", u" status up   WiFi DICT new Device", "DC-AP-WF-f ")
					self.addToStatesUpdateList(dev.id,u"AP", ipNDevice+"-#"+unicode(apN))
					self.addToStatesUpdateList(dev.id,u"powerMgmt"+suffixN, powerMgmt)
					self.addToStatesUpdateList(dev.id,u"name", nameCl)
					self.addToStatesUpdateList(dev.id,u"rx_tx_Rate" + suffixN, rxtx)
					self.addToStatesUpdateList(dev.id,u"signal" + suffixN, signal)
					self.addToStatesUpdateList(dev.id,u"noise" + suffixN, noise)
					self.MAC2INDIGO[xType][MAC][u"idleTime" + suffixN] = idletime
					self.MAC2INDIGO[xType][MAC][u"inList"+suffixN] = 1
					self.addToStatesUpdateList(dev.id,u"state"+suffixN, state)
					self.MAC2INDIGO[xType][MAC][u"upTime"+suffixN] = newUpTime
					indigo.variable.updateValue("Unifi_New_Device", dev.name+"/"+MAC+"/"+ipx)


			self.doInList(suffixN,wifiIP=ipNDevice)
			self.executeUpdateStatesList()

		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		#if time.time()-waitT > 0.001: #self.myLog( text=unicode(self.blockAccess).ljust(28)+part.ljust(18)+"    exectime> %6.3f"%(time.time()-waitT)+ " @ "+datetime.datetime.now().strftime("%M:%S.%f")[:-3])
		if len(self.blockAccess)>0:	 del self.blockAccess[0]
		return



	####-----------------	 ---------
	## AP devices themselves  DICT
	####-----------------	 ---------
	def doAPdictsSELF(self,apDict, apInd, apNumb, channel, GHz, ipNDevice, MAC, hostname):

		part="doAPdictsSELF"+unicode(random.random()); self.blockAccess.append(part)
		for ii in range(90):
				if len(self.blockAccess) == 0 or self.blockAccess[0] == part: break # my turn?
				self.sleep(0.1)
		if ii >= 89: self.blockAccess = [] # for safety if too long reset list

		if "model_display" in apDict:  model = (apDict[u"model_display"])
		else:
			self.indiLOG.log(30,u"model_display not in dict doAPdicts")
			model = ""

		shortC	= apDict[u"vap_table"][apInd]

		devType ="Device-AP"
		isType	= "isAP"
		devName = "AP"
		xType	= "AP"
		try:

				nStations = unicode(shortC[u"num_sta"])
				essid	  = unicode(shortC[u"essid"])
				radio	  = unicode(shortC[u"radio"])
				tx_power  = unicode(shortC[u"tx_power"])

				new = True
				if MAC in self.MAC2INDIGO[xType]:
					try:
						dev = indigo.devices[self.MAC2INDIGO[xType][MAC]["devId"]]
						if dev.deviceTypeId != devType: 1 / 0
						#self.myLog( text=MAC + " " + dev.name)
						new = False
					except:
						if self.decideMyLog(u"Logic"): self.indiLOG.log(20,MAC + "  " + unicode(self.MAC2INDIGO[xType][MAC]) + " wrong " + devType)
						for dev in indigo.devices.iter("props."+isType):
							if "MAC" not in dev.states: continue
							if dev.states[u"MAC"] != MAC: continue
							self.MAC2INDIGO[xType][MAC][u"devId"] = dev.id
							new = False
							break
				if not new:
						if self.decideMyLog(u"DictDetails") or MAC in self.MACloglist: self.indiLOG.log(20,u"DC-AP---   "+ipNDevice + " hostname:" + hostname + " MAC:" + MAC + " GHz:" + GHz + "  essid:" + essid + " channel:" + channel + "    nStations:" + nStations + "     tx_power:" + tx_power + "    radio:" + radio )
						if u"uptime" in apDict and apDict[u"uptime"] !="":
							if u"upSince" in dev.states:
								self.addToStatesUpdateList(dev.id,u"upSince", time.strftime("%Y-%d-%m %H:%M:%S", time.localtime(time.time() - apDict[u"uptime"])) )
						if tx_power != dev.states[u"tx_power_" + GHz]:
							self.addToStatesUpdateList(dev.id,u"tx_power_" + GHz, tx_power)
						if channel != dev.states[u"channel_" + GHz]:
							self.addToStatesUpdateList(dev.id,u"channel_" + GHz, channel)
						if essid != dev.states[u"essid_" + GHz]:
							self.addToStatesUpdateList(dev.id,u"essid_" + GHz, essid)
						if nStations != dev.states[u"nStations_" + GHz]:
							self.addToStatesUpdateList(dev.id,u"nStations_" + GHz, nStations)
						if radio != dev.states[u"radio_" + GHz]:
							self.addToStatesUpdateList(dev.id,u"radio_" + GHz, radio)
						self.MAC2INDIGO[xType][MAC][u"ipNumber"] = ipNDevice
						if ipNDevice != dev.states[u"ipNumber"]:
							self.addToStatesUpdateList(dev.id,u"ipNumber", ipNDevice)
						if hostname != dev.states[u"hostname"]:
							self.addToStatesUpdateList(dev.id,u"hostname", hostname)
						if dev.states[u"status"] != "up":
							self.setImageAndStatus(dev, "up", oldStatus=dev.states[u"status"],ts=time.time(),  level=1, text1=dev.name.ljust(30) + u" status up            AP    DICT", reason="AP DICT", iType=u"STATUS-AP")
						self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
						if dev.states[u"model"] != model and model !="":
							self.addToStatesUpdateList(dev.id,u"model", model)
						if dev.states[u"apNo"] != apNumb:
							self.addToStatesUpdateList(dev.id,u"apNo", apNumb)

						self.setStatusUpForSelfUnifiDev(MAC)


				if new:
					try:
						dev = indigo.device.create(
							protocol=indigo.kProtocol.Plugin,
							address=MAC,
							name=devName + "_" + MAC,
							description=self.fixIP(ipNDevice) + "-" + hostname,
							pluginId=self.pluginId,
							deviceTypeId=devType,
							folder=self.folderNameIDCreated,
							props={u"useWhatForStatus":"",isType:True})
						self.setupStructures(xType, dev, MAC)
						self.setupBasicDeviceStates(dev, MAC, "AP", ipNDevice,"", "", u" status up            AP DICT  new AP", u"STATUS-AP")
						self.addToStatesUpdateList(dev.id,u"essid_" + GHz, essid)
						self.addToStatesUpdateList(dev.id,u"channel_" + GHz, channel)
						self.addToStatesUpdateList(dev.id,u"MAC", MAC)
						self.addToStatesUpdateList(dev.id,u"hostname", hostname)
						self.addToStatesUpdateList(dev.id,u"nStations_" + GHz, nStations)
						self.addToStatesUpdateList(dev.id,u"radio_" + GHz, radio)
						self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
						self.addToStatesUpdateList(dev.id,u"model", model)
						self.addToStatesUpdateList(dev.id,u"tx_power_" + GHz, tx_power)
						self.executeUpdateStatesList()
						self.buttonConfirmGetAPDevInfoFromControllerCALLBACK()
						indigo.variable.updateValue("Unifi_New_Device", dev.name+"/"+MAC+"/"+ipNDevice)
					except	Exception, e:
					  if len(unicode(e)) > 5:
							self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.executeUpdateStatesList()

		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		#if time.time()-waitT > 0.001: #self.myLog( text=unicode(self.blockAccess).ljust(28)+part.ljust(18)+"    exectime> %6.3f"%(time.time()-waitT)+ " @ "+datetime.datetime.now().strftime("%M:%S.%f")[:-3])
		if len(self.blockAccess)>0:	 del self.blockAccess[0]
		return




	####-----------------	 ---------
	def doGatewaydictSELF(self, gwDict):

		part="doGatewaydict"+unicode(random.random()); self.blockAccess.append(part)
		for ii in range(90):
				if len(self.blockAccess) == 0 or self.blockAccess[0] == part: break # my turn?
				self.sleep(0.1)
		if ii >= 89: self.blockAccess = [] # for safety if too long reset list

		try:

			devType = "gateway"
			devName = "gateway"
			isType	= "isGateway"
			xType	= u"GW"
			suffixN	 = "DHCP"
			##########	do gateway params  ###
			#self.myLog( text=" GW dict if_table:"+json.dumps(gwDict, sort_keys=True, indent=2 ) )

			if "if_table"			  not in gwDict: return
			if	  "config_port_table"	  in gwDict: table = "config_port_table"
			elif  "config_network_ports"  in gwDict: table = "config_network_ports"
			else:									 return

			#  get lan info ------
			ipNDevice	= ""
			MAClan		= ""
			MAC			= ""
			wan			= ""
			lan			= ""
			publicIP	= ""
			model		= ""
			cpuPercent	= ""
			memPercent	= ""
			temperature = ""
			temperature_Board_CPU 	= ""
			temperature_Board_PHY 	= ""
			temperature_CPU 		= ""
			temperature_PHY 		= ""
			MAC			= ""
			gateways	= ""
			MAClan		= ""
			wanUP		= ""
			wanPingTime = ""
			wanLatency	= ""
			wanDownload = ""
			wanUpload	= ""
			nameservers = "-"
			wanRunDate	= ""
			wanUpTime	= ""
			gateways	= "-"
			wanUpTime	= ""
			upTime		= ""

			if "connect_request_ip" in gwDict:
				ipNDevice = self.fixIP(gwDict["connect_request_ip"])
			if ipNDevice =="": return


			if table =="config_network_ports":
					if "LAN" in gwDict[table]:
						ifnameLAN = gwDict[table]["LAN"]
						for xx in range(len(gwDict[u"if_table"])):
							if "name" in gwDict[u"if_table"][xx] and gwDict[u"if_table"][xx]["name"] == ifnameLAN:
								lan = gwDict[u"if_table"][xx]
					if "WAN" in gwDict[table]:
						ifnameWAN = gwDict[table]["WAN"]
						for xx in range(len(gwDict[u"if_table"])):
							if "name" in gwDict[u"if_table"][xx] and gwDict[u"if_table"][xx]["name"] == ifnameWAN:
								wan = gwDict[u"if_table"][xx]

			elif table =="config_port_table":
				for xx in range(len(gwDict[table])):
					if "name" in gwDict[table][xx] and gwDict[table][xx]["name"].lower() == "lan":
						ifnameLAN = gwDict[table][xx]["ifname"]
						if "name" in gwDict[u"if_table"][xx] and gwDict[u"if_table"][xx]["name"] == ifnameLAN:
							lan = gwDict[u"if_table"][xx]
					if "name" in gwDict[table][xx] and gwDict[table][xx]["name"].lower() =="wan":
						ifnameWAN = gwDict[table][xx]["ifname"]
						if "name" in gwDict[u"if_table"][xx] and gwDict[u"if_table"][xx]["name"] == ifnameWAN:
							wan = gwDict[u"if_table"][xx]
			else: return

#			 self.myLog( text="wan" + unicode(wan) )
#			 self.myLog( text="lan" + unicode(lan) )
#			 self.myLog( text="gwDict" + json.dumps(gwDict["config_port_table"], sort_keys=True, indent=2) )
#			 self.myLog( text="if_table" + json.dumps(gwDict["if_table"], sort_keys=True, indent=2 ) )

			if wan == "": return
			if lan == "": return


			if "ip" in wan:	   publicIP	   = wan[u"ip"].split("/")[0]
			if "uptime" in wan:
				wanUpTime = self.convertTimedeltaToDaysHoursMin(wan[u"uptime"])

			if "mac" in wan:				MAC			= wan[u"mac"]
			if "gateways" in wan:			gateways	= "-".join(wan[u"gateways"])
			if "model_display" in gwDict:	model		= gwDict[u"model_display"]
			else:
				self.indiLOG.log(30,u"model_display not in dict doGatewaydict")

			if "system-stats" in gwDict:
				sysStats = gwDict["system-stats"]
				if "cpu" in sysStats:	 cpuPercent = sysStats["cpu"]
				if "mem" in sysStats:	 memPercent = sysStats["mem"]
				if "temps" in sysStats:
					if	len(sysStats["temps"]) > 0:
						if type(sysStats["temps"]) == type({}):
							try:
								for key,value in sysStats["temps"].iteritems():
									if   key =="Board (CPU)": 	temperature_Board_CPU 	= GT.getNumber(value)
									elif key =="Board (PHY)":	temperature_Board_PHY 	= GT.getNumber(value)
									elif key =="CPU": 			temperature_CPU 		= GT.getNumber(value)
									elif key =="PHY": 			temperature_PHY 		= GT.getNumber(value)
								#self.myLog( text="doGatewaydictSELF sysStats[temp]ok : "+temperature)
							except:
								self.indiLOG.log(30,"doGatewaydictSELF sysStats[temp]err : "+unicode(sysStats["temps"]))
						else:
							temperature	 = GT.getNumber(sysStats["temps"])
							#self.myLog( text="doGatewaydictSELF sysStats: empty "+unicode(sysStats))

			if "speedtest_lastrun" in wan and wan[u"speedtest_lastrun"] !=0:
											wanRunDate	   = datetime.datetime.fromtimestamp(float(wan[u"speedtest_lastrun"])).strftime(u"%Y-%m-%d %H:%M:%S") + u"[UTC]"
			if "mac" in lan:				MAClan		   = lan[u"mac"]
			if "up" in wan:					wanUP		   = "up" if wan[u"up"] else "down"
			if "speedtest_ping" in wan:		wanPingTime	   = "%4.1f" % wan[u"speedtest_ping"] + u"[ms]"
			if "latency" in wan:			wanLatency	   = "%4.1f" % wan[u"latency"] + u"[ms]"
			if "xput_down" in wan:			wanDownload	   = "%4.1f" % wan[u"xput_down"] + u"[Mb/S]"
			if "xput_up" in wan:			wanUpload	   = "%4.1f" % wan[u"xput_up"] + u"[Mb/S]"
			if "nameservers" in wan:		nameservers	   = "-".join(wan[u"nameservers"])

			if MAC =="": return

			new = True

			if MAC in self.MAC2INDIGO[xType]:
				try:
					dev = indigo.devices[self.MAC2INDIGO[xType][MAC]["devId"]]
					if dev.deviceTypeId != devType: 1 / 0
					#self.myLog( text=MAC + " " + dev.name)
					new = False
				except:
					if self.decideMyLog(u"Logic") or MAC in self.MACloglist: self.indiLOG.log(20,MAC + "     " + unicode(self.MAC2INDIGO[xType][MAC]) + " wrong " + devType)
					for dev in indigo.devices.iter("props."+isType):
						if "MAC" not in dev.states:			continue
						if dev.states[u"MAC"] != MAC:		continue
						self.MAC2INDIGO[xType][MAC]["devId"] = dev.id
						new = False
						break

			if not new:
					if u"uptime" in gwDict and gwDict[u"uptime"] !="":
						if u"upSince" in dev.states:
							self.addToStatesUpdateList(dev.id,u"upSince",	time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()-gwDict[u"uptime"])) )

					self.MAC2INDIGO[xType][MAC][u"ipNumber"] = ipNDevice
					self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()

					if gateways != dev.states[u"gateways"]:								self.addToStatesUpdateList(dev.id,u"gateways", gateways)
					if nameservers != dev.states[u"nameservers"]:						self.addToStatesUpdateList(dev.id,u"nameservers", nameservers)
					if MAClan != dev.states[u"MAClan"]:									self.addToStatesUpdateList(dev.id,u"MAClan", MAClan)
					if ipNDevice != dev.states[u"ipNumber"]:							self.addToStatesUpdateList(dev.id,u"ipNumber", ipNDevice)
					if publicIP != dev.states[u"publicIP"]:								self.addToStatesUpdateList(dev.id,u"publicIP", publicIP)
					if wanPingTime != dev.states[u"wanPingTime"]:						self.addToStatesUpdateList(dev.id,u"wanPingTime", wanPingTime)
					if wanLatency != dev.states[u"wanLatency"]:							self.addToStatesUpdateList(dev.id,u"wanLatency", wanLatency)
					if wanUpload != dev.states[u"wanUpload"]:							self.addToStatesUpdateList(dev.id,u"wanUpload", wanUpload)
					if wanRunDate != dev.states[u"wanRunDate"]:							self.addToStatesUpdateList(dev.id,u"wanRunDate", wanRunDate)
					if wanDownload != dev.states[u"wanDownload"]:						self.addToStatesUpdateList(dev.id,u"wanDownload", wanDownload)
					if wanUpTime != dev.states[u"wanUpTime"]:							self.addToStatesUpdateList(dev.id,u"wanUpTime", wanUpTime)
					if dev.states[u"wan"] != wanUP:										self.addToStatesUpdateList(dev.id,u"wan", wanUP)
					if dev.states[u"MAC"] != MAC:										self.addToStatesUpdateList(dev.id,u"MAC", MAC)
					if dev.states[u"model"] != model and model != "":					self.addToStatesUpdateList(dev.id,u"model", model)
					if dev.states[u"memPercent"] != cpuPercent and memPercent != "":	self.addToStatesUpdateList(dev.id,u"memPercent", memPercent)
					if dev.states[u"cpuPercent"] != cpuPercent and cpuPercent != "":	self.addToStatesUpdateList(dev.id,u"cpuPercent", cpuPercent)
					if dev.states[u"temperature"] != temperature and temperature != "": self.addToStatesUpdateList(dev.id,u"temperature", temperature)
					if dev.states[u"temperature_Board_CPU"] != temperature_Board_CPU and temperature_Board_CPU != "": self.addToStatesUpdateList(dev.id,u"temperature_Board_CPU", temperature_Board_CPU)
					if dev.states[u"temperature_Board_PHY"] != temperature_Board_PHY and temperature_Board_PHY != "": self.addToStatesUpdateList(dev.id,u"temperature_Board_PHY", temperature_Board_PHY)
					if dev.states[u"temperature_CPU"]		!= temperature_CPU 		 and temperature_CPU != "":		  self.addToStatesUpdateList(dev.id,u"temperature_CPU", temperature_CPU)
					if dev.states[u"temperature_PHY"]		!= temperature_PHY 		 and temperature_PHY != "":		  self.addToStatesUpdateList(dev.id,u"temperature_PHY", temperature_PHY)

					if dev.states[u"status"] != "up":									self.setImageAndStatus(dev, "up",oldStatus=dev.states[u"status"], ts=time.time(), level=1, text1=dev.name.ljust(30) + u" status up		   GW DICT if_table", reason="gateway DICT", iType=u"STATUS-GW")

					if self.decideMyLog(u"Dict") or MAC in self.MACloglist:			self.indiLOG.log(20,u"DC-GW-1--  "+MAC + "     ip:"+ ipNDevice+"    " + dev.name +"    new data")

					self.setStatusUpForSelfUnifiDev(MAC)


			if new:
				try:
					dev = indigo.device.create(
						protocol=indigo.kProtocol.Plugin,
						address=MAC,
						name=devName+"_" + MAC,
						description=self.fixIP(ipNDevice),
						pluginId=self.pluginId,
						deviceTypeId=devType,
						folder=self.folderNameIDCreated,
						props={u"useWhatForStatus":"",isType:True})
					self.setupStructures(xType, dev, MAC)
					self.addToStatesUpdateList(dev.id,u"MAC",			MAC)
					self.addToStatesUpdateList(dev.id,u"MAClan",		MAClan)
					self.addToStatesUpdateList(dev.id,u"wan",			wanUP)
					self.addToStatesUpdateList(dev.id,u"wanPingTime",	wanPingTime)
					self.addToStatesUpdateList(dev.id,u"wanLatency",	wanLatency)
					self.addToStatesUpdateList(dev.id,u"wanUpload",	wanUpload)
					self.addToStatesUpdateList(dev.id,u"wanDownload",	wanDownload)
					self.addToStatesUpdateList(dev.id,u"wanRunDate",	wanRunDate)
					self.addToStatesUpdateList(dev.id,u"wanUpTime",	wanUpTime)
					self.addToStatesUpdateList(dev.id,u"gateways",		gateways)
					self.addToStatesUpdateList(dev.id,u"nameservers",	nameservers)
					self.setupBasicDeviceStates(dev, MAC, xType, ipNDevice, "", "", u" status up         GW DICT new gateway if_table", u"STATUS-GW")
					indigo.variable.updateValue("Unifi_New_Device", dev.name+"/"+MAC+"/"+ipNDevice)
					if self.decideMyLog(u"Dict") or MAC in self.MACloglist: self.indiLOG.log(20,u"DC-GW-1--- "+">>"+MAC + "<<  ip:"+ ipNDevice+"  "+ dev.name +"  new dec" )
				except	Exception, e:
					if len(unicode(e)) > 5:
						self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.executeUpdateStatesList()



		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		#if time.time()-waitT > 0.001: #self.myLog( text=unicode(self.blockAccess).ljust(28)+part.ljust(18)+"    exectime> %6.3f"%(time.time()-waitT)+ " @ "+datetime.datetime.now().strftime("%M:%S.%f")[:-3])
		if len(self.blockAccess)>0:	 del self.blockAccess[0]
		return


	####-----------------	 ---------
	def convertTimedeltaToDaysHoursMin(self,uptime):
		try:
			ret = ""
			uptime = float(uptime)
			xx = unicode(datetime.timedelta(seconds=uptime)).replace(" days","").split(",")
			if len(xx) ==2:
				ret = xx[0]+"d "
				yy = xx[1].split(":")
				if len(yy) >1:
					ret += yy[0]+"h " +yy[1]+"m"
			if len(xx) ==1:
				yy = xx[0].split(":")
				if len(yy) >1:
					ret += yy[0]+"h " +yy[1]+"m"
			return ret
		except: pass


	####-----------------	 ---------
	def doNeighborsdict(self,apDict,apNumb,ipNDevice):
		part="doNeighborsdict"+unicode(random.random()); self.blockAccess.append(part)
		for ii in range(90):
				if len(self.blockAccess) == 0 or self.blockAccess[0] == part: break # my turn?
				self.sleep(0.1)
		if ii >= 89: self.blockAccess = [] # for safety if too long reset list

		try:
			devType =u"neighbor"
			devName =u"neighbor"
			isType = "isNeighbor"
			xType = u"NB"
			for kk in range(len(apDict)):

				shortR = apDict[kk][u"scan_table"]
				for shortC in shortR:
					MAC = unicode(shortC[u"bssid"])
					channel = unicode(shortC[u"channel"])
					essid = unicode(shortC[u"essid"])
					age = unicode(shortC[u"age"])
					adhoc = unicode(shortC[u"is_adhoc"])
					try:
						rssi = unicode(shortC[u"rssi"])
					except:
						rssi = ""
					if "model_display" in shortC:  model = (shortC[u"model_display"])
					else:
						model = ""

					new = True
					if int(channel) >= 36:
						GHz = u"5"
					else:
						GHz = u"2"
					if MAC in self.MAC2INDIGO[xType]:
						try:
							dev = indigo.devices[self.MAC2INDIGO[xType][MAC]["devId"]]
							if dev.deviceTypeId != devType: 1 / 0
							new = False
						except:
							if self.decideMyLog(u"Logic") or MAC in self.MACloglist: self.indiLOG.log(20,MAC + "     " + unicode(self.MAC2INDIGO[xType][MAC]) + " wrong " + devType)
							for dev in indigo.devices.iter("props."+isType):
								if "MAC" not in dev.states: continue
								if dev.states[u"MAC"] != MAC: continue
								self.setupStructures(xType, dev, MAC, init=False)
								new = False
								break
					if not new:
							self.MAC2INDIGO[xType][MAC][u"ipNumber"] = ipNDevice
							if self.decideMyLog(u"DictDetails") or MAC in self.MACloglist: self.indiLOG.log(20,u"DC-NB-0-   "+ipNDevice+ " MAC: " + MAC + " GHz:" + GHz + "     essid:" + essid + " channel:" + channel )
							if MAC != dev.states[u"MAC"]:
								self.addToStatesUpdateList(dev.id,u"MAC", MAC)
							if essid != dev.states[u"essid"]:
								self.addToStatesUpdateList(dev.id,u"essid", essid)
							if channel != dev.states[u"channel"]:
								self.addToStatesUpdateList(dev.id,u"channel", channel)
							if channel != dev.states[u"adhoc"]:
								self.addToStatesUpdateList(dev.id,u"adhoc", adhoc)

							signalOLD = [" " for iii in range(_GlobalConst_numberOfAP)]
							signalNEW = copy.copy(signalOLD)
							if rssi != "":
								signalOLD = dev.states[u"Signal_at_APs"].split(u"[")[0].split("/")
								if len(signalOLD) == _GlobalConst_numberOfAP:
									signalNEW = copy.copy(signalOLD)
									signalNEW[apNumb] = unicode(int(-90 + float(rssi) / 99. * 40.))
							if signalNEW != signalOLD or dev.states[u"Signal_at_APs"] == "":
								self.addToStatesUpdateList(dev.id,u"Signal_at_APs", "/".join(signalNEW) + "[dBm]")

							if model != dev.states[u"model"] and model != "":
								self.addToStatesUpdateList(dev.id,u"model", model)
							self.MAC2INDIGO[xType][MAC][u"age"] = age
							self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
							self.setImageAndStatus(dev, "up",oldStatus=dev.states[u"status"], ts=time.time(), level=1, text1=dev.name.ljust(30) + u" status up           neighbor DICT ", reason="neighbor DICT", iType=u"DC-NB-1   ")
							if self.updateDescriptions	and dev.description != "Channel= " + channel.rjust(2).replace(" ", "0") + " - SID= " + essid:
								dev.description = "Channel= " + channel.rjust(2).replace(" ", "0") + " - SID= " + essid
								dev.replaceOnServer()


					if new and not self.ignoreNewNeighbors:
						self.indiLOG.log(20,"new: neighbor  " +MAC)
						try:
							dev = indigo.device.create(
								protocol=indigo.kProtocol.Plugin,
								address=MAC,
								name=devName + "_" + MAC,
								description="Channel= " + channel.rjust(2).replace(" ", "0") + " - SID= " + essid,
								pluginId=self.pluginId,
								deviceTypeId=devType,
								folder=self.folderNameNeighbors,
								props={u"useWhatForStatus":"",isType:True})
						except	Exception, e:
							if len(unicode(e)) > 5:
								self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							continue

						self.setupStructures(xType, dev, MAC)
						self.addToStatesUpdateList(dev.id,u"channel", channel)
						signalNEW = [" " for iii in range(_GlobalConst_numberOfAP)]
						if rssi != "":
							signalNEW[apNumb] = unicode(int(-90 + float(rssi) / 99. * 40.))
						self.addToStatesUpdateList(dev.id,u"Signal_at_APs", "/".join(signalNEW) + "[dBm]")
						self.addToStatesUpdateList(dev.id,u"essid", essid)
						self.addToStatesUpdateList(dev.id,u"model", model)
						self.MAC2INDIGO[xType][MAC][u"age"] = age
						self.addToStatesUpdateList(dev.id,u"adhoc", adhoc)
						self.setupBasicDeviceStates(dev, MAC, xType, "", "", "", u" status up        neighbor DICT new neighbor", "DC-NB-2   ")
						indigo.variable.updateValue("Unifi_New_Device", dev.name+"/"+MAC+"/")
				self.executeUpdateStatesList()

		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		#if time.time()-waitT > 0.001: #self.myLog( text=unicode(self.blockAccess).ljust(28)+part.ljust(18)+"    exectime> %6.3f"%(time.time()-waitT)+ " @ "+datetime.datetime.now().strftime("%M:%S.%f")[:-3])
		if len(self.blockAccess)>0:	 del self.blockAccess[0]
		return


	####-----------------	 ---------
	#### this does the unifswitch device itself
	####-----------------	 ---------
	def doSWdictSELF(self, theDict, apNumb, ipNDevice, MAC, hostname):

		part="doSWdictSELF"+unicode(random.random()); self.blockAccess.append(part)
		for ii in range(90):
				if len(self.blockAccess) == 0 or self.blockAccess[0] == part: break # my turn?
				self.sleep(0.1)
		if ii >= 89: self.blockAccess = [] # for safety if too long reset list

		if "model_display" in theDict:	model = (theDict[u"model_display"])
		else:
			self.indiLOG.log(30,u"model_display not in dict doSWdictSELF")
			model = ""


		devName = u"SW"
		xType	= u"SW"
		isType	= "isSwitch"

		try:
			fanLevel	= ""
			if u"fan_level" in theDict:
				fanLevel = unicode(theDict[u"fan_level"])

			temperature = ""
			if u"general_temperature" in theDict:
				if unicode(theDict[u"general_temperature"]) !="0":
					temperature = GT.getNumber(theDict[u"general_temperature"])
			overHeating		= ""
 			if u"overheating" in theDict:
 				overHeating = theDict[u"overheating"]
			uptime			= unicode(theDict[u"uptime"])
			portTable		= theDict[u"port_table"]
			nports			= len(portTable)

			if nports not in self.numberOfPortsInSwitch:
				for nn in self.numberOfPortsInSwitch:
					if nports < nn:
						nports =nn
					if MAC not in self.MAC2INDIGO[xType]:
						self.indiLOG.log(30,u"switch device model "+model+" not support: please contact author. This has "+unicode(nports)+" ports; supported are 8,10,18,26,52 ports only - remember there are extra ports for fiber cables , using next highest..")

			if nports > self.numberOfPortsInSwitch[-1]: return




			devType = u"Device-SW-" + unicode(nports)
			new = True

			if MAC in self.MAC2INDIGO[xType]:
				try:
					dev = indigo.devices[self.MAC2INDIGO[xType][MAC]["devId"]]
					if dev.deviceTypeId != devType: raise error
					new = False
				except:
					if self.decideMyLog(u"Logic") or MAC in self.MACloglist: self.indiLOG.log(20,MAC+"  "+unicode(self.MAC2INDIGO[xType][MAC])+u" wrong "+ devType)
					for dev in indigo.devices.iter("props."+isType):
						if u"MAC" not in dev.states: continue
						if dev.states[u"MAC"] != MAC: continue
						self.MAC2INDIGO[xType][MAC]["devId"] = dev.id
						new = False
						break


			if not new:

					if self.decideMyLog(u"DictDetails") or MAC in self.MACloglist:  self.indiLOG.log(20,u"DC-SW-0    "+ipNDevice + u" SW  hostname:" + hostname + u" MAC:" + MAC)
					self.MAC2INDIGO[xType][MAC][u"ipNumber"] = ipNDevice

					if u"uptime" in theDict and theDict[u"uptime"] !="":
						if u"upSince" in dev.states:
							self.addToStatesUpdateList(dev.id,u"upSince", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()-theDict[u"uptime"])) )

					ports = {}
					if dev.states[u"switchNo"] != apNumb:
						self.addToStatesUpdateList(dev.id,u"switchNo", apNumb)

					if u"ports" not in self.MAC2INDIGO[xType][MAC]:
						self.MAC2INDIGO[xType][MAC][u"ports"]={}
					self.MAC2INDIGO[xType][MAC][u"nPorts"] = len(portTable)

					for port in portTable:

						if u"port_idx" not in port: continue
						ID = port[u"port_idx"]
						idS = "%02d" % ID

						if unicode(ID) not in self.MAC2INDIGO[xType][MAC][u"ports"]:
							self.MAC2INDIGO[xType][MAC][u"ports"][unicode(ID)] = {u"rxLast": 0, u"txLast": 0, u"timeLast": 0,u"poe":"",u"fullDuplex":"",u"link":"",u"nClients":0}
						portsMAC = self.MAC2INDIGO[xType][MAC][u"ports"][unicode(ID)]
						if portsMAC[u"timeLast"] != 0.:
							try:
								dt = max(5, time.time() - portsMAC[u"timeLast"]) * 1000
								rxRate = "%1d" % ((port[u"tx_bytes"] - portsMAC[u"txLast"]) / dt + 0.5)
								txRate = "%1d" % ((port[u"rx_bytes"] - portsMAC[u"rxLast"]) / dt + 0.5)
							except	Exception, e:
								if len(unicode(e)) > 5:
									self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							###self.myLog( text=u"rxRate: " + unicode(rxRate)+	 u"     txRate: " + unicode(txRate))
							try:
								errors = unicode(port[u"tx_dropped"] + port[u"tx_errors"] + port[u"rx_errors"] + port[u"rx_dropped"])
							except:
								errors = u"?"
							if port[u"full_duplex"]:
								fullDuplex = u"FD"
							else:
								fullDuplex = u"HD"
							portsMAC["fullDuplex"] = fullDuplex+u"-" + (unicode(port[u"speed"]))

							if u"is_uplink"  in port and port["is_uplink"]:
								SWP = "UpL"
							else:
								SWP = ""

							nDevices = 0
							if u"mac_table" in port:
								nDevices = len(port[u"mac_table"])
							portsMAC["nClients"] = nDevices
							ppp = u"#C: " + "%02d" % nDevices

							### check if another unifi switch or gw is attached to THIS port , add SW:# or GW:0to the port string
							if u"lldp_table"  in port and len(port["lldp_table"]) >0:
								lldp_table = port[u"lldp_table"][0]
								if u"lldp_chassis_id" in lldp_table and u"lldp_port_id" in lldp_table:
									try:
										macUPdowndevice = lldp_table[u"lldp_chassis_id"].lower()  # unifi deliver lower case , indigo uses upper case for MAC #
										if	macUPdowndevice in self.MAC2INDIGO[u"GW"]:
											ppp+=";GateW"
											SWP ="GW"
										elif  macUPdowndevice in self.MAC2INDIGO[xType]:
											try:	portNatSW = ",P:"+lldp_table[u"lldp_port_id"].split("/")[1]
											except: portNatSW = ""
											if SWP =="" : SWP = "DwL"
											devIdOfSwitch = self.MAC2INDIGO[u"SW"][macUPdowndevice]["devId"]
											ppp+= ";"+SWP+":"+ unicode(indigo.devices[devIdOfSwitch].states[u"switchNo"])+portNatSW
									except	Exception, e:
											self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

							portsMAC["link"] = SWP

							poe=""
							if u"poe_enable" in port:
								if port[u"poe_enable"]:
									if (u"poe_good" in port and port[u"poe_good"])	:
										poe="poe1"
									elif (u"poe_mode" in port and port[u"poe_mode"] =="passthrough") :
										poe="poeP"
									else:
										poe="poe0"
								else:
										poe="poeX"
							if poe !="":
								ppp+=";"+poe
							portsMAC["poe"] = poe

							if nDevices > 0:
								ppp += u";" + fullDuplex + u"-" + (unicode(port[u"speed"]))
								ppp += u"; err:" + errors
								ppp += u"; rx-tx[kb/s]:" + rxRate + "-" + txRate


								if ppp != dev.states[u"port_" + idS]:
									self.addToStatesUpdateList(dev.id,u"port_" + idS, ppp)



							if u"port_" + idS in dev.states:
								if ppp != dev.states[u"port_" + idS]:
									self.addToStatesUpdateList(dev.id,u"port_" + idS, ppp)



						portsMAC[u"txLast"]	   = port[u"tx_bytes"]
						portsMAC[u"rxLast"]	   = port[u"rx_bytes"]
						portsMAC[u"timeLast"]  = time.time()

					if model != dev.states[u"model"] and model !="":
						self.addToStatesUpdateList(dev.id,u"model", model)
					if uptime != self.MAC2INDIGO[xType][MAC][u"upTime"]:
						self.MAC2INDIGO[xType][MAC][u"upTime"] =uptime
					if temperature !="" and "temperature" in dev.states and  temperature != dev.states[u"temperature"]:
						self.addToStatesUpdateList(dev.id,u"temperature", temperature)
					if "overHeating" !="" and "overHeating" in dev.states and overHeating != dev.states[u"overHeating"]:
							self.addToStatesUpdateList(dev.id,u"overHeating", overHeating)
					if ipNDevice != dev.states[u"ipNumber"]:
						self.addToStatesUpdateList(dev.id,u"ipNumber", ipNDevice)
					if hostname != dev.states[u"hostname"]:
						self.addToStatesUpdateList(dev.id,u"hostname", hostname)
					if dev.states[u"status"] != u"up":
						self.setImageAndStatus(dev, u"up",oldStatus=dev.states[u"status"], ts=time.time(), level=1, text1=dev.name.ljust(30) + u" status up            SW    DICT", reason="switch DICT", iType=u"STATUS-SW")
					self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
					if "fanLevel" in dev.states and  fanLevel != "" and fanLevel != dev.states[u"fanLevel"]:
						self.addToStatesUpdateList(dev.id,u"fanLevel", fanLevel)


					if self.updateDescriptions:
						ipx = self.fixIP(ipNDevice)
						oldIPX = dev.description.split("-")
						if oldIPX[0] != ipx or ( (dev.description != ipx + "-" + hostname) or len(dev.description) < 5):
							if oldIPX[0] != ipx and oldIPX[0] !="":
								indigo.variable.updateValue("Unifi_With_IPNumber_Change",dev.name+"/"+dev.states["MAC"]+"/"+oldIPX[0]+"/"+ipx)
							if len(oldIPX) < 2:
								oldIPX.append(hostname.strip("-"))
							elif len(oldIPX) == 2 and oldIPX[1] == "":
								if hostname != "":
									oldIPX[1] = hostname.strip("-")
							oldIPX[0] = ipx
							newDescr = "-".join(oldIPX)
							dev.description = newDescr
							dev.replaceOnServer()


					self.setStatusUpForSelfUnifiDev(MAC)
					#break

			if new:
				try:
					dev = indigo.device.create(
						protocol=indigo.kProtocol.Plugin,
						address=MAC,
						name=devName+u"_" + MAC,
						description=self.fixIP(ipNDevice) + "-" + hostname,
						pluginId=self.pluginId,
						deviceTypeId=devType,
						folder=self.folderNameIDCreated,
						props={u"useWhatForStatus":"",isType:True})
					self.setupStructures(xType, dev, MAC)
					self.MAC2INDIGO[xType][MAC][u"upTime"] = uptime
					self.addToStatesUpdateList(dev.id,u"model", model)
					if temperature !="" and "temperature" in dev.states and  temperature != dev.states[u"temperature"]:
						self.addToStatesUpdateList(dev.id,u"temperature", temperature)
					if "overHeating" !="" and "overHeating" in dev.states and overHeating != dev.states[u"overHeating"]:
 						self.addToStatesUpdateList(dev.id,u"overHeating", overHeating)
					self.addToStatesUpdateList(dev.id,u"hostname", hostname)
					self.addToStatesUpdateList(dev.id,u"switchNo", apNumb)
					self.setupBasicDeviceStates(dev, MAC, xType, ipNDevice, "", "", u" status up     SW DICT  new SWITCH", "STATUS-SW")
					indigo.variable.updateValue("Unifi_New_Device", dev.name+"/"+MAC+"/"+ipNDevice)
				except	Exception, e:
					if len(unicode(e)) > 5:
						self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						self.indiLOG.log(40,u"     for mac#"+MAC+";  hostname: "+ hostname)
						self.indiLOG.log(40,u"MAC2INDIGO: "+unicode(self.MAC2INDIGO[xType]))

			self.executeUpdateStatesList()

		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		#if time.time()-waitT > 0.001: #self.myLog( text=unicode(self.blockAccess).ljust(28)+part.ljust(18)+"    exectime> %6.3f"%(time.time()-waitT)+ " @ "+datetime.datetime.now().strftime("%M:%S.%f")[:-3])
		if len(self.blockAccess)>0:	 del self.blockAccess[0]

		return

	####----------------- if FINGSCAN is enabled send update signal	 ---------
	def setStatusUpForSelfUnifiDev(self, MAC):
		try:

			if MAC in self.MAC2INDIGO[u"UN"]:
				self.MAC2INDIGO[u"UN"][MAC][u"lastUp"] = time.time()+20
				devidUN = self.MAC2INDIGO[u"UN"][MAC]["devId"]
				try:
					devUN = indigo.devices[devidUN]
					if devUN.states["status"] !=u"up":
						self.addToStatesUpdateList(devidUN,u"status", u"up")
						self.addToStatesUpdateList(devidUN,u"lastStatusChangeReason", u"switch message")
						if self.decideMyLog(u"Logic") or MAC in self.MACloglist :  self.indiLOG.log(20,u"updateself setStatusUpForSelfUnifiDev:      updating status to up MAC:" + MAC+"  "+devUN.name+"  was: "+ devUN.states["status"] )
					if unicode(devUN.displayStateImageSel) !="SensorOn":
						devUN.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
				except:pass

		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	####----------------- if FINGSCAN is enabled send update signal	 ---------
	def sendUpdatetoFingscanNOW(self, force=False):
		try:
			x = ""
			if not self.enableFINGSCAN:
				self.sendUpdateToFingscanList ={}
				return x
			if self.sendUpdateToFingscanList =={} and not force:
				return x
			if self.countLoop < 10:
				self.sendUpdateToFingscanList ={}
				return x  ## only after stable ops for 10 loops ~ 20 secs

			plug = indigo.server.getPlugin("com.karlwachs.fingscan")
			if not plug.isEnabled():
				self.sendUpdateToFingscanList ={}
				return x

			if not force:
				localF = copy.copy(self.sendUpdateToFingscanList)
				for devid in localF:
					if devid !="":
							dev= indigo.devices[int(devid)]
							if dev.deviceTypeId != u"neighbor" or ( dev.deviceTypeId == u"neighbor" and not self.ignoreNeighborForFing) :
								try:
									if self.decideMyLog(u"Fing"): self.indiLOG.log(20,u"FINGSC---   "+u"updating fingscan with " + dev.name + u" = " + dev.states[u"status"])
									plug.executeAction(u"unifiUpdate", props={u"deviceId": [devid]})
									self.fingscanTryAgain = False
								except	Exception, e:
									if len(unicode(e)) > 5:
										self.indiLOG.log(40,"in Line {} has error={}   finscan update failed".format(sys.exc_traceback.tb_lineno, e) )
									self.fingscanTryAgain = True

			else:
				devIds	  = []
				devNames  = []
				devValues = {}
				stringToPrint = u"\n"
				for dev in indigo.devices.iter(self.pluginId):
					if dev.deviceTypeId == u"client": continue
					devIds.append(unicode(dev.id))
					stringToPrint += dev.name + u"= " + dev.states[u"status"] + u"\n"

				if devIds != []:
					for i in range(3):
						if self.decideMyLog(u"Fing"): self.indiLOG.log(20,u"FINGSC---   "+u"updating fingscan try# " + unicode(i + 1) + u";     with " + stringToPrint )
						plug.executeAction(u"unifiUpdate", props={u"deviceId": devIds})
						self.fingscanTryAgain = False
						break

		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			else:
				x = "break"
		self.sendUpdateToFingscanList ={}
		return x
	####----------------- if FINGSCAN is enabled send update signal	 ---------
	def sendBroadCastNOW(self):
		try:
			x = ""
			if	self.enableBroadCastEvents =="0":
				self.sendBroadCastEventsList = []
				return x
			if self.sendBroadCastEventsList == []:
				return x
			if self.countLoop < 10:
				self.sendBroadCastEventsList = []
				return x  ## only after stable ops for 10 loops ~ 20 secs

			msg = copy.copy(self.sendBroadCastEventsList)
			self.sendBroadCastEventsList = []
			if len(msg) >0:
				msg ={"pluginId":self.pluginId,"data":msg}
				try:
					if self.decideMyLog(u"BC"): self.indiLOG.log(20,u"BroadCast-   "+u"updating BC with " + unicode(msg) )
					indigo.server.broadcastToSubscribers(u"deviceStatusChanged", json.dumps(msg))
				except	Exception, e:
					if len(unicode(e)) > 5:
						self.indiLOG.log(40,"in Line {} has error={}   finscan update failed".format(sys.exc_traceback.tb_lineno, e) )

		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			else:
				x = "break"
		return x

	####-----------------	 ---------
	def checkMAC(self, MAC):
		macs = MAC.split(":")
		for nn in range(len(macs)):
			mac = macs[nn]
			if len(mac) < 2: macs[nn] = u"0" + mac
		return ":".join(macs)

	####-----------------	 ---------
	def fixIP(self, ip):
		if len(ip) < 7: return ip
		ipx = ip.split(u"/")[0].split(u".")
		ipx[3] = "%03d" % (int(ipx[3]))
		return u".".join(ipx)

	####-----------------	 ---------
	def setupBasicDeviceStates(self, dev, MAC, devType, ip, ipNDevice, GHz, text1, type):
		try:
			self.addToStatesUpdateList(dev.id,u"created", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
			self.addToStatesUpdateList(dev.id,u"MAC", MAC)
			self.MAC2INDIGO[devType][MAC][u"lastUp"] = time.time()
			if ip !="":
				self.addToStatesUpdateList(dev.id,u"ipNumber", ip)

			self.setImageAndStatus(dev, "up",oldStatus=dev.states[u"status"], ts=time.time(), level=1, text1=dev.name.ljust(30) + text1, iType=type,reason="initialsetup")
			vendor = self.getVendortName(MAC)
			if vendor != "":
					self.addToStatesUpdateList(dev.id,u"vendor", vendor)
					self.moveToUnifiSystem(dev, vendor)
		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return

	####-----------------	 ---------
	def testIgnoreMAC(self, MAC,  fromSystem="") :
		ignore = False
		#self.myLog( text=u"testIgnoreMAC testing: MAC "+MAC+";  called from: "+fromSystem )
		if MAC in self.MACignorelist:
			if self.decideMyLog(u"Logic"):  self.indiLOG.log(20,fromSystem+"  "+u"ignored: message for MAC:"+ MAC)
			return True

		if len(self.MACSpecialIgnorelist) == 0:
			return False

		MACSplit = (MAC.lower()).split(":")
		for MACsp in self.MACSpecialIgnorelist:
			MACSPSplit = (MACsp.lower()).split(":")
			ignore = True
			for nn  in range(6):
				if MACSPSplit[nn] !="xx" and MACSPSplit[nn] != MACSplit[nn]:
					ignore = False
					break
			if ignore:
				if True or self.decideMyLog(u"Logic"):  self.indiLOG.log(20,fromSystem+"  "+u"ignored: MAC:"+ MAC+"  due to  special ignore: "+MACsp)
				return True
		return False

	####-----------------	 ---------
	def moveToUnifiSystem(self,dev,vendor):
		try:
			if vendor.upper().find("UBIQUIT") >-1:
				indigo.device.moveToFolder(dev.id, value=self.folderNameIDSystemID)
				self.indiLOG.log(20,u"moving "+dev.name+u";  to folderID: "+ unicode(self.folderNameIDSystemID))
		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	####-----------------	 ---------
	def getVendortName(self,MAC):
		if self.enableMACtoVENDORlookup !="0" and not self.waitForMAC2vendor:
			self.waitForMAC2vendor = self.M2V.makeFinalTable()

		return	self.M2V.getVendorOfMAC(MAC)


	####-----------------	 ---------
	def setImageAndStatus(self, dev, newStatus, oldStatus=u"123abc123abcxxx", ts="", level=1, text1="", iType=u"", force=False, fing=True,reason=u""):
		try:
			if oldStatus == u"123abc123abc":
				oldStatus = dev.states[u"status"]
			retC = False
			try:	xType = self.xTypeMac[unicode(dev.id)]["xType"]
			except: return
			MAC	  =	 self.xTypeMac[unicode(dev.id)][u"MAC"]
			if oldStatus != newStatus or force:
				if ts != "":
					retC = True
				if (text1 != "" and self.decideMyLog(u"Logic")) or MAC in self.MACloglist:  self.indiLOG.log(20,iType+"  "+text1)

				if oldStatus != newStatus:
					if fing and oldStatus != u"123abc123abcxxx":
						self.sendUpdateToFingscanList[unicode(dev.id)] = unicode(dev.id)
					self.addToStatesUpdateList(dev.id,u"status", newStatus)

					if u"lastStatusChangeReason" in dev.states and reason !=u"":
						self.addToStatesUpdateList(dev.id,u"lastStatusChangeReason", reason)
					if (not force and self.decideMyLog(u"Logic") )  or MAC in self.MACloglist: self.indiLOG.log(20,u"STAT-Change "+dev.states[u"MAC"] +u" st changed  " + dev.states[u"status"]+"/"+newStatus+"; "+text1)
					retC = True

		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		return

	####-----------------	 ---------
	#### wake on lan and pings	START
	####-----------------	 ---------
	def sendWakewOnLanAndPing(self, MAC,IPNumber, nBC=2, waitForPing=500, countPings=1, waitBeforePing=0.5, waitAfterPing=0.5, nPings =1, calledFrom="", props=""):
		try:
			doWOL = True
			if props != "" and "useWOL" in props and props["useWOL"] =="0": doWOL = False
			if doWOL:
				self.sendWakewOnLan(MAC, calledFrom=calledFrom)
				if nBC ==2:
					self.sleep(0.05)
					self.sendWakewOnLan(MAC, calledFrom=calledFrom)
				self.sleep(waitBeforePing)
			return self.checkPing(IPNumber, waitForPing=waitForPing, countPings=countPings, nPings=nPings, waitAfterPing=waitAfterPing, calledFrom=calledFrom)
		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}  called from: {} ".format(sys.exc_traceback.tb_lineno, e, calledFrom) )

	####-----------------	 ---------
	def checkPing(self, IPnumber , waitForPing=100, countPings=1,nPings=1, waitAfterPing=0.5, calledFrom=""):
		try:
			Wait = ""
			if waitForPing != "":
				Wait = "-W "+ str(waitForPing)
			Count = "-c 1"

			if countPings != "":
				Count = "-c "+str(countPings)

			if nPings == 1 :
				waitAfterPing = 0.

			retCode =1
			for nn in range(nPings):
				retCode = subprocess.call('/sbin/ping -o '+Wait+' '+Count+' -q '+IPnumber+' >/dev/null',shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE) # "call" will wait until its done and deliver retcode 0 or >0
				if self.decideMyLog(u"Ping"):  self.indiLOG.log(20,calledFrom+" "+u"ping resp:"+IPnumber+"    :" +str(retCode))
				if retCode ==0:	   return 0
				if nn != nPings-1: self.sleep(waitAfterPing)
			return retCode
		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,"in Line {} has error={}  called from: {} ".format(sys.exc_traceback.tb_lineno, e, calledFrom) )

	####-----------------	 ---------
	def sendWakewOnLan(self, MAC, calledFrom=""):
		if self.broadcastIP !="9.9.9.255":
			data = ''.join(['FF' * 6, (MAC.upper()).replace(':', '') * 16])
			sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
			sock.sendto(data.decode("hex"), (self.broadcastIP, 9))
			if self.decideMyLog(u"Ping"):  self.indiLOG.log(20,calledFrom+" "+u"sendWakewOnLan for "+MAC+";    called from "+calledFrom+";  bc ip: "+self.broadcastIP)
	####-----------------	 ---------
	#### wake on lan and pings	END
	####-----------------	 ---------


	####-----------------	 ---------
	def manageLogfile(self, apDict, apNumb,unifiDeviceType):
		try:
				name = self.indigoPreferencesPluginDir + u"dict-"+unifiDeviceType+u"#" + unicode(apNumb)
				self.writeJson( apDict, fName=name+".txt", sort=False, doFormat=True )
		except	Exception, e:
				if len(unicode(e)) > 5:
					self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


	####-----------------	 ---------
	def exeDisplayStatus(self, dev, status, force=True):
				if status in [u"up","ON"] :
					dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
				elif status in [u"down",u"off"]:
					dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
				elif status in [u"expired","REC"] :
					dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
				elif status in [u"susp"] :
					dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
				elif status == u"" :
					dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
				if force or status =="":
					dev.updateStateOnServer(u"displayStatus",self.padDisplay(status)+datetime.datetime.now().strftime(u"%m-%d %H:%M:%S"))
					dev.updateStateOnServer(u"status",status)
					dev.updateStateOnServer(u"onOffState",value= dev.states["status"] in ["up","rec","ON"], uiValue= dev.states["displayStatus"])


	####-----------------	 ---------
	def addToStatesUpdateList(self,devid,key,value):
		try:
			devId = unicode(devid)
			### no down during startup .. 100 secs
			if key == "status" and value !="up":
			   if time.time() - self.pluginStartTime <0:
					return

			local = copy.deepcopy(self.devStateChangeList)
			if devId not in local:
				local[devId]={}
			if key in local[devId]:
				if value != local[devId][key]:
					local[devId][key] = {}
			local[devId][key] = value
			self.devStateChangeList = copy.deepcopy(local)

		except	Exception, e:
			if len(unicode(e))	> 5 :
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return




	####-----------------	 ---------
	def executeUpdateStatesList(self):
		devId =""
		key =""
		local =""
		try:
			if len(self.devStateChangeList) ==0: return
			local = copy.deepcopy(self.devStateChangeList)
			self.devStateChangeList ={}
			changedOnly = {}
			trigList=[]
			for devId in  local:
				try: int(devId)
				except: continue
				if len( local[devId]) > 0:
					dev =indigo.devices[int(devId)]
					for key in local[devId]:
						value = local[devId][key]
						if unicode(value) != unicode(dev.states[key]):
							if devId not in changedOnly: changedOnly[devId]=[]
							changedOnly[devId].append({u"key":key,u"value":value})
							if key == u"status":
								ts = datetime.datetime.now().strftime(u"%Y-%m-%d %H:%M:%S")
								changedOnly[devId].append({u"key":u"lastStatusChange", u"value":ts})
								changedOnly[devId].append({u"key":u"displayStatus",	   u"value":self.padDisplay(value)+ts[5:] } )
								changedOnly[devId].append({u"key":u"onOffState",	   u"value":value in ["up","rec","ON"],   u"uiValue":self.padDisplay(value)+ts[5:] } )
								self.exeDisplayStatus(dev, value, force=False)

								self.statusChanged = max(1,self.statusChanged)
								trigList.append(dev.name)
								val = unicode(value).lower()
								if self.enableBroadCastEvents !="0" and val in ["up","down","expired","rec","ON"]:
									props = dev.pluginProps
									if	self.enableBroadCastEvents == "all" or	("enableBroadCastEvents" in props and props["enableBroadCastEvents"] == "1" ):
										msg = {"action":"event", "id":str(dev.id), "name":dev.name, "state":"status", "valueForON":"up", "newValue":val}
										if self.decideMyLog(u"BC"):	self.indiLOG.log(20,"BroadCast "+dev.name+" " +unicode(msg))
										self.sendBroadCastEventsList.append(msg)



					if devId in changedOnly and changedOnly[devId] !=[]:

						self.dataStats[u"updates"][u"devs"]	  +=1
						self.dataStats[u"updates"][u"states"] +=len(changedOnly)
						if self.indigoVersion >6:
							try:
								dev.updateStatesOnServer(changedOnly[devId])
							except	Exception, e:
								self.indiLOG.log(40,"in Line {} has error={} \n devId:{};     changedOnlyDict:{}".format(sys.exc_traceback.tb_lineno, e,unicode(devId),unicode(changedOnly[devId]) ) )
						else:
							for uu in changedOnly[devId]:
								dev.updateStateOnServer(uu[u"key"],uu[u"value"])

			if len(trigList) >0:
				for devName	 in trigList:
					indigo.variable.updateValue(u"Unifi_With_Status_Change",devName)
				self.triggerEvent(u"someStatusHasChanged")
		except	Exception, e:
			if len(unicode(e))	> 5 :
				self.indiLOG.log(40,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				try:
					self.indiLOG.log(40,dev.name+u"     "+ devId +u"  "+ unicode(key)+";  devStateChangeList:\n"+ unicode(local))
				except:pass
		if len(self.sendBroadCastEventsList) >0: self.sendBroadCastNOW()
		return

	####-----------------	 ---------
	def padDisplay(self,status):
		if	 status == u"up":		 return status.ljust(11)
		elif status == u"expired":	 return status.ljust(8)
		elif status == u"down":		 return status.ljust(9)
		elif status == u"susp":		 return status.ljust(9)
		elif status == u"changed":	 return status.ljust(8)
		elif status == u"double":	 return status.ljust(8)
		elif status == u"ignored":	 return status.ljust(8)
		elif status == u"off":		 return status.ljust(11)
		elif status == u"REC":		 return status.ljust(9)
		elif status == u"ON":		 return status.ljust(10)
		else:						 return status.ljust(10)


	########################################
	# General Action callback
	######################
	def actionControlUniversal(self, action, dev):
		###### BEEP ######
		if action.deviceAction == indigo.kUniversalAction.Beep:
			# Beep the hardware module (dev) here:
			# ** IMPLEMENT ME **
			indigo.server.log(u"sent \"{}\" beep request not implemented".format(dev.name) )

		###### STATUS REQUEST ######
		elif action.deviceAction == indigo.kUniversalAction.RequestStatus:
			# Query hardware module (dev) for its current status here:
			# ** IMPLEMENT ME **
			indigo.server.log(u"sent \"{}\" status request not implemented".format(dev.name) )

	####-----------------
	########################################
	# Sensor Action callback
	######################
	def actionControlSensor(self, action, dev):
		###### TURN ON ######
		if action.sensorAction == indigo.kSensorAction.TurnOn:
			self.setImageAndStatus(dev, "up",oldStatus=dev.states[u"status"], ts=time.time(), iType=u"actionControlSensor",reason=u"TurnOn")

		###### TURN OFF ######
		elif action.sensorAction == indigo.kSensorAction.TurnOff:
			self.setImageAndStatus(dev, "up",oldStatus=dev.states[u"status"], ts=time.time(), iType=u"actionControlSensor",reason=u"TurnOff")

		###### TOGGLE ######
		elif action.sensorAction == indigo.kSensorAction.Toggle:
			if dev.onState:
				self.setImageAndStatus(dev, "up",oldStatus=dev.states[u"status"], ts=time.time(), iType=u"actionControlSensor",reason=u"toggle")
			else:
				self.setImageAndStatus(dev, "up",oldStatus=dev.states[u"status"], ts=time.time(), iType=u"actionControlSensor",reason=u"toggle")

		self.executeUpdateStatesList()

########################################
########################################
####----checkPluginPath----
########################################
########################################
	####------ --------
	def checkPluginPath(self, pluginName, pathToPlugin):

		if self.pathToPlugin.find("/" + self.pluginName + ".indigoPlugin/") == -1:
			self.errorLog(u"--------------------------------------------------------------------------------------------------------------")
			self.errorLog(u"The pluginName is not correct, please reinstall or rename")
			self.errorLog(u"It should be   /Libray/....../Plugins/" + pluginName + ".indigoPlugin")
			p = max(0, pathToPlugin.find("/Contents/Server"))
			self.errorLog(u"It is: " + pathToPlugin[:p])
			self.errorLog(u"please check your download folder, delete old *.indigoPlugin files or this will happen again during next update")
			self.errorLog(u"---------------------------------------------------------------------------------------------------------------")
			self.sleep(100)
			return False
		return True

########################################
########################################
####----move files to ...indigo x.y/Preferences/Plugins/< pluginID >.----
########################################
########################################
	####------ --------
	def moveToIndigoPrefsDir(self, fromPath, toPath):
		if os.path.isdir(toPath): 		
			return True
		indigo.server.log(u"--------------------------------------------------------------------------------------------------------------")
		indigo.server.log("creating plugin prefs directory ")
		os.mkdir(toPath)
		if not os.path.isdir(toPath): 	
			self.errorLog("| preference directory can not be created. stopping plugin:  "+ toPath)
			self.errorLog(u"--------------------------------------------------------------------------------------------------------------")
			self.sleep(100)
			return False
		indigo.server.log("| preference directory created;  all config.. files will be here: "+ toPath)
			
		if not os.path.isdir(fromPath): 
			indigo.server.log(u"--------------------------------------------------------------------------------------------------------------")
			return True
		cmd = "cp -R '"+ fromPath+"'  '"+ toPath+"'"
		os.system(cmd )
		self.sleep(1)
		indigo.server.log("| plugin files moved:  "+ cmd)
		indigo.server.log("| please delete old files")
		indigo.server.log(u"--------------------------------------------------------------------------------------------------------------")
		return True


########################################
########################################
####-----------------  logging ---------
########################################
########################################

	####----------------- ---------
	def setLogfile(self, lgFile):
		self.logFileActive =lgFile
		if   self.logFileActive =="standard":	self.logFile = ""
		elif self.logFileActive =="indigo":		self.logFile = self.indigoPath.split("Plugins/")[0]+"Logs/"+self.pluginId+"/plugin.log"
		else:									self.logFile = self.indigoPreferencesPluginDir +"plugin.log"
		self.myLog( text="myLogSet setting parameters -- logFileActive= "+ unicode(self.logFileActive) + "; logFile= "+ unicode(self.logFile)+ ";  debugLevel= "+ unicode(self.debugLevel), destination="standard")



			
			
	####-----------------	 ---------
	def decideMyLog(self, msgLevel):
		try:
			if msgLevel	 == u"all" or u"all" in self.debugLevel:	 return True
			if msgLevel	 == ""	 and u"all" not in self.debugLevel:	 return False
			if msgLevel in self.debugLevel:							 return True
			return False
		except	Exception, e:
			if len(unicode(e)) > 5:
				indigo.server.log( u"decideMyLog in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return False

	####-----------------  print to logfile or indigo log  ---------
	def myLog(self,	 text="", mType="", errorType="", showDate=True, destination=""):
		   
	
		try:
			if	self.logFileActive =="standard" or destination.find("standard") >-1:
				if errorType == u"smallErr":
					self.errorLog(u"------------------------------------------------------------------------------")
					self.errorLog(text)
					self.errorLog(u"------------------------------------------------------------------------------")

				elif errorType == u"bigErr":
					self.errorLog(u"==================================================================================")
					self.errorLog(text)
					self.errorLog(u"==================================================================================")

				elif mType == "":
					indigo.server.log(text)
				else:
					indigo.server.log(text, type=mType)


			if	self.logFileActive !="standard":

				ts =""
				try:
					if len(self.logFile) < 3: return # not properly defined
					f =	 open(self.logFile,"a")
				except	Exception, e:
					indigo.server.log(u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					try:
						f.close()
					except:
						pass
					return

				if errorType == u"smallErr":
					if showDate: ts = datetime.datetime.now().strftime(u"%H:%M:%S")
					f.write(u"----------------------------------------------------------------------------------\n")
					f.write((ts+u" ".ljust(12)+u"-"+text+u"\n").encode(u"utf8"))
					f.write(u"----------------------------------------------------------------------------------\n")
					f.close()
					return

				if errorType == u"bigErr":
					if showDate: ts = datetime.datetime.now().strftime(u"%H:%M:%S")
					ts = datetime.datetime.now().strftime(u"%H:%M:%S")
					f.write(u"==================================================================================\n")
					f.write((ts+u" "+u" ".ljust(12)+u"-"+text+u"\n").encode(u"utf8"))
					f.write(u"==================================================================================\n")
					f.close()
					return

				if showDate: ts = datetime.datetime.now().strftime(u"%H:%M:%S")
				if mType == u"":
					f.write((ts+u" " +u" ".ljust(25)  +u"-" + text + u"\n").encode("utf8"))
				else:
					f.write((ts+u" " +mType.ljust(25) +u"-" + text + u"\n").encode("utf8"))
				### print calling function 
				#f.write(u"_getframe:   1:" +sys._getframe(1).f_code.co_name+"   called from:"+sys._getframe(2).f_code.co_name+" @ line# %d"%(sys._getframe(1).f_lineno) ) # +"    trace# "+unicode(sys._getframe(1).f_trace)+"\n" )
				f.close()
				return


		except	Exception, e:
			if len(unicode(e)) > 5:
				self.errorLog(u"myLog in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				indigo.server.log(text)
				try: f.close()
				except: pass

####-----------------  valiable formatter for differnt log levels ---------
# call with: 
# formatter = LevelFormatter(fmt='<default log format>', level_fmts={logging.INFO: '<format string for info>'})
# handler.setFormatter(formatter)
class LevelFormatter(logging.Formatter):
	def __init__(self, fmt=None, datefmt=None, level_fmts={}, level_date={}):
		self._level_formatters = {}
		self._level_date_format = {}
		for level, format in level_fmts.items():
			# Could optionally support level names too
			self._level_formatters[level] = logging.Formatter(fmt=format, datefmt=level_date[level])
		# self._fmt will be the default format
		super(LevelFormatter, self).__init__(fmt=fmt, datefmt=datefmt)

	def format(self, record):
		if record.levelno in self._level_formatters:
			return self._level_formatters[record.levelno].format(record)

		return super(LevelFormatter, self).format(record)
