import logging
import sys

from flask              import Flask
from flask.ext.restful  import reqparse, abort, Api, Resource
from gi.repository      import GObject, Gst, Gtk, Gdk, GdkX11, GstVideo

from tc.client import Client
from tc.utils  import get_logger, ask, print_banner, ipv4, ExitResource, \
                      exit_flask, VideoWindow, find_free_port

logger = get_logger(__name__)
logging.getLogger('werkzeug').setLevel(logging.ERROR)

GObject.threads_init()
Gdk.threads_init()
Gst.init(None)

app = Flask(__name__)
api = Api(app)

class Receiver:
    def __init__(self, port, xid):

        # Create elements
        self.pipeline = Gst.parse_launch(
            ' udpsrc port=%d caps=application/x-rtp ! rtpjitterbuffer'
            ' ! rtph264depay ! decodebin ! xvimagesink' % port
            )

        # Create bus to get events from GStreamer pipeline
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message::eos', self.on_eos)
        self.bus.connect('message::error', self.on_error)

        self.bus.enable_sync_message_emission()
        self.bus.connect('sync-message::element', self.on_sync_message)
        self.xid = xid

        self.pipeline.set_state(Gst.State.PLAYING)
    
    def on_eos(self, bus, msg):
        logger.error('on_eos() what should I do?')

    def on_error(self, bus, msg):
        logger.error('on_error(): %s', msg.parse_error())

    def on_sync_message(self, bus, msg):
        if msg.get_structure().get_name() == 'prepare-window-handle':
            msg.src.set_window_handle(self.xid)


class ScreenClient(Client):

    def __init__(self):
        srv_addr = ask('Server address > ', '127.0.0.1', ipv4)
        srv_port = ask('Server port    > ', 5000, int)
        scr_name = ask('Screen name    > ')
        super().__init__('screens', scr_name, srv_addr, srv_port)
        self.rtp_port = find_free_port()
     

def main():
    print_banner()
    api.add_resource(ExitResource, '/exit')
    try: 
        screen = ScreenClient()
        screen.connect()
    except Exception as e:
        logger.error(e)
        sys.exit(1)
    
    logger.info("Listening RTP/H264 on port %s", screen.rtp_port)
    logger.info("Listening HTTP on port %s", screen.http_port)

    xid, queue = VideoWindow.factory(screen.name)
    receiver = Receiver(screen.rtp_port, xid)

    app.run(port=screen.http_port, debug=False)

if __name__ == '__main__':
    main()
