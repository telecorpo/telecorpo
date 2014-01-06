
import re
import gi
import Tkinter as tk

from gi.repository import GObject, Gst, Gdk, GLib, GstVideo
from twisted.internet import reactor

from tc.exceptions import PipelineFailure

__ALL__ = ['Pipeline', 'StreamingWindow', 'PipelineFailure']


gi.require_version('Gst', '1.0')
GObject.threads_init()
Gdk.threads_init()
Gst.init(None)


class Element(object):
    def __init__(self, elem):
        self.__dict__['_elem'] = elem

    def __getattr__(self, name):
        name = name.replace('-', '_')
        try:
            return self.__dict__['_elem'].get_property(name)
        except Exception:
            # FIXME check for errors
            raise 

    def __setattr__(self, name, value):
        name = name.replace('-', '_')
        self.__dict__['_elem'].set_property(name, value)

    def emit(self, evt, *args):
        self._elem.emit(evt, *args)


class Pipeline(object):
    """Parses a gstreamer pipeline and provide access to its elements events.
    
    """

    _named_elements_re = re.compile(r'\sname=(\w+)')
    _named_tee_sink_re = re.compile(r'tee.*?name=(\w+)')

    def __init__(self, desc):
        # pipeline spec
        self.description = desc
        
        try:
            self._pipe = Gst.parse_launch(desc)
        except GObject.GError as err:
            raise PipelineFailure("%s: %s" % (err, ' '.join(desc.split())))

        # don't allow duplicated element names
        names = self._named_elements_re.findall(desc)
        if any(names.count(n) > 1 for n in names):
            raise PipelineFailure("Duplicate element '%s'" % name)

        self.bus = self._pipe.get_bus()
        self.bus.enable_sync_message_emission()
        self.bus.connect('sync-message::element', self._on_sync)
        
        self.xid = None
        self._xid = None # trick to test XID
        self._is_started = False
    
    def __getattr__(self, name):
        """Provides attribute access for pipeline elements."""
        name = name.replace('-', '_')
        return Element(self.__dict__['_pipe'].get_by_name(name))

    def _on_sync(self, bus, msg):
        if msg.get_structure().get_name() != 'prepare-window-handle':
            return
        msg.src.set_property('force-aspect-ratio', True)
        msg.src.set_window_handle(self.xid)
        self._xid = self.xid
    
    def setXID(self, xid):
        self.xid = xid

    def start(self):
        """Starts the pipeline."""
        self._is_started = True
        self._pipe.set_state(Gst.State.PLAYING)

    def stop(self):
        """Stops the pipeline."""
        self._is_started = False
        self._pipe.set_state(Gst.State.NULL)

    @property
    def is_started(self):
        return self._is_started


class StreamingWindow(object):
    def __init__(self, root, pipe, title):
        self.pipe = pipe
        self.root = root
        self.title = title
        self.root.wm_title(title)

        self.frame = tk.Frame(self.root, bg='#000000')
        self.frame.pack(expand=tk.YES, fill=tk.BOTH)

        # bind window events
        self.root.protocol("WM_DELETE_WINDOW", self.stop)
        self.frame.bind('<Double-Button-1>', self._toggle_fullscreen)
        self._is_fullscreen = False

        # window handler
        self.xid = self.frame.winfo_id()
        self.pipe.setXID(self.xid)

    def _toggle_fullscreen(self, evt):
        self.root.attributes('-fullscreen', self._is_fullscreen)
        self._is_fullscreen = not self._is_fullscreen
    
    def start(self):
        self.pipe.start()

    def stop(self):
        self.pipe.stop()
        reactor.stop()

