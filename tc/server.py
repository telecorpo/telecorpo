import logging
from types import SimpleNamespace
from flask import Flask, request
from flask.ext.restful import reqparse, abort, Api, Resource
from uuid import uuid1

from tc.utils import get_logger, ipv4, print_banner

logger = get_logger(__name__)
app = Flask(__name__)
api = Api(app)

SCREENS = {}
CAMERAS = {}
ROUTES = []

class CamerasResource(Resource):

    parser = reqparse.RequestParser()
    parser.add_argument('name', type=str, required=True)
    parser.add_argument('addr', type=ipv4, required=True)
    parser.add_argument('http_port', type=int, required=True)

    def get(self, id):
        if id:
            try:
                return CAMERAS[id]
            except KeyError:
                abort(404)
        return CAMERAS

    def post(self, id):
        args = self.parser.parse_args()
        camera = SimpleNamespace(
            id   = uuid1().hex,
            name = args['name'],
            addr = args['addr'],
            http_port = args['http_port'])
        CAMERAS[camera.id] = camera
        logger.info("New camera created", camera)
        return camera.id, 201

    def delete(self, id):
        if (not id) or (id not in CAMERAS):
            abort(400)
        del CAMERAS[id]
        return '', 204


api.add_resource(CamerasResource,
    '/cameras',
    '/cameras/<string:id>',
    defaults={'id': None})

def main():
    print_banner()
    # logging.getLogger('werkzeug').setLevel(logging.DEBUG)
    port = 5000
    logger.info("Starting server on port %s", 5000)
    app.run(port=port, debug=True)

if __name__ == '__main__':
    main()
