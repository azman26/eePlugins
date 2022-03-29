# -*- coding: utf-8 -*-
#
#  BlackHarmonyBoxInfo - Converter
#
# j00zek: this file has changed name just to avoid errors using opkg (situation when file was installed by different pockage)
#

from __future__ import absolute_import #zmiana strategii ladowanie modulow w py2 z relative na absolute jak w py3
from Components.Converter.Converter import Converter
from Components.Converter.Poll import Poll
from Components.Element import cached
from Components.Language import language
import os

try:
    from Tools.HardwareInfoVu import HardwareInfoVu
except:
    from Tools.HardwareInfo import HardwareInfo

def _(text):
    if language.getLanguage()[:2] == 'pl':
        tmp = text.replace('Size','Wielkość').replace('Used','zajęte').replace('Available','wolne').replace('free','wolne').replace('in Use','wykorzystano').replace('No infos available','Brak informacji')
    else:
        tmp = _(text)
    return tmp

class j00zekModBoxInfo(Poll, Converter, object):
    BOXTYPE = 0
    LOAD = 1
    MEMINFO = 2
    UPTIME = 3

    def __init__(self, type):
        Converter.__init__(self, type)
        Poll.__init__(self)
        self.poll_interval = 10000
        self.poll_enabled = True
        self.justValue = False
        if type.find('Value') > -1:
            self.justValue = True
            type = type.replace('Value','')
        if type == "BoxType":
            self.type = self.BOXTYPE
            self.poll_enabled = False
        elif type == "LoadAverage":
            self.type = self.LOAD
        elif type == "MemInfo":
            self.type = self.MEMINFO
        elif type == "Uptime":
            self.type = self.UPTIME
        else:
            self.type = self.BOXTYPE

    def getModel(self):
        retTXT = ''
        try:
            box_info = HardwareInfoVu().get_device_name().upper()
            retTXT = "VU+ %s" % box_info
        except Exception:
            try:
                box_info = HardwareInfo().get_device_name().upper()
                if self.justValue: retTXT = box_info
                else: retTXT = "Model: %s" % box_info
            except Exception:
                if self.justValue: retTXT = "N/A"
                else: retTXT = "Model: N/A"
        return retTXT

    def getLoadAverage(self):
        retTXT = ''
        try:
            with open("/proc/loadavg", 'r') as file:
                load_info = file.read().split()[0:3]
            if self.justValue: retTXT =  "%s" % (', '.join(load_info))
            else: retTXT =  "Load average: %s" % (', '.join(load_info))
        except Exception:
            if self.justValue: retTXT =  "N/A"
            else: retTXT =  "Load average: N/A"
        return retTXT

    def getMemInfo(self):
        retTXT = ''
        try:
            with open("/proc/meminfo", 'r') as file:
                mem_info = file.read().split()
            totalMem = int(mem_info[1])
            freeMem = int(mem_info[7])
            usedMeM = totalMem - freeMem
            usedPercent = "%d %%" % int(usedMeM * 100 / totalMem)
            retTXT =  _("Size: %s, Used: %s (%s), Available: %s") % (self.formatFileSize(totalMem), self.formatFileSize(usedMeM), usedPercent, self.formatFileSize(freeMem))
            if not self.justValue: retTXT =  "MemFree: " + retTXT
        except Exception:
            if self.justValue: retTXT = "N/A"
            else: retTXT =  "MemFree: N/A"
        return retTXT

    def getUptime(self):
        retTXT = ''
        try:
            with open("/proc/uptime", 'r') as file:
                uptime_info = file.read().split()
            total_seconds = float(uptime_info[0])
            MINUTE  = 60
            HOUR    = MINUTE * 60
            DAY     = HOUR * 24
            days    = int( total_seconds / DAY )
            hours   = int( ( total_seconds % DAY ) / HOUR )
            minutes = int( ( total_seconds % HOUR ) / MINUTE )
            seconds = int( total_seconds % MINUTE )
            uptime = ""
            if  language.getLanguage()[:2] == 'pl':
                if days > 0:
                    uptime += str(days) + " " + (days == 1 and "dzień" or "dni" ) + ", "
                if len(uptime) > 0 or hours > 0:
                    uptime += str(hours) + " " + (hours == 1 and "godzina" or "godzin" ) + ", "
                if len(uptime) > 0 or minutes > 0:
                    uptime += str(minutes) + " " + (minutes == 1 and "minuta" or "minut" )
                if self.justValue: retTXT = "%s" % uptime
                else: retTXT =  "Czas pracy: %s" % uptime
            else:
                if days > 0:
                    uptime += str(days) + " " + (days == 1 and "day" or "days" ) + ", "
                if len(uptime) > 0 or hours > 0:
                    uptime += str(hours) + " " + (hours == 1 and "hour" or "hours" ) + ", "
                if len(uptime) > 0 or minutes > 0:
                    uptime += str(minutes) + " " + (minutes == 1 and "minute" or "minutes" )
                if self.justValue: retTXT = "%s" % uptime
                else: retTXT =  "Uptime: %s" % uptime
        except Exception:
            pass
        return retTXT

    @cached
    def getText(self):
        if self.type == self.BOXTYPE:
            return self.getModel()
        elif self.type == self.LOAD:
            return self.getLoadAverage()
        elif self.type == self.MEMINFO:
            return self.getMemInfo()
        elif self.type == self.UPTIME:
            return self.getUptime()
        else:
            return "???"

    text = property(getText)
    
    def formatFileSize(self, size):
        filesize = size
        suffix = ('KB', 'MB', 'GB', 'TB')
        index = 0
        while filesize > 1024:
            filesize = float(filesize) / 1024.0
            index += 1
        filesize_string = "%.2f" % filesize
        if not filesize_string:
            filesize_string = '0'
        return "%s %s" % (filesize_string, suffix[min(index, 4)])
