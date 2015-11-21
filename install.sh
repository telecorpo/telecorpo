#!/bin/bash

color="$(tput bold)$(tput setaf 2)"
reset="$(tput sgr0)"

echo ${color}[1/3] Updating the package index${reset}
apt-get update -q

version=$(wget -q -O - https://raw.githubusercontent.com/telecorpo/telecorpo/master/VERSION)
echo ${color}[2/3] Downloading and installing telecorpo $version ${reset}

package=telecorpo_${version}_all.deb
cd /tmp
wget -q https://raw.githubusercontent.com/wiki/pslacerda/telecorpo/$package

dpkg -i $package
sudo apt-get -f install
