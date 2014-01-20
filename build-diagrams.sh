#!/bin/bash

cd $(dirname $0)
pyreverse --ignore 'tests' tc

for f in *.dot
do
    dot -Tpng $f -o ${f/dot/png}
    rm $f
done

mv classes_No_Name.png classes.png
mv packages_No_Name.png packages.png

xdg-open classes.png
