"""
    tc.camera
    ~~~~~~~~~

    Camera module.
"""

import multiprocessing

from gi.repository import Gst
from tornado.web import RequestHandler

from tc.clients import (Connection, VideoWindow, BaseStreaming,
                       Actions, WebApplication)
from tc.utils import get_logger, ask, banner, ipv4, port, TCException


LOG = get_logger(__name__)


class Handler(RequestHandler):
    endpoint = r'/(hd|ld)/(add|remove)'

    def initialize(self, actions):
        self.actions = actions

    def post(self, kind, action):
        try:
            addr = ipv4(self.get_argument('addr'))
            rtp_port = port(self.get_argument('rtp_port'))
        except ValueError as err:
            LOG.exception(err)
            raise SystemExit
        
        signal = msg = None

        if action == 'add':
            msg = "Streaming {} to %s:%d".format(kind.upper())
            if kind == 'hd':
                signal = Actions.ADD_HD_CAMERA_CLIENT
            else:
                signal = Actions.ADD_LD_CAMERA_CLIENT
        else:
            msg = "Stop {} streaming to %s:%d".format(kind.upper())
            if kind == 'hd':
                signal = Actions.RM_HD_CAMERA_CLIENT
            else:
                signal = Actions.RM_LD_CAMERA_CLIENT
        LOG.info(msg)
        self.actions.put((signal, (addr, rtp_port)))
        self.write('')


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
    actions = multiprocessing.Queue()

    url_format = 'http://{addr}:{port}/cameras/{name}'
    connection = Connection(cam_name, srv_addr, srv_port, url_format, exit)

    streamer_proc = Streamer(source, exit, actions)
    window_proc = VideoWindow(cam_name, exit, actions)
    http_proc = WebApplication(connection.http_port, [Handler,],
                               {'actions':actions}, exit, actions)

    connection.connect()
    procs = [streamer_proc, window_proc, http_proc]

    for proc in procs:
        proc.start()

    for proc in procs:
        proc.join()

if __name__ == '__main__':
    main()

