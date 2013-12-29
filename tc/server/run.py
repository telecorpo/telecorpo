import atexit
import builtins
import flask
import flask.ext.restful
import json
import requests
import signal

from types import SimpleNamespace

from tc.server.camera import CameraResource, CameraListResource
from tc.server.screen import ScreenResource, ScreenListResource
from tc.server.route import RouteResource, RouteListResource
from tc.utils import banner, get_logger


builtins.SCREENS = {}
builtins.CAMERAS = {}
builtins.ROUTES = []


LOG = get_logger(__name__)
APP = flask.Flask(__name__)
API = flask.ext.restful.Api(APP)


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, SimpleNamespace):
            return dict(obj.__dict__)
        return json.JSONEncoder.default(self, obj)


@API.representation('application/json')
def outputs_json(data, code, headers=None):
    data = json.dumps(data, cls=CustomJSONEncoder)
    resp = flask.make_response(data, code)
    resp.headers.extend(headers or {})
    return resp


def main():
    banner()

    # exit handler
    def _exit_handler(signum, stackframe):
        clients = []
        clients += CAMERAS.values()
        clients += SCREENS.values()

        for client in clients:
            url = 'http://%s:%s/exit' % (client.addr, client.http_port)
            print(url)
            r = requests.delete(url)
            print(r)
            if not r.ok:
                LOG.error("Failed to delete %r", client)
                LOG.error("Error %d %s: %s", r.status_code, r.reason, r.text)
        raise SystemExit

    for signum in [signal.SIGINT, signal.SIGTERM]:
        signal.signal(signum, _exit_handler)

    # register HTTP resources
    resources = [
        CameraResource, CameraListResource,
        ScreenResource, ScreenListResource,
        RouteResource, RouteListResource
    ]
    for resource in resources:
        API.add_resource(resource, resource.endpoint)

    # start server
    port = 5000
    LOG.info("Starting server on port %s", port)
    APP.run(port=port, debug=False)

if __name__ == '__main__':
    main()
