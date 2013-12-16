import atexit
import logging
import sys

from flask              import Flask
from flask.ext.restful  import reqparse, abort, Api, Resource
from gi.repository      import GObject, Gst
from types              import SimpleNamespace

from tc.client import Client
from tc.utils  import get_logger, ask, print_banner, ipv4

logger = get_logger(__name__)

app = Flask(__name__)
api = Api(app)

GObject.threads_init()
Gst.init(None)

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

        self.pipeline.set_state(Gst.State.PLAYING)
    
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


def ask_user():
    source = 'videotestsrc ! video/x-raw,framerate=30/1,width=480,heigth=360'
    srv_addr = ask('Server address > ', '127.0.0.1', ipv4)
    srv_port = ask('Server port    > ', 5000, int)
    cam_src  = ask('Source element > ', source)
    cam_name = ask('Camera name    > ')
    
    return srv_addr, srv_port, cam_src, cam_name


class StreamerResource(Resource):
     
    parser = reqparse.RequestParser()
    parser.add_argument('addr', type=ipv4, required=True)
    parser.add_argument('rtp_port', type=int,  required=True)

    def post(self, action):
        args = self.parser.parse_args()
        addr = args['addr'] 
        rtp_port = args['rtp_port']

        if action == 'add':
            logger.info("Streaming to %s:%d", addr, rtp_port)
            app.streamer.add_client(addr, rtp_port)
        elif action == 'remove':
            logger.info("Stopping streaming to %s on port %d", addr, rtp_port)
            app.streamer.remove_client(addr, rtp_port)
        else:
            msg = "Unknow action '{}'".format(action)
            logger.info(msg)
            abort(404, message=msg)
        return '', 200

def main():
    print_banner()
    api.add_resource(StreamerResource, '/<string:action>')

    try: 
        srv_addr, srv_port, cam_src, cam_name = ask_user()
        app.streamer = Streamer(cam_src)
        camera = Client('cameras', cam_name, srv_addr, srv_port)
        camera.connect()
    except Exception as e:
        logger.error(e)
        sys.exit(1)

    atexit.register(camera.disconnect)

    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    app.run(port=camera.http_port, debug=False)
# 
if __name__ == '__main__':
    main()
