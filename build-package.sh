#!/bin/bash

ROOT=$(readlink -f $(dirname $0))

cd $ROOT
rm -rf dist/

python setup.py sdist

cd dist
tar xzf *.tar.gz

cd telecorpo-*/
python setup.py --command-packages=stdeb.command sdist_dsc

set eux

cd deb_dist/telecorpo-*/
DEPS=", python-tk, python-gi"
DEPS=$DEPS", gir1.2-gstreamer-1.0, gir1.2-gst-plugins-base-1.0"
DEPS=$DEPS", gstreamer1.0-plugins-good, gstreamer1.0-plugins-ugly"
DEPS=$DEPS", gstreamer1.0-plugins-bad, gstreamer1.0-libav"
sed -i.bak "/^Depends:/s/$/$DEPS/" debian/control
dpkg-buildpackage -rfakeroot -uc -us

cp ../*.deb $ROOT
# mv ../*.deb $ROOT
# rm -rf $ROOT/dist
