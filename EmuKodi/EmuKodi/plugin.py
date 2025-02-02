from Components.config import config
from importlib import reload
from Plugins.Plugin import PluginDescriptor
from Plugins.Extensions.EmuKodi.version import Version
import os, subprocess
import Screens.Standby

print("[EmuKodi.plugin] v:", Version )

def safeSubprocessCMD(myCommand):
    with open("/proc/sys/vm/drop_caches", "w") as f: f.write("1\n") #for safety to not get GS due to lack of memory
    subprocess.Popen(myCommand, shell=True)

def EmuKodiConfigLeaveStandbyInitDaemon():
    print('EmuKodiConfigLeaveStandbyInitDaemon() >>>')
    if os.path.exists('/usr/sbin/emukodiSRV'): safeSubprocessCMD('emukodiSRV restart')

def EmuKodiConfigStandbyCounterChanged(configElement):
    print('EmuKodiConfigStandbyCounterChanged() >>>')
    killCdmDevicePlayer()
    try:
        if EmuKodiConfigLeaveStandbyInitDaemon not in Screens.Standby.inStandby.onClose:
            Screens.Standby.inStandby.onClose.append(EmuKodiConfigLeaveStandbyInitDaemon)
    except Exception as e:
        print('EmuKodiConfigStandbyCounterChanged EXCEPTION: %s' % str(e))

def killCdmDevicePlayer():
    if os.path.exists('/var/run/cdmDevicePlayer.pid'): 
        try:
            pid = open('/var/run/cdmDevicePlayer.pid', 'r').readline().strip()
            os.kill(pid, signal.SIGTERM) #or signal.SIGKILL
            os.remove('/var/run/cdmDevicePlayer.pid')
        except Exception:
            pass

# sessionstart
def sessionstart(reason, session = None):
    from Screens.Standby import inStandby
    if reason == 0:
        config.misc.standbyCounter.addNotifier(EmuKodiConfigStandbyCounterChanged, initial_call=False)
        killCdmDevicePlayer()
        cmds = ''
        if os.path.exists('/usr/sbin/emukodiSRV'): cmds = 'emukodiSRV restart;\n'
        cmds += 'wget -q https://raw.githubusercontent.com/azman26/EPGazman/main/azman_channels_mappings.py -O /usr/lib/enigma2/python/Plugins/Extensions/EmuKodi/azman_channels_mappings.py'
        safeSubprocessCMD(cmds)
    global EmuKodiEventsInstance
    if EmuKodiEventsInstance is None:
        EmuKodiEventsInstance = EmuKodiEvents(session)

def main(session, **kwargs):
    import Plugins.Extensions.EmuKodi.EmuKodiAddons
    reload(Plugins.Extensions.EmuKodi.EmuKodiAddons)
    session.open(Plugins.Extensions.EmuKodi.EmuKodiAddons.EmuKodi_Menu)

def Plugins(path, **kwargs):
    myList = [PluginDescriptor(name="Konfiguracja dodatków", where = PluginDescriptor.WHERE_PLUGINMENU, icon="logo.png", fnc = main, needsRestart = False),
            PluginDescriptor(name="EmuKodi", where = PluginDescriptor.WHERE_SESSIONSTART, fnc = sessionstart, needsRestart = False, weight = -1)
           ]
    return myList

############################################# SLeventsWrapper #################################
EmuKodiEventsInstance = None

from Components.ServiceEventTracker import ServiceEventTracker#, InfoBarBase
from enigma import iPlayableService#, eServiceCenter, iServiceInformation
#import ServiceReference
from enigma import eTimer
import time, signal, traceback

class EmuKodiEvents:
    def __init__(self, session):
        #print("[EmuKodiEvents.__init__] >>>")
        self.session = session
        self.service = None
        self.onClose = []
        self.myCDM = None
        self.deviceCDM = None
        self.runningProcessName = ''
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
                    #print('[EmuKodiEvents]__findProcessRunningPID procCMDline="%s"\n' % open(procCMDline, 'r').read())
                    if ProcessName in open(procCMDline, 'r').read():
                        PID = procPID
                        break
        return int(PID)
    
    def __killRunningPlayer(self):
        print("[EmuKodiEvents.__killRunningPlayer] >>>")
        self.RestartServiceTimer.stop()
        self.LastPlayedService = None
        if not self.deviceCDM is None:
            self.deviceCDM.stopPlaying() #wyłącza playera i czyści bufor dvb, bez tego  mamy 5s opóźnienia
        for pidFile in ['/var/run/cdmDevicePlayer.pid', '/var/run/emukodiCLI.pid', '/var/run/exteplayer3.pid']:
            if os.path.exists(pidFile):
                pid = open(pidFile, 'r').readline().strip()
                if os.path.exists('/proc/%s' % pid):
                    os.kill(int(pid), signal.SIGTERM) #or signal.SIGKILL
                os.remove(pidFile)

    def __restartServiceTimerCB(self):
        #print("[EmuKodiEvents.__restartServiceTimerCB] >>>")
        self.RestartServiceTimer.stop()
        if self.LastPlayedService is None:
            print("[EmuKodiEvents.__restartServiceTimerCB] self.LastPlayedService is None, stopping currently playing service")
            self.LastPlayedService = self.session.nav.getCurrentlyPlayingServiceReference()
            self.session.nav.stopService()
            self.restartServiceTimerCBCounter = 20
            self.ExtPlayerPID = 0
            self.RestartServiceTimer.start(2000, True)
        else:
            #waiting for exteplayer3 to start
            if os.path.exists('/var/run/cdmDevicePlayer.pid'):
                if self.ExtPlayerPID == 0:
                    self.ExtPlayerPID = int(open('/var/run/cdmDevicePlayer.pid', 'r').readline().strip())
                    self.RestartServiceTimer.start(1000, True) # dajemy czas na załadowanie wszystkiego
                elif os.path.exists(os.path.join('/proc', str(self.ExtPlayerPID))):
                    print("[EmuKodiEvents.__restartServiceTimerCB] cdmDevicePlayer uruchomiony, włączam E2 żeby widzieć dane EPG")
                    self.session.nav.playService(self.LastPlayedService)
                    self.LastPlayedService = None
                else:
                    print("[EmuKodiEvents.__restartServiceTimerCB] cdmDevicePlayer niespodziewanie wyłączony")
            elif os.path.exists('/var/run/emukodiCLI.pid'):
                if not os.path.exists('/var/run/exteplayer3.pid'):
                    if self.restartServiceTimerCBCounter > 0:
                        print("[EmuKodiEvents.__restartServiceTimerCB] czekam jeszcze %s sekund na uruchomienie exteplayer3" % self.restartServiceTimerCBCounter)
                        self.restartServiceTimerCBCounter -= 1
                        self.RestartServiceTimer.start(1000, True)
                    else:
                        print("[EmuKodiEvents.__restartServiceTimerCB] czekam jeszcze %s sekund ma uruchomienie exteplayer3" % self.restartServiceTimerCBCounter)
                else:
                    print("[EmuKodiEvents.__restartServiceTimerCB] exteplayer3 uruchomiony, włączam E2 żeby widzieć dane EPG")
                    self.session.nav.playService(self.LastPlayedService)
                    self.LastPlayedService = None
            else:
                print("[EmuKodiEvents.__restartServiceTimerCB] emukodiCLI niespodziewanie wyłączony")
    
    def __evStart(self):
        #print("[EmuKodiEvents.__evStart] >>>")
        try:
            service = self.session.nav.getCurrentlyPlayingServiceReference()
            if not service is None:
                CurrentserviceString = service.toString()
                print("[EmuKodiEvents]__evStart CurrentserviceString=", CurrentserviceString)
                if self.LastServiceString == CurrentserviceString:
                    print('[EmuKodiEvents.__evStart] LastServiceString = CurrentserviceString, nothing to do')
                    return
                self.LastServiceString = CurrentserviceString
                self.__killRunningPlayer()#zatrzymuje uruchomiony z kontrolą podprocess odtwarzacza
                if not ':http%3a//cdmplayer' in CurrentserviceString:
                    print('[EmuKodiEvents.__evStart] no http%3a//cdmplayer service, nothing to do')
                else:
                    serviceList = CurrentserviceString.split(":")
                    print("[EmuKodiEvents.__evStart] serviceList=", serviceList)
                    url = serviceList[10].strip()
                    if url.startswith('http%3a//cdmplayer/'):
                        print("[EmuKodiEvents.__evStart] url.startswith('http%3a//cdmplayer/')")
                        if self.deviceCDM is None: #tutaj, zeby bez sensu nie ladować jak ktos nie ma/nie uzywa
                            try:
                                import pywidevine.cdmdevice.cdmDevice
                                self.deviceCDM = pywidevine.cdmdevice.cdmDevice.cdmDevice()
                                print("[EmuKodiEvents.__evStart] deviceCDM loaded")
                            except ImportError:
                                self.deviceCDM = False
                                print("[EmuKodiEvents.__evStart] EXCEPTION loading deviceCDM")
                        if self.deviceCDM != False:
                            if not self.deviceCDM.doWhatYouMustDo(url):
                                #tryToDoSomething take time to proceed and initiate player.
                                # so we need to ...
                                #   - mark this to properly manage __evEnd eventmap (if not managed, killed process & black screen)
                                #   - stop enigma player (if not stopped only back screen)
                                self.deviceCDM.tryToDoSomething(url)
                                self.RestartServiceTimer.start(100, True)
        except Exception as e:
            print('[EmuKodiEvents.__evStart] EXCEPTION:', str(e))
            print(traceback.format_exc())
