

import glob
import requests
import socket
import textwrap
import threading
import tkinter as tk

from gi.repository import Gst, GObject, GstRtspServer
from idlelib.WidgetRedirector import WidgetRedirector
from tkinter import messagebox

from .common import create_new_server_socket, get_logger, PongServer, test_source

class ReadOnlyText(tk.Text):
    def __init__(self, *args, **kwargs):
        value = kwargs.pop('value')
        tk.Text.__init__(self, *args, **kwargs)
        self.insert('1.0', value)
        self.__redirector = WidgetRedirector(self)
        self.__insert =  self.__redirector.register("insert",
                                                    lambda *args, **kw: "break")
        self.__delete =  self.__redirector.register("delete",
                                                    lambda *args, **kw: "break")


class RTSPServer(threading.Thread):

    def __init__(self, exit_evt):
        super().__init__()
        self.exit_evt = exit_evt
        self.sources = None
        self.find_sources()

        self.server = GstRtspServer.RTSPServer()
        sock, self.port = create_new_server_socket()
        sock.close()
        self.server.set_service(str(self.port))
    
    @property
    def mount_points(self):
        return list(self.sources.keys())

    def find_sources(self):
        self.sources = {}
        if test_source('dv1394src'):
            self.sources['dv1394'] = "dv1394src ! queue ! rtpdvpay"

        for dev in glob.glob('/dev/video*'):
            elem = 'v4l2src device={}'.format(dev)
            if test_source(elem):
                self.sources[dev[5:]] = (
                    "{} !  queue ! videoconvert ! video/x-raw,format=I420 ! queue"
                    " ! x264enc preset=ultrafast tune=zerolatency ! queue ! rtph264pay".format(elem)
                )
        # if len(self.sources) == 0:
        if True:
            self.sources['smpte'] = (
                "videotestsrc is-live=true ! queue ! x264enc preset=ultrafast tune=zerolatency"
                " ! queue ! rtph264pay"
            )
    
    def check_exit(self):
        if self.exit_evt.is_set():
            self.loop.quit()
        return True

    def run(self):
        mounts = self.server.get_mount_points()
        for mount, pipeline in self.sources.items():
            mount = "/{}".format(mount)
            pipeline = "( {} name=pay0 pt=96 )".format(pipeline)
            factory = GstRtspServer.RTSPMediaFactory()
            factory.set_launch(pipeline)
            factory.set_shared(True)
            mounts.add_factory(mount, factory)
        
        self.server.attach()
        self.loop = GObject.MainLoop()
        GObject.idle_add(self.check_exit)
        self.loop.run()


class Window(threading.Thread):

    def __init__(self, exit_evt, params):
        super().__init__()
        self.exit_evt = exit_evt
        self.params = params

    def draw(self):
        self.root = tk.Tk()
        self.root.wm_title('Telecorpo Producer')
        self.root.protocol('WM_DELETE_WINDOW', self.quit)
        
        tk.Label(self.root, text="Server").grid(row=0, column=0)
        self.entry = tk.Entry(self.root)
        self.entry.grid(row=0, column=1)

        self.button = tk.Button(self.root, text="Connect", command=self.connect)
        self.button.grid(row=0, column=2)
        
        text = "Listening heartbeats at 0.0.0.0:{}\n".format(self.params['ping_port'])
        text += "Streaming RTSP at\n"
        for mount_point in self.params['rtsp_mounts'].split():
            text += "  rtsp://0.0.0.0:{}/{}\n".format(self.params['rtsp_port'], mount_point)
        self.text = ReadOnlyText(self.root, value=text)
        self.text.grid(row=1, columnspan=3)
    
    def quit(self):
        self.exit_evt.set()
        self.root.destroy()

    def connect(self):
        server = self.entry.get()
        addr, _, port = server.partition(":")
        try:
            socket.inet_aton(addr)
            port = int(port) if port else 13370
        except:
            messagebox.showerror('Error', 'Invalid connection string')
            return

        url = 'http://{}:{}/'.format(addr, port)
        try:
            resp = requests.put(url, self.params).json()
        except:
            messagebox.showerror('Error', 'Cannont connect to server')
            return
        if 'message' in resp:
            messagebox.showerror('Error', resp['message'])
            return
        
        self.entry.configure(state='disabled')
        # self.button.configure(state='disabled')

    def run(self):
        self.draw()
        self.root.mainloop()


def main():
    Gst.init()
    GObject.threads_init()

    exit_evt = threading.Event()

    pong_server = PongServer(exit_evt)
    pong_server.start()

    rtsp_server = RTSPServer(exit_evt)
    rtsp_server.start()

    window = Window(exit_evt, {
        'rtsp_mounts': ' '.join(rtsp_server.mount_points),
        'rtsp_port': rtsp_server.port,
        'ping_port': pong_server.port
    })
    window.start()

    window.join()
    rtsp_server.join()
    pong_server.join()

if __name__ == '__main__':
    main()
