#### tlumaczenia
PluginName = 'StreamlinkConfig'

from Components.config import *
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
PluginLanguageDomain = "plugin-" + PluginName
PluginLanguagePath = resolveFilename(SCOPE_PLUGINS, 'Extensions/%s/locale' % (PluginName))
from Components.Language import language
import gettext, os
    
#### get user configs ####
def readCFG(cfgName, defVal = ''):
    retValue = defVal
    for cfgPath in ['/j00zek/streamlink_defaults/','/hdd/User_Configs', '/etc/streamlink/']:
        if os.path.exists(os.path.join(cfgPath, cfgName)):
            retValue = open(os.path.join(cfgPath, cfgName), 'r').readline().strip()
            break
    return retValue

def localeInit():
    lang = language.getLanguage()[:2]
    os.environ["LANGUAGE"] = lang
    gettext.bindtextdomain(PluginLanguageDomain, PluginLanguagePath)

def mygettext(txt):
    t = gettext.dgettext(PluginLanguageDomain, txt)
    return t

localeInit()
language.addCallback(localeInit)

################################################################################################
config.plugins.streamlinkSRV = ConfigSubsection()

config.plugins.streamlinkSRV.installBouquet   = NoSave(ConfigNothing())
config.plugins.streamlinkSRV.removeBouquet    = NoSave(ConfigNothing())
config.plugins.streamlinkSRV.generateBouquet  = NoSave(ConfigNothing())
config.plugins.streamlinkSRV.downloadBouquet  = NoSave(ConfigNothing())
config.plugins.streamlinkSRV.unmanagedBouquet = NoSave(ConfigNothing())
config.plugins.streamlinkSRV.VLCusingLUA      = NoSave(ConfigNothing())

if os.path.exists('/usr/lib/enigma2/python/Plugins/Extensions/StreamlinkConfig/NoZapWrappers'):
    config.plugins.streamlinkSRV.NoZapWrappers      = NoSave(ConfigYesNo(default = True))
else:
    config.plugins.streamlinkSRV.NoZapWrappers      = NoSave(ConfigYesNo(default = False))
if os.path.exists('/usr/lib/enigma2/python/Plugins/Extensions/YTDLPWrapper'):
    config.plugins.streamlinkSRV.hasYTDLPWrapper     = NoSave(ConfigYesNo(default = True))
else:
    config.plugins.streamlinkSRV.hasYTDLPWrapper     = NoSave(ConfigYesNo(default = False))
if os.path.exists('/usr/lib/enigma2/python/Plugins/Extensions/YTDLWrapper'):
    config.plugins.streamlinkSRV.hasYTDLWrapper      = NoSave(ConfigYesNo(default = True))
else:
    config.plugins.streamlinkSRV.hasYTDLWrapper      = NoSave(ConfigYesNo(default = False))
if os.path.exists('/usr/lib/enigma2/python/Plugins/Extensions/StreamlinkWrapper'):
    config.plugins.streamlinkSRV.hasStreamlinkWrapper      = NoSave(ConfigYesNo(default = True))
else:
    config.plugins.streamlinkSRV.hasStreamlinkWrapper      = NoSave(ConfigYesNo(default = False))
if os.path.exists('/usr/lib/enigma2/python/Plugins/Extensions/e2iplayerWrapper'):
    config.plugins.streamlinkSRV.hase2iplayerWrapper      = NoSave(ConfigYesNo(default = True))
else:
    config.plugins.streamlinkSRV.hase2iplayerWrapper      = NoSave(ConfigYesNo(default = False))

config.plugins.streamlinkSRV.enabled = ConfigYesNo(default = False)
config.plugins.streamlinkSRV.logLevel = ConfigSelection(default = "debug", choices = [("none", _("none")),
                                                                                    ("info", _("info")),
                                                                                    ("warning", _("warning")),
                                                                                    ("error", _("error")),
                                                                                    ("critical", _("critical")),
                                                                                    ("debug", _("debug")),
                                                                                    ("trace", _("trace")),
                                                                              ])
config.plugins.streamlinkSRV.logToFile = ConfigEnableDisable(default = False)
config.plugins.streamlinkSRV.ClearLogFile = ConfigEnableDisable(default = True)
config.plugins.streamlinkSRV.logPath = ConfigSelection(default = "/tmp", choices = [("/home/root", "/home/root"), ("/tmp", "/tmp"), ("/hdd", "/hdd"), ])
config.plugins.streamlinkSRV.PortNumber = ConfigSelection(default = "8088", choices = [("8088", "8088"), ("88", "88"), ])
config.plugins.streamlinkSRV.bufferPath = ConfigText(default = "/tmp", fixed_size = False)
#Tryb pracy streamlinka
config.plugins.streamlinkSRV.binName = ConfigSelection(default = "streamlinkSRV", choices = [("streamlinkSRV", "W 100% zgodny ze streamlinkiem, ale wolniejszy"), ("streamlinkproxySRV", "Korzysta ze streamlinka, szybszy ale niektóre adresy mogą nie działać"),])
config.plugins.streamlinkSRV.SRVmode = ConfigSelection(default = "serviceapp", choices = [("serviceapp", "Standardowo korzysta z odtwarzacza E2"), ("exteplayer3", "Korzysta z zewnętrznego odtwarzacza exteplayer3"),])
config.plugins.streamlinkSRV.DRMmode = ConfigSelection(default = "serviceapp", choices = [("serviceapp", "Standardowo korzysta z odtwarzacza E2"), ("exteplayer3", "Korzysta z zewnętrznego odtwarzacza exteplayer3"),])

config.plugins.streamlinkSRV.Recorder = ConfigEnableDisable(default = False)
config.plugins.streamlinkSRV.RecordMaxTime = ConfigSelection(default = "120", choices = [("120", _("2h")), ("180", _("3h")),])

config.plugins.streamlinkSRV.StandbyMode = ConfigEnableDisable(default = True)

config.plugins.streamlinkSRV.useExtPlayer = ConfigEnableDisable(default = False)
if os.path.exists('/iptvplayer_rootfs/usr/bin/exteplayer3'):
    config.plugins.streamlinkSRV.ActiveExtPlayer = ConfigSelection(default = "sl+sss", choices = [("sl+sss", "sl i exteplayer3 od SSS"), ("sl+sys", "sl i exteplayer3 z OPKG"), ("sss", "exteplayer3 od SSS"), ("sys", "exteplayer3 z OPKG")])
else:
    config.plugins.streamlinkSRV.ActiveExtPlayer = ConfigSelection(default = "sl+sys", choices = [("sl+sys", "sl i exteplayer3 z OPKG"), ("sys", "exteplayer3 z OPKG"),])

if not os.path.exists('/etc/streamlink/ActiveExtPlayer'):
    open('/etc/streamlink/ActiveExtPlayer', 'w').write(config.plugins.streamlinkSRV.ActiveExtPlayer.value)

# pilot.wp.pl
config.plugins.streamlinkSRV.WPusername = ConfigText(readCFG('WPusername'), fixed_size = False)
config.plugins.streamlinkSRV.WPpassword = ConfigPassword(readCFG('WPpassword'), fixed_size = False)
config.plugins.streamlinkSRV.WPbouquet  = NoSave(ConfigNothing())
config.plugins.streamlinkSRV.WPlogin    = NoSave(ConfigNothing())
config.plugins.streamlinkSRV.WPpreferDASH = ConfigEnableDisable(default = False)
config.plugins.streamlinkSRV.WPdevice = ConfigSelection(default = "androidtv", choices = [("androidtv", "Android TV"), ("web", _("web client")), ])
config.plugins.streamlinkSRV.WPvideoDelay = ConfigSelection(default = "0", choices = [("0", _("don't delay")), ("0.25", _("by %s s." % '0.25')),
                                                                                      ("0.5", _("by %s s." % '0.5')), ("0.75", _("by %s s." % '0.75')),
                                                                                      ("1.0", _("by %s s." % '1.0')), ("5.0", _("by %s s." % '5.0'))])

def DBGlog(text):
    print('[SLK]', str(text))
    #open("/tmp/StreamlinkConfig.log", "a").write('%s\n' % str(text))
