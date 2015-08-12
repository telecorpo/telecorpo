#!/bin/bash
set -u

print-step() {
    green=$(tput setaf 2)
    bold=$(tput bold)
    underline=$(tput smul)
    reset=$(tput sgr0)

    printf ${green}${bold}
    printf "$1 "
    printf ${reset}

    shift
    printf ${bold}${underline}
    printf "$@"
    printf ${reset}'\n'
}


BUILD_DIR=$PWD/build

rm -rf $BUILD_DIR
mkdir -p $BUILD_DIR

#
#print-step [1/2] 'Packing GstRtspServer'
#GIT_URL='git://anongit.freedesktop.org/gstreamer/gst-rtsp-server'
#GST_VERSION=$(gst-inspect-1.0 --version | awk '{ if (NF==2) print $2 }')
#CONFIGURE_FLAGS="--prefix=/usr --disable-debug"
#
#(cd build
#    git clone --single-branch --branch $GST_VERSION $GIT_URL)
#
#(cd build/gst-rtsp-server
#    sh autogen.sh -- $CONFIGURE_FLAGS
#    test $? != 0 && autoreconf -i && ./configure $CONFIGURE_FLAGS   // XXX!!
#
#    mkdir fake_root
#    make -j$(nproc)
#    make install DESTDIR=$PWD/fake_root
#
#    fpm -s dir -t deb -n libgstrtspserver-1.0 -v $GST_VERSION \
#      -C fake_root \
#      -p libgstrtspserver-1.0_VERSION_ARCH.deb \
#      -d libgstreamer1.0-0 \
#      -d gstreamer1.0-plugins-base \
#      -d gir1.2-glib-2.0)


print-step [2/2] 'Packing TeleCorpo'
GIT_URL='https://github.com/pslacerda/telecorpo.git'
TC_VERSION=$(
    wget -q -O - https://api.github.com/repos/pslacerda/telecorpo/tags |
      perl -ne '/"name": "([0-9].[0-9]*[24680])"/ && print "$1\n"' |
      sort -rnt. -k1,1 -k2,2 | head -n1)

# TODO: add package type 'python3' as in `fpm -s python3`
(cd build
    git clone --single-branch --branch $TC_VERSION $GIT_URL)

(cd build/telecorpo
    mkdir fake_root
    mkdir -p fake_root/usr/share/applications
    fpm -s python -t deb \
#      --python-package-name-prefix python3 \
      --python-pip /usr/bin/pip3 --python-bin /usr/bin/python3 \
      -d libgstrtspserver-1.0 \
      -d gstreamer1.0-plugins-ugly \
      -d python3 \
      -d gir1.2-gstreamer-1.0 \
      telecorpo/setup.py
    cp telecorpo.desktop fake_root/usr/share/applications)
