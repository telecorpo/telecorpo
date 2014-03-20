#!/usr/bin/env pyton3

import logging
import multiprocessing
import signal
import socket
import sys
import time
import threading
import zmq

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst, GdkX11, GstVideo

GObject.threads_init()
Gst.init(None)

from utils import Window, ServerInfo, get_logger


LOGGER = get_logger("camera")


class Pipeline:

    def __init__(self, xid):
        source = self.detect_source()
        self.pipe = Gst.parse_launch("""
            {source} ! videoconvert ! video/x-raw,format=I420 ! tee name=t 
                t. ! queue ! x264enc tune=zerolatency ! queue ! rtph264pay
                   ! multiudpsink name=sink
                t. ! queue ! autovideosink sync=false
        """.format(source=self.detect_source()))
        self.sink = self.pipe.get_by_name('sink')
        self.clients = []

        self.xid = xid

        self.bus = self.pipe.get_bus()
        self.bus.add_signal_watch()
        self.bus.enable_sync_message_emission()
        self.bus.connect('sync-message::element', self._on_sync_message)

    def _on_sync_message(self, bus, msg):
        if msg.get_structure().get_name() == 'prepare-window-handle':
            msg.src.set_window_handle(self.xid)

    def detect_source(self):
        if self.has_firewire():
            return "dv1394src ! dvdemux ! dvdec ! queue"
        elif self.has_v4l2():
            return "v4l2src"
        else:
            return "videotestsrc"

    def has_firewire(self):
        pipe = Gst.parse_launch('dv1394src ! fakesink')
        pipe.set_state(Gst.State.PLAYING)
        ok = True
        if Gst.StateChangeReturn.FAILURE == pipe.get_state(0)[0]:
            ok = False
        pipe.set_state(Gst.State.NULL)
        return ok

    def has_v4l2(self):
        pipe = Gst.parse_launch('v4l2src ! fakesink')
        pipe.set_state(Gst.State.PLAYING)
        ok = True
        if Gst.StateChangeReturn.FAILURE == pipe.get_state(0)[0]:
            ok = False
        pipe.set_state(Gst.State.NULL)
        return ok

    def play(self):
        self.pipe.set_state(Gst.State.PLAYING)

    def stop(self):
        self.pipe.set_state(Gst.State.NULL)

    def add_client(self, addr, port):
        if (addr, port) not in self.clients:
            self.clients.append((addr, port))
            self.sink.emit('add', addr, port)

    def remove_client(self, addr, port):
        if (addr, port) in self.clients:
            self.clients.remove((addr, port))
            self.sink.emit('remove', addr, port)


class Streamer(threading.Thread):
    
    def __init__(self, camera, server, exit_evt, context=None):
        super().__init__()

        self.context = context or zmq.Context.instance()
        self.camera = camera
        self.server = server
        self.exit_evt = exit_evt

    def wait_for_xid(self):
        sock = self.context.socket(zmq.REP)
        sock.bind(self.camera.xid_endpoint)
        xid = sock.recv_pyobj()
        sock.send(b"")
        return xid
    
    def run(self):
        xid = self.wait_for_xid()
        pipe = Pipeline(xid)

        pipe.play()

        sock = self.context.socket(zmq.REP)
        sock.bind(self.camera.route_endpoint)
        
        LOGGER.debug("Accepting routes")
        while not self.exit_evt.is_set():
            try:
                action, screen, addr, port = sock.recv_pyobj(zmq.NOBLOCK)
            except zmq.Again:
                time.sleep(0.1)
                continue
            if action == 'route':
                print(1)
                LOGGER.info("Streaming to %s <%s:%d>" % (screen, addr, port))
                pipe.add_client(addr, port)
            elif action == 'unroute':
                LOGGER.info("Stop streaming to %s <%s:%s>" % (screen, addr,
                                                              port))
                pipe.remove_client(addr, port)
            sock.send(b"")
        pipe.stop()


class CameraInfo:
    """Store immutable camera information"""

    route_port = 4150
    xid_endpoint = 'ipc:///tmp/tc.camera_xid'
    
    def __init__(self, name, server):
        self.name = name
        self.server = server

    @property
    def route_endpoint(self):
        return 'tcp://%s:%d' % (self.addr, self.route_port)
    
    @property
    def addr(self):
        """Which address of this camera can reach the server?"""
        if hasattr(self, '_addr'):
            return self._addr

        s = socket.socket()
        s.connect((self.server.addr, self.server.hello_port))
        p = s.getsockname()
        s.close()
        self._addr = p[0]
        return self._addr

        self.exit_evt = exit

def main():
    # Parse arguments
    if len(sys.argv) != 3:
        print("usage: tc-camera NAME SERVER", file=sys.stderr)
        sys.exit(1)

    server = ServerInfo(sys.argv[2].strip())
    camera = CameraInfo(sys.argv[1].strip(), server)

    print(camera.addr)
    
    context = zmq.Context.instance()
    
    # Register this client
    LOGGER.info("Send hello I'm %s", camera.name)
    hello = context.socket(zmq.REQ)
    hello.connect(server.hello_endpoint)
    hello.send_pyobj(["camera", camera.name, camera.route_endpoint])

    resp = hello.recv_pyobj()
    if resp != "ok":
        LOGGER.fatal(resp)
        sys.exit(2)
    
    # Program exits when one of these events is set
    thread_exit_event = threading.Event()
    proc_exit_event = multiprocessing.Event()

    # Catch Ctrl-C interrupts
    def exit(signal, frame):
        thread_exit_event.set()
        proc_exit_event.set()
    signal.signal(signal.SIGINT, exit)
    
    # Initialize streaming code
    LOGGER.info("Plubing capture & streaming pipeline")
    streamer = Streamer(camera, server, thread_exit_event)
    streamer.start()
    
    # Initialize GUI
    LOGGER.info("Drawing window")
    window = Window('%s - camera' % camera.name, camera.xid_endpoint,
                    proc_exit_event)
    window.start()

    try:
        while not (thread_exit_event.is_set() or proc_exit_event.is_set()):
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        thread_exit_event.set()
        proc_exit_event.set()
    
    # Unregister this client
    LOGGER.info("Send bye")
    bye = context.socket(zmq.REQ)
    bye.connect(server.bye_endpoint)
    bye.send_pyobj(["camera", camera.name])
    bye.recv()


if __name__ == '__main__':
    main()
