

import itertools
import zmq

from utils import ServerInfo


class Broker:
    cameras = {}
    screens = {}
    routes = []

    def __init__(self):
        self.info = ServerInfo('*')
        self.context = zmq.Context.instance()
    
        self.hello = self.context.socket(zmq.REP) 
        self.hello.bind(self.info.hello_endpoint)

        self.bye = self.context.socket(zmq.REP)
        self.bye.bind(self.info.bye_endpoint)

        self.list_cameras = self.context.socket(zmq.REP)
        self.list_cameras.bind(self.info.list_cameras_endpoint)

        self.list_screens = self.context.socket(zmq.REP)
        self.list_screens.bind(self.info.list_screens_endpoint)

    def start(self):
        poller = zmq.Poller()
        poller.register(self.hello, zmq.POLLIN)
        poller.register(self.bye, zmq.POLLIN)
        poller.register(self.list_cameras, zmq.POLLIN)
        poller.register(self.list_screens, zmq.POLLIN)

        while True:
            socks = dict(poller.poll())

            if self.hello in socks and socks[self.hello] == zmq.POLLIN:
                self.handle_hello()
            
            if self.bye in socks and socks[self.bye] == zmq.POLLIN:
                self.handle_bye()

            if self.list_cameras in socks:
                self.handle_list_cameras()

            if self.list_screens in socks:
                self.handle_list_screens()

    def handle_bye(self):
        kind, name = self.bye.recv_pyobj()

        if kind == 'camera':
            # delete unused routes
            self.routes = [r for r in self.routes if r[0] != name]
            del self.cameras[name]

        elif kind == 'screen':
            # delete unused routes
            for camera, screen in self.routes:
                if screen == name:
                    continue

                screen_addr, screen_port = self.screens[screen]
                
                sock = self.context.socket(zmq.REQ)
                sock.connect(self.cameras[camera])
                sock.send_pyobj(['unroute', screen, screen_addr, screen_port])
                sock.recv()
            self.routes = [r for r in self.routes if r[1] != name]
            del self.screens[name]

        self.bye.send(b"")

    def handle_hello(self):
        msg = self.hello.recv_pyobj()
        kind, name = msg[:2]
        
        if name in itertools.chain(self.cameras, self.screens):
            self.hello.send_pyobj("Name '%s' already taken" % name)
            return

        if kind == 'camera':
            route_endpoint = msg[2]
            self.cameras[name] = route_endpoint
        else:
            addr, port = msg[2:]
            self.screens[name] = (addr, port)
        self.hello.send_pyobj("ok")

    def handle_list_cameras(self):
        name = self.list_cameras.recv_pyobj()
        if not name:
            result = True, self.cameras
        elif name in self.cameras:
            result = True, self.cameras[name]
        else:
            result = False, "Camera not found"
        self.list_cameras.send_pyobj(result)

    def handle_list_screens(self):
        name = self.list_screens.recv_pyobj()
        if not name:
            result = True, self.screens
        elif name in self.screens:
            result = True, self.screens[name]
        else:
            result = False, "Screen not found"
        self.list_screens.send_pyobj(result)


if __name__ == '__main__':
    broker = Broker()
    broker.start()
