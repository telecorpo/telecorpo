
from mock import Mock
from twisted.test import proto_helpers
from twisted.trial import unittest

from tc.common import tk
from tc.camera import *
from tc.tests import TestCase, ProtocolTestCase


class TestCameraEquipment(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.root = tk.Tk()
        source = 'videotestsrc ! video/x-raw,format=I420,framerate=30/1'
        self.cam = CameraEquipment(self.root, source, 'foo')

    def test_title(self):
        self.assertEqual(self.cam.title, 'foo - tc-camera')

    def test_hdsink(self):
        self.assertEqual(self.cam.pipe.hdsink.sync, True)
        self.assertEqual(self.cam.pipe.hdsink.send_duplicates, False)

    def test_addClient(self):
        raise unittest.SkipTest("Hard to test.")

    def test_delClient(self):
        raise unittest.SkipTest("Hard to test.")


