import multiprocessing
import sys

from gi.repository import Gst

from tc.utils import get_logger, ask, banner, ipv4, TCException
from tc.clients import Connection, WebApplication, Streaming

LOG = get_logger(__name__)


class Receiver(Streaming):

    def __init__(self, port, name, exit, actions):
        pipeline = Gst.parse_launch("""
            udpsrc port=%d caps=application/x-rtp ! rtpjitterbuffer
                ! rtph264depay ! decodebin ! xvimagesink
        """ % port)
        title = '%s - Screen' % name
        super().__init__(pipeline, title, exit, actions, name='Receiver')


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

    receiver_proc = Receiver(connection.rtp_port, scr_name, exit, actions)
    http_proc = WebApplication(connection.http_port, [], {}, exit, actions)

    connection.connect()
    procs = [receiver_proc, http_proc]

    for proc in procs:
        proc.start()

    for proc in procs:
        proc.join()

if __name__ == '__main__':
    main()
