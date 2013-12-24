#!/bin/sh

PYVENV=pyvenv-3.3
INSTALL_DIR=/opt/telecorpo
REPOSITORY=https://bitbucket.org/pslacerda/telecorpo.git

apt-get install -y python3.3 python3-enum34 git-core gir1.2-gtk-3.0 
apt-get install -y python3-gi gstreamer1.0-tools gir1.2-gstreamer-1.0 \
                   gir1.2-gst-plugins-base-1.0 gstreamer1.0-plugins-good \
                   gstreamer1.0-plugins-ugly gstreamer1.0-plugins-bad \
                   gstreamer1.0-libav

rm -rf $INSTALL_DIR
git clone $REPOSITORY $INSTALL_DIR
$PYVENV --system-site-packages $INSTALL_DIR/venv
. $INSTALL_DIR/venv/bin/activate
cd $INSTALL_DIR && python setup.py develop
