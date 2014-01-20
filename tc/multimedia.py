
import gi
# import Tkinter as tk

# from abc import ABCMeta, abstractmethod
from gi.repository import GObject, Gst, Gdk, GLib, GstVideo

from tc import MultimediaException

# from .streamers import H264StreamerBin
# from .receivers import H264ReceiverBin

from twisted.python import log


gi.require_version('Gst', '1.0')
GObject.threads_init()
Gdk.threads_init()
Gst.init(None)


class Element(object):
    """Wrapper arount Gst.Element."""

    def __init__(self, gstelem):
        self._elem = gstelem
    
    def getProperty(self, name):
        return self._elem.get_property(name)
    
    def setProperty(self, name, value):
        self._elem.set_property(name, value)

    def emit(self, signal, *args):
        self._elem.emit(signal, *args)


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
                log.msg("SUCCESS: Gstreamer is PLAYING")

        elif ret == Gst.StateChangeReturn.NO_PREROLL:
            log.msg("NO_PREROLL: make sure you are using a live source")

        elif ret == Gst.StateChangeReturn.SUCCESS: 
            log.msg("SUCCESS: Gstreamer is PLAYING")
            self.stop()
            if failureCallback:
                failureCallback()

        elif ret == Gst.StateChangeReturn.FAILURE:
            log.err(RuntimeError("FAILURE: failed to play"))
            self.stop()

        else:
            raise RuntimeError("FIXME")

    def stop(self):
        ret = self._pipe.set_state(Gst.State.NULL)
        if ret != Gst.StateChangeReturn.SUCCESS:
            raise RuntimeError("FIXME")
    
    def __getattr__(self, name):
        elem = self._pipe.get_by_name(name)
        if not elem:
            if '_' in name:
                return self.__getattr__(name.replace('_', '-'))
            raise MultimediaException("Element<%s> not found" % name)
        return Element(elem)


def cameraFactory(src, resolution=None, framerate=None, xid=None):
    if resolution:
        height, width = map(int, resolution)
    else:
        height, width = 300, 400
    
    framerate = int(framerate) or 30

    if src == 'v4l2':
        captureBin = Gst.ElementFactory.make('v4l2src', None)
    elif src in ['ball', 'smpte']:
        captureBin = Gst.ElementFactory.make('videotestsrc', None)
        captureBin.set_property('pattern', src)
    else:
        raise NotImplementedError("Source '%s' not implemented" % src)
    

    caps = Gst.Caps.from_string('video/x-raw,format=I420,width=%(width)d,'
                                'height=%(height)d,'
                                'framerate=%(framerate)d/1' % locals())
    capsfilter = Gst.ElementFactory.make('capsfilter', None)
    capsfilter.set_property('caps', caps)

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

    gpipe = Gst.Pipeline()
    for elem in [captureBin, capsfilter, tee, x264enc, rtpPay, videosink, udpsink]:
        if not gpipe.add(elem):
            raise MultimediaException("Couldn't build Gst.Pipeline")

    assert gpipe.add(queue0)
    assert gpipe.add(queue1)

    captureBin.link(capsfilter)
    capsfilter.link(tee)

    tee.link(queue0)
    queue0.link(x264enc)
    x264enc.link(rtpPay)
    rtpPay.link(udpsink)

    tee.link(queue1)
    queue1.link(videosink)

    return Pipeline(gpipe, xid)


def screenFactory(port, latency=0, xid=None):

    udpsrc = Gst.ElementFactory.make('udpsrc', None)
    udpsrc.set_property('port', port)

    caps = Gst.Caps.from_string('application/rtp, media=video')
    capsfilter = Gst.ElementFactory.make('capsfilter', None)
    capsfilter.set_property('caps', caps)
    jitterbuffer = Gst.ElementFactory.make('rtpjitterbuffer', None)
    jitterbuffer.set_property('latency', latency)

    depayloader = Gst.ElementFactory.make('rtph264depay', None)
    decoder = Gst.ElementFactory.make('avdec_h264', None)
    decoder.set_property('debug-mv', True)

    videosink = Gst.ElementFactory.make('autovideosink', None)

    gpipe = Gst.Pipeline()
    for elem in [udpsrc, capsfilter, jitterbuffer, depayloader, decoder, videosink]:
        if not gpipe.add(elem):
            raise MultimediaException("Couldn't build Gst.Pipeline")

    udpsrc.link(capsfilter)
    capsfilter.link(jitterbuffer)
    jitterbuffer.link(depayloader)
    depayloader.link(decoder)
    decoder.link(videosink)

    return Pipeline(gpipe, xid)

