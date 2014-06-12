
import inspect
import redis
import socket
import time

from tc.utils import get_logger

LOG = get_logger(__name__)


class TelecorpoException(Exception):
    pass


class Connection:

    def __init__(self, server):
        self.r = redis.StrictRedis(*server)
        self.ps = self.r.pubsub()

    def _register(self, name, attempt=0):
        LOG.info("Registering this node")
        try:
            if attempt == 3:
                raise TelecorpoException("register_lock key was deadlocked")

            if not self.r.set('register_lock', 1, ex=3, nx=True):
                LOG.warn("Network busy... trying again...")
                time.sleep(1)
                self._register(name, attempt+1)

            elif not self.r.sadd('nodes', name):
                    raise TelecorpoException(
                        "Name already taken. Choose another one.")
        except Exception as e:
            self.r.delete('register_lock')
            LOG.exception(e)
            raise

    def _deregister(self, name):
        self.r.srem('nodes', name)

    def watch_events(self):
        self.ps.subscribe(['camera_ready', 'camera_deleted', 'screen_ready',
            'screen_deleted', 'server_down', 'route'])

        for item in self.ps.listen():
            if item['type'] == 'message':
                channel = item['channel'].decode()
                callback = getattr(self, 'on_%s' % channel, None)
                if callback:
                    try:
                        callback(*item['data'].decode().split())
                    except Exception as err:
                        LOG.exception(err)


class CameraConnection(Connection):

    def __init__(self, name, pipe, server):
        self.name = name
        self.pipe = pipe
        super().__init__(server)

    def register(self):
        self._register(self.name)
        self.r.sadd('cameras', self.name)
        self.r.delete('register_lock')
        self.r.publish('camera_ready', self.name)
    
    def deregister(self):
        self._deregister(self.name)
        self.r.srem('cameras', self.name)
        self.r.delete('camera:%s:clients' % self.name)
        self.r.publish('camera_deleted', self.name)

    def on_route(self, camera, screen):
        if camera != self.name:
            return
        ipaddr = self.r.get('screen:%s:ipaddr' % screen).decode()
        self.pipe.add_client(ipaddr, 12345)
    
    def on_screen_deleted(self, screen):
        if self.r.srem('camera:%s:clients' % self.name, screen):
            self.r.get('screen:%s:ipaddr'
            self.pipe.delete_client(ipaddr, 12345)

class ScreenConnection(Connection):
    
    def __init__(self, name, server):
        self.name = name
        self.ipaddr = self.find_ipaddr(server)
        super().__init__(server)

    def find_ipaddr(self, server):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((server[0], server[1]))
        ipaddr = s.getsockname()[0]
        s.close()
        return ipaddr

    def register(self):
        self._register(self.name)
        self.r.sadd('screens', self.name)
        self.r.set('screen:%s:ipaddr' % self.name, self.ipaddr)
        self.r.delete('register_lock')

    def deregister(self):
        self._deregister(self.name)
        self.r.srem('screens', self.name)
        self.r.delete('screen:%s:ipaddr' % self.name)

if __name__ == '__main__':
    import sys
    conn = CameraConnection(sys.argv[1], ('localhost', 6379, 0))
    conn.register()
    conn.watch_events()
