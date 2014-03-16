
from twisted.internet import protocol, reactor
from twisted.protocols import basic
from zope import interface

from tc.video import Pipeline, StreamingWindow, has_firewire, has_v4l2
from tc.equipment import IEquipment, ReferenceableEquipment


__ALL__ = ['CameraWindow', 'CameraProtocol', 'CameraProtocolFactory']


class CameraEquipment(StreamingWindow):
    interface.implements(IEquipment)

    kind = 'CAMERA'
    port = None
    _description = """
        %s ! videoconvert ! videorate ! videoscale ! tee name=t
            t. ! queue ! x264enc tune=zerolatency ! rtph264pay
                ! multiudpsink name=hdsink
            t. ! queue ! autovideosink
    """

    def __init__(self, tkroot, name):
        if has_firewire():
            source = 'dv1394src ! dvdemux ! dvdec'
        elif has_v4l2():
            source = 'v4l2src'
        else:
            source = 'videotestsrc pattern=ball'
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

