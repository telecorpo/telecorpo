
from mock import MagicMock, Mock
from twisted.internet import reactor, defer
from twisted.spread import pb
from twisted.test import proto_helpers
from zope.interface import implements 
from tc.server import Server
from tc.exceptions import DuplicatedName, NotFound
from tc.equipment import IEquipment, ReferenceableEquipment
from tc.tests import TestCase, IOPump, connect, ProtocolTestCase

class DummyEquipment:
    implements(IEquipment)
    def __init__(self, name, port=None):
        self.name = name
        self.port = port
    def start(self):
        pass
    def stop(self):
        pass


class DummyCamera(DummyEquipment):
    kind = "CAMERA"
    def addClient(self, addr, port):
        pass
    def delClient(self, addr, port):
        pass


class DummyScreen(DummyEquipment):
    kind = "SCREEN"
    def changeLatency(self, latency):
        pass


class TestServer(ProtocolTestCase):
    
    def test_cameraRegistration(self):
        cam = DummyCamera("c@a")
        d = self.connect(cam)
        def check(*args):
            self.assertTrue(cam.name in self.spbroot.cameras)
        d.addCallback(check)

    def test_screenRegistration(self):
        scr = DummyScreen("s@a", 1337)
        d = self.connect(scr)
        def check(*args):
            self.assertTrue(scr.name in self.spbroot.screens)
            self.assertEqual(scr.port, self.spbroot.screens[scr.name].port)
        d.addCallback(check)

    def test_duplicatedNameRegistration(self):
        cam = DummyCamera("dup@a")
        scr = DummyScreen("dup@a")
        scr.stop = Mock()
        
        def check1(none):
            self.assertTrue(cam.name in self.spbroot.cameras)
            d2 = self.connect(scr)
            d2.addCallback(check2)

        def check2(none):
            self.assertTrue(scr.name not in self.spbroot.screens)
            self.pump()
            self.assertTrue(scr.stop.called)

        d1 = self.connect(cam)
        d1.addCallback(check1)

    def test_simpleRoute(self):
        cam = DummyCamera("c@a")
        scr = DummyScreen("s@a", 1337)

        cam.addClient = Mock()

        def step1(none):
            self.connect(scr).addCallback(step2)

        def step2(none):
            d = self.refs[cam].pbroot.callRemote("route", "c@a", "s@a")
            self.pump()
            self.pump()
            d.addCallback(step3)

        def step3(none):
            self.assertTrue(("c@a", "s@a") in self.spbroot.routes)
            # XXX addres hardcoded in proto_helpers.StringTransport
            cam.addClient.assert_called_with('192.168.1.1', 1337)

        self.connect(cam).addCallback(step1)

    def test_complexRoute(self):
        cam1 = DummyCamera("c1@a")
        cam1.delClient = Mock()
        cam2 = DummyCamera("c2@a")
        scr = DummyScreen("s@a", 1337)
        
        def step1(none):
            d = self.refs[cam1].pbroot.callRemote("route", "c1@a", "s@a")
            self.pump()
            self.pump()
            d.addCallback(step2)
            return d

        def step2(none):
            d = self.refs[cam1].pbroot.callRemote("route", "c2@a", "s@a")
            self.pump()
            self.pump()
            d.addCallback(check)
            return d

        def check(none):
            self.assertEqual([("c2@a", "s@a")], self.spbroot.routes)
            # XXX address hardcoded in proto_helper.StrignTransport
            cam1.delClient.assert_called_with('192.168.1.1', 1337)

        d = defer.DeferredList([self.connect(cam1), self.connect(cam2),
                                self.connect(scr)])
        d.addCallback(step1)

    def test_erroneousRoute(self):
        cam = DummyCamera("c@a")

        def step1(none):
            d = self.refs[cam].pbroot.callRemote("route", "c@a", "bad_name")
            self.pump()
            self.pump()
            self.assertFailure(d, NotFound)

        self.connect(cam).addCallback(step1)

    def test_changeLatency(self):
        scr = DummyScreen("s@a", 1337)
        scr.changeLatency = Mock()

        def step1(none):
            d = self.refs[scr].pbroot.callRemote("changeLatency", "s@a", -20)
            self.pump()
            self.pump()
            d.addCallback(check) 
    
        def check(none):
            scr.changeLatency.assert_called_with(-20)

        self.connect(scr).addCallback(step1)
