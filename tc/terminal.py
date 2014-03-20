
import cmd
import sys
import zmq

from tc.utils import ServerInfo

class Terminal(cmd.Cmd):
    
    def __init__(self, server):
        super().__init__()
        self.server = server
        self.context = zmq.Context.instance()
        self.prompt = '% '

    def postcmd(self, stop, line):
        if line.strip() != "":
            print()
        self.lastcmd = ""
        return stop
    
    def _get_camera(self, name=None):
        sock = self.context.socket(zmq.REQ)
        sock.connect(self.server.list_cameras_endpoint)
        sock.send_pyobj(name)
        return sock.recv_pyobj()

    def _get_screen(self, name=None):
        sock = self.context.socket(zmq.REQ)
        sock.connect(self.server.list_screens_endpoint)
        sock.send_pyobj(name)
        return sock.recv_pyobj()

    def do_list_cameras(self, line):
        ok, obj = self._get_camera()
        if ok:
            if len(obj) != 0:
                print(", ".join(sorted(obj)))
            else:
                print("No camera found")
        else:
            print(obj)

    def do_list_screens(self, line):
        ok, obj = self._get_screen()
        if ok:
            if len(obj) != 0:
                print(", ".join(sorted(obj)))
            else:
                print("No screen found")
        else:
            print(obj)

    def do_route(self, line):
        args = line.split()
        if len(args) != 2:
            print("Invalid number of arguments")
            return
        camera, screen = args
        sock = self.context.socket(zmq.REQ)
        sock.connect(self.server.route_endpoint)
        sock.send_pyobj(['route', camera, screen])
        print(sock.recv_pyobj())
        

    def do_EOF(self, line):
        return True


def main(server_addr):
    server = ServerInfo(server_addr)
    terminal = Terminal(server)
    print('Press Ctrl-D to exit')
    terminal.cmdloop()

if __name__ == '__main__':
    main()
