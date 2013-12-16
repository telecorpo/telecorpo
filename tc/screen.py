import atexit
import logging
import sys

from flask              import Flask
from flask.ext.restful  import reqparse, abort, Api, Resource
from gi.repository      import GObject, Gst
from types              import SimpleNamespace

from tc.client import Client
from tc.utils  import get_logger, ask, print_banner, ipv4, ExitResource

logger = get_logger(__name__)

GObject.threads_init()
Gst.init(None)

app = Flask(__name__)
api = Api(app)


class Receiver:
    def __init__(self, port):

        # Create elements
        self.pipeline = Gst.parse_launch(
            ' udpsrc port=%d caps=application/x-rtp ! rtpjitterbuffer'
            ' ! rtph264depay ! decodebin ! autovideosink' % port
            )

        # Create bus to get events from GStreamer pipeline
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message::eos', self.on_eos)
        self.bus.connect('message::error', self.on_error)

        self.pipeline.set_state(Gst.State.PLAYING)
    
    def on_eos(self, bus, msg):
        logger.error('on_eos() what should I do?')

    def on_error(self, bus, msg):
        logger.error('on_error(): %s', msg.parse_error())


def ask_user():
    srv_addr = ask('Server address > ', '127.0.0.1', ipv4)
    srv_port = ask('Server port    > ', 5000, int)
    scr_name = ask('Screen name    > ')
    
    return srv_addr, srv_port, scr_name


def main():
    print_banner()
    api.add_resource(ExitResource, '/exit')

    try: 
        srv_addr, srv_port, scr_name = ask_user()
        screen = Client('screens', scr_name, srv_addr, srv_port)
        receiver = Receiver(screen.rtp_port)
        screen.connect()
    except Exception as e:
        logger.error(e)
        sys.exit(1)

    atexit.register(screen.disconnect)

    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    app.run(port=screen.http_port, debug=False)
# 
if __name__ == '__main__':
    main()
