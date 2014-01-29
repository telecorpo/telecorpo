
import Tkinter as tk


# class CommandDispatcher(object):

class Colors:
    SELECTED = '#a11'
    BLINK = '#aa1'
    IDLE = '#1aa'

class VideoWidget(tk.Frame):
    def __init__(self, tkroot, dragndrop, title):
        tk.Frame.__init__(self, tkroot)
        self.dragndrop = dragndrop
        self.title = title
        self.label = tk.Label(tkroot, text=title, bg=Colors.IDLE)
        self.label.bind('<Button-1>', self.onClicked)
        self.label.pack(fill=tk.BOTH, expand=1)
        # self.label.pack()

        self.video = tk.Frame(tkroot, bg='#000000', width=200, height=150)
        self.video.bind('<Button-1>', self.onClicked)
        self.video.pack()

    def onClicked(self, event):
        pass
    
    def getWindowHandle(self):
        return self.video.winfo_id()


class CameraWidget(VideoWidget):
    
    def onClicked(self, event):
        def undo():
            self.dragndrop['camera'] = None
            self.label.config(bg=Colors.IDLE)

        if self.dragndrop['camera'] == self.title:
            undo()
        else:
            self.dragndrop['unselect']()
            self.label.config(bg=Colors.SELECTED)
            self.dragndrop['camera'] = self.title
            self.dragndrop['unselect'] = undo


class ScreenWidget(VideoWidget):
    def onClicked(self, event):
        if not self.dragndrop['camera']:
            return
        self.label.configure(bg=Colors.BLINK)
        print '%s -> %s' % (self.dragndrop['camera'], self.title)
        self.after(500, lambda: self.label.configure(bg=Colors.IDLE))


class ManagerWindow(object):

    def __init__(self, tkroot):
        self.cameras = []
        self.screens = []
        self.tkroot = tkroot
        self.tkroot.columnconfigure(0, weight=1)
        self.tkroot.columnconfigure(1, weight=1)

        self.selection = {'camera': None, 'unselect': lambda: None}

        label = tk.Label(tkroot, text='Cameras')
        label.grid(row=0, column=0)
        self.camerasContainer = tk.Text(self.tkroot)
        self.camerasContainer.grid(row=1, column=0, sticky='n')

        label = tk.Label(tkroot, text='Screens')
        label.grid(row=0, column=1)
        self.screensContainer = tk.Text(self.tkroot)
        self.screensContainer.grid(row=1, column=1, sticky='n')

    def addCamera(self, camera):
        widget = CameraWidget(self.camerasContainer, self.selection, camera.name)
        self.camerasContainer.window_create(tk.INSERT, window=widget)

        self.cameras.append(camera)
        camera.widget = widget
        return widget.getWindowHandle()

    def addScreen(self, screen):
        widget = ScreenWidget(self.screensContainer, self.selection, screen.name)
        self.screensContainer.window_create(tk.INSERT, window=widget)

        self.screens.append(screen)
        screen.widget = widget
        return widget.getWindowHandle()


if __name__ == '__main__':
    r = tk.Tk()
    mw = ManagerWindow(r)
    class C:
        def __init__(self, name):
            self.name = name
    mw.addCamera(C('a'))
    mw.addCamera(C('b'))
    mw.addCamera(C('c'))

    mw.addScreen(C('x'))
    mw.addScreen(C('z'))
    # mw.addScreen(C('z'))
    r.mainloop()


