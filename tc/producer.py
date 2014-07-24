
import glob
import ipaddress
import socket
import textwrap
import threading
import tkinter as tk

from tkinter import ttk, messagebox
from gi.repository import Gst, GstRtspServer, GObject


def test_source(elem):
    pipe = Gst.parse_launch('{} ! fakesink'.format(elem))
    pipe.set_state(Gst.State.PLAYING)
    ok = True
    if Gst.StateChangeReturn.FAILURE == pipe.get_state(0)[0]:
        ok = False
    pipe.set_state(Gst.State.NULL)
    return ok


def probe_sources():
    sources = {'smpte': "videotestsrc do-timestamp=true is-live=true"}

    if test_source('dv1394src'):
        sources['dv1394'] = "dv1394src do-timestamp=true ! dvdemux ! dvdec"

    for dev in glob.glob('/dev/video*'):
        elem = 'v4l2src do-timestamp=true device={}'.format(dev)
        name = dev[5:]
        if test_source(elem):
            sources[name] = elem
    return sources


def run_rtsp_server(sources):

    import sys
    if sys.argv[1] == '--hack':
        sources['router'] = ('udpsrc port=13375 ! queue !  application/x-rtp'
                             ' ! rtpjitterbuffer latency=100 ! rtph264depay '
                             ' ! avdec_h264 ')

    server = GstRtspServer.RTSPServer()
    server.set_service("13371")
    
    mounts = server.get_mount_points()
    for mount_point, pipeline in sources.items():
        launch = ("( {} ! queue ! videoconvert ! videoscale ! videorate"
                  " ! video/x-raw,format=I420 ! queue"
                  " ! x264enc speed-preset=ultrafast tune=zerolatency"
                  " ! queue ! rtph264pay pt=96 name=pay0 )"
                  "".format(pipeline))
        factory = GstRtspServer.RTSPMediaFactory()
        factory.set_launch(launch)
        factory.set_shared(True)
        factory.set_suspend_mode(GstRtspServer.RTSPSuspendMode.NONE)
        mounts.add_factory("/{}".format(mount_point), factory)

    server.attach()
    GObject.MainLoop().run()


def registrate_producer(server_address, source_names):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((server_address, 13370))
        sock.send(" ".join(source_names).encode())
        resp = sock.recv(1024).decode()
    if resp != "OK":
        raise Exception(resp)


class MainWindow(tk.Frame):
    
    def __init__(self, master):
        super().__init__(master)
        self.available_sources = probe_sources()

        self.master.title('Telecorpo Producer')
        self.draw_source_list()
        self.draw_connection_form()
    
    def draw_source_list(self):
        self.tree = ttk.Treeview(self.master)
        for source_name in self.available_sources:
            self.tree.insert('', 'end', text=source_name)
        self.tree.grid(row=0, sticky='nsew')
        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)

    def draw_connection_form(self): 
        self.form = ttk.Frame(self.master)
        self.form.grid(row=1, sticky='nsew')
        
        def entry_placeholder(dummy):
            self.entry.delete(0, 'end')
            self.entry.unbind('<FocusIn>')

        self.entry = ttk.Entry(self.form)
        self.entry.insert(0, "server address")
        self.entry.bind('<Return>', self.on_click)
        self.entry.bind('<FocusIn>', entry_placeholder)
        self.entry.grid(row=0, column=0, sticky='nsew')
        self.form.columnconfigure(0, weight=1)

        self.button = ttk.Button(self.form, text="Registrate",
                                 command=self.on_click)
        self.button.grid(row=0, column=1)

    def get_selected_sources(self):
        sources = {}
        for item in self.tree.selection():
            name = self.tree.item(item, 'text')
            sources[name] = self.available_sources[name]
        return sources

    def on_click(self, dummy=None):
        # check source selection
        selected_sources = self.get_selected_sources()
        if len(selected_sources) == 0:
            messagebox.showwarning("User error",
                                   "Select at least one video source")
            return
        
        # disable source selection
        self.tree.configure(selectmode='none')

        # run RTSP server
        rtsp_thread = threading.Thread(target=run_rtsp_server,
                                       args=(selected_sources,),
                                       daemon=True)
        rtsp_thread.start()

        
        # attemp to registrate this producer 
        try:
            server_address = str(ipaddress.ip_address(self.entry.get().strip()))
            registrate_producer(server_address, selected_sources)
        except Exception as err:
            messagebox.showerror("Error",
                                 "Failed to connect the server.\n{}".format(err))
            return

        # disable registration
        self.entry.configure(state='disabled')
        self.button.configure(state='disabled')


def main():
    Gst.init(None)
    root = tk.Tk()
    win = MainWindow(root)
    root.mainloop()


if __name__ == '__main__':
    main()

