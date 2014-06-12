
import logging
import redis
import time
import unittest

from unittest.mock import MagicMock

from tc.messaging import (Connection, TelecorpoException, CameraConnection,
                          ScreenConnection)

class BaseConnectionTest(unittest.TestCase):

    def setUp(self):
        self.server_addr = ('localhost', 6379, 0)
        self.r = redis.StrictRedis(*self.server_addr)
        self.ps = self.r.pubsub(ignore_subscribe_messages=True)
        self.r.flushdb()
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        self.r.flushdb()

    def wait_for_message(self, timeout=0.1, ignore_subscribe_messages=False):
        now = time.time()
        timeout = now + timeout
        while now < timeout:
            message = self.ps.get_message(
                ignore_subscribe_messages=ignore_subscribe_messages)
            if message is not None:
                return message['data'].decode()
            time.sleep(0.01)
            now = time.time()
        return None

class ConnectionTest(BaseConnectionTest):

    def test_registration(self):
        conn = Connection(self.server_addr)
        conn._register('foo')
        self.assertTrue(self.r.sismember('nodes', 'foo'))
    
    def test_registration_lock(self):
        self.r.set('register_lock', 1)
        self.assertRaises(TelecorpoException, self.test_registration)

    def test_registration_duplicated_name(self):
        self.test_registration()
        self.assertRaises(TelecorpoException, self.test_registration)
    
    def test_deregistration(self):
        conn = Connection(self.server_addr)
        conn._register('foo')
        conn._deregister('foo')
        self.assertFalse(self.r.sismember('nodes', 'foo'))


class CameraConnectionTest(BaseConnectionTest):

    def test_registration(self):
        self.ps.subscribe('camera_ready')

        cam = CameraConnection('foo', MagicMock(), self.server_addr)
        cam.register()

        self.assertTrue(self.r.sismember('cameras', 'foo'))
        self.assertEqual(self.wait_for_message(), 'foo')
    
    def test_deregistration(self):
        self.ps.subscribe('camera_deleted')

        cam = CameraConnection('foo', MagicMock(), self.server_addr)
        cam.register()
        cam.deregister()

        self.assertFalse(self.r.sismember('cameras', 'foo'))
        self.assertEqual(self.wait_for_message(), 'foo')

    def test_rouing(self):
        cam = CameraConnection('cam', MagicMock(), self.server_addr)
        scr = ScreenConnection('scr', self.server_addr)
        
        cam.register()
        scr.register()

        cam.on_route('foo', 'scr')
        cam.on_route('cam', 'scr')
        
        self.assertEqual(cam.pipe.add_client.call_count, 1)
        cam.pipe.add_client.assert_called_with('127.0.0.1', 12345)
