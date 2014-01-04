from mock import MagicMock
from twisted.internet import reactor
from twisted.trial import unittest
from twisted.spread import pb
from twisted.test import proto_helpers

from tc.server import Server

class TestCase(unittest.TestCase):
    def setUp(self):
        reactor.stop = MagicMock()


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


def connect(root):
    serverFactory = pb.PBServerFactory(root)
    serverBroker = serverFactory.buildProtocol(())

    clientFactory = pb.PBClientFactory()
    clientBroker = clientFactory.buildProtocol(())

    clientTransport = proto_helpers.StringTransport()
    serverTransport = proto_helpers.StringTransport()
    clientBroker.makeConnection(clientTransport)
    serverBroker.makeConnection(serverTransport)

    pump = IOPump(clientBroker, serverBroker, clientTransport, serverTransport)
    # initial communication
    pump.pump()

    return clientFactory, serverFactory, pump


class ProtocolTestCase(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.server = Server()
        self.client = None
        self.clientFactory, self.serverFactory, self.pump = connect(self.server)
        d = self.clientFactory.getRootObject()
        d.addCallback(self.gotRoot)
        return d
    
    def buildClient(self, pbroot):
        raise NotImplementedError

    def gotRoot(self, pbroot):
        self.client = self.buildClient(pbroot)
        d = self.client.start()
        self.pump.pump()
        self.pump.pump()


