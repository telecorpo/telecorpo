
from itertools import chain
from twisted.spread import pb



class NotFound(pb.Error):
    pass


class DuplicatedName(pb.Error):
    pass


class ClientRef(object):
    def __init__(self, name, kind, ref):
        self.name = name
        self.kind = kind
        self.ref = ref

    @property
    def local(self):
        return self._name.split('@')[1]


class Server(pb.Root):
    def __init__(self):
        self.cameras = {}
        self.managers = {}
        self.screens = {}
    
    def getCamera(self, name):
        try:
            return self.cameras[name]
        except KeyError:
            raise NotFound

    def remote_register(self, kind, name, obj):
        if name in chain(self.cameras, self.managers, self.screens):
            raise DuplicatedName
        if kind == 'CAMERA': refs = self.cameras
        elif kind == 'MANAGER': refs = self.managers
        elif kind == 'SCREEN': refs = self.screen
        else:
            raise ValueError("kind must be CAMERA, MANAGER or SCREEN")
        refs[name] = ClientRef(name, kind, obj)

    def remote_unregister(self, name):
        for ref in chain(self.cameras.values(), self.managers.values(),
                           self.screens.values()):
            if ref.name == name:
                if ref.kind == 'CAMERA': refs = self.cameras
                if ref.kind == 'MANAGER': refs = self.managers
                if ref.kind == 'SCREEN': refs = self.screen
                del refs[ref.name]
                ref.ref.callRemote("purge")
                break
        else:
            raise NotFound

