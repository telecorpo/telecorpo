
from flask.ext.restful  import reqparse, abort, Resource, types
from types              import SimpleNamespace

from tc.utils           import get_logger, ipv4, delete, TelecorpoException, post


LOG = get_logger(__name__)


class ScreenResource(Resource):
    """Handle requests relative to one screen."""

    #: endpoint URL
    endpoint = '/screens/<string:name>'

    parser = reqparse.RequestParser()
    parser.add_argument('addr', type=ipv4, required=True)
    parser.add_argument('http_port', type=int, required=True)
    parser.add_argument('rtp_port', type=int, required=True)

    def get(self, name):
        """Return one or all screens."""
        LOG.debug(">> get('%s')", name)
        try:
            LOG.debug(SCREENS[name])
            return SCREENS[name]
        except KeyError:
            LOG.error("Screen '%s' doesn't exists", name)
            abort(404)

    def post(self, name):
        """Create a new screen."""
        LOG.debug(">> post('%s')", name)

        # build the new screen
        args = self.parser.parse_args()
        screen = SimpleNamespace(
            name = name,
            addr = args['addr'],
            http_port = args['http_port'],
            rtp_port = args['rtp_port'])

        # check if screen's name was already taken
        if name in SCREENS:
            message = "Screen name '%s' was already taken" % screen.name
            LOG.error(message)
            abort(409, message=message)

        # persisting object
        SCREENS[name] = screen
        LOG.debug(screen)
        LOG.info("New screen '%s' created", screen.name)

        # created, success
        return screen.name, 201

    def delete(self, name):
        """Delete a screen."""
        LOG.debug(">> delete('%s')", name)

        try:
            scr = SCREENS.pop(name)
            LOG.debug(scr)
            LOG.info("Screen '%s' was removed from server", name)
        except KeyError:
            LOG.error("Screen '%s' doesn't exists", name)
            abort(404)

        # delete associated routes
        for route in [r for r in ROUTES if r.screen == scr.name]:
            cam = CAMERAS[route.camera]
            ROUTES.remove(route)

            try:
                post('http://{}:{}/remove'.format(cam.addr, cam.http_port),
                     data={'addr': scr.addr, 'rtp_port': scr.rtp_port})
                LOG.info("Removed route %r", route)
            except TelecorpoException as ex:
                LOG.error(str(ex))
                LOG.error("Failed to remove route %r", route)

        # tells screen to exit
        # XXX this may fail if who requested the deletion was the screen itself
        try:
            delete('http://{}:{}'.format(scr.addr, scr.http_port))
            LOG.warn("Hopefully the screen was closed. NO guarantees")
        except TelecorpoException:
            pass

        # ok, success
        return '', 200


class ScreenListResource(Resource):
    """Handle requests relative to all cameras."""
    endpoint = '/screens'
    def get(self):
        """List all screens."""
        LOG.debug(">> get()")
        return SCREENS, 200


