import builtins
import flask
import flask.ext.restful
import json

from types import SimpleNamespace

from tc.server.camera import CameraResource, CameraListResource
from tc.server.screen import ScreenResource, ScreenListResource
from tc.server.route import RouteResource
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
    
    # register HTTP resources
    resources = [
        CameraResource, CameraListResource,
        ScreenResource, ScreenListResource,
        RouteResource
    ]
    for resource in resources:
        API.add_resource(resource, resource.endpoint)
    
    # start server
    port = 5000
    LOG.info("Starting server on port %s", port)
    APP.run(port=port, debug=True)

if __name__ == '__main__':
    main()
