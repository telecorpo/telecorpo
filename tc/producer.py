
import gi
import glob
import ipaddress
import socket
import threading
import tkinter as tk

from tkinter import ttk, messagebox

gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
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
    sources = {'smpte': "videotestsrc is-live=true"}

    if test_source('dv1394src'):
        sources['dv1394'] = "dv1394src ! dvdemux ! dvdec"

    for dev in glob.glob('/dev/video*'):
        elem = 'v4l2src device={}'.format(dev)
        name = dev[5:]
        if test_source(elem):
            sources[name] = elem
    return sources


def run_rtsp_server(sources, x264params):

    server = GstRtspServer.RTSPServer()
    server.set_service("13371")
    
    mounts = server.get_mount_points()
    for mount_point, pipeline in sources.items():
        launch = ("( {} ! videoconvert ! videoscale ! videorate"
                  " ! queue"
                  " ! x264enc {}"
                  " ! queue ! rtph264pay pt=96 name=pay0 )"
                  "".format(pipeline, x264params))
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
        self.cam_tree = ttk.Treeview(self.master)
        for source_name in self.available_sources:
            self.cam_tree.insert('', 'end', text=source_name)
        self.cam_tree.grid(row=0, sticky='nsew')
        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)

    def draw_connection_form(self): 
        self.form = ttk.Frame(self.master)
        self.form.grid(row=1, sticky='nsew')
        
        def entry_placeholder(dummy):
            self.addr_entry.delete(0, 'end')
            self.addr_entry.unbind('<FocusIn>')

        self.addr_entry = ttk.Entry(self.form)
        self.addr_entry.insert(0, "server address")
        self.addr_entry.bind('<Return>', self.on_click)
        self.addr_entry.bind('<FocusIn>', entry_placeholder)
        self.addr_entry.grid(row=1, column=0, sticky='nsew')

        self.h264_entry = ttk.Entry(self.form)
        self.h264_entry.insert(0, "tune=zerolatency "
                                   "intra-refresh=true "
                                   "key-int-max=0")
        self.h264_entry.grid(row=0, column=0, sticky='nsew')

        self.form.columnconfigure(0, weight=1)

        self.button = ttk.Button(self.form, text="Registrate",
                                 command=self.on_click)
        self.button.grid(row=0, column=1, rowspan=2)

    def get_selected_sources(self):
        sources = {}
        for item in self.cam_tree.selection():
            name = self.cam_tree.item(item, 'text')
            sources[name] = self.available_sources[name]
        return sources

    def on_click(self, dummy=None):
        # check source selection
        selected_sources = self.get_selected_sources()
        if len(selected_sources) == 0:
            messagebox.showwarning("User error",
                                   "Select at least one video source")
            return
        
        # disable registration
        self.cam_tree.configure(selectmode='none')
        self.addr_entry.configure(state='disabled')
        self.h264_entry.configure(state='disabled')
        self.button.configure(state='disabled')

        # run RTSP server
        x264params = self.h264_entry.get().strip()
        rtsp_thread = threading.Thread(target=run_rtsp_server,
                                       args=(selected_sources, x264params),
                                       daemon=True)
        rtsp_thread.start()

        
        # attemp to registrate this producer 
        try:
            server_address = str(ipaddress.ip_address(self.addr_entry.get().strip()))
            registrate_producer(server_address, selected_sources)
        except Exception as err:
            messagebox.showerror("Error",
                                 "Failed to connect the server.\n{}".format(err))
            # reenable registration
            self.cam_tree.configure(selectmode='extended')
            self.addr_entry.configure(state='enabled')
            self.h264_entry.configure(state='enabled')
            self.button.configure(state='enabled')


def main():
    Gst.init(None)
    root = tk.Tk()
    win = MainWindow(root)
    root.mainloop()


if __name__ == '__main__':
    main()
