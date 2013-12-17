import atexit
import json
import requests

from requests import ConnectionError, Timeout

from tc       import utils
from tc.utils import TelecorpoException

logger = utils.get_logger(__name__)

class Client:
    def __init__(self, url_endpoint, name, server_addr, server_port):
        self.id = None
        self.name = name
        self.http_port = utils.find_free_port()
        self.addr = utils.get_ip_address(server_addr, server_port)

        self._url_endpoint = url_endpoint

        self._server_addr = server_addr
        self._server_port = server_port

        self._connect_url = None
        self._disconnect_url = None
    
    def connect(self):
        logger.debug("Attemping new connection to %s:%s", self._server_addr,
                     self._server_port)

        # discover client connection URL
        url = 'http://%s:%d/%s' % (self._server_addr, self._server_port,
                                   self._url_endpoint)
        
        # discover parameters
        params = {}
        for k, v in self.__dict__.items():
            if k.startswith('_') or hasattr(v, '__call__'):
                continue
            params[k] = v

        try:
            logger.debug("Posting to %s with parameters %r", url, params)
            r = requests.post(url, timeout=5, data=params)
            if not r.ok:
                msg = "Error %d %s: %s" % (r.status_code, r.reason, r.text)
                raise TelecorpoException(msg)
            self.id = json.loads(r.text)
            logger.debug("Got ID %s", self.id)
            atexit.register(self.disconnect)
        except (ConnectionError, ConnectionRefusedError, Timeout):
            msg = "Could not connect to server %s:%d" % (self._server_addr,
                                                         self._server_port)
            raise TelecorpoException(msg)


    def disconnect(self):
        # discover client disconnection URL
        cls_name = self.__class__.__name__.lower()
        url = 'http://%s:%d/%s/%s?close_client=false' 
        url = url % (self._server_addr, self._server_port, self._url_endpoint,
                     self.id)
        
        # delete this client
        r = requests.delete(url, timeout=5)

        if not r.ok:
            msg = ("Failed to disconnect, server may be in inconsistent state."
                   " You MUST notify the developer IF the server wasn't shutdown.")
            raise TelecorpoException(msg)

