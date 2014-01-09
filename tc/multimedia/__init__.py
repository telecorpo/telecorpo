
import Tkinter as tk

class VideoWindow(object):
    # FIXME untested
    def __init__(self, tkroot, title):
        self.tkroot = tkroot
        self.tkroot.wm_title(title)
        self.isFullscreen = False

        self.frame = tk.Frame(tkroot, bg='#000000')
        self.frame.pack(expand=tk.YES, fill=tk.BOTH)

        # Bind window events.
        tkroot.protocol("WM_DELETE_WINDOW", self.quit)
        self.frame.bind('<Double-Button-1>', self.toggleFullscreen)

        # Window handler
        self.xid = self.frame.winfo_id()

    def toggleFullscreen(self, event):
        self.tkroot.attributes('-fullscreen', self.isFullscreen)
        self.isFullscreen = not self.isFullscreen

    def getWindowHandle(self):
        return self.xid

    def quit(self):
        from twisted.internet import reactor
        if reactor.running:
            reactor.stop()
