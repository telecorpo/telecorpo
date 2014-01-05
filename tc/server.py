
from itertools import chain
from twisted.spread import pb

from tc.exceptions import NotFound, DuplicatedName


class ClientRef(object):
    def __init__(self, name, kind, ref, addr, port=None):
        self.name = name
        self.kind = kind
        self.addr = addr
        self.port = port
        self.ref = ref
    
    @property
    def local(self):
        return self._name.split('@')[1]

    def __hash__(self):
        return hash(self.name) + hash(self.port)


class Server(pb.Root):
    def __init__(self):
        self.cameras = {}
        self.managers = {}
        self.screens = {}
        self.routes = []
    
    def getCamera(self, name):
        try:
            return self.cameras[name]
        except KeyError:
            raise NotFound

    def remote_register(self, obj, kind, name, port):
        if name in chain(self.cameras, self.managers, self.screens):
            raise DuplicatedName
        if kind == 'CAMERA': refs = self.cameras
        elif kind == 'MANAGER': refs = self.managers
        elif kind == 'SCREEN': refs = self.screens
        else:
            raise ValueError("kind must be CAMERA, MANAGER or SCREEN")
        addr = obj.broker.transport.getPeer().host
        refs[name] = ClientRef(name, kind, obj, addr, port)

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

    def remote_route(self, cam_name, scr_name):
        try:
            camera = self.cameras[cam_name]
            screen = self.screens[scr_name]
        except KeyError:
            raise NotFound
        
        if (camera.name, screen.name) in self.routes:
            return

        for cam, scr in self.routes:
            if scr == scr_name:
                cam = self.cameras[cam]
                scr = self.screens[scr]
                cam.ref.callRemote("delClient", scr.addr, scr.port)
                self.routes.remove((cam.name, scr.name))

        self.routes.append((camera.name, screen.name))
        camera.ref.callRemote("addClient", screen.addr, screen.port)
    
    def remote_changeLatency(self, scr_name, delta):
        try:
            screen = self.screens[scr_name]
            screen.ref.callRemote("changeLatency", delta)
        except KeyError:
            raise NotFound
