
import colorlog
import logging
import re
import socket

from os import path

class TelecorpoException(Exception):
    pass

ipv4_regex = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
def ipv4(value):
    if not ipv4_regex.search(value):
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


def get_logger(name):
    format = "%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(message)s"
    handler = logging.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(format))

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return logger

def print_banner():
    banner = path.join(path.dirname(__file__), 'banner.txt')
    print(open(banner).read())
