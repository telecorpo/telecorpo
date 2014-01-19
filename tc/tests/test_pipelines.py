
import Tkinter as tk

from time import sleep

from gi.repository import GObject, Gst, Gdk, GLib, GstVideo

from tc import MultimediaException
from twisted.trial.unittest import TestCase

from tc.pipelines import Pipeline, cameraFactory, screenFactory

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

        self.assertEqual(pipe.a.getProperty('dump'), False)
        pipe.a.setProperty('dump', True)
        self.assertEqual(pipe.a.getProperty('dump'), True)


class FactoriesTestCase(TestCase):

    def test_camera(self):
        cam = cameraFactory("smpte", (300, 400), 30)
        cam.play()

        cam.multiudpsink.emit('add', '127.0.0.1', 1337)
        self.assertEquals(cam.multiudpsink.getProperty('clients'),
                          '127.0.0.1:1337')

        cam.multiudpsink.emit('remove', '127.0.0.1', 1337)
        self.assertEquals(cam.multiudpsink.getProperty('clients'), '')

        cam.stop()

    def test_screen(self):
        scr = screenFactory(1337)
        scr.play()
        scr.stop()

