import atexit
import flask
import flask.ext.restful
import json
import multiprocessing
import requests

from requests import ConnectionError, Timeout

from tc       import utils
from tc.utils import TelecorpoException
from tc.streaming import Streamer

from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop, PeriodicCallback

logger = utils.get_logger(__name__)
LOG = utils.get_logger(__name__)

class BaseClient:
    """Class responsible for collect user info and connect to server."""

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



class WebApp(multiprocessing.Process):

    def __init__(self, name, exit_conn, port, resources):
        super().__init__()

        self.app = flask.Flask(name)
        self.port = port
        self.exit_conn = exit_conn
        self.exit_callbacks = []

        # build REST api
        self.rest_api = flask.ext.restful.Api(self.app)
        for resource in resources:
            resource.exit_conn = self.exit_conn
            self.rest_api.add_resource(resource, resource.endpoint)
        
        # create app context
        with self.app.app_context() as ctx:
            ctx.g.exit_conn = self.exit_conn

        # continuously check exit_conn
        self.periodic_cb = PeriodicCallback(self._check_exit, 100)

    def on_exit(self):
        pass

    def _check_exit(self):
        if self.exit_conn.poll() and self.exit_conn.recv():
            IOLoop.instance().stop()
            self.on_exit()
    
    def run(self):
        http_server = HTTPServer(WSGIContainer(self.app))
        http_server.listen(self.port)

        self.periodic_cb.start()
        self.streamer.start()
        self.app.debug = False
        LOG.info("Listening HTTP on port %s", self.port)
        IOLoop.instance().start()

