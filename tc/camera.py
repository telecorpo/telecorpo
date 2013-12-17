"""
    tc.camera
    ~~~~~~~~~

    Main camera module.
"""

import flask
import sys

from flask.ext import restful
from flask.ext.restful import reqparse

from tc.client import BaseClient
from tc.streaming import Streamer
from tc.utils import get_logger, ask, banner, ipv4, ExitResource, VideoWindow


LOG = get_logger(__name__)
APP = flask.Flask(__name__)


class CameraClient(BaseClient):
    def __init__(self):
        src = 'videotestsrc pattern=snow '
        src += '! video/x-raw,format=I420,framerate=30/1,width=480,heigth=360'

        srv_addr = ask('Server address > ', '127.0.0.1', ipv4)
        srv_port = ask('Server port    > ', 5000, int)
        self.source = ask('Source element > ', src)
        cam_name = ask('Camera name    > ')
        print()

        super().__init__('cameras', cam_name, srv_addr, srv_port)


class Resource(restful.Resource):

    parser = reqparse.RequestParser()
    parser.add_argument('addr', type=ipv4, required=True)
    parser.add_argument('rtp_port', type=int,  required=True)

    def post(self, action):
        args = self.parser.parse_args()
        addr = args['addr']
        port = args['rtp_port']

        if action == 'add':
            LOG.info("Streaming to %s:%d", addr, port)
            APP.streamer.add_client(addr, port)

        elif action == 'remove':
            LOG.info("Stopping streaming to %s on port %d", addr, port)
            APP.streamer.remove_client(addr, port)

        else:
            LOG.error("Unknow action '%s'", action)
            restful.abort(404)
        return '', 200


def main():
    banner()

    # register HTTP resources
    api = restful.Api(APP)
    api.add_resource(Resource, '/<string:action>')
    api.add_resource(ExitResource, '/exit')

    try:
        # ask user some questions and connect to server
        camera = CameraClient()
        camera.connect()

        # create video window and start streaming
        xid, queue = VideoWindow.factory(camera.name)
        APP.streamer = Streamer(camera.source, xid)
        APP.streamer.start()

    except Exception as e:
        LOG.error(e)
        sys.exit(1)
    
    # start server
    LOG.info("Listening HTTP on port %s", camera.http_port)
    APP.run(port=camera.http_port, debug=False)


if __name__ == '__main__':
    main()
