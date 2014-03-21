
import colorlog
import logging
import multiprocessing
import random
import zmq
from os import path


import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst, GdkX11, GstVideo

GObject.threads_init()
Gst.init(None)

def banner():
    print(open(path.join(path.dirname(__file__), 'banner.txt')).read())
     

def get_logger(name):
    log = logging.getLogger(name)
    log.setLevel(logging.DEBUG)
    
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(colorlog.ColoredFormatter(
        "%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(message)s"
    ))

    log.addHandler(stream_handler)
    return log


class Pipeline:

    def __init__(self, pipe, xid):
        self.pipe = pipe
        self.xid = xid
        self.bus = self.pipe.get_bus()
        self.bus.add_signal_watch()
        self.bus.enable_sync_message_emission()
        self.bus.connect('sync-message::element', self._on_sync_message)

    def _on_sync_message(self, bus, msg):
        if msg.get_structure().get_name() == 'prepare-window-handle':
            msg.src.set_window_handle(self.xid)

    def play(self):
        self.pipe.set_state(Gst.State.PLAYING)

    def stop(self):
        self.pipe.set_state(Gst.State.NULL)


class Window(multiprocessing.Process):

    def __init__(self, title, ipc_path, exit_event):
        super().__init__()
        self.exit_event = exit_event
        self.ipc_path = ipc_path
        self.title = title
    
    def draw(self):
        # http://bugs.python.org/issue5527
        import tkinter as tk
        self.root = tk.Tk()
        self.root.wm_title(self.title)
        self.is_fullscreen = False
        
        self.frame = tk.Frame(self.root, bg='#000000')
        self.frame.pack(expand=tk.YES, fill=tk.BOTH)
        self.frame.bind('<Double-Button-1>', self.toggle_fullscreen)

        self.root.protocol('WM_DELETE_WINDOW', self.exit)
        self.root.after(100, self.check_exit)
    
    def check_exit(self):
        if self.exit_event.is_set():
            self.exit()
        else:
            self.root.after(100, self.check_exit)

    def exit(self):
        self.exit_event.set()
        import time; time.sleep(0.3)
        self.root.destroy()
    
    def send_xid(self):
        self.xid = self.frame.winfo_id()
        sock = zmq.Context().socket(zmq.REQ)
        # sock.connect('ipc:///tmp/tc.camera_xid')
        sock.connect(self.ipc_path)
        sock.send_pyobj(self.xid)
        sock.recv()

    def toggle_fullscreen(self, evt):
        self.root.attributes('-fullscreen', self.is_fullscreen)
        self.is_fullscreen = not self.is_fullscreen
    
    def run(self):
        self.draw()
        self.send_xid()
        self.root.mainloop()


class ServerInfo:
    """Store immutable server information"""
    
    hello_port = 4140
    bye_port = 4141
    route_port = 4142
    list_cameras_port = 4143
    list_screens_port = 4144
    
    def __init__(self, address):
        self.addr = address

    @property
    def hello_endpoint(self):
        return 'tcp://%s:%d' % (self.addr, self.hello_port)
    
    @property
    def bye_endpoint(self):
        return 'tcp://%s:%d' % (self.addr, self.bye_port)

    @property
    def list_cameras_endpoint(self):
        return 'tcp://%s:%d' % (self.addr, self.list_cameras_port)

    @property
    def list_screens_endpoint(self):
        return 'tcp://%s:%d' % (self.addr, self.list_screens_port)

    @property
    def route_endpoint(self):
        return 'tcp://%s:%d' % (self.addr, self.route_port)


