import atexit
import colorlog
import flask
import json
import logging
import re
import requests
import socket

from requests import post, delete
from requests.exceptions import Timeout
from os import path



class TelecorpoException(Exception):
    pass


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


ipv4_re = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
def ipv4(value):
    if not ipv4_re.search(value):
        raise ValueError("Invalid IP address: {}".format(value))
    return value


def ask(prompt, default=None, validator=lambda x: x):
    value = input(prompt).strip()
    if not (value or default):
        raise ValueError('Empty value')
    return validator(value) if value != '' else validator(default)


def banner():
    print(open(path.join(path.dirname(__file__), 'banner.txt')).read())


def _request_exception_handler(func, *args, **kw):
    try:
        r = func(*args, **kw)
        if not r.ok:
            msg = "Error {} {}: {}".format(r.status_code, r.reason, r.text)
            raise TelecorpoException(msg)
        return json.loads(r.text)
    except (requests.ConnectionError, requests.Timeout,
            TelecorpoException) as ex:
        raise TelecorpoException(ex)

def post(url, data=None, timeout=5):
    _request_exception_handler(requests.post, url, data=(data or {}),
                               timeout=timeout)

def delete(url, data=None, timeout=5):
    _request_exception_handler(requests.delete, url, data=(data or {}),
                               timeout=timeout)
