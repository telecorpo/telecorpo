
from StringIO import StringIO
from mock import MagicMock
from twisted.internet import protocol, reactor
from twisted.protocols import policies
from zope.interface import implements

from tc.broker import Server
from tc.equipment import IEquipment, ReferenceableEquipment
from tc.tests import TestCase, IOPump, connect


class DummyEquipment:
    implements(IEquipment)
    def __init__(self, name, kind):
        self.name = name
        self.kind = kind
    def start(s): pass
    def stop(s): pass


class ReferenceableEquipmentRegistrationTestCase(TestCase):
    def test_registration(self):
        server_orig = Server()
        client, server, pump = connect(server_orig)
        d = client.getRootObject()
        def gotRoot(root):
            dummy = DummyEquipment('foo@a', 'CAMERA')
            dummy.start = MagicMock()
            dummy.stop = MagicMock()
            r = ReferenceableEquipment(dummy, root)
            r.start()
            pump.pump()
            self.assertTrue('foo@a' in server_orig.cameras)
            r.stop()
            pump.pump()
            self.assertFalse('foo@a' in server_orig.cameras)
            self.assertTrue(reactor.stop.called)
            self.assertTrue(dummy.start.called)
            self.assertTrue(dummy.stop.called)
        d.addCallback(gotRoot)
        return d
        
