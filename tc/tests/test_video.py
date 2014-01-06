
from time import sleep
from tc.common import TCFailure, tk
from tc.video import *
from tc.tests import TestCase

class PipelineTestCase(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.pipe = Pipeline("""
            videotestsrc ! fakesink name=s sync=false
        """)

    def test_get_property(self):
        self.assertEqual(self.pipe.s.sync, False)

    def test_set_property(self):
        self.pipe.s.sync = True
        self.assertEqual(self.pipe.s.sync, True)

    def test_is_started(self):
        self.assertFalse(self.pipe.is_started)
        self.pipe.start()
        self.assertTrue(self.pipe.is_started)
        self.pipe.stop()
        self.assertFalse(self.pipe.is_started)


class StreamingWindowTestCase(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.root = tk.Tk()
        pipe = Pipeline('videotestsrc ! xvimagesink')
        self.win = StreamingWindow(self.root, pipe, 'foo')
        self.win.start()
        self.playing = True

    def tearDown(self):
        if self.playing:
            self.win.stop()
    
    def test_title(self):
        self.assertEqual(self.win.root.wm_title(), 'foo')

    def test_toggle_fullscreen(self):
        # TODO Trigger <Double-Button-1> istead of use toggle_fullscreen()
        #      directly.

        # Double click enable fullscreen?
        # self.win.frame.event_generate('<Double-Button-1>')
        self.win._toggle_fullscreen(None)
        self.root.update()
        self.assertEqual(self.win.root.attributes('-fullscreen'), 0)
        
        # Double click again revert?
        # self.win.frame.event_generate('<Double-Button-1>')
        self.win._toggle_fullscreen(None)
        self.root.update()
        self.assertFalse(self.win.root.attributes('-fullscreen'), 1)
    
    def test_xid(self):
        self.win.start()
        sleep(.1)
        self.assertEquals(self.win.xid, self.win._xid)

