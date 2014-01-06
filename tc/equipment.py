import collections

from twisted.spread import pb
from zope import interface

from tc.exceptions import DuplicatedName


__ALL__ = ['IEquipment', 'ReferenceableEquipment']


class IEquipment(interface.Interface):
    name = interface.Attribute("""Name of equipment.""")
    kind = interface.Attribute("""Kind of equipment.""")
    port = interface.Attribute("""Port of equipment.""")

    def start(): pass
    def stop(): pass


class ReferenceableEquipment(pb.Referenceable):
    interface.implements(IEquipment)

    def __init__(self, thing, pbroot):
        if not IEquipment.providedBy(thing):
            raise ValueError("thing or connection not provides IEquipment")
        self.name = thing.name
        self.kind = thing.kind
        self.port = thing.port

        self.thing = thing
        self.pbroot = pbroot
    
    def connect(self):
        d = self.pbroot.callRemote("register", self, self.kind, self.name,
                                   self.port)
        def onError(err):
            err.trap(DuplicatedName)
            self.stop()
        d.addErrback(onError)
        return d 
    
    def start(self):
        self.thing.start()
        d = self.connect()
        return d

    def stop(self):
        from twisted.internet import reactor
        self.thing.stop()

    def __getattr__(self, name):
        if not name.startswith('remote_'):
            raise AttributeError
        method = getattr(self.thing, name[7:])
        if not isinstance(method, collections.Callable):
            raise AttributeError
        return method

