
import coloredlogs
import logging
import os.path
import re
import socket

class TelecorpoException(Exception):
    pass

ipv4_regex = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
def ipv4(value):
    if not ipv4_regex.search(value):
        raise ValueError(u"Invalid IP address: {}".format(value))
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
    logger = logging.getLogger(name)
    logger.addHandler(coloredlogs.ColoredStreamHandler(
        level           = logging.DEBUG,
        show_hostname   = False,
        show_timestamps = False
        ))
    return logger

def print_banner():
    print open(os.path.join(os.path.dirname(__file__), 'banner.txt')).read()
