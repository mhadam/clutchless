""" A tool for working with torrents and their data in the Transmission BitTorrent client.

Usage:
    clutchless [options] [-v ...] <command> [<args> ...]

Options:
    -a <address>, --address <address>   Address for Transmission (default is http://localhost:9091/transmission/rpc).
    -h, --help  Show this screen.
    -v, --verbose   Verbose terminal output (multiple -v increase verbosity).

The available clutchless commands are:
    add         Add torrents to Transmission (with or without data).
    find        Locate data that belongs to torrent files.
    link        For torrents with missing data in Transmission, find the data and fix the location.
    archive     Copy .torrent files from Transmission for backup.
    organize    Migrate torrents to a new location, sorting them into separate folders for each tracker.
    prune       Clean up things in different contexts (files, torrents, etc.).

See 'clutchless help <command>' for more information on a specific command.

"""
import logging
import sys
from typing import Mapping

from docopt import docopt

from clutchless.command.command import (
    CommandResult,
)
from clutchless.command.factory import CommandCreator
from clutchless.external.transmission import clutch_factory, ClutchApi


class Application:
    def __init__(self, args: Mapping):
        self.args = args

    def run(self):
        logging.basicConfig(level=logging.DEBUG)
        clutch_client = clutch_factory(self.args)
        client = ClutchApi(clutch_client)
        command = CommandCreator(self.args, client).get_command()
        result: CommandResult = command.run()
        result.output()


def parse_logging_level(args: Mapping) -> int:
    return args.get("--verbose", 0)


def setup_logging(verbosity):
    base_loglevel = 30
    verbosity = min(verbosity, 2)
    loglevel = base_loglevel - (verbosity * 10)
    logging.basicConfig(level=loglevel, format="%(message)s")


def main():
    try:
        args = docopt(__doc__, options_first=True)

        verbosity = parse_logging_level(args)
        setup_logging(verbosity)

        application = Application(args)
        application.run()
    except Exception as e:
        logging.error(str(e))
        logging.debug("", exc_info=True)
        try:
            sys.exit(e.errno)
        except AttributeError:
            sys.exit(1)
