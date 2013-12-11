import atexit
import flask
import logging
import sys
import types

from flask              import Flask
from flask.ext.restful  import reqparse, abort, Api, Resource
from requests           import get, post, delete, ConnectionError, Timeout

from tc.camera.streamer import Streamer
from tc.utils           import ipv4, get_ip_address, TelecorpoException, \
                               find_free_port, get_logger, print_banner

logger = get_logger(__name__)
camera = types.SimpleNamespace()
server = types.SimpleNamespace()


def ask(prompt, default=None, validator=lambda x: x):
    value = input(prompt).strip()
    if not (value or default):
        raise ValueError('Empty value')
    return validator(value) if value != '' else validator(default)

def connect():
    try:
        server.addr   = ask('Server address > ', '127.0.0.1', ipv4)
        server.port   = ask('Server port    > ', 5000, int)
        camera.source = 'videotestsrc ! video/x-raw,framerate=30/1,width=480,heigth=360'
        camera.source = ask('Source element > ', camera.source)
        camera.name   = ask('Camera name    > ')

    except ValueError as e:
        logger.error(e.message)
        sys.exit(1)

    try:
        logger.debug("Getting camera IP address")
        camera.addr = get_ip_address(server.addr)
        
        logger.debug("Looking for a free port")
        camera.http_port = find_free_port()

        logger.info("Requesting ID for server")
        url = 'http://{}:{}/cameras'.format(server.addr, server.port)
        resp = post(url, timeout=5, data={
            'name'     : camera.name,
            'addr'     : camera.addr,
            'http_port': camera.http_port})

        if not resp.ok:
            logger.error("Error %d: %s. %s", resp.status_code, resp.reason, resp.text)
            sys.exit(1)
        
        logger.info("Camera connected with id %s", id)
        camera.id = resp.text

        logger.info("Camera located at  %s", url)
        server.url = 'http://{}:{}/cameras/{}'.format(server.addr, server.port, camera.id)

        return id, url

    except TelecorpoException as e:
        logger.error(e.message)
    except (ConnectionError, ConnectionRefusedError, Timeout):
        logger.error("Could not connect to server %s on port %d", server.addr, server.port)
    sys.exit(1)

def cleanup(id, url):
    logger.warn("Disconnecting from server")
    resp = delete(url)
    if not resp.ok:
        logger.error(
            'Failed to unregister this camera, server may be in inconsistent state.'
            ' You MUST notify the developers.')

#
# Create HTTP interface
#
app = Flask(__name__)
api = Api(app)



class Resource(Resource):
     
    parser = reqparse.RequestParser()
    parser.add_argument('action', type=str, required=True)
    parser.add_argument('type',  type=str,  required=False)
    parser.add_argument('addr', type=ipv4, required=True)
    parser.add_argument('rtp_port', type=int,  required=True)

    def post(self):
        args = self.parser.parse_args()
        addr = args['addr'] 
        rtp_port = args['rtp_port']

        if args['type'] == 'add':
            logger.info("Starting streaming to %s on port %d", addr, rtp_port)
            flask.g.streamer.add_client(addr, rtp_port)
        elif args['type'] == 'remove':
            logger.info("Stopping streaming to %s on port %d", addr, rtp_port)
            flask.g.streamer.remove_client(addr, rtp_port)
        return '', 200

api.add_resource(Resource, '/')

def main(): 
    print_banner()
    connect()
    atexit.register(cleanup, camera.id, server.url)

    logger.debug("Creating Streamer with source element \"%s\"", camera.source)
    flask.g.streammer = Streamer(camera.source)

    logger.debug("Starting HTTP interface.")
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    app.run(port=camera.http_port)

if __name__ == '__main__':
    main()
