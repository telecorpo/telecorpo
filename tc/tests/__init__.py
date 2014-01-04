from mock import MagicMock
from twisted.internet import reactor
from twisted.trial import unittest
from twisted.spread import pb
from twisted.test import proto_helpers


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
