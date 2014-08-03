
import ipaddress, os, sys
from gi.repository import GObject, Gst, Gtk


class Application:
    
    glade_file = None

    def __init__(self):
        directory = os.path.dirname(sys.modules['tc'].__file__)
        glade_file = os.path.join(directory, self.glade_file)

        self.builder = Gtk.Builder.new_from_file(glade_file)
        self.builder.connect_signals(self)
        self.window = self.builder.get_object('main-window')
    
    @classmethod
    def main(cls):
        GObject.threads_init()
        Gst.init()

        app = cls()
        app.window.show_all()

        Gtk.main()

    def on_main_window_delete_event(self, *args):
        Gtk.main_quit(*args)

    @staticmethod
    def parse_address(address):
        address = address.strip()
        try:
            ipaddress.IPv4Address(address)
        except ValueError:
            raise ValueError("'%s' does not appear to be a valid IPv4 address"
                    % address)
        return address

    @property
    def is_connected(self):
        """
        The application is connected if the connection-box was disabled.

        """
        return self.builder.get_object('connection-box').is_sensitive()

    def error(self, message):
        """
        Warns the user about some error.

        """
        dialog = Gtk.MessageDialog(self.window, 0, Gtk.MessageType.ERROR,
                Gtk.ButtonsType.OK, "Error")
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def on_connect_button_clicked(self, button):
        """
        Read address-entry and calls connect(). On a sucessfull
        connection the connection-box is disabled.

        """
        try:
            address = self.builder.get_object('address-entry')
            address = self.parse_address(address.get_text())
        except ValueError as err:
            self.error(str(err))
            return
        try:
            self.connect(address)
        except Exception as err:
            self.error("Couldn't connect to server.\n%s" % err)
            return
        connection_box = self.builder.get_object('connection-box')
        connection_box.set_sensitive(False)

    def connect(self, address):
        pass


