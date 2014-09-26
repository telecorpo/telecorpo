#!/bin/sh

# create a X display
Xephyr -ac -noreset -screen 800x600 :1 &
XEPHYR_PID=$!
DISPLAY=:1 metacity &

# emulate network
core-gui --start network.imn

# cleanup
kill -15 $XEPHYR_PID
