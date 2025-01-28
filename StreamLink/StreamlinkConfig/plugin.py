from Components.config import config
from importlib import reload
from Plugins.Plugin import PluginDescriptor
from . import mygettext as _

import os, sys, subprocess, time


import Screens.Standby

DBG = True

def safeSubprocessCMD(myCommand):
    if DBG: print('[SLK] safeSubprocessCMD(%s)' % myCommand)
    with open("/proc/sys/vm/drop_caches", "w") as f: f.write("1\n") #for safety to not get GS due to lack of memory
    subprocess.Popen(myCommand, shell=True)

def SLconfigLeaveStandbyInitDaemon():
    print('[SLK] LeaveStandbyInitDaemon() >>>')
    safeSubprocessCMD('%s restart' % config.plugins.streamlinkSRV.binName.value)

def SLconfigStandbyCounterChanged(configElement):
    print('[SLK] standbyCounterChanged() >>>')
    if config.plugins.streamlinkSRV.StandbyMode.value == True:
        safeSubprocessCMD('streamlinkproxySRV stop;streamlinkproxySRV stop;killall -q exteplayer3')
    else:
        safeSubprocessCMD('killall -q exteplayer3')
    try:
        if SLconfigLeaveStandbyInitDaemon not in Screens.Standby.inStandby.onClose:
            Screens.Standby.inStandby.onClose.append(SLconfigLeaveStandbyInitDaemon)
    except Exception as e:
        print('standbyCounterChanged EXCEPTION: %s' % str(e))

# sessionstart
def sessionstart(reason, session = None):
    if os.path.exists("/tmp/StreamlinkConfig.log"):
        os.remove("/tmp/StreamlinkConfig.log")
    print("[SLK] sessionstart")
    if not os.path.exists('/usr/bin/exteplayer3'):
        print("[SLK] błąd brak zainstalowanego exteplayer3")
    if os.path.exists('/usr/sbin/streamlinkproxy'):
        print("[SLK] UWAGA !!! pakiet streamlinkproxy zainstalowany - to oznacza potencjalne problemy !!!")
    cmds = []
    cmds.append("[ `ps -ef|grep -v grep|grep -c streamlinkproxy` -gt 0 ] && killall streamlinkproxy >/dev/null")
    #cmds.append("/usr/lib/enigma2/python/Plugins/Extensions/StreamlinkConfig/bin/re-initiate.sh")
    cmds.append("[ `ps -ef|grep -v grep|grep -c streamlinkproxySRV` -gt 0 ] && streamlinkproxySRV stop")
    cmds.append("[ `ps -ef|grep -v grep|grep -c streamlinkSRV` -gt 0 ] && streamlinkSRV stop")
    cmds.append('killall -q streamlink')
    cmds.append('killall -q exteplayer3')
    cmds.append('killall -q ffmpeg')
    cmds.append('rm -f /tmp/ffmpeg-*')
    cmds.append('rm -f /tmp/streamlinkpipe-*')
    cmds.append('[ -e /tmp/stream.ts ] && rm -f /tmp/stream.ts')
    if config.plugins.streamlinkSRV.enabled.value:
        cmds.append("%s restart" % config.plugins.streamlinkSRV.binName.value)
    safeSubprocessCMD(';'.join(cmds))
    from Screens.Standby import inStandby
    if reason == 0 and config.plugins.streamlinkSRV.StandbyMode.value == True:
        print('[SLK] reason == 0 and StandbyMode enabled')
        config.misc.standbyCounter.addNotifier(SLconfigStandbyCounterChanged, initial_call=False)
    #global SLeventsWrapperInstance
    #if SLeventsWrapperInstance is None:
    #    SLeventsWrapperInstance = SLeventsWrapper(session)

def timermenu(menuid, **kwargs):
    print("[SLK] timermenu(%s)" % str(menuid))
    if menuid == "timermenu":
        return [(_("Streamlink Timers"), mainRecorder, "streamlinktimer", None)]
    else:
        return []

def mainRecorder(session, **kwargs):
    print("[SLK] mainRecorder()")
    import Plugins.Extensions.StreamlinkConfig.StreamlinkRecorder
    reload(Plugins.Extensions.StreamlinkConfig.StreamlinkRecorder)
    session.open(Plugins.Extensions.StreamlinkConfig.StreamlinkRecorder.StreamlinkRecorderScreen)

def main(session, **kwargs):
    print("[SLK] main")
    #import Plugins.Extensions.StreamlinkConfig.StreamlinkConfiguration
    #reload(Plugins.Extensions.StreamlinkConfig.StreamlinkConfiguration)
    session.open(SLK_Menu)

def Plugins(path, **kwargs):
    myList = [PluginDescriptor(name=_("Streamlink Configuration"), where = PluginDescriptor.WHERE_PLUGINMENU, icon="logo.png", fnc = main, needsRestart = False),
            PluginDescriptor(name="StreamlinkConfig", where = PluginDescriptor.WHERE_SESSIONSTART, fnc = sessionstart, needsRestart = False, weight = -1)
           ]
    if config.plugins.streamlinkSRV.Recorder.value == True:
        myList.append(PluginDescriptor(name="StreamlinkRecorder", description="StreamlinkRecorder", where = [PluginDescriptor.WHERE_MENU], fnc=timermenu))
    return myList

####MENU
from Screens.Screen import Screen
from Components.Pixmap import Pixmap
from Components.Sources.List import List
from Components.ActionMap import ActionMap
from Plugins.Extensions.StreamlinkConfig.version import Version
from Components.MenuList import MenuList
from Tools.LoadPixmap import LoadPixmap

class SLK_Menu(Screen):
    skin = """
<screen position="center,center" size="880,500">
        <widget source="list" render="Listbox" position="0,0" size="880,500" scrollbarMode="showOnDemand">
                <convert type="TemplatedMultiContent">
                        {"template": [
                                MultiContentEntryPixmapAlphaTest(pos = (12, 2), size = (120, 40), png = 0),
                                MultiContentEntryText(pos = (138, 2), size = (760, 40), font=0, flags = RT_HALIGN_LEFT|RT_VALIGN_CENTER, text = 1),
                                ],
                                "fonts": [gFont("Regular", 24)],
                                "itemHeight": 44
                        }
                </convert>
        </widget>
</screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        self.setup_title = "SLK menu v. %s" % Version
        Screen.setTitle(self, self.setup_title)
        self["list"] = List()
        self["setupActions"] = ActionMap(["SetupActions", "MenuActions"],
            {
                    "cancel": self.quit,
                    "ok": self.openSelected,
                    "menu": self.quit,
                    #"down": self.down,
                    #"up": self.up
            }, -2)
        self.setTitle("SLK menu v. %s" % Version)
        self["list"].list = []
        self.createsetup()

    def createsetup(self):
        Mlist = []
        if not os.path.exists('/usr/sbin/streamlinkSRV'):
            Mlist.append(self.buildListEntry("Demon nie zainstalowany", "info.png",'doNothing'))
        elif os.path.exists('/usr/sbin/streamlinkproxy'):
            Mlist.append(self.buildListEntry("streamlinkproxy nie wspierany", "info.png",'doNothing'))
        elif not os.path.exists("/usr/lib/enigma2/python/Plugins/SystemPlugins/ServiceApp/serviceapp.so"):
            Mlist.append(self.buildListEntry("Brak zainstalowanego serviceapp", "info.png",'doNothing'))
        else:
            Mlist.append(self.buildListEntry("Zaprogramuj nagranie", "config.png",'menuRecorderConfig'))
            Mlist.append(self.buildListEntry("Konfiguracja demona", "config.png",'menuDaemonConfig'))
            Mlist.append(self.buildListEntry("Dodaj/Usuń bukiet IPTV", "iptv.png",'menuAvailableIPTVbouquets'))
            Mlist.append(self.buildListEntry("Pobierz/Usuń bukiet IPTV kolegi Azman", "azman.png",'menuIPTVazman'))
            Mlist.append(self.buildListEntry("Zmień framework w serwisach IPTV", "folder.png",'menuIPTVframework'))
            #Mlist.append(self.buildListEntry("Zmień wrapper na serwer 127.0.0.1 w serwisach IPTV", "folder.png",'menuIPTVwrappersrv'))
            Mlist.append(self.buildListEntry("Konfiguacja pilot.wp.pl", "wptv.png",'menuPilotWPpl'))
        self["list"].list = Mlist

    def buildListEntry(self, description, image, optionname):
            image = '/usr/lib/enigma2/python/Plugins/Extensions/StreamlinkConfig/pic/%s' % image
            if os.path.exists(image):
                pixmap = LoadPixmap(image)
            else:
                pixmap = LoadPixmap('/usr/lib/enigma2/python/Plugins/Extensions/StreamlinkConfig/pic/config.png')
            return((pixmap, description, optionname))

    def openSelected(self):
        selected = str(self["list"].getCurrent()[2])
        if selected == 'menuDaemonConfig':
            import Plugins.Extensions.StreamlinkConfig.menuDaemonConfig
            reload(Plugins.Extensions.StreamlinkConfig.menuDaemonConfig)
            self.session.openWithCallback(self.doNothing,Plugins.Extensions.StreamlinkConfig.menuDaemonConfig.StreamlinkConfiguration)
            return
        elif selected == 'menuAvailableIPTVbouquets':
            import Plugins.Extensions.StreamlinkConfig.menuAvailableIPTVbouquets
            reload(Plugins.Extensions.StreamlinkConfig.menuAvailableIPTVbouquets)
            self.session.openWithCallback(self.doNothing,Plugins.Extensions.StreamlinkConfig.menuAvailableIPTVbouquets.StreamlinkConfiguration)
            return
        elif selected == 'menuIPTVazman':
            import Plugins.Extensions.StreamlinkConfig.menuIPTVazman
            reload(Plugins.Extensions.StreamlinkConfig.menuIPTVazman)
            self.session.openWithCallback(self.doNothing,Plugins.Extensions.StreamlinkConfig.menuIPTVazman.StreamlinkConfiguration)
            return
        elif selected == 'menuIPTVframework':
            import Plugins.Extensions.StreamlinkConfig.menuIPTVframework
            reload(Plugins.Extensions.StreamlinkConfig.menuIPTVframework)
            self.session.openWithCallback(self.doNothing,Plugins.Extensions.StreamlinkConfig.menuIPTVframework.StreamlinkConfiguration)
            return
        elif selected == 'menuIPTVwrappersrv':
            import Plugins.Extensions.StreamlinkConfig.menuIPTVwrappersrv
            reload(Plugins.Extensions.StreamlinkConfig.menuIPTVwrappersrv)
            self.session.openWithCallback(self.doNothing,Plugins.Extensions.StreamlinkConfig.menuIPTVwrappersrv.StreamlinkConfiguration)
            return
        elif selected == 'menuPilotWPpl':
            import Plugins.Extensions.StreamlinkConfig.menuPilotWPpl
            reload(Plugins.Extensions.StreamlinkConfig.menuPilotWPpl)
            self.session.openWithCallback(self.doNothing,Plugins.Extensions.StreamlinkConfig.menuPilotWPpl.StreamlinkConfiguration)
            return

    def doNothing(self, retVal = None):
        return
                
    def quit(self):
        self.close()

############################################# SLeventsWrapper #################################
SLeventsWrapperInstance = None

from Components.ServiceEventTracker import ServiceEventTracker#, InfoBarBase
from enigma import iPlayableService#, eServiceCenter, iServiceInformation
#import ServiceReference
from enigma import eTimer
import traceback

class SLeventsWrapper:
    def __init__(self, session):
        #print("[SLK.SLeventsWrapper.__init__] >>>")
        self.session = session
        self.service = None
        self.onClose = []
        self.myCDM = None
        self.deviceCDM = None
        self.runningProcessName = ''
        self.runningPlayer = None
        self.ExtPlayerPID = 0
        self.LastServiceString = ""
        self.RestartServiceTimer = eTimer()
        self.RestartServiceTimer.callback.append(self.__restartServiceTimerCB)
        self.LastPlayedService = None
        self.__event_tracker = ServiceEventTracker(screen=self, eventmap={iPlayableService.evStart: self.__evStart})
        return

    def __findProcessRunningPID(self, ProcessName):
        PID = 0
        if ProcessName != '':
            ProcessName += ' '
            for procPID in os.listdir('/proc'):
                procCMDline = os.path.join('/proc', procPID, 'cmdline')
                if os.path.exists(procCMDline):
                    #print('[SLK.SLeventsWrapper]__findProcessRunningPID procCMDline="%s"\n' % open(procCMDline, 'r').read())
                    if ProcessName in open(procCMDline, 'r').read():
                        PID = procPID
                        break
        return int(PID)
    
    def __getProcessRunningPID(self, ProcessName):
        PID = 0
        pname = '/var/run/%s.pid' % ProcessName
        if os.path.exists(pname):
            PID = open(pname , 'r').read().strip()
        else:
            PID = self.__findProcessRunningPID(ProcessName)
        return int(PID)
    
    def __killRunningPlayer(self):
        # poniższe wyłącza playera i czyści bufor dvb, bez tego  mamy 5s opóźnienia
        if not self.runningPlayer is None:
            print('[SLK.SLeventsWrapper.__killRunningPlayer] self.runningPlayer is not None')
            if self.runningPlayer.poll() is None: 
                print('[SLK.SLeventsWrapper.__killRunningPlayer] sending play_stop to player')
                self.runningPlayer.communicate(input="q\n")[0]
                time.sleep(0.2)
            if self.runningPlayer.poll() is None: 
                print('[SLK.SLeventsWrapper.__killRunningPlayer] terminating player')
                self.runningPlayer.terminate()
                time.sleep(0.2)
            if self.runningPlayer.poll() is None:
                print('[SLK.SLeventsWrapper.__killRunningPlayer] player still running')
            else:
                self.runningPlayer = None

    def __killRunningProcess(self):
        #print('[SLK.SLeventsWrapper]__killRunningProcess self.runningProcessName="%s"' % self.runningProcessName)
        self.__killRunningPlayer()
        cmd2run = []
        if self.runningProcessName != '':
            slPID = self.__getProcessRunningPID(self.runningProcessName)
            if slPID > 0:
                cmd2run.append('kill %s' % slPID)
                cmd2run.append('sleep 0.2') #wait sl to terminate subprocesses
                #cmd2run.append('rm -f /tmp/streamlinkpipe-%s-*' % slPID)
                safeSubprocessCMD(';'.join(cmd2run))
            slPID = self.__findProcessRunningPID(self.runningProcessName)
            if slPID == 0:
                if os.path.exists('/var/run/%s.pid' % self.runningProcessName):
                    os.remove('/var/run/%s.pid' % self.runningProcessName)
                self.runningProcessName = ''
        
    def __restartServiceTimerCB(self):
        #print("[SLK.SLeventsWrapper.__restartServiceTimerCB] >>>")
        self.RestartServiceTimer.stop()
        if self.LastPlayedService is None:
            print("[SLK.SLeventsWrapper.__restartServiceTimerCB] self.LastPlayedService is None, stopping currently playing service")
            self.LastPlayedService = self.session.nav.getCurrentlyPlayingServiceReference()
            self.session.nav.stopService()
            self.restartServiceTimerCBCounter = 0
            self.ExtPlayerPID = 0
            self.RestartServiceTimer.start(2000, True)
        else:
            #print("[SLK.SLeventsWrapper.__restartServiceTimerCB] self.LastPlayedService is NOT None")
            #waiting for exteplayer3 to start
            ExtPlayerPID = self.__findProcessRunningPID('exteplayer3')
            if self.ExtPlayerPID == 0 and ExtPlayerPID > 0:
                self.ExtPlayerPID = ExtPlayerPID
            elif self.ExtPlayerPID > 0 and ExtPlayerPID == 0:
                print("[SLK.SLeventsWrapper.__restartServiceTimerCB] running exteplayer3 exited unexpectly, end of waiting :(" )
                return
            if self.ExtPlayerPID == 0 and self.restartServiceTimerCBCounter < 21:
                print("[SLK.SLeventsWrapper.__restartServiceTimerCB] waiting %s seconds for %s to start" % (self.restartServiceTimerCBCounter, self.runningProcessName))
                self.restartServiceTimerCBCounter += 1
                self.RestartServiceTimer.start(1000, True)
            elif self.ExtPlayerPID != 0 and self.restartServiceTimerCBCounter < 21:
                print("[SLK.SLeventsWrapper.__restartServiceTimerCB] %s started, waiting another second to enable E2 player to see EPG data" % self.runningProcessName)
                self.restartServiceTimerCBCounter += 222
                self.RestartServiceTimer.start(1000, True)
            elif self.ExtPlayerPID == 0 and self.restartServiceTimerCBCounter >= 21:
                print("[SLK.SLeventsWrapper.__restartServiceTimerCB] błąd uruchamiania streamlinka")
                self.restartServiceTimerCBCounter += 1
                self.RestartServiceTimer.start(1000, True)
            else:
                print("[SLK.SLeventsWrapper.__restartServiceTimerCB] %s started, enabling E2 player to see EPG data" % self.runningProcessName)
                self.session.nav.playService(self.LastPlayedService)
                self.LastPlayedService = None
    
    def __evStart(self):
        #print("[SLK.SLeventsWrapper.__evStart] >>>")
        if self.myCDM is None:
            try:
                import pywidevine.cdmdevice.privatecdm
                self.myCDM = pywidevine.cdmdevice.privatecdm.privatecdm()
            except ImportError:
                self.myCDM = False
        
        try:
            service = self.session.nav.getCurrentlyPlayingServiceReference()
            if not service is None:
                CurrentserviceString = service.toString()
                #print("[SLK.SLeventsWrapper]__evStart CurrentserviceString=", CurrentserviceString)
                serviceList = CurrentserviceString.split(":")
                print("[SLK.SLeventsWrapper.__evStart] serviceList=", serviceList)
                if len(serviceList) > 10:
                    url = serviceList[10].strip()
                    if url == '':
                        #print('[SLK.SLeventsWrapper.__evStart] url == ""')
                        self.__killRunningProcess()
                        self.LastServiceString = ''
                    else:
                        if self.LastServiceString == CurrentserviceString:
                            print('[SLK.SLeventsWrapper.__evStart] LastServiceString = CurrentserviceString, nothing to do')
                            return
                        self.LastServiceString = CurrentserviceString
                        self.__killRunningPlayer()#zatrzymuje uruchomiony z kontrolą podprocess, czyli de facto powyższe
                        self.__killRunningProcess()
                        #wybor odtwarzacza
                        if url.startswith('http%3a//127.0.0.1'):
                            print('[SLK.SLeventsWrapper.__evStart] local URL (127.0.0.1), nothing to do')
                            return
                        elif url.startswith('http%3a//slplayer/'):
                            print("[SLK.SLeventsWrapper.__evStart] url.startswith('http%3a//slplayer/')")
                            self.runningProcessName = 'streamlink'
                            cmd2run = []
                            slPID = self.__getProcessRunningPID('streamlink')
                            if slPID > 0:
                                cmd2run.append('kill %s;' % slPID)
                                cmd2run.append('sleep 0.2;') #wait sl to terminate subprocesses
                                cmd2run.append('rm -f /var/run/%s.pid;' % slPID)
                                #cmd2run.append('/usr/bin/killall -q exteplayer3;')
                                #cmd2run.append('/usr/bin/killall -q ffmpeg;')
                                #cmd2run.append('rm -f /tmp/streamlinkpipe-%s-*;' % slPID)
                            if os.path.exists('/tmp/stream.ts'):
                                cmd2run.append('rm -f /tmp/stream.ts;')
                            cmd2run.append('/usr/sbin/streamlink')
                            cmd2run.extend(['-l','none'])
                            if os.path.exists('/iptvplayer_rootfs/usr/bin/exteplayer3'): #wersja sss jest chyba lepsza, jak mamy to ją użyjmy
                                cmd2run.extend(['-p','/iptvplayer_rootfs/usr/bin/exteplayer3'])
                            else:
                                cmd2run.extend(['-p','/usr/bin/exteplayer3'])
                            cmd2run.extend(['--player-http','--verbose-player',"'%s'" % url.replace('http%3a//slplayer/',''), 'best'])
                            safeSubprocessCMD(' '.join(cmd2run))
                            self.RestartServiceTimer.start(100, True)
                            return
        except Exception as e:
            print('[SLK.SLeventsWrapper.__evStart] exception:', str(e))
            print(traceback.format_exc())
