
from flask.ext.restful  import reqparse, abort, Resource, types
from requests           import delete
from types              import SimpleNamespace
from uuid               import uuid1

from tc.utils           import get_logger, ipv4


LOG = get_logger(__name__)


class ScreenResource(Resource):
    """Handle requests relative to one screen."""
    
    #: endpoint URL
    endpoint = '/screens/<string:id>'

    parser = reqparse.RequestParser()
    parser.add_argument('close_client', type=types.boolean)

    def get(self, id):
        """Return an individual screen."""
        LOG.debug("get('%s')", id)
        try:
            LOG.debug(SCREENS[id])
            return SCREENS[id]
        except KeyError:
            LOG.error("Screen with id='%s' doesn't exists", id)
            abort(404)

    def delete(self, id):
        """Delete a screen."""
        LOG.debug("delete('%s')", id)
        
        # parse arguments
        args = self.parser.parse_args()
        close_screen = args['close_client']
        if close_screen is None:
            close_screen = True

        # wtf, something went wrong on client code
        if id not in SCREENS:
            LOG.error("Screen with id='%s' doesn't exists", id)
            abort(404)
        
        # delete the screen from server
        screen = SCREENS.pop(id)
        LOG.debug(screen)
        LOG.info("Screen '%s' was removed from server", screen.name)
        
        # delete associated routes
        for route in [r for r in ROUTES if r.screen == screen.id]:
            print(route.camera)
            camera = CAMERAS[route.camera]
            ROUTES.remove(route)
            r = post('http://%s:%s/remove', data={
                'addr': camera.addr,
                'rtp_port': camera.rtp_port
            })
            if not r.ok:
                LOG.error("Could not remove associated route %r", route)
                LOG.error("Error %d %s: %s" % (r.status_code, r.reason, r.text))
            else:
                LOG.info("Removed associated route %r", route)

        # send an exit message to screen
        if close_screen:
            delete('http://%s:%s' % (screen.addr, screen.http_port))
            LOG.info("Hopefully it was closed")

        # ok, success
        return '', 200


class ScreenListResource(Resource):
    """Handle requests relative to all cameras."""
    
    #: endpoint URL
    endpoint = '/screens'

    parser = reqparse.RequestParser()
    parser.add_argument('name', type=str, required=True)
    parser.add_argument('addr', type=ipv4, required=True)
    parser.add_argument('http_port', type=int, required=True)
    parser.add_argument('rtp_port', type=int, required=True)
    
    def get(self):
        """List all cameras."""
        LOG.debug("get()")
        return SCREENS, 200

    def post(self):
        """Create a new screen."""
        LOG.debug("post()")
        
        # build the new screen
        args = self.parser.parse_args()
        screen = SimpleNamespace(
            id   = uuid1().hex,
            name = args['name'],
            addr = args['addr'],
            http_port = args['http_port'],
            rtp_port = args['rtp_port'])

        # check if screen's name was already taken
        if screen.name in [s.name for s in SCREENS.values()]:
            message = "Screen name '%s' was already taken" % screen.name
            LOG.error(message)
            abort(409, message=message)

        # persisting object
        SCREENS[screen.id] = screen
        LOG.debug(screen)
        LOG.info("New screen '%s' created", screen.name)

        # created, success
        return screen.id, 201

