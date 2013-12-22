
from collections        import namedtuple
from flask.ext.restful  import reqparse, abort, Resource, types
from requests           import delete, post
from types              import SimpleNamespace
from uuid               import uuid1

from tc.utils           import (get_logger, ipv4, post, delete,
                                TelecorpoException)

LOG = get_logger(__name__)
Route = namedtuple('Route', 'camera screen')

class RouteResource(Resource):
    """Handle routes."""

    #: endpoint URL
    endpoint = '/routes/<cam_name>/<scr_name>'

    def post(self, cam_name, scr_name):
        """Create a route."""
        LOG.debug(">> post('%s', '%s')", cam_name, scr_name)

        try:
            cam = CAMERAS[cam_name]
            scr = SCREENS[scr_name]
            route = Route(cam_name, scr_name)
        except KeyError:
            msg = "Camera '{}' or screen '{}' not found".format(cam_name,
                                                                scr_name)
            LOG.error(msg)
            abort(404, message=msg)

        # take a shortcut if the route was already created
        if route in ROUTES:
            LOG.debug("%s already exists", route)
            return '', 200

        # if screen is active on another route deactivate it
        affected = [r for r in ROUTES if r.screen == scr_name]
        if len(affected) == 1:
            affected = affected[0]
            LOG.debug("Removing the %s", affected)

            affected_cam = CAMERAS[affected.camera]
            affected_scr = SCREENS[affected.screen]
            data = {
                'addr': affected_scr.addr,
                'http_port': affected_scr.http_port
            }
            url = 'http://{}:{}/remove'.format(affected_cam.addr,
                                               affected_cam.http_port)
            LOG.debug("Posting %s with data=%r", url, data)
            try:
                post(url, data=data)
                ROUTES.remove(affected)
            except TelecorpoException as ex:
                LOG.error(str(ex))
                msg = "Failed to remove {}".format(affected)
                LOG.error(msg)
                abort(500,  message=msg)

        # bad error
        elif len(affected) > 1:
            LOG.critical("Screen '%s' is on more than one route", scr_name)

        # clear, now create the route
        try:
            url = 'http://{}:{}/add'.format(cam.addr, cam.http_port)
            post(url, data=scr.__dict__)
            ROUTES.append(route)
        except TelecorpoException as ex:
            LOG.error(str(ex))
            msg = "Failed to create {}".format(route)
            LOG.error(msg)
            abort(500, message=msg)

        # ok, success
        LOG.info("%r created", route)
        return '', 200

class RouteListResource(Resource):
    endpoint = '/routes'
    def get(self):
        LOG.debug(">> get()")
        return ROUTES, 200
