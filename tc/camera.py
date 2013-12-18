"""
    tc.camera
    ~~~~~~~~~

    Main camera module.
"""

import flask
import multiprocessing
import queue
import sys
import tornado.web

from flask.ext import restful
from flask.ext.restful import reqparse

from tc.client import BaseClient, WebApp
from tc.streaming import Streamer
from tc.utils import get_logger, ask, banner, ipv4, ExitResource, VideoWindow

LOG = get_logger(__name__)

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

    endpoint = '/<string:action>'

    parser = reqparse.RequestParser()
    parser.add_argument('addr', type=ipv4, required=True)
    parser.add_argument('rtp_port', type=int,  required=True)

    def get(self, action):
        return action, 200

    def post(self, action):
        args = self.parser.parse_args()
        addr = args['addr']
        port = args['rtp_port']

        if action == 'add':
            LOG.info("Streaming to %s:%d", addr, port)
            flask.g.streamer.add_client(addr, port)

        elif action == 'remove':
            LOG.info("Stopping streaming to %s on port %d", addr, port)
            flask.g.streamer.remove_client(addr, port)

        else:
            LOG.error("Unknow action '%s'", action)
            restful.abort(404)
        return '', 200
    
    def delete(self, action):
        LOG.warn("Exiting")
        IOLoop.instance().stop()
        self.exit_conn.send(True)


class CameraWebApp(WebApp):

    def __init__(self, camera, xid, exit_conn):
        self.camera = camera
        super().__init__(camera.name, exit_conn, camera.http_port, [Resource,])
        self.streamer = Streamer(camera.source, xid)
        with self.app.app_context() as ctx:
            ctx.g.streamer = self.streamer

    def on_exit(self):
        self.streamer.stop()


def main():
    banner()

    http_conn, gui_conn = multiprocessing.Pipe()
    
    try:
        # ask user some questions and connect to server
        camera = CameraClient()
        camera.connect()

        # create video window process
        gui_proc, xid = VideoWindow.factory(camera.name, gui_conn)

        # create webapp (and streamer) process
        # http_proc = WebAppFlask(__name__, http_conn, camera.http_port,
        #                         [Resource,], camera.source, xid)
        http_proc = CameraWebApp(camera, xid, http_conn)
        http_proc.start()

    except Exception as e:
        LOG.error(e)
        raise e
        sys.exit(1)
    
    http_proc.join()
    gui_proc.join()


if __name__ == '__main__':
    main()
