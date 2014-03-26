#!/bin/bash

VERSION=$1
NAME=telecorpo-$VERSION

sudo apt-get install -y \
    python3 python3-dev python3-setuptools python3-tk python3-gi \
    gstreamer1.0-tools gstreamer1.0-plugins-{good,ugly,bad} gstreamer1.0-libav \
    gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 \
    build-essential

rm -rf /tmp/$NAME

(cd /tmp &&
    wget https://bitbucket.org/pslacerda/telecorpo/downloads/$NAME.tar.gz &&
    tar xzf $NAME.tar.gz)

(cd /tmp/$NAME &&
    sudo python3 setup.py install)
