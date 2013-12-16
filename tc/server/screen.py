
from flask.ext.restful  import reqparse, abort, Resource, types
from requests           import delete
from types              import SimpleNamespace
from uuid               import uuid1

from tc.utils           import get_logger, ipv4

logger = get_logger(__name__)

class ScreenResource(Resource):
    """Handle requests relative to one screen."""
    
    #: endpoint URL
    endpoint = '/screens/<string:id>'

    parser = reqparse.RequestParser()
    parser.add_argument('close_client', type=types.boolean)

    def get(self, id):
        """Return an individual screen."""

        logger.debug("get('%s')", id)
        try:
            logger.debug(SCREENS[id])
            return SCREENS[id]
        except KeyError:
            logger.error("Screen with id='%s' doesn't exists", id)
            abort(404)

    def delete(self, id):
        """Delete a screen."""
        logger.debug("delete('%s')", id)
        
        # parse arguments
        args = self.parser.parse_args()
        close_screen = args['close_client']
        if close_screen is None:
            close_screen = True

        # wtf, something went wrong on client code
        if id not in SCREENS:
            logger.error("Screen with id='%s' doesn't exists", id)
            abort(404)
        
        # delete the screen from server
        screen = SCREENS.pop(id)
        logger.debug(screen)
        logger.info("Screen named '%s' was removed from server", screen.name)

        # send an exit message to screen
        if close_screen:
            delete('http://%s:%s' % (screen.addr, screen.http_port))
            logger.info("Hopefully it was closed")

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
        logger.debug("get()")
        return SCREENS, 200

    def post(self):
        """Create a new screen."""
        logger.debug("post()")
        
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
            logger.error(message)
            abort(409, message=message)

        # persisting object
        SCREENS[screen.id] = screen
        logger.debug(screen)
        logger.info("New screen named '%s' created", screen.name)

        # created, success
        return screen.id, 201
