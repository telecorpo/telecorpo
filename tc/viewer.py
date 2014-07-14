
import ipaddress
import socket
import time
import tkinter as tk

from tkinter import messagebox, ttk
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

    def __init__(self, producers, extra):
        self.producers = producers
        self.extra = extra

        self.pipe = None
        self.bus = None
        self.selector = None

        self.build()

    def on_pad_added(self, element, pad, target):
        sinkpad = target.get_compatible_pad(pad, pad.get_caps())
        pad.link(sinkpad)
        # return True

    def build(self):
        
        if self.pipe:
            self.pipe.set_state(Gst.State.NULL)
        self.pipe = Gst.Pipeline()

        self.selector = Gst.ElementFactory.make('input-selector', None)
        big_sink = Gst.ElementFactory.make('xvimagesink', 'big-sink') 

        self.pipe.add(self.selector)
        self.pipe.add(big_sink)

        self.selector.link(big_sink)

        index = 0

        for producer in sorted(self.producers):
            for source in  sorted(self.producers[producer]):

                src = Gst.ElementFactory.make("rtspsrc", None)
                src.set_property("latency", 100)
                src.set_property("location",
                        "rtsp://{}:13371/{}".format(producer, source))

                decode = Gst.ElementFactory.make("decodebin", "decode-%s" % index)
                tee = Gst.ElementFactory.make("tee", "tee-%s" % index)
                 
                queue1 = Gst.ElementFactory.make("queue", "q1-%s" % index)
                videosink = Gst.ElementFactory.make("autovideosink", "videosink-%s" % index)

                queue2 = Gst.ElementFactory.make("queue", "q2-%s" % index)
                scale = Gst.ElementFactory.make("videoscale", "scale-%s" % index)
                convert = Gst.ElementFactory.make("videoconvert", "convert-%s" % index)
                rate = Gst.ElementFactory.make("videorate", "rate-%s" % index)


                self.pipe.add(src)
                self.pipe.add(decode)
                self.pipe.add(tee)
                self.pipe.add(queue1)
                self.pipe.add(videosink)
                self.pipe.add(queue2)
                self.pipe.add(scale)
                self.pipe.add(convert)
                self.pipe.add(rate)


                src.link(decode)
                decode.connect("pad-added", self.on_pad_added, tee)

                tee.link(queue1)
                queue1.link(videosink)
                
                tee.link(queue2)
                queue2.link(scale)
                scale.link(convert)
                convert.link(rate)

                rate.link(self.selector)

                self.extra[producer][source]['index'] = index
                index += 1

    def start(self):
        self.pipe.set_state(Gst.State.PLAYING)

    def stop(self):
        self.pipe.set_state(Gst.State.NULL)

    def select(self, producer, source):
        index = self.extra[producer][source]['index']
        selected_pad = self.selector.get_static_pad("sink_{}".format(index))
        self.selector.set_property('active-pad', selected_pad)



class MainWindow(tk.Frame):

    def __init__(self, master):
        super().__init__(master)

        self.producers = {}
        self.producers_extra = {}

        self.pipe = None
        
        self.flow = None
        self.master.title('Telecorpo Viewer')
        self.draw_query_form()

    def draw_query_form(self):
        self.form = ttk.Frame()
        self.form.grid(row=0, sticky='nsew')

        def entry_placeholder(dummy):
            self.entry.delete(0, 'end')
            self.entry.unbind('<FocusIn>')

        self.entry = ttk.Entry(self.form)
        self.entry.insert(0, "server address")
        self.entry.bind('<Return>', self.on_click)
        self.entry.bind('<FocusIn>', entry_placeholder)
        self.entry.grid(row=0, column=0)

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
        
        # disable manual query
        self.entry.configure(state='disabled')
        self.button.configure(state='disabled')

        self.update_sources(server_address)

    def update_sources(self, server_address):

        def add_callback():
            self.master.after(1000, self.update_sources, server_address)

        new_producers = query_producers(server_address)
        if self.producers == new_producers:
            add_callback()
            return
        
        self.producers = new_producers
        self.producers_extra = {}

        if self.flow:
            self.flow.destroy()

        self.flow = tk.Text(self.master, relief='flat')
        self.flow.grid(row=1, sticky='nsew')
        self.flow.configure(state='disabled')
        
        for producer in sorted(self.producers):
            self.producers_extra[producer] = {}
            for source in sorted(self.producers[producer]):
                frame = ttk.Frame(self.master, width=40, height=30)
                frame.bind('<Button-1>', lambda e: self.pipe.select(producer, source))
                self.flow.window_create(tk.INSERT, window=frame)
                # self.flow.insert("end", "   ")            
                self.producers_extra[producer][source] = {'xid': frame.winfo_id()}

        if self.pipe:
            self.pipe.stop()

        self.pipe = Pipeline(self.producers, self.producers_extra)
        self.pipe.start()

        add_callback()


def main():
    Gst.init()
    root = tk.Tk()
    win = MainWindow(root)
    root.mainloop()


if __name__ == '__main__':
    # main()
    Gst.init()
    producers =   {'127.0.0.1': ['smpte', 'video0']}
    extra = {
        '127.0.0.1': {
            'smpte': {'xid': 123},
            'video0': {'xid': 123}}
    }
    pipe = Pipeline(producers, extra)
    pipe.start()
    time.sleep(2)
    Gst.debug_bin_to_dot_file(pipe.pipe, Gst.DebugGraphDetails.CAPS_DETAILS, "pipe")
    while True:
        pass
