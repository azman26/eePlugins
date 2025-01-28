find /usr/lib/enigma2/python/Plugins/Extensions/EmuKodi/site-packages/cdmplayer* -iname *.py | 
  while read F 
  do
    #echo "$F"
    sed "s/streamlink\./cdmplayer./g" -i "$F"
    sed "s/streamlink_cli\./cdmplayer_cli./g" -i "$F"
        sed "s/from streamlink import/from cdmplayer import/g" -i "$F"
        sed "s/from streamlink_cli import/from cdmplayer_cli import/g" -i "$F"
  done
