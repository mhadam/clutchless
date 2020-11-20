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
from typing import Mapping, Any

from docopt import docopt

from clutchless.command.command import (
    CommandOutput,
)
from clutchless.configuration import CommandCreator, command_factories
from clutchless.external.filesystem import DefaultFilesystem, DefaultFileLocator
from clutchless.external.metainfo import DefaultMetainfoReader
from clutchless.external.transmission import clutch_factory, ClutchApi


class Application:
    def __init__(self, args: Mapping, dependencies: Mapping):
        self.args = args
        self.dependencies = dependencies

    def run(self):
        logging.basicConfig(level=logging.DEBUG)
        command = CommandCreator(self.dependencies, command_factories).get_command(
            self.args
        )
        result: CommandOutput = command.run()
        result.display()


def parse_logging_level(args: Mapping) -> int:
    return args.get("--verbose", 0)


def setup_logging(verbosity):
    base_loglevel = 30
    verbosity = min(verbosity, 2)
    loglevel = base_loglevel - (verbosity * 10)
    logging.basicConfig(level=loglevel, format="%(message)s")


def get_dependencies(args: Mapping) -> Mapping[str, Any]:
    clutch_client = clutch_factory(args)
    fs = DefaultFilesystem()
    return {
        "client": ClutchApi(clutch_client),
        "fs": fs,
        "locator": DefaultFileLocator(fs),
        "metainfo_reader": DefaultMetainfoReader(),
    }


def main():
    try:
        args = docopt(__doc__, options_first=True)

        verbosity = parse_logging_level(args)
        setup_logging(verbosity)

        dependencies = get_dependencies(args)
        application = Application(args, dependencies)
        application.run()
    except Exception as e:
        logging.exception(str(e))
        logging.debug("", exc_info=True)
        try:
            sys.exit(e.errno)
        except AttributeError:
            sys.exit(1)
