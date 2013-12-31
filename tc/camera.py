
from tc.common import get_logger
from tc.video import Pipeline, StreamingWindow

__ALL__ = ['CameraWindow']

LOG = get_logger(__name__)


class CameraWindow(StreamingWindow):

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

        # self.pipe.hdsink.sync = True
        self.pipe.hdsink.send_duplicates = False
    
    def add_hd_client(self, addr, port):
        # FIXME untested
        self.pipe.hdsink.emit('add', addr, port)

    def del_hd_client(self, addr, port):
        # FIXME untested
        self.pipe.hdsink.emit('remove', addr, port)


if __name__ == '__main__':
    import tkinter as tk
    from twisted.internet import tksupport, reactor
    root = tk.Tk()
    tksupport.install(root)
    cam = CameraWindow(root, 'videotestsrc ! video/x-raw', 'cam1')
    reactor.run()
