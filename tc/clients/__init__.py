"""
    tc.client
    ~~~~~~~~~

    This module implements common clients classes.
"""

import atexit
import collections
import multiprocessing
import queue
import socket
import time
import tkinter as tk # require tcl8.5.15 see http://bugs.python.org/issue5527

import tornado.web
import tornado.ioloop

from gi.repository import GObject, Gst, Gdk, GLib, GstVideo # GstVideo required for set_window_handle
from tornado import wsgi, httpserver, ioloop

from tc.utils import get_logger, TCException, is_verbose
from tc.utils.http import post, delete


GObject.threads_init()
Gdk.threads_init()
Gst.init(None)


LOG = get_logger(__name__)


class Actions:
    ADD_HD_CAMERA_CLIENT = 1 # (ipaddr, rtp_port)
    ADD_LD_CAMERA_CLIENT = 3 # ditto
    RM_HD_CAMERA_CLIENT  = 2 # ditto
    RM_LD_CAMERA_CLIENT  = 4 # ditto
    XID                  = 5 # xid_value


class BaseProcess(multiprocessing.Process):
    """
    Base process class. Childs must set the `exit` event to terminate this and
    all others :class:`BaseProcess`es instances that share the same exit event.
    Childs must check periodically for the `exit` event and exit accordingly.

    :param exit: event that mark this process to termination.
    :param actions: global actions queue 
    """
    def __init__(self, exit, actions, name=None):
        super().__init__(name=name)
        self.exit = exit
        self.actions = actions
        self.actions_callbacks = collections.defaultdict(list)

    def add_callback(self, action, cb):
        """Register a callback to some action."""
        self.actions_callbacks[action].append(cb)

    def run_callbacks(self, action, args):
        """Run all callbacks for a given action."""
        for cb in self.actions_callbacks[action]:
            if args == None:
                cb()
            if isinstance(args, collections.Iterable):
                cb(*args)
            else:
                cb(args)

    def run(self):
        while not self.exit.is_set():
            time.sleep(0.1)
            try:
                action, args = self.actions.get(False)
                self.run_callbacks(action, args)
            except queue.Empty:
                continue
        LOG.debug("Stoping")


class Streaming(BaseProcess):

    def __init__(self, pipeline, title, exit, actions, name=None):
        super().__init__(exit, actions, name)
        self.title = title
        self.is_fullscreen = False
        self.pipeline = pipeline
        self.xid = None
    
    def configure_pipeline(self):
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message::eos', self.on_eos)
        self.bus.connect('message::error', self.on_error)

        self.bus.enable_sync_message_emission()
        self.bus.connect('sync-message::element', self.on_sync_message)

    def create_widgets(self):
        self.root = tk.Tk()
        self.root.title(self.title)
        self.root.protocol("WM_DELETE_WINDOW", self.exit.set)
        # self.root.after(100, self.check_events)
        
        # display frame
        self.video = tk.Frame(self.root, bg='#000000')
        self.video.pack(expand=tk.YES, fill=tk.BOTH)

        # toggle fullscreen on double click
        self.video.bind('<Double-Button-1>', self.toggle_fullscreen)

        # get XID and check for exit event
        self.xid = self.video.winfo_id()

    def on_eos(self, bus, msg):
        """End of stream handler."""
        LOG.error("EOS reached, what should I do?")

    def on_error(self, bus, msg):
        """Error handler."""
        LOG.error("An error occurred. %s", msg.parse_error())

    def on_sync_message(self, bus, msg):
        """Sync pipeline xvideosink element with a X window self.xid."""
        if msg.get_structure().get_name() != 'prepare-window-handle':
            return
        # msg.src.set_property('force-aspect-ratio', True)
        msg.src.set_window_handle(self.xid)

    def toggle_fullscreen(self, event):
        self.root.attributes('-fullscreen', self.is_fullscreen)
        self.is_fullscreen = not self.is_fullscreen

    def check_events(self):
        if self.exit.is_set():
            self.root.destroy()

    def run(self):
        LOG.info("Start streaming.")
        self.create_widgets()
        self.configure_pipeline()
        self.pipeline.set_state(Gst.State.PLAYING)
        while not self.exit.is_set():
            self.root.update()
            time.sleep(0.2)
            try:
                action, args = self.actions.get(False)
                self.run_callbacks(action, args)
            except queue.Empty:
                continue
        LOG.info("Start stop.")
        self.pipeline.set_state(Gst.State.NULL)
        self.exit.set()


class WebApplication(BaseProcess):

    def __init__(self, port, handlers, init_data, exit, actions):
        super().__init__(exit, actions, 'WebApplication')
        self.port = port
        class ExitHandler(tornado.web.RequestHandler):
            endpoint = r'/exit'
            def put(self):
                exit.set()
            def delete(self):
                exit.set()
        handlers.append(ExitHandler)
        self.app = tornado.web.Application([
            (h.endpoint, h, init_data) for h in handlers
        ])
        self.app.debug = is_verbose()

    def _check_exit(self):
        if self.exit.is_set():
            LOG.debug("Stoping")
            tornado.ioloop.IOLoop.instance().stop()

    def run(self):
        LOG.info("Listening HTTP on port %d", self.port)
        self.app.listen(self.port)
        tornado.ioloop.PeriodicCallback(self._check_exit, 100).start()
        tornado.ioloop.IOLoop.instance().start()


class Connection:
    """Collect networking data and connect to server."""

    def __init__(self, name, srv_addr, srv_port, url_format, exit):
        """
        Args:
            srv_addr: server IP address.
            srv_port: server HTTP port.
        """

        self.name = name
        self.http_port = self.get_free_port()
        self.rtp_port = self.get_free_port()
        self.addr = self.get_addr(srv_addr, srv_port)

        self._srv_addr = srv_addr
        self._srv_port = srv_port
        self._resource_url = url_format.format(addr=srv_addr, port=srv_port,
                                               name=self.name)
        self._exit = exit

    def connect(self):
        LOG.debug("Trying to connect to %s:%s", self._srv_addr, self._srv_port)

        # discover connection parameters
        # (ignore private members and functions)
        params = {}
        for k, v in self.__dict__.items():
            if k.startswith('_') or hasattr(v, '__call__'):
                continue
            params[k] = v

        # connection code
        try:
            LOG.debug("Posting %s to %s", params, self._resource_url)
            post(self._resource_url, params)
        except TCException as ex:
            LOG.fatal(str(ex))
            LOG.fatal("Could not connect to server")
            raise SystemExit

        # always call disconnect on exit
        atexit.register(self.disconnect)

    def disconnect(self):
        try:
            delete(self._resource_url)
        except TCException as ex:
            msg = ("Failed to disconnect, server may be in inconsistent state."
                   " You MUST notify the developer IF the server wasn't shutdown.")
            LOG.fatal(msg)
        finally:
            LOG.info("Até mais")
            self._exit.is_set()

    @classmethod
    def get_free_port(cls):
        # FIXME no guarantees that it will be free when you use it
        # FIXME (may occur race conditions)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(('', 0))
        port = s.getsockname()[1]
        s.close()
        return port

    @classmethod
    def get_addr(cls, srv_addr, srv_port):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect((srv_addr, srv_port))
            return s.getsockname()[0]
        except socket.error:
            msg = "Failed to get ip address or server is down."
            raise TCException(msg)


