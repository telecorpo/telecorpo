

import itertools
import zmq

from tc.utils import ServerInfo, get_logger


LOGGER = get_logger(__name__)


# UGLY POORLY WRITTEN CODE


class UserError(Exception):
    pass


class state:
    info = ServerInfo('*')
    context = zmq.Context.instance()

    cameras = {}
    screens = {}
    routes = []


class Sockets:
    def __init__(self):
        hello = state.context.socket(zmq.REP) 
        hello.bind(state.info.hello_endpoint)

        bye = state.context.socket(zmq.REP)
        bye.bind(state.info.bye_endpoint)

        list_cameras = state.context.socket(zmq.REP)
        list_cameras.bind(state.info.list_cameras_endpoint)

        list_screens = state.context.socket(zmq.REP)
        list_screens.bind(state.info.list_screens_endpoint)

        route = state.context.socket(zmq.REP)
        route.bind(state.info.route_endpoint)


def route(cam, scr):
    try: 
        addr, port = state.screens[scr]
    except KeyError:
        raise UserError("Screen not found")
    try:
        sock = state.context.socket(zmq.REQ)
        sock.connect(state.cameras[cam])
    except KeyError:
        raise UserError("Camera not found")

    sock.send_pyobj(['route', scr, addr, port])
    sock.recv()
    state.routes.append((cam, scr))

    for old_cam in [c for c, s in state.routes if s == scr and c != cam]:
        unroute(old_cam, scr)


def unroute(cam, scr):
    try:
        state.routes.remove((cam, scr))
    except ValueError:
        raise UserError("Route doesn't exists")

    sock = state.context.socket(zmq.REQ)
    sock.connect(state.cameras[cam])

    addr, port = state.screens[scr]
    sock.send_pyobj(['unroute', scr, addr, port])
    sock.recv()


def hello(kind, name, obj):
    if name in itertools.chain(state.cameras, state.screens):
        raise UserError("Name already taken")
    if kind == 'camera':
        route_endpoint = obj[0]
        state.cameras[name] = route_endpoint
    elif kind == 'screen':
        addr, port = obj
        state.screens[name] = addr, int(port)


def bye(kind, name):
    if kind == "camera":
        try:
            del state.cameras[name]
            state.routes = [r for r in state.routes if r[0] != name]
        except KeyError:
            raise UserError("Camera not found")

    elif kind == 'screen':
        try:
            del state.screens[name]
            for cam in [r[0] for r in state.routes if r[1] == name]:
                unroute(cam, name)
        except KeyError:
            raise UserError("Screen not found")


def list_cameras(name=None):
    if not name:
        return state.cameras
    try:
        return state.cameras[name]
    except KeyError:
        raise UserError("Camera not found")


def list_screens(name=None):
    if not name:
        return state.screens
    try:
        return state.screens[name]
    except KeyError:
        raise UserError("Screen not found")


def main_loop():
    class sockets:
        hello = state.context.socket(zmq.REP) 
        hello.bind(state.info.hello_endpoint)

        bye = state.context.socket(zmq.REP)
        bye.bind(state.info.bye_endpoint)

        list_cameras = state.context.socket(zmq.REP)
        list_cameras.bind(state.info.list_cameras_endpoint)

        list_screens = state.context.socket(zmq.REP)
        list_screens.bind(state.info.list_screens_endpoint)

        route = state.context.socket(zmq.REP)
        route.bind(state.info.route_endpoint)

    poller = zmq.Poller()
    poller.register(sockets.hello, zmq.POLLIN)
    poller.register(sockets.bye, zmq.POLLIN)
    poller.register(sockets.route, zmq.POLLIN)
    poller.register(sockets.list_cameras, zmq.POLLIN)
    poller.register(sockets.list_screens, zmq.POLLIN)

    while True:
        socks = dict(poller.poll())

        if sockets.hello in socks:
            parts = sockets.hello.recv_pyobj()
            try:
                hello(parts[0], parts[1], parts[2:])
                sockets.hello.send_pyobj("ok")
            except UserError as err:
                sockets.hello.send_pyobj(str(err))

        if sockets.bye in socks:
            bye(*sockets.bye.recv_pyobj())
            sockets.bye.send(b"")

        if sockets.route in socks:
            action, cam, scr = sockets.route.recv_pyobj()
            try:
                if action == 'route':
                    route(cam, scr)
                else:
                    unroute(cam, scr)
                sockets.route.send_pyobj("ok")
            except UserError as err:
                sockets.route.send_pyobj(str(err))
        
        if sockets.list_cameras in socks:
            name = sockets.list_cameras.recv_pyobj()
            try:
                resp = list_cameras(name)
                sockets.list_cameras.send_pyobj([True, resp])
            except UserError as err:
                sockets.list_cameras.send_pyobj([False, str(err)])

        if sockets.list_screens in socks:
            name = sockets.list_screens.recv_pyobj()
            try:
                resp = list_screens(name)
                sockets.list_screens.send_pyobj([True, resp])
            except UserError as err:
                sockets.list_screens.send_pyobj([False, str(err)])


def main():
    try:
        main_loop()
    except KeyboardInterrupt:
        LOGGER.critical("Close all clients manually")

if __name__ == '__main__':
    main()
