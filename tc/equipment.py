from twisted.spread import pb
from zope import interface


__ALL__ = ['IEquipment', 'ReferenceableEquipment']


class IEquipment(interface.Interface):
    name = interface.Attribute("""Name of equipment.""")
    kind = interface.Attribute("""Kind of equipment.""")

    def start(): pass
    def stop(): pass


class ReferenceableEquipment(pb.Referenceable):
    interface.implements(IEquipment)

    def __init__(self, thing, server):
        if not IEquipment.providedBy(thing):
            raise ValueError("thing or connection not provides IEquipment")
        self.name = thing.name
        self.kind = thing.kind

        self.thing = thing
        self.server = server
    
    def connect(self):
        self.server.callRemote("register", self.kind, self.name, self)

    def remote_purge(self):
        """Connection closed by server."""
        from twisted.internet import reactor
        self.thing.stop()
        reactor.stop()

    def start(self):
        self.connect()
        self.thing.start()

    def stop(self):
        self.server.callRemote("unregister", self.name)
        self.remote_purge()
