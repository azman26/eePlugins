# -*- coding: utf-8 -*-
from __future__ import absolute_import #zmiana strategii ladowanie modulow w py2 z relative na absolute jak w py3
from Plugins.Extensions.StreamlinkConfig.__init__ import mygettext as _ , readCFG , DBGlog
from Plugins.Extensions.StreamlinkConfig.version import Version
from Plugins.Extensions.StreamlinkConfig.plugins.azmanIPTVsettings import get_azmanIPTVsettings
import os, time, sys
# GUI (Screens)
from Components.ActionMap import ActionMap
from Components.config import *
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
#from Components.Sources.StaticText import StaticText
from enigma import eTimer, eConsoleAppContainer

from Screens.ChoiceBox import ChoiceBox
from Screens.Console import Console
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Setup import SetupSummary

try:
    from emukodi.xbmcE2 import *
    from emukodi.e2Console import emukodiConsole
except Exception as e:
    print('AQQ ERROR', str(e))
    addons_path = 'ERROR'
    emukodi_path = 'ERROR'
    emukodiConsole = Console
    
#### streamlink config /etc/streamlink/config ####
def getFFlist():
    ffList = []
    for f in sorted(os.listdir("/usr/bin"), key=str.lower):
        if f.startswith('ffmpeg'):
            ffList.append(("/usr/bin/%s" % f, f ))
    return ffList

def getCurrFF():
    ff = '/usr/bin/ffmpeg'
    for c in getStreamlinkConfig():
        if c.startswith('ffmpeg-ffmpeg='):
            tmp = c.split('=')[1].strip()
            if os.path.exists(tmp):
                ff = tmp
    return ff
    
def getStreamlinkConfig():
    try:
        cfg = open('/etc/streamlink/config', 'r').read().splitlines()
    except Exception:
        cfg = []
    return cfg

config.plugins.streamlinkSRV.streamlinkconfig = NoSave(ConfigNothing())
config.plugins.streamlinkSRV.streamlinkDRMconfig = NoSave(ConfigNothing())
config.plugins.streamlinkSRV.streamlinkEMUKODIconfig = NoSave(ConfigNothing())
config.plugins.streamlinkSRV.streamlinkconfigFFMPEG = NoSave(ConfigSelection(default = getCurrFF(), choices = getFFlist()))


class StreamlinkConfiguration(Screen, ConfigListScreen):
    from enigma import getDesktop
    if getDesktop(0).size().width() == 1920: #definicja skin-a musi byc tutaj, zeby vti sie nie wywalalo na labelach, inaczej trzeba uzywasc zrodla statictext
        skin = """<screen name="StreamlinkConfiguration" position="center,center" size="1000,700" title="Streamlink configuration">
                    <widget name="config"     position="20,20"   zPosition="1" size="960,600" scrollbarMode="showOnDemand" />
                    <widget name="key_red"    position="20,630"  zPosition="2" size="240,30" foregroundColor="red"    valign="center" halign="left" font="Regular;22" transparent="1" />
                    <widget name="key_green"  position="260,630" zPosition="2" size="240,30" foregroundColor="green"  valign="center" halign="left" font="Regular;22" transparent="1" />
                    <widget name="key_yellow" position="500,630" zPosition="2" size="240,30" foregroundColor="yellow" valign="center" halign="left" font="Regular;22" transparent="1" />
                    <widget name="key_blue"   position="740,630" zPosition="2" size="240,30" foregroundColor="blue"   valign="center" halign="left" font="Regular;22" transparent="1" />
                  </screen>"""
    else:
        skin = """<screen name="StreamlinkConfiguration" position="center,center" size="700,400" title="Streamlink configuration">
                    <widget name="config"     position="20,20" size="640,325" zPosition="1" scrollbarMode="showOnDemand" />
                    <widget name="key_red"    position="20,350" zPosition="2" size="150,30" foregroundColor="red" valign="center" halign="left" font="Regular;22" transparent="1" />
                    <widget name="key_green"  position="170,350" zPosition="2" size="150,30" foregroundColor="green" valign="center" halign="left" font="Regular;22" transparent="1" />
                    <widget name="key_yellow" position="360,350" zPosition="2" size="150,30" foregroundColor="yellow" valign="center" halign="left" font="Regular;22" transparent="1" />
                    <widget name="key_blue"   position="500,350" zPosition="2" size="150,30" foregroundColor="blue" valign="center" halign="left" font="Regular;22" transparent="1" />
                  </screen>"""
    def buildList(self):
        self.DoBuildList.stop()
        Mlist = []
        #cdmStatus == True:
        pythonRunner = '/usr/bin/python'
        addonScript = 'plugin.video.cdaplMB/main.py'
        runAddon = '%s %s' % (pythonRunner, os.path.join(addons_path, addonScript))
        webServer = ''
                            
        for cfgFile in ['refr_token', 'username', 'password']:
            if not os.path.exists('/etc/streamlink/cdaplMB/%s' % cfgFile): os.system('touch /etc/streamlink/cdaplMB/%s' % cfgFile)
                            
        if open('/etc/streamlink/cdaplMB/username','r').read().strip() == '':
            Mlist.append(getConfigListEntry( 'cda: Brak danych w /etc/streamlink/cdaplMB/username' , config.plugins.streamlinkSRV.streamlinkconfig))
        elif open('/etc/streamlink/cdaplMB/password','r').read().strip() == '':
            Mlist.append(getConfigListEntry( 'cda: Brak danych w /etc/streamlink/cdaplMB/password' , config.plugins.streamlinkSRV.streamlinkconfig))
        elif open('/etc/streamlink/cdaplMB/refr_token','r').read().strip() == '':
            emuKodiCmdsList = []
            emuKodiCmdsList.append(runAddon + " '1' '' 'resume:false'") #logowanie nastepuje bez podania trybu
            autoClose = True #ustawienie parametrow w zaleznoci od akcji
            webServer = ''
            Mlist.append(getConfigListEntry( "Zaloguj do cda", config.plugins.streamlinkSRV.streamlinkEMUKODIconfig, ('cdaplMB', 'ActionConfirmed', emuKodiCmdsList, autoClose, webServer, addonScript)))
        else:
            if os.path.exists('/etc/streamlink/cdaplMB/login_info'):
                login_info = open('/etc/streamlink/cdaplMB/login_info','r').read().strip()
                if login_info != '':
                    login_info = login_info.replace('[COLOR gold]','').replace('[/COLOR]','')
                    #wylogowanie
                    emuKodiCmdsList = []
                    emuKodiCmdsList.append("rm -f /etc/streamlink/cdaplMB/*")
                    emuKodiCmdsList.append("echo 'Wylogowano z serwisu cda i usunięto dane tymczasowe'")
                    emuKodiCmdsList.append("sleep 2")
                    autoClose = True #ustawienie parametrow w zaleznoci od akcji
                    Mlist.append(getConfigListEntry( login_info + '\c00981111' + ' WYLOGUJ!!!', config.plugins.streamlinkSRV.streamlinkEMUKODIconfig, ('cdaplMB', 'ActionConfirmed', emuKodiCmdsList, autoClose, webServer, addonScript)))
            #pobieranie listy
            emuKodiCmdsList = []
            emuKodiCmdsList.append("echo 'Logowanie do serwisu'")
            emuKodiCmdsList.append(runAddon + " '1' '' 'resume:false'") #logowanie nastepuje bez podania trybu
            emuKodiCmdsList.append("echo 'Pobieranie listy kanałów'")
            emuKodiCmdsList.append(runAddon + " '1' '?image=DefaultMovies.png&mode=listM3U&moviescount=0&page=1&title=CDA%20TV%20-%20Telewizja%20Online&url' 'resume:false'")
            autoClose = True #ustawienie parametrow w zaleznoci od akcji
            webServer = ''
            Mlist.append(getConfigListEntry( _("Press OK to create bouquet for") + ' cda' , config.plugins.streamlinkSRV.streamlinkEMUKODIconfig, ('cdaplMB', 'userbouquet', emuKodiCmdsList, autoClose, webServer, addonScript)))
        return Mlist
    
    def getAddonsRunPath(self, addonName):
        runAddon = '/usr/bin/python plugin.video.%s/main.py' % os.path.join(addons_path, addonName)

    def __init__(self, session, args=None):
        DBGlog('%s' % '__init__')
        self.doAction = None
        if os.path.exists('/usr/sbin/streamlinkSRV') and os.path.islink('/usr/sbin/streamlinkSRV') and 'StreamlinkConfig/' in os.readlink('/usr/sbin/streamlinkSRV'):
            self.mySL = True
        else:
            self.mySL = False
        
        self.DoBuildList = eTimer()
        self.DoBuildList.callback.append(self.buildList)
        
        Screen.__init__(self, session)
        self.session = session

        # Summary
        self.setup_title = 'Konfguracja cda.pl'
        self.onChangedEntry = []

        # Buttons
        self["key_red"] = Label(_("Cancel"))
        
        if self.mySL == True:
            self["key_green"] = Label(_("Save"))
            self["key_blue"] = Label(_("Restart daemon"))
            if os.path.exists('/usr/lib/python2.7'):
                self["key_yellow"] = Label()
            elif os.path.exists('/tmp/streamlinkSRV.log'):
                self["key_yellow"] = Label(_("Show log"))
        else:
            self["key_green"] = Label()
            self["key_blue"] = Label()
            self["key_yellow"] = Label()

        # Define Actions
        self["actions"] = ActionMap(["StreamlinkConfiguration"],
            {
                "cancel":   self.exit,
                "red"   :   self.exit,
                "green" :   self.save,
                "yellow":   self.yellow,
                "blue"  :   self.blue,
                "save":     self.save,
                "ok":       self.Okbutton,
                "prevConf": self.prevConf,
                "nextConf": self.nextConf,
            }, -2)
        if 0:
            if not self.selectionChanged in self["config"].onSelectionChanged:
                self["config"].onSelectionChanged.append(self.selectionChanged)
        
        self.onLayoutFinish.append(self.layoutFinished)
        self.doAction = None
        ConfigListScreen.__init__(self, self.buildList(), on_change = self.changedEntry)

    def saveConfig(self):
        for x in self["config"].list:
            if len(x) >= 2:
                x[1].save()
        configfile.save()

    def save(self):
        if self.mySL == True:
            self.saveConfig()
            os.system('%s stop' % config.plugins.streamlinkSRV.binName.value)
            if config.plugins.streamlinkSRV.enabled.value:
                os.system('%s start' % config.plugins.streamlinkSRV.binName.value)
            self.VisibleSection = 0
            self.close(None)
        
    def refreshBuildList(self, ret = False):
        DBGlog('refreshBuildList >>>')
        self["config"].list = self.buildList()
        self.DoBuildList.start(50, True)
        
    def doNothing(self, ret = False):
        DBGlog('doNothing >>>')
        return
      
    def yellow(self):
        if self.mySL == True:
            if os.path.exists('/tmp/streamlinkSRV.log'):
                self.session.openWithCallback(self.doNothing ,Console, title = '/tmp/streamlinkSRV.log', cmdlist = [ 'cat /tmp/streamlinkSRV.log' ])
        
    def blue(self):
        if self.mySL == True:
            mtitle = _('Restarting daemon')
            cmd = '/usr/sbin/%s restart' % config.plugins.streamlinkSRV.binName.value
            self.session.openWithCallback(self.doNothing ,Console, title = mtitle, cmdlist = [ cmd ])
        
    def exit(self):
        self.VisibleSection = 0
        self.close(None)
        
    def prevConf(self):
        DBGlog('prevConf >>> VisibleSection = %s' % self.VisibleSection)
        self.VisibleSection -= 1
        if self.VisibleSection < 1:
            self.VisibleSection = 5
        self.refreshBuildList()
        
    def nextConf(self):
        DBGlog('nextConf >>> VisibleSection = %s' % self.VisibleSection)
        self.VisibleSection += 1
        if self.VisibleSection > 5:
            self.VisibleSection = 1
        self.refreshBuildList()
    
    def layoutFinished(self):
        print('layoutFinished')
        self.VisibleSection = 0
        self.DoBuildList.start(10, True)
        self.setTitle(self.setup_title)
        
        if os.path.exists("/usr/lib/enigma2/python/Plugins/SystemPlugins/ServiceApp/serviceapp.so"):
            self.choicesList = [(_("Don't change"),"0"),("gstreamer (root 4097)","4097"),("ServiceApp gstreamer (root 5001)","5001"), ("ServiceApp ffmpeg (root 5002)","5002"),("Hardware (root 1) wymagany do PIP","1")]
        else:
            self.choicesList = [(_("Don't change"),"0"),("gstreamer (root 4097)","4097"),("Hardware (root 1) wymagany do PIP","1"),(_("ServiceApp not installed!"), None)]
        
    def changedEntry(self):
        DBGlog('%s' % 'changedEntry()')
        try:
            for x in self.onChangedEntry:
                x()
        except Exception as e:
            DBGlog('%s' % str(e))

    def selectionChanged(self):
        if 0:
            DBGlog('%s' % 'selectionChanged(%s)' % self["config"].getCurrent()[0])

    def getCurrentEntry(self):
        return self["config"].getCurrent()[0]

    def getCurrentValue(self):
        if len(self["config"].getCurrent()) >= 2:
            return str(self["config"].getCurrent()[1].getText())

    def createSummary(self):
        return SetupSummary

    def Okbutton(self):
        DBGlog('%s' % 'Okbutton')
        try:
            self.doAction = None
            curIndex = self["config"].getCurrentIndex()
            selectedItem = self["config"].list[curIndex]
            if len(selectedItem) >= 2:
                currItem = selectedItem[1]
                currInfo = selectedItem[0]
                if isinstance(currItem, ConfigText):
                    from Screens.VirtualKeyBoard import VirtualKeyBoard
                    self.session.openWithCallback(self.OkbuttonTextChangedConfirmed, VirtualKeyBoard, title=(currInfo), text = currItem.value)
                elif currItem == config.plugins.streamlinkSRV.One:
                    if self.VisibleSection == 1: self.VisibleSection = 0
                    else: self.VisibleSection = 1
                    self.refreshBuildList()
                elif currItem == config.plugins.streamlinkSRV.Two:
                    if self.VisibleSection == 2: self.VisibleSection = 0
                    else: self.VisibleSection = 2
                    self.refreshBuildList()
                elif currItem == config.plugins.streamlinkSRV.Three:
                    if self.VisibleSection == 3: self.VisibleSection = 0
                    else: self.VisibleSection = 3
                    self.refreshBuildList()
                elif currItem == config.plugins.streamlinkSRV.Four:
                    if self.VisibleSection == 4: self.VisibleSection = 0
                    else: self.VisibleSection = 4
                    self.refreshBuildList()
                elif currItem == config.plugins.streamlinkSRV.Five:
                    if self.VisibleSection == 5: self.VisibleSection = 0
                    else: self.VisibleSection = 5
                    self.refreshBuildList()
                elif currItem == config.plugins.streamlinkSRV.WPbouquet:
                    if config.plugins.streamlinkSRV.WPusername.value == '' or config.plugins.streamlinkSRV.WPpassword.value == '':
                        self.session.openWithCallback(self.doNothing,MessageBox, _("Username & Password are required!"), MessageBox.TYPE_INFO, timeout = 5)
                        return
                    else:
                        self.doAction = ('wpBouquet.py' , '/etc/enigma2/userbouquet.WPPL.tv', config.plugins.streamlinkSRV.WPusername.value, config.plugins.streamlinkSRV.WPpassword.value)
                elif currItem == config.plugins.streamlinkSRV.WPlogin:
                    if config.plugins.streamlinkSRV.WPusername.value == '' or config.plugins.streamlinkSRV.WPpassword.value == '':
                        self.session.openWithCallback(self.doNothing,MessageBox, _("Username & Password are required!"), MessageBox.TYPE_INFO, timeout = 5)
                        return
                    else:
                        self.saveConfig()
                        cmd = "/usr/bin/python /usr/lib/enigma2/python/Plugins/Extensions/StreamlinkConfig/plugins/wpBouquet.py checkLogin '%s' '%s'" % (config.plugins.streamlinkSRV.WPusername.value, config.plugins.streamlinkSRV.WPpassword.value)
                        self.session.openWithCallback(self.doNothing ,Console, title = "SL %s %s" % (Version, _('Credentials verification')), cmdlist = [ cmd ])
                        return
                elif currItem == config.plugins.streamlinkSRV.generateBouquet:
                    DBGlog('currItem == config.plugins.streamlinkSRV.generateBouquet')
                    bouquetFileName = currInfo.split(': ')[1].strip()
                    self.doAction = ('generate_%s.py' % bouquetFileName, '/etc/enigma2/%s' % bouquetFileName, 'anonymous','nopassword')
                elif currItem == config.plugins.streamlinkSRV.removeBouquet: #removeBouquet
                    DBGlog('currItem == config.plugins.streamlinkSRV.removeBouquet')
                    #wybrany bukiet
                    bouquetFileName = currInfo.split(': ')[1].strip()
                    self.doAction = ('removeBouquet.py', '/etc/enigma2/%s' % bouquetFileName, _("Bouquet_'%s' _removed_properly") % bouquetFileName)
                elif currItem == config.plugins.streamlinkSRV.installBouquet: #installBouquet
                    DBGlog('currItem == config.plugins.streamlinkSRV.installBouquet')
                    #wybrany bukiet
                    bouquetFileName = currInfo.split(': ')[1].strip()
                    self.cleanBouquets_tvradio()
                    self.doAction = ('installBouquet.py', bouquetFileName)
                elif currItem == config.plugins.streamlinkSRV.downloadBouquet: #downloadBouquet
                    DBGlog('currItem == config.plugins.streamlinkSRV.installBouquet')
                    #wybrany bukiet
                    bouquetFileName = currInfo.split(': ',1)[1].split(' ',1)[0].strip()
                    self.cleanBouquets_tvradio()
                    url2bouquet = selectedItem[2]
                    #DBGlog('url2bouquet=%s' % url2bouquet)
                    self.doAction = ('downloadBouquet.py', bouquetFileName, url2bouquet, )
                elif currItem == config.plugins.streamlinkSRV.unmanagedBouquet: #modify local bouquet
                    DBGlog('currItem == config.plugins.streamlinkSRV.unmanagedBouquet')
                    #wybrany bukiet
                    bouquetFileName = currInfo.split(': ',1)[1].split(' ',1)[0].strip()
                    self.cleanBouquets_tvradio()
                    self.session.openWithCallback(self.localBouquetSelectedAction, ChoiceBox, title = _("What to do?"), list = [(_("Try to find correct reference to enable EPG"),"e"),
                                                                                                                                (_("Change framework"),"f"), 
                                                                                                                                (_("Change Streamlink connection type"),"sl")
                                                                                                                                ])
                    return
                elif currItem == config.plugins.streamlinkSRV.streamlinkEMUKODIconfig: #bouquets based on KODI plugins
                    DBGlog('currItem == config.plugins.streamlinkSRV.streamlinkEMUKODIconfig')
                    self.emuKodiActions(selectedItem)
                    return
                ####
                DBGlog('%s' % str(self.doAction))
                if not self.doAction is None:
                    cmd = self.doAction[0]
                    bfn = self.doAction[1]
                    DBGlog('%s' % bfn)
                    if cmd == 'removeBouquet.py':
                        cmd = '/usr/bin/python /usr/lib/enigma2/python/Plugins/Extensions/StreamlinkConfig/plugins/%s' % ' '.join(self.doAction)
                        self.session.openWithCallback(self.retFromCMD ,Console, title = "SL %s %s" % (Version, _('Removing bouquet...')), cmdlist = [ cmd ])
                    elif os.path.exists(bfn):
                        self.cmdTitle = _('Updating %s...') % bfn
                        self.session.openWithCallback(self.OkbuttonConfirmed, MessageBox, _("Do you want to update '%s' file?") % bfn, MessageBox.TYPE_YESNO, default = False)
                    elif cmd == 'downloadBouquet.py':
                        self.cmdTitle = _('Downloading %s...') % bfn
                        self.session.openWithCallback(self.OkbuttonConfirmed, MessageBox, _("Do you want to download '%s' file?") % bfn, MessageBox.TYPE_YESNO, default = False)
                    else:
                        self.cmdTitle = _('Creating %s...') % bfn
                        self.session.openWithCallback(self.OkbuttonConfirmed, MessageBox, _("Do you want to create '%s' file?") % bfn, MessageBox.TYPE_YESNO, default = True)
        except Exception as e:
            DBGlog('%s' % str(e))

    def localBouquetChangeFramework(self, ret ):
        if ret is None:
            DBGlog("localBouquetChangeFramework(ret ='%s')" % str(ret))
        else:
            self.doAction = self.doAction + ('f',)
            self.doAction = self.doAction + (ret[1],)
            self.session.openWithCallback(self.retFromCMD ,Console, title = "SL %s %s" % (Version, _('Modifying bouquet...')), cmdlist = [ ' '.join(self.doAction) ])

    def localBouquetChangeSLType(self, ret ):
        if ret is None:
            DBGlog("localBouquetchangeSLType(ret ='%s')" % str(ret))
        else:
            self.doAction = self.doAction + ('sl',)
            self.doAction = self.doAction + (ret[1],)
            self.session.openWithCallback(self.retFromCMD ,Console, title = "SL %s %s" % (Version, _('Modifying bouquet...')), cmdlist = [ ' '.join(self.doAction) ])

    def localBouquetSelectedAction(self, ret):
        curIndex = self["config"].getCurrentIndex()
        selectedItem = self["config"].list[curIndex]
        bouquetFileName = selectedItem[0].split(': ',1)[1].split(' ',1)[0].strip()
        
        self.doAction = ('/usr/bin/python', '/usr/lib/enigma2/python/Plugins/Extensions/StreamlinkConfig/plugins/changeLocalBouquet.py', bouquetFileName, )
        
        if ret is None:
            DBGlog("localBouquetSelectedAction(ret ='%s')" % str(ret))
            return
        elif ret[1] == 'f': #Change framework
            self.session.openWithCallback(self.localBouquetChangeFramework, ChoiceBox, title = _("Select Multiframework"), list = self.choicesList)
        elif ret[1] == 'e': #Try to find correct reference to enable EPG
            self.doAction = self.doAction + ('e',)
            self.session.openWithCallback(self.retFromCMD ,Console, title = "SL %s %s" % (Version, _('Modifying bouquet...')), cmdlist = [ ' '.join(self.doAction) ])
            return
        elif ret[1] == 'sl': #Change Streamlink connection type
            self.session.openWithCallback(self.localBouquetChangeSLType, ChoiceBox, title = _("Select Streamlink connection type"), list = [(_("Use streamlinkSRV"),"SRV"), (_("Use Wrappers"),"wrapper"), 
                                                                                                                           (_("Use direct connection"),"direct")
                                                                                                                           ])
        
    def cleanBouquets_tvradio(self): #clean bouquets.tv from non existing files
        for TypBukietu in('/etc/enigma2/bouquets.tv','/etc/enigma2/bouquets.radio'):
            f = ''
            for line in open(TypBukietu,'r'):
                if 'FROM BOUQUET' in line:
                    fname = line.split('FROM BOUQUET')[1].strip().split('"')[1].strip()
                    if os.path.exists('/etc/enigma2/%s' % fname):
                        f += line
                else:
                    f += line
            open(TypBukietu,'w').write(f)
            
    def OkbuttonTextChangedConfirmed(self, ret ):
        if ret is None:
            DBGlog("OkbuttonTextChangedConfirmed(ret ='%s')" % str(ret))
        else:
            try:
                curIndex = self["config"].getCurrentIndex()
                self["config"].list[curIndex][1].value = ret
            except Exception as e:
                DBGlog('%s' % str(e))

    def OkbuttonConfirmed(self, ret = False):
        if ret:
            self.session.openWithCallback(self.SelectedFramework, ChoiceBox, title = _("Select Multiframework"), list = self.choicesList)

    def OkbuttonConfirmed2(self, ret = False):
        if ret:
            doActionPath = '/usr/lib/enigma2/python/Plugins/Extensions/StreamlinkConfig/plugins/'
            cmd = '/usr/bin/python %s%s %s %s %s' % (doActionPath,
                                                 ' '.join(self.doAction),
                                                 config.plugins.streamlinkSRV.PortNumber.value,
                                                 '4097', 'y'
                                                )
            DBGlog('%s' % cmd)
            self.session.openWithCallback(self.doNothing ,Console, title = "SL %s %s" % (Version, self.cmdTitle), cmdlist = [ cmd ])

    def SelectedFramework(self, ret):
        if not ret or ret == "None" or isinstance(ret, (int, float)):
            ret = (None,'4097')
        doActionPath = '/usr/lib/enigma2/python/Plugins/Extensions/StreamlinkConfig/plugins/'
        cmd = '/usr/bin/python %s%s %s %s %s' % (doActionPath,
                                                 ' '.join(self.doAction),
                                                 config.plugins.streamlinkSRV.PortNumber.value,
                                                 ret[1],
                                                 'y'
                                                )
        if self.doAction[0] == 'wpBouquet.py':
            DBGlog('%s WPuser WPpass %s %s' % (self.doAction[0], config.plugins.streamlinkSRV.PortNumber.value, ret[1]))
        else:
            DBGlog('%s' % cmd)
        self.session.openWithCallback(self.retFromCMD ,Console, title = "SL %s %s" % (Version, self.cmdTitle), cmdlist = [ cmd ])

    def reloadBouquets(self):
        from enigma import eDVBDB
        eDVBDB.getInstance().reloadBouquets()
        
    def retFromCMD(self, ret = False):
        DBGlog('retFromCMD >>>')
        self.cleanBouquets_tvradio()
        self.reloadBouquets()
        msg = _("Bouquets has been reloaded")
        self.session.openWithCallback(self.refreshBuildList,MessageBox, msg, MessageBox.TYPE_INFO, timeout = 5)

    def emuKodiConsoleCallback(self, ret = False):
        if self.emuKodiAction[1] == 'userbouquet': #akcja
            self.retFromCMD(ret)
        else:
            self.refreshBuildList()

    def emuKodiActionConfirmed(self, ret = False):
        if ret:
            curIndex = self["config"].getCurrentIndex()
            selectedItem = self["config"].list[curIndex]
            self.emuKodiAction = selectedItem[2] #('playermb', 'login', emuKodiCmdsList, autoClose, webServer, addonScript)
            dostawca = self.emuKodiAction[0]
            akcja = self.emuKodiAction[1]
            emuKodiCmdsList = self.emuKodiAction[2]
            autoClose = self.emuKodiAction[3]
            webServer = self.emuKodiAction[4]
            addonScript = self.emuKodiAction[5]
            pythonRunner = '/usr/bin/python'
            if akcja == 'userbouquet':
                plikBukietu = '/etc/enigma2/userbouquet.%s.tv' % dostawca
                emuKodiCmdsList.append('%s %s %s "%s"' % (pythonRunner, os.path.join(emukodi_path, 'e2Bouquets.py'), plikBukietu, addonScript))
            #uruchomienie lancucha komend
            if webServer != '':
                pass
            if len(emuKodiCmdsList) > 0:
                cleanWorkingDir()
                log("===== %s - %s ====" % (dostawca, akcja))
                self.session.openWithCallback(self.emuKodiConsoleCallback ,emukodiConsole, title = "SL %s %s-%s" % (Version, 'EmuKodi', dostawca), 
                                                cmdlist = emuKodiCmdsList, closeOnSuccess = autoClose)
            
    def emuKodiActions(self, selectedItem):
        DBGlog('emuKodiActions(%s)' % str(selectedItem))
        if len(selectedItem) < 3:
            self.session.openWithCallback(self.doNothing,MessageBox, 'Nie wiem co zrobić ;)', MessageBox.TYPE_INFO, timeout = 5)
            return
        else:
            self.emuKodiAction = selectedItem[2] #('playermb', 'login', emuKodiCmdsList, autoClose, webServer, addonScript)
            dostawca = self.emuKodiAction[0]
            akcja = self.emuKodiAction[1]
            if dostawca == 'playermb' and akcja == 'login':
                MsgInfo = "Zostaniesz poproszony o podanie kodu w przeglądarce.\nBędziesz mieć na to maksimum 340 sekund i nie będziesz mógł przerwać.\n\nJesteś gotowy?"
                self.session.openWithCallback(self.emuKodiActionConfirmed, MessageBox, MsgInfo, MessageBox.TYPE_YESNO, default = False, timeout = 15)
                return
            if dostawca == 'cdaplMB' and akcja == 'ActionConfirmed': self.emuKodiActionConfirmed(True)
            elif dostawca == 'canalplusvod' and akcja == 'login': pass
            elif dostawca == 'pgobox' and akcja == 'login': pass
            elif dostawca == 'pilot.wp' and akcja == 'login': pass
            elif akcja == 'userbouquet':
                #pobranie swiezych definicji
                os.system('wget https://raw.githubusercontent.com/azman26/EPGazman/main/azman_channels_mappings.py -O /usr/lib/enigma2/python/Plugins/Extensions/StreamlinkConfig/plugins/azman_channels_mappings.py')
                plikBukietu = '/etc/enigma2/userbouquet.%s.tv' % dostawca
                if os.path.exists(plikBukietu): MsgInfo = "Zaktualizować plik %s ?" % plikBukietu
                else: MsgInfo = "Utworzyć plik %s ?" % plikBukietu
                self.session.openWithCallback(self.emuKodiActionConfirmed, MessageBox, MsgInfo, MessageBox.TYPE_YESNO, default = False, timeout = 15)
                return
            else:
                self.doAction = ('emukodiBouquets.py', 'UNKNOWN', "'%s'" % selectedAction.replace(' ','_'))
        return
