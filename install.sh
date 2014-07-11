#!/bin/bash

apt-get install -qq python3 python3-setuptools python3-gi \
                    gstreamer1.0-{tools,libav,plugins-{good,bad,ugly}} \
                    gir1.2-{gstreamer-1.0,gtk-3.0}

tag=https://api.bitbucket.org/1.0/repositories/pslacerda/telecorpo/tags
tag=$(wget -q -O - $tag | python -m json.tool | grep -E '^ {4}\"' \
    | cut -d\" -f2 | sort -rt_ -k1,1 -k2,2 | head -1)

tempdir=$(mktemp -d)
tarball=https://bitbucket.org/pslacerda/telecorpo/get/$tag.zip

echo $tag $tarball
(cd $tempdir && wget -q $tarball && unzip $tag)
(cd $tempdir/*/ && python3 setup.py install)

rm -rf $tempdir
