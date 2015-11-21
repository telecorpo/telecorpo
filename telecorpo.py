
import ipaddress
import gi
import time

gi.require_version('Gtk', '3.0')
gi.require_version('GUdev', '1.0')
gi.require_version('GstRtspServer', '1.0')
gi.require_version('GstRtsp', '1.0')

from gi.repository import GObject, Gtk, GUdev, GstRtspServer, GstRtsp


SETTINGS = {
    'CHANNEL_PORT': 1234,
    'RTSP_PORT': 8554,
    'RTSP_ADDR_RANGE': ipaddress.IPv4Network('224.3.44.0/24'),
    'RTSP_PORT_RANGE': range(5000, 5011),
    'TTL': 16,
}

def show_error_dialog(message):
    dialog = Gtk.MessageDialog(SETTINGS['APP_WINDOW'], 0,
                               Gtk.MessageType.ERROR,
                               Gtk.ButtonsType.OK,
                               "Error")
    dialog.format_secondary_text(message)
    dialog.set_modal(True)
    dialog.run()
    dialog.destroy()

def run_server(sources_model):
    server = GstRtspServer.RTSPServer()
    # server.set_service(str(RTSP_PORT))
    
    addr_pool = GstRtspAdressPool()
    addr_pool.addr_range(min(SETTINGS['RTSP_ADDR_RANGE']),
                         max(SETTINGS['RTSP_ADDR_RANGE']),
                         min(SETTINGS['RTSP_PORT_RANGE']),
                         max(SETTINGS['RTSP_PORT_RANGE']),
                         SETTINGS['TTL'])

    mounts = server.get_mount_points()
    for path, name, src_pipe in sources_model:
        launch = ("( {} ! queue ! videoconvert ! videoscale ! videorate"
                  " ! video/x-raw,format=I420 ! queue"
                  " ! x264enc tune=zerolatency intra-refresh=true key-int-max=0"
                  " ! queue ! rtph264pay pt=96 name=pay0 )"
                  "".format(src_pipe))
        factory = GstRtspServer.RTSPMediaFactory()
        factory.set_launch(launch)
        factory.set_shared(True)
        factory.set_suspend_mode(GstRtspServer.RTSPSuspendMode.NONE)
        factory.set_address_pool(addr_pool, GstRtsp.RTSPLowerTrans.UDP_MCAST)
        mounts.add_factory(path, factory)

    return server.attach()


class ServerPage(Gtk.Box):

    def __init__(self):
        super().__init__()
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.sources_model = Gtk.ListStore(str, str, str)
        self.sources_model.append(('/smpte',
                                   'SMPTE Color Bars',
                                   'videotestsrc is-live=1'))
        self.view = Gtk.TreeView.new_with_model(self.sources_model)
        self.view.props.expand = True
        self.pack_start(self.view, True, True, 0)

        self.view.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        for i, title in enumerate(['identifier', 'name', 'pipeline']):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=i)
            self.view.append_column(column)
        
        hbox = Gtk.Box()
        self.pack_start(hbox, True, True, 0)
        self.h264_parameters = Gtk.Entry()
        hbox.pack_start(Gtk.Label("H.264 parameters"), True, True, 0)
        hbox.pack_start(self.h264_parameters, True, True, 0)

        self.switch = Gtk.Switch()
        self.switch.props.expand = False
        self.pack_end(self.switch, True, True, 0)
        self.switch.connect('state-set', self.on_switch_state_set)
    
        client = GUdev.Client.new(['video4linux'])
        client.connect('uevent', self.on_uevent)
    
        for device in client.query_by_subsystem('video4linux'):
            self.add_v4l_device(device)

    def on_switch_state_set(self, switch, state):
        if switch:
            self.server_id = run_server(self.sources_model)
        elif not GObject.Source.is_destroyed(self.server_id):
            GObject.Source.destroy(self.server_id)

    def add_v4l_device(self, device):
        path = '/%s' % device.get_name()
        name = ' '.join(device.get_sysfs_attr_as_strv('name'))
        pipe = 'v4l2src device=%s' % device.get_device_file()
        self.sources_model.append((path, name, pipe))

    def on_uevent(self, client, action, device):
        # FIXME "path" é um péssimo nome
        if action == 'add':
            if device.get_subsystem() == 'video4linux':
                self.add_v4l_device(device) 
            elif device.get_subsystem() == 'ieee1394':
                raise NotImplementedError()

        elif action == 'remove':
            path = '/%s' % device.get_name()
            for row in self.sources_model:
                if path == row[0]:
                    break
            else:
                self.sources_model.remove(row.iter)


class ViewerPage(Gtk.Box):
    
    def __init__(self):
        super().__init__()
        self.set_orientation(Gtk.Orientation.VERTICAL)
        
        areas = {k:Gtk.DrawingArea() for k in range(9)}
        
        #TODO substituir por um flowbox
        self.grid = Gtk.Grid()
        self.grid.props.expand = True
        self.pack_start(self.grid, True, True, 0)

        for i, (url, area) in enumerate(areas.items()):
            self.grid.attach(area, i%3, i//3, 1, 1)
        
        self.switch = Gtk.Switch()
        self.switch.props.expand = False
        self.pack_end(self.switch, True, True, 0)


class ConfigPage(Gtk.Grid):

    def __init__(self):
        super().__init__()
        self.draw()

    def draw(self): 
        self.attach(Gtk.Label("Channel port"), 0, 0, 1, 1)
        adjustment = Gtk.Adjustment(SETTINGS['CHANNEL_PORT'],
                1024, 2**16-1, 1, 10, 100)
        channel_port = Gtk.SpinButton()
        channel_port.set_adjustment(adjustment)
        self.attach(channel_port, 1, 0, 2, 1)

        self.attach(Gtk.Label("RTSP port"), 0, 1, 1, 1)
        adjustment = Gtk.Adjustment(SETTINGS['RTSP_PORT'],
                1024, 2**16-1, 1, 10, 100)
        rtsp_port = Gtk.SpinButton()
        rtsp_port.set_adjustment(adjustment)
        self.attach(rtsp_port, 1, 1, 2, 1)

        self.attach(Gtk.Label("RTSP address range"), 0, 2, 1, 1)
        rtsp_addr_range = Gtk.Entry() 
        rtsp_addr_range.set_text(str(SETTINGS['RTSP_ADDR_RANGE']))
        self.attach(rtsp_addr_range, 1, 2, 2, 1)

        self.attach(Gtk.Label("RTSP port range"), 0, 3, 1, 1)
        adjustment = Gtk.Adjustment(min(SETTINGS['RTSP_PORT_RANGE']),
                1024, 2**16-1, 1, 10, 100)
        rtsp_port_min = Gtk.SpinButton() 
        rtsp_port_min.set_adjustment(adjustment)
        self.attach(rtsp_port_min, 1, 3, 1, 1)
        adjustment = Gtk.Adjustment(max(SETTINGS['RTSP_PORT_RANGE']),
                1024, 2**16-1, 1, 10, 100)
        rtsp_port_max = Gtk.SpinButton() 
        rtsp_port_max.set_adjustment(adjustment)
        self.attach(rtsp_port_max, 2, 3, 1, 1)

        channel_port.connect('value-changed', self.on_channel_port_value_changed)
        rtsp_port.connect('value-changed', self.on_rtsp_port_value_changed)
        rtsp_port_min.connect('value-changed', self.on_rtsp_port_min_value_changed,
                rtsp_port_max)
        rtsp_port_max.connect('value-changed', self.on_rtsp_port_max_value_changed,
                rtsp_port_min)
        rtsp_addr_range.connect('focus-out-event', self.on_rtsp_addr_range_focus_out_event)

    def on_channel_port_value_changed(self, spinbutton):
        SETTINGS['CHANNEL_PORT'] = spinbutton.get_value_as_int()

    def on_rtsp_port_value_changed(self, spinbutton):
        SETTINGS['RTSP_PORT'] = spinbutton.get_value_as_int()

    def on_rtsp_port_min_value_changed(self, rtsp_port_min, rtsp_port_max):
        min_val = rtsp_port_min.get_value_as_int()
        max_val = rtsp_port_max.get_value_as_int()
        try:
            self.set_rtsp_port_range(min_val, max_val)
        except:
            rtsp_port_min.set_value(min(SETTINGS['RTSP_PORT_RANGE']))

    def on_rtsp_port_max_value_changed(self, rtsp_port_max, rtsp_port_min):
        min_val = rtsp_port_min.get_value_as_int()
        max_val = rtsp_port_max.get_value_as_int()
        try:
            self.set_rtsp_port_range(min_val, max_val)
        except:
            rtsp_port_max.set_value(max(SETTINGS['RTSP_PORT_RANGE']))
    
    def set_rtsp_port_range(self, min_val, max_val):
        if min_val >= max_val:
            msg = "Wrong RTSP port range. %d >= %d" % (min_val, max_val)
            show_error_dialog(msg)
            raise Exception
        SETTINGS['RTSP_PORT_RANGE'] = range(min_val, max_val+1)

    def on_rtsp_addr_range_focus_out_event(self, entry, event):
        try:
            addr_range = ipaddress.IPv4Network(entry.get_text())
            SETTINGS['RTSP_ADDR_RANGE'] = addr_range
        except Exception as err:
            show_error_dialog(str(err))
            entry.set_text(str(SETTINGS['RTSP_ADDR_RANGE']))


class MainWindow(Gtk.ApplicationWindow):

    def __init__(self):
        super().__init__(title="TeleCorpo")
        
        headerbar = Gtk.HeaderBar()
        headerbar.set_show_close_button(True)
        headerbar.set_decoration_layout('menu:minimize,close')
        headerbar.props.title = 'TeleCorpo'
        self.set_titlebar(headerbar)
        
        notebook = Gtk.Notebook()
        self.add(notebook)
        notebook.props.tab_pos = Gtk.PositionType.LEFT

        self.server_page = ServerPage()
        notebook.append_page(self.server_page, Gtk.Label('Server'))
        
        self.viewer_page = ViewerPage()
        notebook.append_page(self.viewer_page, Gtk.Label('Viewer'))

        self.config_page = ConfigPage()
        notebook.append_page(self.config_page, Gtk.Label('Settings'))

        self.connect('delete-event', Gtk.main_quit)


if __name__ == '__main__':
    main_window = MainWindow()
    main_window.show_all()
    main_window.show_all()
    main_window.show_all()

    SETTINGS['APP_WINDOW'] = main_window

    def debug():
        from pprint import pprint
        pprint(SETTINGS)
        return True
    GObject.timeout_add(2000, debug)

    Gtk.main()

