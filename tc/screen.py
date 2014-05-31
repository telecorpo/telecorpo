
import socket
from .messaging import Node



class Screen(Node):
    def __init__(self, forwarder, name):
        super().__init__(forwarder, 'screen', name)

    def recv_add_route(self, origin, msg):
        if msg['screen'] == self.name:

def main(name, forwarder):
    scr = Screen(forwarder, name)
    try:
        scr.main_loop()
    except KeyboardInterrupt:
        pass

