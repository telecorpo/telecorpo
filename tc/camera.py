
from twisted.internet import protocol, reactor
from twisted.protocols import basic
from zope import interface

from tc.video import Pipeline, StreamingWindow
from tc.equipment import IEquipment, ReferenceableEquipment


__ALL__ = ['CameraWindow', 'CameraProtocol', 'CameraProtocolFactory']


class CameraEquipment(StreamingWindow):
    interface.implements(IEquipment)

    kind = 'CAMERA'
    # port = None
    _description = """
        %s ! tee name=t
            t. ! queue ! x264enc tune=zerolatency ! rtph264pay
                ! multiudpsink name=hdsink
            t. ! queue ! x264enc tune=zerolatency ! rtph264pay
                ! multiudpsink name=ldsink
            t. ! queue ! autovideosink
    """

    def __init__(self, tkroot, source, name):
        pipe = Pipeline(self._description % source)
        title = '%s - tc-camera' % name
        self.name = name
        StreamingWindow.__init__(self, tkroot, pipe, title)

        # self.pipe.hdsink.sync = True
        self.pipe.hdsink.send_duplicates = False
    
    def addClient(self, addr, port):
        # FIXME untested
        self.pipe.hdsink.emit('add', addr, port)

    def delClient(self, addr, port):
        # FIXME untested
        # FIXME delClient "works" even if client wasn't previously added 
        self.pipe.hdsink.emit('remove', addr, port)

