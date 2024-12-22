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
        safeSubprocessCMD('wget https://raw.githubusercontent.com/azman26/EPGazman/main/azman_channels_mappings.py -O /usr/lib/enigma2/python/Plugins/Extensions/StreamlinkConfig/plugins/azman_channels_mappings.py')

def main(session, **kwargs):
    import Plugins.Extensions.EmuKodi.EmuKodiAddons
    reload(Plugins.Extensions.EmuKodi.EmuKodiAddons)
    session.open(Plugins.Extensions.EmuKodi.EmuKodiAddons.EmuKodi_Menu)

def Plugins(path, **kwargs):
    myList = [PluginDescriptor(name="Konfiguracja dodatków", where = PluginDescriptor.WHERE_PLUGINMENU, icon="logo.png", fnc = main, needsRestart = False),
            PluginDescriptor(name="EmuKodi", where = PluginDescriptor.WHERE_SESSIONSTART, fnc = sessionstart, needsRestart = False, weight = -1)
           ]
    return myList
