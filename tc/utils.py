import atexit
import colorlog
import flask
import json
import logging
import re
import socket
import types

from requests import post, delete
from requests.exceptions import Timeout
from flask.ext.restful import Api, Resource
from os import path



class TelecorpoException(Exception):
    pass


class TelecorpoEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, types.SimpleNamespace):
            return dict(obj.__dict__)
        return json.JSONEncoder.default(self, obj)


ipv4_re = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
def ipv4(value):
    if not ipv4_re.search(value):
        raise ValueError("Invalid IP address: {}".format(value))
    return value


def get_ip_address(addr, port=5000):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((addr, port))
        return s.getsockname()[0]
    except socket.error:
        raise TelecorpoException('Failed to get ip address or server is down.')


def find_free_port():
    # FIXME no guarantees that it will be free when you use it
    # FIXME (may occur race conditions)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port


def ask(prompt, default=None, validator=lambda x: x):
    value = input(prompt).strip()
    if not (value or default):
        raise ValueError('Empty value')
    return validator(value) if value != '' else validator(default)


def get_logger(name):
    format = ''.join(["%(log_color)s%(levelname)-8s%(reset)s ",
                     "%(black)s%(bold)s%(name)s%(reset)s: ",
                      "%(message)s"])
    handler = logging.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(format))

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return logger

def print_banner():
    return
    banner = path.join(path.dirname(__file__), 'banner.txt')
    print(open(banner).read())

def cleanup(url):
    logger.warn("Disconnecting from server")
    resp = delete(url + '?close_client=false')
    if not resp.ok:
        logger.error(resp.reason)
        logger.error("Failed to delete this camera, server may be in"
                     " inconsistent state.")
        logger.error("You MUST notify the developers if the server wasn't"
                     " shutdown.")

def connect(client, server, type):
    try:
        logger.debug("Getting IP address")
        client.addr = get_ip_address(server.addr)
        
        logger.debug("Looking for a free port")
        client.http_port = find_free_port()
        client.rtp_port = find_free_port()

        logger.info("Requesting ID for server")
        url = 'http://%s:%s/%s' % (server.addr, server.port, type)
        resp = post(url, timeout=5, data=dict(client.__dict__))

        if not resp.ok:
            logger.error(resp.reason)
            logger.error("Error %d %s. %s", resp.status_code, resp.reason, msg)
            sys.exit(1)
        
        client.id = json.loads(resp.text)
        logger.info("Your ID is '%s'", client.id)
        server.url = 'http://%s:%s/%s/%s' % (server.addr, server.port, type, client.id)
        
        atexit.register(cleanup, server.url)
        return

    except TelecorpoException as e:
        logger.error(e.message)
    except (ConnectionError, ConnectionRefusedError, Timeout):
        logger.error("Could not connect to server %s on port %d",
                     server.addr, server.port)
    sys.exit(1)

class ExitResource(Resource):
    def delete(self):
        func = flask.request.environ.get('werkzeug.server.shutdown')
        if func is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        logger.warn("Exiting")
        func()

logger = get_logger(__name__)
