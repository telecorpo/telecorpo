
import cmd
import sys
import zmq

from utils import ServerInfo

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
                print(", ".join(obj))
            else:
                print("No camera found")
        else:
            print(obj)

    def do_list_screens(self, line):
        ok, obj = self._get_screen()
        if ok:
            if len(obj) != 0:
                print(", ".join(obj))
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
        
        ok, obj = self._get_camera(camera)
        if not ok:
            print(obj)
            return
        route_endpoint = obj

        ok, obj = self._get_screen(screen)
        if not ok:
            print(obj)
            return
        addr, port = obj

        sock = self.context.socket(zmq.REQ)
        sock.connect(route_endpoint)
        sock.send_pyobj(['route', screen, addr, port])
        sock.recv()

    def do_EOF(self, line):
        return True


def main():
    if len(sys.argv) != 2:
        print("usage: tc-terminal SERVER", file=sys.stderr)
        sys.exit(1)

    server = ServerInfo(sys.argv[1].strip())
    terminal = Terminal(server)
    terminal.cmdloop()

if __name__ == '__main__':
    main()
