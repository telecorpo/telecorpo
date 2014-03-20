#!/usr/bin/env pyton3

import logging
import multiprocessing
import signal
import socket
import sys
import threading
import zmq

from utils import Window, ServerInfo


LOGGER = logging.getLogger("screen")
LOGGER.setLevel(logging.DEBUG)


class Receiver(threading.Thread):
    
    def __init__(self, screen, server, exit_evt, context=None):
        super().__init__()

        self.context = context or zmq.Context.instance()
        self.screen = screen
        self.server = server
        self.exit_evt = exit_evt
    
    def wait_for_xid(self):
        sock = self.context.socket(zmq.REP)
        sock.bind(self.screen.xid_endpoint)
        xid = sock.recv_pyobj()
        sock.send(b"")
        return xid
    
    def create_pipeline(self, xid, port):
        import mock
        return mock.Mock()

    def run(self):
        xid = self.wait_for_xid()
        pipe = self.create_pipeline(xid, self.screen.port)

        pipe.play()
        
        import time
        while not self.exit_evt.is_set():
            time.sleep(0.1)


class ScreenInfo:
    """Store immutable screen information"""

    xid_endpoint = 'ipc:///tmp/tc.screen_xid'

    def __init__(self, name, server):
        self.name = name
        self.server = server
    
    @property
    def addr(self):
        """Which address of this client can reach the server?"""
        if hasattr(self, '_addr'):
            return self._addr

        s = socket.socket()
        s.connect((self.server.addr, self.server.hello_port))
        p = s.getsockname()
        s.close()
        self._addr = p[0]
        return self._addr

    @property
    def port(self):
        """Port for listening RTMP streaming"""
        if hasattr(self, '_port'):
            return self._port

        s = socket.socket()
        s.connect((self.server.addr, self.server.hello_port))
        p = s.getsockname()
        s.close()
        self._port = p[1]
        return self._port


def main():
    # Parse arguments
    if len(sys.argv) != 3:
        print("usage: tc-screen NAME SERVER", file=sys.stderr)
        sys.exit(1)
    
    server = ServerInfo(sys.argv[2].strip())
    screen = ScreenInfo(sys.argv[1].strip(), server)

    context = zmq.Context.instance()

    # Register this client
    LOGGER.info("Send hello I'm %s", screen.name)
    hello = context.socket(zmq.REQ)
    hello.connect(server.hello_endpoint)
    hello.send_pyobj(["screen", screen.name, screen.addr, screen.port])
    
    resp = hello.recv_pyobj()
    if resp != "ok":
        LOGGER.fatal(resp)
        sys.exit(2)
    
    # Program exits when on of these events is set
    thread_exit_event = threading.Event()
    proc_exit_event = multiprocessing.Event()

    # Catch Ctrl-C signals
    def exit(signal, frame):
        thread_exit_event.set()
        proc_exit_event.set()
    signal.signal(signal.SIGINT, exit)
    
    # Initialize streaming (receiving) code
    LOGGER.info("Waiting for moving bodies")
    receiver = Receiver(screen, server, thread_exit_event)
    receiver.daemon = True
    receiver.start()
    
    # Initialize GUI
    LOGGER.info("Drawing window")
    window = Window('%s - screen' % screen.name, screen.xid_endpoint,
                    proc_exit_event)
    window.daemon = True
    window.start()
    
    # Do nothing until an exit event is set
    try:
        import time
        while not (thread_exit_event.is_set() or proc_exit_event.is_set()):
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        thread_exit_event.set()
        proc_exit_event.set()
    
    # Unregister this client
    bye = context.socket(zmq.REQ)
    bye.connect(server.bye_endpoint)
    bye.send_pyobj(["screen", screen.name])
    bye.recv()


if __name__ == '__main__':
    main()
