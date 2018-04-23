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
import versionCheck.versionCheck as VS
import MACMAP.MAC2Vendor as M2Vclass

import threading
import copy
import json
import myLogPgms.myLogPgms 
import requests
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)



## Static parameters, not changed in pgm
_GlobalConst_numberOfAP  = 5
_GlobalConst_numberOfSW  = 11

_GlobalConst_numberOfGroups = 10
_GlobalConst_groupList      =[u"Group"+unicode(i) for i in range(_GlobalConst_numberOfGroups)]
_GlobalConst_dTypes =["UniFi","gateway","DHCP","SWITCH","Device-AP","Device-SW-8","Device-SW-10","Device-SW-18" ,"Device-SW-26","Device-SW-52","neighbor"]
################################################################################
# noinspection PyUnresolvedReferences
class Plugin(indigo.PluginBase):
    ####-----------------             ---------
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

        #pfmt = logging.Formatter('%(asctime)s.%(msecs)03d\t%(levelname)-12s\t%(name)s.%(funcName)-25s %(msg)s', datefmt='%Y-%m-%d %H:%M:%S')
        #self.plugin_file_handler.setFormatter(pfmt)

        self.pathToPlugin = os.getcwd() + "/"
        ## = /Library/Application Support/Perceptive Automation/Indigo 6/Plugins/piBeacon.indigoPlugin/Contents/Server Plugin
        p = max(0, self.pathToPlugin.lower().find("/plugins/")) + 1
        self.indigoPath = self.pathToPlugin[:p]
        #self.errorLog(self.indigoPath)
        #self.errorLog(self.pathToPlugin)
        #self.errorLog(self.pathToPlugin)
        self.indigoVersion = int(self.indigoPath.strip("/")[-1:])
        indigo.server.log(u"setting parameters for indigo version: >>"+unicode(self.indigoVersion)+u"<<")   
        self.pluginState                = "init"
        self.pluginVersion      = pluginVersion
        self.pluginId           = pluginId
        self.pluginName         = pluginId.split(".")[-1]

    ####-----------------             ---------
    def __del__(self):
        indigo.PluginBase.__del__(self)

    ###########################     INIT    ## START ########################

    ####----------------- @ startup set global parameters, create directories etc ---------
    def startup(self):
        indigo.server.log("initializing  ... variables")

        self.debugLevel = 0
        if self.pathToPlugin.find("/" + self.pluginName + ".indigoPlugin/") == -1:
            self.errorLog(u"--------------------------------------------------------------------------------------------------------------")
            self.errorLog(u"The pluginName is not correct, please reinstall or rename")
            self.errorLog(u"It should be   /Libray/....../Plugins/" + self.pluginName + ".indigoPlugin")
            p = max(0, self.pathToPlugin.find("/Contents/Server"))
            self.errorLog(u"It is: " + self.pathToPlugin[:p])
            self.errorLog(u"please check your download folder, delete old *.indigoPlugin files or this will happen again during next update")
            self.errorLog(u"---------------------------------------------------------------------------------------------------------------")
            self.sleep(2000)
            exit(1)
            return
            
        self.myPID = os.getpid()
        self.MACuserName   = pwd.getpwuid(os.getuid())[0]
        self.MAChome       = os.path.expanduser("~")
        self.indigoDir     = self.MAChome+"/indigo/" #  this is the data directory

        self.unifiPath     = self.indigoDir + "unifi/"
        self.unifiPathOld  = self.MAChome + "/documents/unifi/"


 
        if True:
            if not os.path.exists(self.indigoDir):
                os.mkdir(self.indigoDir)

            if not os.path.exists(self.unifiPath):
                os.mkdir(self.unifiPath)
    
                if not os.path.exists(self.unifiPath):
                    self.errorLog("error creating the plugin data dir did not work, can not create: "+ self.unifiPath)
                    self.sleep(1000)
                    exit()
                
                if os.path.exists(self.unifiPathOld) :
                    self.ML.myLog( text=u" moving "+ "cp -R" + self.unifiPathOld+"* " + self.unifiPath )
                    os.system("cp -R " + self.unifiPathOld+"* " + self.unifiPath )




        self.ML = myLogPgms.myLogPgms.MLX()
        self.debugLevel         = []
        if self.pluginPrefs.get(u"debugLogic", False):           self.debugLevel.append("Logic")
        if self.pluginPrefs.get(u"debugLog", False):             self.debugLevel.append("Log")
        if self.pluginPrefs.get(u"debugDict", False):            self.debugLevel.append("Dict")
        if self.pluginPrefs.get(u"debugLogDetails", False):      self.debugLevel.append("LogDetails")
        if self.pluginPrefs.get(u"debugDictDetails", False):     self.debugLevel.append("DictDetails")
        if self.pluginPrefs.get(u"debugConnection", False):      self.debugLevel.append("Connection")
        if self.pluginPrefs.get(u"debugFing", False):            self.debugLevel.append("Fing")
        if self.pluginPrefs.get(u"debugall", False):             self.debugLevel.append("all")
        self.logFileActive          = self.pluginPrefs.get("logFilePath", "no")
        if self.logFileActive =="no":
            self.logFile =""
            indigo.server.log("logfile handling: regular indigo logfile")
        elif self.logFileActive =="indigo":
            self.logFile = self.indigoPath.split("Plugins/")[0]+"logs/"+self.pluginId+"/UniFi.log"
            indigo.server.log("logfile handling to : "+self.logFile)
        else:
            self.logFile    = self.unifiPath + "UniFi.log"
            indigo.server.log("logfile handling to : "+self.logFile)


        self.ML.myLogSet(debugLevel = self.debugLevel ,logFileActive=self.logFileActive, logFile = self.logFile)

        indigo.server.log(self.pluginId)
        indigo.server.log(self.logFile)



        self.expectCmdFile  = {   "APtail": "execLog.exp",
                     "GWtail": "execLog.exp",
                     "SWtail": "execLog.exp",
                     "GWdict": "dictLoop.exp",
                     "SWdict": "dictLoop.exp",
                     "APdict": "dictLoop.exp"}
        self.commandOnServer= {   "APtail": "'/usr/bin/tail -f /var/log/messages'",
                     "GWtail": "'/usr/bin/tail -f /var/log/messages'",
                     "SWtail": "'/usr/bin/tail -f /var/log/messages'",
                     "GWdict": "mca-dump | sed -e 's/^ *//'",
                     "SWdict": "mca-dump | sed -e 's/^ *//'",
                     "APdict": "mca-dump | sed -e 's/^ *//'"}
        self.promptOnServer = {   "APtail": "BZ.v",
                     "GWtail": ":~",
                     "SWtail": "US.v",
                     "GWdict": ":~",
                     "SWdict": "US.v",
                     "APdict": "BZ.v"}
        self.startDictToken = {   "APtail": "x",
                     "GWtail": "x",
                     "SWtail": "x",
                     "GWdict": "mca-dump | sed -e 's/^ *//'",
                     "SWdict": "mca-dump | sed -e 's/^ *//'",
                     "APdict": "mca-dump | sed -e 's/^ *//'"}
        self.endDictToken   = {   "APtail": "x",
                     "GWtail": "x",
                     "GWtail": "x",
                     "GWdict": "xxxThisIsTheEndTokenxxx",
                     "SWdict": "xxxThisIsTheEndTokenxxx",
                     "APdict": "xxxThisIsTheEndTokenxxx"}
        self.numberOfPortsInSwitch=[8,10,18,26,52]
        
        gwPrompt  = self.pluginPrefs.get(u"gwPrompt",u":~")
        self.promptOnServer["GWtail"] = gwPrompt
        self.promptOnServer["GWdict"] = gwPrompt


        self.blockAccess = []
        self.waitForMAC2vendor = False
        self.enableMACtoVENDORlookup    = self.pluginPrefs.get(u"enableMACtoVENDORlookup","21")
        if self.enableMACtoVENDORlookup != "0":
            self.M2V = M2Vclass.MAP2Vendor(refreshFromIeeAfterDays = int(self.enableMACtoVENDORlookup) )
            self.waitForMAC2vendor = self.M2V.makeFinalTable()
        
        self.updateDescriptions         = self.pluginPrefs.get(u"updateDescriptions", True)
        self.ignoreNeighborForFing      = self.pluginPrefs.get(u"ignoreNeighborForFing", True)
        self.useUNIFIdevices            = True
        self.ignoreNewNeighbors         = self.pluginPrefs.get(u"ignoreNewNeighbors", False)
        self.enableFINGSCAN             = self.pluginPrefs.get(u"enableFINGSCAN", False)
        self.sendUpdateToFingscanList   = {}
        self.unifiCloudKeySiteName      = self.pluginPrefs.get(u"unifiCloudKeySiteName", "default")
        self.unifiCloudKeyIP            = self.pluginPrefs.get(u"unifiCloudKeyIP", "")
        self.unifiCloudKeyPort          = self.pluginPrefs.get(u"unifiCloudKeyPort", "8443")
        self.unifiCloudKeyMode          = self.pluginPrefs.get(u"unifiCloudKeyMode", "ON")
        self.unifiCONTROLLERUserID      = self.pluginPrefs.get(u"unifiCONTROLLERUserID", "")
        self.unifiCONTROLLERPassWd      = self.pluginPrefs.get(u"unifiCONTROLLERPassWd", "")
        self.pluginPrefs[u"createUnifiDevicesCounter"] =     int(self.pluginPrefs.get(u"createUnifiDevicesCounter",0))   

        self.unifiUserID                = self.pluginPrefs.get(u"unifiUserID", "")
        self.unifiPassWd                = self.pluginPrefs.get(u"unifiPassWd", "")
        self.unifiApiWebPage            =  "/api/s/"
        self.unifiControllerSession     = ""
        self.unfiCurl                   = self.pluginPrefs.get(u"unfiCurl", "curl")
        self.restartIfNoMessageSeconds  = int(self.pluginPrefs.get(u"restartIfNoMessageSeconds", 600))
        self.expirationTime             = int(self.pluginPrefs.get(u"expirationTime", 120) )
        self.loopSleep                  = float(self.pluginPrefs.get(u"loopSleep", 2.))
        self.timeoutDICT                = unicode(int(self.pluginPrefs.get(u"timeoutDICT", 10)))
        self.folderNameCreated          = self.pluginPrefs.get(u"folderNameCreated",   "UNIFI_created")
        self.folderNameNeighbors        = self.pluginPrefs.get(u"folderNameNeighbors", "UNIFI_neighbors")
        self.folderNameSystem           = self.pluginPrefs.get(u"folderNameSystem",    "UNIFI_system")
        self.fixExpirationTime          = self.pluginPrefs.get(u"fixExpirationTime",    True)
        self.MACignorelist              = {}
        self.HANDOVER                   = {}
        self.lastUnifiCookie            = 0.
        self.groupStatusList        ={"Group0":{"members":{},"allHome":False,"allAway":False,"oneHome":False,"oneAway":False,"nHome":0,"nAway":0},
                                      "Group1":{"members":{},"allHome":False,"allAway":False,"oneHome":False,"oneAway":False,"nHome":0,"nAway":0},
                                      "Group2":{"members":{},"allHome":False,"allAway":False,"oneHome":False,"oneAway":False,"nHome":0,"nAway":0},
                                      "Group3":{"members":{},"allHome":False,"allAway":False,"oneHome":False,"oneAway":False,"nHome":0,"nAway":0},
                                      "Group4":{"members":{},"allHome":False,"allAway":False,"oneHome":False,"oneAway":False,"nHome":0,"nAway":0},
                                      "Group5":{"members":{},"allHome":False,"allAway":False,"oneHome":False,"oneAway":False,"nHome":0,"nAway":0},
                                      "Group6":{"members":{},"allHome":False,"allAway":False,"oneHome":False,"oneAway":False,"nHome":0,"nAway":0},
                                      "Group7":{"members":{},"allHome":False,"allAway":False,"oneHome":False,"oneAway":False,"nHome":0,"nAway":0},
                                      "Group8":{"members":{},"allHome":False,"allAway":False,"oneHome":False,"oneAway":False,"nHome":0,"nAway":0},
                                      "Group9":{"members":{},"allHome":False,"allAway":False,"oneHome":False,"oneAway":False,"nHome":0,"nAway":0}}
        self.groupStatusListALL     ={"nHome":0,"nAway":0,"anyChange":False}
        self.triggerList=[]
        self.statusChanged = 0


        self.updateStatesList={}
        self.logCount       = {}
        self.ipNumbersOfAPs = ["" for nn in range(_GlobalConst_numberOfAP)]
        self.APsEnabled     = [False for nn in range(_GlobalConst_numberOfAP)]

        self.ipNumbersOfSWs = ["" for nn in range(_GlobalConst_numberOfSW)]
        self.SWsEnabled     = [False for nn in range(_GlobalConst_numberOfSW)]

        self.devNeedsUpdate = []

        self.MACloglist     = {}

        self.readDictEverySeconds={}
        self.readDictEverySeconds[u"AP"] = unicode(int(self.pluginPrefs.get(u"readDictEverySecondsAP", 120) ))
        self.readDictEverySeconds[u"GW"] = unicode(int(self.pluginPrefs.get(u"readDictEverySecondsGW", 120) ))
        self.readDictEverySeconds[u"SW"] = unicode(int(self.pluginPrefs.get(u"readDictEverySecondsSW", 120) ))
        self.devStateChangeList          = {}
        self.APUP={}
        self.SWUP={}
        self.GWUP={}



        self.NumberOFActiveAP =0
        for i in range(_GlobalConst_numberOfAP):
            ip0 = self.pluginPrefs.get(u"ip"+unicode(i), "")
            ac  = self.pluginPrefs.get(u"ipON"+unicode(i), "")
            if not self.isValidIP(ip0): ac = False
            self.APUP[ip0]=time.time()
            self.ipNumbersOfAPs[i]=ip0
            if ac: 
                self.APsEnabled[i]=True
                self.NumberOFActiveAP += 1


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

        ip0 = self.pluginPrefs.get(u"ipUGA",  "")
        ac  = self.pluginPrefs.get(u"ipUGAON",False)

        if self.isValidIP(ip0) and ac:
            self.ipnumberOfUGA = ip0
            self.UGAEnabled = True
            self.GWUP[ip0] = time.time()
        else:
            self.ipnumberOfUGA = ""
            self.UGAEnabled = False

        self.getFolderId()





        self.stop = []
        self.stopCTRLC = False


        for ll in range(len(self.ipNumbersOfAPs)):
            self.killIfRunning(self.ipNumbersOfAPs[ll],u"")
        self.killIfRunning(self.ipnumberOfUGA, "")

        try:         indigo.variable.delete(u"Unifi_With_Status_Change")
        except:      pass
        try:         indigo.variable.create(u"Unifi_With_Status_Change")
        except:      pass

        self.setGroupStatus(init=True)        

        self.readDataStats() 
        self.readMACdata()
        self.checkDisplayStatus()
        
        self.pluginStartTime = time.time()+150


        self.checkforUnifiSystemDevicesState = "start"

        self.killIfRunning("", "")
        self.ML.checkLogFiles()

        return


    ####-----------------    ---------
    def checkDisplayStatus(self):
        try:
            for dev in indigo.devices.iter(self.pluginId):
                if u"displayStatus" not in dev.states: continue
            
            if "MAC" in dev.states and dev.deviceTypeId == u"UniFi" and dev.states[u"MAC"] in self.MACignorelist:
                if dev.states[u"displayStatus"].find(u"ignored") ==-1:
                    dev.updateStateOnServer("displayStatus",self.padDisplay(u"ignored")+datetime.datetime.now().strftime(u"%m-%d %H:%M:%S"))
                    if unicode(dev.displayStateImageSel) !="PowerOff":
                        dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
            else:
                self.exeDisplayStatus(dev, status)


            old = dev.states[u"displayStatus"].split(u" ")
            if len(old) ==3:
                new = self.padDisplay(old[0].strip())+dev.states[u"lastStatusChange"][5:]
                if dev.states[u"displayStatus"] != new:
                    dev.updateStateOnServer(u"displayStatus",new)
            else:
                dev.updateStateOnServer(u"displayStatus",self.padDisplay(old[0].strip())+dev.states[u"lastStatusChange"][5:])
        except  Exception, e:
            if len(unicode(e)) > 5:
                indigo.server.log(u"checkDisplayStatus in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))


        return 



    ####-----------------    ---------
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

    ####-----------------  update state lists ---------
    def deviceStartComm(self, dev):
        if self.ML.decideMyLog(u"Logic"): self.ML.myLog( text=u"starting device:  " + dev.name+"  "+unicode(dev.id)+"  "+dev.states[u"MAC"])
        if  self.pluginState == "init":
            dev.stateListOrDisplayStateIdChanged()
        elif self.pluginState == "run":
            self.devNeedsUpdate.append(unicode(dev.id))
        return

    ####-----------------    ---------
    def deviceStopComm(self, dev):
        if  self.pluginState != "stop":
            self.devNeedsUpdate.append(unicode(dev.id))
            if self.ML.decideMyLog(u"Logic"): self.ML.myLog( text=u"stopping device:  " + dev.name+"  "+unicode(dev.id) ,mType=u"LOGIC")

    ####-----------------    ---------
    def didDeviceCommPropertyChange(self, origDev, newDev):
        #if origDev.pluginProps['xxx'] != newDev.pluginProps['address']:
        #    return True
        return False
    ###########################     INIT    ## END   ########################


    ####-----------------    ---------
    def getFolderId(self):

            self.folderNameCreatedID        = 0
            self.folderNameSystemID    = 0
            try:
                self.folderNameCreatedID = indigo.devices.folders.getId(self.folderNameCreated)
            except:
                pass
            if self.folderNameCreatedID ==0:
                try:
                    ff = indigo.devices.folder.create(self.folderNameCreated)
                    self.folderNameCreatedID = ff.id
                except:
                    self.folderNameCreatedID = 0

            try:
                self.folderNameSystemID = indigo.devices.folders.getId(self.folderNameSystem)
            except:
                pass
            if self.folderNameSystemID ==0:
                try:
                    ff = indigo.devices.folder.create(self.folderNameSystem)
                    self.folderNameSystemID = ff.id
                except:
                    self.folderNameSystemID = 0

            try:
                self.folderNameNeighborsID = indigo.devices.folders.getId(self.folderNameNeighbors)
            except:
                pass
            if self.folderNameNeighborsID ==0:
                try:
                    ff = indigo.devices.folder.create(self.folderNameNeighbors)
                    self.folderNameNeighborsID = ff.id
                except:
                    self.folderNameNeighborsID = 0


            return

    ####-----------------    ---------
    def validateDeviceConfigUi(self, valuesDict, typeId, devId):
        try:
            if self.ML.decideMyLog(u"Logic"): self.ML.myLog( text=u"Validate Device dict:" +unicode(valuesDict) ,mType=u"SETUP")
            self.devNeedsUpdate.append(devId)

            dev = indigo.devices[int(devId)]
            if "groupMember" in dev.states: 
                memberList =""
                for group in  _GlobalConst_groupList:
                    if group in valuesDict: 
                        if unicode(valuesDict[group]).lower() =="true":
                            memberList += group+"/"
                            self.groupStatusList[group]["members"][unicode(devId)] = True
                    elif unicode(devId) in  self.groupStatusList[group]["members"]: del self.groupStatusList[group]["members"][unicode(devId)] 
                memberList = memberList.strip("/")
                if dev.states["groupMember"] != memberList:
                    dev.updateStateOnServer("groupMember",memberList)


            return (True, valuesDict)
        except  Exception, e:
            if len(unicode(e)) > 5: indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        errorDict = valuesDict
        return (False, valuesDict, errorDict)
        


    ####-----------------  set the geneeral config parameters---------
    def validatePrefsConfigUi(self, valuesDict):


        rebootRequired                              = False
        self.lastUnifiCookie                        = 0
        self.checkforUnifiSystemDevicesState        = "validateConfig"
        self.enableFINGSCAN                         = valuesDict[u"enableFINGSCAN"]
        self.ignoreNewNeighbors                     = valuesDict[u"ignoreNewNeighbors"]
        self.loopSleep                              = float(valuesDict[u"loopSleep"])
        self.unifiCONTROLLERUserID                  = valuesDict[u"unifiCONTROLLERUserID"]
        self.unifiCONTROLLERPassWd                  = valuesDict[u"unifiCONTROLLERPassWd"]

        
        
        if self.unifiUserID  != valuesDict[u"unifiUserID"]:rebootRequired = True
        if self.unifiPassWd  != valuesDict[u"unifiPassWd"]:rebootRequired = True
        self.unifiUserID                            = valuesDict[u"unifiUserID"]
        self.unifiPassWd                            = valuesDict[u"unifiPassWd"]
        self.unifiApiWebPage                        = valuesDict[u"unifiApiWebPage"]
        self.unfiCurl                               = valuesDict[u"unfiCurl"]
        self.unifiCloudKeyIP                        = valuesDict[u"unifiCloudKeyIP"]
        self.unifiCloudKeyPort                      = valuesDict[u"unifiCloudKeyPort"]
        self.unifiCloudKeyMode                      = valuesDict[u"unifiCloudKeyMode"]
        self.unifiCloudKeySiteName                  = valuesDict[u"unifiCloudKeySiteName"]
        self.ignoreNeighborForFing                  = valuesDict[u"ignoreNeighborForFing"]
        self.updateDescriptions                     = valuesDict[u"updateDescriptions"]
        self.folderNameCreated                      = valuesDict[u"folderNameCreated"]
        self.folderNameNeighbors                    = valuesDict[u"folderNameNeighbors"]
        self.folderNameSystem                       = valuesDict[u"folderNameSystem"]
        self.getFolderId()
        if self.enableMACtoVENDORlookup != valuesDict[u"enableMACtoVENDORlookup"] and self.enableMACtoVENDORlookup == "0":
            rebootRequired                         = True
        self.enableMACtoVENDORlookup               = valuesDict[u"enableMACtoVENDORlookup"]

        self.logFileActive                          = unicode(valuesDict[u"logFilePath"])
        if self.logFileActive =="no":
            self.logFile =""
        elif self.logFileActive =="indigo":
            self.logFile = self.indigoPath.split("Plugins/")[0]+"logs/"+self.pluginId+"/UniFi.log"
        else:
            self.logFile    = self.unifiPath + "UniFi.log"

        xx                                          = unicode(int(valuesDict[u"timeoutDICT"]))
        if xx != self.timeoutDICT:
            rebootRequired = True
            self.ML.myLog( text=u"restart...  timeoutDICT changed ")
            self.timeoutDICT                        = xx

        ##
        self.debugLevel         = []
        if valuesDict[u"debugLogic"]:           self.debugLevel.append("Logic")
        if valuesDict[u"debugLog"]:             self.debugLevel.append("Log")
        if valuesDict[u"debugDict"]:            self.debugLevel.append("Dict")
        if valuesDict[u"debugLogDetails"]:      self.debugLevel.append("LogDetails")
        if valuesDict[u"debugDictDetails"]:     self.debugLevel.append("DictDetails")
        if valuesDict[u"debugConnection"]:      self.debugLevel.append("Connection")
        if valuesDict[u"debugFing"]:            self.debugLevel.append("Fing")
        if valuesDict[u"debugall"]:             self.debugLevel.append("all")

        for TT in[u"AP",u"GW",u"SW"]:
            try:    xx           = unicode(int(valuesDict[u"readDictEverySeconds"+TT]))
            except: xx           = u"120"
            if xx != self.readDictEverySeconds[TT]:
                self.readDictEverySeconds[TT]                 = xx
                valuesDict[u"readDictEverySeconds"+TT]        = xx
                rebootRequired = True
                self.ML.myLog( text=u"restart...  readDictEverySeconds changed")


        try:    xx           = int(valuesDict[u"restartIfNoMessageSeconds"])
        except: xx           = 500
        if xx != self.restartIfNoMessageSeconds:
            self.restartIfNoMessageSeconds                   = xx
            valuesDict[u"restartIfNoMessageSeconds"]         = xx

        try:    self.expirationTime                 = int(valuesDict[u"expirationTime"])
        except: self.expirationTime                 = 120
        valuesDict[u"expirationTime"]               = self.expirationTime

        self.fixExpirationTime                      = valuesDict[u"fixExpirationTime"]



        acNew = [False for i in range(_GlobalConst_numberOfAP)]
        ipNew = ["" for i in range(_GlobalConst_numberOfAP)]
        for i in range(_GlobalConst_numberOfAP):
            ip0 = valuesDict[u"ip"+unicode(i)]
            ac  = valuesDict[u"ipON"+unicode(i)]
            if not self.isValidIP(ip0): ac = False
            acNew[i]             = ac
            ipNew[i]             = ip0
            if ac: acNew[i] = True
            if acNew[i] != self.APsEnabled[i]:
                rebootRequired =True
                self.ML.myLog( text=u"restart...  enable/disable AP changed")
            if ipNew[i] != self.ipNumbersOfAPs[i]:
                rebootRequired = True
                self.APUP[ipNew[i]] = time.time()
                self.ML.myLog( text=u"restart...  Ap ipNumber changed")
        self.ipNumbersOfAPs = copy.copy(ipNew)
        self.APsEnabled     = copy.copy(acNew)

        acNew = [False for i in range(_GlobalConst_numberOfSW)]
        ipNew = ["" for i in range(_GlobalConst_numberOfSW)]
        for i in range(_GlobalConst_numberOfSW):
            ip0 = valuesDict[u"ipSW"+unicode(i)]
            ac  = valuesDict[u"ipSWON"+unicode(i)]
            if not self.isValidIP(ip0): ac = False
            acNew[i]             = ac
            ipNew[i]             = ip0
            if ac: acNew[i] = True
            if acNew[i] != self.SWsEnabled[i]:
                rebootRequired =True
                self.ML.myLog( text=u"restart...  enable/disable SW changed")
            if ipNew[i] != self.ipNumbersOfSWs[i]:
                rebootRequired = True
                self.SWUP[ipNew[i]] = time.time()


                self.ML.myLog( text=u"restart...  SW ipNumber changed")
        self.ipNumbersOfSWs = copy.copy(ipNew)
        self.SWsEnabled     = copy.copy(acNew)



        gwPrompt    = valuesDict[u"gwPrompt"]
        if gwPrompt != self.promptOnServer["GWtail"]:
            rebootRequired = True
        self.promptOnServer["GWtail"] = gwPrompt
        self.promptOnServer["GWdict"] = gwPrompt

        ip0         = valuesDict[u"ipUGA"]
        if self.ipnumberOfUGA != ip0:
            rebootRequired = True
            self.ML.myLog( text=u"restart...  GW ipNumber changed")

        ac          = valuesDict[u"ipUGAON"]
        if not self.isValidIP(ip0): ac = False
        if self.UGAEnabled != ac:
            rebootRequired = True
            self.ML.myLog( text=u"restart...  enable/disable GW changed")

        self.UGAEnabled    = ac
        self.ipnumberOfUGA = ip0

        self.ML.myLogSet(debugLevel = self.debugLevel ,logFileActive=self.logFileActive, logFile = self.logFile)

        if rebootRequired: 
            self.quitNow = u"config changed"
        return True, valuesDict

    ####-----------------  config setting ----  END    ----------#########

    ####-----------------    ---------
    def getCPU(self,pid):
        ret = subprocess.Popen("ps -ef | grep " + unicode(pid) + " | grep -v grep", stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()
        lines = ret[0].strip("\n").split("\n")
        for line in lines:
            if len(line) < 100: continue
            items = line.split()
            if items[1] != unicode(pid): continue
            if len(items) < 6: continue
            return (items[6])
            break
        return ""

    ####-----------------    ---------
    def printConfigMenu(self, MAC="", valuesDict=None, typeId="", devId=0):
        try:
            self.ML.myLog( text=u" ",mType=" ")
            self.ML.myLog( text=u"UniFi  =============plugin config Parameters========",mType=" ")
            self.ML.myLog( text=u"AP ip#              enabled / disabled")
            for ll in range(len(self.ipNumbersOfAPs)):
                self.ML.myLog( text=self.ipNumbersOfAPs[ll].ljust(18) +"  "+ unicode(self.APsEnabled[ll]))

            self.ML.myLog( text=u"SW ip#              enabled / disabled")
            for ll in range(len(self.ipNumbersOfSWs)):
                self.ML.myLog( text=self.ipNumbersOfSWs[ll].ljust(18) +"  "+ unicode(self.SWsEnabled[ll]))

            self.ML.myLog( text=self.ipnumberOfUGA.ljust(18) + "  " + unicode(self.UGAEnabled)+ u"    gateway")
            self.ML.myLog( text=u"----------------------------------------------",mType=" ")
            self.ML.myLog( text=u"cpu used: ".ljust(30) + self.getCPU(self.myPID))

            self.ML.myLog( text=u"debugLevel".ljust(30)                + unicode(self.debugLevel).ljust(3))
            self.ML.myLog( text=u"unifi UserID".ljust(30)              + unicode(self.unifiUserID))
            self.ML.myLog( text=u"unifi PassWd".ljust(30)              + unicode(self.unifiPassWd))
            self.ML.myLog( text=u"unifi CONTROLLER Mode".ljust(30)     + unicode(self.unifiCloudKeyMode))
            self.ML.myLog( text=u"unifi CONTROLLER UserID".ljust(30)   + unicode(self.unifiCONTROLLERUserID))
            self.ML.myLog( text=u"unifi CONTROLLER PassWd".ljust(30)   + unicode(self.unifiCONTROLLERPassWd))
            self.ML.myLog( text=u"logFile".ljust(30)                   + unicode(self.logFile))
            self.ML.myLog( text=u"enableFINGSCAN".ljust(30)            + unicode(self.enableFINGSCAN))
            self.ML.myLog( text=u"ignoreNeighborForFing".ljust(30)     + unicode(self.ignoreNeighborForFing))
            self.ML.myLog( text=u"expirationTime".ljust(30)            + unicode(self.expirationTime).ljust(3)+u" [sec]")
            self.ML.myLog( text=u"readDictEverySeconds".ljust(30)      + unicode(self.readDictEverySeconds)+u" [sec]")
            self.ML.myLog( text=u"restartIfNoMessageSeconds".ljust(30) + unicode(self.restartIfNoMessageSeconds).ljust(3)+u" [sec]")
            self.ML.myLog( text=u"loopSleep".ljust(30)                 + unicode(self.loopSleep).ljust(3)+u" [sec]")

            self.ML.myLog( text=u"")
 
            self.ML.myLog( text=u"UniFi  =============plugin config Parameters========  END ", mType=" ")
            self.ML.myLog( text=u" ", mType=" ")

        except  Exception, e:
            if len(unicode(e)) > 5:
                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

        return valuesDict


    ####-----------------    ---------
    def printMACs(self,MAC=""):
        try:

            self.ML.myLog( text=u"===== UNIFI device info =========",  mType="  ")
            for dev in indigo.devices.iter(self.pluginId):
                if dev.deviceTypeId == u"client":         continue
                if MAC !="" and dev.states[u"MAC"] != MAC: continue
                self.ML.myLog( text=dev.name+ u"  id: "+unicode(dev.id).ljust(12)+ u";   type:"+ dev.deviceTypeId,  mType="device info")
                self.ML.myLog( text=u"props:",  mType=u" ")
                props = dev.pluginProps
                for p in props:
                    self.ML.myLog( text=unicode(props[p]),  mType=p)

                self.ML.myLog( text=u"states:",  mType=u" ")
                for p in dev.states:
                    self.ML.myLog( text=unicode(dev.states[p]),  mType=p)

            self.ML.myLog( text=u"counters, timers etc:",  mType=u" ")
            if MAC in self.MAC2INDIGO[u"UN"]:
                self.ML.myLog( text=unicode(self.MAC2INDIGO[u"UN"][MAC]), mType="UniFi")
                
            if MAC in self.MAC2INDIGO[u"AP"]:
                self.ML.myLog( text=unicode(self.MAC2INDIGO[u"AP"][MAC]), mType="AP")

            if MAC in self.MAC2INDIGO[u"SW"]:
                self.ML.myLog( text=unicode(self.MAC2INDIGO[u"SW"][MAC]), mType="SWITCH")

            if MAC in self.MAC2INDIGO[u"GW"]:
                self.ML.myLog( text=unicode(self.MAC2INDIGO[u"GW"][MAC]), mType="GATEWAY")

            if MAC in self.MAC2INDIGO[u"NB"]:
                self.ML.myLog( text=unicode(self.MAC2INDIGO[u"NB"][MAC]), mType="NEIGHBOR")


            self.ML.myLog( text=u"===== UNIFI device info ========= END ",  mType="device info")

        except  Exception, e:
            if len(unicode(e)) > 5:
                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

    ####-----------------    ---------
    def printALLMACs(self):
        try:

            self.ML.myLog( text=u"===== UNIFI device info =========",  mType="")

            for dev in indigo.devices.iter(self.pluginId):
                if dev.deviceTypeId == u"client": continue
                self.ML.myLog( text=u"id:     "+unicode(dev.id).ljust(12)+ u";   type:"+ dev.deviceTypeId,  mType=dev.name)
                line=u"props: "
                props = dev.pluginProps
                for p in props:
                    line+= unicode(p)+u":"+ unicode(props[p])+u";  "
                self.ML.myLog( text=line,  mType=u" ")
                line=u"states: "
                for p in dev.states:
                    line += unicode(p) + u":" + unicode(dev.states[p]) + u";  "
                self.ML.myLog( text=line,  mType=u" ")

                self.ML.myLog( text=u"temp data, counters, timer etc",  mType=u" ")
            for dd in self.MAC2INDIGO[u"UN"]:
                self.ML.myLog( text=unicode(self.MAC2INDIGO[u"UN"][dd]), mType="UNIFI   "+dd)
            for dd in self.MAC2INDIGO[u"AP"]:
                self.ML.myLog( text=unicode(self.MAC2INDIGO[u"AP"][dd]), mType="AP      "+dd)
            for dd in self.MAC2INDIGO[u"SW"]:
                self.ML.myLog( text=unicode(self.MAC2INDIGO[u"SW"][dd]), mType="SWITCH  "+dd)
            for dd in self.MAC2INDIGO[u"GW"]:
                self.ML.myLog( text=unicode(self.MAC2INDIGO[u"GW"][dd]), mType="GAETWAY "+dd)
            for dd in self.MAC2INDIGO[u"NB"]:
                self.ML.myLog( text=unicode(self.MAC2INDIGO[u"NB"][dd]), mType="NEIGHB  "+dd)

            self.ML.myLog( text=u"===== UNIFI device info ========= END ",  mType="")



        except  Exception, e:
            if len(unicode(e)) > 5:
                indigo.server.log( u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))


    ####-----------------    ---------
    def printALLUNIFIsreduced(self):
        try:

            self.ML.myLog( text=u"===== UNIFI device info =========",  mType="")

            dType ="UniFi"                                                     
            line =u"                                 curr.;  exp;   use ping  ;   use what 4;       WiFi;         WiFi;    DHCP;         SWITCH;"
            self.ML.myLog( text=line,  mType=u" ")
            line =u"id:         MAC#             ;  status; time;    up;  down;       Status;     Status;max-idle Time;  ax-AGE; UPtime changed;"
            self.ML.myLog( text=line,  mType=u"dev Name")
            for dev in indigo.devices.iter(self.pluginId):
                if dev.deviceTypeId != dType: continue
                props = dev.pluginProps
                mac = dev.states[u"MAC"]
                if u"useWhatForStatus" in props and props[u"useWhatForStatus"] == u"WiFi": wf = True 
                else:                                                                      wf = False 
                if True:                                            line  = unicode(dev.id).ljust(12)+mac+"; "
                if mac in self.MACignorelist:                       line += ("IGNORED").rjust(7)+u"; "
                elif u"status" in dev.states:                       line += (dev.states[u"status"]).rjust(7)+u"; "
                else:                                               line += (" ").rjust(7)+u"; "
                if u"expirationTime" in props :                     line += (unicode(props[u"expirationTime"]).split(".")[0]).rjust(4)+u"; "
                else:                                               line += " ".ljust(4)+"; "
                if u"usePingUP" in props :                          line += (unicode(props[u"usePingUP"])).rjust(5)+u"; "
                else:                                               line += " ".ljust(5)+"; "
                if u"usePingDOWN" in props :                        line += (unicode(props[u"usePingDOWN"])).rjust(5)+u"; "
                else:                                               line += " ".ljust(5)+"; "
                if u"useWhatForStatus" in props :                   line += (unicode(props[u"useWhatForStatus"])).rjust(12)+u"; "
                else:                                               line += " ".ljust(12)+"; "
                if u"useWhatForStatusWiFi" in props and wf:         line += (unicode(props[u"useWhatForStatusWiFi"])).rjust(10)+u"; "
                else:                                               line += " ".ljust(10)+"; "
                if u"idleTimeMaxSecs" in props and wf:              line += (unicode(props[u"idleTimeMaxSecs"])).rjust(12)+u"; "
                else:                                               line += " ".ljust(12)+"; "
                if u"useAgeforStatusDHCP" in props and not wf:      line += (unicode(props[u"useAgeforStatusDHCP"])).rjust(7)+u"; "
                else:                                               line += " ".ljust(7)+"; "
                if u"useupTimeforStatusSWITCH" in props and not wf: line += (unicode(props[u"useupTimeforStatusSWITCH"])).rjust(14)+u"; "
                else:                                               line += " ".ljust(14)+"; "
                self.ML.myLog( text=line,  mType=dev.name)

            self.ML.myLog( text=u"-------MEMBERS ---------------",mType="GROUPS----- ")
            
            for group in _GlobalConst_groupList:
                list = "\n          "
                lineNumber =0
                for member in sorted(self.groupStatusList[group]["members"]):
                    try: 
                        id = int(member) 
                        try: 
                            list += (indigo.devices[id].name).ljust(29)+", "
                            if len(list)/180  > lineNumber:
                                lineNumber +=1
                                list +="\n          "
                        except  Exception, e:
                            if len(unicode(e)) > 5:
                                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
                    except: pass
                if  list != "\n          ":
                    self.ML.myLog( text=u"members  "+list.strip(","), mType=group)
            self.ML.myLog( text=u"-------MEMBERS ----------------- END",mType="GROUPS----- ")

            self.ML.myLog( text=u" ", mType=" ")

            list = u"-------MEMBERS   ----------------\n          "
            lineNumber =0
            for member in sorted(self.MACignorelist):
                list += member+", "
                if len(list)/180  > lineNumber:
                    lineNumber +=1
                    list +="\n          "
            self.ML.myLog( text=list.strip(","), mType="IGNORED ----- ")
            self.ML.myLog( text=u"-------MEMBERS  -- -------------- END", mType="IGNORED ---")


            self.ML.myLog( text=u"===== UNIFI device info ========= END ",  mType="")



        except  Exception, e:
            if len(unicode(e)) > 5:
                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))




    ####-----------------  data stats menu items    ---------
    def buttonPrintStatsCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        self.buttonPrintTcpipStats()
        self.printUpdateStats()


    ####-----------------    ---------
    def buttonPrintTcpipStats(self):

        if len(self.dataStats["tcpip"]) ==0: return 
        nMin    = 0
        nSecs   = 0
        totByte = 0
        totMsg  = 0
        totErr  = 0
        totRes  = 0
        totAli  = 0
        for uType in sorted(self.dataStats["tcpip"].keys()):
            for ipNumber in sorted(self.dataStats["tcpip"][uType].keys()):
                if nSecs ==0: 
                    self.ML.myLog( text=u"=== data stats for received messages ====  collection started at "+ time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(self.dataStats["tcpip"][uType][ipNumber]["startTime"])), mType="data stats === START" )
                    self.ML.myLog( text=u"ipNumber            msgcount;    msgBytes;  errCount;  restarts;aliveCount;   msg/min; bytes/min;   err/min; aliveC/min", mType="dev type")
                nSecs = time.time() - self.dataStats["tcpip"][uType][ipNumber]["startTime"]
                nMin  = nSecs/60.
                out=ipNumber.ljust(18)
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
                totMsg  += self.dataStats["tcpip"][uType][ipNumber]["inMessageCount"] 
                totErr  += self.dataStats["tcpip"][uType][ipNumber]["inErrorCount"] 
                totRes  += self.dataStats["tcpip"][uType][ipNumber]["restarts"] 
                totAli  += self.dataStats["tcpip"][uType][ipNumber]["aliveTestCount"] 
                
                self.ML.myLog( text=out, mType="  "+uType+"-"+self.dataStats["tcpip"][uType][ipNumber]["APN"])
        self.ML.myLog( text=u"total             "+ "%10d"%totMsg+";%12d"%totByte+";%10d"%totErr+ ";%10d"%totRes+u";%10d"%totAli+ ";%10.3f"%(totMsg/nMin) + ";%10.1f"%(totByte/nMin)+ ";%10.7f"%(totErr/nMin)+ ";%10.3f"%(totAli/nMin)+";", mType="T O T A L S")
        self.ML.myLog( text=u"===  total time measured: %d "%(nSecs/(24*60*60)) +time.strftime("%H:%M:%S", time.gmtime(nSecs)), mType="data stats === END" )


    ####-----------------    ---------
    def printUpdateStats(self,):
        if len(self.dataStats["updates"]) ==0: return 
        nSecs = max(1,(time.time()-  self.dataStats["updates"]["startTime"]))
        nMin  = nSecs/60.
        self.ML.myLog( text=u" ", mType=" " )
        self.ML.myLog( text=u"===  measuring started at: " +time.strftime("%H:%M:%S",time.localtime(self.dataStats["updates"]["startTime"])), mType="indigo update stats === " )
        self.ML.myLog( text=u"updates: %10d"%self.dataStats["updates"]["devs"]  +";  updates/sec: %10.2f"%(self.dataStats["updates"]["devs"]  /nSecs)+";  updates/minute: %10.2f"%(self.dataStats["updates"]["devs"]  /nMin),  mType="   device ")
        self.ML.myLog( text=u"updates: %10d"%self.dataStats["updates"]["states"]+";  updates/sec: %10.2f"%(self.dataStats["updates"]["states"]/nSecs)+";  updates/minute: %10.2f"%(self.dataStats["updates"]["states"]/nMin),  mType="   states ")
        self.ML.myLog( text=u"===  total time measured: %d "%(nSecs/(24*60*60)) +time.strftime(" %H:%M:%S", time.gmtime(nSecs)),  mType="indigo update stats === END" )
        return 

    ####-----------------    ---------
    def buttonZeroStatsCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        self.zeroDataStats()
        return 
    ####-----------------    ---------
    def buttonResetStatsCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        self.resetDataStats()
        return 

    ####-----------------  reboot unifi device   ---------
    ####-----------------    ---------
    def filterUnifiDevicesACTION(self, valuesDict=None, filter="", typeId="", devId=""):
        return self.filterUnifDevices(valuesDict)

    ####-----------------    ---------
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

    ####-----------------    ---------
    def buttonConfirmrebootCALLBACKaction(self, action1=None, filter="", typeId="", devId=""):
        return self.buttonConfirmrebootCALLBACK(valuesDict=action1.props)

    ####-----------------    ---------
    def buttonConfirmrebootCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        ip_type  =  valuesDict["rebootUNIFIdeviceSelected"].split("-")
        ipNumber = ip_type[0]
        dtype    = ip_type[1]
        cmd = "/usr/bin/expect  '"
        cmd+= self.pathToPlugin + "rebootUNIFIdeviceAP.exp" + "' "
        cmd+= self.unifiUserID + " " 
        cmd+= self.unifiPassWd + " "
        cmd+= ipNumber + " "
        cmd+= self.promptOnServer[dtype] + " &"
        if self.ML.decideMyLog(u"Connection"): self.ML.myLog( text=cmd ,mType="REBOOT")
        ret = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()
        if self.ML.decideMyLog(u"Connection"): self.ML.myLog( text=unicode(ret) ,mType="REBOOT")
        
        return 


    ####-----------------  set properties for all devices   ---------
    def buttonConfirmSetWifiOptCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        for MAC in self.MAC2INDIGO["UN"]:
            try:
                dev = indigo.devices[self.MAC2INDIGO["UN"][MAC]["devId"]]
                props = dev.pluginProps
                self.ML.myLog( text=u"doing "+ dev.name)
                if props["useWhatForStatus"] == "WiFi":
                    props["useWhatForStatusWiFi"]   = "Optimized"
                    props[u"idleTimeMaxSecs"]       = u"30"
                    dev.replacePluginPropsOnServer(props)
                    
                    dev = indigo.devices[self.MAC2INDIGO["UN"][MAC]["devId"]]
                    props = dev.pluginProps
                    self.ML.myLog( text=u"done "+ dev.name+" "+ unicode(props))
            except  Exception, e:
                    indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        self.printALLUNIFIsreduced()
        return 
    ####-----------------    ---------
    def buttonConfirmSetWifiIdleCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        for MAC in self.MAC2INDIGO["UN"]:
            try:
                dev = indigo.devices[self.MAC2INDIGO["UN"][MAC]["devId"]]
                props = dev.pluginProps
                if props["useWhatForStatus"] == "WiFi":
                    props["useWhatForStatusWiFi"]   = "IdleTime"
                    props[u"idleTimeMaxSecs"]       = u"30"
                    dev.replacePluginPropsOnServer(props)
            except:
                pass
        self.printALLUNIFIsreduced()
        return 
    ####-----------------    ---------
    def buttonConfirmSetWifiUptimeCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        for MAC in self.MAC2INDIGO["UN"]:
            try:
                dev = indigo.devices[self.MAC2INDIGO["UN"][MAC]["devId"]]
                props = dev.pluginProps
                if props["useWhatForStatus"] == "WiFi":
                    props["useWhatForStatusWiFi"]   = "UpTime"
                    dev.replacePluginPropsOnServer(props)
            except:
                pass
        self.printALLUNIFIsreduced()
        return 
    ####-----------------    ---------
    def buttonConfirmSetNonWifiOptCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        for MAC in self.MAC2INDIGO["UN"]:
            try:
                dev = indigo.devices[self.MAC2INDIGO["UN"][MAC]["devId"]]
                props = dev.pluginProps
                if props["useWhatForStatus"] != "WiFi":
                    props["useWhatForStatus"]           = "OptDhcpSwitch"
                    props[u"useAgeforStatusDHCP"]       = u"60"
                    props[u"useupTimeforStatusSWITCH"]  = True
                    dev.replacePluginPropsOnServer(props)
            except:
                pass
        self.printALLUNIFIsreduced()
        return 
    ####-----------------    ---------
    def buttonConfirmSetNonWifiToSwitchCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        for MAC in self.MAC2INDIGO["UN"]:
            try:
                dev = indigo.devices[self.MAC2INDIGO["UN"][MAC]["devId"]]
                props = dev.pluginProps
                if props["useWhatForStatus"] != "WiFi":
                    props["useWhatForStatus"]           = "SWITCH"
                    props[u"useupTimeforStatusSWITCH"]  = True
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
                    props["useWhatForStatus"]           = "DHCP"
                    props[u"useAgeforStatusDHCP"]       = u"60"
                    dev.replacePluginPropsOnServer(props)
            except:
                pass
        self.printALLUNIFIsreduced()
        return 
    ####-----------------    ---------
    def buttonConfirmSetUsePingUPonCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        for MAC in self.MAC2INDIGO["UN"]:
            try:
                dev = indigo.devices[self.MAC2INDIGO["UN"][MAC]["devId"]]
                props = dev.pluginProps
                props["usePingUP"]           = True
                dev.replacePluginPropsOnServer(props)
            except:
                pass
        self.printALLUNIFIsreduced()
        return 
    ####-----------------    ---------
    def buttonConfirmSetUsePingUPoffCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        for MAC in self.MAC2INDIGO["UN"]:
            try:
                dev = indigo.devices[self.MAC2INDIGO["UN"][MAC]["devId"]]
                props = dev.pluginProps
                props["usePingUP"]           = False
                dev.replacePluginPropsOnServer(props)
            except:
                pass
        self.printALLUNIFIsreduced()
        return 
    ####-----------------    ---------
    def buttonConfirmSetUsePingDOWNonCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        for MAC in self.MAC2INDIGO["UN"]:
            try:
                dev = indigo.devices[self.MAC2INDIGO["UN"][MAC]["devId"]]
                props = dev.pluginProps
                props["usePingDOWN"]           = True
                dev.replacePluginPropsOnServer(props)
            except:
                pass
        self.printALLUNIFIsreduced()
        return 
    ####-----------------    ---------
    def buttonConfirmSetUsePingDOWNoffCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        for MAC in self.MAC2INDIGO["UN"]:
            try:
                dev = indigo.devices[self.MAC2INDIGO["UN"][MAC]["devId"]]
                props = dev.pluginProps
                props["usePingDOWN"]           = False
                dev.replacePluginPropsOnServer(props)
            except:
                pass
        self.printALLUNIFIsreduced()
        return 
    ####-----------------    ---------
    def buttonConfirmSetExpTimeCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        for MAC in self.MAC2INDIGO["UN"]:
            try:
                dev = indigo.devices[self.MAC2INDIGO["UN"][MAC]["devId"]]
                props = dev.pluginProps
                props["expirationTime"]           =int(valuesDict["expirationTime"])
                dev.replacePluginPropsOnServer(props)
            except:
                pass
        self.printALLUNIFIsreduced()
        return 


    ####-----------------    ---------
    def inpDummy(self, valuesDict=None, filter="", typeId="", devId=""):
        return valuesDict

    ####-----------------  filter specific MAC number   ---------


    ####-----------------    ---------
    def filterWiFiDevice(self, filter="", valuesDict=None, typeId="", devId=""):
    
        list = []
        for dev in indigo.devices.iter(self.pluginId):
            if dev.deviceTypeId != "UniFi":   continue
            if "AP" not  in dev.states:       continue
            if len(dev.states["AP"]) < 5:     continue
            list.append([dev.states["MAC"].lower(),dev.name+"--"+ dev.states["MAC"] +"-- AP:"+dev.states["AP"]])
        return sorted(list, key=lambda x: x[1])

    ####-----------------    ---------
    def filterUNIFIsystemDevice(self, filter="", valuesDict=None, typeId="", devId=""):
    
        list = []
        for dev in indigo.devices.iter(self.pluginId):
            if dev.deviceTypeId in [u"UniFi","neighbor"]:   continue
            list.append([dev.states["MAC"].lower(),dev.name+"--"+ dev.states["MAC"] ])
        return sorted(list, key=lambda x: x[1])



    ####-----------------    ---------
    def filterMACNoIgnored(self, filter="", valuesDict=None, typeId="", devId=""):
        xlist = []
        for dev in indigo.devices.iter(self.pluginId):
            if u"MAC" in dev.states:
                if "displayStatus" in dev.states and   dev.states["displayStatus"].find("ignored") >-1: continue
                xlist.append([dev.states[u"MAC"],dev.states[u"MAC"] + " - "+dev.name])
        return sorted(xlist, key=lambda x: x[1])

    ####-----------------    ---------
    def filterMAC(self, filter="", valuesDict=None, typeId="", devId=""):
        xlist = []
        for dev in indigo.devices.iter(self.pluginId):
            if u"MAC" in dev.states:
                xlist.append([dev.states[u"MAC"],dev.states[u"MAC"] + " - "+dev.name])
        return sorted(xlist, key=lambda x: x[1])
        
    ####-----------------    ---------
    def filterMACunifiOnly(self, filter="", valuesDict=None, typeId="", devId=""):
        xlist = []
        for dev in indigo.devices.iter(self.pluginId):
            if u"MAC" in dev.states:
                if dev.deviceTypeId != u"UniFi": continue
                xlist.append([dev.states[u"MAC"],dev.name+u"--"+dev.states[u"MAC"] ])
        return sorted(xlist, key=lambda x: x[1])
        
    ####-----------------    ---------
    def filterMACunifiOnlyUP(self, filter="", valuesDict=None, typeId="", devId=""):
        xlist = []
        for dev in indigo.devices.iter(self.pluginId):
            if u"MAC" in dev.states:
                if dev.deviceTypeId != u"UniFi": continue
                if u"status" in dev.states and dev.states[u"status"].find(u"up") >-1:
                    xlist.append([dev.states[u"MAC"],dev.name+u"--"+dev.states[u"MAC"] ])
        return sorted(xlist, key=lambda x: x[1])
        
    ####-----------------    ---------
    def filterMAConlyAP(self, filter="", valuesDict=None, typeId="", devId=""):
        xlist = []
        for dev in indigo.devices.iter(self.pluginId):
            if u"MAC" in dev.states:
                if dev.deviceTypeId != u"Device-AP": continue
                if u"status" in dev.states and dev.states[u"status"].find(u"up") >-1:
                    xlist.append([dev.states[u"MAC"],dev.name+u"--"+dev.states[u"MAC"] ])
        return sorted(xlist, key=lambda x: x[1])
        
        
    ####-----------------    ---------
    def filterMACunifiIgnored(self, filter="", valuesDict=None, typeId="", devId=""):
        xlist = []
        for MAC in self.MACignorelist:
                textMAC = MAC
                for dev in indigo.devices.iter(self.pluginId):
                    if dev.deviceTypeId != "UniFi": continue
                    if "MAC" in dev.states:
                        textMAC = dev.name+" - "+MAC
                        break
                xlist.append([MAC,textMAC])
        return sorted(xlist, key=lambda x: x[1])
        
    ####-----------------  logging for specific MAC number   ---------



    ####-----------------    ---------
    def buttonConfirmStartLoggingCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        self.MACloglist[valuesDict[u"MACdeviceSelected"]]=True
        self.ML.myLog( text=u"start track-logging for MAC# "+valuesDict[u"MACdeviceSelected"])
        return 
    ####-----------------    ---------
    def buttonConfirmStopLoggingCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        self.MACloglist={}
        self.ML.myLog( text=u" stop logging ")
        return 

    ####-----------------  device info   ---------
    def buttonConfirmPrintMACCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        self.printMACs(MAC=valuesDict[u"MACdeviceSelected"])
        return 
    ####-----------------    ---------
    def buttonprintALLMACsCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        self.printALLMACs()
        return 
    ####-----------------    ---------
    def printALLUNIFIsreducedMenue(self, valuesDict=None, filter="", typeId="", devId=""):
        self.printALLUNIFIsreduced()
        return 



    ####-----------------  Ignore MAC info   ---------
    def buttonConfirmStartIgnoringCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        self.MACignorelist[valuesDict[u"MACdeviceSelected"]]=1
        self.ML.myLog( text=u"start ignoring  MAC# "+valuesDict[u"MACdeviceSelected"])
        for dev in indigo.devices.iter(self.pluginId):
            if dev.deviceTypeId != u"UniFi": continue
            if u"MAC" in dev.states  and dev.states[u"MAC"] == valuesDict[u"MACdeviceSelected"]:
                if u"displayStatus" in dev.states: 
                    dev.updateStateOnServer(u"displayStatus",self.padDisplay(u"ignored")+datetime.datetime.now().strftime(u"%m-%d %H:%M:%S"))
                    dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
                dev.updateStateOnServer(u"status","ignored")
        self.saveMACdata()
        return 
    ####-----------------  UN- Ignore MAC info   ---------
    ####-----------------    ---------
    def buttonConfirmStopIgnoringCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        try: del self.MACignorelist[valuesDict[u"MACdeviceIgnored"]]
        except: pass
        for dev in indigo.devices.iter(self.pluginId):
            if dev.deviceTypeId != u"UniFi": continue
        self.saveMACdata()
        self.ML.myLog( text=u" stop ignoring  MAC# " +valuesDict[u"MACdeviceIgnored"])
        return 



    ####-----------------  powercycle switch port   ---------
    ####-----------------    ---------
    def filterUnifiSwitchACTION(self, valuesDict=None, filter="", typeId="", devId=""):
        return self.filterUnifiSwitch(valuesDict)

    ####-----------------    ---------
    def filterUnifiSwitch(self, filter="", valuesDict=None, typeId="", devId=""):
        list = []
        for dev in indigo.devices.iter(self.pluginId):
            if dev.deviceTypeId.find(u"Device-SW")==-1: continue
            swNo = int(dev.states[u"switchNo"])
            if self.SWsEnabled[swNo]:
                list.append((unicode(swNo)+u"-SWtail-"+unicode(dev.id),unicode(swNo)+"-"+self.ipNumbersOfSWs[swNo]+u"-"+dev.name))
        return list

    def buttonConfirmSWCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        self.unifiSwitchSelectedID =  valuesDict[u"selectedUnifiSwitch"].split("-")[2]
        return
        
    ####-----------------    ---------
    def filterUnifiSwitchPort(self, filter="", valuesDict=None, typeId="", devId=""):
    
        list = []
        try:    int(self.unifiSwitchSelectedID)
        except: return list
        
        dev = indigo.devices[int(self.unifiSwitchSelectedID)]
        snNo = unicode(dev.states[u"switchNo"] )
        for port in range(99):
            if u"port_%02d"%port not in dev.states: continue
            if  dev.states[u"port_%02d"%port].find("poe") >-1:
                name =""
                for dev2 in indigo.devices.iter(self.pluginId):
                    if "SW_Port" in dev2.states and len(dev2.states["SW_Port"]) > 2:
                        sw   = dev2.states["SW_Port"].split(":")
                        if sw[0] == snNo:
                            if sw[1].find("poe") >-1:
                                if unicode(port) == sw[1].split("-")[0]:
                                    name = " - "+dev2.name
                                    break
                list.append([port,u"port#"+unicode(port)+name])
        return list

    ####-----------------    ---------
    def filterUnifiClient(self, filter="", valuesDict=None, typeId="", devId=""):
    
        list = []
        for dev2 in indigo.devices.iter(self.pluginId):
            if "SW_Port" in dev2.states and len(dev2.states["SW_Port"]) > 2:
                sw   = dev2.states["SW_Port"].split(":")
                if sw[1].find("poe") >-1:
                    port = sw[1].split("-")[0]
                    list.append([sw[0]+"-"+port,u"sw"+sw[0]+"-"u"port#"+unicode(port)+" - "+dev2.name])
        return list
                

    ####-----------------    ---------
    def buttonConfirmpowerCycleCALLBACKaction(self, action1=None, filter="", typeId="", devId=""):
        return self.buttonConfirmpowerCycleCALLBACK(valuesDict=action1.props)

    ####-----------------    ---------
    def buttonConfirmpowerCycleCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        ip_type  =  valuesDict[u"selectedUnifiSwitch"].split(u"-")
        ipNumber = self.ipNumbersOfSWs[int(ip_type[0])]
        dtype    = ip_type[1]
        port     = unicode(valuesDict[u"selectedUnifiSwitchPort"])
        cmd = u"/usr/bin/expect  '"
        cmd+= self.pathToPlugin + u"cyclePort.exp" + "' "
        cmd+= self.unifiUserID + u" " 
        cmd+= self.unifiPassWd + u" "
        cmd+= ipNumber + " "
        cmd+= port + u" "
        cmd+= self.promptOnServer[dtype] +u" &"
        if self.ML.decideMyLog(u"Connection"): self.ML.myLog( text=cmd ,mType="RECYCLE")
        ret = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()
        if self.ML.decideMyLog(u"Connection"): self.ML.myLog( text=unicode(ret) ,mType="RECYCLE")
        return 
 



    ####-----------------    ---------
    def buttonConfirmpowerCycleClientsCALLBACKaction(self, action1=None, filter="", typeId="", devId=""):
        return self.buttonConfirmpowerCycleClientsCALLBACK(valuesDict=action1.props)

    ####-----------------    ---------
    def buttonConfirmpowerCycleClientsCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        ip_type  =  valuesDict[u"selectedUnifiClientSwitchPort"].split(u"-")
        valuesDict[u"selectedUnifiSwitch"]      = ip_type[0]+u"-SWtail"
        valuesDict[u"selectedUnifiSwitchPort"]  = ip_type[1]
        self.buttonConfirmpowerCycleCALLBACK(valuesDict)
        return 


   
    ####-----------------  Unifi api calls    ---------


######## block / unblock reconnect 
    ####-----------------    ---------
    def buttonConfirmReconnectCALLBACKaction(self, action1=None, filter="", typeId="", devId=""):
        return self.buttonConfirmReconnectCALLBACK(valuesDict=action1.props)

    ####-----------------    ---------
    def buttonConfirmReconnectCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        self.executeCMDOnController(data={"cmd":"kick-sta","mac":valuesDict["selectedDevice"]},pageString="/cmd/stamgr")
        return 
        
    ####-----------------    ---------
    def buttonConfirmBlockCALLBACKaction(self, action1=None, filter="", typeId="", devId=""):
        return self.buttonConfirmBlockCALLBACK(valuesDict=action1.props)

    ####-----------------    ---------
    def buttonConfirmBlockCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        self.executeCMDOnController(data={"cmd":"block-sta","mac":valuesDict["selectedDevice"]},pageString="/cmd/stamgr")
        return 

    ####-----------------    ---------
    def buttonConfirmUnBlockCALLBACKaction(self, action1=None, filter="", typeId="", devId=""):
        return self.buttonConfirmUnBlockCALLBACK(valuesDict=action1.props)

    ####-----------------    ---------
    def buttonConfirmUnBlockCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        self.executeCMDOnController(data={"cmd":"unblock-sta","mac":valuesDict["selectedDevice"]}, pageString="/cmd/stamgr")
        return 
######## block / unblock reconnec  end 

######## reports for specific stations / devices 
    ####-----------------    ---------
    def buttonConfirmPrintDevInfoFromControllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        self.executeCMDOnController(data={}, pageString="/stat/device/"+valuesDict["MACdeviceSelectedsys"], jsonAction="print",startText="== Device print: /stat/device/"+valuesDict["MACdeviceSelectedsys"]+" ==")
        return 

    ####-----------------    ---------
    def buttonConfirmPrintClientInfoFromControllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        self.executeCMDOnController(data={}, pageString="/stat/sta/"+valuesDict["MACdeviceSelectedclient"], jsonAction="print",startText="== Client print: /stat/sta/"+valuesDict["MACdeviceSelectedclient"]+" ==")
        return 

######## reports all devcies    
    ####-----------------    ---------
    def buttonConfirmPrintalluserInfoFromControllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        data = self.executeCMDOnController(data={"type":"all","conn":"all"}, pageString="/stat/alluser/", jsonAction="returnData")
        self.unifsystemReport3(data, "== ALL USER report ==")
        return
        
    ####-----------------    ---------
    def buttonConfirmPrintuserInfoFromControllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        data = self.executeCMDOnController(data={}, pageString="/list/user/", jsonAction="returnData")
        self.unifsystemReport3(data, "== USER report ==")

####   general reports
    ####-----------------    ---------
    def buttonConfirmPrintHealthInfoFromControllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        data = self.executeCMDOnController(data={}, pageString="/stat/health/", jsonAction="returnData")
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
                if item2 =="subsystem":   continue
                if item2 =="status":      continue
                if item2 =="tx_bytes-r":  continue
                if item2 =="rx_bytes-r":  continue
                ll+=unicode(item2)+":"+unicode(item[item2])+";  "
            out+=ll+("\n")
        self.ML.myLog( text=u" ",mType="unifi-Report")
        self.ML.myLog( text=out,mType="unifi-Report")
        return 

    ####-----------------    ---------
    def buttonConfirmPrintPortForWardInfoFromControllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        data =self.executeCMDOnController(data={}, pageString="/stat/portforward/", jsonAction="returnData")
        out ="== PortForward report ==\n"
        out+= "##".ljust(4) + "name".ljust(20) + "protocol".ljust(10) + "source".ljust(16)  + "fwd_port".ljust(9)+ "dst_port".ljust(9)+ "fwd_ip".ljust(17)+ "rx_bytes".ljust(10)+ "rx_packets".ljust(17)+"\n"            
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
        self.ML.myLog( text=u" ",mType="unifi-Report")
        self.ML.myLog( text=out,mType="unifi-Report")
        return 
    ####-----------------    ---------
    def buttonConfirmPrintAlarmInfoFromControllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        data = self.executeCMDOnController(data={}, pageString="/list/alarm/", jsonAction="returnData")
        self.unifsystemReport1(data,True,"  ==AlarmReport==",limit=99999)
        return
        

    ####-----------------    ---------
    def buttonConfirmPrintEventInfoFromControllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):

        limit                     = 100
        if "PrintEventInfoMaxEvents" in valuesDict:
            try:    limit = int(valuesDict["PrintEventInfoMaxEvents"])
            except: pass

        PrintEventInfoLoginEvents = False
        if "PrintEventInfoLoginEvents" in valuesDict:
            try:    PrintEventInfoLoginEvents = valuesDict["PrintEventInfoLoginEvents"]
            except: pass


        if PrintEventInfoLoginEvents:
            ltype = "WITH"
            useLimit = limit
        else:
            ltype = "Skipping"
            useLimit = 5*limit

        data = self.executeCMDOnController(data={"_sort":"+time", "within":999,"_limit":useLimit}, pageString="/stat/event/", jsonAction="returnData")
        self.unifsystemReport1(data,False,"  ==EVENTs ..;  last "+str(limit)+" events ;  -- "+ltype+" login events ==",limit,PrintEventInfoLoginEvents=PrintEventInfoLoginEvents)
            
        return 
        
    ####-----------------    ---------
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
            else:                 ll+= (" ").ljust(21)

            if "num_sta" in item:
                ll+= unicode(item["num_sta"]).rjust(8)
            else:                 ll+= (" ").rjust(8)

            if "bytes" in item:
                ll+= ("{0:,d}".format(int(item["bytes"]))).rjust(12)
            else:                 ll+= (" ").rjust(12)

            out+=ll+("\n")
        self.ML.myLog( text=u" ",mType="unifi-Report")
        self.ML.myLog( text=out,mType="unifi-Report")
        return 

        
    ####-----------------    ---------
    def buttonConfirmPrint48HourInfoFromControllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        en = int( time.time() - (time.time() % 3600) ) * 1000
        st = en - 2*86400000
        data = self.executeCMDOnController(data={"attrs": ["bytes","wan-tx_bytes","wan-rx_bytes","wan-tx_bytes", "num_sta", "wlan-num_sta", "lan-num_sta", "time"], "start": st, "end": en}, pageString="/stat/report/hourly.site", jsonAction="returnData")
        self.unifsystemReport2(data,"== 48 HOUR report ==")

    ####-----------------    ---------
    def buttonConfirmPrint7DayInfoFromControllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        en = int( time.time() - (time.time() % 3600) ) * 1000
        st = en - 7*86400000
        data = self.executeCMDOnController(data={"attrs": ["bytes","wan-tx_bytes","wan-rx_bytes","wan-tx_bytes", "num_sta", "wlan-num_sta", "lan-num_sta", "time"], "start": st, "end": en}, pageString="/stat/report/daily.site", jsonAction="returnData")
        self.unifsystemReport2(data,"== 7 DAY report ==")



    ####-----------------    ---------
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
            else:                 ll+= (" ").ljust(6)

            if "bc_filter_enabled" in item:
                ll+= unicode(item["bc_filter_enabled"]).ljust(6)
            else:                ll+= (" ").ljust(6)

            if "bc_filter_list" in item:
                ll+= unicode(item["bc_filter_list"]).ljust(15)
            else:                ll+= (" ").ljust(15)

            if "dtim_mode" in item:
                ll+= unicode(item["dtim_mode"]).ljust(8)
            else:                ll+= (" ").ljust(8)

            if "dtim_na" in item:
                ll+= unicode(item["dtim_na"]).ljust(3)
            else:                ll+= (" ").ljust(3)

            if "dtim_ng" in item:
                ll+= unicode(item["dtim_ng"]).ljust(3)
            else:                ll+= (" ").ljust(3)

            if "mac_filter_enabled" in item:
                ll+= unicode(item["mac_filter_enabled"]).ljust(6)
            else:                ll+= (" ").ljust(6)

            if "mac_filter_list" in item:
                ll+= unicode(item["mac_filter_list"]).ljust(20)
            else:                ll+= (" ").ljust(20)

            if "mac_filter_policy" in item:
                ll+= unicode(item["mac_filter_policy"]).ljust(8)
            else:                ll+= (" ").ljust(8)

            if "schedule" in item:
                ll+= unicode(item["schedule"]).ljust(15)
            else:                ll+= (" ").ljust(15)

            if "security" in item:
                ll+= unicode(item["security"]).ljust(8)
            else:                ll+= (" ").ljust(8)

            if "wpa_enc" in item:
                ll+= unicode(item["wpa_enc"]).ljust(6)
            else:                ll+= (" ").ljust(6)
            
            if "wpa_mode" in item:
                ll+= unicode(item["wpa_mode"]).ljust(6)
            else:                ll+= (" ").ljust(6)


            out+=ll+("\n")
        self.ML.myLog( text=u" ",mType="unifi-Report")
        self.ML.myLog( text=out,mType="unifi-Report")
        return 


    ####-----------------    ---------
    def unifsystemReport1(self,data,useName, start,limit, PrintEventInfoLoginEvents= False):
        out =start+"\n"
        if useName:
            out+= "##### datetime------".ljust(21+6) + "name---".ljust(30) + "subsystem--".ljust(12) + "key--------".ljust(30)  + "msg-----".ljust(50)+"\n"            
        else:
            out+= "##### datetime------".ljust(21+6)                       + "subsystem--".ljust(12) + "key--------".ljust(30)  + "msg-----".ljust(50)+"\n"            
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
                for  xx in ["ap_name","gw_name","sw_name","ap_name"]:
                    if xx in item:    
                        ll+= item[xx].ljust(30)
                        found = True
                        break
                if not found:
                        ll+= " ".ljust(30)
            ll +=item["subsystem"].ljust(12) + item["key"].ljust(30) + item["msg"].ljust(50)
            out+= ll.replace("\n","")+"\n"
        self.ML.myLog( text=u" ",mType="unifi-Report")
        self.ML.myLog( text=out,mType="unifi-Report")
        return 

    ####-----------------    ---------
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
                if item2 =="lan-num_sta":   continue
                if item2 =="wlan-num_sta":  continue
                if item2 =="num_sta":       continue
                if item2 =="wan-rx_bytes":  continue
                if item2 =="wan-tx_bytes":  continue
                if item2 =="time":          continue
                if item2 =="oid":           continue
                if item2 =="site":          continue
                ll+=unicode(item2)+":"+unicode(item[item2])+";  "

            out+=ll+("\n")
        self.ML.myLog( text=u" ",mType="unifi-Report")
        self.ML.myLog( text=out,mType="unifi-Report")
        return 
    
    ####-----------------    ---------
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
                if item2 =="hostname":     continue
                if item2 =="mac":          continue
                if item2 =="first_seen":   continue
                if item2 =="last_seen":    continue
                if item2 =="site_id":      continue
                if item2 =="_id":          continue
                if item2 =="network_id":   continue
                if item2 =="usergroup_id": continue
                if item2 =="noted":        continue
                if item2 =="name":         continue
                if item2 =="is_wired":     continue
                if item2 =="oui":          continue
                if item2 =="blocked":      continue
                if item2 =="fixed_ip":     continue
                if item2 =="use_fixedip":  continue
                if item2 =="is_guest":     continue
                if item2 =="duration":     continue
                if item2 =="rx_bytes":     continue
                if item2 =="tx_bytes":     continue
                if item2 =="tx_packets":   continue
                if item2 =="rx_packets":   continue
                ll+=unicode(item2)+":"+unicode(item[item2])+";  "
            out+=ll+("\n")
            
            
        self.ML.myLog( text=u" ",mType="unifi-Report")
        self.ML.myLog( text=out,mType="unifi-Report")
        return 


######## reports end 


        
######## actions and menu set leds on /off
    ####-----------------    ---------
    def buttonConfirmAPledONControllerCALLBACKaction(self, action1=None, filter="", typeId="", devId=""):
        return self.buttonConfirmAPledONControllerCALLBACK(valuesDict=action1.props)
    ####-----------------    ---------
    def buttonConfirmAPledONControllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        self.executeCMDOnController(data={"led_enabled":True}, pageString="/set/setting/mgmt")
        return 

    ####-----------------    ---------
    def buttonConfirmAPledOFFControllerCALLBACKaction(self, action1=None, filter="", typeId="", devId=""):
        return self.buttonConfirmAPledOFFControllerCALLBACK(valuesDict=action1.props)
    ####-----------------    ---------
    def buttonConfirmAPledOFFControllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        self.executeCMDOnController(data={"led_enabled":False,"mac":False}, pageString="/set/setting/mgmt")
        return 

    ####-----------------    ---------
    def buttonConfirmAPxledONControllerCALLBACKaction(self, action1=None, filter="", typeId="", devId=""):
        return self.buttonConfirmAPxledONControllerCALLBACK(valuesDict=action1.props)
    ####-----------------    ---------
    def buttonConfirmAPxledONControllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        self.executeCMDOnController(data={"cmd":"set-locate","mac":valuesDict["selectedAPDevice"]}, pageString="/cmd/devmgr")
        return 

    ####-----------------    ---------
    def buttonConfirmAPxledOFFControllerCALLBACKaction(self, action1=None, filter="", typeId="", devId=""):
        return self.buttonConfirmAPxledOFFControllerCALLBACK(valuesDict=action1.props)
    ####-----------------    ---------
    def buttonConfirmAPxledOFFControllerCALLBACK(self, valuesDict=None, filter="", typeId="", devId=""):
        self.executeCMDOnController(data={"cmd":"unset-locate","mac":valuesDict["selectedAPDevice"]}, pageString="/cmd/devmgr")
        return 
######## set leds on /off  END 

########  check if we have new unifi system devces, if yes: litt basic variables and request a reboot 
    ####-----------------    ---------
    def checkForNewUnifiSystemDevices(self):
        try:
            if self.checkforUnifiSystemDevicesState =="": return
            self.checkforUnifiSystemDevicesState  = ""
            if self.unifiCloudKeyMode!= "ON"            : return 
            newDeviceFound =[]
        
            deviceDict =        self.executeCMDOnController(data={}, pageString="/stat/device/", jsonAction="returnData")
            if deviceDict =={}: return
            for item in deviceDict:
                ipNumber = ""
                MAC      = ""
                if "type"      not in item: continue
                uType    = item["type"]
                
                if uType == "ugw":
                    if "network_table" in item:
                        #self.ML.myLog( text=u"network_table:"+json.dumps(item["network_table"], sort_keys=True, indent=2)  ,mType="test"     )
                        for nwt in item["network_table"]:
                            if "mac" in nwt and "ip"  in nwt and "name"  in nwt and nwt["name"].lower() =="lan": 
                                ipNumber = nwt["ip"]
                                MAC      = nwt["mac"]
                                break
                else:
                    if "mac" in item and "ip" in item:
                        ipNumber = item["ip"]
                        MAC      = item["mac"]

                #self.ML.myLog( text=u"ipNumber:"+ipNumber+" MAC:"+MAC+" uType:"+uType  ,mType="test"     )
                if MAC =="" or ipNumber == "": 
                    #self.ML.myLog( text=unicode(item),mType="test"     )
                    continue
                
                found = False
                name = "--"
                for dev in indigo.devices.iter(self.pluginId):
                    if dev.deviceTypeId == u"UniFi": continue
                    if "MAClan" in dev.states and dev.states[u"MAClan"] == MAC: 
                        found = True
                        name = dev.name
                        break 
                    if "MAC" in dev.states and dev.states[u"MAC"] == MAC: 
                        found = True
                        name = dev.name
                        break 
                        ## found devce no action
                
                #self.ML.myLog( text=u"  found:"+unicode(found)+" name:"+name   ,mType="test"     )
                if not found: 

                    if uType.find("uap") >-1:
                        for i in range(len(self.ipNumbersOfAPs)):
                            if  not self.isValidIP(self.pluginPrefs[u"ip"+unicode(i)]):
                                newDeviceFound.append("uap:  , new "+ipNumber+"  existing: "+unicode(self.pluginPrefs[u"ip"+unicode(i)]) )
                                self.ipNumbersOfAPs[i]                      = ipNumber
                                self.pluginPrefs[u"ip"+unicode(i)]          = ipNumber
                                self.pluginPrefs[u"ipON"+unicode(i)]        = True
                                self.checkforUnifiSystemDevicesState        = "reboot"
                                newDeviceFound.append("uap: "+unicode(i)+", "+ipNumber)
                                break
                            else:
                                if self.pluginPrefs[u"ip"+unicode(i)  ]  == ipNumber:
                                    newDeviceFound.append("uap:  , new "+ipNumber+"  existing: "+unicode(self.pluginPrefs[u"ip"+unicode(i)]) )
                                    self.ipNumbersOfAPs[i]                  = ipNumber
                                    self.pluginPrefs[u"ipON"+unicode(i)]    = True
                                    self.checkforUnifiSystemDevicesState    = "reboot"
                                    newDeviceFound.append("uap: "+unicode(i)+", "+ipNumber)
                                    break

                    elif uType.find("usw") >-1:
                        for i in range(len(self.ipNumbersOfSWs)):
                            if  not self.isValidIP(self.pluginPrefs[u"ip"+unicode(i)] ):
                                newDeviceFound.append("usw:  , new "+ipNumber+"  existing: "+unicode(self.pluginPrefs[u"ipSW"+unicode(i)]) )
                                self.ipNumbersOfSWs[i]                      = ipNumber
                                self.pluginPrefs[u"ipSW"+unicode(i)]        = ipNumber
                                self.pluginPrefs[u"ipSWON"+unicode(i)]      = True
                                self.checkforUnifiSystemDevicesState        = "reboot"
                                break
                            else:
                                if self.pluginPrefs[u"ipSW"+unicode(i)]  == ipNumber:
                                    newDeviceFound.append("usw:  , new "+ipNumber+"  existing: "+unicode(self.pluginPrefs[u"ipSW"+unicode(i)]) )
                                    self.ipNumbersOfSWs[i]                  = ipNumber
                                    self.pluginPrefs[u"ipSWON"+unicode(i)]  = True
                                    self.checkforUnifiSystemDevicesState    = "reboot"
                                    break

                    elif uType.find("ugw") >-1:
                            #### "ip" in the dict is the ip number of the wan connection NOT the inernal IP for the gateway !!
                            #### using 2 other places instead to get the LAN IP 
                            if  not self.isValidIP(self.pluginPrefs[u"ipUGA"]):
                                newDeviceFound.append("ugw:  , new "+ipNumber+"  existing: "+unicode(self.pluginPrefs[u"ipUGA"]) )
                                self.ipnumberOfUGA                          = ipNumber
                                self.pluginPrefs[u"ipUGA"]                  = ipNumber
                                self.pluginPrefs[u"ipUGAON"]                = True
                                self.checkforUnifiSystemDevicesState        = "reboot"
                            else:
                                if self.pluginPrefs[u"ipUGA"] != ipNumber:
                                    newDeviceFound.append("ugw:  , new "+ipNumber+"  existing: "+unicode(self.pluginPrefs[u"ipUGA"]) )
                                    self.ipnumberOfUGA                      = ipNumber
                                    self.pluginPrefs[u"ipUGA"]              = ipNumber
                                    self.pluginPrefs[u"ipUGAON"]            = True
                                    self.checkforUnifiSystemDevicesState    = "reboot"
                                else:
                                    newDeviceFound.append("ugw:  , new ipUGAON was : "+unicode(self.pluginPrefs[u"ipUGAON"]) )
                                    self.pluginPrefs[u"ipUGAON"]            = True
                                    self.checkforUnifiSystemDevicesState    = "reboot"

            if self.checkforUnifiSystemDevicesState =="reboot":
                try:
                    self.pluginPrefs[u"createUnifiDevicesCounter"] = int(self.pluginPrefs[u"createUnifiDevicesCounter"] ) +1
                    if int(self.pluginPrefs[u"createUnifiDevicesCounter"] ) > 1: # allow only 1 unsucessful try, then wait 10 minutes
                        self.checkforUnifiSystemDevicesState           = ""
                    else:
                        self.ML.myLog( text=u" reboot required due to new UNIFI system device found:"+unicode(newDeviceFound),mType="Connection")
                except:
                        self.checkforUnifiSystemDevicesState           = ""
            try:    indigo.server.savePluginPrefs()
            except: pass

            if self.checkforUnifiSystemDevicesState =="":
                self.pluginPrefs[u"createUnifiDevicesCounter"] = 0

        except  Exception, e:
            if len(unicode(e)) > 5:
                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

        return



    ####-----------------    ---------
    def executeCMDOnController(self, data={},pageString="",jsonAction="",startText=""):

        try:    
            if not self.isValidIP(self.unifiCloudKeyIP): return {}
            if self.unifiCloudKeyMode.find("ON")   ==-1: return {}
        
            if self.unfiCurl =="curl":
                cmdL  = "/usr/bin/curl --insecure -c /tmp/cookie   --data '"+json.dumps({"username":self.unifiCONTROLLERUserID,"password":self.unifiCONTROLLERPassWd})+"' https://"+self.unifiCloudKeyIP+":"+self.unifiCloudKeyPort+"/api/login"
                if data =={}: dataDict = ""
                else:         dataDict = "--data '"+json.dumps(data)+"'"
                cmdR  = "/usr/bin/curl --insecure -b /tmp/cookie "  +dataDict+                                                                     " https://"+self.unifiCloudKeyIP+":"+self.unifiCloudKeyPort+self.unifiApiWebPage+self.unifiCloudKeySiteName+"/"+pageString.strip("/")

                if self.ML.decideMyLog(u"Connection"): self.ML.myLog( text=cmdL ,mType="Connection")
                try:
                    if time.time() - self.lastUnifiCookie > 300: # re-login every 5 minutes
                        ret = subprocess.Popen(cmdL, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()
                        jj = json.loads(ret[0])
                        if jj["meta"]["rc"] !="ok": 
                            self.ML.myLog( text=u"error: (wrong UID/passwd, ip number?) ...>>"+ unicode(ret[0]) +"<<\n"+unicode(ret[1]),mType="Connection")
                            return {}
                        elif self.ML.decideMyLog(u"Connection"):     self.ML.myLog( text=ret[0] ,mType="Connection")
                        self.lastUnifiCookie =time.time()

                    if self.ML.decideMyLog(u"Connection"):           self.ML.myLog( text=cmdR ,mType="Connection")
                    if startText !="":           self.ML.myLog( text=startText ,mType="Connection")
                    try:
                        ret = subprocess.Popen(cmdR, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()
                        try: 
                            jj = json.loads(ret[0])
                        except :
                            indigo.server.log("executeCMDOnController has error, no json object returned: " + unicode(ret))
                            return {}
                        if jj["meta"]["rc"] !="ok": 
                            self.ML.myLog( text=u"error: >>"+ unicode(ret[0]) +"<<\n"+unicode(ret[1]) ,mType="Connection")
                            return {}
                        elif self.ML.decideMyLog(u"Connection"):
                            self.ML.myLog( text=ret[0] ,mType="Connection")
                        if jj["meta"]["rc"] =="ok" and jsonAction=="print":
                            self.ML.myLog( text=u" info\n"+ json.dumps(jj["data"],sort_keys=True, indent=2),mType="Connection" )
                        if jj["meta"]["rc"] =="ok" and jsonAction=="returnData":
                            return jj["data"]
                        return {}
                    except  Exception, e:
                        indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
                except  Exception, e:
                    indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))


            ############# not tested, does not work on OSX  el capitan ssl lib too old  ##########
            elif self.unfiCurl =="requests":
                if self.unifiControllerSession =="" or (time.time() - self.lastUnifiCookie) > 300: 
                    self.unifiControllerSession  = requests.Session()
                    url  = "https://"+self.unifiCloudKeyIP+":"+self.unifiCloudKeyPort+"/api/login"
                    dataLogin = json.dumps({"username":self.unifiUserID,"password":self.unifiPassWd})
                    resp  = self.unifiControllerSession.post(url, data = dataLogin, verify=False)
                    if self.ML.decideMyLog(u"Connection"): self.ML.myLog( text=resp.text,mType="Connection")
                    self.lastUnifiCookie =time.time()

                
                if data =={}: dataDict = ""
                else:         dataDict = json.dumps(data)
                url = "https://"+self.unifiCloudKeyIP+":"+self.unifiCloudKeyPort+self.unifiApiWebPage+self.unifiCloudKeySiteName+"/"+pageString.strip("/")

                if self.ML.decideMyLog(u"Connection"): self.ML.myLog( text=url +"  "+ dataDict,mType="Connection")
                if startText !="":           self.ML.myLog( text=startText ,mType="Connection")
                try:
                        resp = self.unifiControllerSession.post(url,data = dataDict)
                        jj = json.loads(resp.text)
                        if jj["meta"]["rc"] !="ok" :
                           self.ML.myLog( text=u"error:>> "+ unicode(resp) ,mType="Reconnect")
                        if self.ML.decideMyLog(u"Connection"):  self.ML.myLog( text=resp.text ,mType="Reconnect")
                        if jj["meta"]["rc"] =="ok" and jsonAction=="print":
                            self.ML.myLog( text=u" info\n"+ json.dumps(jj["data"],sort_keys=True, indent=2),mType="Connection" )
                        elif jj["meta"]["rc"] =="ok" and jsonAction=="returnData":
                            return jj["data"]
                        return {}
                except  Exception, e:
                    indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))


        except  Exception, e:
            indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        return {}
   

    ####-----------------  add devices to groups  menu   ---------
    def buttonConfirmAddDevGroupCALLBACK(self, valuesDict=None, typeId="", devId=0):
        try:
            newGroup =  valuesDict["addRemoveGroupsWhichGroup"]
            devtypes =  valuesDict["addRemoveGroupsWhichDevice"]
            types    =""; lanWifi="" 
            if   devtypes == "system":   types =["gateway","DHCP","SWITCH","Device-AP","Device-SW-8","Device-SW-10","Device-SW-18" ,"Device-SW-26","Device-SW-52"]  
            elif devtypes == "neighbor": types =["neighbor"]  
            elif devtypes == "LAN":      types =["UniFi"] ; lanWifi ="LAN"
            elif devtypes == "wifi":     types =["UniFi"] ; lanWifi ="wifi" 
            for dev in indigo.devices.iter(self.pluginId):
                if dev.deviceTypeId not in types: continue
                if lanWifi == "wifi" and "AP" in dev.states:
                    if ( dev.states["AP"] =="" or 
                         dev.states["signalWiFi"]     =="" ): continue
                if lanWifi == "LAN" and "AP" in dev.states:
                    if not  ( dev.states["AP"] =="" or 
                              dev.states["signalWiFi"]     =="" ): continue
                props = dev.pluginProps
                updateProps = False
                if newGroup not in props or unicode(props[newGroup]).lower() !="true":
                    props[newGroup] = True
                    updateProps  = True
                groupMember=""
                for group in _GlobalConst_groupList:
                    if group in props and unicode(props[group]).lower() =="true" :  
                        groupMember+=group+u","
                if updateProps: dev.replacePluginPropsOnServer(props)
                if dev.states["groupMember"] != groupMember: 
                    dd = indigo.devices[dev.id]
                    dd.updateStateOnServer("groupMember",groupMember)
                 
            self.statusChanged = 2
                    
        except  Exception, e:
            if len(unicode(e)) > 5:
                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        return valuesDict


    ####-----------------  remove devices to groups  menu   ---------
    def buttonConfirmRemDevGroupCALLBACK(self, valuesDict=None, typeId="", devId=0):
        try:
            self.ML.myLog( text=u" valuesDict "+unicode(_GlobalConst_groupList)+"  "+ unicode(valuesDict)) 
            newGroup =  valuesDict["addRemoveGroupsWhichGroup"]
            devtypes =  valuesDict["addRemoveGroupsWhichDevice"]
            types    =""; lanWifi="" 
            if   devtypes == "system":   types =["gateway","DHCP","SWITCH","Device-AP","Device-SW-8","Device-SW-10","Device-SW-18" ,"Device-SW-26","Device-SW-52"]  
            elif devtypes == "neighbor": types =["neighbor"]  
            elif devtypes == "LAN":      types =["UniFi"] ; lanWifi ="LAN"
            elif devtypes == "wifi":     types =["UniFi"] ; lanWifi ="wifi" 
            for dev in indigo.devices.iter(self.pluginId):
                if dev.deviceTypeId not in types: continue
                if lanWifi == "wifi" and "AP" in dev.states:
                    if ( dev.states["AP"] =="" or 
                         dev.states["signalWiFi"]     =="" ): continue
                if lanWifi == "LAN" and "AP" in dev.states:
                    if not  ( dev.states["AP"] =="" or 
                              dev.states["signalWiFi"]     =="" ): continue

                props = dev.pluginProps
                updateProps = False
                if newGroup in props and unicode(props[newGroup]).lower() != "false":
                    props[newGroup] = False
                    updateProps  = True
                groupMember=""
                for group in _GlobalConst_groupList:
                    if group in props and unicode(props[group]).lower() == "true":  
                        groupMember+=group+u","
                if updateProps: dev.replacePluginPropsOnServer(props)
                if dev.states["groupMember"] != groupMember: 
                    dd = indigo.devices[dev.id]
                    dd.updateStateOnServer("groupMember",groupMember)

            self.statusChanged = 2
        except  Exception, e:
            if len(unicode(e)) > 5:
                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        return valuesDict

    ####-----------------      ---------
    def setGroupStatus(self, init=False):
        self.statusChanged = 0
        try:

            if init:
               try:         indigo.variable.create("Unifi_With_Status_Change")
               except:      pass

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
                    self.groupStatusListALL["nHome"]     +=1
                else:                            
                    self.groupStatusListALL["nAway"]     +=1

                if dev.states["groupMember"] == "": continue
                if not dev.enabled:  continue
                okList.append(unicode(dev.id))
                props= dev.pluginProps
                for group in _GlobalConst_groupList:
                    if group in dev.states["groupMember"]:
                        self.groupStatusList[group]["members"][unicode(dev.id)] = True
                        if dev.states["status"]=="up":
                            if self.groupStatusList[group]["oneHome"] =="0":
                                triggerGroup[group]["oneHome"] = True
                                self.groupStatusList[group]["oneHome"]   = "1"
                            self.groupStatusList[group]["nHome"]     +=1
                        else:
                            if self.groupStatusList[group]["oneAway"] =="0":
                                triggerGroup[group]["oneAway"] = True
                            self.groupStatusList[group]["oneAway"]   = "1"
                            self.groupStatusList[group]["nAway"]     +=1
 
 


            if init: # dont need to do this every time, only if device has changed 
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
                    self.groupStatusList[group]["allAway"]   = "1"
                    self.groupStatusList[group]["oneHome"]   = "0"
                else:        
                    self.groupStatusList[group]["allAway"]   = "0"
                    
                if self.groupStatusList[group]["nHome"] == len(self.groupStatusList[group]["members"]):
                    if self.groupStatusList[group]["allHome"] =="0":
                        triggerGroup[group]["allHome"] = True
                    self.groupStatusList[group]["allHome"]   = "1"
                    self.groupStatusList[group]["oneAway"]   = "0"
                else:        
                    self.groupStatusList[group]["allHome"]   = "0"


            # now extra variables
            for group in  _GlobalConst_groupList:
                for tType in ["Home","Away"]:
                    varName="Unifi_Count_"+group+"_"+tType
                    gName="n"+tType
                    try:
                        var = indigo.variables[varName]
                    except:
                        indigo.variable.create(varName)
                        var = indigo.variables[varName]
                    
                    if var.value !=  unicode(self.groupStatusList[group][gName]):   
                        indigo.variable.updateValue(varName,unicode(self.groupStatusList[group][gName]))


            
            for tType in ["Home","Away"]:
                varName="Unifi_Count_ALL_"+tType
                gName="n"+tType
                try:
                    var = indigo.variables[varName]
                except:
                    indigo.variable.create(varName)
                    var = indigo.variables[varName]
                
                if var.value !=  unicode(self.groupStatusListALL[gName]):   
                    indigo.variable.updateValue(varName,unicode(self.groupStatusListALL[gName]))


            #for group in  self.groupStatusList:
            #    self.ML.myLog( text=group+"  "+ unicode( self.groupStatusList[group]))
            #indigo.server.log("trigger list "+ unicode( self.triggerList))


            if  init != "init" and len(self.triggerList) > 0:
                for group in triggerGroup:
                    for tType in triggerGroup[group]:
                        #indigo.server.log(group+"-"+tType+"  trigger:"+unicode(triggerGroup[group][tType]))
                        if triggerGroup[group][tType]:
                            self.triggerEvent(group+"_"+tType)
                
        except  Exception, e:
            self.ML.myLog( text=u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

        return

######################################################################################
    # Indigo Trigger Start/Stop
######################################################################################

    ####-----------------    ---------
    def triggerStartProcessing(self, trigger):
#		self.ML.myLog( text=u"BeaconData",u"<<-- entering triggerStartProcessing: %s (%d)" % (trigger.name, trigger.id) )iDeviceHomeDistance
        self.triggerList.append(trigger.id)
#		self.ML.myLog( text=u"BeaconData",u"exiting triggerStartProcessing -->>")

    ####-----------------    ---------
    def triggerStopProcessing(self, trigger):
#		self.ML.myLog( text=u"BeaconData",u"<<-- entering triggerStopProcessing: %s (%d)" % (trigger.name, trigger.id))
        if trigger.id in self.triggerList:
#			self.ML.myLog( text=u"BeaconData",u"TRIGGER FOUND")
            self.triggerList.remove(trigger.id)
#		self.ML.myLog( text=u"BeaconData", u"exiting triggerStopProcessing -->>")

    #def triggerUpdated(self, origDev, newDev):
    #	self.logger.log(4, u"<<-- entering triggerUpdated: %s" % origDev.name)
    #	self.triggerStopProcessing(origDev)
    #	self.triggerStartProcessing(newDev)


######################################################################################
    # Indigo Trigger Firing
######################################################################################

    ####-----------------    ---------
    def triggerEvent(self, eventId):
        #self.ML.myLog( text=u"<<-- entering triggerEvent: %s " % eventId)
        for trigId in self.triggerList:
            trigger = indigo.triggers[trigId]
            #self.ML.myLog( text=u"<<-- trigger "+ unicode(trigger)+"  eventId:"+ eventId)
            if trigger.pluginTypeId == eventId:
                #self.ML.myLog( text=u"<<-- trigger exec")
                indigo.trigger.execute(trigger)
        return




    ####-----------------setup empty dicts for pointers  type, mac --> indigop and indigo --> mac,  type ---------
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
                    if u"useAgeforStatusDHCP" in props and  props[u"useAgeforStatusDHCP"] != "" and props[u"useAgeforStatusDHCP"] != u"-1":
                        upDown = u"DHCP" + "-age:" + props[u"useAgeforStatusDHCP"]
                    else:
                        upDown = u"DHCP" 

                elif props[u"useWhatForStatus"] == u"OptDhcpSwitch":
                    upDown ="OPT: "
                    if u"useAgeforStatusDHCP" in props and  props[u"useAgeforStatusDHCP"] != "" and props[u"useAgeforStatusDHCP"] != u"-1":
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
                self.addToStatesUpdateList(unicode(dev.id),u"upDownSetting", upDown)

            if u"expirationTime" not in props:
                props[u"expirationTime"] = self.expirationTime
                update=True

            if u"AP" in dev.states:
                if dev.states[u"AP"].find("-") ==-1 :
                    newAP= dev.states[u"AP"]+"-"
                    dev.updateStateOnServer(u"AP",newAP)

                
        except  Exception, e:
            if len(unicode(e)) > 5:
                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        if update:
            dev.replacePluginPropsOnServer(props)
        return 


    ####-----------------setup empty dicts for pointers  type, mac --> indigop and indigo --> mac,  type ---------
    def setupStructures(self, xType, dev, MAC): 
        try:
            if xType == u"UN" and MAC in self.MACignorelist: 
                if MAC in self.MAC2INDIGO[xType]:
                    del self.MAC2INDIGO[xType][MAC]
                return 
            devIds = unicode(dev.id)
            if devIds not in self.xTypeMac:
                self.xTypeMac[devIds]={"xType":"", "MAC":""}
            self.xTypeMac[devIds]["xType"] = xType
            self.xTypeMac[devIds][u"MAC"]   = MAC

            if xType not in self.MAC2INDIGO:
                self.MAC2INDIGO[xType]={}

            if MAC not in self.MAC2INDIGO[xType]:
               self.MAC2INDIGO[xType][MAC] = {}

            self.MAC2INDIGO[xType][MAC]["devId"] = dev.id
            if u"ipNumber" not in self.MAC2INDIGO[xType][MAC]:
                if u"ipNumber" in dev.states:
                    self.MAC2INDIGO[xType][MAC][u"ipNumber"] = dev.states[u"ipNumber"]

            try:    self.MAC2INDIGO[xType][MAC][u"lastUp"] == float(self.MAC2INDIGO[xType][MAC][u"lastUp"])
            except: self.MAC2INDIGO[xType][MAC][u"lastUp"] =0.
                
                
        except  Exception, e:
            indigo.server.log(  u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e) )
            indigo.server.log( unicode(xType)+"  "+devIds+"  "+unicode(MAC)+"  "+unicode(self.MAC2INDIGO))
            time.sleep(300)

        if xType ==u"UN":
                self.MAC2INDIGO[xType][MAC][u"AP"]             = dev.states[u"AP"].split("-")[0]

                for item in [u"inListWiFi",u"inListDHCP",]:
                    if item not in self.MAC2INDIGO[xType][MAC]:
                            self.MAC2INDIGO[xType][MAC][item] = False
                for item in [u"GHz",u"idleTimeWiFi",u"upTimeWifi",u"upTimeDHCP"]:
                    if item not in self.MAC2INDIGO[xType][MAC]:
                            self.MAC2INDIGO[xType][MAC][item] = ""

                for ii in range(_GlobalConst_numberOfSW):
                    for item in [u"inListSWITCH_"]:
                        #indigo.server.log("setupStructures testing inListSWITCH_:"+str(ii)) 
                        if item+unicode(ii) not in self.MAC2INDIGO[xType][MAC]:
                            self.MAC2INDIGO[xType][MAC][item+unicode(ii)] = -1
                            indigo.server.log("setupStructures adding inListSWITCH_:"+str(ii)) 
                    for item in [u"ageSWITCH_",u"uptimeSWITCH_"]:
                        if item+unicode(ii) not in self.MAC2INDIGO[xType][MAC]:
                            self.MAC2INDIGO[xType][MAC][item+unicode(ii)] = ""
                for nnn in self.MAC2INDIGO["UN"]:
                    if nnn.find("inListSWITCH_") >-1:
                        indigo.server.log("setupStructures MAC2INDIGO:"+unicode(self.MAC2INDIGO["UN"][nnn]))


        if xType ==u"SW":
            if "ports" not in self.MAC2INDIGO[xType][MAC]:
                self.MAC2INDIGO[xType][MAC][u"ports"] = {}
            if u"uptime" not in self.MAC2INDIGO[xType][MAC]:
                self.MAC2INDIGO[xType][MAC][u"uptime"] = ""

        elif xType ==u"AP":
            pass
            
        elif xType ==u"GW":
            pass
            
        elif xType ==u"NB":
            if u"age" not in self.MAC2INDIGO[xType][MAC]:
                self.MAC2INDIGO[xType][MAC][u"age"] = ""



    ###########################    MAIN LOOP  ############################
    ####-----------------init  main loop ---------
    def runConcurrentThread(self):
        nowDT = datetime.datetime.now()
        self.lastMinute     = nowDT.minute
        self.lastHour       = nowDT.hour
        self.logQueue       = Queue.Queue()
        self.logQueueDict   = Queue.Queue()
        self.apDict         = {}
        self.countLoop      = 0
        self.upDownTimers   = {}
        self.xTypeMac       = {}

        indigo.server.log(u" start  runConcurrentThread, initializing variables ..")

######## ths for fixing the change from mac to MAC in states
        self.MacToNamesOK = True
        if self.enableMACtoVENDORlookup  != "0": 
            self.ML.myLog( text=u"..getting missing vendor names for MAC #")
        self.MAC2INDIGO = {}
        self.readMACdata()
        delDEV = {}
        for dev in indigo.devices.iter(self.pluginId):
            if dev.deviceTypeId == u"client": continue
            if u"status" not in dev.states:
                self.ML.myLog( text=dev.name + u" has no status")
                continue
          
            props= dev.pluginProps
            goodDevice = True
            devId = unicode(dev.id)
            
            if u"MAC" in dev.states:
                MAC = dev.states[u"MAC"]
                if dev.states[u"MAC"] == "":
                    if dev.address != "":
                        try:
                            self.addToStatesUpdateList(unicode(dev.id),u"MAC", dev.address)
                            MAC = dev.address
                        except:
                            goodDevice = False
                            self.ML.myLog( text=dev.name + u" no MAC # deleting")
                            delDEV[devId]=True
                            continue
                if dev.address != MAC:
                    props["address"] = MAC
                    dev.replacePluginPropsOnServer(props)
            
            if self.MacToNamesOK and u"vendor" in dev.states:
                if (dev.states[u"vendor"] == "" or dev.states[u"vendor"].find("<html>") >-1 ) and goodDevice:
                    vendor = self.getVendortName(MAC)
                    if vendor != "":
                        self.addToStatesUpdateList(unicode(dev.id),u"vendor", vendor)
                    if  dev.states[u"vendor"].find("<html>") >-1   and   vendor =="" :
                        self.addToStatesUpdateList(unicode(dev.id),u"vendor", "")


            if dev.deviceTypeId == u"UniFi":
                #self.ML.myLog( text=u" adding to MAC2INDIGO " + MAC)
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
                self.addToStatesUpdateList(unicode(dev.id),u"created", nowDT.strftime(u"%Y-%m-%d %H:%M:%S"))


            self.setStateupDown(dev)

            self.executeUpdateStatesList()

        for devid in delDEV:
             self.ML.myLog( text=" deleting , bad mac "+ devid )
             indigo.device.delete[int(devid)]



        ## remove old non exiting MAC / indigo devices 
        for xType in self.MAC2INDIGO:
            if "" in self.MAC2INDIGO[xType]:
                del self.MAC2INDIGO[xType][""]
            delMAC = {}
            for MAC in self.MAC2INDIGO[xType]:
                if len(MAC) < 16: 
                    delMAC[MAC] = True
                    continue
                try: indigo.devices[self.MAC2INDIGO[xType][MAC][u"devId"]]
                except  Exception, e:
                    self.ML.myLog( text= "removing indigo id: "+ unicode(self.MAC2INDIGO[xType][MAC][u"devId"])+"  from internal list" )
                    time.sleep(1)
                    delMAC[MAC] = True
            for MAC in delMAC:
                del self.MAC2INDIGO[xType][MAC]
        delMAC = {}

        delDEV = {}
        for devId  in self.xTypeMac:
            try:     dev = indigo.devices[int(devId)]
            except  Exception, e:
                self.ML.myLog( text=u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e) )
                if unicode(e).find("timeout") >-1:
                    self.sleep(20)
                    return 
                delDEV[devId]=True
            MAC =  self.xTypeMac[devId]["MAC"]
            if self.xTypeMac[devId]["xType"]=="SW":
                ipN = dev.states["ipNumber"]
                sw  = dev.states["switchNo"]
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
                sw  = dev.states["apNo"]
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

                

        for devId in delDEV:
            del self.xTypeMac[devId]
        delDEV = {}

        self.saveMACdata()

        self.lastSecCheck   = time.time()

        self.readupDownTimers()
        self.saveupDownTimers()

        ##start accepting staus = DOWN in 30secs
        self.pluginStartTime = time.time() +30

        self.pluginState   = "run"

        ###########  set up threads  ########
        try:
            self.trAPLog  = {}
            self.trAPDict = {}
            nsleep= 4
            if self.NumberOFActiveAP > 0:
                self.ML.myLog( text=u"..starting threads for %d APs %d sec apart (MSG-log and db-DICT)"  %(self.NumberOFActiveAP,nsleep) )
                for ll in range(_GlobalConst_numberOfAP):
                    if self.APsEnabled[ll]:
                        ipn = self.ipNumbersOfAPs[ll]
                        if self.ML.decideMyLog(u"Logic"): self.ML.myLog( text=u"AP Thread # " + unicode(ll)+ "  "+ ipn ,mType=u"START")
                        self.trAPLog[unicode(ll)] = threading.Thread(name=u'self.getMessages', target=self.getMessages, args=(ipn,ll,u"APtail",float(self.readDictEverySeconds[u"AP"])*2,))
                        self.trAPLog[unicode(ll)].start()
                        self.sleep(0.2)
                        self.trAPDict[unicode(ll)] = threading.Thread(name=u'self.getMessages', target=self.getMessages, args=(ipn,ll,u"APdict",float(self.readDictEverySeconds[u"AP"])*2,))
                        self.trAPDict[unicode(ll)].start()
                        self.sleep(nsleep)


        except  Exception, e:
            self.ML.myLog( text=u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e) )
            self.stop = copy.copy(self.ipNumbersOfAPs)
            self.quitNow = u"stop"
            return



        if self.UGAEnabled:
            self.ML.myLog( text=u"..starting threads for GW (MSG-log and db-DICT)")
            self.trGWLog  = threading.Thread(name=u'self.getMessages', target=self.getMessages, args=(self.ipnumberOfUGA,u"GW",u"GWtail",float(self.readDictEverySeconds[u"GW"])*2,))
            self.trGWLog.start()
            self.sleep(0.2)
            self.trGWDict = threading.Thread(name=u'self.getMessages', target=self.getMessages, args=(self.ipnumberOfUGA,u"GW",u"GWdict",float(self.readDictEverySeconds[u"GW"])*2,))
            self.trGWDict.start()




        try:
            self.trSWLog = {}
            self.trSWDict = {}
            if self.NumberOFActiveSW > 0:
                nsleep = 15 - self.NumberOFActiveSW
                minCheck = float(self.readDictEverySeconds[u"SW"])*2.
                if self.NumberOFActiveSW > 1:
                    minCheck = 2.* float(self.readDictEverySeconds[u"SW"]) / self.NumberOFActiveSW
                else:
                    minCheck = 2.* float(self.readDictEverySeconds[u"SW"])
                self.ML.myLog( text=u"..starting threads for %d SWs %d sec apart (db-DICT only)"  %(self.NumberOFActiveSW,nsleep) )
                for ll in range(_GlobalConst_numberOfSW):
                    if self.SWsEnabled[ll]:
                        ipn = self.ipNumbersOfSWs[ll]
                        if self.ML.decideMyLog(u"Logic"): self.ML.myLog( text=u"SW Thread tr # " + unicode(ll) + "  " + ipn, mType=u"START")
     #                   self.trSWLog[unicode(ll)] = threading.Thread(name='self.getMessages', target=self.getMessages, args=(ipn, ll, "SWtail",float(self.readDictEverySeconds[u"SW"]*2,))
     #                   self.trSWLog[unicode(ll)].start()
                        self.trSWDict[unicode(ll)] = threading.Thread(name=u'self.getMessages', target=self.getMessages, args=(ipn, ll, u"SWdict",minCheck,))
                        self.trSWDict[unicode(ll)].start()
                        if self.NumberOFActiveSW > 1: self.sleep(nsleep)


        except  Exception, e:
            self.ML.myLog( text=u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
            self.stop = copy.copy(self.ipNumbersOfSWs)
            self.quitNow = u"stop"
            
     

        #self.sendUpdatetoFingscanNOW(force=True)

    ################   ------- here the loop starts    --------------
        indigo.server.log( u"initialized")
        try:    indigo.server.savePluginPrefs()
        except: pass
        self.sleep(1)
        lastHourCheck       = datetime.datetime.now().hour
        lastMinuteCheck     = datetime.datetime.now().minute
        lastMinute10Check   = datetime.datetime.now().minute/10
        self.pluginStartTime = time.time()
        try:
            self.quitNow = ""
            while self.quitNow == "":
                self.sleep(self.loopSleep)
                
                if self.checkforUnifiSystemDevicesState == "validateConfig" or \
                  (self.checkforUnifiSystemDevicesState == "start"  and (time.time() -self.pluginStartTime) > 30):
                    self.checkForNewUnifiSystemDevices()
                    if self.checkforUnifiSystemDevicesState == "reboot":
                        self.quitNow ="new devices"
                        self.checkforUnifiSystemDevicesState =""
                        break

                self.saveDataStats()
                self.saveMACdata()
                part = u"main"+unicode(random.random()); self.blockAccess.append(part)
                for ii in range(90):
                    if len(self.blockAccess) == 0 or self.blockAccess[0] == part: break # my turn?
                    self.sleep(0.1)   
                if ii >= 89: self.blockAccess = [] # for safety if too long reset list

                ## check for expirations etc
              
                self.checkOnChanges()
                self.executeUpdateStatesList()
              
                self.periodCheck()
                self.executeUpdateStatesList()
                self.sendUpdatetoFingscanNOW()
                if   self.statusChanged ==1:  self.setGroupStatus()
                elif self.statusChanged ==2:  self.setGroupStatus(init=True)
                VS.versionCheck(self.pluginId,self.pluginVersion,indigo,13,45,printToLog="log")

              
                if len(self.devNeedsUpdate) > 0:
                    for devId in self.devNeedsUpdate:
                        try:
                            ##indigo.server.log(" updating devId:"+ unicode(devId))
                            dev = indigo.devices[devId]
                            self.setStateupDown(dev)
                        except:
                            pass
                    self.devNeedsUpdate = []
                    self.saveupDownTimers()
                    self.setGroupStatus(init=True)

                self.executeUpdateStatesList()
                
                if len(self.blockAccess)>0:  del self.blockAccess[0]
                self.countLoop += 1
            
                if lastMinuteCheck != datetime.datetime.now().minute: 
                    lastMinuteCheck = datetime.datetime.now().minute
                    self.statusChanged = max(1,self.statusChanged)
                    
                    if lastMinute10Check != (datetime.datetime.now().minute)/10: 
                        lastMinute10Check = datetime.datetime.now().minute/10
                        self.checkforUnifiSystemDevicesState = "10minutes"
                        self.checkForNewUnifiSystemDevices()
                        if self.checkforUnifiSystemDevicesState == "reboot":
                            self.quitNow ="new devices"
                            self.checkforUnifiSystemDevicesState =""
                            break

                    
                        if lastHourCheck != datetime.datetime.now().hour:
                            lastHourCheck = datetime.datetime.now().hour

                            self.saveupDownTimers()
                            if lastHourCheck ==1: # recycle at midnight 
                                try:             
                                    indigo.variable.delete("Unifi_With_Status_Change")
                                    try:         indigo.variable.create("Unifi_With_Status_Change")
                                    except:      pass
                                except:          pass



        except  Exception, e:
                if len(unicode(e)) > 5:
                    indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        ################   ------- here the loop ends    --------------

        self.pluginState   = "stop"



        if self.quitNow == "": self.quitNow = u" restart / self.stop requested "
        if self.quitNow == u"config changed":
            self.resetDataStats()

        indigo.server.log( u" stopping plugin due to:  ::::: " + unicode(self.quitNow) + u" :::::")
        try:
            for ll in range(len(self.SWsEnabled)):
                self.trSWLog[unicode(ll)].join()
                self.trSWDict[unicode(ll)].join()
            for ll in range(len(self.APsEnabled)):
                self.trAPLog[unicode(ll)].join()
                self.trAPDict[unicode(ll)].join()
            self.trGWLog[unicode(ll)].join()
            self.trGWDict[unicode(ll)].join()
            

        except:
            pass

        ## kill all expect "uniFi" programs 
        self.killIfRunning("", "")

        self.saveupDownTimers()
    
        self.sleep(1)
        serverPlugin = indigo.server.getPlugin(self.pluginId)
        serverPlugin.restart(waitUntilDone=False)

        return


    ####-----------------    ---------
    def saveupDownTimers(self):
        try:
            f = open(self.unifiPath+"upDownTimers","w")
            f.write(json.dumps(self.upDownTimers))
            f.close()
        except  Exception, e:
            indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

    ####-----------------    ---------
    def readupDownTimers(self):
        try:
            f = open(self.unifiPath+"upDownTimers","r")
            self.upDownTimers = json.loads(f.read())
            f.close()
        except:
            self.upDownTimers ={}
            try:
                f.close()
            except:
                pass

    ####-----------------    ---------
    def checkOnChanges(self,):
        xType   = u"UN"
        try:
            if self.upDownTimers =={}: return
            deldev={}

            for devid in self.upDownTimers:
                try:
                    dev= indigo.devices[int(devid)]
                except  Exception, e:
                    if unicode(e).find("timeout waiting") > -1:
                        self.ML.myLog( text=u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
                        self.ML.myLog( text=u"communication to indigo is interrupted")
                        return
                    if unicode(e).find("not found in database") >-1:    
                        deldev[devid] =1
                        continue
                    indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
                    return
                    
                props=dev.pluginProps
                expT =self.getexpT(props)
                dt  = time.time() - expT
                dtDOWN = time.time() -  self.upDownTimers[devid][u"down"]
                dtUP   = time.time() -  self.upDownTimers[devid][u"up"]
                
                if dev.states[u"status"] !="up": newStat = u"down"
                else:                            newStat = u"up"
                if self.upDownTimers[devid][u"down"] > 10.:
                    if dtDOWN < 2: continue # ignore and up-> in the last 2 secs to avoid constant up-down-up
                    if self.doubleCheckWithPing(newStat,dev.states["ipNumber"], props,dev.states[u"MAC"],"Logic", "checkOnChanges", "CHAN-WiF-Pg","UN") ==0:
                            deldev[devid] = 1
                            continue
                    if u"useWhatForStatusWiFi"  in props and props[u"useWhatForStatusWiFi"] in [u"FastDown",u"Optimized"]: 
                        if dtDOWN > 10. and dev.states[u"status"] == u"up":
                            self.setImageAndStatus(dev, "down", ts=dt - 0.1, fing=True, level=1, text1= dev.name.ljust(30) + u" status was up   changed period WiFi, expT= %4.1f"%expT+"  dt= %4.1f"%dt, iType=u"CHAN-WiFi",reason="FastDown")
                            self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time() - expT
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

        except  Exception, e:
            indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

        return 


    ####-----------------    ---------
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

    ####-----------------    ---------
    def periodCheck(self,):
        try:

            if  self.countLoop < 10: return

            changed = False

            for dev in indigo.devices.iter(self.pluginId):

                try:

                    props = dev.pluginProps
                    devid = unicode(dev.id)


                    MAC     = dev.states[u"MAC"]
                    if dev.deviceTypeId == u"UniFi" and self.testIgnoreMAC(MAC,"priodCheck") : continue
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
                    xType   = self.xTypeMac[devid]["xType"]

                    expT= self.getexpT(props)
                    try:
                        lastUpTT   = self.MAC2INDIGO[xType][MAC][u"lastUp"]
                    except:
                        lastUpTT = time.time()

                    if dev.deviceTypeId == u"UniFi":

                        if u"useWhatForStatus" in props:
                            if props[u"useWhatForStatus"] == "WiFi":
                                suffixN = "WiFi"
                                if u"useWhatForStatusWiFi" not in props or  (u"useWhatForStatusWiFi" in props and props[u"useWhatForStatusWiFi"] != u"FastDown"):

                                    dt = time.time() - lastUpTT
                                    if (devid in self.upDownTimers  and time.time() -  self.upDownTimers[devid][u"down"] > expT ) or (dt > 1 * expT) :
                                        if    dt <  1 * expT: status = u"up"
                                        elif  dt <  2 * expT: status = u"down"
                                        else :                status = u"expired"
                                        if not self.expTimerSettingsOK("AP",MAC, dev): continue 

                                        if status != "up":
                                            if dev.states["status"] == u"up":
                                                if self.doubleCheckWithPing(status,dev.states["ipNumber"], props,dev.states[u"MAC"],"Logic", "Period check-WiFi", "chk-Time",xType) ==0:
                                                    status  = u"up" 
                                                    self.setImageAndStatus(dev, "up", oldStatus=dev.states[u"status"],ts=time.time(), fing=False, level=1, text1= dev.name.ljust(30) + u" status "  + status.ljust(10) +";  set to UP,  reset by ping ", iType=u"PER-AP-Wi-0",reason=u"Period Check Wifi "+status)
                                                    changed = True
                                                    continue
                                                else:
                                                    self.setImageAndStatus(dev, status, oldStatus=dev.states[u"status"],ts=time.time(), fing=True, level=1, text1= dev.name.ljust(30) + u" status "  + status.ljust(10) +" changed period WiFi, expT= %4.1f"%expT+"  dt= %4.1f"%dt, iType=u"PER-AP-Wi-1",reason=u"Period Check Wifi "+status)
                                                    changed = True
                                                    continue

                                            if dev.states["status"] == u"down" and status !="down": # to expired 
                                                    self.setImageAndStatus(dev, status, oldStatus=dev.states[u"status"],ts=time.time(), fing=True, level=1, text1= dev.name.ljust(30) + u" status "  + status.ljust(10) +" changed period WiFi, expT= %4.1f"%expT+"  dt= %4.1f"%dt, iType=u"PER-AP-Wi-1",reason=u"Period Check Wifi "+status)
                                                    changed = True
                                                    continue

                                        else: 
                                            if dev.states[u"status"] != status:
                                                if self.doubleCheckWithPing(status,dev.states["ipNumber"], props,dev.states[u"MAC"],"Logic", "Period check-WiFi", "chk-Time",xType) !=0:
                                                    pass
                                                else:
                                                    changed = True
                                                    status ="up"
                                                    self.setImageAndStatus(dev, status, oldStatus=dev.states[u"status"],ts=time.time(), fing=True, level=1, text1= dev.name.ljust(30) + u" status "  + status.ljust(10) +" changed period WiFi, expT= %4.1f"%expT+"  dt= %4.1f"%dt, iType=u"PER-AP-Wi-1",reason=u"Period Check Wifi "+status)
                                                continue


                                elif  (u"useWhatForStatusWiFi" in props and props[u"useWhatForStatusWiFi"] == u"FastDown") and dev.states[u"status"] =="down" and (time.time() - lastUpTT > 2 * expT):
                                        if not self.expTimerSettingsOK("AP",MAC, dev): continue 
                                        status = u"expired"
                                        changed = True
                                        #indigo.server.log(u" period "+ dev.name+u" changed: old status: "+dev.states[u"status"]+u"; new  "+status)
                                        self.setImageAndStatus(dev, status, oldStatus=dev.states[u"status"],ts=time.time(), fing=True, level=1, text1= dev.name.ljust(30) + u" status "  + status.ljust(10) +" changed period WiFi, expT= %4.1f"%expT+"  dt= %4.1f"%dt, iType=u"PER-AP-Wi-2",reason=u"Period Check Wifi "+status)
 

                            elif props[u"useWhatForStatus"] ==u"SWITCH":
                                suffixN = u"SWITCH"
                                dt = time.time() - lastUpTT
                                if   dt <  1 * expT:  status = u"up"
                                elif dt <  2 * expT:  status = u"down"
                                else :                status = u"expired"
                                if not self.expTimerSettingsOK("SW",MAC, dev): continue 
                                if dev.states[u"status"] != status:
                                    if status =="down" and self.doubleCheckWithPing(status,dev.states["ipNumber"], props,dev.states[u"MAC"],"Logic", "Period check-SWITCH", "chk-Time",xType) ==0:
                                            status = u"up"
                                    if dev.states[u"status"] != status:
                                        changed = True
                                        self.setImageAndStatus(dev, status,oldStatus=dev.states[u"status"], ts=time.time(), fing=True, level=1, text1= dev.name.ljust(30) + u" status " + unicode(status).ljust(10) + " changed period SWITCH ,  expT= %4.1f"%expT+"  dt= %4.1f"%dt, iType=u"PER-SW-0",reason=u"Period Check SWITCH "+status)
     


                            elif props[u"useWhatForStatus"] == u"DHCP":
                                suffixN = u"DHCP"
                                dt = time.time() - lastUpTT
                                if   dt <  1 * expT:  status = u"up"
                                elif dt <  2 * expT:  status = u"down"
                                else :                status = u"expired"
                                if not self.expTimerSettingsOK("GW",MAC, dev): continue 
                                if dev.states[u"status"] != status:
                                    if status == "down" and self.doubleCheckWithPing(status,dev.states["ipNumber"], props,dev.states[u"MAC"],"Logic", "Period check-DHCP", "chk-Time",xType) ==0:
                                        status = u"up"
                                    if dev.states[u"status"] != status:
                                        changed = True
                                        self.setImageAndStatus(dev, status,oldStatus=dev.states[u"status"], ts=time.time(), fing=True, level=1, text1= dev.name.ljust(30) + u" status " + unicode(status).ljust(10) + " changed period DHCP,  expT= %4.1f"%expT+"  dt= %4.1f"%dt, iType=u"PER-DHCP-0",reason=u"Period Check DHCP "+status)
 

                            else:
                                dt = time.time() - lastUpTT
                                if   dt <  1 * expT:  status = u"up"
                                elif dt <  2 * expT:  status = u"down"
                                else               :  status = u"expired"
                                if dev.states[u"status"] != status:
                                    if status =="down" and self.doubleCheckWithPing(status,dev.states["ipNumber"], props,dev.states[u"MAC"],"Logic", "Period check-default", "chk-Time",xType) ==0:
                                        status = u"up"
                                    if dev.states[u"status"] != status:
                                        changed = True
                                        self.setImageAndStatus(dev, status,oldStatus=dev.states[u"status"], ts=time.time(), fing=True, level=1, text1= dev.name.ljust(30) + u" status " + unicode(status).ljust(10) + " changed period regular expiration expT= %4.1f" % expT + "  dt= %4.1f" % dt+u" useWhatForStatus else "+ props[u"useWhatForStatus"], iType=u"PER-expire",reason=u"Period Check other")
                        continue
                    elif dev.deviceTypeId == u"Device-AP":
                        try:
                            ipN = dev.states[u"ipNumber"]
                            if ipN not in self.APUP:
                                continue
                                ipN = self.ipNumbersOfAPs[int(dev.states[u"apNo"])]
                                dev.updateStateOnServer(u"ipNumber", ipN )

                            dt = time.time() - self.APUP[dev.states[u"ipNumber"]]
                            if   dt <  1 * expT:  status = u"up"
                            elif dt <  2 * expT:  status = u"down"
                            else :                status = u"expired"
                            if dev.states[u"status"] != status:
                                if status =="down" and self.doubleCheckWithPing(status,dev.states["ipNumber"], props,dev.states[u"MAC"],"Logic", "Period check-dev-AP", "chk-Time",xType) ==0:
                                    status = u"up"
                                if dev.states[u"status"] != status:
                                    changed = True
                                    self.setImageAndStatus(dev,status,oldStatus=dev.states[u"status"],ts=time.time(), fing=True, level=1, text1= dev.name.ljust(30) + u" status " + status.ljust(10) + " changed period expT= %4.1f" % expT + "  dt= %4.1f" % dt, iType=u"PER-DEV-AP")
                        except  Exception, e:
                            if len(unicode(e)) > 5:
                                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
                            continue

                    elif dev.deviceTypeId.find(u"Device-SW") >-1:
                        try:
                            ipN = dev.states[u"ipNumber"]
                            if ipN not in self.SWUP:
                                ipN = self.ipNumbersOfSWs[int(dev.states[u"switchNo"])]
                                dev.updateStateOnServer(u"ipNumber", ipN )
                                
                            dt = time.time() - self.SWUP[ipN]
                            if   dt < 1 * expT: status = u"up"
                            elif dt < 2 * expT: status = u"down"
                            else:               status = u"expired"
                            if dev.states[u"status"] != status:
                                if status =="down" and self.doubleCheckWithPing(status,dev.states["ipNumber"], props,dev.states[u"MAC"],"Logic", "Period check-dev-SW", "chk-Time",xType) ==0:
                                    status = u"up"
                                if dev.states[u"status"] != status:
                                    changed = True
                                    self.setImageAndStatus(dev,status,oldStatus=dev.states[u"status"],ts=time.time(), fing=True, level=1, text1=dev.name.ljust(30) + u" status " + status.ljust(10) + " changed period expT= %4.1f" % expT + "  dt= %4.1f" % dt, iType=u"PER-DEV-SW")
                        except  Exception, e:
                            if len(unicode(e)) > 5:
                                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
                            continue


                    elif dev.deviceTypeId == u"neighbor":
                        try:
                            dt = time.time() - lastUpTT
                            if   dt < 1 * expT: status = u"up"
                            elif dt < 2 * expT: status = u"down"
                            else:               status = u"expired"
                            if dev.states[u"status"] != status:
                                    changed=True
                                    self.setImageAndStatus(dev,status,oldStatus=dev.states[u"status"],ts=time.time(), fing=self.ignoreNeighborForFing, level=1, text1=dev.name.ljust(30) + u" status " + status.ljust(10) + " changed period expT= %4.1f" % expT + "  dt= %4.1f" % dt, iType=u"PER-DEV-NB")
                        except  Exception, e:
                            if len(unicode(e)) > 5:
                                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
                            continue
                    else:
                        try:
                            dt = time.time() - lastUpTT
                            if dt < 1 * expT:   status = u"up"
                            elif dt < 2 * expT: status = u"down"
                            else:               status = u"expired"
                            if dev.states[u"status"] != status:
                                if status =="down" and self.doubleCheckWithPing(status,dev.states["ipNumber"], props,dev.states[u"MAC"],"Logic", "Period check-def", "chk-Time",xType) ==0:
                                    status = u"up"
                                if dev.states[u"status"] != status:
                                    changed=True
                                    self.setImageAndStatus(dev,status, oldStatus=dev.states[u"status"],ts=time.time(), fing=True, level=1, text1=dev.name.ljust(30) + u" status " + status.ljust(10) + " changed period expT= %4.1f"%expT+"  dt= %4.1f"%dt+u" devtype else:"+dev.deviceTypeId, iType=u"PER-DEV-exp")
 
                        except:
                            continue

                    self.lastSecCheck = time.time()
                except  Exception, e:
                    if len(unicode(e)) > 5:
                        indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
                        indigo.server.log(u"looking at device: "+dev.name)
            

        except  Exception, e:
            if len(unicode(e)) > 5:
                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        return  changed 





    ###########################    UTILITIES  #### START #################
    
    ### reset exp timer if it is shorter than the device exp time 
    ####-----------------    ---------
    def expTimerSettingsOK(self,xType,MAC,  dev):
        try:
            props = dev.pluginProps 
            if u"expirationTime" not in props:                                             
                return True
            if not self.fixExpirationTime: return True

            if float(self.readDictEverySeconds[xType]) <  float(props[u"expirationTime"]): return True
            newExptime  = float(self.readDictEverySeconds[xType])+30
            self.ML.myLog( text=u"  "+MAC+" updating exp time for "+dev.name+" to "+ unicode(newExptime), mType=u"Per-check1" )       
            props[u"expirationTime"] = newExptime
            dev.replacePluginPropsOnServer(props)
            return False

        except  Exception, e:
                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        return True

    ###  kill expect pids if running
    ####-----------------    ---------
    def killIfRunning(self,ipNumber,expectPGM):
        if expectPGM !="" and ipNumber !="":
            cmd = "ps -ef | grep uniFiAP | grep '" + ipNumber + " ' | grep /usr/bin/expect | grep "+expectPGM+" | grep -v grep"
        elif expectPGM !="" and ipNumber == "":
            cmd = "ps -ef | grep uniFiAP | grep /usr/bin/expect     | grep "+expectPGM+" | grep -v grep"
        elif expectPGM =="" and ipNumber != "":
            cmd = "ps -ef | grep uniFiAP | grep '" + ipNumber + " ' | grep /usr/bin/expect | grep -v grep"
        else:
            cmd = "ps -ef | grep uniFiAP |  grep /usr/bin/expect    | grep -v grep"


        if self.ML.decideMyLog(u"Connection"): self.ML.myLog( text=u"killing request: "+cmd, mType=u"KILL")
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
                ipid = int(pid)
                ret = subprocess.Popen("/bin/kill -9  " + pid, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()
                if self.ML.decideMyLog(u"Connection"): self.ML.myLog( text=u"killing expect "+expectPGM+" w ip# " +ipNumber +"  " +unicode(pid)+":\n"+line ,mType=u"KILL" )
                continue

            except:
                pass

    ### test if AP are up, first ping then check if expect is running
    ####-----------------    ---------
    def testAPandPing(self,ipNumber, type):
        try:
            if self.ML.decideMyLog(u"Connection"): self.ML.myLog( text=u"testing if " + ipNumber  + "/usr/bin/expect "+self.expectCmdFile[type]+" is running " ,mType=u"CONNtest")
            if os.path.isfile(self.pathToPlugin +self.expectCmdFile[type]):
                if self.ML.decideMyLog(u"Connection"): self.ML.myLog( text=self.expectCmdFile[type]+" exists, now doing ping" ,mType=u"CONNtest")
            if self.testPing(ipNumber) != 0:
                if self.ML.decideMyLog(u"Connection"): self.ML.myLog( text=u"ping not returned" ,mType=u"CONNtest")
                return False

            if self.ML.decideMyLog(u"Connection"): self.ML.myLog( text=u"check if pgm is running" ,mType=u"CONNtest")
            ret = subprocess.Popen("ps -ef | grep " +self.expectCmdFile[type]+ "| grep " + ipNumber + " | grep /usr/bin/expect | grep -v grep", stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()[0]
            if len(ret) < 5: False
            lines = ret.split("\n")
            for line in lines:
                if len(line) < 5:
                    continue

                ##self.ML.myLog( text=line )
                items = line.split()
                if len(items) < 5:
                    continue

                if self.ML.decideMyLog(u"Connection"): self.ML.myLog( text=u"expect is running" ,mType=u"CONNtest")
                return True

            if self.ML.decideMyLog(u"Connection"): self.ML.myLog( text=type+ "  "+ ipNumber +u" is NOT running" ,mType=u"CONNtest")
            return False
        except  Exception, e:
                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))



    ### do the ping test    
    ####-----------------    ---------
    def testPing(self,ipNumber, nTries=2):
        try:
            if nTries!=2:
                ret = os.system("/sbin/ping  -c 1 -W 1 -o " + ipNumber + ">/dev/null ")  # send max 1 package
                if int(ret) == 0: # ping ok
                    return 0
                return 1


            ret = os.system("/sbin/ping  -c 4 -W 1 -o " + ipNumber + ">/dev/null ")  # send max 4 packets, wait 0.5 secs between each and if one gets back stop
            if int(ret) == 0:
                return 0

            self.ML.myLog( text=u" ping return-code not 0: " + unicode(ret) )
            self.sleep(2)
            ret = os.system("/sbin/ping  -c 4 -W 1 -o " + ipNumber + ">/dev/null ")
            if int(ret) == 0:
                return 0

            self.ML.myLog( text=u" ping return-code not 0: " + unicode(ret) )
            return 1
        except  Exception, e:
            indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e) )
        return 1

    ### init,save,write data stats for receiving messages 
    ####-----------------    ---------
    def addTypeToDataStats(self,ipNumber, apN, uType):
        try: 
            if uType not in self.dataStats["tcpip"]:
                self.dataStats["tcpip"][uType]={}
            if ipNumber not in self.dataStats["tcpip"][uType]:
                self.dataStats["tcpip"][uType][ipNumber]={u"inMessageCount":0,u"inMessageBytes":0,u"inErrorCount":0,u"restarts":0,u"startTime":time.time(),u"APN":unicode(apN), u"aliveTestCount":0}
        except  Exception, e:
            indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e) )
    ####-----------------    ---------
    def zeroDataStats(self): 
        for uType in self.dataStats["tcpip"]:
            for ipNumber in self.dataStats["tcpip"][uType]:
                self.dataStats["tcpip"][uType][ipNumber][u"inMessageCount"]   =0
                self.dataStats["tcpip"][uType][ipNumber][u"inMessageBytes"]   =0
                self.dataStats["tcpip"][uType][ipNumber][u"aliveTestCount"]   =0
                self.dataStats["tcpip"][uType][ipNumber][u"inErrorCount"]     =0
                self.dataStats["tcpip"][uType][ipNumber][u"restarts"]         =0
                self.dataStats["tcpip"][uType][ipNumber][u"startTime"]        =time.time()
        self.dataStats["updates"]={"devs":0,"states":0,"startTime":time.time()}
    ####-----------------    ---------
    def resetDataStats(self): 
        self.dataStats={"tcpip":{},"updates":{"devs":0,"states":0,"startTime":time.time()}}
        self.saveDataStats()  
    ####-----------------    ---------
    def saveDataStats(self): 
        if time.time() - 60  < self.lastSaveDataStats: return 
        self.lastSaveDataStats = time.time() 
        f=open(self.unifiPath+"dataStats","w")
        f.write(json.dumps(self.dataStats, sort_keys=True, indent=2))
        f.close()
        
    ####-----------------    ---------
    def readDataStats(self):
        self.lastSaveDataStats  = time.time() -60 
        try:
            f=open(self.unifiPath+"dataStats","r")
            self.dataStats= json.loads(f.read())
            f.close()
            if "tcpip" not in self.dataStats: 
                self.resetDataStats()
            return
        except: pass

        self.resetDataStats()
        return 

    ### ----------- save read MAC2INDIGO  -----  ##
        
    ####-----------------    ---------
    def saveMACdata(self): 
        if time.time() - 20  < self.lastSaveMAC2INDIGO: return 
        self.lastSaveMAC2INDIGO = time.time() 

        f=open(self.unifiPath+"MAC2INDIGO","w")
        f.write(  json.dumps( self.MAC2INDIGO, sort_keys=True, indent=2 ) )
        f.close()
        f=open(self.unifiPath+"MACignorelist","w")
        f.write(  json.dumps( self.MACignorelist) )
        f.close()
        
    ####-----------------    ---------
    def readMACdata(self):
        self.lastSaveMAC2INDIGO  = time.time() -21 
        try:
            f=open(self.unifiPath+"MAC2INDIGO","r")
            self.MAC2INDIGO= json.loads(f.read())
            f.close()
        except: 
            self.MAC2INDIGO ={"UN":{},u"GW":{},u"SW":{},u"AP":{},u"NB":{},u"SW":{}}
        try:
            f=open(self.unifiPath+"MACignorelist","r")
            self.MACignorelist= json.loads(f.read())
            f.close()
        except: 
            self.MACignorelist ={}
        return 

        
    ### here we do the work, setup the logfiles listening and read the logfiles and check if everything is running, if not restart
    ####-----------------    ---------
    def getMessages(self, ipNumber, apN, uType, repeatRead):


        apnS = unicode(apN)
        self.addTypeToDataStats(ipNumber, apnS, uType)
        try:
            errorCount =0
            unifiDeviceType = uType[0:2]

            #### for ever, until self.stop is set
            total               = ""
            lastTestServer      = time.time()
            lastForcedRestart   = -1
            testServerCount     = -3  # not for the first 3 rounds
            connectErrorCount   = 0
            msgSleep            = 1
            minWaitbeforeRestart= max(float(self.restartIfNoMessageSeconds), float(repeatRead) )
            while True:

                if (time.time()- lastForcedRestart) > minWaitbeforeRestart: # init comm
                            if self.ML.decideMyLog(u"Connection"):
                                if lastForcedRestart> 0:
                                    self.ML.myLog( text=uType +" " + ipNumber +"  "+self.expectCmdFile[uType]+" forcing restart of msg after " + unicode(int(time.time() - lastForcedRestart)) + " sec without message" ,mType=u"EXPECT" )
                                    self.dataStats["tcpip"][uType][ipNumber]["restarts"]+=1
                                else:
                                    self.ML.myLog( text=u"launching " + ipNumber ,mType=u"START" )

                            try:       ListenProcess.close()
                            except:    pass

                            self.killIfRunning(ipNumber,self.expectCmdFile[uType] )
                            if not self.testServerIfOK(ipNumber):
                                self.ML.myLog(text="\n\n================================================\n FATAL error connecting to ip#: "\
                                +ipNumber+" wrong ip/ password ...?\n================================================n",mType="getMessages") 
                                return 
                            ListenProcess, msg = self.startConnect(ipNumber,uType)

                            if msg != "":
                                self.ML.myLog( text=u" fatal error, connect for ip#: " + ipNumber ,mType=u"START" )
                                if connectErrorCount > 3: return
                                self.sleep(5)
                                continue

                            connectErrorCount = 0
                            lastForcedRestart = time.time()


                self.sleep(msgSleep)

                ## force restart after xx seconds no matter what?
                if errorCount > 3:
                    self.ML.myLog( text=uType + " " + ipNumber + " forcing restart of msg after due to error count in json", mType=u"EXPECT")
                    errorCount =0
                    lastForcedRestart = time.time()
                    self.killIfRunning(ipNumber, "")
                    #ListenProcess, msg = self.startConnect(ipNumber, uType)

                ## force a logfile respnse by logging in. this is needed to make the tail -f pis send a message to make sure we are still alove
                if (time.time() - lastForcedRestart) > max(30.,minWaitbeforeRestart*0.9): 
                    if  uType.find("tail") >- 1: 
                        if (time.time() - lastTestServer) > 30:
                            testServerCount +=1
                            if testServerCount > 1:
                                lastForcedRestart = 0

                            else:
                                if self.testAPandPing(ipNumber,uType):
                                    if not self.testServerIfOK(ipNumber):
                                        self.ML.myLog(text="\n\n================================================\n FATAL error connecting to ip#: "\
                                        +ipNumber+" wrong ip/ password ...?\n================================================n",mType="getMessages") 
                                        return 
                                else:
                                    lastForcedRestart =0
                            lastTestServer = time.time()

                ## should we stop?, is our IP number listed?
                if ipNumber in self.stop:
                    self.ML.myLog( text=uType+ " stop in getMessage stop=True" )
                    # ListenProcess.close()
                    while self.stop.count(ipNumber) > 0:
                        self.stop.remove(ipNumber)
                    return

                ## here we actually read the stuff
                try:
                    linesFromServer = os.read(ListenProcess.stdout.fileno(),32767) ## = 32k
                    msgSleep = 0.1 # fast read to follow
                except  Exception, e:
                    if unicode(e).find("[Errno 35]") == -1:  # "Errno 35" is the normal response if no data, if other error: exit
                        self.ML.myLog( text=u"error" + unicode( e ) )
                        # ListenProcess.close()
                        stop.append(ipNumber)
                    else:
                        msgSleep = 0.4 # nothing new, can wait
                    continue
                    ## did we get anything?

                if linesFromServer != "":
                    self.dataStats["tcpip"][uType][ipNumber]["inMessageCount"]+=1
                    self.dataStats["tcpip"][uType][ipNumber]["inMessageBytes"]+=len(linesFromServer)
                    lastForcedRestart = time.time()
                    lastTestServer    = time.time()
                    testServerCount   = 0
                    ## any error messages from OSX?
                    pos1 = linesFromServer.find("closed by remote host")
                    pos2 = linesFromServer.find("Killed by signal")
                    pos3 = linesFromServer.find("Killed -9")
                    if (  pos1 >- 1 or pos2 >- 1 or pos3 > -1):
                        self.ML.myLog( text=uType+" returning " + ipNumber  ,mType=u"EXPECT" )
                        if pos1 >-1: self.ML.myLog( text=unicode(linesFromServer[max(0,pos1 - 100):pos1 + 100]), mType=u"EXPECT")
                        if pos2 >-1: self.ML.myLog( text=unicode(linesFromServer[max(0,pos2 - 100):pos2 + 100]), mType=u"EXPECT")
                        if pos3 >-1: self.ML.myLog( text=unicode(linesFromServer[max(0,pos3 - 100):pos3 + 100]), mType=u"EXPECT")
                        self.ML.myLog( text=uType+" we should restarting listener on server " ,mType=u"EXPECT" )

                        #self.killIfRunning(ipNumber,self.expectCmdFile[uType])
                        #ListenProcess, msg = self.startConnect(ipNumber,uType)
                        continue
                    ##self.ML.myLog( text=unicode(r))


                ######### for tail logfile
                    if uType.find("dict") ==-1:
                        ## fill the queue and send to the method that uses it
                        if      unifiDeviceType == "AP":
                            self.APUP[ipNumber] = time.time()
                        elif    unifiDeviceType == "GW":
                            self.GWUP[ipNumber] = time.time()
                        errorCount = 0
                        if linesFromServer.find("ThisIsTheAliveTestFromUnifiToPlugin") > -1:
                            self.dataStats["tcpip"][uType][ipNumber]["aliveTestCount"]+=1
                            if self.ML.decideMyLog(u"Connection"): self.ML.myLog( text=uType + "  " + ipNumber + " ThisIsTheAliveTestFromUnifiToPlugin received ", mType=u"CONNect")
                            continue
                        self.logQueue.put((linesFromServer,ipNumber,apN, uType,unifiDeviceType))
                        self.updateIndigoWithLogData()  #####################  here we call method to do something with the data


                    ######### for Dicts
                    else:
                        total += linesFromServer
                        ppp = total.split(self.startDictToken[uType])
                        if len(ppp) ==2:
                            if ppp[1].find(self.endDictToken[uType]) >-1:
                                dictData0 = ppp[len(ppp) - 1].lstrip("\r\n")

                                try:
                                    dictData= dictData0.split(self.endDictToken[uType])[0]
                                    ## remove last line
                                    if dictData[-1] !="}":
                                        ppp = dictData.rfind("}")
                                        dictData = dictData[0:ppp+1]
                                    theDict= json.loads(dictData)
                                    errorCount = 0
                                    if    unifiDeviceType == "AP":
                                        self.APUP[ipNumber] = time.time()
                                    elif  unifiDeviceType == "SW":
                                        self.SWUP[ipNumber] = time.time()
                                    elif  unifiDeviceType == "GW":
                                        self.GWUP[ipNumber] = time.time()
                                    self.logQueueDict.put((theDict,ipNumber,apN,uType, unifiDeviceType))
                                    self.updateIndigoWithDictData2()  #####################  here we call method to do something with the data
                                except  Exception, e:
                                    if len(unicode(e)) > 5:
                                        indigo.server.log(u"in Line '%s' has error='%s',receiving DICTs for %s;   check unifi logfile; if this happens to often increase DICT timeout " % (sys.exc_traceback.tb_lineno, e,ipNumber))
                                        self.ML.myLog( text=uType+ "  "+ ipNumber+" error in the JSON data", mType=u"EXPECT")
                                        self.ML.myLog( text=uType+" JSON-start="+unicode(  total[0:120]  ).replace("\n","").replace("\r",""), mType=u"EXPECT")
                                        self.ML.myLog( text=uType+" JSON-end  ="+unicode(  total[-min(len(total)-1,120):]  ).replace("\n","").replace("\r",""), mType=u"EXPECT")
                                        self.dataStats["tcpip"][uType][ipNumber]["inErrorCount"]+=1

                                        errorCount+=1
                                    lastForcedRestart = time.time() - minWaitbeforeRestart*0.91
                                total = ""
                        else:
                            total=""
                    if self.statusChanged > 0:   
                        self.setGroupStatus()
                        

        except  Exception, e:
            if len(unicode(e)) > 5:
                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))



    ### start the expect command to get the logfile
    ####-----------------    ---------
    def startConnect(self, ipNumber, uType):
        try:
            TT= uType[0:2]
            for ii in range(20):
                if uType.find("dict")>-1:
                    cmd = "/usr/bin/expect  '" + \
                          self.pathToPlugin + self.expectCmdFile[uType] + "' " + \
                          self.unifiUserID + " " + \
                          self.unifiPassWd + " " + \
                          ipNumber + " " + \
                          self.promptOnServer[uType] + " " + \
                          self.endDictToken[uType]+ " " + \
                          unicode(self.readDictEverySeconds[TT])+ " " + \
                          unicode(self.timeoutDICT)
                    if uType.find("AP") >-1:
                         cmd += "  /var/log/messages"
                    else:
                         cmd += "  doNotSendAliveMessage"

                else:
                    cmd = "/usr/bin/expect  '" + \
                          self.pathToPlugin +self.expectCmdFile[uType] + "' " + \
                          self.unifiUserID + " " + \
                          self.unifiPassWd + " " + \
                          ipNumber + " " + \
                          self.promptOnServer[uType] + " " + \
                          self.commandOnServer[uType]

                if self.ML.decideMyLog(u"Connection"): self.ML.myLog( text=cmd, mType=u"EXPECT")
                ListenProcess = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                ##pid = ListenProcess.pid
                ##self.ML.myLog( text=u" pid= " + unicode(pid) )
                msg = unicode(ListenProcess.stderr)
                if msg.find("[Err ") > -1:  # try this again
                    self.ML.myLog( text=uType + " error connecting " + msg, mType=u"EXPECT")
                    self.sleep(20)
                    continue

                # set the O_NONBLOCK flag of ListenProcess.stdout file descriptor:
                flags = fcntl.fcntl(ListenProcess.stdout, fcntl.F_GETFL)  # get current p.stdout flags
                fcntl.fcntl(ListenProcess.stdout, fcntl.F_SETFL, flags | os.O_NONBLOCK)
                return ListenProcess, ""

        except  Exception, e:
            if len(unicode(e)) > 5:
                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        return "", ""


    ####-----------------    ---------
    def testServerIfOK(self, ipNumber):
        cmd = "/usr/bin/expect  '" + self.pathToPlugin +"test.exp' " + self.unifiUserID + " " + self.unifiPassWd + " " + ipNumber 
        if self.ML.decideMyLog(u"Connection"): self.ML.myLog( text=cmd, mType=u"EXPECT")
        ret = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()
        if ret[0].find("Welcome") > -1:       return True
        if ret[0].find("UniFi") > -1:         return True
        if ret[0].find("Edge") > -1:          return True
        if ret[0].find("BusyBox") > -1:       return True
        if ret[0].find("Ubiquiti") > -1:      return True
        if ret[0].find("ubnt") > -1:          return True
        self.ML.myLog(text="\n==========="+ipNumber+"  ==> "+ ret[0],mType=u"testConnection") 
        return False





    ####-----------------    ---------
    def updateIndigoWithLogData(self):
        try:
            while not self.logQueue.empty():
                item = self.logQueue.get()

                lines           = item[0].split("\r\n")
                ipNumber        = item[1]
                apN             = item[2]
                uType           = item[3]
                xType           = item[4]

                ## update device-ap with new timestamp, it is up
                if self.ML.decideMyLog(u"Log"): self.ML.myLog( text=ipNumber+"  "+ unicode(apN)+ "  "+uType+"  "+xType+"\n"+ unicode(lines), mType=u"MS-----" )
              
                ### update lastup for unifi devices  
                if xType in self.MAC2INDIGO:
                    for MAC in self.MAC2INDIGO[xType]:
                        if xType== u"UN" and self.testIgnoreMAC(MAC,"log"): continue
                        if ipNumber == self.MAC2INDIGO[xType][MAC][u"ipNumber"]:
                            self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
                            break
                            
                if   uType == "APtail":
                    self.doAPmessages(lines, ipNumber, apN)
                elif uType == "GWtail":
                    self.doGWmessages(lines, ipNumber, apN)
                elif uType == "SWtail":
                    self.doSWmessages(lines, ipNumber, apN)

                self.executeUpdateStatesList()

            self.logQueue.task_done()
            if len(self.sendUpdateToFingscanList) >0: self.sendUpdatetoFingscanNOW()
        except  Exception, e:
            if len(unicode(e)) > 5:
                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))


    ####-----------------    ---------
    def doGWmessages(self, lines,ipNumber,apN):
        try:
            devType  = u"UniFi"
            devName  = u"UniFi"
            suffixN  = u"DHCP"
            xType    = u"UN"

            part="doGWmessages"+unicode(random.random()); self.blockAccess.append(part)
            for ii in range(90):
                if len(self.blockAccess) == 0 or self.blockAccess[0] == part: break # my turn?
                self.sleep(0.1)
            if ii >= 89: self.blockAccess = [] # for safety if too long reset list

# looking for dhcp refresh requests  
#  Oct 26 22:20:00 GW sudo:     root : TTY=unknown ; PWD=/ ; USER=root ; COMMAND=/bin/sh -c echo -e '192.168.1.180\t iPhone.localdomain\t #on-dhcp-event 18:65:90:6a:b9:c' >> /etc/hosts
       
            tag = "TTY=unknown ; PWD=/ ; USER=root ; COMMAND=/bin/sh -c echo -e '"
            for line in lines:
                if len(line) < 10: continue
                if line.find(tag) ==-1: continue
                if self.ML.decideMyLog(u"LogDetails"): self.ML.myLog( text=line, mType=u"MS-GW---" )
                items   = line .split(tag)
                if len(items) !=2: continue
                items   = items[1].split("' >> /etc/hosts")
                if len(items) != 2: continue
                items   = items[0].split("\\t")
                if len(items) != 3: continue
                ip      = items[0]
                name    = items[1]
                items   = items[2].split()
                if len(items) != 2: continue

                MAC = self.checkMAC(items[1])# fix a bug in hosts file
                if self.testIgnoreMAC(MAC,"GW-msg"): continue

                new = True
                if MAC in self.MAC2INDIGO[xType]:
                    try:
                        dev = indigo.devices[self.MAC2INDIGO[xType][MAC][u"devId"]]
                        if dev.deviceTypeId != devType: 1/0
                        new = False
                    except:
                        if self.ML.decideMyLog(u"LogDetails") or MAC in self.MACloglist: self.ML.myLog( text=MAC + "  " + unicode(self.MAC2INDIGO[xType][MAC][u"devId"]) + " wrong " + devType)
                        for dev in indigo.devices.iter(self.pluginId):
                            if dev.deviceTypeId == "client": continue
                            if dev.deviceTypeId != devType: continue
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
                        self.addToStatesUpdateList(unicode(dev.id),u"ipNumber", ip)
                    ## if a device asks for dhcp extension, it must be alive,  good for everyone..
                    if True :#  useWhatForStatus" in props and props[u"useWhatForStatus"] == "DHCP":
                        if dev.states[u"status"] != "up":
                            self.setImageAndStatus(dev, "up",oldStatus= dev.states[u"status"],ts=time.time(), level=1, text1= dev.name.ljust(30) + u" status up         GW msg ", iType=u"STATUS-DHCP",reason=u"MS-DHCP "+u"up")
                        else:
                            if self.ML.decideMyLog(u"LogDetails") or MAC in self.MACloglist: self.ML.myLog( text=MAC + " restarting expTimer due to DHCP renew", mType=u"MS-GW-" )
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
                            folder=self.folderNameCreatedID,
                            props={u"useWhatForStatus":"DHCP","useAgeforStatusDHCP":"-1"})
                    except  Exception, e:
                        if len(unicode(e)) > 5:
                            indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
                        continue    
                    self.setupStructures(xType, dev, MAC)
                    self.setupBasicDeviceStates(dev, MAC, "UN", "", "", "", u" status up         GW msg new device", "STATUS-DHCP")
 
            self.executeUpdateStatesList()
        except  Exception, e:
            if len(unicode(e)) > 5:
                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

        self.executeUpdateStatesList()

        if len(self.blockAccess)>0:  del self.blockAccess[0]


        return
                        

    ####-----------------    ---------
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
                if self.ML.decideMyLog(u"Log"): self.ML.myLog( text=ipNumber+"  "+ line,type = "MS-SW----")


        except  Exception, e:
                if len(unicode(e)) > 5:
                    indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        
        if len(self.blockAccess)>0:  del self.blockAccess[0]
        return
        
        
    ####-----------------    ---------
    def doAPmessages(self, lines, ipNumberAP, apN):
        
        part="doAPmessages"+unicode(random.random()); self.blockAccess.append(part)
        for ii in range(90):
                if len(self.blockAccess) ==0 or self.blockAccess[0]==part:
                    break
                self.sleep(0.1)   
        if ii >= 89: self.blockAccess = [] # for safety if too long reset list
        
        try:
            devType = "UniFi"
            devName = "UniFi"
            suffixN  = "WiFi"
            xType   =  u"UN" 

            for line in lines:
                if len(line) < 2: continue
                tags = line.split()
                MAC = ""
                if self.ML.decideMyLog(u"Log"): self.ML.myLog( text=unicode(ipNumberAP)+"-"+unicode(apN) + "  " + line, mType=u"MS-AP----")

                ll = line.find("[HANDOVER]") + 10 +1 ## len of [HANDOVER] + one space
                if ll  > 30:
                    if ll+17  >=  len(line):     continue  # 17 = len of MAC address
                    lin2 = line.split("[HANDOVER]")[1]
                    tags = lin2.split()
                    if len(tags) !=5: continue
                    MAC = tags[0]
                    if MAC.count(":") != 5:      continue
                    if self.testIgnoreMAC(MAC,"AP-msg"): continue

                    ipNumber = tags[4]  # new IP number of target AP 
                    self.HANDOVER[MAC] = {"tt":time.time(),"ipNumberNew":ipNumber, "ipNumberOld":tags[2]}
                        ### handle this: [HANDOVER] 
                        #13:40:42 AP----      -192.168.1.4  Apr 16 13:40:41 4-kons daemon.notice hostapd: ath0: IEEE 802.11 UBNT-ROAM.get-sta-data for 18:65:90:6a:b9:0c
                        #13:40:42 AP----      -192.168.1.4  Apr 16 13:40:41 4-kons user.info kernel: [92232.074000] ubnt_roam [BASIC]:[HANDOVER] 18:65:90:6a:b9:0c from 192.168.1.4 to 192.168.1.5
                        #13:40:42 AP----      -192.168.1.4  Apr 16 13:40:41 4-kons daemon.notice hostapd: ath0: IEEE 802.11 UBNT-ROAM.sta-leave: 18:65:90:6a:b9:0c
                        #13:40:42 AP----      -192.168.1.4  Apr 16 13:40:41 4-kons daemon.info hostapd: ath0: STA 18:65:90:6a:b9:0c IEEE 802.11: disassociated
                        #13:40:42 MS-AP-WiFi -  AP message received 18:65:90:6a:b9:0c  UniFi-iphone7-karl;  old/new associated 192.168.1.4/192.168.1.4
                        #13:40:42 MS-AP-WiFi - 18:65:90:6a:b9:0c UniFi-iphone7-karl             check timer,  down token: disassociated time.time() -upt 1492368042.1

                ###  add test for :
                # 13:22:58 AP----      -192.168.1.4  Apr 15 13:22:57 4-kons user.info kernel: [ 4766.438000] ubnt_roam [BASIC]:Presence at AP 192.168.1.5 verified for 18:65:90:6a:b9:0c
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
                        if ll+1 >=  len(tags):                 continue
                        MAC = tags[ll + 1]
                        if MAC.count(":") != 5:                
                            continue
                        if  line.find("Authenticating") > 10:  
                            continue
                        if  line.find("STA Leave!!") != -1 :   
                            continue
                        if  line.find("STA enter") != -1:      
                            continue
                    except Exception, e: 
                        if unicode(e).find("not in list") >-1: continue
                        indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
                        continue

                if self.testIgnoreMAC(MAC,"AP-msg"): continue
                
                
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
                            if self.ML.decideMyLog(u"all"): self.ML.myLog( text=MAC + "  " + unicode(self.MAC2INDIGO[xType][MAC][u"devId"]) + " wrong " + devType)
                            for dev in indigo.devices.iter(self.pluginId):
                                if dev.deviceTypeId == "client": continue
                                if dev.deviceTypeId != devType:  continue
                                if "MAC" not in dev.states:      continue
                                if dev.states[u"MAC"] != MAC:    continue
                                self.MAC2INDIGO[xType][MAC]={}
                                self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
                                self.MAC2INDIGO[xType][MAC][u"devId"] = dev.id
                                new = False
                                break
                    
                    if not new:
                        props =  dev.pluginProps
                        devId = unicode(dev.id)
                        if devId not in self.upDownTimers:
                            self.upDownTimers[devId] = {"down": 0, "up": 0}

                        oldIP = dev.states[u"AP"]
                        if ipNumberAP != oldIP.split("-")[0]:
                            if up:
                                self.addToStatesUpdateList(unicode(dev.id),u"AP", ipNumberAP+"-#"+unicode(apN))
                            else:
                                if self.ML.decideMyLog(u"LogDetails") or MAC in self.MACloglist: self.ML.myLog( text=u"  AP message received "+MAC+"  "+ dev.name+";  old/new associated AP "+oldIP+"/"+unicode(ipNumberAP)+"-"+unicode(apN)  +" ignoring as associated to old AP", mType=u"MS-AP-WiF-0")
                                continue

    
                        if "useWhatForStatus" in props and props[u"useWhatForStatus"] == "WiFi":
                        
                            if self.ML.decideMyLog(u"LogDetails") or MAC in self.MACloglist: self.ML.myLog( text=u"  AP message received "+MAC+"  "+ dev.name+";  old/new associated "+oldIP+"/"+unicode(ipNumberAP)+"-#"+unicode(apN) , mType=u"MS-AP-WiF-1")

                            if up: # is up now
                                self.MAC2INDIGO[xType][MAC][u"idleTime" + suffixN] = 0
                                self.upDownTimers[devId][u"down"] = 0
                                self.upDownTimers[devId][u"up"] = time.time()
                                if dev.states[u"status"] != "up":
                                    self.setImageAndStatus(dev, "up",oldStatus= dev.states[u"status"], ts=time.time(), level=1, text1= dev.name.ljust(30) + u" status up         AP message received "+ipNumberAP, iType=u"MS-AP-WiF-2",reason=u"MSG WiFi "+u"up")
                                self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()

                            else: # is down now
                                try:
                                    if devId not in self.upDownTimers:
                                        self.upDownTimers[devId] = {"down": 0, "up": 0}

                                    if ipNumberAP == oldIP.split("-")[0]: # only if its on the same current AP
                                        dt = (time.time() - self.upDownTimers[devId][u"up"])

                                        if "useWhatForStatusWiFi" in props and props[u"useWhatForStatusWiFi"] in ["FastDown","Optimized"]:
                                            if self.ML.decideMyLog(u"Logic") or MAC in self.MACloglist: self.ML.myLog( text=u" "+MAC+" "+ dev.name.ljust(30) + u" check timer,  down;  token: " + token + " time.time() -upt %4.1f" % dt, mType=u"MS-AP-WiF-3")
                                            if (dt) > 5.0:
                                                if dev.states[u"status"] == "up":
                                                    #indigo.server.log(u" apmsg dw "+ dev.name+u" changed: old status: "+dev.states[u"status"]+u"; new  down")
                                                    if props[u"useWhatForStatusWiFi"] == "FastDown":  # in fast down set it down right now
                                                        self.setImageAndStatus(dev, "down",oldStatus="up", ts=time.time(), level=1, text1=" "+MAC+" "+ dev.name.ljust(30) + u" status down         AP message received fast down-", iType=u"MS-AP-WiF-4",reason=u"MSG DHCP "+u"down")
                                                        self.upDownTimers[devId][u"down"] = time.time()
                                                    else:  # in optimized give it 3 more secs
                                                        self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time() - self.getexpT(props)+3
                                                        self.upDownTimers[devId][u"down"] = time.time() +3
                                                    self.upDownTimers[devId][u"up"]   = 0.
                                                
                                        elif dt > 2.:
                                            self.upDownTimers[devId][u"down"] =  time.time()  # this is a down message
                                            self.upDownTimers[devId][u"up"]   = 0.
                                except  Exception, e:
                                    if len(unicode(e)) > 5:
                                        indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))


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
                                folder=self.folderNameCreatedID,
                                props={u"useWhatForStatus":"WiFi","useWhatForStatusWiFi":"Expiration"})
                        except Exception, e:
                            if len(unicode(e)) > 5:
                                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e)+" trying to create: "+devName+"_" + MAC)
                            continue
                        self.setupStructures(xType, dev, MAC)
                        self.addToStatesUpdateList(unicode(dev.id),u"AP", ipNumberAP+"-#"+unicode(apN))
                        self.MAC2INDIGO[xType][MAC][u"idleTime" + suffixN] = 0
                        if unicode(dev.id) in self.upDownTimers:
                            del self.upDownTimers[unicode(dev.id)]
                        self.setupBasicDeviceStates(dev, MAC,  "UN", "", "", "", "  "+MAC+u" status up         AP msg new device", "MS-AP-WiF-6")

                        self.executeUpdateStatesList()
        except  Exception, e:
            if len(unicode(e)) > 5:
                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

        self.executeUpdateStatesList()
     
        if len(self.blockAccess)>0:  del self.blockAccess[0]

        return

    ####-----------------    ---------
    ### double check up/down with ping 
    ####-----------------    ---------
    def doubleCheckWithPing(self,newStatus, ipNumber, props,MAC,debLevel, section, theType,xType):
        
        if ("usePingUP" in props and props["usePingUP"] and newStatus =="up" ) or ( "usePingDOWN" in props and props["usePingDOWN"] and newStatus !="up") : 
            if self.testPing(ipNumber,nTries=1) == 1: 
                if self.ML.decideMyLog(debLevel) or MAC in self.MACloglist: self.ML.myLog( text=u" "+MAC+" "+section+" , status changed - not up , ping test failed" ,mType=theType)
                return 1
            else:
                if self.ML.decideMyLog(debLevel) or MAC in self.MACloglist: self.ML.myLog( text=u" "+MAC+" "+section+" , status changed - not up , ping test OK" ,mType=theType)
                if xType in self.MAC2INDIGO:
                    self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
                return 0
        return -1


    ####-----------------    ---------
    ### for the dict,
    ####-----------------    ---------
    def updateIndigoWithDictData2(self):
        try:
            while not self.logQueueDict.empty():
                next = self.logQueueDict.get()
                #self.ML.myLog( text=unicode(next[0])[0:300] ,mType=u"up...Data2" )
                ###if self.ML.decideMyLog(u"Connection"): self.ML.myLog( text=unicode(next)[0:1000] + "...." ,mType=u"MESS---")
                self.updateIndigoWithDictData(next[0],next[1],next[2],next[3],next[4])
            self.logQueueDict.task_done()
        except  Exception, e:
            if len(unicode(e)) > 5:
                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

        if len(self.sendUpdateToFingscanList) >0: self.sendUpdatetoFingscanNOW()
        


    ####-----------------    ---------
    def updateIndigoWithDictData(self, apDict, ipNumber, apNumb, uType, unifiDeviceType):
        if len(apDict) < 1: return

        try:
            self.manageLogfile(apDict,apNumb,unifiDeviceType)

            if self.ML.decideMyLog(u"Dict"): self.ML.myLog( text=u"ipNumber: "+unicode(ipNumber)+"  apNumb: "+unicode(apNumb)+"  uType: "+unicode(uType)+"  unifiDeviceType: "+unicode(unifiDeviceType)+"  "+ unicode(apDict)[0:100] + "...." ,mType=u"DC-----")


            if unifiDeviceType =="GW":
            ### gateway
                self.doGatewaydictSELF(apDict)
                self.doDHCPdictClients(apDict)



            elif unifiDeviceType == "SW":
                if "mac"         not in apDict: return
                if u"port_table" not in apDict: return 
                if u"hostname"   not in apDict: return 
                if u"ip"         not in apDict: return 

                MAC = apDict[u"mac"]
                hostname = apDict[u"hostname"].strip()
                ipNDevice = apDict[u"ip"]

                #################  update SWs themselves
                self.doSWdictSELF(apDict, apNumb, ipNDevice, MAC, hostname)

                #################  now update the devices on switch
                self.doSWITCHdictClients(apDict, apNumb, ipNDevice, MAC, hostname)

            elif unifiDeviceType == "AP":
                if "mac"         not in apDict: return
                if u"vap_table"  not in apDict: return 
                if u"ip"         not in apDict: return 

                MAC      = apDict[u"mac"]
                hostname = apDict[u"hostname"].strip()
                ipNDevice= apDict[u"ip"]

                for jj in range(len(apDict[u"vap_table"])):
                    channel = unicode(apDict[u"vap_table"][jj][u"channel"])
                    if int(channel) >= 36:
                        GHz = "5"
                    else:
                        GHz = "2"

    #################  update APs themselves
                    self.doAPdictsSELF(apDict, jj, apNumb,  channel, GHz, ipNDevice, MAC, hostname)

    #################  now update the WiFi clients
                    self.doWiFiCLIENTSdict(apDict[u"vap_table"][jj][u"sta_table"],  GHz, ipNDevice, apNumb)


    ############  update neighbors
                if "radio_table"         in  apDict:  
                    self.doNeighborsdict(apDict[u"radio_table"], apNumb, ipNDevice)


        except  Exception, e:
            if len(unicode(e)) > 5:
                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))


        return




    ####-----------------    ---------
    #################  update APs
    ####-----------------    ---------
    def doInList(self,suffixN,  wifiIP=""):


        suffix = suffixN.split("_")[0]
        try:
            ## now check if device is not in dict, if not ==> initiate status --> down
            xType = u"UN"
            delMAC={}
            for MAC in self.MAC2INDIGO[xType]:
                if self.MAC2INDIGO[xType][MAC][u"inList"+suffixN]  == -1: continue  # do not test
                if self.MAC2INDIGO[xType][MAC][u"inList"+suffixN]  ==  1: continue  # is here 
                try:
                    devId = self.MAC2INDIGO[xType][MAC][u"devId"]
                    dev   = indigo.devices[devId]
                    aW    = dev.states["AP"]
                    if wifiIP =="" or aW == wifiIP:
                        self.MAC2INDIGO[xType][MAC][u"inList"+suffixN] = 0
                    if wifiIP !="" and aW != wifiIP:                                             continue
                    if dev.states[u"status"] != "up":                                            continue
 
                    props= dev.pluginProps
                    if "useWhatForStatus" not in props or props[u"useWhatForStatus"] != suffix:  continue
                except  Exception, e:
                    if unicode(e).find("timeout waiting") > -1:
                        self.ML.myLog( text=u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
                        self.ML.myLog( text=u"communication to indigo is interrupted")
                        return
                    indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e)+"  just deleted?.. then ignore message")
                    indigo.server.log(u"deleting device from internal lists -- MAC:"+ MAC+";  devId:"+unicode(devId))
                    delMAC[MAC]=1
                    continue    

                try:   
                    lastUpTT   = self.MAC2INDIGO[xType][MAC][u"lastUp"]
                except:
                    lastUpTT = time.time() - 1000


                expT = self.getexpT(props)# this should be much faster than normal expiration 
                if wifiIP !="" : expTUse  = max(expT/2.,10) # only for non wifi devices 
                else:            expTUse  = expT
                dt = time.time() - lastUpTT
                if dt < 1 * expT:
                    status = "up"
                elif dt < 2 * expT:
                    status = "down"
                else:
                    status = "expired"


                if dev.states[u"status"] != status and status !="up":
                    if "usePingUP" in props and props["usePingUP"]  and status !="up" and self.testPing(dev.states["ipNumber"],nTries=1) == 0: 
                            if self.ML.decideMyLog(u"Logic") or MAC in self.MACloglist: self.ML.myLog( text=u"  "+dev.states[u"MAC"]+" check, status changed - not up , ping test ok resetting to up" ,mType="List-"+suffix)
                            self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
                            continue

                    # indigo.server.log(" 4 " +dev.name + " set to "+ status)
                    #indigo.server.log(u" inList "+ dev.name+u" changed: old status: "+dev.states[u"status"]+u"; new  "+status)
                    self.setImageAndStatus(dev, status,oldStatus=dev.states[u"status"], ts=time.time(), level=1, text1= dev.name.ljust(30) + u" in list status " + status.ljust(10) + " "+suffixN+"  dt= %5.1f" % dt + ";  expT= %5.1f" % expT+ "  wifi:" +wifiIP, iType=u"STATUS-"+suffix,reason=u"NotInList "+suffixN+u" "+wifiIP+u" "+status)
                    #self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time() - expT
       #self.executeUpdateStatesList()

            for MAC in delMAC:
                del  self.MAC2INDIGO[xType][MAC]

        except  Exception, e:
            if len(unicode(e)) > 5:
                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        return




    ####-----------------    ---------
    #### this does the unifswitch attached devices
    ####-----------------    ---------
    def doSWITCHdictClients(self, apDict, apNumb, ipNDevice, MACSW, hostnameSW):
        
    
    
        part="doSWITCHdict"+unicode(random.random()); self.blockAccess.append(part)
        for ii in range(90):
                if len(self.blockAccess) ==0 or self.blockAccess[0]==part:  break
                self.sleep(0.1)   
        if ii >= 89: self.blockAccess = [] # for safety if too long reset list

    
        try:

            devType = "UniFi"
            devName = "UniFi"
            suffix  = "SWITCH"
            xType   = u"UN"

            portTable = apDict[u"port_table"]


            if ipNDevice not in self.SWUP:  
                if len(self.blockAccess)>0:  del self.blockAccess[0]
                return 
            
            switchNumber =-1
            for ii in range(_GlobalConst_numberOfSW):
                if not self.SWsEnabled[ii]:             continue
                if ipNDevice !=self.ipNumbersOfSWs[ii]: continue
                switchNumber = ii
                break

            if switchNumber <0: 
                if len(self.blockAccess)>0:  del self.blockAccess[0]
                return 

            swN     =   unicode(switchNumber)
            suffixN = suffix+u"_"+swN


            for MAC in self.MAC2INDIGO[xType]:
                if len(MAC) < 16:
                    self.MAC2INDIGO[xType][MAC][u"inList"+suffixN] = -1  # was not here   
                    continue
                try:
                    if self.MAC2INDIGO[xType][MAC][u"inList"+suffixN]  > 0:  # was here was here , need to test 
                        self.MAC2INDIGO[xType][MAC][u"inList"+suffixN] = 0   
                except:
                        indigo.server.log("error in doSWITCHdictClients: mac:"+ MAC+"  "+unicode(self.MAC2INDIGO[xType][MAC]) )
                        return 
                else:
                    self.MAC2INDIGO[xType][MAC][u"inList"+suffixN] = -1  # was not here   
                
         
            for port in portTable:
              
                ##indigo.server.log("port # "+ unicode(ii)+unicode(portTable[0:100])
                portN = unicode(port[u"port_idx"])
                if "mac_table" not in port: continue
                macTable =  port[u"mac_table"]
                if macTable == []:  continue
                if "port_idx" in port:
                    portN = unicode(port[u"port_idx"])
                else:
                    portN = ""
                isUpLink = False  
                isDownLink = False
                
                if "is_uplink"    in port and port["is_uplink"]:            isUpLink   = True
                elif "lldp_table" in port and len(port["lldp_table"]) > 0:  isDownLink = True

                #if isUpLink:          continue
                #if isDownLink:        continue

                for switchDevices in macTable:
                    MAC = switchDevices[u"mac"]
                    if self.testIgnoreMAC(MAC,"SW-Dict"): continue

                    if "age" in switchDevices:      age    = switchDevices[u"age"]
                    else: age = ""
                    if "ip" in switchDevices:       
                                                    ip     = switchDevices[u"ip"]
                                                    try:    self.MAC2INDIGO[xType][MAC][u"ipNumber"] = ip
                                                    except: continue
                    else:                           ip = ""
                    if "uptime" in switchDevices:   newUp  = unicode(switchDevices[u"uptime"])
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
                            if self.ML.decideMyLog(u"Logic") or MAC in self.MACloglist: self.ML.myLog( text=MAC + "  " + unicode(self.MAC2INDIGO[xType][MAC][u"devId"]) + " wrong " + devType)
                            for dev in indigo.devices.iter(self.pluginId):
                                if dev.deviceTypeId == "client":    continue
                                if dev.deviceTypeId != devType:     continue
                                if "MAC" not in dev.states:         continue
                                if dev.states[u"MAC"] != MAC:       continue
                                self.setupStructures(xType, dev, MAC, init=False)
                                self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
                                self.MAC2INDIGO[xType][MAC][u"inList"+suffixN] = 1
                                new = False
                                break

                    if not new:
                    
                        self.MAC2INDIGO[xType][MAC][u"inList"+suffixN] = 1
                        if self.ML.decideMyLog(u"Dict") or MAC in self.MACloglist: self.ML.myLog( text=ipNDevice +" "+ MAC+" "+ dev.name+"; IP:"+ip+"; AGE:"+unicode(age)+"; newUp:"+unicode(newUp)+ "; nameSW:"+unicode(nameSW), mType=u"DC-SW-00")


                        if not ( isUpLink or isDownLink ):  # only the direct switch can change the switch:port #s
                            poe="" 
                            if len(dev.states[u"AP"]) < 5: # do not look for POE for wifi devices
                                if MACSW in self.MAC2INDIGO["SW"]:  # do we know the switch
                                    if portN in self.MAC2INDIGO["SW"][MACSW][u"ports"]: # is the port in the switch 
                                        if u"poe" in self.MAC2INDIGO["SW"][MACSW][u"ports"][portN] and self.MAC2INDIGO["SW"][MACSW][u"ports"][portN][u"poe"]  !="": # if empty dont add "-"
                                            poe = "-"+self.MAC2INDIGO["SW"][MACSW][u"ports"][portN][u"poe"] 

                            newPort = swN+":"+portN+poe
                                
                            if dev.states[u"SW_Port"] != newPort:
                                self.addToStatesUpdateList(unicode(dev.id),u"SW_Port", newPort)

                        
                        props=dev.pluginProps

                        newd = False
                        devidd = unicode(dev.id)
                        if ip != "":
                            if dev.states[u"ipNumber"] != ip:
                                self.addToStatesUpdateList(unicode(dev.id),u"ipNumber", ip)
                            self.MAC2INDIGO[xType][MAC][u"ipNumber"] = ip
                        self.MAC2INDIGO[xType][MAC][u"age"+suffixN] = age
                        if dev.states[u"name"] != nameSW and nameSW !="":
                            self.addToStatesUpdateList(unicode(dev.id),u"name", nameSW)

                        newStatus = "up"
                        oldStatus = dev.states[u"status"]
                        oldUp     = self.MAC2INDIGO[xType][MAC][u"uptime" + suffixN]
                        self.MAC2INDIGO[xType][MAC][u"uptime" + suffixN]= unicode(newUp)
                        if "useWhatForStatus" in props and props[u"useWhatForStatus"] in ["SWITCH","OptDhcpSwitch"]:
                            if self.ML.decideMyLog(u"Dict") or MAC in self.MACloglist: self.ML.myLog( text=ipNDevice +" "+ MAC+" "+ dev.name+"; oldStatus:"+oldStatus+"; IP:"+ip+"; AGE:"+unicode(age)+"; newUp:"+unicode(newUp)+ "; oldUp:"+unicode(oldUp)+ "; nameSW:"+unicode(nameSW), mType=u"DC-SW-0")
                            if oldUp ==  newUp and oldStatus =="up":
                                if "useupTimeforStatusSWITCH" in props and props[u"useupTimeforStatusSWITCH"] :
                                    if  "usePingDOWN" in props and props["usePingDOWN"]  and status !="up" and self.testPing(dev.states["ipNumber"],nTries=1) == 0: 
                                        if self.ML.decideMyLog(u"DictDetails") or MAC in self.MACloglist: self.ML.myLog( text=u" "+ MAC+ u" reset timer for status up  notuptime const  but answers ping", mType=u"DC-SW-1")
                                        self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
                                    else:
                                        if self.ML.decideMyLog(u"DictDetails") or MAC in self.MACloglist: self.ML.myLog( text=u" "+ MAC+ u"   SW DICT network_table , Uptime not changed, continue expiration timer", mType=u"DC-SW-2")
                                else: # will only expired if not in list anymore 
                                    if  "usePingDOWN" in props and props["usePingDOWN"]  and status !="up" and self.testPing(dev.states["ipNumber"],nTries=1) != 0: 
                                        if self.ML.decideMyLog(u"DictDetails") or MAC in self.MACloglist: self.ML.myLog( text=u" "+ MAC+ u" SW DICT network_table , but does not answer pingg, continue expiration timer", mType=u"DC-SW-3")
                                    else:
                                        if self.ML.decideMyLog(u"DictDetails") or MAC in self.MACloglist: self.ML.myLog( text=u" "+ MAC+ u" reset timer for status up    answers ping in  DHCP list", mType=u"DC-SW-4")
                                        self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()


                            else:
                                if  "usePingUP" in props and props["usePingUP"]  and status !="up" and self.testPing(dev.states["ipNumber"],nTries=1) != 0: 
                                    if self.ML.decideMyLog(u"Dict") or MAC in self.MACloglist: self.ML.myLog( text=u" "+  MAC+  u" SW DICT network_table , but does not answer ping, continue expiration timer", mType=u"DC-SW-5")
                                else:
                                    self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
                                    if self.ML.decideMyLog(u"Dict") or MAC in self.MACloglist: self.ML.myLog( text=u" "+  MAC+u" SW DICT network_table  restart exp timer ", mType=u"DC-SW-6")
                            
                        if self.updateDescriptions:
                            oldIPX = dev.description.split("-")[0]
                            if ipx !="" and (oldIPX != ipx or ( (dev.description != ipx + "-" + nameSW or len(dev.description) < 5) and len(nameSW)> 0 and  (dev.description).find("=WiFi") ==-1 )) :
                                dev.description = ipx + "-" + nameSW
                                if self.ML.decideMyLog(u"DictDetails") or MAC in self.MACloglist: self.ML.myLog( text=u"updating description for "+dev.name+"  to   "+ dev.description, mType=u"DC-SW-7") 
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
                                folder=self.folderNameCreatedID,
                                props={u"useWhatForStatus":"SWITCH","useupTimeforStatusSWITCH":""})
 
                        except  Exception, e:
                            if len(unicode(e)) > 5:
                                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
                            continue

                        self.setupStructures(xType, dev, MAC)
                        self.addToStatesUpdateList(unicode(dev.id),u"SW_Port", "")
                        self.MAC2INDIGO[xType][MAC][u"age"+suffixN] = age
                        self.MAC2INDIGO[xType][MAC][u"uptime"+suffixN] = newUp
                        self.setupBasicDeviceStates(dev, MAC, xType, ip, "", "", u" status up         SWITCH DICT new Device", "STATUS-SW")
                        self.MAC2INDIGO[xType][MAC][u"inList"+suffixN] = 1

            self.doInList(suffixN)
            self.executeUpdateStatesList()



        except  Exception, e:
            if len(unicode(e)) > 5:
                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

        #if time.time()-waitT > 0.001: #indigo.server.log(unicode(self.blockAccess).ljust(28)+part.ljust(18)+"  exectime> %6.3f"%(time.time()-waitT)+ " @ "+datetime.datetime.now().strftime("%M:%S.%f")[:-3])
        if len(self.blockAccess)>0:  del self.blockAccess[0]

        return

    ####-----------------    ---------
    def doDHCPdictClients(self, gwDict):

        part="doDHCPdictClients"+unicode(random.random()); self.blockAccess.append(part)
        for ii in range(90):
                if len(self.blockAccess) == 0 or self.blockAccess[0] == part: break # my turn?
                self.sleep(0.1)   
        if ii >= 89: self.blockAccess = [] # for safety if too long reset list
        
        
        try:
            devType = u"UniFi"
            devName = u"UniFi"
            suffixN = u"DHCP"
            xType   = u"UN"

            ###########  do DHCP devices
            if "network_table" not in gwDict: 
                if self.ML.decideMyLog(u"Logic"): self.ML.myLog( text=u"network_table not in dict "+unicode(gwDict[u"network_table"])[0:100], mType=u"DC-DHCP-E0")
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
                    if self.ML.decideMyLog(u"Logic"): self.ML.myLog( text=u"no DHCP in gwateway ?.. skipping info "+unicode(gwDict[u"network_table"])[0:100], mType=u"DC-DHCP-E1")
                    return # DHCP not enabled on gateway, no info from GW available
               
            if "connect_request_ip" in gwDict:
                ipNumber = gwDict["connect_request_ip"]
            else:
                ipNumber = "            "
            ##indigo.server.log(" GW dict: lan0" + unicode(lan0)[:100])
            
            if self.ML.decideMyLog(u"DictDetails") or MAC in self.MACloglist: self.ML.myLog( text=u"host_table len:"+unicode(len(host_table))+"  "+unicode(host_table)[0:100], mType = "DC-DHCP-00")
            if len(host_table) > 0:
                for item in host_table:
                    
                    ##indigo.server.log(" nn: "+ unicode(nn)+"; lan: "+ unicode(lan)[0:200] )


                    if "ip" in item:  ip = item[u"ip"]
                    else:             ip = ""
                    MAC                  = item[u"mac"]
                    if self.testIgnoreMAC(MAC,"GW-Dict"): continue
                    age                  = item[u"age"]
                    uptime               = item[u"uptime"]
                    new                  = True
                    #indigo.server.log(" GW dict: network_table" + unicode(host_table)[:100])
                    if MAC in self.MAC2INDIGO[xType]:
                        try:
                            dev = indigo.devices[self.MAC2INDIGO[xType][MAC][u"devId"]]
                            if dev.deviceTypeId != devType: 1 / 0
                            # indigo.server.log(MAC+" "+ dev.name)
                            new = False
                            self.MAC2INDIGO[xType][MAC][u"inList" + suffixN] = 1
                        except:
                            if self.ML.decideMyLog(u"Logic") or MAC in self.MACloglist: self.ML.myLog( text=MAC + "  " + unicode(self.MAC2INDIGO[xType][MAC]) + " wrong " + devType)
                            for dev in indigo.devices.iter(self.pluginId):
                                if dev.deviceTypeId == "client": continue
                                if dev.deviceTypeId != devType: continue
                                if "MAC" not in dev.states: continue
                                if dev.states[u"MAC"] != MAC: continue
                                self.setupStructures(xType, dev, MAC, init=False)
                                self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
                                self.MAC2INDIGO[xType][MAC][u"inList" + suffixN] = 1 
                                new = False
                                break

                    if not new:
                            if self.ML.decideMyLog(u"DictDetails") or MAC in self.MACloglist: self.ML.myLog( text=ipNumber+" "+ MAC +" " + dev.name +" ip:" + ip + " age:" + unicode(age) + " uptime:" + unicode(uptime), mType = "DC-DHCP-0")
                                
                            self.MAC2INDIGO[xType][MAC][u"inList"+suffixN] = True
                                
                            props = dev.pluginProps
                            new = False
                            if MAC != dev.states[u"MAC"]:
                                self.addToStatesUpdateList(unicode(dev.id),u"MAC", MAC)
                            if ip != "": 
                                if ip != dev.states[u"ipNumber"]:
                                    self.addToStatesUpdateList(unicode(dev.id),u"ipNumber", ip)
                                self.MAC2INDIGO[xType][MAC][u"ipNumber"] = ip

                            newStatus = "up"
                            if "useWhatForStatus" in props and props[u"useWhatForStatus"] in ["DHCP","OptDhcpSwitch"]:

                                if "useAgeforStatusDHCP" in props and props[u"useAgeforStatusDHCP"] != "-1"  and float(age) > float( props[u"useAgeforStatusDHCP"]):
                                        if dev.states[u"status"] == "up":
                                            if "usePingDOWN" in props and props["usePingDOWN"] and self.testPing(dev.states["ipNumber"],nTries=1) == 0:  # did  answer
                                                if self.ML.decideMyLog(u"DictDetails") or MAC in self.MACloglist: self.ML.myLog( text=u" "+ MAC+ u" reset exptimer DICT network_table AGE>max, but answers ping " + unicode(props[u"useAgeforStatusDHCP"]), mType=u"DC-DHCP-1")
                                                self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
                                                newStatus = "up"
                                            else: 
                                                if self.ML.decideMyLog(u"DictDetails") or MAC in self.MACloglist: self.ML.myLog( text=u" "+ MAC+ u" set timer for status down    GW DICT network_table AGE>max:" + unicode(props[u"useAgeforStatusDHCP"]), mType=u"DC-DHCP-2")
                                                newStatus = "startDown"

                                else: # good data, should be up 
                                    if "usePingUP" in props and props["usePingUP"] and dev.states[u"status"] =="up" and self.testPing(dev.states["ipNumber"],nTries=1) == 1:  # did not answer
                                            self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time() - self.getexpT(props) # down immediately
                                            self.setImageAndStatus(dev, "down",oldStatus=dev.states[u"status"], ts=time.time(), level=1, text1= dev.name.ljust(30) + u"set timer for status down       ping does not answer", iType=u"DC-DHCP-4",reason=u"DICT "+suffixN+u" up")
                                            newStatus = "down"
                                    elif dev.states[u"status"] != "up":
                                            self.setImageAndStatus(dev, "up",oldStatus=dev.states[u"status"], ts=time.time(), level=1, text1= dev.name.ljust(30) + u" status up         GW DICT network_table", iType=u"DC-DHCP-4",reason=u"DICT "+suffixN+u" up")
                                            newStatus = "up"

                                if newStatus =="up":
                                    self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()

                            self.MAC2INDIGO[xType][MAC][u"age"+suffixN]     = age 
                            self.MAC2INDIGO[xType][MAC][u"uptime"+suffixN]  = uptime 

                            if self.updateDescriptions:
                                oldIPX = dev.description.split("-")
                                ipx = self.fixIP(ip)
                                if ipx!="" and oldIPX[0] != ipx:
                                    oldIPX[0] = ipx
                                    dev.description = "-".join(oldIPX)
                                    if self.ML.decideMyLog(u"DictDetails") or MAC in self.MACloglist: self.ML.myLog( text=u"updating description for "+dev.name+"  to   "+ dev.description) 
                                    dev.replaceOnServer()


                            #break
                    if new:
                        try:
                            dev = indigo.device.create(
                                protocol=indigo.kProtocol.Plugin,
                                address=MAC,
                                name=devName + "_" + MAC,
                                description=self.fixIP(ip),
                                pluginId=self.pluginId,
                                deviceTypeId=devType,
                                folder=self.folderNameCreatedID,
                                props={ "useWhatForStatus":"DHCP","useAgeforStatusDHCP": "-1","useWhatForStatusWiFi":""})
                        except  Exception, e:
                            if len(unicode(e)) > 5:
                                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
                            continue

                        self.setupStructures(xType, dev, MAC)
                        self.MAC2INDIGO[xType][MAC][u"age"+suffixN]         = age 
                        self.MAC2INDIGO[xType][MAC][u"uptime"+suffixN]      = uptime 
                        self.MAC2INDIGO[xType][MAC][u"inList"+suffixN]      = True
                        self.setupBasicDeviceStates(dev, MAC, xType, ip, "", "", u" status up         GW DICT  new device","DC-DHCP-3")



            ## now check if device is not in dict, if not ==> initiate status --> down
            self.doInList(suffixN)
            self.executeUpdateStatesList()


        except  Exception, e:
                    if len(unicode(e)) > 5:
                        indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        if len(self.blockAccess)>0:  del self.blockAccess[0]
        return




    ####-----------------    ---------
    def doWiFiCLIENTSdict(self,adDict, GHz, ipNDevice,apN):

        part="doWiFiCLIENTSdict"+unicode(random.random()); self.blockAccess.append(part)
        for ii in range(90):
                if len(self.blockAccess) == 0 or self.blockAccess[0] == part: break # my turn?
                self.sleep(0.1)   
        if ii >= 89: self.blockAccess = [] # for safety if too long reset list

        if len(adDict) ==0:
            if len(self.blockAccess)>0:  del self.blockAccess[0]
            return
            
        if self.ML.decideMyLog(u"Dict") : self.ML.myLog( text=unicode(adDict)[0:100] + "...." ,mType=u"DC-WF---")
        try:
            devType = "UniFi"
            devName = "UniFi"
            suffixN = "WiFi"
            xType   = u"UN"
            #self.ML.myLog( text=u"DictDetails", ipNDevice + " GHz" +GHz, mType=u"DICT-WiFi")
            for MAC in self.MAC2INDIGO[xType]:
                if self.MAC2INDIGO[xType][MAC][u"AP"]  != ipNDevice: continue
                if self.MAC2INDIGO[xType][MAC][u"GHz"] != GHz:       continue
                for MAC in self.MAC2INDIGO[xType]:
                    self.MAC2INDIGO[xType][MAC][u"inList"+suffixN] = 0
                    

            for ii in range(len(adDict)):
              
                new             = True
                MAC             = unicode(adDict[ii][u"mac"])
                if self.testIgnoreMAC(MAC,"WF-Dict"): continue
                ip              = unicode(adDict[ii][u"ip"])
                txRate          = unicode(adDict[ii][u"tx_rate"])
                rxRate          = unicode(adDict[ii][u"rx_rate"])
                rxtx            = rxRate+"/"+txRate+" [Kb]"
                signal          = unicode(adDict[ii][u"signal"])
                noise           = unicode(adDict[ii][u"noise"])
                idletime        = unicode(adDict[ii][u"idletime"])
                try:state       = format(int(adDict[ii][u"state"]), '08b')  ## not in controller 
                except: state   =""
                newUpTime       = unicode(adDict[ii][u"uptime"])
                try:
                    nameCl      = unicode(adDict[ii][u"hostname"]).strip()
                except:
                    nameCl      = ""
                powerMgmt = unicode(adDict[ii][u"state_pwrmgt"])
                ipx = self.fixIP(ip)
                #if  MAC == "54:9f:13:3f:95:25":
                #self.ML.myLog( text=u"DictDetails", ipNDevice+" checking MAC in dict "+MAC  ,mType=u"DICT-WiFi")

                if MAC in self.MAC2INDIGO[xType]:
                    try:
                        dev = indigo.devices[self.MAC2INDIGO[xType][MAC][u"devId"]]
                        if dev.deviceTypeId != devType: 1/0
                        #indigo.server.log(MAC+" "+ dev.name)
                        new = False
                        self.MAC2INDIGO[xType][MAC][u"AP"]         = ipNDevice
                        self.MAC2INDIGO[xType][MAC][u"inList" + suffixN] = 1 
                        self.MAC2INDIGO[xType][MAC][u"GHz"]        = GHz
                    except:
                        if self.ML.decideMyLog(u"Logic") or MAC in self.MACloglist: self.ML.myLog( text=MAC + "  " + unicode(self.MAC2INDIGO[xType][MAC]) + " wrong " + devType)
                        for dev in indigo.devices.iter(self.pluginId):
                            if dev.deviceTypeId == "client": continue
                            if dev.deviceTypeId != devType: continue
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
                        if self.ML.decideMyLog(u"DictDetails") or MAC in self.MACloglist:
                            self.ML.myLog( text=(ipNDevice +" " + MAC + " " + dev.name +  " GHz:" + GHz + " ip:" + ip +
                                            "  txRate:" + txRate + " rxRate:" + rxRate+ " uptime:" + newUpTime +
                                            "  signal:" + signal + "  name:" + nameCl + "  powerMgmt:" + powerMgmt), mType=u"DC-WF-NN")
                        devidd = unicode(dev.id)

                        oldAssociated =  dev.states[u"AP"].split("-")[0]   
                        newAssociated =  ipNDevice
                        try:     oldIdle =  int(self.MAC2INDIGO[xType][MAC][u"idleTime" + suffixN])
                        except:  oldIdle = 0

                        # this is for the case when device switches betwen APs and the old one is still sending.. ignore that one 
                        if dev.states[u"AP"].split("-")[0] != ipNDevice: 
                            try: 
                                if oldIdle < 600 and  int(idletime) > oldIdle: continue # oldIdle <600 is to catch expired devices
                            except:
                                pass
                        
                        if dev.states[u"AP"]!= ipNDevice+"-#"+unicode(apN):
                            self.addToStatesUpdateList(unicode(dev.id),u"AP", ipNDevice+"-#"+unicode(apN))

                        self.MAC2INDIGO[xType][MAC][u"inList"+suffixN] = 1
                            
                        if ip != "": 
                            if dev.states[u"ipNumber"] != ip:
                                self.addToStatesUpdateList(unicode(dev.id),u"ipNumber", ip)
                            self.MAC2INDIGO[xType][MAC][u"ipNumber"] = ip
                            
                        if dev.states[u"name"] != nameCl and nameCl !="":
                            self.addToStatesUpdateList(unicode(dev.id),u"name", nameCl)
                            
                        if dev.states[u"GHz"] != GHz:
                            self.addToStatesUpdateList(unicode(dev.id),u"GHz", GHz)
                            
                        if dev.states[u"powerMgmt"+suffixN] != powerMgmt:
                            self.addToStatesUpdateList(unicode(dev.id),u"powerMgmt"+suffixN, powerMgmt)
                            
                        if dev.states[u"rx_tx_Rate"+suffixN] != rxtx:
                            self.addToStatesUpdateList(unicode(dev.id),u"rx_tx_Rate"+suffixN, rxtx)
                            
                        if dev.states[u"noise"+suffixN] != noise:
                            uD = True
                            try: 
                                if abs(int(dev.states[u"noise"+suffixN])- int(noise)) < 3:
                                    uD=  False
                            except: pass
                            if uD: self.addToStatesUpdateList(unicode(dev.id),u"noise"+suffixN, noise)

                        if dev.states[u"signal"+suffixN] != signal:
                            uD = True
                            try: 
                                if abs(int(dev.states[u"signal"+suffixN])- int(signal)) < 3:
                                    uD=  False
                            except: pass
                            if uD: self.addToStatesUpdateList(unicode(dev.id),u"signal"+suffixN, signal)

                        try:    oldUpTime = unicode(int(self.MAC2INDIGO[xType][MAC][u"uptime"+suffixN]))
                        except: oldUpTime = "0"
                        self.MAC2INDIGO[xType][MAC][u"uptime"+suffixN] = newUpTime
                            
                        if dev.states[u"state" + suffixN] != state:
                            self.addToStatesUpdateList(unicode(dev.id),u"state" + suffixN, state)
                            
                        if dev.states[u"AP"].split("-")[0] != ipNDevice:
                            self.addToStatesUpdateList(unicode(dev.id),u"AP", ipNDevice+"-#"+unicode(apN) )
                            
                        if idletime != "":
                            self.MAC2INDIGO[xType][MAC][u"idleTime" + suffixN] =  idletime

                        oldStatus = dev.states[u"status"]
                           
                        if self.updateDescriptions:  
                            oldDescr = dev.description.split("-")
                            oldIPX   = oldDescr[0]
                            if oldIPX != ipx or (dev.description != ipx + "-" + nameCl+"=WiFi" or len(dev.description) < 5):
                                if len(oldDescr) < 2:
                                    oldDescr.append(nameCl.strip("-"))
                                elif len(oldDescr) == 2 and oldDescr[1] == "":
                                    if nameCl != "":
                                        oldDescr[1] = nameCl.strip("-")
                                oldDescr[0] = ipx
                                newDescr = "-".join(oldDescr)
                                if (dev.description).find("=WiFi")==-1:
                                    dev.description = newDescr+"=WiFi"
                                else:
                                    dev.description = newDescr
                                dev.replaceOnServer()
                            
                        # check what is used to determine up / down, make WiFi a priority
                        if ( "useWhatForStatus" not in  props ) or ( "useWhatForStatus"  in props and props[u"useWhatForStatus"] != "WiFi" ):
                            try:
                                if time.time() - time.mktime(datetime.datetime.strptime(dev.states[u"created"], "%Y-%m-%d %H:%M:%S").timetuple()) <  60:
                                    props = dev.pluginProps
                                    props[u"useWhatForStatus"]      = "WiFi"
                                    props[u"useWhatForStatusWiFi"]  = "Optimized"
                                    dev.replacePluginPropsOnServer(props)
                                    props = dev.pluginProps
                            except:
                                self.addToStatesUpdateList(unicode(dev.id),u"created", datetime.datetime.now().strftime(u"%Y-%m-%d %H:%M:%S"))
                                props = dev.pluginProps
                                props[u"useWhatForStatus"]      = "WiFi"
                                props[u"useWhatForStatusWiFi"]  = "Optimized"
                                dev.replacePluginPropsOnServer(props)
                                props = dev.pluginProps

                        if "useWhatForStatus" in props and props[u"useWhatForStatus"] == "WiFi":

                            if "useWhatForStatusWiFi" not in props or ("useWhatForStatusWiFi" in props and  props[u"useWhatForStatusWiFi"] !="FastDown"):

                                try:     newUpTime = int(newUpTime)
                                except:  newUpTime = int(oldUpTime)
                                try:
                                    idleTimeMaxSecs  = float(props[u"idleTimeMaxSecs"])
                                except:
                                    idleTimeMaxSecs = 5
                                if self.ML.decideMyLog(u"Logic") or MAC in self.MACloglist: self.ML.myLog( text=ipNDevice +" "+MAC+" "+ dev.name+"newUpTime:"+unicode(newUpTime)+"  oldUpTime:"+ unicode(oldUpTime)+"  idletime:"+ unicode(idletime)+"  idleTimeMaxSecs:"+unicode(idleTimeMaxSecs)+"  old/new associated "+unicode(oldAssociated.split("-")[0])+"/"+unicode(newAssociated), mType=u"DC-WF-0"  )


                                if "useWhatForStatusWiFi" in props and ( props[u"useWhatForStatusWiFi"] =="Optimized"):

                                    if oldStatus == "up":
                                        expT =self.getexpT(props)
                                        if (  float(newUpTime) != float(oldUpTime)  ) or  (  float(idletime)  < idleTimeMaxSecs  ):
                                                if self.ML.decideMyLog(u"Logic") or MAC in self.MACloglist: self.ML.myLog( text=u" "+MAC+" "+dev.name.ljust(30) + u" reset exptimer   WiFi DICT use idle...= ", mType=u"DC-WF-O3")
                                                self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
                                        else:
                                            if ( oldAssociated.split("-")[0] != newAssociated ): # ignore new AP
                                                if self.ML.decideMyLog(u"Logic") or MAC in self.MACloglist: self.ML.myLog( text=u" "+MAC+" "+dev.name.ljust(30) + u" reset exptimer, new AP  WiFi DICT", mType=u"DC-WF-O3")
                                                self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time() 
                                            else: # same old 
                                                if self.ML.decideMyLog(u"Logic") or MAC in self.MACloglist: self.ML.myLog( text=u" "+MAC+" "+dev.name.ljust(30) + u" set timer to expire   WiFi DICT use idle...= ", mType=u"DC-WF-O3")
                                                #self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time() - expT
                                                self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()- self.getexpT(props) + 10

                                    else: # old = down
                                        if ( float(newUpTime) != float(oldUpTime) ) or  (  float(idletime)  <= idleTimeMaxSecs  ):
                                            self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
                                            self.setImageAndStatus(dev, "up",oldStatus=oldStatus,ts=time.time(),reason=u"DICT "+suffixN+u" "+ipNDevice+u" up Optimized")
                                            if self.ML.decideMyLog(u"Logic") or MAC in self.MACloglist: self.ML.myLog( text=u" "+MAC+" "+dev.name.ljust(30) + u" status up     WiFi DICT use idle", mType=u"DC-WF-O4")
                                        else: 
                                            if ( oldAssociated.split("-")[0] != newAssociated ): # ignore new AP
                                                if self.ML.decideMyLog(u"Logic") or MAC in self.MACloglist: self.ML.myLog( text=u" "+MAC+" "+dev.name.ljust(30) + u" status up  new AP   WiFi DICT use idle", mType=u"DC-WF-O4")
                                                self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()


                                elif "useWhatForStatusWiFi" in props and (props[u"useWhatForStatusWiFi"] =="IdleTime" ):
                                    if self.ML.decideMyLog(u"Logic") or MAC in self.MACloglist: self.ML.myLog( text=u" "+MAC+" "+ dev.name+u" IdleTime..  checking IdleTime/max: "+unicode(idletime)+"/"+props[u"idleTimeMaxSecs"] +"  old/new associated "+unicode(oldAssociated.split("-")[0])+"/"+unicode(newAssociated), mType=u"DC-WF-ID")
                                    try:
                                        idleTimeMaxSecs  = float(props[u"idleTimeMaxSecs"])
                                    except:
                                        idleTimeMaxSecs = 5

                                    if float(idletime)  > idleTimeMaxSecs and oldStatus == "up":
                                        if ( oldAssociated.split("-")[0] == newAssociated ):
                                            if "usePingDOWN" in props and props["usePingDOWN"] and self.testPing(dev.states["ipNumber"],nTries=1) ==0: 
                                                    if self.ML.decideMyLog(u"Logic"): self.ML.myLog( text=u"  "+dev.states[u"MAC"]+"  reset exptimer  - , ping test ok" ,mType="DC-WF-I1")
                                                    self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
                                            else:
                                                self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()- self.getexpT(props) + 10
                                        else: 
                                            if self.ML.decideMyLog(u"Logic") or MAC in self.MACloglist: self.ML.myLog( text=u" "+MAC+" "+dev.name.ljust(30) + u" status up  new AP   WiFi DICT use idle", mType=u"DC-WF-I5")
                                            self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()

                                    elif float(idletime)  <= idleTimeMaxSecs:
                                        if self.ML.decideMyLog(u"Logic") or MAC in self.MACloglist: self.ML.myLog( text=u" "+MAC+" "+dev.name.ljust(30) + u" reset exptimer      WiFi DICT use idle< max: "+unicode(idletime), mType=u"DC-WF-I3")
                                        self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
                                        if oldStatus != "up":
                                            self.setImageAndStatus(dev, "up",oldStatus=oldStatus,ts=time.time(),reason=u"DICT "+ipNDevice+u" "+suffixN+u" up idle-time")
                                            if self.ML.decideMyLog(u"Logic") or MAC in self.MACloglist: self.ML.myLog( text=u" "+MAC+" "+dev.name.ljust(30) + u" status up     WiFi DICT use idle", mType=u"DC-WF-I4")


                                elif "useWhatForStatusWiFi" in props and (props[u"useWhatForStatusWiFi"] == "UpTime" ):
                                    if newUpTime == oldUpTime and oldStatus == "up":
                                        if "usePingUP" in props and props["usePingUP"] and status !="up" and self.testPing(dev.states["ipNumber"],nTries=1) == 0: 
                                                if self.ML.decideMyLog(u"Logic") or MAC in self.MACloglist: self.ML.myLog( text=u" "+dev.states[u"MAC"]+" reset exptimer  , ping test ok" ,mType="DC-WF-UT")
                                                self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
                                        #self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time() - self.getexpT(props)
                                        else:
                                            if self.ML.decideMyLog(u"Logic") or MAC in self.MACloglist: self.ML.myLog( text=u" "+MAC+" "+dev.name.ljust(30) + u" set timer for status down     WiFi DICT use Uptime same ", mType=u"DC-WF-U1")

                                    elif newUpTime != oldUpTime and oldStatus != u"up":
                                        self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
                                        self.setImageAndStatus(dev, u"up",oldStatus=oldStatus, ts=time.time(), level=1, text1=dev.name.ljust(30) + " "+MAC+u" status up     WiFi DICT use uptime",iType=u"DC-WF-U2",reason=u"DICT "+ipNDevice+u" "+suffixN+u" up time")

                                    elif oldStatus == u"up":
                                        if self.ML.decideMyLog(u"Logic") or MAC in self.MACloglist: self.ML.myLog( text=u" "+dev.states[u"MAC"]+" reset exptimer  , normal extension" ,mType="DC-WF-U3")
                                        self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()


                                else:
                                    self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
                                    if oldStatus != "up":
                                        self.setImageAndStatus(dev, "up", oldStatus=oldStatus,level=1, text1=dev.name.ljust(30) + " "+MAC+u" status up     WiFi DICT general", iType=u"DC-WF-UE",reason=u"DICT "+suffixN+u" "+ipNDevice+u" up else")
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
                            folder=self.folderNameCreatedID,
                            props={u"useWhatForStatus":u"WiFi", u"useWhatForStatusWiFi":u"Expiration"})
                    except  Exception, e:
                        if len(unicode(e)) > 5:
                            indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
                        try:
                            devName += u"_"+( unicode(time.time() - int(time.time())) ).split(".")[1] # create random name 
                            indigo.server.log(u"trying again to create device with differnt name "+devName)
                            dev = indigo.device.create(
                                protocol=indigo.kProtocol.Plugin,
                                address=MAC,
                                name=devName + u"_" + MAC,
                                description=ipx + u"-" + nameCl+"=Wifi",
                                pluginId=self.pluginId,
                                deviceTypeId=devType,
                                folder=self.folderNameCreatedID,
                                props={u"useWhatForStatus":u"WiFi", u"useWhatForStatusWiFi":u"Expiration"})
                        except  Exception, e:
                            if len(unicode(e)) > 5:
                                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
                            continue


                    self.setupStructures(xType, dev, MAC)
                    self.setupBasicDeviceStates(dev, MAC, xType, ip, ipNDevice, "", u" status up         WiFi DICT new Device", "DC-AP-WiF-f")
                    self.addToStatesUpdateList(unicode(dev.id),u"AP", ipNDevice+"-#"+unicode(apN))
                    self.addToStatesUpdateList(unicode(dev.id),u"powerMgmt"+suffixN, powerMgmt)
                    self.addToStatesUpdateList(unicode(dev.id),u"name", nameCl)
                    self.addToStatesUpdateList(unicode(dev.id),u"rx_tx_Rate" + suffixN, rxtx)
                    self.addToStatesUpdateList(unicode(dev.id),u"signal" + suffixN, signal)
                    self.addToStatesUpdateList(unicode(dev.id),u"noise" + suffixN, noise)
                    self.MAC2INDIGO[xType][MAC][u"idleTime" + suffixN] = idletime
                    self.MAC2INDIGO[xType][MAC][u"inList"+suffixN] = 1
                    self.addToStatesUpdateList(unicode(dev.id),u"state"+suffixN, state)
                    self.MAC2INDIGO[xType][MAC][u"uptime"+suffixN] = newUpTime 

                
            self.doInList(suffixN,wifiIP=ipNDevice)
            self.executeUpdateStatesList()

        except  Exception, e:
            if len(unicode(e)) > 5:
                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

        #if time.time()-waitT > 0.001: #indigo.server.log(unicode(self.blockAccess).ljust(28)+part.ljust(18)+"  exectime> %6.3f"%(time.time()-waitT)+ " @ "+datetime.datetime.now().strftime("%M:%S.%f")[:-3])
        if len(self.blockAccess)>0:  del self.blockAccess[0]
        return



    ####-----------------    ---------
    ## AP devices themselves  DICT
    ####-----------------    ---------
    def doAPdictsSELF(self,apDict, apInd, apNumb, channel, GHz, ipNDevice, MAC, hostname):
    
        part="doAPdictsSELF"+unicode(random.random()); self.blockAccess.append(part)
        for ii in range(90):
                if len(self.blockAccess) == 0 or self.blockAccess[0] == part: break # my turn?
                self.sleep(0.1)   
        if ii >= 89: self.blockAccess = [] # for safety if too long reset list

        if "model_display" in apDict:  model = (apDict[u"model_display"])
        else:     
            self.ML.myLog( text=u"model_display not in dict doAPdicts") 
            model = ""
            
        shortC  = apDict[u"vap_table"][apInd]
    
        devType ="Device-AP"
        devName ="AP"
        xType   = "AP"
        try:
              
                nStations = unicode(shortC[u"num_sta"])
                essid = unicode(shortC[u"essid"])
                radio = unicode(shortC[u"radio"])
                tx_power = unicode(shortC[u"tx_power"])
                
                new = True
                if MAC in self.MAC2INDIGO[xType]:
                    try:
                        dev = indigo.devices[self.MAC2INDIGO[xType][MAC]["devId"]]
                        if dev.deviceTypeId != devType: 1 / 0
                        #indigo.server.log(MAC + " " + dev.name)
                        new = False
                    except:
                        if self.ML.decideMyLog(u"Logic"): self.ML.myLog( text=MAC + "  " + unicode(self.MAC2INDIGO[xType][MAC]) + " wrong " + devType)
                        for dev in indigo.devices.iter(self.pluginId):
                            if dev.deviceTypeId == "client": continue
                            if "MAC" not in dev.states: continue
                            if dev.states[u"MAC"] != MAC: continue
                            self.MAC2INDIGO[xType][MAC][u"devId"] = dev.id
                            new = False
                            break
                if not new:
                        if self.ML.decideMyLog(u"DictDetails") or MAC in self.MACloglist: self.ML.myLog( text=ipNDevice + " hostname:" + hostname + " MAC:" + MAC + " GHz:" + GHz + "  essid:" + essid + " channel:" + channel + "  nStations:" + nStations + "  tx_power:" + tx_power + "  radio:" + radio ,mType=u"DC-AP---")
                        if u"uptime" in apDict and apDict[u"uptime"] !="":         
                            if u"upSince" in dev.states:
                                self.addToStatesUpdateList(unicode(dev.id),u"upSince", time.strftime("%Y-%d-%m %H:%M:%S", time.localtime(time.time() - apDict[u"uptime"])) )
                        if channel != dev.states[u"tx_power_" + GHz]:
                            self.addToStatesUpdateList(unicode(dev.id),u"tx_power_" + GHz, tx_power)
                        if channel != dev.states[u"channel_" + GHz]:
                            self.addToStatesUpdateList(unicode(dev.id),u"channel_" + GHz, channel)
                        if channel != dev.states[u"essid_" + GHz]:
                            self.addToStatesUpdateList(unicode(dev.id),u"essid_" + GHz, essid)
                        if nStations != dev.states[u"nStations_" + GHz]:
                            self.addToStatesUpdateList(unicode(dev.id),u"nStations_" + GHz, nStations)
                        if radio != dev.states[u"radio_" + GHz]:
                            self.addToStatesUpdateList(unicode(dev.id),u"radio_" + GHz, radio)
                        self.MAC2INDIGO[xType][MAC][u"ipNumber"] = ipNDevice
                        if ipNDevice != dev.states[u"ipNumber"]:
                            self.addToStatesUpdateList(unicode(dev.id),u"ipNumber", ipNDevice)
                        if hostname != dev.states[u"hostname"]:
                            self.addToStatesUpdateList(unicode(dev.id),u"hostname", hostname)
                        if dev.states[u"status"] != "up":
                            self.setImageAndStatus(dev, "up", oldStatus=dev.states[u"status"],ts=time.time(),  level=1, text1=dev.name.ljust(30) + u" status up         AP  DICT", iType=u"STATUS-AP")
                        self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
                        if dev.states[u"model"] != model and model !="":
                            self.addToStatesUpdateList(unicode(dev.id),u"model", model)
                        if dev.states[u"apNo"] != apNumb:
                            self.addToStatesUpdateList(unicode(dev.id),u"apNo", apNumb)

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
                            folder=self.folderNameCreatedID,
                            props={u"useWhatForStatus":""})
                        self.setupStructures(xType, dev, MAC)
                        self.setupBasicDeviceStates(dev, MAC, "AP", ipNDevice,"", "", u" status up         AP DICT  new AP", u"STATUS-AP")
                        self.addToStatesUpdateList(unicode(dev.id),u"essid_" + GHz, essid)
                        self.addToStatesUpdateList(unicode(dev.id),u"channel_" + GHz, channel)
                        self.addToStatesUpdateList(unicode(dev.id),u"MAC", MAC)
                        self.addToStatesUpdateList(unicode(dev.id),u"hostname", hostname)
                        self.addToStatesUpdateList(unicode(dev.id),u"nStations_" + GHz, nStations)
                        self.addToStatesUpdateList(unicode(dev.id),u"radio_" + GHz, radio)
                        self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
                        self.addToStatesUpdateList(unicode(dev.id),u"model", model)
                        self.addToStatesUpdateList(unicode(dev.id),u"tx_power_" + GHz, tx_power)
                    except  Exception, e:
                      if len(unicode(e)) > 5:
                            indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
                self.executeUpdateStatesList()

        except  Exception, e:
            if len(unicode(e)) > 5:
                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

        #if time.time()-waitT > 0.001: #indigo.server.log(unicode(self.blockAccess).ljust(28)+part.ljust(18)+"  exectime> %6.3f"%(time.time()-waitT)+ " @ "+datetime.datetime.now().strftime("%M:%S.%f")[:-3])
        if len(self.blockAccess)>0:  del self.blockAccess[0]
        return




    ####-----------------    ---------
    def doGatewaydictSELF(self, gwDict):
    
        part="doGatewaydict"+unicode(random.random()); self.blockAccess.append(part)
        for ii in range(90):
                if len(self.blockAccess) == 0 or self.blockAccess[0] == part: break # my turn?
                self.sleep(0.1)   
        if ii >= 89: self.blockAccess = [] # for safety if too long reset list
    
        try:

            devType = "gateway"
            devName = "gateway"
            xType   = u"GW"
            suffixN  = "DHCP"
            ##########  do gateway params  ###
            #indigo.server.log(" GW dict if_table:"+json.dumps(gwDict, sort_keys=True, indent=2 ) )

            if "if_table" not in gwDict: return
            wan = gwDict[u"if_table"][0]
            for kk in gwDict[u"if_table"]:
                if "gateways" in kk and len(kk["gateways"]) > 2:
                    wan = kk
                    break
            MAC = wan[u"mac"]


            #  get lan info ------
            if True:
                lanPort     = -1 
                ipNDevice   = ""
                MAClan      = ""
                if "connect_request_ip" in gwDict:
                    ipNDevice = gwDict["connect_request_ip"]

                if ipNDevice == "":
                    if "config_port_table" in gwDict:
                        for xx in range(len(gwDict["config_port_table"])):
                            if "name" in gwDict["config_port_table"][xx] and gwDict["config_port_table"][xx]["name"] =="lan":
                                lanPort = xx
                                break

                for xx in range(len(gwDict[u"if_table"])):
                    lan = gwDict[u"if_table"][xx]
                    if ipNDevice !="":
                        if "ip" in lan and ipNDevice == lan[u"ip"]:
                            MAClan   = lan[u"mac"]
                            break
                    elif lanPort > -1 and lanPort == xx and "gateways" not in lan:
                        if "ip" in lan:                 
                            ipNDevice    = lan[u"ip"]
                            MAClan = lan[u"mac"]
                            break
                    elif xx == 1:
                        if "ip" in lan:
                            ipNDevice   = lan[u"ip"]
                            MAClan      = lan[u"mac"]
                            break

                ipNDevice = self.fixIP(ipNDevice)

            if "ip" in wan:                 publicIP    = wan[u"ip"].split("/")[0]
            else:                           publicIP    = ""
            if "speedtest_ping" in wan:     pingTime    = "%4.1f" % wan[u"speedtest_ping"] + u"[ms]"
            else:                           pingTime    = ""
            if "latency" in wan:            latency     = "%4.1f" % wan[u"latency"] + u"[ms]"
            else:                           latency     = ""
            if "xput_down" in wan:          download    = "%4.1f" % wan[u"xput_down"] + u"[Mb/S]"
            else:                           download    = ""
            if "xput_up" in wan:            upload      = "%4.1f" % wan[u"xput_up"] + u"[Mb/S]"
            else:                           upload      = ""
            if "nameservers" in wan:        nameservers = "-".join(wan[u"nameservers"])
            else:                           nameservers = "-"
            if "gateways" in wan:           gateways    = "-".join(wan[u"gateways"])
            else:                           gateways    = "-"
            if "speedtest_lastrun" in wan:  runDate     = datetime.datetime.fromtimestamp(float(wan[u"speedtest_lastrun"])).strftime(u"%Y-%m-%d %H:%M:%S") + u"[UTC]"
            else:                           runDate     = ""
            if "model_display" in gwDict:   model       = gwDict[u"model_display"]
            else:                           
                self.ML.myLog( text=u"model_display not in dict doGatewaydict") 
                model = ""



            new = True
          
            if MAC in self.MAC2INDIGO[xType]:
                try:
                    dev = indigo.devices[self.MAC2INDIGO[xType][MAC]["devId"]]
                    if dev.deviceTypeId != devType: 1 / 0
                    #indigo.server.log(MAC + " " + dev.name)
                    new = False
                except:
                    if self.ML.decideMyLog(u"Logic") or MAC in self.MACloglist: self.ML.myLog( text=MAC + "  " + unicode(self.MAC2INDIGO[xType][MAC]) + " wrong " + devType)
                    for dev in indigo.devices.iter(self.pluginId):
                        if dev.deviceTypeId == "client":    continue
                        if dev.deviceTypeId != devType:     continue
                        if "MAC" not in dev.states:         continue
                        if dev.states[u"MAC"] != MAC:       continue
                        self.MAC2INDIGO[xType][MAC]["devId"] = dev.id
                        new = False
                        break

            if not new:
                    if u"uptime" in gwDict and gwDict[u"uptime"] !="":         
                        if u"upSince" in dev.states:
                            self.addToStatesUpdateList(unicode(dev.id),u"upSince",  time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()-gwDict[u"uptime"])) )

                    self.MAC2INDIGO[xType][MAC][u"ipNumber"] = ipNDevice
                    if MAClan != dev.states[u"MAClan"]:
                        self.addToStatesUpdateList(unicode(dev.id),u"MAClan", MAClan)
                    if ipNDevice != dev.states[u"ipNumber"]:
                        self.addToStatesUpdateList(unicode(dev.id),u"ipNumber", ipNDevice)
                    if pingTime != dev.states[u"pingTime"]:
                        self.addToStatesUpdateList(unicode(dev.id),u"pingTime", pingTime)
                    if latency != dev.states[u"latency"]:
                        self.addToStatesUpdateList(unicode(dev.id),u"latency", latency)
                    if publicIP != dev.states[u"publicIP"]:
                        self.addToStatesUpdateList(unicode(dev.id),u"publicIP", publicIP)
                    if gateways != dev.states[u"gateways"]:
                        self.addToStatesUpdateList(unicode(dev.id),u"gateways", gateways)
                    if upload != dev.states[u"upload"]:
                        self.addToStatesUpdateList(unicode(dev.id),u"upload", upload)
                    if upload != dev.states[u"runDate"]:
                        self.addToStatesUpdateList(unicode(dev.id),u"runDate", runDate)
                    if download != dev.states[u"download"]:
                        self.addToStatesUpdateList(unicode(dev.id),u"download", download)
                    if nameservers != dev.states[u"nameservers"]:
                        self.addToStatesUpdateList(unicode(dev.id),u"nameservers", nameservers)
                    if dev.states[u"status"] != "up":
                        self.setImageAndStatus(dev, "up",oldStatus=dev.states[u"status"], ts=time.time(), level=1, text1=dev.name.ljust(30) + u" status up         GW DICT if_table", iType=u"STATUS-GW")

                    if self.ML.decideMyLog(u"Dict") or MAC in self.MACloglist: self.ML.myLog( text=MAC + "  ip:"+ ipNDevice+"  "+ dev.name +"  new data" ,mType=u"DC-GW-1")

                    self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
                    if dev.states[u"MAC"] != MAC:
                        self.addToStatesUpdateList(unicode(dev.id),u"MAC", MAC)
                    if dev.states[u"model"] != model and model != "":
                        self.addToStatesUpdateList(unicode(dev.id),u"model", model)

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
                        folder=self.folderNameCreatedID,
                        props={u"useWhatForStatus":""})
                    self.setupStructures(xType, dev, MAC)
                    self.addToStatesUpdateList(unicode(dev.id),u"MAClan", MAClan)
                    self.addToStatesUpdateList(unicode(dev.id),u"pingTime", pingTime)
                    self.addToStatesUpdateList(unicode(dev.id),u"latency", latency)
                    self.addToStatesUpdateList(unicode(dev.id),u"gateways", gateways)
                    self.addToStatesUpdateList(unicode(dev.id),u"upload", upload)
                    self.addToStatesUpdateList(unicode(dev.id),u"download", download)
                    self.addToStatesUpdateList(unicode(dev.id),u"runDate", runDate)
                    self.addToStatesUpdateList(unicode(dev.id),u"nameservers", nameservers)
                    self.setupBasicDeviceStates(dev, MAC, xType, ipNDevice, "", "", u" status up         GW DICT new gateway if_table", u"STATUS-GW")
                except  Exception, e:
                    if len(unicode(e)) > 5:
                        indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
            self.executeUpdateStatesList()



        except  Exception, e:
            if len(unicode(e)) > 5:
                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

        #if time.time()-waitT > 0.001: #indigo.server.log(unicode(self.blockAccess).ljust(28)+part.ljust(18)+"  exectime> %6.3f"%(time.time()-waitT)+ " @ "+datetime.datetime.now().strftime("%M:%S.%f")[:-3])
        if len(self.blockAccess)>0:  del self.blockAccess[0]
        return



    ####-----------------    ---------
    def doNeighborsdict(self,apDict,apNumb,ipNDevice):
    
    
        part="doNeighborsdict"+unicode(random.random()); self.blockAccess.append(part)
        for ii in range(90):
                if len(self.blockAccess) == 0 or self.blockAccess[0] == part: break # my turn?
                self.sleep(0.1)   
        if ii >= 89: self.blockAccess = [] # for safety if too long reset list
    
    
    
        try:
            devType =u"neighbor"
            devName =u"neighbor"
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
                            if self.ML.decideMyLog(u"Logic") or MAC in self.MACloglist: self.ML.myLog( text=MAC + "  " + unicode(self.MAC2INDIGO[xType][MAC]) + " wrong " + devType)
                            for dev in indigo.devices.iter(self.pluginId):
                                if dev.deviceTypeId == "client": continue
                                if dev.deviceTypeId != devType: continue
                                if "MAC" not in dev.states: continue
                                if dev.states[u"MAC"] != MAC: continue
                                self.setupStructures(xType, dev, MAC, init=False)
                                new = False
                                break
                    if not new:
                            self.MAC2INDIGO[xType][MAC][u"ipNumber"] = ipNDevice
                            if self.ML.decideMyLog(u"DictDetails") or MAC in self.MACloglist: self.ML.myLog( text=ipNDevice+ " MAC: " + MAC + " GHz:" + GHz + "  essid:" + essid + " channel:" + channel ,mType=u"DC-NEIG-0")
                            if MAC != dev.states[u"MAC"]:
                                self.addToStatesUpdateList(unicode(dev.id),u"MAC", MAC)
                            if essid != dev.states[u"essid"]:
                                self.addToStatesUpdateList(unicode(dev.id),u"essid", essid)
                            if channel != dev.states[u"channel"]:
                                self.addToStatesUpdateList(unicode(dev.id),u"channel", channel)
                            if channel != dev.states[u"adhoc"]:
                                self.addToStatesUpdateList(unicode(dev.id),u"adhoc", adhoc)

                            signalOLD = [" " for iii in range(_GlobalConst_numberOfAP)]
                            signalNEW = copy.copy(signalOLD)
                            if rssi != "":
                                signalOLD = dev.states[u"Signal_at_APs"].split(u"[")[0].split("/")
                                if len(signalOLD) == _GlobalConst_numberOfAP:
                                    signalNEW = copy.copy(signalOLD)
                                    signalNEW[apNumb] = unicode(int(-90 + float(rssi) / 99. * 40.))
                            if signalNEW != signalOLD or dev.states[u"Signal_at_APs"] == "":
                                self.addToStatesUpdateList(unicode(dev.id),u"Signal_at_APs", "/".join(signalNEW) + "[dBm]")

                            if model != dev.states[u"model"] and model != "":
                                self.addToStatesUpdateList(unicode(dev.id),u"model", model)
                            self.MAC2INDIGO[xType][MAC][u"age"] = age 
                            self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()
                            self.setImageAndStatus(dev, "up",oldStatus=dev.states[u"status"], ts=time.time(), level=1, text1=dev.name.ljust(30) + u" status up         neighbor DICT ", iType=u"DC-NEIG-1")
                            if self.updateDescriptions  and dev.description != "Channel= " + channel.rjust(2).replace(" ", "0") + " - SID= " + essid:
                                dev.description = "Channel= " + channel.rjust(2).replace(" ", "0") + " - SID= " + essid
                                dev.replaceOnServer()


                    if new and not self.ignoreNewNeighbors:
                        indigo.server.log("new: neighbor  " +MAC)
                        try:
                            dev = indigo.device.create(
                                protocol=indigo.kProtocol.Plugin,
                                address=MAC,
                                name=devName + "_" + MAC,
                                description="Channel= " + channel.rjust(2).replace(" ", "0") + " - SID= " + essid,
                                pluginId=self.pluginId,
                                deviceTypeId=devType,
                                folder=self.folderNameNeighbors,
                                props={u"useWhatForStatus":""})
                        except  Exception, e:
                            if len(unicode(e)) > 5:
                                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
                            continue

                        self.setupStructures(xType, dev, MAC)
                        self.addToStatesUpdateList(unicode(dev.id),u"channel", channel)
                        signalNEW = [" " for iii in range(_GlobalConst_numberOfAP)]
                        if rssi != "":
                            signalNEW[apNumb] = unicode(int(-90 + float(rssi) / 99. * 40.))
                        self.addToStatesUpdateList(unicode(dev.id),u"Signal_at_APs", "/".join(signalNEW) + "[dBm]")
                        self.addToStatesUpdateList(unicode(dev.id),u"essid", essid)
                        self.addToStatesUpdateList(unicode(dev.id),u"model", model)
                        self.MAC2INDIGO[xType][MAC][u"age"] = age 
                        self.addToStatesUpdateList(unicode(dev.id),u"adhoc", adhoc)
                        self.setupBasicDeviceStates(dev, MAC, xType, "", "", "", u" status up         neighbor DICT new neighbor", "DC-NEIG-2")
                self.executeUpdateStatesList()

        except  Exception, e:
            if len(unicode(e)) > 5:
                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

        #if time.time()-waitT > 0.001: #indigo.server.log(unicode(self.blockAccess).ljust(28)+part.ljust(18)+"  exectime> %6.3f"%(time.time()-waitT)+ " @ "+datetime.datetime.now().strftime("%M:%S.%f")[:-3])
        if len(self.blockAccess)>0:  del self.blockAccess[0]
        return


    ####-----------------    ---------
    #### this does the unifswitch device itself
    ####-----------------    ---------
    def doSWdictSELF(self, theDict, apNumb, ipNDevice, MAC, hostname):

        part="doSWdictSELF"+unicode(random.random()); self.blockAccess.append(part)
        for ii in range(90):
                if len(self.blockAccess) == 0 or self.blockAccess[0] == part: break # my turn?
                self.sleep(0.1)   
        if ii >= 89: self.blockAccess = [] # for safety if too long reset list
           
        if "model_display" in theDict:  model = (theDict[u"model_display"])
        else:     
            self.ML.myLog( text=u"model_display not in dict doSWdictSELF") 
            model = ""


        devName = u"SW"
        xType   = u"SW"

        try:
            temperature = "" 

            if u"general_temperature" in theDict:
                if unicode(theDict[u"general_temperature"]) !="0":
                    temperature = unicode(theDict[u"general_temperature"])+ u"[ºC]"
            overHeating     = 1 if theDict[u"overheating"] else 0
            uptime          = unicode(theDict[u"uptime"])
            portTable       = theDict[u"port_table"]
            nports          = len(portTable)
            
            if nports not in self.numberOfPortsInSwitch:
                for nn in self.numberOfPortsInSwitch:
                    if nports < nn:
                        nports =nn
                    if MAC not in self.MAC2INDIGO[xType]:       
                        indigo.server.log(u"switch device model "+model+" not support: please contact author. This has "+unicode(nports)+" ports; supported are 8,10,18,26,52 ports only - remember there are extra ports for fiber cables , using next highest..")

            if nports > self.numberOfPortsInSwitch[-1]: return 



                
            devType = u"Device-SW-" + unicode(nports)
            new = True
              
            if MAC in self.MAC2INDIGO[xType]:
                try:
                    dev = indigo.devices[self.MAC2INDIGO[xType][MAC]["devId"]]
                    if dev.deviceTypeId != devType: raise error
                    new = False
                except:
                    if self.ML.decideMyLog(u"Logic") or MAC in self.MACloglist: self.ML.myLog( text=MAC+"  "+unicode(self.MAC2INDIGO[xType][MAC])+u" wrong "+ devType)
                    for dev in indigo.devices.iter(self.pluginId):
                        if dev.deviceTypeId !=devType: continue
                        if u"MAC" not in dev.states: continue
                        if dev.states[u"MAC"] != MAC: continue
                        self.MAC2INDIGO[xType][MAC]["devId"] = dev.id
                        new = False
                        break


            if not new:

                    if self.ML.decideMyLog(u"DictDetails") or MAC in self.MACloglist:  self.ML.myLog( text=ipNDevice + u" SW  hostname:" + hostname + u" MAC:" + MAC, mType=u"DC-SW-1")
                    self.MAC2INDIGO[xType][MAC][u"ipNumber"] = ipNDevice

                    if u"uptime" in theDict and theDict[u"uptime"] !="":         
                        if u"upSince" in dev.states:
                            self.addToStatesUpdateList(unicode(dev.id),u"upSince", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()-theDict[u"uptime"])) )

                    ports = {}
                    if dev.states[u"switchNo"] != apNumb:
                        self.addToStatesUpdateList(unicode(dev.id),u"switchNo", apNumb)

                    if u"ports" not in self.MAC2INDIGO[xType][MAC]:
                        self.MAC2INDIGO[xType][MAC][u"ports"]={}
                    self.MAC2INDIGO[xType][MAC][u"nPorts"] = len(portTable)
                        
                    for port in portTable:

                        if u"port_idx" not in port: continue
                        id = port[u"port_idx"]
                        idS = "%02d" % id

                        if unicode(id) not in self.MAC2INDIGO[xType][MAC][u"ports"]:
                            self.MAC2INDIGO[xType][MAC][u"ports"][unicode(id)] = {u"rxLast": 0, u"txLast": 0, u"timeLast": 0,u"poe":"",u"fullDuplex":"",u"link":"",u"nClients":0}
                        portsMAC = self.MAC2INDIGO[xType][MAC][u"ports"][unicode(id)]
                        if portsMAC[u"timeLast"] != 0.:
                            try:
                                dt = max(5, time.time() - portsMAC[u"timeLast"]) * 1000
                                rxRate = "%1d" % ((port[u"tx_bytes"] - portsMAC[u"txLast"]) / dt + 0.5)
                                txRate = "%1d" % ((port[u"rx_bytes"] - portsMAC[u"rxLast"]) / dt + 0.5)
                            except  Exception, e:
                                if len(unicode(e)) > 5:
                                    indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
                            ###indigo.server.log(u"rxRate: " + unicode(rxRate)+  u"  txRate: " + unicode(txRate))
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
                                        if  macUPdowndevice in self.MAC2INDIGO[u"GW"]:
                                            ppp+=";GateW"
                                            SWP ="GW"
                                        elif  macUPdowndevice in self.MAC2INDIGO[xType]:
                                            try:    portNatSW = ",P:"+lldp_table[u"lldp_port_id"].split("/")[1]
                                            except: portNatSW = ""
                                            if SWP =="" : SWP = "DwL" 
                                            devIdOfSwitch = self.MAC2INDIGO[u"SW"][macUPdowndevice]["devId"]
                                            ppp+= ";"+SWP+":"+ unicode(indigo.devices[devIdOfSwitch].states[u"switchNo"])+portNatSW
                                    except  Exception, e:
                                            self.ML.myLog( text=u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

                            portsMAC["link"] = SWP

                            poe=""
                            if u"poe_enable" in port and port[u"poe_enable"]:
                                if (u"poe_good" in port and port[u"poe_good"])  :
                                    poe="poe1"
                                elif (u"poe_mode" in port and port[u"poe_mode"] =="passthrough") :
                                    poe="poeP"
                                else:
                                    poe="poe0"
                            if poe !="":
                                ppp+=";"+poe
                            portsMAC["poe"] = poe

                            if nDevices > 0:
                                ppp += u";" + fullDuplex + u"-" + (unicode(port[u"speed"]))
                                ppp += u"; err:" + errors
                                ppp += u"; rx-tx[kb/s]:" + rxRate + "-" + txRate

                                            
                                if ppp != dev.states[u"port_" + idS]:
                                    self.addToStatesUpdateList(unicode(dev.id),u"port_" + idS, ppp)

    

                            if u"port_" + idS in dev.states:
                                if ppp != dev.states[u"port_" + idS]:
                                    self.addToStatesUpdateList(unicode(dev.id),u"port_" + idS, ppp)



                        portsMAC[u"txLast"]    = port[u"tx_bytes"]
                        portsMAC[u"rxLast"]    = port[u"rx_bytes"]
                        portsMAC[u"timeLast"]  = time.time()

                    if model != dev.states[u"model"] and model !="":
                        self.addToStatesUpdateList(unicode(dev.id),u"model", model)
                    if uptime != self.MAC2INDIGO[xType][MAC][u"uptime"]:
                        self.MAC2INDIGO[xType][MAC][u"uptime"] =uptime
                    if temperature != dev.states[u"temperature"]:
                        self.addToStatesUpdateList(unicode(dev.id),u"temperature", temperature)
                    if "overHeating" in dev.states and overHeating != dev.states[u"overHeating"]:
                            self.addToStatesUpdateList(unicode(dev.id),u"overHeating", overHeating)
                    if ipNDevice != dev.states[u"ipNumber"]:
                        self.addToStatesUpdateList(unicode(dev.id),u"ipNumber", ipNDevice)
                    if hostname != dev.states[u"hostname"]:
                        self.addToStatesUpdateList(unicode(dev.id),u"hostname", hostname)
                    if dev.states[u"status"] != u"up":
                        self.setImageAndStatus(dev, u"up",oldStatus=dev.states[u"status"], ts=time.time(), level=1, text1=dev.name.ljust(30) + u" status up         SW  DICT", iType=u"STATUS-SW")
                    self.MAC2INDIGO[xType][MAC][u"lastUp"] = time.time()


                    if self.updateDescriptions:  
                        ipx = self.fixIP(ipNDevice)
                        oldDescr = dev.description.split("-")
                        oldIPX   = oldDescr[0]
                        if oldIPX != ipx or ( (dev.description != ipx + "-" + hostname) or len(dev.description) < 5):
                            if len(oldDescr) < 2:
                                oldDescr.append(hostname.strip("-"))
                            elif len(oldDescr) == 2 and oldDescr[1] == "":
                                if hostname != "":
                                    oldDescr[1] = hostname.strip("-")
                            oldDescr[0] = ipx
                            newDescr = "-".join(oldDescr)
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
                        folder=self.folderNameCreatedID,
                        props={u"useWhatForStatus":""})
                    self.setupStructures(xType, dev, MAC)
                    self.MAC2INDIGO[xType][MAC][u"uptime"] = uptime
                    self.addToStatesUpdateList(unicode(dev.id),u"model", model)
                    self.addToStatesUpdateList(unicode(dev.id),u"temperature", temperature)
                    self.addToStatesUpdateList(unicode(dev.id),u"overHeating", overHeating)
                    self.addToStatesUpdateList(unicode(dev.id),u"hostname", hostname)
                    self.addToStatesUpdateList(unicode(dev.id),u"switchNo", apNumb)
                    self.setupBasicDeviceStates(dev, MAC, xType, ipNDevice, "", "", u" status up         SW DICT  new SWITCH", "STATUS-SW")
                except  Exception, e:
                    if len(unicode(e)) > 5:
                        indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
                        indigo.server.log(u"     for mac#"+MAC+";  hostname: "+ hostname)
                        indigo.server.log(u"MAC2INDIGO: "+unicode(self.MAC2INDIGO[xType]))

            self.executeUpdateStatesList()

        except  Exception, e:
            if len(unicode(e)) > 5:
                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

        #if time.time()-waitT > 0.001: #indigo.server.log(unicode(self.blockAccess).ljust(28)+part.ljust(18)+"  exectime> %6.3f"%(time.time()-waitT)+ " @ "+datetime.datetime.now().strftime("%M:%S.%f")[:-3])
        if len(self.blockAccess)>0:  del self.blockAccess[0]

        return

    ####----------------- if FINGSCAN is enabled send update signal  ---------
    def setStatusUpForSelfUnifiDev(self, MAC):
        try:

            if MAC in self.MAC2INDIGO[u"UN"]:
                self.MAC2INDIGO[u"UN"][MAC][u"lastUp"] = time.time()+20
                devidUN = self.MAC2INDIGO[u"UN"][MAC]["devId"]
                try:    
                    devUN = indigo.devices[devidUN]
                    if devUN.states["status"] !=u"up":
                        self.addToStatesUpdateList(unicode(devidUN),u"status", u"up")
                        self.addToStatesUpdateList(unicode(devidUN),u"lastStatusChangeReason", u"switch message")
                        if self.ML.decideMyLog(u"Logic") or MAC in self.MACloglist :  self.ML.myLog( text=u"setStatusUpForSelfUnifiDev:   updating status to up MAC:" + MAC+"  "+devUN.name+"  was: "+ devUN.states["status"]  , mType=u"updateself")
                    if unicode(devUN.displayStateImageSel) !="SensorOn":
                        devUN.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
                except:pass
                
        except  Exception, e:
            if len(unicode(e)) > 5:
                indigo.server.log( u"updating fingscan has error in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

    ####----------------- if FINGSCAN is enabled send update signal  ---------
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
                                    if self.ML.decideMyLog(u"Fing"): self.ML.myLog( text=u"updating fingscan with " + dev.name + u" = " + dev.states[u"status"] ,mType=u"FINGSC" )
                                    plug.executeAction(u"unifiUpdate", props={u"deviceId": [devid]})
                                    self.fingscanTryAgain = False
                                except  Exception, e:
                                    if len(unicode(e)) > 5:
                                        indigo.server.log( u"updating fingscan has error in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e)+u" finscan update failed")
                                    self.fingscanTryAgain = True

            else:
                devIds    = []
                devNames  = []
                devValues = {}
                stringToPrint = u"\n"
                for dev in indigo.devices.iter(self.pluginId):
                    if dev.deviceTypeId == u"client": continue
                    devIds.append(unicode(dev.id))
                    stringToPrint += dev.name + u"= " + dev.states[u"status"] + u"\n"

                if devIds != []:
                    for i in range(3):
                        if self.ML.decideMyLog(u"Fing"): self.ML.myLog( text=u"updating fingscan try# " + unicode(i + 1) + u";   with " + stringToPrint ,mType=u"FINGSC")
                        plug.executeAction(u"unifiUpdate", props={u"deviceId": devIds})
                        self.fingscanTryAgain = False
                        break

        except  Exception, e:
            if len(unicode(e)) > 5:
                indigo.server.log( u"updating fingscan has error in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
            else:
                x = "break"
        self.sendUpdateToFingscanList ={}
        return x

    ####-----------------    ---------
    def checkMAC(self, MAC):
        macs = MAC.split(":")
        for nn in range(len(macs)):
            mac = macs[nn]
            if len(mac) < 2: macs[nn] = u"0" + mac
        return ":".join(macs)

    ####-----------------    ---------
    def fixIP(self, ip):
        if len(ip) < 7: return ip
        ipx = ip.split(u"/")[0].split(u".")
        ipx[3] = "%03d" % (int(ipx[3]))
        return u".".join(ipx)

    ####-----------------    ---------
    def setupBasicDeviceStates(self, dev, MAC, devType, ip, ipNDevice, GHz, text1, type):
        try:
            self.addToStatesUpdateList(unicode(dev.id),u"created", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            self.addToStatesUpdateList(unicode(dev.id),u"MAC", MAC)
            self.MAC2INDIGO[devType][MAC][u"lastUp"] = time.time()
            if ip !="":
                self.addToStatesUpdateList(unicode(dev.id),u"ipNumber", ip)

            self.setImageAndStatus(dev, "up",oldStatus=dev.states[u"status"], ts=time.time(), level=1, text1=dev.name.ljust(30) + text1, iType=type)
            vendor = self.getVendortName(MAC)
            if vendor != "":
                    self.addToStatesUpdateList(unicode(dev.id),u"vendor", vendor)
                    self.moveToUnifiSystem(dev, vendor)
        except  Exception, e:
            if len(unicode(e)) > 5:
                indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        return 

    ####-----------------    ---------
    def testIgnoreMAC(self,MAC,fromSystem):
        if MAC not in self.MACignorelist: return False
        if self.ML.decideMyLog(u"Logic"):  self.ML.myLog( text=u"ignored: message for MAC:"+ MAC,mType=fromSystem) 
        return True
        
        
    ####-----------------    ---------
    def moveToUnifiSystem(self,dev,vendor):
        try:
            if vendor.upper().find("UBIQUIT") >-1:
                indigo.device.moveToFolder(dev.id, value=self.folderNameSystemID)        
                indigo.server.log(u"moving "+dev.name+u";  to folderID: "+ unicode(self.folderNameSystemID))
        except  Exception, e:
            if len(unicode(e)) > 5:
                indigo.server.log(u"moveToUnifiSystem in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

    ####-----------------    ---------
    def getVendortName(self,MAC):
        if self.enableMACtoVENDORlookup !="0" and not self.waitForMAC2vendor:
            self.waitForMAC2vendor = self.M2V.makeFinalTable()

        return  self.M2V.getVendorOfMAC(MAC)
            
        
    ####-----------------    ---------
    def setImageAndStatus(self, dev, newStatus, oldStatus=u"123abc123abcxxx", ts="", level=1, text1="", iType=u"", force=False, fing=True,reason=u""):
        try:
            if oldStatus == u"123abc123abc":
                oldStatus = dev.states[u"status"]
            retC = False
            try:    xType = self.xTypeMac[unicode(dev.id)]["xType"]
            except: return 
            MAC   =  self.xTypeMac[unicode(dev.id)][u"MAC"]
            if oldStatus != newStatus or force:
                if ts != "":
                    retC = True
                if (text1 != "" and self.ML.decideMyLog(u"Logic")) or MAC in self.MACloglist:  self.ML.myLog( text=text1, mType=iType)

                if oldStatus != newStatus:
                    if fing and oldStatus != u"123abc123abcxxx":
                        self.sendUpdateToFingscanList[unicode(dev.id)] = unicode(dev.id)
                    self.addToStatesUpdateList(unicode(dev.id),u"status", newStatus)
                    #self.exeDisplayStatus( dev, newStatus)

                    if u"lastStatusChangeReason" in dev.states and reason !=u"":
                        self.addToStatesUpdateList(unicode(dev.id),u"lastStatusChangeReason", reason)
                    if (not force and self.ML.decideMyLog(u"Logic") )  or MAC in self.MACloglist: self.ML.myLog( text=u" "+dev.states[u"MAC"] +u" st changed  " + dev.states[u"status"]+"/"+newStatus+"; "+text1 ,mType=u"STAT-Change" )
                    retC = True
                
        except  Exception, e:
            if len(unicode(e)) > 5:
                indigo.server.log(u"setImageAndStatus in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

        return  



    ####-----------------    ---------
    def manageLogfile(self, apDict, apNumb,unifiDeviceType):
        try:

            if self.logFileActive !="no":
                if unicode(apNumb) not in self.logCount:
                    self.logCount[unicode(apNumb)] =0
                self.logCount[unicode(apNumb)] += 1

                name = self.unifiPath + u"dict-"+unifiDeviceType+u"#" + unicode(apNumb) + u"-Seq-"
                maxLog =2
                for ii in range(maxLog):
                    if os.path.isfile(name + unicode(maxLog - ii) + ".txt"):
                        os.remove(name + unicode(maxLog - ii) + ".txt")
                    if os.path.isfile(name + unicode(maxLog-1 - ii) + ".txt"):
                        os.rename(name + unicode(maxLog-1 - ii) + ".txt", name + unicode(maxLog - ii) + ".txt")

                f = open(name+"0.txt", "w")
                if self.logCount[unicode(apNumb)] > maxLog: self.logCount[unicode(apNumb)] = 0
                f.write(json.dumps(apDict, sort_keys=True, indent=2))
                f.close()

        except  Exception, e:
                if len(unicode(e)) > 5:
                    indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))


    ####-----------------    ---------
    def exeDisplayStatus(self, dev, status):
                if status == u"up" :
                    dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
                elif status == u"down":
                    dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
                elif status == u"expired" :
                    dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
                elif status == u"" :
                    dev.updateStateOnServer(u"displayStatus",self.padDisplay(u"expired")+datetime.datetime.now().strftime(u"%m-%d %H:%M:%S"))
                    dev.updateStateOnServer(u"status",u"expired")
                    dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)


    ####-----------------    ---------
    def addToStatesUpdateList(self,devId,key,value):
        try:
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

        except  Exception, e:
            if len(unicode(e))  > 5 :
                self.ML.myLog( text=u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e) )
        return    




    ####-----------------    ---------
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
                    for key in  local[devId]:
                        value =  local[devId][key]
                        if unicode(value) != unicode(dev.states[key]):
                            if devId not in changedOnly: changedOnly[devId]=[]
                            changedOnly[devId].append({u"key":key,u"value":value})
                            if key == u"status": 
                                ts = datetime.datetime.now().strftime(u"%Y-%m-%d %H:%M:%S")
                                changedOnly[devId].append({u"key":u"lastStatusChange", u"value":ts})
                                changedOnly[devId].append({u"key":u"displayStatus",    u"value":self.padDisplay(value)+ts[5:] } )
                                self.exeDisplayStatus(dev, value)
                                
                                self.statusChanged = max(1,self.statusChanged)
                                trigList.append(dev.name)

                            
                    if devId in changedOnly and changedOnly[devId] !=[]:
                        self.dataStats[u"updates"][u"devs"]   +=1
                        self.dataStats[u"updates"][u"states"] +=len(changedOnly)
                        if self.indigoVersion >6:
                            try:
                                dev.updateStatesOnServer(changedOnly[devId])
                            except  Exception, e:
                                if len(unicode(e))  > 5 :
                                    self.ML.myLog( text=u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e) )
                                self.ML.myLog( text=u"devId:" + unicode(devId)+ u";  changedOnlyDict:"+unicode(changedOnly[devId]))
                        else:
                            for uu in changedOnly[devId]:
                                #indigo.server.log(dev.name + "  "+unicode(uu))
                                dev.updateStateOnServer(uu[u"key"],uu[u"value"])

            if len(trigList) >0: 
                for devName  in trigList:
                    indigo.variable.updateValue(u"Unifi_With_Status_Change",devName)
                self.triggerEvent(u"someStatusHasChanged")
        except  Exception, e:
            if len(unicode(e))  > 5 :
                self.ML.myLog( text=u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e) )
                #self.logger.error(dev.name+u"  "+ devId +u"  "+ key)
                try:
                    self.ML.myLog( text=dev.name+u"  "+ devId +u"  "+ unicode(key)+";  devStateChangeList:\n"+ unicode(local))
                except:pass
        return 
        
    ####-----------------    ---------
    def padDisplay(self,status):
        if	 status == u"up":        return status.ljust(11)
        elif status == u"expired":   return status.ljust(8)
        elif status == u"down":      return status.ljust(9)
        elif status == u"changed":   return status.ljust(8)
        elif status == u"double":    return status.ljust(8)
        elif status == u"ignored":   return status.ljust(8)
        else:                        return status.ljust(10)

    