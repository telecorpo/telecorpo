
from twisted.internet import protocol, reactor
from twisted.protocols import basic

from tc.common import get_logger
from tc.video import StreamingWindow, Pipeline


LOG = get_logger(__name__)


class ScreenWindow(StreamingWindow):

    _description = """
        udpsrc port=%d caps=application/x-rtp
            ! rtpjitterbuffer latency=%d name=buffer ! rtph264depay
            ! decodebin ! xvimagesink
    """ 

    def __init__(self, root, port, name, latency=200):
        pipe = Pipeline(self._description % (port, latency))
        title = '%s - tc-screen' % name
        super(ScreenWindow, self).__init__(root, pipe, title)
        self.port = port

        self.frame.bind('<Button-4>', self._on_mouse_wheel)
        self.frame.bind('<Button-5>', self._on_mouse_wheel)

    def _on_mouse_wheel(self, evt):
        latency = self.pipe.buffer.latency
        text = None
        if evt.num == 5 and latency - 100 >= 0:
            latency -= 100
            text = 'decreased'
        elif evt.num == 4:
            latency += 100
            text = 'increased'
        if text:
            self.pipe.stop()
            self.pipe = Pipeline(self._description % (self.port, latency))
            self.pipe.start()
