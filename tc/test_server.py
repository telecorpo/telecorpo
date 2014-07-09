
import json
import unittest
from .server import app, PRODUCERS


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        PRODUCERS.clear()

    def test_zero_producers(self):
        rv = self.app.get('/')
        assert rv.data == b'{}'

    def test_one_producers(self):
        data={
            'ping_port': 1234,
            'rtsp_port': 1234,
            'rtsp_mounts': 'aa bb'
        }
        rv = self.app.put('/', data=data)
        data['rtsp_mounts'] = ['aa', 'bb']
        data['ipaddr'] = None
        assert json.loads(rv.data.decode()) == data

    def test_duplicate_producers(self):
        self.test_one_producers()
        data={
            'ping_port': 1234,
            'rtsp_port': 1234,
            'rtsp_mounts': 'aa bb'
        }
        rv = self.app.put('/', data=data)
        assert json.loads(rv.data.decode()) == {
            "message": "Producer already connected"
        }

if __name__ == '__main__':
    unittest.main()

