from Components.config import config
from importlib import reload
from Plugins.Plugin import PluginDescriptor
import os, subprocess
import Screens.Standby

def safeSubprocessCMD(myCommand):
    with open("/proc/sys/vm/drop_caches", "w") as f: f.write("1\n") #for safety to not get GS due to lack of memory
    subprocess.Popen(myCommand, shell=True)

def EmuKodiConfigLeaveStandbyInitDaemon():
    print('EmuKodiConfigLeaveStandbyInitDaemon() >>>')
    if os.path.exists('/usr/sbin/emukodiSRV'): safeSubprocessCMD('emukodiSRV restart')

def EmuKodiConfigStandbyCounterChanged(configElement):
    print('EmuKodiConfigStandbyCounterChanged() >>>')
    try:
        if EmuKodiConfigLeaveStandbyInitDaemon not in Screens.Standby.inStandby.onClose:
            Screens.Standby.inStandby.onClose.append(EmuKodiConfigLeaveStandbyInitDaemon)
    except Exception as e:
        print('EmuKodiConfigStandbyCounterChanged EXCEPTION: %s' % str(e))

# sessionstart
def sessionstart(reason, session = None):
    from Screens.Standby import inStandby
    if reason == 0:
        config.misc.standbyCounter.addNotifier(EmuKodiConfigStandbyCounterChanged, initial_call=False)
        if os.path.exists('/usr/sbin/emukodiSRV'): safeSubprocessCMD('emukodiSRV restart')
        safeSubprocessCMD('wget https://raw.githubusercontent.com/azman26/EPGazman/main/azman_channels_mappings.py -O /usr/lib/enigma2/python/Plugins/Extensions/EmuKodi/azman_channels_mappings.py')
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
import time, traceback

class EmuKodiEvents:
    def __init__(self, session):
        #print("[EmuKodiEvents.__init__] >>>")
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
                    #print('[EmuKodiEvents]__findProcessRunningPID procCMDline="%s"\n' % open(procCMDline, 'r').read())
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
            print('[EmuKodiEvents.__killRunningPlayer] self.runningPlayer is not None')
            if self.runningPlayer.poll() is None: 
                print('[EmuKodiEvents.__killRunningPlayer] sending play_stop to player')
                self.runningPlayer.communicate(input="q\n")[0]
                time.sleep(0.2)
            if self.runningPlayer.poll() is None: 
                print('[EmuKodiEvents.__killRunningPlayer] terminating player')
                self.runningPlayer.terminate()
                time.sleep(0.2)
            if self.runningPlayer.poll() is None:
                print('[EmuKodiEvents.__killRunningPlayer] player still running')
            else:
                self.runningPlayer = None

    def __killRunningProcess(self):
        #print('[EmuKodiEvents]__killRunningProcess self.runningProcessName="%s"' % self.runningProcessName)
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
        #print("[EmuKodiEvents.__restartServiceTimerCB] >>>")
        self.RestartServiceTimer.stop()
        if self.LastPlayedService is None:
            print("[EmuKodiEvents.__restartServiceTimerCB] self.LastPlayedService is None, stopping currently playing service")
            self.LastPlayedService = self.session.nav.getCurrentlyPlayingServiceReference()
            self.session.nav.stopService()
            self.restartServiceTimerCBCounter = 0
            self.ExtPlayerPID = 0
            self.RestartServiceTimer.start(2000, True)
        else:
            #print("[EmuKodiEvents.__restartServiceTimerCB] self.LastPlayedService is NOT None")
            #waiting for exteplayer3 to start
            ExtPlayerPID = self.__findProcessRunningPID('exteplayer3')
            if self.ExtPlayerPID == 0 and ExtPlayerPID > 0:
                self.ExtPlayerPID = ExtPlayerPID
            elif self.ExtPlayerPID > 0 and ExtPlayerPID == 0:
                print("[EmuKodiEvents.__restartServiceTimerCB] running exteplayer3 exited unexpectly, end of waiting :(" )
                return
            if self.ExtPlayerPID == 0 and self.restartServiceTimerCBCounter < 21:
                print("[EmuKodiEvents.__restartServiceTimerCB] waiting %s seconds for %s to start" % (self.restartServiceTimerCBCounter, self.runningProcessName))
                self.restartServiceTimerCBCounter += 1
                self.RestartServiceTimer.start(1000, True)
            elif self.ExtPlayerPID != 0 and self.restartServiceTimerCBCounter < 21:
                print("[EmuKodiEvents.__restartServiceTimerCB] %s started, waiting another second to enable E2 player to see EPG data" % self.runningProcessName)
                self.restartServiceTimerCBCounter += 222
                self.RestartServiceTimer.start(1000, True)
            elif self.ExtPlayerPID == 0 and self.restartServiceTimerCBCounter >= 21:
                print("[EmuKodiEvents.__restartServiceTimerCB] błąd uruchamiania streamlinka")
                self.restartServiceTimerCBCounter += 1
                self.RestartServiceTimer.start(1000, True)
            else:
                print("[EmuKodiEvents.__restartServiceTimerCB] %s started, enabling E2 player to see EPG data" % self.runningProcessName)
                self.session.nav.playService(self.LastPlayedService)
                self.LastPlayedService = None
    
    def __evStart(self):
        #print("[EmuKodiEvents.__evStart] >>>")
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
                #print("[EmuKodiEvents]__evStart CurrentserviceString=", CurrentserviceString)
                serviceList = CurrentserviceString.split(":")
                print("[EmuKodiEvents.__evStart] serviceList=", serviceList)
                if len(serviceList) > 10:
                    url = serviceList[10].strip()
                    if url == '':
                        #print('[EmuKodiEvents.__evStart] url == ""')
                        self.__killRunningProcess()
                        self.LastServiceString = ''
                    else:
                        if self.LastServiceString == CurrentserviceString:
                            print('[EmuKodiEvents.__evStart] LastServiceString = CurrentserviceString, nothing to do')
                            return
                        self.LastServiceString = CurrentserviceString
                        if self.myCDM != False and url.startswith('http%3a//cdm/') and self.myCDM.doWhatYouMustDo(url):
                                self.runningPlayer = self.myCDM.player
                                self.runningProcessName = 'streamlink'
                                return
                        self.__killRunningPlayer()#zatrzymuje uruchomiony z kontrolą podprocess, czyli de facto powyższe
                        self.__killRunningProcess()
                        #wybor odtwarzacza
                        if url.startswith('http%3a//127.0.0.1'):
                            print('[EmuKodiEvents.__evStart] local URL (127.0.0.1), nothing to do')
                            return
                        elif url.startswith('http%3a//cdmplayer/'):
                            print("[EmuKodiEvents.__evStart] url.startswith('http%3a//cdmplayer/')")
                            if self.deviceCDM is None: #tutaj, zeby bez sensu nie ladować jak ktos nie ma/nie uzywa
                                try:
                                    import pywidevine.cdmdevice.cdmDevice
                                    self.deviceCDM = pywidevine.cdmdevice.cdmDevice.cdmDevice()
                                except ImportError:
                                    self.deviceCDM = False
                            if self.deviceCDM != False and self.deviceCDM.tryToDoSomething(url):
                                self.runningPlayer = self.deviceCDM.player
                                self.runningProcessName = 'streamlink'
                                #tryToDoSomething take time to proceed and initiate player.
                                # so we need to ...
                                #   - mark this to properly manage __evEnd eventmap (if not managed, killed process & black screen)
                                #   - stop enigma player (if not stopped only back screen)
                                self.RestartServiceTimer.start(100, True)
                            return
        except Exception as e:
            print('[EmuKodiEvents.__evStart] exception:', str(e))
            print(traceback.format_exc())
