from Components.ActionMap import ActionMap
from Components.config import *
from enigma import eConsoleAppContainer, eDVBDB, eTimer, getDesktop
from Plugins.Extensions.EmuKodi.plugin import safeSubprocessCMD
from Plugins.Extensions.EmuKodi.version import Version
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen

import json, os, signal, sys, subprocess, time, traceback

import Screens.Standby
####MENU
from Components.Pixmap import Pixmap
from Components.Sources.List import List
from Components.MenuList import MenuList
from Tools.LoadPixmap import LoadPixmap
### EmuKodiConfiguration
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Screens.ChoiceBox import ChoiceBox
from Screens.Setup import SetupSummary

from emukodi.xbmcE2 import *
from emukodi.e2Console import emukodiConsole
###

DBG = True

################################################################################################
config.plugins.EmuKodi = ConfigSubsection()
config.plugins.EmuKodi.configItem = NoSave(ConfigNothing())
config.plugins.EmuKodi.MenuInitIndex = NoSave(ConfigInteger(default = 0))
config.plugins.EmuKodi.ConfigurationInitIndex = NoSave(ConfigInteger(default = 0))
config.plugins.EmuKodi.PlayerInitIndex = NoSave(ConfigInteger(default = 0))
config.plugins.EmuKodi.openSelected = NoSave(ConfigText(default = '', fixed_size = False))
config.plugins.EmuKodi.username  = NoSave(ConfigText(default = '', fixed_size = False))
config.plugins.EmuKodi.password  = NoSave(ConfigPassword(default = '', fixed_size = False))
config.plugins.EmuKodi.PBGOklient  = NoSave(ConfigSelection(default = "iCOK", choices = [("iCOK", "iCOK (konto w iPolsat Box)"), 
                                                                                  ("polsatbox", "polsatbox (konto w Polsat Box Go)"), ]))
config.plugins.EmuKodi.LoginCode  = NoSave(ConfigText(default = '', fixed_size = False))


if not os.path.exists('/etc/EmuKodi'):
    os.mkdir('/etc/EmuKodi')

################################################################################################

def readCFG(cfgName, defVal = ''):
    retValue = defVal
    for cfgPath in ['/j00zek/EmuKodi_defaults/','/hdd/User_Configs', '/etc/EmuKodi/']:
        if os.path.exists(os.path.join(cfgPath, cfgName)):
            retValue = open(os.path.join(cfgPath, cfgName), 'r').readline().strip()
            break
    return retValue

def saveCFG(cfgName, val = ''):
    with open(os.path.join('/etc/EmuKodi/', cfgName), 'w') as fw:
        fw.write(val.strip())
        fw.close()

def ensure_str(string2decode):
    if isinstance(string2decode, bytes):
        return string2decode.decode('utf-8', 'ignore')
    return string2decode


class EmuKodi_Menu(Screen):
    skin = """
<screen position="center,center" size="880,540">
        <widget source="list" render="Listbox" position="0,0" size="880,500" scrollbarMode="showOnDemand">
                <convert type="TemplatedMultiContent">
                        {"template": [
                                MultiContentEntryPixmapAlphaTest(pos = (2, 2), size = (120, 40), png = 0),
                                MultiContentEntryText(pos = (138, 2), size = (760, 40), font=0, flags = RT_HALIGN_LEFT|RT_VALIGN_CENTER, text = 1),
                                ],
                                "fonts": [gFont("Regular", 24)],
                                "itemHeight": 45
                        }
                </convert>
        </widget>
        <widget name="key_red"    position="20,510" zPosition="2" size="150,30" foregroundColor="red" valign="center" halign="left" font="Regular;22" transparent="1" />
        <widget name="key_green"  position="170,510" zPosition="2" size="150,30" foregroundColor="green" valign="center" halign="left" font="Regular;22" transparent="1" />
        <widget name="key_yellow"  position="340,510" zPosition="2" size="150,30" foregroundColor="yellow" valign="center" halign="left" font="Regular;22" transparent="1" />
        <widget name="key_ok"  position="490,510" zPosition="2" size="350,30" foregroundColor="gray" valign="center" halign="left" font="Regular;22" transparent="1" />
</screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        print('EmuKodi_Menu.__init__() >>>')
        self.setup_title = "EmuKodi menu v. %s" % Version
        Screen.setTitle(self, self.setup_title)
        self["list"] = List()
        # Buttons
        self["key_red"] = Label("Anuluj")
        self["key_green"] = Label("Uruchom")
        self["key_ok"] = Label('OK - Konfiguracja')
        self.ShowAllServices = False
        self["key_yellow"] = Label('Tryb')

        self["setupActions"] = ActionMap(["EmuKodiMenu"],
            {
                    "cancel": self.quit,
                    "play": self.playSelected,
                    "config": self.configSelected,
                    "keyYellow": self.keyYellow,
            }, -2)
        self.setTitle(self.setup_title)
        try:
            with open('/usr/lib/enigma2/python/Plugins/Extensions/EmuKodi/EmuKodiAddons.json', 'r') as jf:
                self.addonsDict = json.load(jf)
        except Exception as e:
            print('EmuKodi_Menu', str(e))
            self.addonsDict = {'Błąd ładowania danych :(': {"enabled": None, "error": True}}
        self["list"].list = []
        self.createsetup()

    def keyYellow(self):
        if self.ShowAllServices:
            self.ShowAllServices = False
        else:
            self.ShowAllServices = True
        self.createsetup()

    def createsetup(self):
        Mlist = []
        if not os.path.exists("/usr/lib/enigma2/python/Plugins/SystemPlugins/ServiceApp/serviceapp.so"):
            Mlist.append(self.buildListEntry(None, "Brak zainstalowanego serviceapp", "info.png"))
        else:
            cdmStatus = None
            try:
                from  pywidevine.cdmdevice.checkCDMvalidity import testDevice
                cdmStatus = testDevice()
                print('EmuKodi_Menu cdmStatus = "%s"' % cdmStatus)
            except Exception as e: 
                print('EmuKodi_Menu',str(e))
                Mlist.append(self.buildListEntry(None, r'\c00981111' + "*** Błąd ładowania modułu urządzenia cdm ***", "info.png"))
            open('/etc/EmuKodi/cdmStatus','w').write(str(cdmStatus))
            if cdmStatus is None:
                Mlist.append(self.buildListEntry(None, r'\c00981111' + "*** Błąd sprawdzania urządzenia cdm ***", "info.png"))

            if not cdmStatus is None:
                if os.path.exists('/iptvplayer_rootfs/usr/bin/exteplayer3'):
                    if os.path.exists('/etc/EmuKodi/ActiveServiceappPlayer'):
                        ActiveExtPlayer = 'serviceapp'
                    else:
                        ActiveExtPlayer = 'extexplayer3 od SSS'
                    Mlist.append(self.buildListEntry(None, "Aktywny odtwarzacz: %s (OK)" % ActiveExtPlayer, "ActiveServiceappPlayer.cfg"))
                addonKeysList = []
                for addonKey in sorted(self.addonsDict, key=str.casefold):
                    addonDef = self.addonsDict[addonKey]
                    if addonDef.get('error', False):
                        Mlist = []
                        Mlist.append(self.buildListEntry(addonKey))
                    elif addonDef.get('enabled', False) or self.ShowAllServices:
                        Mlist.append(self.buildListEntry(addonKey))

        self["list"].list = Mlist
        self["list"].setCurrentIndex(config.plugins.EmuKodi.MenuInitIndex.value)
        print('EmuKodi_Menu setCurrentIndex', config.plugins.EmuKodi.MenuInitIndex.value)

    def buildListEntry(self, addonKey, description = '', image='',):
        if addonKey is not None:
            addonDef = self.addonsDict[addonKey]
            image = addonDef.get('icon', 'config.png')
            #opis
            if addonDef.get('enabled', False) == False:
                description = "!!! BEZ WSPARCIA %s" % addonKey
            else:
                description = addonKey
        #ladowanie loga
        if image.endswith('.cfg'):
            addonKey = image
            image = 'config.png'
        image = '/usr/lib/enigma2/python/Plugins/Extensions/EmuKodi/pic/%s' % image
        if os.path.exists(image):
            pixmap = LoadPixmap(image)
        else:
            pixmap = LoadPixmap('/usr/lib/enigma2/python/Plugins/Extensions/EmuKodi/pic/config.png')
        return((pixmap, description, addonKey))

    def storeselectedMenuIndex(self):
        try:
            config.plugins.EmuKodi.MenuInitIndex.value = self["list"].getCurrentIndex()
        except Exception:
            config.plugins.EmuKodi.MenuInitIndex.value = self["list"].getSelectedIndex() #np. openvix
        print('getCurrentIndex', config.plugins.EmuKodi.MenuInitIndex.value)

    def configSelected(self):
        SelectedAddonKey = str(self["list"].getCurrent()[2])
        SelectedAddonDef = self.addonsDict.get(SelectedAddonKey, None)
        if SelectedAddonKey == 'ActiveServiceappPlayer.cfg':
            if os.path.exists('/etc/EmuKodi/ActiveServiceappPlayer'):
                os.remove('/etc/EmuKodi/ActiveServiceappPlayer')
            else:
                open("/etc/EmuKodi/ActiveServiceappPlayer", "w").write('')
            self.createsetup()
        elif SelectedAddonDef is None or SelectedAddonDef.get('enabled', False) == False:
            print('EmuKodi_Menu.configSelected(%s) addon not existing or not enabled, exiting' % SelectedAddonKey)
            return
        else:
            self.storeselectedMenuIndex()
            #tworzenie katalogu konfiguracyjnego
            cfgDir = SelectedAddonDef['cfgDir']
            if not os.path.exists('/etc/EmuKodi/%s' % cfgDir):
                os.system('mkdir -p /etc/EmuKodi/%s' % cfgDir)
            #uruchamianie ekranu konfiguracyjnego
            try:
                self.session.openWithCallback(self.doNothing, EmuKodiConfiguration, SelectedAddonDef)
            except Exception as e:
                exc_formatted = traceback.format_exc().strip()
                print('EmuKodi_Menu.configSelected exception:', exc_formatted)
                self.session.openWithCallback(self.doNothing,MessageBox, '...' + '\n'.join(exc_formatted.splitlines()[-6:]), MessageBox.TYPE_INFO)
            return


    def playSelected(self):
        SelectedAddonKey = str(self["list"].getCurrent()[2])
        SelectedAddonDef = self.addonsDict.get(SelectedAddonKey, None)
        if SelectedAddonDef is None or SelectedAddonDef.get('enabled', False) == False:
            print('EmuKodi_Menu.playSelected(%s) addon not existing or not enabled, exiting' % SelectedAddonKey)
            return
        else:
            self.storeselectedMenuIndex()
            #tworzenie katalogu konfiguracyjnego
            cfgDir = SelectedAddonDef['cfgDir']
            if not os.path.exists('/etc/EmuKodi/%s' % cfgDir):
                os.system('mkdir -p /etc/EmuKodi/%s' % cfgDir)
            #uruchamianie ekranu konfiguracyjnego
            try:
                self.session.openWithCallback(self.doNothing, EmuKodiPlayer, SelectedAddonDef)
            except Exception as e:
                import traceback
                exc_formatted = traceback.format_exc().strip()
                print('EmuKodi_Menu.playSelected exception:', exc_formatted)
                self.session.openWithCallback(self.doNothing,MessageBox, '...' + '\n'.join(exc_formatted.splitlines()[-6:]), MessageBox.TYPE_INFO)
            return

    def doNothing(self, retVal = None):
        return
                
    def quit(self):
        self.close()

######################################################################################################################################################

class EmuKodiConfiguration(Screen, ConfigListScreen):
    if getDesktop(0).size().width() == 1920: #definicja skin-a musi byc tutaj, zeby vti sie nie wywalalo na labelach, inaczej trzeba uzywasc zrodla statictext
        skin = """<screen name="EmuKodiConfiguration" position="center,center" size="1000,300" title="EmuKodi configuration">
                    <widget name="config"     position="20,20"   zPosition="1" size="960,220" scrollbarMode="showOnDemand" />
                    <widget name="key_red"    position="20,250"  zPosition="2" size="240,30" foregroundColor="red"    valign="center" halign="left" font="Regular;22" transparent="1" />
                    <widget name="key_green"  position="260,250" zPosition="2" size="240,30" foregroundColor="green"  valign="center" halign="left" font="Regular;22" transparent="1" />
                  </screen>"""
    else:
        skin = """<screen name="EmuKodiConfiguration" position="center,center" size="700,300" title="EmuKodi configuration">
                    <widget name="config"     position="20,20" size="640,225" zPosition="1" scrollbarMode="showOnDemand" />
                    <widget name="key_red"    position="20,250" zPosition="2" size="150,30" foregroundColor="red" valign="center" halign="left" font="Regular;22" transparent="1" />
                    <widget name="key_green"  position="170,250" zPosition="2" size="150,30" foregroundColor="green" valign="center" halign="left" font="Regular;22" transparent="1" />
                  </screen>"""
    def buildList(self):
        Mlist = []
        for cfgFile in self.SelectedAddonDef.get('cfgFiles',[]):
            if '=' in cfgFile:
                defVal = str(cfgFile.split('=')[1])
                cfgFile = cfgFile.split('=')[0]
            else:
                defVal = ""
            if not os.path.exists('/etc/EmuKodi/%s/%s' % (self.addonName,cfgFile)):
                open('/etc/EmuKodi/%s/%s' % (self.addonName,cfgFile), 'w').write(defVal)
                            
        #info
        if os.path.exists('/etc/enigma2/userbouquet.%s.tv' % self.addonName):
            fc = open('/etc/enigma2/userbouquet.%s.tv' % self.addonName,'r').read()
            if 'http%3a//cdmplayer' in fc:
                Mlist.append(getConfigListEntry(r'\c00f2ec73' + "Obecnie kanały bukietu %s korzystają z odtwarzacza zewnętrznego" % self.addonName))
            else:
                Mlist.append(getConfigListEntry(r'\c00f2ec73' + "Obecnie kanały bukietu %s korzystają z serviceapp" % self.addonName))

        #ladowanie konfiguracji
        self.cfgValues2Configs = []
        for cfgValue in self.SelectedAddonDef.get('cfgValues',[]):
            actVal = readCFG('%s/%s' % (self.addonName, cfgValue), defVal = '')
            if cfgValue == 'username':
                config.plugins.EmuKodi.username.value = actVal
                Mlist.append(getConfigListEntry( 'Użytkownik' , config.plugins.EmuKodi.username))
                self.cfgValues2Configs.append(('username', config.plugins.EmuKodi.username))
            elif cfgValue == 'password':
                config.plugins.EmuKodi.password.value = actVal
                Mlist.append(getConfigListEntry( 'Hasło' , config.plugins.EmuKodi.password))
                self.cfgValues2Configs.append(('password', config.plugins.EmuKodi.password))
            elif cfgValue == 'klient':
                config.plugins.EmuKodi.PBGOklient.value = actVal
                Mlist.append(getConfigListEntry( 'Klient' , config.plugins.EmuKodi.PBGOklient))
                self.cfgValues2Configs.append(('klient', config.plugins.EmuKodi.PBGOklient))
            elif cfgValue == 'LoginCode':
                config.plugins.EmuKodi.PBGOklient.value = actVal
                Mlist.append(getConfigListEntry( 'LoginCode' , config.plugins.EmuKodi.LoginCode))
                self.cfgValues2Configs.append(('LoginCode', config.plugins.EmuKodi.LoginCode))

        #Akcje
        login_info = readCFG('%s/login_info' % self.addonName, defVal = '')
        if login_info != '':
            login_info = login_info.replace('[COLOR gold]','').replace('[/COLOR]','')
            Mlist.append(getConfigListEntry(login_info))
        #logowanie
        if len(self.SelectedAddonDef.get('login',[])) > 0:
            Mlist.append(getConfigListEntry( "Logowanie do serwisu", config.plugins.EmuKodi.configItem, 'login'))
        #logowanieTV
        elif len(self.SelectedAddonDef.get('loginTV',[])) > 0:
            Mlist.append(getConfigListEntry('Logowanie kodem urządzenia (w przeglądarce)', config.plugins.EmuKodi.configItem, 'loginTV'))
        #pobieranie listy
        if len(self.SelectedAddonDef.get('userbouquet',[])) > 0:
            Mlist.append(getConfigListEntry( "Generowanie bukietu programów" , config.plugins.EmuKodi.configItem, 'userbouquet'))
        #wylogowanie
        if len(self.SelectedAddonDef.get('logout',[])) > 0:
            Mlist.append(getConfigListEntry( "Wylogowanie z serwisu", config.plugins.EmuKodi.configItem, 'logout'))
        #czyszczenie danych
        Mlist.append(getConfigListEntry( "Czyszczenie/kasowanie konfiguracji", config.plugins.EmuKodi.configItem, 'clean'))
        #wejscie do wtyczki
        Mlist.append(getConfigListEntry( "Wejdź do wtyczki", config.plugins.EmuKodi.configItem, 'openAddon'))
        return Mlist
    
    def __init__(self, session, SelectedAddonDef):
        print('EmuKodiConfiguration.__init__() >>>')
        self.SelectedAddonDef = SelectedAddonDef
        self.addonName = self.SelectedAddonDef.get('cfgDir','')
        self.plikBukietu = '/etc/enigma2/userbouquet.%s.tv' % self.addonName
        self.cfgValues2Configs = []
        self.pythonRunner = '/usr/bin/python'
        self.addonScript = self.SelectedAddonDef.get('addonScript','')
        self.runAddon = '%s %s' % (self.pythonRunner, os.path.join(addons_path, self.addonScript))
        Screen.__init__(self, session)
        self.session = session

        # Summary
        self.setup_title = 'Konfguracja %s' % self.SelectedAddonDef.get('cfgDir','')
        self.onChangedEntry = []

        # Buttons
        self["key_red"] = Label(_("Cancel"))
        self["key_green"] = Label(_("Save"))
        self["key_yellow"] = Label()
        self["key_blue"] = Label()

        # Define Actions
        self["actions"] = ActionMap(["EmuKodiConfiguration"],
            {
                "cancel":   self.exit,
                "red"   :   self.exit,
                "green" :   self.save,
                "ok":       self.Okbutton,
            }, -2)
        
        self.onLayoutFinish.append(self.layoutFinished)
        ConfigListScreen.__init__(self, self.buildList(), on_change = self.changedEntry)

    def save(self):
        for value2Config in self.cfgValues2Configs:
            actVal = readCFG('%s/%s' % (self.addonName, value2Config[0]), defVal = '')
            if readCFG('%s/%s' % (self.addonName, value2Config[0]), defVal = '') != value2Config[1].value:
                saveCFG('%s/%s' % (self.addonName, value2Config[0]), value2Config[1].value)

        self.close(None)
        
    def doNothing(self, ret = False):
        return
        
    def exit(self):
        self.close(None)
        
    def layoutFinished(self):
        self.setTitle(self.setup_title)
        
        if 0: #os.path.exists("/usr/lib/enigma2/python/Plugins/SystemPlugins/ServiceApp/serviceapp.so"):
            self.choicesList = [("Odtwarzacz zewnętrzny (zalecany)","1e"), ("Odtwarzacz zewnętrzny (zalecany dla Vu+)","4097e"), ("gstreamer (root 4097)","4097"),("ServiceApp gstreamer (root 5001)","5001"), ("ServiceApp ffmpeg (root 5002)","5002")]
        else:
            self.choicesList = [("Odtwarzacz zewnętrzny, framework 1 (zalecany)","1e"), ("Odtwarzacz zewnętrzny, framework 4097 (zalecany dla Vu+)","4097e"), ("Odtwarzacz zewnętrzny, framework 5002","5002e")]
        
    def changedEntry(self):
        print('EmuKodiConfiguration.changedEntry() >>>')
        try:
            for x in self.onChangedEntry:
                x()
        except Exception as e:
            print('EmuKodiConfiguration.changedEntry()', str(e))

    def getCurrentEntry(self):
        return self["config"].getCurrent()[0]

    def getCurrentValue(self):
        if len(self["config"].getCurrent()) >= 2:
            return str(self["config"].getCurrent()[1].getText())

    def createSummary(self):
        return SetupSummary

    def buildemuKodiCmdsFor(self, ForVal):
        for cmd in self.SelectedAddonDef.get(ForVal,[]):
            cmdLine = '%s %s' % (self.runAddon, cmd)
            print('EmuKodiConfiguration.buildemuKodiCmdsFor() cmdLine:', cmdLine)
            self.emuKodiCmdsList.append(cmdLine)
    
    def Okbutton(self):
        try:
            curIndex = self["config"].getCurrentIndex()
            selectedItem = self["config"].list[curIndex]
            print('EmuKodiConfiguration.Okbutton() selectedItem:' , str(selectedItem))
            if len(selectedItem) >= 2:
                currItem = selectedItem[1]
                currInfo = selectedItem[0]
                if isinstance(currItem, ConfigText):
                    from Screens.VirtualKeyBoard import VirtualKeyBoard
                    self.session.openWithCallback(self.OkbuttonTextChangedConfirmed, VirtualKeyBoard, title=(currInfo), text = currItem.value)
                elif currItem == config.plugins.EmuKodi.configItem: #bouquets based on KODI plugins
                    self.currAction = selectedItem[2]
                    self.autoClose = False
                    self.emuKodiCmdsList = []
                    
                    if self.currAction == 'login':
                        self.buildemuKodiCmdsFor('login')
                        self.emuKodiActionConfirmed(True)
                        return
                    elif self.currAction == 'loginTV':
                        self.buildemuKodiCmdsFor('loginTV')
                        MsgInfo = "Zostaniesz poproszony o podanie kodu w przeglądarce.\nBędziesz mieć na to maksimum 340 sekund i nie będziesz mógł przerwać.\n\nJesteś gotowy?"
                        self.session.openWithCallback(self.emuKodiActionConfirmed, MessageBox, MsgInfo, MessageBox.TYPE_YESNO, default = False, timeout = 15)
                        return
                    elif self.currAction == 'userbouquet':
                        if os.path.exists(self.plikBukietu):
                            MsgInfo = "Zaktualizować plik %s ?" % self.plikBukietu
                        else:
                            MsgInfo = "Utworzyć plik %s ?" % self.plikBukietu
                        self.session.openWithCallback(self.userbouquetConfirmed, MessageBox, MsgInfo, MessageBox.TYPE_YESNO, default = False, timeout = 15)
                        return
                    elif self.currAction == 'logout':
                        self.buildemuKodiCmdsFor('logout')
                        self.emuKodiActionConfirmed(True)
                        return
                    elif self.currAction == 'clean':
                        self.emuKodiCmdsList.append("rm -f /etc/EmuKodi/%s/*" % self.addonName)
                        self.emuKodiCmdsList.append("echo 'Skasowano wszystkie dane serwisu %s. Wymagany restart!!!'" % self.addonName)
                        self.emuKodiCmdsList.append("sleep 2")
                        self.autoClose = True
                        self.session.openWithCallback(self.emuKodiActionConfirmed, MessageBox, "Na pewno skasować konfigurację %s?" % self.addonName, MessageBox.TYPE_YESNO, default = False, timeout = 15)
                        return
                    elif self.currAction == 'openAddon':
                        try:
                            self.session.openWithCallback(self.doNothing, EmuKodiPlayer, self.SelectedAddonDef)
                        except Exception as e:
                            import traceback
                            exc_formatted = traceback.format_exc().strip()
                            print('EmuKodiConfiguration.playSelected exception:', exc_formatted)
                            self.session.openWithCallback(self.doNothing,MessageBox, '...' + '\n'.join(exc_formatted.splitlines()[-6:]), MessageBox.TYPE_INFO)
                        return
        except Exception as e:
            print('EmuKodiConfiguration.Okbutton() Exception: %s' % str(e))

    def OkbuttonTextChangedConfirmed(self, ret ):
        if ret is None:
            print("EmuKodiConfiguration.OkbuttonTextChangedConfirmed(ret ='%s')" % str(ret))
        else:
            try:
                curIndex = self["config"].getCurrentIndex()
                self["config"].list[curIndex][1].value = ret
            except Exception as e:
                print('EmuKodiConfiguration.OkbuttonTextChangedConfirmed()', str(e))

    def userbouquetConfirmed(self, ret = False):
        if ret:
            self.session.openWithCallback(self.SelectedFramework, ChoiceBox, title = _("Select Multiframework"), list = self.choicesList)

    def SelectedFramework(self, ret):
        if not ret or ret == "None" or isinstance(ret, (int, float)):
            ret = (None,'4097')
        wybranyFramework = ret[1]
        self.emuKodiCmdsList.append("echo 'Pobieranie listy kanałów'")
        self.buildemuKodiCmdsFor('userbouquet')
        self.emuKodiCmdsList.append("sleep 1") #zeby dac czas na zapis plikow kodi.
        self.emuKodiCmdsList.append('%s %s %s "%s" %s' % (self.pythonRunner, os.path.join(emukodi_path, 'e2Bouquets.py'), self.plikBukietu, self.addonScript, wybranyFramework))
        self.emuKodiActionConfirmed(True)

    def emuKodiActionConfirmed(self, ret = False):
        if ret:
            #uruchomienie lancucha komend
            if len(self.emuKodiCmdsList) > 0:
                cleanWorkingDir()
                log("===== %s - %s ====" % (self.addonName, self.currAction))
                self.session.openWithCallback(self.emuKodiConsoleCallback ,emukodiConsole, title = "SL %s %s-%s" % (Version, 'EmuKodi', self.addonName), 
                                                cmdlist = self.emuKodiCmdsList, closeOnSuccess = self.autoClose)

    def emuKodiConsoleCallback(self, ret = False):
        if self.currAction == 'userbouquet':
            #czyszczenie bouquets.tv
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
            #przeladowanie bukietow
            eDVBDB.getInstance().reloadBouquets()
            self.session.openWithCallback(self.doNothing,MessageBox, "Bukiety zostały przeładowane", MessageBox.TYPE_INFO, timeout = 5)

######################################################################################################################################################

class EmuKodiPlayer(Screen):
    skin = """
<screen position="center,center" size="1200,700" flags="wfNoBorder" >
        <widget name="Title" position="5,5" size="1190,30" font="Regular;24" halign="left" noWrap="1" transparent="1" />
        <widget source="list" render="Listbox" position="5,40" size="1190,500" scrollbarMode="showOnDemand" transparent="1" >
                <convert type="TemplatedMultiContent">
                        {"template": [
                                MultiContentEntryPixmapAlphaTest(pos = (10, 10), size = (40, 40), png = 0),
                                MultiContentEntryText(pos = (138, 2), size = (1050, 40), font=0, flags = RT_HALIGN_LEFT|RT_VALIGN_CENTER, text = 1),
                                ],
                                "fonts": [gFont("Regular", 26)],
                                "itemHeight": 45
                        }
                </convert>
        </widget>
        <eLabel position="0,550" size="1200,2"  backgroundColor="#aaaaaa" />
        <widget name="KodiNotificationsAndStatus" position="5,560" size="870,100" font="Regular;16" halign="left" noWrap="0" transparent="1" backgroundColor="#aa000000"/>
</screen>"""

    def __init__(self, session, SelectedAddonDef):
        print('EmuKodiPlayer.__init__() >>>')
        self.prev_running_service = None
        self.SelectedAddonDef = SelectedAddonDef
        self.addonName = self.SelectedAddonDef.get('cfgDir','')
        self.plikBukietu = '/etc/enigma2/userbouquet.%s.tv' % self.addonName
        self.cfgValues2Configs = []
        self.pythonRunner = '/usr/bin/python'
        self.addonScript = self.SelectedAddonDef.get('addonScript','')
        self.runAddon = '%s %s' % (self.pythonRunner, os.path.join(addons_path, self.addonScript))
        self.AddonCmd = ''
        self.AddonCmdsDict = {}
        self.InitAddonCmd = "'1' ' '"
        self.LastAddonCmd = ''
        self.headerStatus = ''
        self.deviceCDM = None
        
        self.KodiDirectoryItemsPath = os.path.join(working_dir, 'xbmcplugin_DirectoryItems')

        Screen.__init__(self, session)
        self.setup_title = "%s Player" % self.addonName
        self["KodiNotificationsAndStatus"] = Label()
        self["Title"] = Label(self.setup_title)
        self["list"] = List()
        self["setupActions"] = ActionMap(["SetupActions", "MenuActions"],
            {
                    "cancel": self.quit,
                    "ok": self.openSelectedMenuItem,
                    "menu": self.quit,
            }, -2)
        try:
            with open('/usr/lib/enigma2/python/Plugins/Extensions/EmuKodi/EmuKodiAddons.json', 'r') as jf:
                self.addonsDict = json.load(jf)
        except Exception as e:
            print('EmuKodiPlayer.__init__() Exception', str(e))
            self.addonsDict = {'Błąd ładowania dodatków :(': {}}
        self["list"].list = []
        self.infoTimer = eTimer()
        self.infoTimer.callback.append(self.showKodiNotificationAndStatus)
        self.timer = eTimer()
        self.timer.callback.append(self.EmuKodiCmdRun)
        self.onShown.append(self._onShown)
        self.EmuKodiCmd = eConsoleAppContainer()
        self.EmuKodiCmd.appClosed.append(self.EmuKodiCmdClosed)
        self.EmuKodiCmd.dataAvail.append(self.EmuKodiCmdAvail)
        try: self.LastPlayedService = self.session.nav.getCurrentlyPlayingServiceReference()
        except Exception: self.LastPlayedService = None
        

    def _onShown(self):
        self.prev_running_service = self.session.nav.getCurrentlyPlayingServiceReference()
        self.AddonCmd = self.InitAddonCmd
        self.headerStatus = ' - inicjalizacja'
        self.LastAddonCmd = ''
        self.timer.start(1000,True) # True=singleshot
        self.infoTimer.start(100)

    def showKodiNotificationAndStatus(self):
        self["Title"].setText(self.setup_title + self.headerStatus)
        
    def EmuKodiCmdRun(self):
        self.timer.stop()
        if self.AddonCmd == '':
            print('EmuKodiPlayer.EmuKodiCmdRun() - nie podano komendy :(')
        elif 0: #self.AddonCmdsDict.get(self.AddonCmd, None) is not None:
            self.EmuKodiCmdClosed('Mlist')
        else:
            self.headerStatus = ' - ładowanie danych'
            cleanWorkingDir()
            cmd2run = '%s %s ' % (self.runAddon, self.AddonCmd)
            print('EmuKodiPlayer.EmuKodiCmdRun() cmd2run "%s"' % cmd2run)
            self.EmuKodiCmd.execute(cmd2run)

    def EmuKodiCmdAvail(self, text = ''):
        text = ensure_str(text)
        if text != '':
            tmpText = self["KodiNotificationsAndStatus"].getText()
            self["KodiNotificationsAndStatus"].setText(tmpText + text)
        
    def EmuKodiCmdClosed(self, retval):
        print('EmuKodiPlayer.EmuKodiCmdClosed(retval = %s)' % retval)
        if retval == 'Mlist':
            self.AddonCmdsDict.get(self.AddonCmd, {})
        else:
            self.headerStatus = ' - analiza otrzymanych danych'
        self.createTree()
        self.headerStatus = ' - oczekiwanie'
        self.LastAddonCmd = self.AddonCmd

    def createTree(self):
        print('EmuKodiPlayer.createTree() >>>')
        Mlist = []
        
        if self.AddonCmd != self.InitAddonCmd:
            Mlist.append(self.buildListEntry({'label': '<< Początek', 'thumbnailImage': None, 'url': self.InitAddonCmd, 'isFolder': True}))
            Mlist.append(self.buildListEntry({'label': '< Cofnij', 'thumbnailImage': None, 'url': self.LastAddonCmd}))
        else:
            if os.path.exists(self.plikBukietu):
                Mlist.append(self.buildListEntry({'label': '>>> Wygenerowany bukiet <<<', 'thumbnailImage': None, 'url': 'plikBukietu'}))

        if self.AddonCmd == 'plikBukietu':
            with open(self.plikBukietu, 'r') as inFile:
                for line in inFile:
                    if line.startswith('#SERVICE'):
                        items = line.split(':')
                        Mlist.append(self.buildListEntry({'label': items[11], 'thumbnailImage': None, 'url': items[10]}))
                    
        
        elif os.path.exists(self.KodiDirectoryItemsPath):
            with open(self.KodiDirectoryItemsPath, 'r') as inFile:
                for line in inFile:
                    try:
                        lineDict = json.loads(line)
                        Mlist.append(self.buildListEntry(lineDict))
                    except Exception as e:
                        exc_formatted = traceback.format_exc().strip()
                        print('EmuKodiPlayer.createTree exception:', exc_formatted)
                        Mlist.append(self.buildListEntry({'label': 'Błąd ładowania linii :(', 'thumbnailImage':'error.png'}))
        self["list"].list = Mlist
        self.AddonCmdsDict[self.AddonCmd] = Mlist
        self.setTitle(self.setup_title + ' - oczekiwanie')

    def buildListEntry(self, lineDict): #&name=...&url=...&thumbnailImage=...&iconlImage=...&url=...
        title = lineDict.get('label', '')
        if lineDict.get('label2', None) is not None:
            if lineDict.get('label2') != lineDict.get('label'):
                title += '' + lineDict.get('label2')
        elif lineDict.get('plot', None) is not None:
            if lineDict.get('plot') != lineDict.get('label'):
                plot = lineDict.get('plot')
                plot = plot.split('[CR]')[0]
                title += ' ' + plot
        #czyszczenie ze smiecia
        title = title.replace('[/COLOR]',r'\c00ffffff')
        title = title.replace('[B]','').replace('[/B]','').replace('[I]','').replace('[/I]','').replace('[CR]','')
        #https://html-color.codes/
        title = title.replace('[COLOR khaki]',r'\c00C3B091').replace('[COLOR gold]',r'\c00ffd700').replace('[COLOR lightblue]',r'\c00add8e6')
        title = title.replace('[COLOR yellowgreen]',r'\c00adff2f')
        #ladowanie image
        if lineDict.get('isFolder', False):
            image = 'folder.png'
        elif lineDict.get('isPlayable', False):
            image = 'movie.png'
        elif not lineDict.get('thumbnailImage', None) is None:
            image = lineDict.get('thumbnailImage')
        elif not lineDict.get('iconImage', None) is None:
            image = lineDict.get('iconImage')
        else:
            image = 'noCover.png'
        if len(image) > 4 and image[-4:] in ('.png','.jpg', '.svg'):
            image = '/usr/lib/enigma2/python/Plugins/Extensions/EmuKodi/pic/%s' % image
            if not os.path.exists(image):
                image = '/usr/lib/enigma2/python/Plugins/Extensions/EmuKodi/pic/noCover.png'
        pixmap = LoadPixmap(image)
        return((pixmap, title, lineDict))

    def stopVideo(self):
        print("[EmuKodiPlayer.stopVideo] >>>")
        if not self.deviceCDM is None:
            self.deviceCDM.stopPlaying() #wyłącza playera i czyści bufor dvb, bez tego  mamy 5s opóźnienia
        for pidFile in ['/var/run/cdmDevicePlayer.pid', '/var/run/emukodiCLI.pid', '/var/run/exteplayer3.pid']:
            if os.path.exists(pidFile):
                pid = open(pidFile, 'r').readline().strip()
                if os.path.exists('/proc/%s' % pid):
                    os.kill(int(pid), signal.SIGTERM) #or signal.SIGKILL
                os.remove(pidFile)

    def playVideo(self, url):
        print("[EmuKodiPlayer.playVideo] url=", url)
        self.session.nav.stopService()
        
        if self.deviceCDM is None: #tutaj, zeby bez sensu nie ladować jak ktos nie ma/nie uzywa
            try:
                import pywidevine.cdmdevice.cdmDevice
                self.deviceCDM = pywidevine.cdmdevice.cdmDevice.cdmDevice()
                print("[EmuKodiPlayer.playVideo] deviceCDM loaded")
            except ImportError:
                self.deviceCDM = False
                print("[EmuKodiPlayer.playVideo] EXCEPTION loading deviceCDM")
        if self.deviceCDM != False:
            if not self.deviceCDM.doWhatYouMustDo(url):
                self.deviceCDM.tryToDoSomething(url)
    
    def openSelectedMenuItem(self):
        self.stopVideo()
        lineDict = self["list"].getCurrent()[2]
        print('EmuKodiPlayer.openSelectedMenuItem',lineDict)
        self["KodiNotificationsAndStatus"].setText(str(lineDict))
        
        if 1: #lineDict.get('isFolder', False):
            self.AddonCmd = str(lineDict.get('url', "?"))
            if self.AddonCmd == "?":
                self["KodiNotificationsAndStatus"].setText("Nie zdefinowana komenda :( ")
                return
            elif self.AddonCmd == "plikBukietu":
                self["KodiNotificationsAndStatus"].setText("ładuje plik bukietu")
                self.createTree()
                return
            elif self.AddonCmd.startswith('http%3a//cdmplayer/'):
                self["KodiNotificationsAndStatus"].setText(self.AddonCmd)
                self.playVideo(self.AddonCmd)
                return
            elif str(lineDict.get('IsPlayable', '')) in ['true','True']:
                self["KodiNotificationsAndStatus"].setText('Play')
                self.playVideo(self.AddonCmd)
                return
            elif self.AddonCmd.startswith('/usr/') and "?" in self.AddonCmd:
                self.AddonCmd = "'1' '?" + self.AddonCmd.split('?')[1] + "' 'resume:false'"
            
            self["KodiNotificationsAndStatus"].setText(self.AddonCmd)
            self.headerStatus = ' - ładowanie %s' % lineDict.get('label', "?")
            self.EmuKodiCmdRun()
        
    def doNothing(self, retVal = None):
        return
                
    def quit(self):
        self.stopVideo()
        if self.prev_running_service:
            self.session.nav.playService(self.prev_running_service)
        self.close()
