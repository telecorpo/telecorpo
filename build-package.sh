#!/bin/bash

ROOT=$(readlink -f $(dirname $0))

cd $ROOT
rm -rf dist/

python setup.py sdist

cd dist
tar xzf *.tar.gz

cd telecorpo-*/
python setup.py --command-packages=stdeb.command sdist_dsc

cd deb_dist/telecorpo-*/
dpkg-buildpackage -rfakeroot -uc -us

set eux
mv ../*.deb $ROOT
rm -rf $ROOT/dist
