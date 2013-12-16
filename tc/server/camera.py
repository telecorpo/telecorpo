
from flask.ext.restful  import reqparse, abort, Resource, types
from requests           import delete
from types              import SimpleNamespace
from uuid               import uuid1

from tc.utils           import get_logger, ipv4

logger = get_logger(__name__)

class CameraResource(Resource):
    """Handle requests relative a one camera."""
    
    #: endpoint URL
    endpoint = '/cameras/<string:id>'
    
    parser = reqparse.RequestParser()
    parser.add_argument('close_client', type=types.boolean)

    def get(self, id):
        """Return an idividual camera."""

        logger.debug("get('%s')", id)
        try:
            logger.debug(CAMERAS[id])
            return CAMERAS[id]
        except KeyError:
            logger.error("Camera with id='%s' doesn't exists", id)
            abort(404)

    def delete(self, id):
        """Delete a camera."""
        logger.debug("delete('%s')", id)
        
        # parse arguments
        args = self.parser.parse_args()
        close_camera = args['close_client']
        if close_camera is None:
            close_camera = True
        
        # wtf, something is wrong on client code
        if id not in CAMERAS:
            logger.error("Camera with id='%s' doesn't exists", id)
            abort(404)
       
        # delete camera from server
        camera = CAMERAS.pop(id)
        logger.debug(camera)
        logger.info("Camera named '%s' was removed from server", camera.name)
        
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

