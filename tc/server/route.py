
from collections        import namedtuple
from flask.ext.restful  import reqparse, abort, Resource, types
from requests           import delete, post
from types              import SimpleNamespace
from uuid               import uuid1

from tc.utils           import get_logger, ipv4

logger = get_logger(__name__)
Route = namedtuple('Route', 'camera screen')

class RouteResource(Resource):
    """Handle routes."""
    
    #: endpoint URL
    endpoint = '/routes'
    
    parser = reqparse.RequestParser()
    parser.add_argument('camera_id', type=str, required=True)
    parser.add_argument('screen_id', type=str, required=True)
    
    def get(self):
        """List all routes."""
        logger.debug("> RoutesResource.get()")
        return ROUTES, 200

    def post(self):
        """Create a route."""
        logger.debug("> RoutesResource.post()")
        
        # parse arguments
        args = self.parser.parse_args()
        try:
            camera = CAMERAS[args['camera_id']]
            screen = SCREENS[args['screen_id']]
            route = Route(camera.id, screen.id)
            logger.debug("Trying to create %s", route)
        except KeyError:
            msg = "Camera or screen not found"
            logger.error(msg)
            abort(404, message=msg)
        
        # take a shortcut if the route was already created
        if route in ROUTES:
            logger.debug("%s already exists", route)
            return '', 200
        
        # screen is active on another route, deactivate it
        affected = [r for r in ROUTES if r.screen == screen.id]
        if len(affected) == 1:
            logger.debug("Removing the route %s", affected[0])

            affected_cam = CAMERAS[affected[0].camera]
            affected_scr = SCREENS[affected[0].screen]
            url = 'http://%s:%s/remove' % (affected_cam.addr,
                                           affected_cam.http_port)
            logger.debug("Posting on %s", url)
            r = post(url, data=dict(affected_scr.__dict__))
            ROUTES.remove(route)
            if not r.ok:
                logger.error("Failed to remove screen '%s' from camera '%s'",
                             affected_scr.id, affected_cam.id)
                logger.error("Error %d %s: %s", r.status_code, r.reason,
                             r.text)
                return
        
        # bad error
        elif len(affected) > 1:
            logger.error("Screen '%s' is on more than one route", screen.id)
        
        # clear, new create the route
        ROUTES.append(route)
        url = 'http://%s:%s/add' % (camera.addr, camera.http_port)
        r = post(url, data=screen.__dict__)
        if not r.ok:
            logger.error("Failed to create %s", route)
            logger.error("Error %d %s: %s", r.status_code, r.reason, r.text)
            return

        # ok, success
        logger.info("Route created")
        return '', 200

