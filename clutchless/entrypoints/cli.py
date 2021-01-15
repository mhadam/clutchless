"""A tool for working with torrents and their data in the Transmission BitTorrent client.

Usage:
    clutchless [options] [-v ...] <command> [<args> ...]

Options:
    -a <address>, --address <address>   Address for Transmission (default is http://localhost:9091/transmission/rpc).
    -h, --help  Show this screen.
    -v, --verbose   Verbose terminal output (multiple -v increase verbosity).

The available clutchless commands are:
    add         Add metainfo files to Transmission (with or without data).
    find        Locate data that belongs to metainfo files.
    link        For torrents with missing data in Transmission, find the data and set the location.
    archive     Copy metainfo files from Transmission for backup.
    organize    Migrate torrents to a new location, sorting them into separate folders for each tracker.
    prune       Clean up things in different contexts (files, torrents, etc.).
    dedupe      Delete duplicate metainfo files from paths.

See 'clutchless help <command>' for more information on a specific command.

"""
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Mapping, Any

from colorama import init, deinit
from docopt import docopt

from clutchless.command.command import CommandOutput
from clutchless.configuration import CommandCreator, command_factories
from clutchless.external.filesystem import DefaultFilesystem, SingleDirectoryFileLocator
from clutchless.external.metainfo import DefaultMetainfoReader
from clutchless.external.transmission import clutch_factory, ClutchApi

logger = logging.getLogger(__name__)


class Application:
    def __init__(self, args: Mapping, dependencies: Mapping):
        self.args = args
        self.dependencies = dependencies

    def run(self):
        creator = CommandCreator(self.dependencies, command_factories)
        try:
            command, subcommand_args = creator.get_command(self.args)
        except asyncio.CancelledError:
            print("Cancelled task")
            return
        except Exception as e:
            logger.warning(e, exc_info=True)
            print(e)
            return
        is_dry_run = subcommand_args.get("--dry-run")
        try:
            if is_dry_run is not None and is_dry_run:
                try:
                    result: CommandOutput = command.dry_run()
                    result.dry_run_display()
                except NotImplementedError:
                    print("This command does not have a dry-run mode")
                    return
            else:
                result: CommandOutput = command.run()
                result.display()
        except ConnectionRefusedError:
            print("Connection failed - is Transmission running?")
            return


def parse_logging_level(args: Mapping) -> int:
    return int(args.get("--verbose", 0))


def get_logging_level(verbosity) -> int:
    base_loglevel = 30
    verbosity = min(verbosity, 2)
    return base_loglevel - (verbosity * 10)


def get_file_handler() -> logging.FileHandler:
    cwd_path = Path(os.getcwd())
    log_path_str = str(cwd_path / "clutchless.log")

    file_handler = logging.FileHandler(log_path_str, "w")

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    return file_handler


def get_dependencies(args: Mapping) -> Mapping[str, Any]:
    clutch_client = clutch_factory(args)
    fs = DefaultFilesystem()
    return {
        "client": ClutchApi(clutch_client),
        "fs": fs,
        "locator": SingleDirectoryFileLocator(fs),
        "metainfo_reader": DefaultMetainfoReader(),
    }


def main():
    try:
        args = docopt(__doc__, options_first=True)

        verbosity = parse_logging_level(args)
        level = get_logging_level(verbosity)
        logging.basicConfig(level=level)
        app_logger = logging.getLogger()
        app_logger.handlers = []

        if verbosity > 0:
            handler = get_file_handler()
            app_logger.addHandler(handler)

        dependencies = get_dependencies(args)
        application = Application(args, dependencies)
        init(autoreset=True)
        application.run()
        deinit()
    except Exception as e:
        logging.exception(str(e))
        logging.debug("", exc_info=True)
        try:
            sys.exit(e.errno)
        except AttributeError:
            sys.exit(1)
