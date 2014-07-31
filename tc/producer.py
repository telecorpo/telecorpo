
import socket

from ipaddress import IPv4Address
from gi.repository import GObject, Gst, GstRtspServer, Gtk, GUdev


def connect(server_address, source_names):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((server_address, 13370))
        sock.send(" ".join(source_names).encode())
        resp = sock.recv(1024).decode()
    if resp != "OK":
        raise Exception(resp)


def run_rtsp_server(sources):
    server = GstRtspServer.RTSPServer()
    server.set_service("13371")

    mounts = server.get_mount_points()
    for mount_point, pipeline in sources:
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
    
    consumers = [] 
    for mount_point, _ in sources:
        pipe = Gst.parse_launch("""
            rtspsrc location=rtsp://127.0.0.1:13371/%s ! fakesink
        """ % mount_point)
        pipe.set_state(Gst.State.PLAYING)
        consumers.append(pipe)
    return server, consumers


def test_source_element(launch):
    pipe = Gst.parse_launch("%s ! fakesink" % launch)
    pipe.set_state(Gst.State.PLAYING)
    ok = True
    if Gst.StateChangeReturn.FAILURE == pipe.get_state(0)[0]:
        ok = False
    pipe.set_state(Gst.State.NULL)
    return ok


class Producer:

    def __init__(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_file('producer.glade')
        self.builder.connect_signals(self)
        self.window = self.builder.get_object('main-window')
        self.source_store = self.builder.get_object('source-store')
    
    @classmethod
    def main(cls):
        GObject.threads_init()
        Gst.init()
        
        producer = cls()
        producer.window.show_all()

        Gtk.main()

    def error(self, message):
        dialog = Gtk.MessageDialog(self.window, 0, Gtk.MessageType.ERROR,
                Gtk.ButtonsType.OK, "Error")
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def add_device(self, name, description, launch):
        self.source_store.append([name, description, False, launch])
    
    def connect(self):
        address = self.builder.get_object('address-entry').get_text().strip()
        try:
            IPv4Address(address)
        except ValueError:
            self.error("'%s' does not appear to be a valid IPv4 address"
                    % address)
            return
        
        sources = []
        for name, description, enable, launch in self.source_store:
            if enable:
                sources.append((name, launch))

        if len(sources) == 0:
            self.error("Select at least one video source")
            return

        refresh_button = self.builder.get_object('refresh-button')
        refresh_button.set_sensitive(False)

        treeview = self.builder.get_object('treeview')
        treeview.set_sensitive(False)
        
        # keep object to avoid garbage collection
        self.dummy = run_rtsp_server(sources)

        try: 
            connect(address, [name for name, launch in sources])
        except Exception as err:
            self.error("Could not connect to server.\n%s" % err)
            return

        form_box = self.builder.get_object('form-box')
        form_box.set_sensitive(False)

    def refresh(self):
        self.source_store.clear()
        udev = GUdev.Client()
        for device in udev.query_by_subsystem('video4linux'):
            launch = "v4l2src device=%s" % device.get_device_file()
            if test_source_element(launch):
                name = device.get_name()
                description = device.get_property('ID_V4L_PRODUCT')
                self.add_device(name, description, launch)

        self.add_device("smpte", "SMPTE color bars",
                "videotestsrc is-live=true")

        self.add_device("desktop", "Desktop sharing",
                "ximagesrc ! videoconvert ! videoscale"
                " ! video/x-raw,width=1280,height=720")
   
    def on_enablecell_toggled(self, cell_renderer, path):
        self.source_store[path][2] = not self.source_store[path][2]

    def on_refresh_button_clicked(self, button):
        self.refresh()

    def on_connect_button_clicked(self, button):
        self.connect()

    def on_main_window_delete_event(self, *args):
        Gtk.main_quit(*args)


if __name__ == '__main__':
    producer = Producer()
    producer.main()

