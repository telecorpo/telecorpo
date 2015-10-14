#!/bin/bash

TC_VERSION=$(
    wget -q -O - https://api.github.com/repos/pslacerda/telecorpo/tags |
      perl -ne '/"name": "([0-9].[0-9]*[24680])"/ && print "$1\n"' |
      sort -rnt. -k1,1 -k2,2 | head -n1)

mkdir -p fake_root fake_root/usr/share/applications
python3 setup.py install --root=fake_root
cp telecorpo.desktop fake_root/usr/share/applications
fpm -s dir -t deb -n telecorpo -v $TC_VERSION -a all -C fake_root \
    -d python3 \
    -d python3-tk \
    -d python3-gi \
    -d gstreamer1.0-plugins-good \
    -d gstreamer1.0-plugins-bad \
    -d gstreamer1.0-plugins-ugly \
    -d gir1.2-gstreamer-1.0 \
    -d gir1.2-gtk-3.0 \
    -d gir1.2-gst-rtsp-server-1.0

