
import socket
from gi.repository import GObject, Gdk, Gst, Gtk, GstVideo, GdkX11
from tc import Application

def query_producers(server_address):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        sock.connect((server_address, 13370))
        sock.send("*".encode())
        resp = sock.recv(4096).decode()

    producers = {}
    for line in resp.splitlines():
        line = line.split()
        producers[line[0]] = line[1:]
    return producers


def search_element(bin, klass):
    iter = bin.iterate_elements()
    while True:
        status, elem = iter.next()
        if isinstance(elem, klass):
            return elem
    return None


class Pipeline:

    def __init__(self, xid):
        self.xid = xid

        self.pipe = Gst.Pipeline()
        self.index = {}
        self.message_callback = lambda *args: print('%s', args)

        bus = self.pipe.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect('sync-message::element', self.on_sync_message)
        bus.connect('message', self.on_message)

        self.selector = Gst.ElementFactory.make('input-selector')
        sink = Gst.ElementFactory.make('autovideosink')
        sink.props.sync = False

        self.pipe.add(self.selector)
        self.pipe.add(sink)

        self.selector.link(sink)

    def on_sync_message(self, bus, msg):
        if msg.get_structure().get_name() != 'prepare-window-handle':
            return
        msg.src.set_window_handle(self.xid)

    def on_message(self, bus, msg):
        if msg.type == Gst.MessageType.ERROR:
            self.pipe.set_state(Gst.State.NULL)
            error, text = msg.parse_error()
            self.message_callback('ERROR: %s\n%s' % (error, text))
        elif msg.type == Gst.MessageType.WARNING:
            error, text = msg.parse_warning()
            self.message_callback('WARNING: %s\n%s' % (error, text))

    def add_source(self, producer, src_elem):
        queue1 = Gst.ElementFactory.make("queue", None)
        decode = Gst.ElementFactory.make("decodebin", None)
        queue2 = Gst.ElementFactory.make("queue", None)
        scale = Gst.ElementFactory.make("videoscale", None)
        convert = Gst.ElementFactory.make("videoconvert", None)
        rate = Gst.ElementFactory.make("videorate", None)

        self.pipe.add(src_elem)
        self.pipe.add(queue1)
        self.pipe.add(decode)
        self.pipe.add(queue2)
        self.pipe.add(scale)
        self.pipe.add(convert)
        self.pipe.add(rate)

        def on_pad_added(element, pad, target):
            sinkpad = target.get_compatible_pad(pad, pad.get_current_caps())
            pad.link(sinkpad)

        src_elem.connect("pad-added", on_pad_added, queue1)
        queue1.link(decode)
        decode.connect("pad-added", on_pad_added, queue2)
        queue2.link(scale)
        scale.link(convert)
        convert.link(rate)
        rate.link(self.selector)

        self.index[producer] = len(self.index)
    
    def select(self, producer):
        index = self.index[producer]
        selected_pad = self.selector.get_static_pad("sink_{}".format(index))
        self.selector.set_property('active-pad', selected_pad)

    def start(self):
        self.pipe.set_state(Gst.State.PLAYING)

    def stop(self):
        self.pipe.set_state(Gst.State.NULL)

    def set_message_callback(self, callback):
        self.message_callback = callback



class Viewer(Application):
    
    glade_file = 'viewer.glade'

    def __init__(self):
        super().__init__()
        self.pipeline = None
        self.latency = 100
        
        video_window = self.builder.get_object('video-window')
        video_window.show_all()
        
        display = self.builder.get_object('display')
        self.xid = display.props.window.get_xid()

        self.is_fullscreen = False

    def on_video_window_button_press_event(self, widget, event):
        if event.button == 1:
            video_window = self.builder.get_object('video-window')
            if self.is_fullscreen:
                video_window.unfullscreen()
            else:
                video_window.fullscreen()
            self.is_fullscreen = not self.is_fullscreen

    def connect(self, address):
        try:
            producers = query_producers(address)
        except Exception as err:
            raise Exception("Couldn't connect to server.\n%s" % str(err))
        
        self.server_address = address
        self.refresh()
        GObject.timeout_add_seconds(1, self.refresh)

    def refresh(self):
        source_store = self.builder.get_object('source-store')
        old_producers = set()
        rtsp_srcs = {}
        
        for _, addr, mp, _, _, _, _, rtspsrc in source_store:
            producer = (addr, mp)
            old_producers.add(producer)
            rtsp_srcs[producer] = rtspsrc
        
        server_producers = query_producers(self.server_address)
        new_producers = set()

        for addr, mount_points in server_producers.items():
            for mp in mount_points:
                producer = (addr, mp)
                new_producers.add(producer)
        
        if old_producers != new_producers:
            self.update_sources(new_producers)
        else:
            self.update_stats()
        return True
    
    def update_sources(self, producers):
        source_store = self.builder.get_object('source-store')
        source_store.clear()
        
        if self.pipeline:
            self.pipeline.stop()
        self.pipeline = Pipeline(self.xid)
        self.pipeline.set_message_callback(self.on_pipeline_message)

        for addr, mp in producers:
            url = "rtsp://%s:13371/%s" % (addr, mp)

            rtspsrc = Gst.ElementFactory.make('rtspsrc')
            rtspsrc.props.latency = self.latency
            rtspsrc.props.location = url

            row = [url, addr, mp, '-', '-', '-', '-', rtspsrc]
            source_store.append(row)

            self.pipeline.add_source((addr, mp), rtspsrc)

        self.pipeline.start()

    def update_stats(self):
        source_store = self.builder.get_object('source-store')

        for i in range(len(source_store)):
            url, addr, mp, _, _, _, _, rtspsrc = source_store[i]

            rtpbin_class = Gst.ElementFactory.make('rtpbin').__class__
            rtpbin = search_element(rtspsrc, rtpbin_class)
            assert rtpbin

            jitter_class = Gst.ElementFactory.make('rtpjitterbuffer').__class__
            jitter = search_element(rtpbin, jitter_class)
            assert jitter

            #FIXME dont do this every second!!!
            jitter.props.do_retransmission = True
            
            stats = jitter.props.stats

            rtx = str(stats.get_value('rtx-count'))
            rtx_success = str(stats.get_value('rtx-success-count'))
            rtx_per_packet = str(stats.get_value('rtx-per-packet'))
            rtx_rtt = str(stats.get_value('rtx-rtt'))
            
            source_store[i] = [url, addr, mp, rtx, rtx_success, rtx_per_packet,
                               rtx_rtt, rtspsrc]
    
    def on_pipeline_message(self, message):
        message_buffer = self.builder.get_object('message-buffer')
        bounds = message_buffer.get_bounds()
        text = message_buffer.get_text(bounds[0], bounds[1], True)
        message_buffer.set_text(text + '\n\n' + message)

    def on_treeview_selection_changed(self, tree_selection):
        source_store = self.builder.get_object('source-store')
        if len(source_store) == 0:
            return
        path = tree_selection.get_selected_rows()[1][0]

        addr = source_store[path][1]
        mp = source_store[path][2]
        
        producer = (addr, mp)
        self.pipeline.select(producer)

    def on_config_button_clicked(self, button):
        source_store = self.builder.get_object('source-store')
        self.latency = self.builder.get_object('latency-spin').get_value_as_int()

        source_store.clear()
        self.refresh()
        

