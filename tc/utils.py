
import multiprocessing
# import tkinter as tk
import zmq

class Window(multiprocessing.Process):

    def __init__(self, title, ipc_path, exit_event):
        super().__init__()
        self.exit_event = exit_event
        self.ipc_path = ipc_path
        self.title = title
    
    def draw(self):
        import tkinter as tk
        self.root = tk.Tk()
        self.root.wm_title(self.title)
        self.is_fullscreen = False
        
        self.frame = tk.Frame(self.root, bg='#000000')
        self.frame.pack(expand=tk.YES, fill=tk.BOTH)
        self.frame.bind('<Double-Button-1>', self.toggle_fullscreen)

        self.root.protocol('WM_DELETE_WINDOW', self.exit)
        self.root.after(100, self.check_exit)
    
    def check_exit(self):
        if self.exit_event.is_set():
            self.exit()
        else:
            self.root.after(100, self.check_exit)

    def exit(self):
        self.exit_event.set()
        import time; time.sleep(0.3)
        self.root.destroy()
    
    def send_xid(self):
        self.xid = self.frame.winfo_id()
        sock = zmq.Context().socket(zmq.REQ)
        # sock.connect('ipc:///tmp/tc.camera_xid')
        sock.connect(self.ipc_path)
        sock.send_pyobj(self.xid)
        sock.recv()

    def toggle_fullscreen(self, evt):
        self.root.attributes('-fullscreen', self.is_fullscreen)
        self.is_fullscreen = not self.is_fullscreen
    
    def run(self):
        self.draw()
        self.send_xid()
        self.root.mainloop()


class ServerInfo:
    """Store immutable server information"""
    
    hello_port = 4140
    bye_port = 4141
    route_port = 4142
    list_cameras_port = 4143
    list_screens_port = 4144
    
    def __init__(self, address):
        self.addr = address

    @property
    def hello_endpoint(self):
        return 'tcp://%s:%d' % (self.addr, self.hello_port)
    
    @property
    def bye_endpoint(self):
        return 'tcp://%s:%d' % (self.addr, self.bye_port)

    @property
    def list_cameras_endpoint(self):
        return 'tcp://%s:%d' % (self.addr, self.list_cameras_port)

    @property
    def list_screens_endpoint(self):
        return 'tcp://%s:%d' % (self.addr, self.list_screens_port)


