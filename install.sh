#!/bin/bash

latest_version() {
    grep '^v[0-9]\?\.[0-9]\?' | sort -t. -k1,1n -k2,2n | tail -1
}

temp=$(mktemp -d)
flags="--git-dir=$tmpdir/.git"

apt-get install -y \
    git \
    python3 python3-setuptools python3-tk python3-gi \
    gstreamer1.0-tools gstreamer1.0-plugins-{good,ugly,bad} gstreamer1.0-libav \
    gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0


git clone https://bitbucket.org/pslacerda/telecorpo.git $temp
version=$(git $flags tag | latest_version)
git $flags checkout $version
python3 $temp/setup.py install
rm -rf $tmpdir
