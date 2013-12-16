import builtins
import logging
import json
import flask
import flask.ext.restful

from tc import utils
from tc.server.camera import CameraResource, CameraListResource
from tc.server.screen import ScreenResource, ScreenListResource

# XXX very very ugly
builtins.SCREENS = {}
builtins.CAMERAS = {}
builtins.ROUTES = []

logger = utils.get_logger(__name__)
app = flask.Flask(__name__)
api = flask.ext.restful.Api(app)

resources = [
    CameraResource, CameraListResource,
    ScreenResource, ScreenListResource
]
for resource in resources:
    api.add_resource(resource, resource.endpoint)

@api.representation('application/json')
def outputs_json(data, code, headers=None):
    data = json.dumps(data, cls=utils.TelecorpoEncoder)
    resp = flask.make_response(data, code)
    resp.headers.extend(headers or {})
    return resp

def main():
    utils.print_banner()
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    port = 5000
    logger.info("Starting server on port %s", 5000)
    app.run(port=port, debug=True)

if __name__ == '__main__':
    main()
