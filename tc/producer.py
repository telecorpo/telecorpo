
import glob
import ipaddress
import socket
import textwrap
import threading
import sys
import tkinter as tk

from tkinter import ttk, messagebox
from gi.repository import Gst, GstRtspServer, GObject, Gtk, Gio


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
    if len(sys.argv) == 2 and sys.argv[1] == '--hack':
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


class Source:

    def __init__(self, name, longname, description):
        self.name = name
        self.longname = longname
        self.description = description

    @staticmethod
    def test_source_element(elem):
        """
        Tests if some source element can be set in PLAYING state.
        
        """
        pipe = Gst.Pipeline()
        sink = Gst.ElementFactory.make('fakesink')

        pipe.add(elem)
        pipe.add(sink)

        elem.link(sink)
        
        pipe.set_state(Gst.State.PLAYING)

        success = True
        if Gst.StateChangeReturn.FAILURE == pipe.get_state(0)[0]:
            success = False
        pipe.set_state(Gst.State.NULL)
        
        return success

    @classmethod
    def find_sources(cls):
        """
        Returns all video sources found.

        """
        sources = []
        
        dv1394 = Gst.ElementFactory.make('dv1394src')
        if cls.test_source_element(dv1394):
            longname = dv1394.props.device_name
            if longname == "Default":
                longname = "Firewire bamera"
            source = Source('dv1394', longname, 'dv1394src ! dvdemux ! dvdec')
            sources.append(source)

        for device in glob.glob('/dev/video*'):
            v4l2 = Gst.ElementFactory.make('v4l2src')
            v4l2.set_property('device', device)
            if cls.test_source_element(v4l2):
                name = device[5:]
                longname = v4l2.get_property('device-name')
                if not longname:
                    longname = 'Video4Linux device'
                source = Source(name, longname, 'v4l2src device=%s' % device)
                sources.append(source)

        if len(sources) == 0:
            source = Source('smpte', 'SMPTE color bars',
                            'videotestsrc is-live=true')
            sources.append(source)

        return sources

    def __repr__(self):
        return "Source<{}>".format(self.description)

    def __str__(self):
        return self.longname


class ProducerWindow(Gtk.ApplicationWindow):

    def __init__(self, app):
        super().__init__(self, app, title="Telecorpo Producer")
        
        ## Draw the header bar
        hb = Gtk.HeaderBar()
        hb.props.show_close_button = True
        hb.props.title = "Telecorpo Producer"
        self.set_titlebar(hb)

        refresh_button = Gtk.Button()
        refresh_button.connect("clicked", self.on_refresh_clicked)
        icon = Gio.ThemedIcon(name="gtk-refresh")
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        refresh_button.add(image)
        hb.pack_end(refresh_button)

        ## Draw the source tree
        self.source_store = Gtk.ListStore(str, str, bool)
        self.tree = Gtk.TreeView(self.source_store)
        
        self.tree.append_column(
            Gtk.TreeViewColumn("Name", Gtk.CellRendererText(), text=0))

        self.tree.append_column(
            Gtk.TreeViewColumn("Description", Gtk.CellRendererText(), text=0))

        self.tree.append_column(
            Gtk.TreeViewColumn("Active", Gtk.CellRendererToggle(), text=0))



    def on_refresh_clicked(self, button):
        refresh_sources()

    def refresh_sources(self):
        self.sources = Source.find_sources()
        self.source_store.clear()
        for source in self.sources:
            self.source_store.append(source.name, source.longname, False)


class ProducerApplication(Gtk.Application):

    def __init__(self):
        Gtk.Application.__init__(self, application_id="telecorpo.producer")

        self.connect("activate", self.on_activate)

    def on_activate(self, event):
        window = ProducerWindow(self)
        window.show()


if __name__ == '__main__':
    app = ProducerApplication()
    exit_status = app.run(sys.argv)
    sys.exit(exit_status)



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

