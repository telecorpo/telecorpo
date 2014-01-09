# from mock import Mock
# from twisted.internet import reactor
# from twisted.trial import unittest
# from twisted.spread import pb
# from twisted.test import proto_helpers
#
# from tc.server import Server
#
# class TestCase(unittest.TestCase):
#     def setUp(self):
#         reactor.stop = Mock()
#
#
# class IOPump:
#
#     def __init__(self, client, server, clientIO, serverIO):
#         self.client = client
#         self.server = server
#         self.clientIO = clientIO
#         self.serverIO = serverIO
#
#     def pump(self):
#         cData = self.clientIO.value()
#         sData = self.serverIO.value()
#         self.clientIO.clear()
#         self.serverIO.clear()
#         self.server.dataReceived(cData)
#         self.client.dataReceived(sData)
#
#     def __call__(self):
#         self.pump()
#
#
# def connect(root):
#     serverFactory = pb.PBServerFactory(root)
#     serverBroker = serverFactory.buildProtocol(())
#
#     clientFactory = pb.PBClientFactory()
#     clientBroker = clientFactory.buildProtocol(())
#
#     clientTransport = proto_helpers.StringTransport()
#     serverTransport = proto_helpers.StringTransport()
#     clientBroker.makeConnection(clientTransport)
#     serverBroker.makeConnection(serverTransport)
#
#     pump = IOPump(clientBroker, serverBroker, clientTransport, serverTransport)
#     # initial communication
#     pump.pump()
#
#     return clientFactory, serverFactory, pump
#
#
# class ProtocolTestCase(TestCase):
#     def setUp(self):
#         self.spbroot = Server()
#         self.pumps = []
#         self.refs = {}
#         reactor.stop = Mock()
#     
#     def connect(self, equip):
#         serverFactory = pb.PBServerFactory(self.spbroot)
#         serverBroker = serverFactory.buildProtocol(())
#
#         clientFactory = pb.PBClientFactory()
#         clientBroker = clientFactory.buildProtocol(())
#
#         clientTransport = proto_helpers.StringTransport()
#         serverTransport = proto_helpers.StringTransport()
#
#         clientBroker.makeConnection(clientTransport)
#         serverBroker.makeConnection(serverTransport)
#
#         pump = IOPump(clientBroker, serverBroker, clientTransport,
#                       serverTransport)
#         pump()
#         self.pumps.append(pump)
#         defer = self.registrate(clientFactory, equip)
#         return defer
#
#     def registrate(self, clientFactory, equip):
#         defer = clientFactory.getRootObject()
#         def gotRoot(pbroot):
#             ref = ReferenceableEquipment(equip, pbroot)
#             ref.start()
#             self.refs[ref.name] = ref
#             self.refs[ref.thing] = ref
#             self.pump()
#         defer.addCallback(gotRoot)
#         return defer
#
#     def pump(self):
#         for pump in self.pumps:
#             pump.pump()
#
