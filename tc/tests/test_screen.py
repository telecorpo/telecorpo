

from mock import Mock
from tc.common import tk
from tc.screen import *
from tc.tests import TestCase, ProtocolTestCase


class TestScreenEquipment(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.root = tk.Tk()
        self.scr = ScreenEquipment(self.root, 1337, 'foo', latency=200)

    def tearDown(self):
        self.scr.stop()

    def test_title(self):
        self.assertEquals(self.scr.title, 'foo - tc-screen')

    def test_changeLatencyWithMouseWheel(self):
        # increase
        self.scr.frame.event_generate('<Button-4>')
        self.root.update()
        self.assertEquals(self.scr.pipe.buffer.latency, 300)
        
        # decrease
        self.scr.frame.event_generate('<Button-5>')
        self.root.update()
        self.assertEquals(self.scr.pipe.buffer.latency, 200)

    def test_changeLatency(self):
        #increase
        self.scr.changeLatency(+40)
        self.root.update()
        self.assertEquals(self.scr.pipe.buffer.latency, 240)

        # decrease
        self.scr.changeLatency(-30)
        self.root.update()
        self.assertEquals(self.scr.pipe.buffer.latency, 210)


class TestReferenceableScreenEquipment(ProtocolTestCase):
    def setUp(self):
        ProtocolTestCase.setUp(self)
        self.pump.pump()
        self.pump.pump()

    def buildClient(self, pbroot):
        self.screen = ScreenEquipment(tk.Tk(), 1337, 'foo@ssa')
        self.screen.changeLatency = Mock()
        return ReferenceableScreenEquipment(self.screen, pbroot)

    def test_changeLatency(self):
        d = self.server.screens['foo@ssa'].ref.callRemote('changeLatency', -3)
        self.pump.pump()
        self.screen.changeLatency.assert_called_with(-3)

    def test_registration(self):
        self.assertEqual(self.server.screens['foo@ssa'].port, 1337)
        
