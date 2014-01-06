
from twisted.internet import protocol, reactor
from twisted.protocols import basic
from zope import interface

from tc.equipment import IEquipment, ReferenceableEquipment
from tc.video import StreamingWindow, Pipeline



class ScreenEquipment(StreamingWindow):
    interface.implements(IEquipment)

    kind = 'SCREEN'
    _description = """
        udpsrc port=%d caps=application/x-rtp
            ! rtpjitterbuffer latency=%d name=buffer ! rtph264depay
            ! decodebin ! xvimagesink
    """ 

    def __init__(self, tkroot, port, name, latency=0):
        pipe = Pipeline(self._description % (port, latency))
        title = '%s - tc-screen' % name
        StreamingWindow.__init__(self, tkroot, pipe, title)
        self.port = port
        self.name = name

        self.frame.bind('<Button-4>', self._on_mouse_wheel)
        self.frame.bind('<Button-5>', self._on_mouse_wheel)

    def _on_mouse_wheel(self, evt):
        latency = self.pipe.buffer.latency
        text = None
        if evt.num == 5:
            self.changeLatency(-100)
        elif evt.num == 4:
            self.changeLatency(+100)

    def changeLatency(self, delta):
        latency = self.pipe.buffer.latency + delta
        if latency < 0:
            latency = 0
        self.pipe.stop()
        self.pipe = Pipeline(self._description % (self.port, latency))
        self.pipe.setXID(self.xid)
        self.pipe.start()
        
