
import gi
import ipaddress
import socket
import time
import tkinter as tk

from tkinter import messagebox, ttk

gi.require_version('Gst', '1.0')
gi.require_version('GdkX11', '3.0')
gi.require_version('Gtk', '3.0')
gi.require_version('GstVideo', '1.0')
gi.require_version('GstRtsp', '1.0')
from gi.repository import Gst, Gtk, GObject, GdkX11, GstVideo, GstRtsp


def query_producers(server_address):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((server_address, 13370))
        sock.send("*".encode())
        resp = sock.recv(4096).decode()

    producers = {}
    for line in resp.splitlines():
        line = line.split()
        producers[line[0]] = line[1:]
    return producers



class Pipeline:

    def __init__(self, main_xid, urls):

        self.urls = urls
        self.main_xid = main_xid
        self.pipe = Gst.Pipeline()
        self.url_to_index = {}

        self.bus = self.pipe.get_bus()
        self.bus.enable_sync_message_emission()
        self.bus.connect('sync-message::element', self.on_sync_message)

        self.selector = None
        self.build()

    def on_pad_added(self, element, pad, target):
        sinkpad = target.get_compatible_pad(pad, pad.get_current_caps())
        pad.link(sinkpad)

    def on_sync_message(self, bus, msg):
        if msg.get_structure().get_name() != 'prepare-window-handle':
            return
        if msg.src.get_name().startswith('main-sink'):
            msg.src.set_window_handle(self.main_xid)

    def build(self):
        self.selector = Gst.ElementFactory.make('input-selector', None)
        main_sink_queue = Gst.ElementFactory.make('queue', None)
        main_sink = Gst.ElementFactory.make('autovideosink', 'main-sink')

        self.pipe.add(self.selector)
        self.pipe.add(main_sink_queue)
        self.pipe.add(main_sink)

        self.selector.link(main_sink_queue)
        main_sink_queue.link(main_sink)

        index = -1
        for url in self.urls:
            index += 1
            self.url_to_index[url] = index

            src = Gst.ElementFactory.make("rtspsrc", None)
            src.set_property("latency", 30)
            src.set_property("location", url)

            queue1 = Gst.ElementFactory.make("queue", None)
            decode = Gst.ElementFactory.make("decodebin", None)
            queue2 = Gst.ElementFactory.make("queue", None)
            scale = Gst.ElementFactory.make("videoscale", None)
            convert = Gst.ElementFactory.make("videoconvert", None)
            rate = Gst.ElementFactory.make("videorate", None)

            self.pipe.add(src)
            self.pipe.add(queue1)
            self.pipe.add(decode)
            self.pipe.add(queue2)
            self.pipe.add(scale)
            self.pipe.add(convert)
            self.pipe.add(rate)

            src.connect("pad-added", self.on_pad_added, decode)
            decode.connect("pad-added", self.on_pad_added, scale)
            scale.link(convert)
            convert.link(rate)
            rate.link(self.selector)

    def start(self):
        self.pipe.set_state(Gst.State.PLAYING)

    def stop(self):
        self.pipe.set_state(Gst.State.NULL)

    def select(self, url):
        index = self.url_to_index[url]
        Gst.debug_bin_to_dot_file(self.pipe, Gst.DebugGraphDetails.CAPS_DETAILS, "pipe")
        selected_pad = self.selector.get_static_pad("sink_{}".format(index))
        self.selector.set_property('active-pad', selected_pad)


class VideoWindow(tk.Toplevel):
    def __init__(self):
        super().__init__()
        self.is_fullscreen = False
        self.configure(bg='#000')
        self.bind('<Double-Button-1>', self.toggle_fullscreen)
    
    def toggle_fullscreen(self, event):
        self.attributes('-fullscreen', self.is_fullscreen)
        self.is_fullscreen = not self.is_fullscreen

    def get_xid(self):
        return self.winfo_id()


class MainWindow(tk.Frame):

    def __init__(self, master):
        super().__init__(master)

        self.producers = None
        self.pipe = None
        self.video_window = None
        
        self.tree = None
        self.master.title('Telecorpo Viewer')
        self.draw_query_form()

    def draw_query_form(self):
        self.form = ttk.Frame(self.master)
        self.form.grid(row=0, sticky='nsew')
        self.master.rowconfigure(0, weight=1)

        def entry_placeholder(dummy):
            self.entry.delete(0, 'end')
            self.entry.unbind('<FocusIn>')

        self.entry = ttk.Entry(self.form)
        self.entry.insert(0, "server address")
        self.entry.bind('<Return>', self.on_click)
        self.entry.bind('<FocusIn>', entry_placeholder)
        self.entry.grid(row=0, column=0, sticky='nsew')
        self.form.columnconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)

        self.button = ttk.Button(self.form, text="Registrate",
                                 command=self.on_click)
        self.button.grid(row=0, column=1)

    def on_click(self, dummy=None): 
        try:
            server_address = str(ipaddress.ip_address(self.entry.get().strip()))
            query_producers(server_address)
        except Exception as err:
            messagebox.showerror("Error",
                                 "Failed to connect the server.\n{}".format(err))
            return
        
        self.update_sources(server_address)

    def on_selection(self, event):
        item = self.tree.selection()[0]
        self.pipe.select(self.tree.item(item, 'text'))

    def update_sources(self, server_address):

        def add_callback():
            self.master.after(1000, self.update_sources, server_address)
        
        new_producers = query_producers(server_address)
        if self.form:
            self.form.destroy()
            self.form = None

        if self.producers == new_producers:
            add_callback()
            return
        
        self.producers = new_producers

        if self.tree:
            self.tree.destroy()
        
        self.tree = ttk.Treeview(self.master)
        self.tree.configure(selectmode='browse')
        self.tree.bind('<<TreeviewSelect>>', self.on_selection)
        self.tree.grid(row=0, sticky='nsew')
        self.master.rowconfigure(0, weight=1)

        urls = []
        for producer in self.producers:
            for source in self.producers[producer]:
                index = len(urls)
                url = 'rtsp://{}:13371/{}'.format(producer, source)
                self.tree.insert('', 'end', text=url)
                urls.append(url)

        if self.pipe:
            self.pipe.stop()
        
        if not self.video_window:
            self.video_window = VideoWindow()

        self.pipe = Pipeline(self.video_window.get_xid(), urls)
        self.pipe.start()

        add_callback()


def main():
    Gst.init(None)
    root = tk.Tk()
    win = MainWindow(root)
    root.mainloop()


if __name__ == '__main__':
    main()
