
import re
import tkinter as tk

from gi.repository import GObject, Gst, Gdk, GLib, GstVideo
from tc.common import get_logger, TCFailure


__ALL__ = ['Pipeline', 'StreamingWindow', 'PipelineFailure']


GObject.threads_init()
Gdk.threads_init()
Gst.init(None)


class PipelineFailure(TCFailure):
    pass


class Element:
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


class Pipeline:
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
            raise PipelineFailure(str(err))

        # don't allow duplicated element names
        names = self._named_elements_re.findall(desc)
        if any(names.count(n) > 1 for n in names):
            raise PipelineFailure("Duplicate element '%s'" % name)

        self.bus = self._pipe.get_bus()
        self._is_playing = False
    
    def __getattr__(self, name):
        """Provides attribute access for pipeline elements."""
        name = name.replace('-', '_')
        return Element(self.__dict__['_pipe'].get_by_name(name))

    def play(self):
        """Starts the pipeline."""
        self._is_playing = True
        self._pipe.set_state(Gst.State.PLAYING)

    def stop(self):
        """Stops the pipeline."""
        self._is_playing = False
        self._pipe.set_state(Gst.State.NULL)

    @property
    def is_playing(self):
        return self._is_playing


class StreamingWindow:
    def __init__(self, root, pipe, title):
        self.pipe = pipe
        self.pipe.bus.enable_sync_message_emission()
        self.pipe.bus.connect('sync-message::elemen', self._on_sync)
        
        self.root = root
        self.title = self.root.title = title

        self.frame = tk.Frame(self.root, bg='#000000')
        self.frame.pack(expand=tk.YES, fill=tk.BOTH)

        # bind window events
        self.root.protocol("WM_DELETE_WINDOW", self.stop)
        self.frame.bind('<Double-Button-1>', self._toggle_fullscreen)
        self._is_fullscreen = False

        # window handler
        self.xid = self.frame.winfo_id()

    def _on_sync(self, bus, msg):
        if msg.get_structure().get_name() != 'prepare-window-handle':
            return
        msg.src.set_property('force-aspect-ratio', True)
        msg.src.set_window_handle(self.xid)

    def _toggle_fullscreen(self, evt):
        self.root.attributes('-fullscreen', self._is_fullscreen)
        self._is_fullscreen = not self._is_fullscreen
    
    def play(self):
        self.pipe.play()

    def stop(self):
        self.pipe.stop()
        self.root.destroy()
    



class ScreenWindow(StreamingWindow):
    def __init__(self, src, name, latency=200):
        pipe = Pipeline("""
            udpsrc port=%d caps=application/x-rtp
                ! rtpjitterbuffer latency=%d name=buffer ! rtph264depay
                ! decodebin ! xvimagesink""" % src)
        title = '%s - tc-screen' % name
        super(ScreenWindow, self).__init__(pipe, title)

        self.frame.bind('<Button-4>', self._on_mouse_wheel)
        self.frame.bind('<Button-5>', self._on_mouse_wheel)

    def _on_mouse_wheel(self, evt):
        latency = self.pipe.property('buffer', 'latency')
        text = None
        if evt.num == 5 and latency - 100 >= 0:
            latency -= 100
            text = 'decreased'
        elif evt.num == 4:
            latency += 100
            text = 'increased'
        if text:
            self.pipe.stop()
            self.pipe = Pipeline(self.pipe.description)
            self.pipe.play()
            LOG.info("Latency %s: %.1f s", text, latency/1000)
    
