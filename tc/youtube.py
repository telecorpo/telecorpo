
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst

GObject.threads_init()
Gst.init()


class YoutubeStreamer:
    
    _resolutions = {
        '240p': (426, 240, 300, 700, 400),
        '360p': (640, 360, 400, 1000, 750),
        '480p': (854, 480, 500, 2000, 1000),
        '720p': (1280, 720, 1500, 4000, 2500),
        '1080p': (1920, 1080, 3000, 6000, 4500)
    }

    _server_url = 'rtmp://a.rtmp.youtube.com/live2'
    _backup_url = 'rtmp://b.rtmp.youtube.com/live2?backup=1'

    def __init__(self, source, token, resolution, bitrate=None, backup=False):
        if isinstance(source, str):
            self.source = Gst.ElementFactory.make('uridecodebin', None)
            self.source.set_property('uri', source)
        elif isinstance(source, Gst.Element):
            self.source = source
        else:
            raise ValueError("{} must be an URI or Gst.Element".format(source))
        
        if resolution not in self._resolutions:
            message = "{} is not a valid resolution".format(resolution)
            raise ValueError(message)
        self.width = self._resolutions[resolution][0]
        self.height = self._resolutions[resolution][1]
        
        recomended_bitrate = self._resolutions[resolution][4]
        bitrate = bitrate or recomended_bitrate

        min_bitrate = self._resolutions[resolution][2]
        max_bitrate = self._resolutions[resolution][3]
        if not (min_bitrate <= bitrate <= max_bitrate):
            message = "{} do not allow this bitrate ({})".format(resolution,
                                                                 bitrate)
            raise ValueError(message)
        
        self.abitrate = 128
        self.vbitrate = bitrate - self.abitrate
        self.destination = "".join([
            "{}/x/{}".format(self._backup_url if backup else self._server_url,
                             token),
            "?videoKeyframeFrequency=2",
            "&totalDatarate={}".format(bitrate),
            " app=live2",
            " flashVer=FME/3.0%20(compatible;%20FMSc%201.0)",
            " swfUrl={}".format(self._backup_url if backup else self._server_url)
        ])

    def build_pipeline(self):
        video_format = ",".join([
            "video/x-raw",
            "format=I420",
            "pixel-aspect-ratio=1/1",
            "interlace-mode=progressive",
            "width={}".format(self.width),
            "height={}".format(self.height),
        ])

        audio_format = ",".join([
            "audio/x-raw",
            "format=S16LE",
            "endianness=1234",
            "signed=true",
            "width=16",
            "depth=16",
            "rate=44100",
            "channels=1"
        ])

        stream_bin = Gst.parse_bin_from_description("""
            videoconvert ! videoscale ! {video_format} ! queue
            ! x264enc bitrate={self.vbitrate}
                      key-int-max=2
                      bframes=2
                      byte-stream=false
                      aud=true
                      cabac=true
                      tune=zerolatency
            ! h264parse ! video/x-h264,level=(string)4.1,profile=main ! queue
            ! mux.

            audiotestsrc is-live=true wave=silence ! {audio_format}
            ! queue ! voaacenc bitrate={self.abitrate} ! queue ! mux.

            flvmux name=mux streamable=true ! queue
            ! rtmpsink location='{self.destination}'
        """.format(**locals()), True)

        self.pipeline = Gst.Pipeline()
        self.pipeline.add(self.source)
        self.pipeline.add(stream_bin)
        self.source.link(stream_bin)
        def link(*args):
            self.source.link(stream_bin)
        self.source.connect("pad-added", link)

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self.on_message)

    def on_message(self, bus, message):
        if message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print("Error: {} {}".format(err, debug))
            self.pipeline.set_state(Gst.State.NULL)
            import sys
            sys.exit(-1)


    def on_pad_added(self, element, pad, target):
        sinkpad = target.get_compatible_pad(pad, pad.get_current_caps())
        pad.link(sinkpad)

    def start(self):
        self.build_pipeline()
        self.pipeline.set_state(Gst.State.PLAYING)



if __name__ == '__main__':
    # import sys
    import argparse
    from gi.repository import GObject

    Gst.init()
    
    parser = argparse.ArgumentParser(
        formatter_class=lambda prog: argparse.HelpFormatter(prog,
                                                            max_help_position=27))
    parser.add_argument("--backup", action='store_true',
                        help="also stream to backup server")
    parser.add_argument("-t", "--token", type=str, help="youtube stream name")
    parser.add_argument("-r", "--resolution", type=str, default='240p',
            help="eg. 360p, 720p")
    parser.add_argument("-b", "--bitrate", type=int)
    parser.add_argument("uri", type=str, default="v4l2://",
            help="source URI (eg. rtsp://server:8554/video.mp4")
    args = parser.parse_args()
    
    primary = YoutubeStreamer(args.uri, args.token, args.resolution)
    primary.start()

    if args.backup:
        backup = YoutubeStreamer(args.uri, args.token, args.resolution, backup=True)
        backup.start()

    GObject.MainLoop().run()
