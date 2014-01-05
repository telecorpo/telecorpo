import collections

from twisted.spread import pb
from zope import interface

from tc.exceptions import DuplicatedName


__ALL__ = ['IEquipment', 'ReferenceableEquipment']


class IEquipment(interface.Interface):
    name = interface.Attribute("""Name of equipment.""")
    kind = interface.Attribute("""Kind of equipment.""")

    def start(): pass
    def stop(): pass


class ReferenceableEquipment(pb.Referenceable):
    interface.implements(IEquipment)

    def __init__(self, thing, pbroot):
        if not IEquipment.providedBy(thing):
            raise ValueError("thing or connection not provides IEquipment")
        self.name = thing.name
        self.kind = thing.kind

        self.thing = thing
        self.pbroot = pbroot
    
    def connect(self):
        d = self.pbroot.callRemote("register", self.kind, self.name, self)
        def onError(err):
            err.trap(DuplicatedName)
            self.remote_purge()
        d.addErrback(onError)
        return d 
    def remote_getAttr(self, name):
        return getattr(self.thing, name)

    def remote_purge(self):
        """Connection closed by server."""
        from twisted.internet import reactor
        self.thing.stop()
        reactor.stop()

    def start(self):
        self.thing.start()
        d = self.connect()
        return d

    def stop(self):
        self.pbroot.callRemote("unregister", self.name)
        self.remote_purge()

    def __getattr__(self, name):
        if not name.startswith('remote_'):
            raise AttributeError
        method = getattr(self.thing, name[7:])
        if not isinstance(method, collections.Callable):
            raise AttributeError
        return method

