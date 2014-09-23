
import argparse
import ipaddress
import json
import logging
import socket
import time

from gi.repository import GLib, Gst, GstRtsp, GstRtspServer, GUdev, GObject
from .application import Command


LOG = logging.getLogger(__name__)


class BroadcasterException(Exception):
    pass


class Device:
    """Wrapper around GStreamer source element/bin.

    :param name: device identifier
    :param long_name: human friendly description
    :param launch: GStreamer partial launch string

    """
    def __init__(self, name, long_name, launch):
        self.name = name
        self.long_name = long_name
        self.launch = launch
    
    def run_test(self):
        """Tests if this device can be played.

        """
        pipe = Gst.parse_launch("%s ! fakesink" % self.launch)
        pipe.set_state(Gst.State.PLAYING)
        ok = True
        if Gst.StateChangeReturn.FAILURE == pipe.get_state(0)[0]:
            ok = False
        pipe.set_state(Gst.State.NULL)
        return ok
    
    @classmethod
    def find_devices(cls):
        """Returns an iterable of all playable devices found.

        """
        udev = GUdev.Client()
        for dev in udev.query_by_subsystem('video4linux'):
            webcam = Device(dev.get_name(), dev.get_property('ID_V4L_PRODUCT'),
                            "v4l2src device=%s" % dev.get_device_file())
            if webcam.run_test():
                LOG.debug("Found device '%s'" % webcam.name)
                yield webcam
        
        dv1394 = Device("dv1394", "Firewire DV camera",
                        "dv1394src ! dvdemux ! dvdec")
        if dv1394.run_test():
            LOG.debug("Found device '%s'" % dv1394.name)
            yield dv1394
        time.sleep(0.3)        
        yield Device("desktop", "Desktop capture", "ximagesrc")
        yield Device("smpte", "SMPTE color bars", "videotestsrc is-live=true")

    def __repr__(self):
        return 'Device<%s, %s>' % (self.name, self.launch)


class Broadcaster:
    """RTSP server implementation based on gst-rtsp-server.
    
    It requires the default :class:`GObject.MainLoop` running for start
    accepting requests.
    
    For multicast RTP streaming `destination` must be a multicast address
    or subnet (eg. 224.3.0.0/24) and `ttl` greater than zero.

    For unicast RTP streaming `destination` must be an unicast address or
    subnet (eg. 0.0.0.0 or 172.16.0.0/16) and `ttl` equals to zero.

    :param devices: Device names list.
    :param port_range: Port range for firewall rules.
    :param destination: Address or subnet that will receive the stream. 
    :param ttl: Multicast time-to-live.

    """
    def __init__(self, devices, port_range, destination, ttl):

        self.devices = [d for d in Device.find_devices() if d.name in devices]

        self.port_range = int(port_range[0]), int(port_range[1])
        self.destination = ipaddress.IPv4Network(destination)
        self.ttl = int(ttl)
        
        # the first port on range is for RTSP and remaining ones for RTP/RTCP
        self.address_poll = GstRtspServer.RTSPAddressPool()
        if not self.address_poll.add_range(str(min(self.destination)),
               str( max(self.destination)), port_range[0]+1, port_range[1],
               ttl):
            raise BroadcasterException("Invalid port_range/destination/ttl"
                                       " combination.")
        
        self.multicast = True
        if self.address_poll.has_unicast_addresses():
            LOG.warn("Multicast disabled")
            self.multicast = False
    
    def attach(self):
        server = GstRtspServer.RTSPServer()
        server.set_service(str(self.port_range[0]))
        LOG.info("Starting the RTSP server on port %d" % self.port_range[0])
        
        mounts = server.get_mount_points()
        for device in self.devices:
            launch = ("( %s ! queue ! videoconvert ! videoscale ! videorate"
                      " ! video/x-raw,format=I420 ! queue"
                      " ! x264enc speed-preset=ultrafast tune=zerolatency"
                      " ! queue ! rtph264pay pt=96 name=pay0 )"
                      "" % device.launch)
            factory = GstRtspServer.RTSPMediaFactory()
            factory.set_address_pool(self.address_poll)
            factory.set_launch(launch)
            factory.set_shared(True)
            mounts.add_factory("/{}".format(device.name), factory)

        self.server_id = server.attach()
        LOG.info("RTSP server attached")

    def detach(self):
        GLib.source_remove(self.server_id)
        LOG.info("RTSP server detached")


class BroadcastCommand(Command):

    name = "broadcast"
    help = "Small RTSP server"

    @classmethod
    def configure_argument_parser(cls, parser):
        parser.add_argument('-d', '--device',
                nargs='+',
                help='Capture device')
        parser.add_argument('--port-range',
                nargs=2,
                default=(11100, 11198),
                type=int,
                help='Port range for firewall rules')
        parser.add_argument('--destination',
                default=ipaddress.IPv4Network('0.0.0.0'),
                help='Destination address or subnet')
        parser.add_argument('--ttl',
                type=int,
                default=0,
                help='Multicast time-to-live')

    @staticmethod
    def main(args): 
        if args.ttl != 0:
            LOG.warn("--ttl is an experimental feature")

        if  str(args.destination) != "0.0.0.0/32":
            LOG.warn("--destination is an experimental feature")

        if not args.device:
            for device in Device.find_devices():
                print('%10s %20s %s %s' % (device.name, device.long_name, ' '*5,
                    device.launch))
        else:
            devices = args.device
            port_range = sorted(args.port_range)
            destination = args.destination
            ttl = args.ttl
            broadcaster = Broadcaster(args.device, port_range, destination, ttl)
            broadcaster.attach()
            
            # ensures the server keep alive after all clients have disconnected
            hack = " ".join("""
                rtspsrc location=rtsp://127.0.0.1:%d/%s ! fakesink
            """ % (port_range[0], dev) for dev in devices)
            hack = Gst.parse_launch(hack)
            hack.set_state(Gst.State.PLAYING)
            
            try:
                GObject.MainLoop().run()
            except KeyboardInterrupt:
                broadcaster.detach()
                hack.set_state(Gst.State.NULL)


