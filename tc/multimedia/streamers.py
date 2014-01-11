import gi
import Tkinter as tk

from abc import ABCMeta, abstractmethod
from gi.repository import GObject, Gst, Gdk, GLib, GstVideo

from tc.exceptions import MultimediaException


__ALL__ = ['H264StreamerBin']


gi.require_version('Gst', '1.0')
GObject.threads_init()
Gdk.threads_init()
Gst.init(None)


class AbstractStreamerBin(Gst.Bin, object):
    """ I'm a sink element that streams contents to multiple destinations.
    
    TODO testing. Maybe is easier test my implementations becaus I'm abstract.

    Arguments:
        name: element name.

    """

    def __init__(self, name):
        Gst.Bin.__init__(self)
        self.set_name(name)

        # User defined encoding and payloading.
        encoder = self.createEncoder('encoder')
        payloader = self.createPayloader('payloader')
        
        # Streams to multiple destinations.
        self.udpsink = Gst.ElementFactory.make('multiudpsink', 'udpsink')
        self.udpsink.set_property('sync', True)
        self.udpsink.set_property('send_duplicates', False)
        
        # Link elements.
        self.add(encoder)
        self.add(payloader)
        self.add(self.udpsink)

        if not payloader.link(self.udpsink):
            msg = "couldn't link the payloader to multiudpsink."
            raise MultimediaException(msg)

        if not encoder.link(payloader):
            msg = "couldn't link the encoder to payloader."
            raise MultimediaException(msg)

        # This is a sink element.
        try:
            sink = encoder.sinkpads[0]
            self.add_pad(Gst.GhostPad.new('sink', sink))
        except IndexError:
            msg = "failed to get the first sink of encoder."
            raise MultimediaException(msg)
        except:
            # FIXME check failures
            raise

    def addClient(self, addr, port):
        """Add an UDP destination."""
        self.udpsink.emit('add', addr, port)

    def removeClient(self, addr, port):
        """Remove an UDP destination."""
        self.udpsink.emit('remove', addr, port)
        
    def createEncoder(self, name):
        """Streams using this encoder."""
        raise NotImplementedError
    
    def createPayloader(self, name):
        """Something like RTP or raw UDP."""
        raise NotImplementedError
    
    def createCapsFilter(self, name):
        """Capabilities required by the encoder sink pad.
        
        The capturer source pad must have the same caps.
        
        """
        raise NotImplementedError


class H264StreamerBin(AbstractStreamerBin):
    
    def createEncoder(self, name):
        enc = Gst.ElementFactory.make('x264enc', name)
        enc.set_property('tune', 'zerolatency')
        enc.set_property('speed-preset', 'ultrafast')
        return enc
    
    def createPayloader(self, name):
        return Gst.ElementFactory.make('rtph264pay', name)

    def createCapsFilter(self, name):
        caps = Gst.Caps.from_string('video/x-raw,format=I420')
        capsfilter = Gst.ElementFactory.make('capsfilter', name)
        capsfilter.set_property("caps", caps)
        return capsfilter

