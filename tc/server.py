
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
    
    def deleteClient(self, kind, name):
        if kind == 'CAMERA':
            for route in list(self.routes):
                if route[0] == name:
                    self.routes.remove(route)
                    # del self.cameras[name]
        elif kind == 'SCREEN':
            for route in list(self.routes):
                if route[1] == name:
                    cam = self.cameras[route[0]]
                    scr = self.screens[route[1]]
                    cam.callRemote("delClient", scr.addr, scr.port)
                    self.routes.remove(route)
                    # del self.screens[name]

    def remote_register(self, obj, kind, name, port):
        if name in chain(self.cameras, self.managers, self.screens):
            raise DuplicatedName
        if kind == 'CAMERA': refs = self.cameras
        elif kind == 'MANAGER': refs = self.managers
        elif kind == 'SCREEN': refs = self.screens
        else:
            raise ValueError("kind must be CAMERA, MANAGER or SCREEN")

        def onDisconnect(remoteRef):
            del refs[name]
            self.deleteClient(kind, name)
        obj.notifyOnDisconnect(onDisconnect)
        addr = obj.broker.transport.getPeer().host
        refs[name] = ClientRef(name, kind, obj, addr, port)

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
