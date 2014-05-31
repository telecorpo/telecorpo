

import socket
import sys

from .messaging import Node


class Camera(Node):

    def __init__(self, forwarder, name):
        super().__init__(forwarder, 'camera', name)

    def recv_add_route(self, origin, msg):
        if msg['camera'] != self.name:
            return
        if msg['screen'] in self.routes:
            return
        LOG.info("start streaming to %s <%s>")

def main(name, forwarder):
    cam = Camera(forwarder, name)
    try:
        cam.main_loop()
    except KeyboardInterrupt:
        pass
