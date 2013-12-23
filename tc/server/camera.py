
from flask.ext.restful  import reqparse, abort, Resource, types
from types              import SimpleNamespace

from tc.utils           import get_logger, ipv4, delete, TelecorpoException


LOG = get_logger(__name__)


class CameraResource(Resource):
    """Handle requests relative a one camera."""

    #: endpoint URL
    endpoint = '/cameras/<string:name>'

    parser = reqparse.RequestParser()
    parser.add_argument('addr', type=ipv4, required=True)
    parser.add_argument('http_port', type=int, required=True)

    def get(self, name):
        """Return an individual camera."""
        LOG.debug(">> get('%s')", name)
        try:
            LOG.debug(CAMERAS[name])
            return CAMERAS[name]
        except KeyError:
            LOG.error("Camera '%s' doesn't exists", name)
            abort(404)

    def post(self, name):
        """Create a new camera."""
        LOG.debug("post()")

        # build the new camera
        args = self.parser.parse_args()
        camera = SimpleNamespace(
            name = name,
            addr = args['addr'],
            http_port = args['http_port'])

        # check if camera's name was already taken
        if name in CAMERAS:
            message = "Camera name '%s' was already taken" % name
            LOG.error(message)
            abort(409, message=message)

        # persisting object
        CAMERAS[name] = camera
        LOG.debug(camera)
        LOG.info("Camera '%s' created", camera.name)

        # created, success
        return camera.name, 201

    def delete(self, name):
        """Delete a camera."""
        LOG.debug(">> delete('%s')", name)

        # delete camera from server
        try:
            cam = CAMERAS.pop(name)
            LOG.debug(cam)
            LOG.info("Camera '%s' was removed from server", cam.name)
        except KeyError:
            LOG.error("Camera '%s' doesn't exists", name)
            abort(404)

        # delete associated routes
        for route in [r for r in ROUTES if r.camera is cam.name]:
            ROUTES.remove(route)
            LOG.info("Removed %s", route)

        # tells camera to exit
        # XXX this may fail if who requested the deletion was the camera itself
        try:
            delete('http://{}:{}'.format(cam.addr, cam.http_port))
            LOG.warn("Hopefully it was closed. NO guarantees")
        except TelecorpoException:
            pass

        # ok, success
        return '', 200


class CameraListResource(Resource):
    """Handle requests relative a all cameras."""
    endpoint = '/cameras'
    def get(self):
        """List all cameras."""
        LOG.debug("get()")
        return CAMERAS, 200

