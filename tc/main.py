
import sys

from gi.repository import Gtk
from tc import Application


class Main(Application):
    
    glade_file = 'main.glade'

    def on_producer_button_clicked(self, button): 
        Gtk.main_quit()
        window = self.builder.get_object('main-window')
        window.destroy()
        from tc.producer import Producer
        Producer.main()

    def on_viewer_button_clicked(self, button):
        Gtk.main_quit()
        window = self.builder.get_object('main-window')
        window.destroy()
        from tc.viewer import Viewer
        Viewer.main()

def main():
    if len(sys.argv) == 2 and sys.argv[1] == 'server':
        from tc import server
        server.main()
    else:
        Main.main()
