import atexit
import colorlog
import flask
import json
import logging
import re
import socket
import types

from multiprocessing    import Process, Queue
from requests import post, delete
from requests.exceptions import Timeout
from flask.ext.restful import Api, Resource
from os import path

from gi.repository      import GObject, Gst, Gtk, Gdk, GdkX11, GstVideo

class VideoWindow(Gtk.Window):

    def __init__(self, title, queue):
        Gtk.Window.__init__(self, title=title)
        self.is_fullscreen = False
        
        self.connect('destroy', self.quit)
        
        # create drawing area
        self.video = Gtk.DrawingArea()
        self.video.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.video.connect('button-press-event', self.on_video_clicked)
        self.add(self.video)
        
        # put the drawing area Xid on queue
        self.queue = queue
        self.show_all()
        self.queue.put(self.video.get_property('window').get_xid())
        
        Gtk.main()

    def on_video_clicked(self, widget, event):
        if event.type == Gdk.EventType._2BUTTON_PRESS and event.button == 1:
            if self.is_fullscreen:
                self.unfullscreen()
                self.is_fullscreen = False
            else:
                self.fullscreen()
                self.is_fullscreen = True
    
    @classmethod
    def factory(self, title):
        queue = Queue(1)
        Process(target=VideoWindow, args=(title, queue)).start()
        return queue.get(), queue


    def quit(self, window):
        Gtk.main_quit()
        self.queue.put('quit')


class TelecorpoException(Exception):
    pass


class TelecorpoEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, types.SimpleNamespace):
            return dict(obj.__dict__)
        return json.JSONEncoder.default(self, obj)


ipv4_re = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
def ipv4(value):
    if not ipv4_re.search(value):
        raise ValueError("Invalid IP address: {}".format(value))
    return value


def get_ip_address(addr, port=5000):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((addr, port))
        return s.getsockname()[0]
    except socket.error:
        raise TelecorpoException('Failed to get ip address or server is down.')


def find_free_port():
    # FIXME no guarantees that it will be free when you use it
    # FIXME (may occur race conditions)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port


def ask(prompt, default=None, validator=lambda x: x):
    value = input(prompt).strip()
    if not (value or default):
        raise ValueError('Empty value')
    return validator(value) if value != '' else validator(default)


def get_logger(name):
    format = ''.join(["%(log_color)s%(levelname)-8s%(reset)s ",
                     "%(black)s%(bold)s%(name)s%(reset)s: ",
                      "%(message)s"])
    handler = logging.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(format))

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return logger

def banner():
    banner = path.join(path.dirname(__file__), 'banner.txt')
    print(open(banner).read())

def cleanup(url):
    logger.warn("Disconnecting from server")
    resp = delete(url + '?close_client=false')
    if not resp.ok:
        logger.error(resp.reason)
        logger.error("Failed to delete this camera, server may be in"
                     " inconsistent state.")
        logger.error("You MUST notify the developers if the server wasn't"
                     " shutdown.")


class ExitResource(Resource):
    def delete(self):
        exit_flask()
        logger.warn("Exiting")

def exit_flask():
    func = flask.request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

logger = get_logger(__name__)
