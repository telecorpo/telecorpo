#!/usr/bin/env python3

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

Gst.init(None)


class Pipeline:

    def __init__(self):
        source = self.detect_source()
        self.pipe = Gst.parse_launch("""
            {source} ! videoconvert ! tee name=t 
                t. ! queue ! x264enc tune=zerolatency ! queue ! rtph264pay
                   ! multiudpsink name=sink
                t. ! queue ! xvimagesink
        """.format(**locals()))
        self.sink = self.pipe.get_by_name('sink')
        self.clients = []
    
    def detect_source(self):
        if self.has_firewire():
            return "dv1394src ! dvdemux ! dvdec ! queue"
        elif self.has_v4l2():
            return "v4l2src"
        else:
            return "videotestsrc"

    def has_firewire(self):
        pipe = Gst.parse_launch('dv1394src ! fakesink')
        pipe.set_state(Gst.State.PLAYING)
        ok = True
        if Gst.StateChangeReturn.FAILURE == pipe.get_state(0)[0]:
            ok = False
        pipe.set_state(Gst.State.NULL)
        return ok

    def has_v4l2(self):
        pipe = Gst.parse_launch('v4l2src ! fakesink')
        pipe.set_state(Gst.State.PLAYING)
        ok = False
        if Gst.State.PLAYING == pipe.get_state(0)[-1]:
            ok = True
        pipe.set_state(Gst.State.NULL)
        return ok

    def play(self):
        self.pipe.set_state(Gst.State.PLAYING)

    def stop(self):
        self.pipe.set_state(Gst.State.NULL)

    def add_client(self, addr, port):
        if (addr, port) not in self.clients:
            self.clients.append((addr, port))
            self.sink.emit('add', addr, port)

    def remove_client(self, addr, port):
        if (addr, port) in self.clients:
            self.clients.remove((addr, port))
            self.sink.emit('remove', addr, port)


if __name__ == '__main__':
    pipe = Pipeline()
    pipe.play()
    
    print(pipe.has_firewire())
    print(pipe.has_v4l2())
    try: 
        import time
        while True:
            addr, port = input('? ').split()
            pipe.add_client(addr, int(port))
            time.sleep(0.2)
            print(pipe.sink.get_property('clients'))
    except KeyboardInterrupt:
        pipe.stop()
        pass
