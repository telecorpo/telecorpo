
import Tkinter as tk

from time import sleep

from gi.repository import GObject, Gst, Gdk, GLib, GstVideo

from tc.exceptions import MultimediaException
from tc.multimedia.pipelines import *

from twisted.trial.unittest import TestCase


class PipelineTestCase(TestCase):

    def test_play(self):
        gpipe = Gst.parse_launch("videotestsrc ! fakesink")
        pipe = BasePipeline(gpipe)

        pipe.play()
        self.assertTrue(pipe.isPlaying)
        self.assertTrue(gpipe.get_state(0)[0], Gst.StateChangeReturn.SUCCESS)

        pipe.stop()
        self.assertFalse(pipe.isPlaying)
        self.assertTrue(gpipe.get_state(0)[0], Gst.StateChangeReturn.SUCCESS)

    def test_xid(self):
        gpipe = Gst.parse_launch("videotestsrc ! autovideosink")
        pipe = BasePipeline(gpipe)
        pipe.setWindowHandle(7)
        pipe.play()
        sleep(0.1)
        self.assertEqual(pipe._xid, 7)
        pipe.stop()


class CameraPipelineTestCase(TestCase):

    def test_addClient(self):
        pipe = CameraPipeline('ball')
        pipe.play()
        pipe.addClient('127.0.0.1', 1337)
        self.assertEqual(pipe.streamer.udpsink.get_property('clients'),
                '127.0.0.1:1337')
        pipe.removeClient('127.0.0.1', 1337)
        self.assertEqual(pipe.streamer.udpsink.get_property('clients'), '')
        pipe.stop()


class ScreenPipelineTestCase(TestCase):
    
    def test_changeLatency(self):
        pipe = ScreenPipeline(1337)

        def getLatency():
            return pipe.receiver.jitter.get_property('latency')

        latency = getLatency()

        pipe.changeLatency(+10)
        self.assertEqual(getLatency(), latency+10)

        pipe.changeLatency(-100000)
        self.assertEqual(getLatency(), 0)

