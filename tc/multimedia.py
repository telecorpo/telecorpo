
import gi
import Tkinter as tk

from gi.repository import GObject, Gst, Gdk, GLib, GstVideo
from twisted.python import log

from tc import MultimediaException


gi.require_version('Gst', '1.0')
GObject.threads_init()
Gdk.threads_init()
Gst.init(None)


class Pipeline(object):
    """Wrapper around Gst.Pipeline."""

    def __init__(self, gstpipe, xid=None):
        self._pipe = gstpipe
        self._bus = gstpipe.get_bus()

        if xid:
            self.xid = xid
            self._bus.enable_sync_message_emission()
            self._bus.connect('sync-message::element', self._onSyncMessage)

    def _onSyncMessage(self, bus, msg):
        if msg.get_structure().get_name() != 'prepare-window-handle':
            return
        msg.src.set_property('force-aspect-ratio', True)
        msg.src.set_window_handle(self.xid)
        # test artifact
        self._xid = self.xid
    
    def isPlaying(self):
        states = self._pipe.get_state(0)
        if states[-1] == Gst.State.PLAYING:
            return True
        elif states[-1] == Gst.State.VOID_PENDING:
            if states[-2] == Gst.State.PLAYING:
                return True
        return False

    def play(self, failureCallback=None):
        '''
        Arguments:
            failureCallback: called in case of failure

        '''
        if self.isPlaying():
            raise MultimediaException("Gstreamer is already PLAYING")

        ret = self._pipe.set_state(Gst.State.PLAYING)

        if ret == Gst.StateChangeReturn.ASYNC:
            if self.isPlaying():
                log.msg("Gstreamer is PLAYING")

        elif ret == Gst.StateChangeReturn.NO_PREROLL:
            log.msg("Waiting for data, make sure you are using a live source")

        elif ret == Gst.StateChangeReturn.SUCCESS: 
            log.msg("Gstreamer is PLAYING")
            self.stop()
            if failureCallback:
                failureCallback()

        elif ret == Gst.StateChangeReturn.FAILURE:
            log.err(RuntimeError("Failed to play"))
            self.stop()

        else:
            raise RuntimeError("FIXME")

    def stop(self):
        ret = self._pipe.set_state(Gst.State.NULL)
        if ret != Gst.StateChangeReturn.SUCCESS:
            raise RuntimeError("FIXME")
        log.msg("Gstreamer was stopped")
    
    def __getattr__(self, name):
        elem = self._pipe.get_by_name(name)
        if not elem:
            if '_' in name:
                return self.__getattr__(name.replace('_', '-'))
            raise MultimediaException("Element<%s> not found" % name)
        return elem


class CameraPipeline(Pipeline):

    def __init__(self, source, xid, resolution, framerate):
        Pipeline.__init__(self, Gst.Pipeline(), xid)

        height, width = map(int, resolution)

        if source == 'v4l2':
            captureBin = Gst.ElementFactory.make('v4l2src', None)
        elif source in ['ball', 'smpte']:
            captureBin = Gst.ElementFactory.make('videotestsrc', None)
            captureBin.set_property('pattern', source)
        else:
            raise NotImplementedError("Camera source '%s' not implemented"
                                      % source)
        
        caps = Gst.Caps.from_string('video/x-raw,format=I420,width=%(width)d,'
                                    'height=%(height)d,'
                                    'framerate=%(framerate)d/1' % locals())
        capsfilter = Gst.ElementFactory.make('capsfilter', None)
        capsfilter.set_property('caps', caps)

        # cameraBin = Gst.parse_bin_from_description("""
        #     tee name=t 
        #         t. ! queue ! videoscale name=scale ! videorate name=rate
        #            ! x264enc tune=zerolatency speed-preset=ultrafast
        #            ! rtph264pay config-interval=1 ! multiudpsink name=hdsink
        #         t. ! queue ! autovideosink
        #         t. ! queue ! videorate ! x264enc tune=zerolatency speed-preset=ultrafast
        #     """)
        tee = Gst.ElementFactory.make('tee', None)

        queue0 = Gst.ElementFactory.make('queue', None)
        x264enc = Gst.ElementFactory.make('x264enc', None)
        x264enc.set_property('tune', 'zerolatency')
        x264enc.set_property('speed-preset', 'ultrafast')
        rtpPay = Gst.ElementFactory.make('rtph264pay', None)
        rtpPay.set_property('config-interval', 1)
        videosink = Gst.ElementFactory.make('autovideosink', None)

        queue1 = Gst.ElementFactory.make('queue', None)
        udpsink = Gst.ElementFactory.make('multiudpsink', 'multiudpsink')
        udpsink.set_property('sync', True)
        udpsink.set_property('send-duplicates', False)

        for elem in [captureBin, capsfilter, tee, x264enc, rtpPay, videosink, udpsink]:
            if not self._pipe.add(elem):
                raise MultimediaException("Couldn't build Gst.Pipeline")

        assert self._pipe.add(queue0)
        assert self._pipe.add(queue1)

        captureBin.link(capsfilter)
        capsfilter.link(tee)

        tee.link(queue0)
        queue0.link(x264enc)
        x264enc.link(rtpPay)
        rtpPay.link(udpsink)

        tee.link(queue1)
        queue1.link(videosink)

    def addClient(self, addr, port):
        self.multiudpsink.emit('add', addr, port)

    def removeClient(self, addr, port):
        self.multiudpsink.emit('remove', addr, port)


class ScreenPipeline(Pipeline):
    def __init__(self, port, xid):
        gpipe = Gst.parse_launch(
            'udpsrc port=%d ! application/x-rtp,media=video !'
            ' rtpjitterbuffer name=buffer latency=0 ! rtph264depay !'
            ' avdec_h264 ! autovideosink name=videosink' % port)
        Pipeline.__init__(self, gpipe, xid)

    def changeLatency(self, delta):
        latency = int(self.buffer.get_property('latency') + delta)
        if latency <= 0:
            latency = 0
        newBuffer = Gst.ElementFactory.make('rtpjitterbuffer', 'buffer')
        newBuffer.set_property('latency', latency)
        oldBuffer = self.buffer

        
        if not (hasattr(self, 'capsfilter') and hasattr(self, 'depayloader')):
            got = 0
            for elem in self._pipe.children:
                if elem.get_name().startswith('capsfilter'):
                    self.capsfilter = elem
                    got += 1
                elif elem.get_name().startswith('rtph264depay'):
                    self.depayloader = elem
                    got += 1
                elif got == 2:
                    break

        self.stop()

        self.capsfilter.unlink(oldBuffer)
        oldBuffer.unlink(self.depayloader)
        self._pipe.remove(oldBuffer)

        self._pipe.add(newBuffer)
        self.capsfilter.link(newBuffer)
        newBuffer.link(self.depayloader)

        self.play()


class VideoWindow(object):
    # FIXME untested
    def __init__(self, tkroot, title):
        self.tkroot = tkroot
        self.tkroot.wm_title(title)
        self.isFullscreen = False

        self.frame = tk.Frame(tkroot, bg='#000000')
        self.frame.pack(expand=tk.YES, fill=tk.BOTH)

        # Bind window events.
        tkroot.protocol("WM_DELETE_WINDOW", self.quit)
        self.frame.bind('<Double-Button-1>', self.toggleFullscreen)

        # Window handler
        self.xid = self.frame.winfo_id()

    def toggleFullscreen(self, event):
        self.tkroot.attributes('-fullscreen', self.isFullscreen)
        self.isFullscreen = not self.isFullscreen

    def getWindowHandle(self):
        return self.xid

    def quit(self):
        from twisted.internet import reactor
        if reactor.running:
            reactor.stop()
