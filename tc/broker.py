
import collections
from tc.exceptions import NotFound, DuplicatedName, ExitException
from twisted.internet import reactor
from twisted.spread import pb
from twisted.python import log


class RemoteType(object):
    CAMERA = 1
    MANAGER = 2
    SCREEN = 3


class _ClientData(object):
    def __init__(self, kind, name, port=None):
        if '@' not in name or name[0] == '@' or name[-1] == '@' or ' ' in name:
            raise ValueError("'%s' is an ivalid name" % name)
        self.kind = kind
        self.name = name
        self.port = port
        self.addr = None

    @property
    def location(self):
        return self.name.partition('@')[2]


class CopyableData(_ClientData, pb.Copyable): pass
class DataCopy(_ClientData, pb.RemoteCopy): pass
pb.setUnjellyableForClass(CopyableData, DataCopy)


class Reference(pb.Referenceable):
    
    def __init__(self, pipe, pbroot):
        self.pipe = pipe
        self.pbroot = pbroot
    
    def connect(self, data):
        df = self.pbroot.callRemote('connect', self, data)
        def onDuplicatedName(err):
            err.trap(DuplicatedName)
            self.pbroot.broker.transport.loseConnection()
            msg = err.getErrorMessage()
            log.msg(msg)
            reactor.stop()
        df.addErrback(onDuplicatedName)
        return df

    def __getattr__(self, name):
        if name.startswith('remote_'):
            name = name[7:]
            if hasattr(self.pipe, name):
                meth = getattr(self.pipe, name)
                if isinstance(meth, collections.Callable):
                    return meth
        raise AttributeError

    def callRemote(self, name, *args, **kwargs):
        return self.pbroot.callRemote(name, *args, **kwargs)


class Broker(pb.Root):
    
    def __init__(self):
        self.remotes = {}
    
    def onDisconnect(self, ref, data):
        if data.kind is RemoteType.SCREEN:
            if data.camera:
                camRef, camData = self.remotes[data.camera]
                camRef.callRemote('removeClient', data.addr, data.port)
        elif data.kind is RemoteType.CAMERA:
            for scrRef, scrData in map(self.remotes.get, data.screens):
                scrData.camera = None
        del self.remotes[data.name]

    def remote_connect(self, ref, data):
        if data.name in self.remotes:
            msg = "Someone is already connected with name '%s'" % data.name
            raise DuplicatedName(msg)
         
        if data.kind is RemoteType.SCREEN:
            data.addr = ref.broker.transport.getPeer().host
            data.camera = None

        elif data.kind is RemoteType.CAMERA:
            data.screens = []

        self.remotes[data.name] = ref, data

        def onDisconnect(ref_):
            self.onDisconnect(ref, data)
        ref.notifyOnDisconnect(onDisconnect)

    def remote_changeLatency(self, scrName, delta):
        try:
            scrRef, scrData = self.remotes[scrName]
            scrRef.callRemote('changeLatency', float(delta))
        except KeyError:
            raise NotFound

    def remote_route(self, camName, scrName):
        try:
            camRef, camData = self.remotes[camName]
            scrRef, scrData = self.remotes[scrName]
        except KeyError:
            raise NotFound

        if scrData.camera == camName:
            return
        
        if scrData.camera:
            oldCamRef, oldCamData = self.remotes[scrData.camera]
            oldCamRef.callRemote('removeClient', scrData.addr, scrData.port)
        
        camData.screens.append(scrName)
        scrData.camera = camName
        camRef.callRemote('addClient', scrData.addr, scrData.port)

