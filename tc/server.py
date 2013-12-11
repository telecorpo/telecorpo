import logging
from types import SimpleNamespace
from flask import Flask, request
from flask.ext.restful import reqparse, abort, Api, Resource
from uuid import uuid1

from tc.utils import ipv4

app = Flask(__name__)
api = Api(app)

SCREENS = {}
CAMERAS = {}
ROUTES = []

parser = reqparse.RequestParser()
parser.add_argument('name',   type=str)
parser.add_argument('site',   type=str)
parser.add_argument('addr',   type=ipv4_type)
parser.add_argument('port',   type=int)
parser.add_argument('id',     type=str)
parser.add_argument('camera', type=str)
parser.add_argument('screen', type=str)

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

    def post(self):
        args = self.parser.parse_args()
        camera = SimpleNamespace(
            id   = uuid1().hex,
            name = args['name'],
            site = args['site'],
            addr = args['addr'],
            http_port = args['http_port'])
        CAMERAS[camera.id] = camera
        return camera.id, 201

    def delete(self, id):
        if (not id) or (id not in CAMERAS):
            abort(400)
        del CAMERAS[id]
        return '', 204


resources = [
    (CamerasResource, {'id': None}, '/cameras', '/cameras/<string:id>'),
    ]

api.add_resource(CamerasResource,
    '/cameras',
    '/cameras/<string:id>',
    defaults={'id': None})

def main():
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    app.run()
