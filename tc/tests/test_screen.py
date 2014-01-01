
from tc.common import tk
from tc.screen import ScreenWindow
from tc.tests import TestCase
from tc.video import Pipeline

class TestScreenWindow(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.root = tk.Tk()
        pipe = Pipeline("videotestsrc ! fakesink")
        self.scr = ScreenWindow(self.root, 1337, 'foo', latency=200)

    def tearDown(self):
        self.scr.stop()

    def test_title(self):
        self.assertEquals(self.scr.title, 'foo - tc-screen')

    def test_increase_latency(self):
        self.scr.frame.event_generate('<Button-4>')
        self.root.update()
        self.assertEquals(self.scr.pipe.buffer.latency, 300)

    def test_decrease_latency(self):
        self.scr.frame.event_generate('<Button-5>')
        self.root.update()
        self.assertEquals(self.scr.pipe.buffer.latency, 100)

