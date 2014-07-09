
import socket
import sys
import threading
import time

# from tkinter import messagebox

from flask import Flask, request
from flask.ext.restful import reqparse, abort, Api, Resource

app = Flask(__name__)
api = Api(app)

PRODUCERS = {}
PRODUCERS_LOCK = threading.Lock()


class Producers(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('rtsp_mounts', type=lambda v: str(v).split(), required=True)
    parser.add_argument('rtsp_port', type=int, required=True)
    parser.add_argument('ping_port', type=int, required=True)

    def put(self):
        with PRODUCERS_LOCK:
            ipaddr = request.remote_addr
            if ipaddr in PRODUCERS:
                abort(400, message='Producer already connected')
            else:
                args = self.parser.parse_args()
                PRODUCERS[ipaddr] = {
                    'ipaddr': ipaddr,
                    'rtsp_mounts': args['rtsp_mounts'],
                    'rtsp_port': args['rtsp_port'],
                    'ping_port': args['ping_port']
                }
                return PRODUCERS[ipaddr]

    def get(self):
        return PRODUCERS

api.add_resource(Producers, '/')


def janitor():
    while True:
        for producer in PRODUCERS.copy().values():
            time.sleep(0.2)
            import ipdb; ipdb.set_trace()
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    addr = (producer['ipaddr'], producer['ping_port'])
                    sock.connect(addr)
                    assert sock.recv(100) == b'ok'
            except socket.error as err:
                with PRODUCERS_LOCK:
                    del PRODUCERS[producer['ipaddr']]
                    break


if __name__ == '__main__':
    janitor_thread = threading.Thread(target=janitor)
    janitor_thread.start()
    app.run(host='0.0.0.0', port=13370, debug=True)
