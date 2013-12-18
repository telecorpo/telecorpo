"""
    tc.screen
    ~~~~~~~~~

    Main screen module.
"""

import flask
import sys

from flask.ext import restful
from flask.ext.restful import reqparse

from tc.client import BaseClient
from tc.streaming import Receiver
from tc.utils import (get_logger, ask, banner, ipv4, ExitResource,
                      VideoWindow, find_free_port)


LOG = get_logger(__name__)


class ScreenClient(BaseClient):
    def __init__(self):
        srv_addr = ask('Server address > ', '127.0.0.1', ipv4)
        srv_port = ask('Server port    > ', 5000, int)
        scr_name = ask('Screen name    > ')
        print()
        super().__init__('screens', scr_name, srv_addr, srv_port)
        self.rtp_port = find_free_port()
     

def main():
    banner()

    # register HTTP resources
    app = flask.Flask(__name__)
    api = restful.Api(app)
    api.add_resource(ExitResource, ExitResource.endpoint) 

    try: 
        # ask user some questions and connect to server
        screen = ScreenClient()
        screen.connect()

        # create video window and start listening for a stream
        xid, queue = VideoWindow.factory(screen.name)
        receiver = Receiver(screen.rtp_port, xid)
        receiver.start()

    except Exception as e:
        LOG.error(e)
        sys.exit(1)
    
    # start server
    LOG.info("Listening RTP/H264 on port %s", screen.rtp_port)
    LOG.info("Listening HTTP on port %s", screen.http_port)
    app.run(port=screen.http_port, debug=False)

if __name__ == '__main__':
    main()
