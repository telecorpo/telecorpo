
import json
import uuid
import socket
import time
import zmq

from .utils import get_logger

# class AttrDict(dict):
#     def __init__(self, *args, **kwargs):
#         super(AttrDict, self).__init__(*args, **kwargs)
#         self.__dict__ = self
#

LOG = get_logger(__name__)
WAIT = 0.5

def uniq():
    return uuid.uuid1().hex

def find_address(forwarder):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((forwarder,1337))
    addr = s.getsockname()[0]
    s.close()
    return addr

def forwarder_device_main():
    try:
        context = zmq.Context(1)
        # Socket facing clients
        frontend = context.socket(zmq.SUB)
        frontend.bind("tcp://*:1337")


        # Socket facing services
        backend = context.socket(zmq.PUB)
        backend.bind("tcp://*:1338")

        frontend.setsockopt(zmq.SUBSCRIBE, b'')

        zmq.device(zmq.FORWARDER, frontend, backend)
    except Exception as e:
        LOG.exception(e)
        LOG.fatal("bringing down zmq device")
    finally:
        frontend.close()
        backend.close()
        context.term()


class Subscriber:
    def __init__(self, ctx, uniq, forwarder, port):
        self.sock = ctx.socket(zmq.SUB)
        self.sock.connect("tcp://%s:1338" % forwarder)
        self.sock.setsockopt(zmq.SUBSCRIBE, b'')
        self.uniq = uniq
    
    def recv(self):
        data = json.loads(self.sock.recv().decode())
        topic, origin, msg = data
        uniq, name = origin
        if uniq == self.uniq:
            return None, None, None
        LOG.debug("received %s" % data)
        return topic, origin, msg


class Publisher:
    def __init__(self, ctx, uniq, name, forwarder):
        self.sock = ctx.socket(zmq.PUB)
        self.sock.connect("tcp://%s:1337" % forwarder)
        self.uniq = uniq
        self.name = name

    def send(self, topic, data):
        origin = (self.uniq, self.name)
        msg = [topic, origin, data]
        LOG.debug("sending %s" % msg)
        self.sock.send(json.dumps(msg).encode())


class Node:
    def __init__(self, forwarder, kind, name):
        self.uniq = uniq()
        self.name = name
        self.kind = kind
        self.addr = find_address(forwarder)

        self.purged = False

        ctx = zmq.Context(1)

        self.sub = Subscriber(ctx, self.uniq, forwarder, "1338")
        self.pub = Publisher(ctx, self.uniq, self.name, forwarder)

    def recv_hello(self, origin, msg):
        uniq, name = origin
        if name == self.name:
            LOG.warn("purging an impostor named %s!" % name)
            self.send_purge(uniq, "Name already taken. Choose another name.")
            return False
        return True
    
    def recv_purge(self, origin, msg):
        if msg['target'] == self.uniq:
            LOG.fatal(msg['text'])
            self.purged = True

    def send_hello(self):
        self.pub.send('hello', {
            'kind': self.kind,
            'addr': self.addr
        })

    def send_purge(self, uniq, text):
        self.pub.send('purge', {
            'target': uniq,
            'text': text
        })

    def main_loop(self):
        LOG.debug("on main_loop()")
        self.send_hello()
        time.sleep(WAIT)

        while not self.purged:
            # import ipdb; ipdb.set_trace()
            topic, origin, msg = self.sub.recv()
            if not topic or origin[0] == self.uniq:
                continue
            callback = getattr(self, 'recv_%s' % topic, None)
            if callback:
                callback(origin, msg)

