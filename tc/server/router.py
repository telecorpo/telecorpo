
from collections        import namedtuple
from flask.ext.restful  import reqparse, abort, Resource, types
from requests           import delete
from types              import SimpleNamespace
from uuid               import uuid1

from tc.utils           import get_logger, ipv4

logger = get_logger(__name__)
Route = namedtuple('Route', 'camera screen')

class RoutesResource(Resource):
    """Handle routes."""
    
    #: endpoint URL
    endpoint = '/routes'
    
    parser = reqparse.RequestParser()
    parser.add_argument('camera_id', type=str)
    parser.add_argument('screen_id', type=str)
    
    def get(self):
        """List all routes."""
        return ROUTES, 200

    def post(self):
        """Create a route."""
        logger.debug("post()")
        
        # parse arguments
        args = self.parser.parse_args()
        try:
            camera = CAMERAS[args['camera_id']]
            screen = SCREENS[args['screen_id']]
        except KeyError:
            abort(404, message="Camera or Screen not found")
        
        route = Route(camera.id, screen.id)
        affected_routes = [Route(c, s) for c, s in ROUTES if s.id == screen.id]
        if len(affected_routes) == 1:
            affected = affected_routes[0]
             
            ROUTES.remove(affected)

        elif len(affected_routes) > 1:
            logger.error("Screen '%s' is on more than one route", screen.id)
        
        ROUTES.append((camera.id, screen.id))

            

        # send a exit message to camera
        if close_camera:
            delete('http://%s:%s' % (camera.addr, camera.http_port))
            logger.info("Hopefully it was closed")
        
        # ok, success
        return '', 200


class CameraListResource(Resource):
    """Handle requests relative a all cameras."""

    #: endpoint URL
    endpoint = '/cameras'

    parser = reqparse.RequestParser()
    parser.add_argument('name', type=str, required=True)
    parser.add_argument('addr', type=ipv4, required=True)
    parser.add_argument('http_port', type=int, required=True)
    
    def get(self):
        """List all cameras."""
        logger.debug("get()")
        return CAMERAS, 200

    def post(self):
        """Create a new camera."""
        logger.debug("post()")
        
        # build the new camera
        args = self.parser.parse_args()
        camera = SimpleNamespace(
            id   = uuid1().hex,
            name = args['name'],
            addr = args['addr'],
            http_port = args['http_port'])

        # check if camera's name was already taken
        if camera.name in [c.name for c in CAMERAS.values()]:
            message = "Camera name '%s' was already taken" % camera.name
            logger.error(message)
            abort(409, message=message)
        
        # persisting object
        CAMERAS[camera.id] = camera
        logger.debug(camera)
        logger.info("New camera named '%s' created", camera.name)

        # created, success
        return camera.id, 201

