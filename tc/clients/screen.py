import flask
import multiprocessing
import sys

from gi.repository import Gst
from flask.ext import restful
from flask.ext.restful import reqparse


from tc.utils import get_logger, ask, banner, ipv4, TCException
from tc.clients import (Connection, WebInterface, VideoWindow, BaseStreaming,
                       Actions)

LOG = get_logger(__name__)


class Receiver(BaseStreaming):

    def __init__(self, port, exit, actions):
        pipeline = Gst.parse_launch("""
            udpsrc port=%d caps=application/x-rtp ! rtpjitterbuffer
                ! rtph264depay ! decodebin ! xvimagesink
        """ % port)
        super().__init__(pipeline, exit, actions, name='Receiver')


def main():
    banner()

    try:
        srv_addr = ask('Server address > ', '127.0.0.1', ipv4)
        srv_port = ask('Server port    > ', 5000, int)
        scr_name = ask('Screen name    > ')
        print()
    except Exception as ex:
        LOG.fatal(str(ex))
        sys.exit(1)

    exit = multiprocessing.Event()
    actions = multiprocessing.Queue()

    url_format = 'http://{addr}:{port}/screens/{name}'
    connection = Connection(scr_name, srv_addr, srv_port, url_format, exit)

    receiver_proc = Receiver(connection.rtp_port, exit, actions)
    window_proc = VideoWindow(scr_name, exit, actions)
    http_proc = WebInterface(connection.http_port, [], exit, actions)

    connection.connect()
    procs = [receiver_proc, window_proc, http_proc]

    for proc in procs:
        proc.start()

    for proc in procs:
        proc.join()

if __name__ == '__main__':
    main()
