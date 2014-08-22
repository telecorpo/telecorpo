
import socket
from gi.repository import GLib, Gst, GstRtsp, GstRtspServer, GUdev
from tc import Application


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
        factory.props.shared = True
        # factory.props.profiles = GstRtsp.RTSPProfile.AVPF
        mounts.add_factory("/{}".format(mount_point), factory)

    return server.attach()


def test_source_element(launch):
    pipe = Gst.parse_launch("%s ! fakesink" % launch)
    pipe.set_state(Gst.State.PLAYING)
    ok = True
    if Gst.StateChangeReturn.FAILURE == pipe.get_state(0)[0]:
        ok = False
    pipe.set_state(Gst.State.NULL)
    return ok


def find_devices():
    udev = GUdev.Client()
    for device in udev.query_by_subsystem('video4linux'):
        launch = "v4l2src device=%s" % device.get_device_file()
        if test_source_element(launch):
            mount_point = device.get_name()
            description = device.get_property('ID_V4L_PRODUCT')
            yield (mount_point, description, launch)
    for device in udev.query_by_subsystem('firewire'):
        launch = "dv1394src guid=%s ! dvdemux ! dvdec" % device.get_sysfs_attr('guid')
        if test_source_element(launch):
            mount_point = device.get_name()
            description = device.get_sysfs_attr('model_name')
            yield (mount_point, description, launch)
    yield ("desktop", "Desktop sharing", "ximagesrc")
    yield ("smpte", "SMPTE color bars", "videotestsrc is-live=true")


def registrate_producer(server_address, mount_points):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        sock.connect((server_address, 13370))
        sock.send(" ".join(mount_points).encode())
        resp = sock.recv(1024).decode()
    if resp != "OK":
        raise Exception(resp)


class Producer(Application):

    glade_file = 'producer.glade'

    def __init__(self):
        super().__init__()
        for mount_point, description, launch in find_devices():
            self.add_device(mount_point, description, launch)

    def add_device(self, mount_point, description, launch):
        source_store = self.builder.get_object('source-store')
        source_store.append([mount_point, description, False, launch])
    
    def get_selected_sources(self):
        source_store = self.builder.get_object('source-store')
        for mount_point, description, enable, launch in source_store:
            if enable:
                yield (mount_point, launch)
    
    def connect(self, address):
        """
        Registrate this producer on server.

        """
        sources = list(self.get_selected_sources())
        mount_points = [mp for mp, _ in sources] 

        if len(sources) == 0:
            raise Exception("Select a least one video source")
        
        rtsp_id = run_rtsp_server(sources)
        
        try:
            registrate_producer(address, mount_points)
        except:
            GLib.source_remove(rtsp_id)
            raise
        
        treeview = self.builder.get_object('treeview')
        treeview.set_sensitive(False)
        
        self.__pipelines = []
        for mount_point in mount_points:
            url = 'rtsp://127.0.0.1:13371/%s' % mount_point
            pipe = Gst.parse_launch("rtspsrc location=%s ! fakesink" % url)
            pipe.set_state(Gst.State.PLAYING)
            self.__pipelines.append(pipe)

    def on_enablecell_toggled(self, cell_renderer, path):
        source_store = self.builder.get_object('source-store')
        source_store[path][2] = not source_store[path][2]

