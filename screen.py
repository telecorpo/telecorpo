#!/usr/bin/env python

import gobject
import pygst
pygst.require("0.10")
import gst

import sys, os
from Tkinter import *

from player import ScreenPlayer

class ScreenPlayer:
    def __init__(self):
        gobject.threads_init()

        # Build elements
        self.src = gst.element_factory_make("videotestsrc", "src")
        self.cspace = gst.element_factory_make("ffmpegcolorspace", "cspace")
        self.sink = gst.element_factory_make("xvimagesink", "sink")
        
        # Build pipeline
        self.pipeline = gst.Pipeline("pipeline")
        self.pipeline.add_many(self.src, self.cspace, self.sink)
        gst.element_link_many(self.src, self.cspace, self.sink)
        
        # Bus bit and bobs
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.enable_sync_message_emission()

        # Current state
        self.playing = True
        self.pipeline.set_state(gst.STATE_PLAYING)

    def connect(self, evt_name, callback):
        self.bus.connect(evt_name, callback)

    def toggle_play(self):
        self.playing = not self.playing
        if self.playing:
            self.pipeline.set_state(gst.STATE_NULL)
        else:
            self.pipeline.set_state(gst.STATE_PLAYING)

class ScreenWindow(Frame):
    def __init__(self, parent, player):
        Frame.__init__(self, parent)    

        # Parent Object
        self.parent = parent
        self.parent.title("Screen")
        self.parent.resizable(width=TRUE, height=TRUE)

        # Video Box
        self.movie_window = Canvas(self, width=640, height=480, bg="black")
        self.movie_window.pack(side=TOP, expand=YES, fill=BOTH)

        # Player
        self.player = player
        self.player.connect("message", self.on_message)
        self.player.connect("sync-message::element", self.on_sync_message)

        # Fullscreen
        self.parent.bind('<Return>', self.toggle_fullscreen)
        self.fullscreen = False
        
        # Play and pause
        self.parent.bind('<space>', self.toggle_play)
        
    def toggle_play(self, event):
        self.player.toggle_play()

    def toggle_fullscreen(self, event):
        if not self.fullscreen:
            fullscreen_geometry = '{}x{}+0+0'.format(
                self.parent.winfo_screenwidth(),
                self.parent.winfo_screenheight())
            self.previous_geometry = self.parent.winfo_geometry()
            self.parent.geometry(fullscreen_geometry)
            self.fullscreen = True
        else:
            self.parent.geometry(self.previous_geometry)
            self.fullscreen = False

    def on_message(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_EOS:
            self.player.set_state(gst.STATE_NULL)
            self.button.set_label("Start")
        elif t == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            print "Error: %s" % err, debug
            self.player.set_state(gst.STATE_NULL)
            self.button.set_label("Start")

    def on_sync_message(self, bus, message):
        if message.structure is None:
            return
        message_name = message.structure.get_name()
        if message_name == "prepare-xwindow-id":
            # Assign the viewport
            # import ipdb; ipdb.set_trace()
            imagesink = message.src
            imagesink.set_property("force-aspect-ratio", True)
            imagesink.set_xwindow_id(self.movie_window.winfo_id())

def main():
    root = Tk()
    player = ScreenPlayer()
    app = ScreenWindow(root, player)
    app.pack(expand=YES, fill=BOTH)
    root.mainloop()  


if __name__ == '__main__':
     main()
