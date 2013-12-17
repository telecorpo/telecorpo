"""
    tc.streaming
    ~~~~~~~~~~~~

    Streaming bits and bobs.
"""

from gi.repository import GObject, Gst, Gdk
from tc import utils

__ALL__ = ['Streamer', 'Receiver']

GObject.threads_init()
Gdk.threads_init()
Gst.init(None)


LOG = utils.get_logger(__name__)


class BaseStreaming:

    def __init__(self, pipeline, xid=None):
        self.pipeline = pipeline
        self.xid = xid
        self.bus = self.pipeline.get_bus()

        self.bus.add_signal_watch()
        self.bus.connect('message::eos', self.on_eos)
        self.bus.connect('message::error', self.on_error)

        if self.xid:
            self.bus.enable_sync_message_emission()
            self.bus.connect('sync-message::element', self.on_sync_message)

    def start(self):
        self.pipeline.set_state(Gst.State.PLAYING)

    def stop(self):
        self.pipeline.set_state(Gst.State.NULL)

    def on_eos(self, bus, msg):
        """End of stream handler."""
        LOG.error("EOS reached, what should I do?")

    def on_error(self, bus, msg):
        """Error handler."""
        LOG.error("An error occurred. %s", msg.parse_error())

    def on_sync_message(self, bus, msg):
        if msg.get_structure().get_name() == 'prepare-window-handle':
            msg.src.set_window_handle(self.xid)


class Streamer(BaseStreaming):

    def __init__(self, source, xid):
        # pipeline = Gst.parse_launch("""
        #     %s ! tee name=t
        #         .t ! queue ! x264enc tune=zerolatency ! rtph264pay
        #             ! multiudpsink name=hd
        #         .t ! queue ! xvimagesink
        # """ % source)
        pipeline = Gst.parse_launch(
            ' %s ! tee name=t'
            ' t. ! queue ! x264enc tune=zerolatency ! rtph264pay ! multiudpsink name=hd sync=true'
            ' t. ! queue ! xvimagesink' % source)
        super().__init__(pipeline, xid)

        self.hdsink = self.pipeline.get_by_name('hd')
        self.hdsink.set_property('sync', True)
        self.hdsink.set_property('send-duplicates', False)

        # self.ldsink = self.pipeline.get_by_name('ld')
        # self.ldsink.set_property('sync', True)
        # self.ldsink.set_property('send-duplicates', False)

    def add_client(self, addr, port):
        """Start streaming to new client."""
        LOG.info("Start streaming to %s:%d", addr, port)
        self.hdsink.emit('add', addr, port)

    def remove_client(self, addr, port):
        """Stop streaming to client."""
        LOG.info("Stop streaming to %s:%d", addr, port)
        self.hdsink.emit('remove', addr, port)


class Receiver(BaseStreaming):

    def __init__(self, port, xid):
        pipeline = Gst.parse_launch("""
            udpsrc port=%d caps=application/x-rtp ! rtpjitterbuffer
                ! rtph264depay ! decodebin ! xvimagesink
        """ % port)
        super().__init__(pipeline, xid)
