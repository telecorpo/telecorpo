"""
    tc.client
    ~~~~~~~~~

    This module implements common clients classes.
"""

import atexit
import collections
import flask
import multiprocessing
import queue
import socket
import time
import tkinter as tk # require tcl8.5.15 see http://bugs.python.org/issue5527

from gi.repository import GObject, Gst, Gdk, GLib, GstVideo # GstVideo required for set_window_handle
from tornado import wsgi, httpserver, ioloop

from tc.utils import get_logger, post, delete, TelecorpoException


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


class BaseStreaming(BaseProcess):
    """Manage Gstreamer pipeline."""

    def __init__(self, pipeline, exit, actions, name=None):
        super().__init__(exit, actions, name=name)
        self.pipeline = pipeline
        self.xid = None

        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message::eos', self.on_eos)
        self.bus.connect('message::error', self.on_error)

        self.bus.enable_sync_message_emission()
        self.bus.connect('sync-message::element', self.on_sync_message)

        self.add_callback(Actions.XID, self.on_xid)

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
        LOG.debug("xvideosink points to self.xid=%r", self.xid)

    def on_xid(self, xid):
        self.xid = xid
        LOG.debug("Playing")
        self.pipeline.set_state(Gst.State.PLAYING)

    def run(self):
        while not self.exit.is_set():
            time.sleep(0.1)
            try:
                action, args = self.actions.get(False)
                self.run_callbacks(action, args)
            except queue.Empty:
                continue
        LOG.debug("Stoping")
        self.pipeline.set_state(Gst.State.NULL)


class VideoWindow(BaseProcess):

    def __init__(self, title, exit, actions):
        super().__init__(exit, actions, name='VideoWindow')
        self.title = title
        self.is_fullscreen = False

    def create_widgets(self):
        # create window
        self.root = tk.Tk()
        self.root.title(self.title)

        # frame for video display
        self.frame = tk.Frame(self.root, bg='#000000')
        self.frame.pack(side=tk.BOTTOM, anchor=tk.S, expand=tk.YES, fill=tk.BOTH)

        # enable fullscreen
        self.frame.bind('<Double-Button-1>', self.toggle_fullscreen)

        # get XID and check for exit event
        self.actions.put((Actions.XID, self.frame.winfo_id()))
        self.root.after(100, self.check_exit)

    def toggle_fullscreen(self, event):
        self.root.attributes('-fullscreen', self.is_fullscreen)
        self.is_fullscreen = not self.is_fullscreen

    def check_exit(self):
        if self.exit.is_set():
            self.root.destroy()

    def run(self):
        self.create_widgets()
        self.root.mainloop()
        self.exit.set()


class WebInterface(BaseProcess):
    """Web application process. Build, manage and terminate client HTTP
    interface.
    """

    def __init__(self, port, resources, exit, actions):
        """
        Args:
            resources: List of restful.Resource.
            exit: Exit event.
            actions: Global actions queue.
        """
        super().__init__(exit, actions, name='webinterface')

        self.app = flask.Flask(__name__)
        self.port = port

        # resource for http://ipaddr:port/exit
        class ExitResource(flask.ext.restful.Resource):
            def delete(self):
                LOG.warn("Exiting")
                ioloop.IOLoop.instance().stop()
                self.exit.set()

        # register flask-restful resources
        self.rest_api = flask.ext.restful.Api(self.app)
        self.rest_api.add_resource(ExitResource, '/exit')
        for resource in resources:
            self.rest_api.add_resource(resource, resource.endpoint)

        # monkey patch flask application context
        with self.app.app_context():
            # FIXME dont work!
            flask.g.actions = self.actions

        # continuously check for exit
        self.periodic_check = ioloop.PeriodicCallback(self._check_exit,
                                                           100)

    def _check_exit(self):
        if self.exit.is_set():
            LOG.debug("Stoping")
            ioloop.IOLoop.instance().stop()

    def run(self):
        http_srv = httpserver.HTTPServer(wsgi.WSGIContainer(self.app))
        http_srv.listen(self.port)

        self.periodic_check.start()
        self.app.debug = False
        LOG.info("Listening HTTP on port %s", self.port)
        ioloop.IOLoop.instance().start()


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
        except TelecorpoException as ex:
            LOG.fatal(str(ex))
            LOG.fatal("Could not connect to server")
            raise SystemExit

        # always call disconnect on exit
        atexit.register(self.disconnect)

    def disconnect(self):
        try:
            delete(self._resource_url)
        except TelecorpoException as ex:
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
            raise TelecorpoException(msg)


