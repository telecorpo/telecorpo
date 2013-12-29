
import json
import requests
from tc.utils import TCException


def _request(func, *args, **kwargs):
    try:
        r = func(*args, **kwargs)
        if not r.ok:
            msg = "Error {} {}: {}".format(r.status_code, r.reason, r.text)
            raise TCException(msg)
        return json.loads(r.text)
    except (requests.ConnectionError, requests.Timeout) as err:
        raise TCException(err)


def post(url, data=None, timeout=5):
    _request(requests.post, url, data=(data or {}), timeout=timeout)


def put(url, data=None, timeout=5):
    _request(requests.put, url, data=(data or {}), timeout=timeout)


def delete(url, data=None, timeout=5):
    _request(requests.delete, url, data=(data or {}), timeout=timeout)
