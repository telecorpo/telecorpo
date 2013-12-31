
import colorlog
import logging
import re
import sys
import Tkinter as tk
import twisted

class TCException(Exception):
    """Base exception class."""


class TCFailure(RuntimeError):
    """Suposed to stop the reactor."""


def get_logger(name):
    format = ''.join(["%(log_color)s%(levelname)-8s%(reset)s ",
                      "%(black)s%(bold)s%(name)s%(reset)s:%(lineno)s ",
                      "(%(black)s%(bold)s%(processName)s%(reset)s): ",
                      "%(message)s"])
    handler = logging.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(format))

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return logger


logging.getLogger('werkzeug').setLevel(logging.ERROR)
LOG = get_logger(__name__)


_ipv4_re = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
def ipv4(value):
    if not _ipv4_re.search(value):
        raise ValueError("Invalid IP address: {}".format(value))
    return value


def port(v):
    v = int(v)
    if not 1 <= v <= 65535:
        raise ValueError("%d not in allowed port range" % v)
    return v


def ask(prompt, default=None, validator=lambda x: x):
    value = input(prompt).strip()
    if not (value or default):
        raise ValueError('Empty value')
    return validator(value) if value != '' else validator(default)


def banner():
    from os import path
    print(open(path.join(path.dirname(__file__), 'banner.txt')).read())


def exit():
    twisted.stop()

