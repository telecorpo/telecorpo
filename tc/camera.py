
from twisted.internet import protocol, reactor
from twisted.protocols import basic
from zope import interface

from tc.common import get_logger
from tc.video import Pipeline, StreamingWindow
from tc.equipment import IEquipment


__ALL__ = ['CameraWindow', 'CameraProtocol', 'CameraProtocolFactory']

LOG = get_logger(__name__)


class CameraWindow(StreamingWindow):
    interface.implements(IEquipment)

    kind = 'CAMERA'
    _description = """
        %s ! tee name=t
            t. ! queue ! x264enc tune=zerolatency ! rtph264pay
                ! multiudpsink name=hdsink
            t. ! queue ! x264enc tune=zerolatency ! rtph264pay
                ! multiudpsink name=ldsink
            t. ! queue ! autovideosink
    """

    def __init__(self, root, source, name):
        pipe = Pipeline(self._description % source)
        title = '%s - tc-camera' % name
        super(CameraWindow, self).__init__(root, pipe, title)
        self.name = name

        # self.pipe.hdsink.sync = True
        self.pipe.hdsink.send_duplicates = False
    
    def add_client(self, addr, port):
        # FIXME untested
        self.pipe.hdsink.emit('add', addr, port)

    def del_client(self, addr, port):
        # FIXME untested
        self.pipe.hdsink.emit('remove', addr, port)

