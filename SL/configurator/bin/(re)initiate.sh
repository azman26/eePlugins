#!/bin/sh
plugBinDir='/usr/lib/enigma2/python/Plugins/Extensions/StreamlinkConfig'

pythonType='unknown'
if [ -e /usr/lib/python3.10 ]; then
  pythonType='python3.10'
elif [ -e /usr/lib/python3.9 ]; then
  pythonType='python3.9'
elif [ -e /usr/lib/python2.7 ]; then
  exit 1
fi

if [ -f /usr/sbin/streamlink ] && [ ! -L /usr/sbin/streamlink ];then
  echo
  echo "Wykryto zainstalowaną NIEZNANĄ wersję klienta streamlinka COŚ MOŻE NIE DZIAŁAĆ!!!"
  echo
else
  ln -sf $plugBinDir/bin/streamlinkCLI.py /usr/sbin/streamlink
fi
if [ -f /usr/sbin/streamlinksrv ] && [ ! -L /usr/sbin/streamlinksrv ];then
  echo
  echo "Wykryto zainstalowaną NIEZNANĄ wersję serwera streamlinka COŚ MOŻE NIE DZIAŁAĆ!!!"
  echo
else
  ln -sf $plugBinDir/bin/streamlinksrv.py /usr/sbin/streamlinksrv
  ln -sf $plugBinDir/bin/streamlinksrv.py /etc/init.d/streamlinksrv
  ln -sf /usr/sbin/streamlinksrv /etc/rc3.d/S50streamlinksrv
  ln -sf /usr/sbin/streamlinksrv /etc/rc4.d/S50streamlinksrv
  if `grep -q 'osd.language=pl_PL' </etc/enigma2/settings`; then
    echo ""
    echo "Mod j00zka serwera streamlink zainstalowany"
    echo ""
  else
    echo ""
    echo "Streamlink server mod j00zek installed"
    echo ""
  fi
  mkdir -p /etc/streamlink
  if [ ! -f /etc/streamlink/config ];then
    cp $plugBinDir/bin/etc_streamlink_config.template /etc/streamlink/config
    if [ -e /usr/lib/enigma2/python/Plugins/SystemPlugins/VTIPanel ];then
      ln -sf $plugBinDir/bin/ffmpeg-4-3-1-armhf-static /usr/bin/ffmpeg-4-3-1-armhf-static
      sed -i 's/^#\(ffmpeg-ffmpeg=\)/\1/' /etc/streamlink/config
    fi
  fi
fi

#tworzenie linkow w strukturze drzewa
if [ -e "/usr/lib/$pythonType/site-packages/streamlink" ];then
  echo "Dołączanie pakietów emukodi i streamlink_cli do pythona..."
  ln -sf $plugBinDir/bin/jtools.py /usr/lib/$pythonType/site-packages/streamlink/jtools.py
  ln -sf $plugBinDir/bin/e2config.py /usr/lib/$pythonType/site-packages/streamlink/e2config.py
  ln -sf "$plugBinDir/plugins/emukodi" "/usr/lib/$pythonType/site-packages/emukodi"
  ln -sf "$plugBinDir/plugins/streamlink_cli" "/usr/lib/$pythonType/site-packages/streamlink_cli"
  echo "Dołączanie nieoficjalnych wtyczek j00zka do streamlinka..."
  find -L "/usr/lib/$pythonType/site-packages/streamlink" -name *.py -type l -exec  rm {} +
  find $plugBinDir/plugins/unofficial/ -iname *.py|while read f; do
    #echo "$f"
    f2=`echo "$f"|sed "s;$plugBinDir/plugins/unofficial/;;"`
    #echo "$f2"
    ln -sf "$f" "/usr/lib/$pythonType/site-packages/streamlink/$f2"
  done

  if [ `grep -c '__version_date__' < "/usr/lib/$pythonType/site-packages/streamlink/__init__.py"` -lt 1 ];then
    echo "Modyfikuję __init__.py ..."
    sed -i '/del get_versions/i __version_date__ = get_versions()["date"]' /usr/lib/$pythonType/site-packages/streamlink/__init__.py
  fi

  if [ `grep -c 'except ImportError as e:' < "/usr/lib/$pythonType/site-packages/streamlink/utils/l10n.py"` -lt 1 ];then
    echo "Modyfikuję l10n.py ..."
    sed -i 's/\(^except ImportError\)\(:.*\)/\1 as e\2\n    print(str(e))\n/' /usr/lib/$pythonType/site-packages/streamlink/utils/l10n.py
  fi


  if [ `grep -c '#j00zek_patch 1' < "/usr/lib/$pythonType/site-packages/streamlink_cli/main.py"` -lt 1 ];then
    echo "Modyfikuję streamlink_cli/main.py ..."
    sed -i 's/\(from socks import __version__ as socks_version\)/\n#j00zek_patch 1\ntry: \1\nexcept Exception: from websocket import __version__ as socks_version\n/' /usr/lib/$pythonType/site-packages/streamlink_cli/main.py
  fi

  if [ $pythonType == 'python2.7' ] && [ `grep -c 'from typing' < "/usr/lib/$pythonType/site-packages/streamlink/plugin/plugin.py"` -gt 0 ];then
    echo "Modyfikuję streamlink/plugin/plugin.py ..."
    sed -i 's/from typing/from backports.typing/' /usr/lib/$pythonType/site-packages/streamlink/plugin/plugin.py
  fi

  #przygotowanie wersji pod WP
  cat /usr/lib/$pythonType/site-packages/streamlink/stream/hls.py|sed 's/ffmpegmux import/_ffmpegmux4wp import/' > /usr/lib/$pythonType/site-packages/streamlink/stream/_hls4wp.py
fi
exit 0
