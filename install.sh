#!/bin/bash

green="$(tput bold)$(tput setaf 2)"
bold="$(tput bold)"
reset="$(tput sgr0)"

echo ${green}[1/4] ${reset}Updating the package index
apt-get update -q

echo ${green}[2/4] ${reset}Installing dependencies
apt-get install -q python3 python3-tk python3-setuptools python3-gi \
                    gstreamer1.0-{tools,plugins-{good,bad,ugly}} \
                    gir1.2-{gstreamer-1.0,gtk-3.0,gst-rtsp-server-1.0}

tag=https://api.github.com/repos/pslacerda/telecorpo/tags
tag=$(wget -q -O - $tag | awk -F\" '/"name"/ {print $4}' \
    | sort -rnt. -k1,1 -k2,2 | head -1)

tempdir=$(mktemp -d)
tarball=https://github.com/pslacerda/telecorpo/archive/$tag.zip

echo ${green}[3/4] ${reset}Downloading ${bold}version $tag${reset} and extracting the tarball
(cd $tempdir && wget -q $tarball && unzip -q $tag)

echo ${green}[4/4] ${reset}Running setuptools
(cd $tempdir/*/ && python3 setup.py -q install)
(cd $tempdir/*/ && cp telecorpo.desktop /usr/share/applications)

rm -rf $tempdir
