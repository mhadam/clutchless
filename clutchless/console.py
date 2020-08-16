""" A tool for working with torrents and their data in the Transmission BitTorrent client.

Usage:
    clutchless [options] <command> [<args> ...]

Options:
    -a <address>, --address <address>   Address for Transmission (default is http://localhost:9091/transmission/rpc).
    -h, --help  Show this screen.
    --version   Show version.

The available clutchless commands are:
    add         Add torrents to Transmission (with or without data).
    find        Locate data that belongs to torrent files.
    link        For torrents with missing data in Transmission, find the data and fix the location.
    archive     Copy .torrent files from Transmission for backup.
    organize    Migrate torrents to a new location, sorting them into separate folders for each tracker.
    prune       Clean up things in different contexts (files, torrents, etc.).

See 'clutchless help <command>' for more information on a specific command.

"""
from collections import defaultdict
from pathlib import Path
from typing import Set, Mapping

from docopt import docopt

from clutchless.command import Command, CommandResult, CommandFactory
from clutchless.parse.add import parse_add_flags, parse_add_arguments
from clutchless.parse.find import FindArgs
from clutchless.parse.shared import parse_data_dirs
from clutchless.subcommand.add import AddCommand
from clutchless.subcommand.archive import ArchiveCommand
from clutchless.subcommand.find import FindCommand
from clutchless.subcommand.link import LinkCommand, DryRunLinkCommand, ListLinkCommand
from clutchless.subcommand.organize import (
    ListOrganizeCommand, OrganizeCommand,
)
from clutchless.subcommand.other import MissingCommand
from clutchless.transmission import TransmissionApi, clutch_factory


def add_factory(argv: Mapping) -> Command:
    # parse arguments
    from clutchless.parse import add as add_command

    args = docopt(doc=add_command.__doc__, argv=argv)
    add_args = parse_add_arguments(args)
    add_flags = parse_add_flags(args)

    # action
    return AddCommand(add_args, add_flags)


def link_factory(argv: Mapping, client: TransmissionApi) -> Command:
    # parse
    from clutchless.parse import link as link_command

    link_args = docopt(doc=link_command.__doc__, argv=argv)
    if link_args.get("--list"):
        return ListLinkCommand(client)

    data_dirs: Set[Path] = parse_data_dirs(link_args.get("<data>"))
    dry_run = link_args.get("--dry-run")
    torrent_files = client.get_incomplete_torrent_files()
    if dry_run:
        return DryRunLinkCommand(data_dirs, torrent_files, client)
    return LinkCommand(data_dirs, torrent_files, client)


def find_factory(argv: Mapping) -> Command:
    # parse arguments
    from clutchless.parse import find as find_command

    find_args: FindArgs = FindArgs.parse_find(
        docopt(doc=find_command.__doc__, argv=argv)
    )
    return FindCommand(find_args)


def organize_factory(argv: Mapping, client: TransmissionApi) -> Command:
    # parse
    from clutchless.parse import organize as organize_command

    org_args = docopt(doc=organize_command.__doc__, argv=argv)
    # action
    if org_args.get("--list"):
        return ListOrganizeCommand(client)
    else:
        # # clutchless --address http://transmission:9091/transmission/rpc organize --list
        # # clutchless --address http://transmission:9091/transmission/rpc add /app/resources/torrents/ -d /app/resources/data/
        # # clutchless --address http://transmission:9091/transmission/rpc organize /app/resources/new -t "0=Testing"
        raw_spec = org_args.get("-t")
        new_path = Path(org_args.get("<location>")).resolve(strict=False)
        return OrganizeCommand(raw_spec, new_path, client)


def archive_factory(argv: Mapping, client: TransmissionApi) -> Command:
    # parse
    from clutchless.parse import archive as archive_command

    archive_args = docopt(doc=archive_command.__doc__, argv=argv)
    location = Path(archive_args.get("<location>"))
    if location:
        return ArchiveCommand(location, client)
    return MissingCommand()


def prune_factory(argv: Mapping) -> Command:
    from clutchless.parse.prune import main as prune_command

    args = docopt(doc=prune_command.__doc__, options_first=True, argv=argv)
    prune_subcommand = args.get("<command>")
    if prune_subcommand == "folder":
        from clutchless.parse.prune import folder as prune_folder_command

        prune_args = docopt(doc=prune_folder_command.__doc__, argv=argv)
        dry_run: bool = prune_args.get("--dry-run")
        folders: Sequence[str] = prune_args.get("<folders>")
        pruned_folders: Set[Path] = prune_folders(folders, dry_run)
        if dry_run:
            print("The following are dry run results.")
        print_pruned_files(pruned_folders)
    elif prune_subcommand == "client":
        from clutchless.parse.prune import client as prune_client_command

        prune_args = docopt(doc=prune_client_command.__doc__, argv=argv)
        dry_run: bool = prune_args.get("--dry-run")
        result: PrunedResult = prune_client(dry_run)
        print_pruned(result, dry_run)
    else:
        print("Invalid prune subcommand: requires <folder|client>")


class MissingCommandFactory(CommandFactory):
    def __call__(self, *args, **kwargs):
        return MissingCommand


command_factories: Mapping[str, CommandFactory] = defaultdict(
    {
        "add": add_factory,
        "link": link_factory,
        "find": find_factory,
        "organize": organize_factory,
        "archive": archive_factory
    },
    MissingCommandFactory
)


class Application:
    def __init__(self, args: Mapping):
        self.args = args

    def run(self):
        command = self.__get_command()
        result: CommandResult = command.run()
        result.output()

    def __get_command(self) -> Command:
        factory = self.__get_factory()
        argv = self.__get_subcommand_args()
        return self.__create_command(factory, argv)

    def __get_factory(self):
        # good to remember that args is a list of arguments
        # here we join together a list of the original command & args without "top-level" options
        command = self.args.get("<command>")
        return command_factories[command]

    def __get_subcommand_args(self) -> Mapping:
        return [self.args["<command>"]] + self.args["<args>"]

    def __create_command(self, factory: CommandFactory, argv: Mapping) -> Command:
        clutch_client = clutch_factory(self.args)
        client = TransmissionApi(clutch_client)
        try:
            return factory(argv, client)
        except TypeError:
            return factory(argv)


def main():
    args = docopt(__doc__, options_first=True)
    application = Application(args)
    application.run()

