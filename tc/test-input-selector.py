#!/usr/bin/env python3


from gi.repository import Gst, GObject
from os import popen
from time import sleep

Gst.init()

pipe = Gst.parse_launch(
    "rtspsrc latency=0 location=rtsp://127.0.0.1:13371/video0 ! video/x-raw,format=RGB,width=450,height=360 ! decodebin ! s. "
    "videotestsrc pattern=1 is-live=1 ! video/x-raw,format=I420,width=400,height=33 !  videorate ! videoconvert ! s. "
    "input-selector name=s ! autovideosink"
)

sel = pipe.get_by_name("s")
pipe.set_state(Gst.State.PLAYING)

def switch_timer(selector):
    n_pads = selector.get_property("n-pads")
    active_pad = selector.get_property("active-pad")
    
    Gst.debug_bin_to_dot_file_with_ts(pipe, Gst.DebugGraphDetails.ALL, "pipe")

    if active_pad.get_name() == "sink_0":
        new_pad = selector.get_static_pad("sink_1")
    else:
        new_pad = selector.get_static_pad("sink_0")
    selector.set_property("active-pad", new_pad)
    print(new_pad)
    print("{} {}".format(n_pads, new_pad.get_name()))
    return True

GObject.timeout_add(1000, switch_timer, sel)
GObject.MainLoop().run()
