from __future__ import absolute_import #zmiana strategii ladowanie modulow w py2 z relative na absolute jak w py3
from Components.config import config
from Plugins.Plugin import PluginDescriptor
from . import mygettext as _ , DBGlog

import os, sys
if sys.version_info.major > 2: #PyMajorVersion
    from importlib import reload

import Screens.Standby


def SLconfigLeaveStandbyInitDaemon():
    DBGlog('LeaveStandbyInitDaemon')

def SLconfigStandbyCounterChanged(configElement):
    DBGlog('standbyCounterChanged')
    try:
        if SLconfigLeaveStandbyInitDaemon not in Screens.Standby.inStandby.onClose:
            Screens.Standby.inStandby.onClose.append(SLconfigLeaveStandbyInitDaemon)
    except Exception as e:
        DBGlog('standbyCounterChanged %s' % str(e))

# sessionstart
def sessionstart(reason, session = None):
    if os.path.exists("/tmp/StreamlinkConfig.log"):
        os.remove("/tmp/StreamlinkConfig.log")
    DBGlog("autostart")
    from Screens.Standby import inStandby
    if reason == 0 and config.plugins.streamlinksrv.StandbyMode.value == True:
        DBGlog('reason == 0 and StandbyMode enabled')
        config.misc.standbyCounter.addNotifier(SLconfigStandbyCounterChanged, initial_call=False)



def main(session, **kwargs):
    import Plugins.Extensions.StreamlinkConfig.StreamlinkConfiguration
    reload(Plugins.Extensions.StreamlinkConfig.StreamlinkConfiguration)
    session.open(Plugins.Extensions.StreamlinkConfig.StreamlinkConfiguration.StreamlinkConfiguration)

def Plugins(path, **kwargs):
    return [PluginDescriptor(name=_("Streamlink Configuration"), where = PluginDescriptor.WHERE_PLUGINMENU, fnc = main, needsRestart = False),
            PluginDescriptor(name="StreamlinkConfig", where = PluginDescriptor.WHERE_SESSIONSTART, fnc = sessionstart, needsRestart = False, weight = -1)
           ]
