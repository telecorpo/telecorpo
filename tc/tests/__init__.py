
from mock import MagicMock
from twisted.internet import reactor
from twisted.trial import unittest


class TestCase(unittest.TestCase):

    def setUp(self):
        reactor.stop = MagicMock()

