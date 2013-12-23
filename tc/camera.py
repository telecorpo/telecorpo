"""
    tc.camera
    ~~~~~~~~~

    Camera module.
"""

import multiprocessing

from gi.repository import Gst
from flask.ext import restful
from flask.ext.restful import reqparse

from tc.client import (Connection, WebInterface, VideoWindow, BaseStreaming,
                       Actions, TelecorpoException)
from tc.utils import get_logger, ask, banner, ipv4


LOG = get_logger(__name__)
ACTIONS = multiprocessing.Queue()


class Resource(restful.Resource):
    """
    """

    endpoint = '/<kind>/<action>'

    parser = reqparse.RequestParser()
    parser.add_argument('addr', type=ipv4, required=True)
    parser.add_argument('rtp_port', type=int,  required=True)

    def post(self, kind, action):
        args = self.parser.parse_args()
        addr = args['addr']
        port = args['rtp_port']
        
        signal = msg = None
        if action == 'add':
            msg = "Streaming {} to %s:%d".format(kind.upper())
            if kind == 'hd':
                signal = Actions.ADD_HD_CAMERA_CLIENT
            elif kind == 'ld':
                signal = Actions.ADD_LD_CAMERA_CLIENT

        elif action == 'remove':
            msg = "Stop {} streaming to %s:%d".format(kind.upper())
            if kind == 'hd':
                signal = Actions.RM_HD_CAMERA_CLIENT
            elif kind == 'ld':
                signal = Actions.RM_LD_CAMERA_CLIENT

        if not (signal and msg):
            LOG.error("Unknow action '%s' or kind '%s'", action, kind)
            restful.abort(404)

        LOG.info(msg)
        ACTIONS.put((signal, (addr, port)))
        return '', 200


class Streamer(BaseStreaming):
    """
    A streamer is an object that capture from a video source, transcode to
    H264 in low and high definition, and stream to multiple destinations using
    RTP.

    :param source: the gstreamer source element.
    :param exit: exit event.
    :param actions: global actions queue.
    """

    def __init__(self, source, exit, actions):
        pipeline = Gst.parse_launch("""
            %s ! tee name=t
                t. ! queue ! x264enc tune=zerolatency ! rtph264pay
                    ! multiudpsink name=hd
                t. ! queue ! x264enc tune=zerolatency ! rtph264pay
                    ! multiudpsink name=ld
                t. ! queue ! xvimagesink
        """ % source)
        super().__init__(pipeline, exit, actions, name='Streamer')

        self.hdsink = self.pipeline.get_by_name('hd')
        self.hdsink.set_property('sync', True)
        self.hdsink.set_property('send-duplicates', False)

        self.ldsink = self.pipeline.get_by_name('ld')
        self.ldsink.set_property('sync', True)
        self.ldsink.set_property('send-duplicates', False)

        self.add_callback(Actions.ADD_HD_CAMERA_CLIENT, self.add_hd_client)
        self.add_callback(Actions.ADD_LD_CAMERA_CLIENT, self.add_ld_client)
        self.add_callback(Actions.RM_HD_CAMERA_CLIENT, self.remove_hd_client)
        self.add_callback(Actions.RM_LD_CAMERA_CLIENT, self.remove_ld_client)

    def add_hd_client(self, addr, port):
        """Start HD streaming to new client."""
        LOG.info("Start HD streaming to %s:%d", addr, port)
        self.hdsink.emit('add', addr, port)

    def add_ld_client(self, addr, port):
        """Start LD streaming to new client."""
        LOG.info("Start LD streaming to %s:%d", addr, port)
        self.ldsink.emit('add', addr, port)

    def remove_hd_client(self, addr, port):
        """Stop HD streaming to client."""
        LOG.info("Stop streaming to %s:%d", addr, port)
        self.hdsink.emit('remove', addr, port)

    def remove_ld_client(self, addr, port):
        """Stop LD streaming to client."""
        LOG.info("Stop streaming to %s:%d", addr, port)
        self.ldsink.emit('remove', addr, port)


def main():
    banner()

    source = """
        videotestsrc pattern=smpte
        ! video/x-raw,format=I420,framerate=30/1,width=480,heigth=360
    """

    try:
        srv_addr = ask('Server address > ', '127.0.0.1', ipv4)
        srv_port = ask('Server port    > ', 5000, int)
        source   = ask('Source element > ', source)
        cam_name = ask('Camera name    > ')
        print()
    except Exception as ex:
        LOG.fatal(str(ex))
        raise SystemExit

    exit = multiprocessing.Event()

    url_format = 'http://{addr}:{port}/cameras/{name}'
    connection = Connection(cam_name, srv_addr, srv_port, url_format, exit)

    streamer_proc = Streamer(source, exit, ACTIONS)
    window_proc = VideoWindow(cam_name, exit, ACTIONS)
    http_proc = WebInterface(connection.http_port, [Resource,], exit, ACTIONS)

    connection.connect()
    procs = [streamer_proc, window_proc, http_proc]

    for proc in procs:
        proc.start()

    for proc in procs:
        proc.join()

if __name__ == '__main__':
    main()

