
import json
import base64
import logging
import socket
import sys
import time

from gi.repository import Gst, Gtk, GObject, Gdk
from gi.repository import GdkX11, GstVideo

from .application import Command

LOG = logging.getLogger(__name__)


class Receiver(Gst.Pipeline):

    def __init__(self, url, xids, cache=None, port_range=None):
        super().__init__()
        
        self._url = url
        self._original_xids = xids
        self._xids = None
        self._cache = cache
        self._port_range = port_range
        self.reset()
    
    def reset(self):
        self._xids = self._original_xids.copy()
        bus = self.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect('message::error', self.on_error)
        bus.connect('message::warning', self.on_warning)
        bus.connect('sync-message::element', self.on_sync_message)
        
        src = Gst.ElementFactory.make('rtspsrc')
        src.props.location = self._url
        if self._cache:
            src.props.latency = int(self._cache)
        if self._port_range:
            src.props.port_range = "%d-%d" % self._port_range

        decode = Gst.ElementFactory.make('decodebin')
        convert = Gst.ElementFactory.make('videoconvert')
        tee = Gst.ElementFactory.make('tee')
        
        self.add(src)
        self.add(decode)
        self.add(convert)
        self.add(tee)
        
        src.connect('pad-added', self.on_pad_added, decode)
        decode.connect('pad-added', self.on_pad_added, convert)
        convert.link(tee)

        for xid in self._xids:
            queue = Gst.ElementFactory.make('queue')
            sink = Gst.ElementFactory.make('autovideosink')

            self.add(queue)
            self.add(sink)

            tee.link(queue)
            queue.link(sink)
    
    def on_pad_added(self, src, pad, target):
        assert pad.link(target.get_compatible_pad(pad))

    def on_error(self, bus, msg):
        LOG.error('<%s> %s %s', self._url, *msg.parse_error())
        self.set_state(Gst.State.NULL)
        time.sleep(1)
        self.reset()
             
    def on_warning(self, bus, msg):
        LOG.warn('<%s> %s %s', self._url, *msg.parse_warning())
    
    def on_sync_message(self, bus, msg):
        if msg.get_structure().get_name() != 'prepare-window-handle':
            return
        msg.src.set_window_handle(self._xids.pop())


class Viewer:

    def __init__(self, urls):
        self._urls = urls
        self._drawingareas = {}
        
        control_window = Gtk.Window()
        control_window.connect("delete-event", Gtk.main_quit)
        flowbox = Gtk.FlowBox(homogeneous=True)
        control_window.add(flowbox)
        
        for url in urls:
            area = Gtk.DrawingArea()
            area.set_size_request(400, 300)
            self._drawingareas[url] = [area,]

            def on_click(area, dummy, url):
                notebook.set_current_page(urls.index(url))

            area.set_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            area.connect('button-press-event', on_click, url)
            flowbox.add(area)
        
        video_window = Gtk.Window()
        notebook = Gtk.Notebook(show_tabs=False)
        video_window.add(notebook)

        for url in urls:  
            area = Gtk.DrawingArea()
            self._drawingareas[url].append(area)
            notebook.append_page(area)
            area.realize()

        control_window.show_all()
        video_window.show_all()

    def get_xids(self, url):
        return [da.props.window.get_xid() for da in self._drawingareas[url]]


class ViewCommand(Command):

    name = "view"
    help = "Watch RTSP streams"

    @classmethod
    def configure_argument_parser(cls, parser):
        parser.add_argument('-s', '--sources',
                nargs='+',
                required=True,
                help='Source URLs')
        parser.add_argument('-c', '--cache',
                type=int,
                default=30,
                help="Buffer size in milliseconds")
        parser.add_argument('--port-range',
                nargs=2,
                default=(11100, 11198),
                type=int,
                help="Port range for firewall rules")
    
    @staticmethod
    def main(args):
        viewer = Viewer(args.sources)
        receivers = []
        for url in args.sources:
            receiver = Receiver(url, viewer.get_xids(url), cache=args.cache,
                port_range=args.port_range)
            receiver.set_state(Gst.State.PLAYING)
            receivers.append(receiver)
        try:
            Gtk.main()
        except KeyboardInterrupt:
            Gtk.main_quit()
            for receiver in receivers:
                receiver.set_state(Gst.State.NULL)

