
from collections        import namedtuple
from flask.ext.restful  import reqparse, Resource

from tc.utils           import (get_logger, ipv4, post, delete,
                                TelecorpoException)

LOG = get_logger(__name__)
Route = namedtuple('Route', 'camera screen')

class RouteResource(Resource):
    """Handle routes."""

    #: endpoint URL
    endpoint = '/routes/<kind>/<cam_name>/<scr_name>'

    def post(self, kind, cam_name, scr_name):
        """Create a route."""
        LOG.debug(">> post('%s', '%s')", cam_name, scr_name)
        
        if kind not in ['hd', 'ld']:
            LOG.fatal("Route kind '{}' not understood.")
            raise SystemExit

        try:
            cam = CAMERAS[cam_name]
            scr = SCREENS[scr_name]
            route = Route(cam_name, scr_name)
        except KeyError:
            LOG.fatal("Camera '{}' or screen '{}' not found".format(cam_name,
                                                                    scr_name))
            raise SystemExit

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
            url = 'http://{}:{}/{}/remove'.format(affected_cam.addr,
                                                  affected_cam.http_port, kind)
            LOG.debug("Posting %s with data=%r", url, data)
            try:
                post(url, data=data)
                ROUTES.remove(affected)
            except TelecorpoException as ex:
                LOG.error(str(ex))
                LOG.fatal("Failed to remove {}".format(affected))
                raise SystemExit

        elif len(affected) > 1:
            LOG.fatal("Screen '%s' is on more than one route", scr_name)
            raise SystemError

        # clear, now create the route
        try:
            url = 'http://{}:{}/{}/add'.format(cam.addr, cam.http_port, kind)
            post(url, data=scr.__dict__)
            ROUTES.append(route)
        except TelecorpoException as ex:
            LOG.error(str(ex))
            LOG.fatal("Failed to create {}".format(route))
            raise SystemExit

        # ok, success
        LOG.info("%r created", route)
        return '', 200

class RouteListResource(Resource):
    endpoint = '/routes'
    def get(self):
        LOG.debug(">> get()")
        return ROUTES, 200
