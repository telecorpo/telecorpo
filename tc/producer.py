

import glob
import ipaddress
import socket

from gi.repository import Gst, GstRtspServer, Gtk

def test_source(elem):
    pipe = Gst.parse_launch('{} ! fakesink'.format(elem))
    pipe.set_state(Gst.State.PLAYING)
    ok = True
    if Gst.StateChangeReturn.FAILURE == pipe.get_state(0)[0]:
        ok = False
    pipe.set_state(Gst.State.NULL)
    return ok


def probe_sources():
    sources = {'smpte': ("videotestsrc is-live=true ! queue"
                        " ! x264enc preset=ultrafast tune=zerolatency"
                        " ! queue ! rtph264pay")}

    if test_source('dv1394src'):
        sources['dv1394'] = "dv1394src ! queue ! rtpdvpay"

    for dev in glob.glob('/dev/video*'):
        elem = 'v4l2src device={}'.format(dev)
        name = dev[5:]
        if test_source(elem):
            sources[name] = ("{} !  queue ! videoconvert"
                             " ! video/x-raw,format=I420 ! queue"
                             " ! x264enc preset=ultrafast tune=zerolatency"
                             " ! queue ! rtph264pay".format(elem))
    return sources


def run_rtsp_server(sources):
    server = GstRtspServer.RTSPServer()
    server.set_service("13371")
    
    mounts = server.get_mount_points()
    for mount_point, pipeline in sources.items():
        factory = GstRtspServer.RTSPMediaFactory()
        factory.set_launch("( {} name=pay0 pt=96 )".format(pipeline))
        factory.set_shared(True)
        mounts.add_factory("/{}".format(mount_point), factory)

    server.attach()
    return server


def registrate_producer(server_address, source_names):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((server_address, 13370))
        sock.send(" ".join(source_names).encode())
        resp = sock.recv(1024).decode()
    if resp != "OK":
        raise Exception(resp)


class ProducerWindow(Gtk.Window):

    def __init__(self):
        super().__init__(title="Telecorpo Producer")

        self.available_sources = probe_sources()
        self.selected_sources = {}

        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.draw_source_list()
        self.draw_connection_form()

        self.add(self.vbox)
    
    def draw_source_list(self):
        self._sources_liststore = Gtk.ListStore(str, bool)
        for srcname in self.available_sources:
            self._sources_liststore.append([srcname, False])
        
        treeview = Gtk.TreeView(model=self._sources_liststore)

        treeview.append_column(
            Gtk.TreeViewColumn("Video source", Gtk.CellRendererText(), text=0))
        
        renderer = Gtk.CellRendererToggle()
        renderer.connect("toggled", self.on_source_toggled)
        treeview.append_column(
            Gtk.TreeViewColumn("Activate", renderer, active=1))
        
        self.vbox.add(treeview)
    
    def draw_connection_form(self):
        hbox = Gtk.Box()

        self._connection_entry = Gtk.Entry()
        self._connection_entry.set_placeholder_text("Server address")
        hbox.add(self._connection_entry)
        
        button = Gtk.Button("Registrate")
        button.connect("clicked", self.on_registrate_clicked)
        hbox.add(button)

        self.vbox.add(hbox)

    def on_source_toggled(self, widget, path):
        self._sources_liststore[path][1] = not self._sources_liststore[path][1]
        self.selected_sources.clear()
        for source_name, selected in self._sources_liststore: 
            if selected:
                self.selected_sources[source_name] = self.available_sources[source_name]

    def on_registrate_clicked(self, button):

        def error(message):
            dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR,
                Gtk.ButtonsType.OK, "Couldn't connect to server")
            dialog.format_secondary_text(message)
            dialog.run()
            dialog.destroy()
       
        if len(self.selected_sources) == 0:
            return error("No sources activated")
        
        # keep variable to avoid garbage collection
        self._server = run_rtsp_server(self.selected_sources)

        try:
            address = self._connection_entry.get_text().strip()
            address = str(ipaddress.ip_address(address))
            registrate_producer(address, self.selected_sources)
            pass
        except Exception as err:
            self._server = None
            return error(str(err))
        
        self.vbox.set_sensitive(False)


if __name__ == '__main__':
    # main()
    Gst.init()
    win = ProducerWindow()
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()
    Gtk.main()
