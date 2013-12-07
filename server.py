import logging
from flask import Flask, request
from flask.ext.restful import reqparse, abort, Api, Resource
from uuid import uuid1

from utils import ipv4_type

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

    def get(self):
        id = parser.parse_args()['id']
        if id:
            assert id in CAMERAS
            return CAMERAS[id]
        return CAMERAS

    def post(self):
        # FIXME assert that args['addr'] is a valid IP address
        args = parse.parse_args()
        assert all(map(args.__contains__, ['name', 'site', 'addr']))
        camera = dict(
            id   = uuid1().hex,
            name = args['name'],
            site = args['site'],
            addr = args['addr'],
            screens = [])
        
        CAMERAS[camera['id']] = camera
        return CAMERAS[camera['id']], 201

    def delete(self):
        id = parser.parse_args()['id']
        assert id in CAMERAS
        del CAMERAS[id]
        #TODO notify associated displays
        return '', 204


class ScreensResource(Resource):
    
    def get(self):
        id = parser.parse_args()['id']
        if id:
            assert id in SCREENS
            return SCREENS[id]
        return SCREENS

    def post(self):
        # FIXME assert that args['addr'] is a valid IP address
        args = parser.parse_args()
        assert all(map(args.__contains__, ['name', 'site', 'addr', 'port']))
        screen = dict(
            id   = uuid1().hex,
            name = args['name'],
            site = args['site'],
            addr = args['addr'],
            port = args['port'])

        SCREENS[screen['id']] = screen
        return SCREENS[screen['id']], 201

    def delete(self):
        id = parser.parse_args()['id']
        assert id in SCREENS
        del SCREENS[id]
        return '', 204

class RoutesResource(Resource):
    
    def get(self):
        return ROUTES 

    def post(self):
        args = parser.parse_args()
        cam = args['camera']
        scr = args['screen']
        
        assert (cam in CAMERAS) and (scr in SCREENS)
         
        affected_routes = [(c, s) for c, s in ROUTES if scr==s]
        assert len(affected_routes) <= 1
        if len(affected_routes) == 1:
            ROUTES.remove(affected_routes[0])
            # TODO disable affected route

        ROUTES.append((cam, scr))
        # TODO notify camer where to stream
        return (cam, scr)


api.add_resource(ScreensResource, '/screens')
api.add_resource(CamerasResource, '/cameras')
api.add_resource(RoutesResource, '/routes')

if __name__ == '__main__':
    app.run(debug=True)
