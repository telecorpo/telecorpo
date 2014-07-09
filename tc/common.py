
import colorlog
import logging
import socket
import threading
import time

from gi.repository import Gst


class TelecorpoException(Exception):
    pass


def test_source(elem):
    pipe = Gst.parse_launch('{} ! fakesink'.format(elem))
    pipe.set_state(Gst.State.PLAYING)
    ok = True
    if Gst.StateChangeReturn.FAILURE == pipe.get_state(0)[0]:
        ok = False
    pipe.set_state(Gst.State.NULL)
    return ok


def get_logger(name):
    log = logging.getLogger(name)
    log.setLevel(logging.DEBUG)
    
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(colorlog.ColoredFormatter(
        "%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(message)s"
    ))

    log.addHandler(stream_handler)
    return log



def create_new_server_socket(min_port=13371, max_port=13380):
    for port in range(min_port, max_port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('', port))
            return sock, sock.getsockname()[1]
        except socket.error:
            pass
    raise TelecorpoException(
        "Cannot found free port in range [{} {}]".format(port_min, port_max))


class PongServer(threading.Thread):

    def __init__(self, exit_evt):
        super().__init__()
        self.exit_evt = exit_evt
        self.sock, self.port = create_new_server_socket()
        self.sock.settimeout(0.5)
        self.sock.listen(10)

    def run(self):
        while not self.exit_evt.is_set():
            try:
                conn, addr = self.sock.accept()
            except socket.timeout:
                continue
            conn.send(b'ok')
            conn.close()

