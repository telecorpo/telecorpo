
import argparse
import builtins
import importlib
import ipaddress
import logging
import pkgutil
import sys
import time

from urllib.parse import urlparse
from gi.repository import Gst, GObject

Gst.init()
GObject.threads_init()

LOG = logging.getLogger(__name__)

class Command:
    pass


def main():

    # Import each tc.* submodule then Command.__subclasses__() fully populated
    loggers_found = []
    import tc
    for _, name, _ in pkgutil.walk_packages(tc.__path__, 'tc.'):
        module = importlib.import_module(name)
        try:
            loggers_found.append(getattr(module, 'LOG'))
        except AttributeError:
            pass

    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', default=0, action='count',
            help='Increase output verbosity')
    parser.add_argument('-f', '--faulty', default=True, action='store_true')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    subparsers.required = True

    for cmd in Command.__subclasses__():
        cmd_parser = subparsers.add_parser(cmd.name, help=cmd.help)
        cmd.configure_argument_parser(cmd_parser)

    args = parser.parse_args()

    # Configure loggers
    try:
        log_level = [logging.WARNING, logging.INFO, logging.DEBUG][args.verbose]
    except IndexError:
        log_level = logging.DEBUG

    for logger in loggers_found:
        logger.setLevel(log_level)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(levelname)-10s %(name)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # Run command
    for cmd in Command.__subclasses__():
        if cmd.name == args.command:
            try:
                cmd.main(args)
            except KeyboardInterrupt:
                pass
            break
    else:
        assert False, "No command executed"
    
