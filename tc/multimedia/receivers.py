import gi
import Tkinter as tk

from abc import ABCMeta, abstractmethod
from gi.repository import GObject, Gst, Gdk, GLib, GstVideo

from tc.exceptions import MultimediaException


__ALL__ = ['H264ReceiverBin']


gi.require_version('Gst', '1.0')
GObject.threads_init()
Gdk.threads_init()
Gst.init(None)


class AbstractReceiverBin(Gst.Bin, object):

    def __init__(self, name):
        Gst.Bin.__init__(self)
        self.set_name(name)

        # Receive from single origin.
        self.udpsrc = Gst.ElementFactory.make('udpsrc', 'udpsrc')
        udpCaps = self.createUDPSourceCaps()
        self.udpsrc.set_property('caps', udpCaps)

        # Buffer configuration
        self.jitter = Gst.ElementFactory.make('rtpjitterbuffer', 'jitter')
        self.jitter.set_property('latency', 0)

        # User defined dencoding and depayloading.
        self.depayloader = self.createDepayloader('depayloader')
        decoder = self.createDecoder('decoder')
        
        # Link elements.
        self.add(self.udpsrc)
        self.add(self.jitter)
        self.add(self.depayloader)
        self.add(decoder)
        
        self.udpsrc.link(self.jitter)
        self.jitter.link(self.depayloader)
        self.depayloader.link(decoder)

        # This is a source element.
        try:
            decoderSrc = decoder.srcpads[0]
            self.add_pad(Gst.GhostPad.new('src', decoderSrc))
        except IndexError:
            msg = "failed to get the first src of decoder"
            raise MultimediaException(msg)
        except:
            # FIXME check failures
            raise
    
    def changeLatency(self, delta):
        # Stops pipeline.
        parent = self.get_parent()
        if not parent:
            msg = "Cannot change latency because the pipeline isn't running"
            raise MultimediaException(msg)
        parent.set_state(Gst.State.NULL)

        # Calculate new latency
        latency = self.jitter.get_property('latency')
        latency += int(delta)
        if latency < 0:
            latency = 0

        # Unlink jitter.
        self.udpsrc.unlink(self.jitter)
        self.jitter.unlink(self.depayloader)
        self.remove(self.jitter)

        # Create new jitterbuffer.
        self.jitter = Gst.ElementFactory.make('rtpjitterbuffer', 'jitter')
        self.jitter.set_property('latency', latency)

        # Link new jitter.
        self.add(self.jitter)
        self.udpsrc.link(self.jitter)
        self.jitter.link(self.depayloader)

        # Restarts the pipeline.
        parent.set_state(Gst.State.PLAYING)
        
    def listenPort(self, port):
        self.udpsrc.set_property('port', port)

    def createDecoder(self, name):
        raise NotImplementedError
    
    def createDepayloader(self, name):
        raise NotImplementedError

    def createCapsFilter(self, name):
        raise NotImplementedError


class H264ReceiverBin(AbstractReceiverBin):

    def createDecoder(self, name):
        return Gst.ElementFactory.make('avdec_h264', name)

    def createDepayloader(self, name):
        return Gst.ElementFactory.make('rtph264depay', name)

    def createUDPSourceCaps(self):
        return Gst.Caps.from_string('application/x-rtp')

