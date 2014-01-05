

from mock import MagicMock, Mock
from twisted.internet import reactor
from zope.interface import implements

from tc.server import Server
from tc.equipment import IEquipment, ReferenceableEquipment
from tc.tests import TestCase, IOPump, connect


class DummyEquipment:
    implements(IEquipment)

    def __init__(self, name, kind, port=1):
        self.name = name
        self.kind = kind
        self.port = port

    def start(self):
        pass

    def stop(self):
        pass


class TestReferenceableEquipment(TestCase):

    def setUp(self):
        TestCase.setUp(self)

        self.dummy = DummyEquipment("a@a", "CAMERA", 1)
        self.dummy.foo = Mock()
        self.dummy.bar = Mock()

        pbroot = None
        self.ref = ReferenceableEquipment(self.dummy, pbroot)

    def test_methodDelegation(self):
        self.ref.remote_foo(1)
        self.dummy.foo.assert_called_once_with(1)

        self.ref.remote_bar()
        self.assertTrue(self.dummy.bar.called)

    def test_properties(self):
        self.assertEqual(self.ref.name, "a@a")
        self.assertEqual(self.ref.kind, "CAMERA")
        self.assertEqual(self.ref.port, 1)

    def test_registration(self):
        server_orig = Server()
        client, server, pump = connect(server_orig)
        d = client.getRootObject()
        def gotRoot(root):
            # create equipment
            dummy = DummyEquipment('foo@a', 'CAMERA')
            dummy.start = MagicMock()
            dummy.stop = MagicMock()
            r = ReferenceableEquipment(dummy, root)
            r.start()
            pump.pump() # remote call "register"

            # it was inserted on server?
            self.assertTrue('foo@a' in server_orig.cameras)

            # create equipment with duplicated name
            r2 = ReferenceableEquipment(DummyEquipment('foo@a', 'SCREEN'), root)
            r2.start()
            pump.pump() # remote call "register"
            pump.pump() # DuplicatedName exception

            # reactor.stop called on duplicated equipment
            self.assertEqual(reactor.stop.call_count, 1)
            
            # stop working equipment
            r.stop()
            pump.pump() # remote call "purge"

            self.assertFalse('foo@a' in server_orig.cameras)
            self.assertEqual(reactor.stop.call_count, 2)
            self.assertTrue(dummy.start.called)
            self.assertTrue(dummy.stop.called)
        d.addCallback(gotRoot)
        return d
        
