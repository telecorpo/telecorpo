
from mock import Mock
from twisted.test import proto_helpers

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


class TestReferenceableCameraEquipment(ProtocolTestCase):
    def buildClient(self, pbroot):
        source = 'videotestsrc ! video/x-raw,format=I420,framerate=30/1'
        camera = CameraEquipment(tk.Tk(), source, 'foo@ssa')
        camera.addClient = Mock()
        camera.delClient = Mock()
        return ReferenceableCameraEquipment(camera, pbroot)

    def test_registration(self):
        self.assertTrue(self.client.name in self.server.cameras)

    def test_addClient(self):
        self.server.cameras['foo@ssa'].ref.callRemote('addClient', '127.0.0.1', 9999)
        self.pump.pump()
        self.assertTrue(self.client.thing.addClient.called)

    def test_delClient(self):
        self.server.cameras['foo@ssa'].ref.callRemote('delClient', '127.0.0.1', 9999)
        self.pump.pump()
        self.assertTrue(self.client.thing.delClient.called)


