
import gi
import Tkinter as tk

from abc import ABCMeta, abstractmethod
from gi.repository import GObject, Gst, Gdk, GLib, GstVideo

from tc.exceptions import MultimediaException

from .streamers import H264StreamerBin
from .receivers import H264ReceiverBin

gi.require_version('Gst', '1.0')
GObject.threads_init()
Gdk.threads_init()
Gst.init(None)




class BasePipeline:
    """An Wrapper around Gst.Pipeline
    
    Arguments:
        gpipe: Gstreamer pipeline
    """
    def __init__(self, gpipe):
        self.gpipe = gpipe
        self.bus = gpipe.get_bus()
        self.xid = self._xid = None
        self.isPlaying = False

    def setWindowHandle(self, xid):
        """Sets an window handle for pipeline exibition. It fails if the
        pipeline is already running.

        Arguments:
            xid: window handle (eg XID)

        """
        self.xid = xid
        if self.isPlaying:
            msg = "cannot set window handle when Pipeline is playing"
            raise MultimediaException(msg)
        self.bus.enable_sync_message_emission()
        self.bus.connect('sync-message::element', self._onSyncMessage)

    def _onSyncMessage(self, bus, msg):
        if msg.get_structure().get_name() != 'prepare-window-handle':
            return
        msg.src.set_property('force-aspect-ratio', True)
        msg.src.set_window_handle(self.xid)
        self._xid = self.xid # test artifact
    
    def play(self):
        """Starts the pipeline."""
        self.isPlaying = True
        self.gpipe.set_state(Gst.State.PLAYING)

    def stop(self):
        """Stops the pipeline."""
        self.isPlaying = False
        self.gpipe.set_state(Gst.State.NULL)


class CameraPipeline(BasePipeline):

    def __init__(self, source):
        gpipe, streamer = self._createGPipeline(source)
        BasePipeline.__init__(self, gpipe)
        self.streamer = streamer

    def addClient(self, addr, port):
        """Starts streaming to a client."""
        if not self.isPlaying:
            raise MultimediaException("pipeline isn't playing")
        self.streamer.addClient(addr, port)

    def removeClient(self, addr, port):
        """Stops streaming to a client."""
        if not self.isPlaying:
            raise MultimediaException("pipeline isn't playing")
        self.streamer.removeClient(addr, port)
    
    @classmethod
    def _createGPipeline(cls, source):
        gpipe = Gst.Pipeline()
        
        # Create elements.
        # FIXME use autoimagesink instead
        capturer = cls._capturerElementFactory(source, 'capturer')
        tee = Gst.ElementFactory.make('tee', 'tee')
        streamerQueue = Gst.ElementFactory.make('queue', None)
        streamer = cls.createStreamer('streamer')
        xvimageQueue = Gst.ElementFactory.make('queue', None)
        xvimageCaps = streamer.createCapsFilter(None)
        xvimage = Gst.ElementFactory.make('xvimagesink', 'xvimagesink')
        
        gpipe.add(capturer)
        gpipe.add(tee)
        gpipe.add(streamerQueue)
        gpipe.add(streamer)
        gpipe.add(xvimageQueue)
        gpipe.add(xvimageCaps)
        gpipe.add(xvimage)

        # Link them.
        capturer.link(tee)
        streamerQueue.link(streamer)
        xvimageQueue.link(xvimageCaps)
        xvimageCaps.link(xvimage)

        if not tee.link(streamerQueue):
            msg = "could not link capturer<%s> with encoder"  % source
            raise MultimediaException(msg)
        if not tee.link(xvimageQueue):
            msg = "could not link capturer<%s> with xvimagesink" % source
            raise MultimediaException(msg)

        return gpipe, streamer

    @classmethod
    def createStreamer(cls, name):
        return H264StreamerBin(name)
    
    @classmethod
    def _capturerElementFactory(cls, source, name):
        if source == 'v4l2':
            elem = Gst.ElementFactory.make('v4l2src', name)
        elif source in ['ball', 'smpte', 'snow']:
            elem = Gst.ElementFactory.make('videotestsrc', name)
            elem.set_property('pattern', source)
        else:
            raise NotImplementedError
        return elem 


class ScreenPipeline(BasePipeline):
    
    def __init__(self, port):
        gpipe, receiver = self._createGPipeline(port)
        BasePipeline.__init__(self, gpipe)
        self.receiver = receiver
        self.port = port

    def changeLatency(self, delta):
        self.receiver.changeLatency(delta)

    @classmethod
    def _createGPipeline(cls, port):
        gpipe = Gst.Pipeline()

        # Create elements
        receiver = cls.createReceiver('receiver', port)
        xvimage = Gst.ElementFactory.make('xvimagesink', None)

        gpipe.add(receiver)
        gpipe.add(xvimage)

        # Link them.
        if not receiver.link(xvimage):
            msg = "could not link receiver with xvimagesink"
            raise MultimediaException(msg)
        return gpipe, receiver

    @classmethod
    def createReceiver(self, name, port):
        recv = H264ReceiverBin(name)
        recv.listenPort(port)
        return recv


if __name__ == '__main__':
    import sys, time, os
    tkroot = tk.Tk()
    window = VideoWindow(tkroot, 'untitled')
    
    if sys.argv[1] == 'c':
        pipe = CameraPipeline('ball')
        pipe.setWindowHandle(window.getWindowHandle())
        pipe.play()
        pipe.addClient('127.0.0.1', 1337)
        pipe.addClient('127.0.0.1', 1338)

        debug_dir = '/tmp/camera'
    if sys.argv[1] == 's':

        pipe = ScreenPipeline(1337)
        pipe.setWindowHandle(window.getWindowHandle())
        def changeLatency(evt):
            pipe.changeLatency(+1000)
        window.frame.bind('<Button-3>', changeLatency)
        pipe.play()
        debug_dir = '/tmp/screen'
    
    os.environ['GST_DEBUG_DUMP_DOT_DIR'] = debug_dir
    os.putenv('GST_DEBUG_DUMP_DOT_DIR', debug_dir)
    try:
        tkroot.mainloop()
    except KeyboardInterrupt:
        tkroot.destroy()
        pipe.stop()
