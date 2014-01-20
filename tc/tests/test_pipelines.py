
import Tkinter as tk

from time import sleep

from gi.repository import GObject, Gst, Gdk, GLib, GstVideo

from tc import MultimediaException
from twisted.trial.unittest import TestCase

from tc.multimedia import Pipeline, CameraPipeline, ScreenPipeline, VideoWindow

class PipelineTestCase(TestCase):

    def test_play(self):
        pipe = Pipeline(Gst.parse_launch("fakesrc ! fakesink"))
        pipe.play()
        self.assertTrue(pipe.isPlaying())
        pipe.stop()

        # pipe = Pipeline(Gst.parse_launch("fakesink ! fakesrc"))
        # self.assertRaises(MultimediaException, pipe.play)

    def test_windowXID(self):
        xid = 7
        pipe = Pipeline(Gst.parse_launch("videotestsrc ! autovideosink"), xid)
        pipe.play()
        sleep(0.1)
        self.assertEqual(pipe.xid, 7)
        pipe.stop()

    def test_getElement(self):
        _ = Gst.parse_launch("fakesrc ! fakesink name=a dump=false")
        pipe = Pipeline(_)

        self.assertEqual(pipe.a.get_property('dump'), False)
        pipe.a.set_property('dump', True)
        self.assertEqual(pipe.a.get_property('dump'), True)


class FactoriesTestCase(TestCase):

    def setUp(self):
        self.root = tk.Tk()
        self.win = VideoWindow(self.root, 'title')
        self.xid = self.win.getWindowHandle()

    def tearDown(self):
        self.root.destroy()

    def test_camera(self):
        cam = CameraPipeline('smpte', 1, (300, 400), self.xid)
        cam.play()

        cam.multiudpsink.emit('add', '127.0.0.1', 1337)
        self.assertEquals(cam.multiudpsink.get_property('clients'),
                          '127.0.0.1:1337')

        cam.multiudpsink.emit('remove', '127.0.0.1', 1337)
        self.assertEquals(cam.multiudpsink.get_property('clients'), '')

        cam.stop()

    def test_screen(self):
        scr = ScreenPipeline(1337, self.xid)
        scr.play()
        scr.stop()

