#!/bin/bash

version=$1
tempdir=$(mktemp -d)

apt-get install -y python3 python3-setuptools python3-gi \
                   gstreamer1.0-{tools,libav,plugins-{good,bad,ugly}} \
                   gir1.2-{gstreamer-1.0,gtk-3.0}

wget -O $tempdir/$version.zip https://bitbucket.org/pslacerda/telecorpo/get/$version.zip
unzip -d $tempdir $tempdir/$version.zip
python3 $tempdir/pslacerda-telecorpo*/setup.py install

rm -rf $tempdir
