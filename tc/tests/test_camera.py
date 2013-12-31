
from tc.common import tk
from tc.camera import *
from tc.tests import TestCase


class TestCameraWindow(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.root = tk.Tk()
        source = 'videotestsrc ! video/x-raw,format=I420,framerate=30/1'
        self.cam = CameraWindow(self.root, source, 'foo')

    def test_title(self):
        self.assertEqual(self.cam.title, 'foo - tc-camera')

    def test_hdsink(self):
        # self.assertEqual(self.cam.pipe.hdsink.sync, True)
        self.assertEqual(self.cam.pipe.hdsink.send_duplicates, False)

