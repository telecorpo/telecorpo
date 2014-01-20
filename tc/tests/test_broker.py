import Tkinter as tk

from gi.repository import Gst
from mock import Mock
from twisted.internet import reactor, defer
from twisted.trial import unittest
from twisted.test import proto_helpers

from tc.broker import *
from tc.multimedia import *


class IOPump:

    def __init__(self, client, server, clientIO, serverIO):
        self.client = client
        self.server = server
        self.clientIO = clientIO
        self.serverIO = serverIO

    def pump(self):
        cData = self.clientIO.value()
        sData = self.serverIO.value()
        self.clientIO.clear()
        self.serverIO.clear()
        self.server.dataReceived(cData)
        self.client.dataReceived(sData)

    def __call__(self):
        self.pump()


class ConnectedTestCase(unittest.TestCase):
    def setUp(self):
        self.broker = Broker()
        self.pumps = []
        self.remotes = {}
        self.tkroot = tk.Tk()
        self.window = VideoWindow(self.tkroot, 'xxx')
        self.xid = self.window.getWindowHandle()
        reactor.stop = Mock()

    def connect(self, copyableData, pipeline):
        serverFactory = pb.PBServerFactory(self.broker)
        serverBroker = serverFactory.buildProtocol(())

        clientFactory = pb.PBClientFactory()
        clientBroker = clientFactory.buildProtocol(())

        clientTransport = proto_helpers.StringTransport()
        serverTransport = proto_helpers.StringTransport()

        clientBroker.makeConnection(clientTransport)
        serverBroker.makeConnection(serverTransport)

        pump = IOPump(clientBroker, serverBroker, clientTransport,
                      serverTransport)
        pump()
        self.pumps.append(pump)

        df = clientFactory.getRootObject()
        def gotRoot(pbroot):
            reference = Reference(pipeline, pbroot)
            # TODO this deferred must be useful
            reference.connect(copyableData)
            # pipeline.play()

            self.remotes[copyableData.name] = reference, copyableData
            self.remotes[copyableData] = reference, copyableData

            self.pump()
            self.pump()
        df.addCallback(gotRoot)
        return df

    def tearDown(self):
        for ref, data in self.remotes.values():
            ref.pipe.stop()
        self.tkroot.destroy()

    def pump(self):
        for pump in self.pumps:
            pump.pump()


class BrokerTestCase(ConnectedTestCase):

    def test_cameraConnection(self):
        pipe = CameraPipeline('ball', self.xid, (300, 400), 25)
        data = CopyableData(RemoteType.CAMERA, 'a@b')

        df = self.connect(data, pipe)
        def check1(_):
            self.assertTrue('a@b' in self.broker.remotes)
        df.addCallback(check1)
        return df

    def test_screenConnection(self):
        pipe = ScreenPipeline(1337, self.xid)
        data = CopyableData(RemoteType.SCREEN, 'a@b', 1337)

        df = self.connect(data, pipe)
        def check1(_):
            self.assertTrue('a@b' in self.broker.remotes)
            self.assertEqual(self.broker.remotes['a@b'][1].addr, '192.168.1.1')
            self.assertEqual(self.broker.remotes['a@b'][1].port, 1337)
        df.addCallback(check1)
        return df 

    def test_duplicateName(self):
        data1 = CopyableData(RemoteType.CAMERA, 'a@b')
        data2 = CopyableData(RemoteType.SCREEN, 'a@b', 1)

        pipe1 = CameraPipeline('ball', self.xid, (300, 400), 25)
        pipe2 = ScreenPipeline(1, self.xid)

        d1 = self.connect(data1, pipe1)
        d2 = self.connect(data2, pipe2)
        dl = defer.DeferredList([d1, d2])
        def afterConnections(r):
            self.assertEqual(len(self.broker.remotes), 1)
            self.assertEqual(reactor.stop.call_count, 1)
        dl.addCallback(afterConnections)
        return dl

    def test_changeLatency(self):
        pipe = ScreenPipeline(1337, self.xid)
        data = CopyableData(RemoteType.SCREEN, 'a@b', 1337)
        
        oldLatency = pipe.buffer.get_property('latency')
        delta = +10

        d1 = self.connect(data, pipe)
        def step1(none):
            d2 = self.remotes['a@b'][0].callRemote('changeLatency', 'a@b', delta)
            d2.addCallback(checkLatency)
            self.pump()
            self.pump()
            return d2

        def checkLatency(none):
            newLatency = pipe.buffer.get_property('latency')
            self.assertEqual(newLatency, oldLatency + 10)

        d1.addCallback(step1)
        return d1

    def test_simpleRoute(self):
        camData = CopyableData(RemoteType.CAMERA, 'cam@br')
        scrData = CopyableData(RemoteType.SCREEN, 'scr@br', 1337)

        camPipe = CameraPipeline('ball', self.xid, (300, 400), 25)
        scrPipe = ScreenPipeline(1337, self.xid)
        
        camPipe.play()
        scrPipe.play()
        
        dl = [self.connect(camData, camPipe), self.connect(scrData, scrPipe)]
        dl = defer.DeferredList(dl)

        def afterConnections(ignore): 
            localRef = self.remotes['cam@br'][0]

            d = localRef.callRemote('route', 'cam@br', 'scr@br')
            d.addCallback(afterRouting)
            self.pump()
            self.pump()
            return d

        def afterRouting(ignore):
            camRef, camData = self.broker.remotes['cam@br']
            self.assertIn('scr@br', camData.screens)

            # # drop cam@br
            # self.remotes['cam@br'][0].pbroot.broker.transport.loseConnection()
            # self.pump()

        dl.addCallback(afterConnections)
        return dl

