
from tc.common import tk
from tc.camera import *

from twisted.trial import unittest

class TestCameraWindow(unittest.TestCase):

    def setUp(self):
        self.root = tkinter.Tk()
        source = 'videotestsrc ! raw/x-video,width=10,height=10,framerate=25/1'
        self.cam = CameraWindow(self.root, source, 'foo')

    def test_title(self):
        self.assertEqual(self.cam.title, 'foo - tc-camera')

    def test_hdsink(self):
        # self.assertEqual(self.cam.pipe.hdsink.sync, True)
        self.assertEqual(self.cam.pipe.hdsink.send_duplicates, False)

