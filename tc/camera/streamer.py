from gi.repository  import GObject, Gst
from tc.utils       import get_logger

__ALL__ = ['Streamer']

GObject.threads_init()
Gst.init(None)
logger = get_logger(__name__)

class Streamer:
    def __init__(self, source):

        # Create elements
        self.pipeline = Gst.parse_launch(
            ' %s ! tee name=t'
            ' t. ! queue ! x264enc tune=zerolatency ! rtph264pay ! multiudpsink name=hd'
            ' t. ! queue ! autovideosink' % source
            )
        self.hdsink = self.pipeline.get_by_name('hd')
        self.hdsink.set_property('sync', True)
        self.hdsink.set_property('send-duplicates', False)

        # Create bus to get events from GStreamer pipeline
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message::eos', self.on_eos)
        self.bus.connect('message::error', self.on_error)
    
    def add_client(self, addr, port):
        logger.info('add_client(): %s:%d', addr, port)
        self.hdsink.emit('add', addr, port)

    def del_client(self, addr, port):
        logger.info('del_client(): %s', addr, port)
        self.hdsink.emit('remove', addr, port)
    
    def on_eos(self, bus, msg):
        logger.error('on_eos() what should I do?')

    def on_error(self, bus, msg):
        logger.error('on_error(): %s', msg.parse_error())
