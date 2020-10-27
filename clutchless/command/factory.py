from collections import defaultdict
from pathlib import Path
from typing import Sequence, Set, Mapping

from docopt import docopt

from clutchless.command.command import Command, CommandFactoryWithoutClient, CommandFactory
from clutchless.external.transmission import TransmissionApi
from clutchless.spec.add import AddArgs, AddFlags
from clutchless.spec.find import FindArgs
from clutchless.spec.shared import PathParser, MetainfoFileCrawler
from clutchless.command.add import AddCommand
from clutchless.command.archive import ArchiveCommand
from clutchless.command.find import FindCommand
from clutchless.command.link import LinkCommand, DryRunLinkCommand, ListLinkCommand
from clutchless.command.organize import (
    ListOrganizeCommand,
    OrganizeCommand,
)
from clutchless.command.other import MissingCommand, InvalidCommand
from clutchless.command.prune.client import PruneClientCommand, DryRunPruneClientCommand
from clutchless.command.prune.folder import (
    PruneFolderCommand,
    DryRunPruneFolderCommand,
)


def add_factory(argv: Sequence[str]) -> Command:
    # parse arguments
    from clutchless.spec import add as add_command

    args = docopt(doc=add_command.__doc__, argv=argv)
    add_args = AddArgs.parse(args)
    add_flags = AddFlags.parse(args)

    # action
    return AddCommand(add_args, add_flags)


def link_factory(argv: Sequence[str], client: TransmissionApi) -> Command:
    # parse
    from clutchless.spec import link as link_command

    link_args = docopt(doc=link_command.__doc__, argv=argv)
    if link_args.get("--list"):
        return ListLinkCommand(client)

    # data_dirs: Set[Path] = parse_data_dirs(link_args.get("<data>"))
    data_dirs: Set[Path] = set()
    dry_run = link_args.get("--dry-run")
    torrent_files = client.get_incomplete_torrent_files()
    if dry_run:
        return DryRunLinkCommand(data_dirs, torrent_files, client)
    return LinkCommand(data_dirs, torrent_files, client)


def find_factory(argv: Sequence[str], client: TransmissionApi) -> Command:
    # parse arguments
    from clutchless.spec import find as find_command

    args = docopt(doc=find_command.__doc__, argv=argv)
    find_args = FindArgs(args, client)
    return FindCommand(find_args)


def organize_factory(argv: Sequence[str], client: TransmissionApi) -> Command:
    # parse
    from clutchless.spec import organize as organize_command

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


def archive_factory(argv: Sequence[str], client: TransmissionApi) -> Command:
    # parse
    from clutchless.spec import archive as archive_command

    archive_args = docopt(doc=archive_command.__doc__, argv=argv)
    location = Path(archive_args.get("<location>"))
    if location:
        print("returning archive command")
        return ArchiveCommand(location, client)
    return MissingCommand()


def prune_folder_factory(argv: Sequence[str], client: TransmissionApi) -> Command:
    from clutchless.spec.prune import folder as prune_folder_command

    prune_args = docopt(doc=prune_folder_command.__doc__, argv=argv)
    dry_run: bool = prune_args.get("--dry-run")
    raw_folders: Sequence[str] = prune_args.get("<folders>")
    folder_paths: Set[Path] = PathParser.parse_paths(raw_folders)
    metainfo_files = MetainfoFileCrawler().crawl(folder_paths)
    if dry_run:
        return DryRunPruneFolderCommand(client, metainfo_files)
    return PruneFolderCommand(client, metainfo_files)


def prune_client_factory(argv: Sequence[str], client: TransmissionApi) -> Command:
    from clutchless.spec.prune import client as prune_client_command

    prune_args = docopt(doc=prune_client_command.__doc__, argv=argv)
    dry_run: bool = prune_args.get("--dry-run")
    if dry_run:
        return DryRunPruneClientCommand(client)
    return PruneClientCommand(client)


def prune_factory(argv: Sequence[str], client: TransmissionApi) -> Command:
    from clutchless.spec.prune import main as prune_command

    args = docopt(doc=prune_command.__doc__, options_first=True, argv=argv)
    prune_subcommand = args.get("<command>")
    if prune_subcommand == "folder":
        return prune_folder_factory(argv, client)
    elif prune_subcommand == "client":
        return prune_client_factory(argv, client)
    else:
        # print("Invalid prune subcommand: requires <folder|client>")
        return MissingCommand()


class InvalidCommandFactory(CommandFactoryWithoutClient):
    def __call__(self, argv: Sequence[str]) -> Command:
        return InvalidCommand()


command_factories: Mapping[str, CommandFactory] = defaultdict(
    lambda: InvalidCommandFactory(),
    {
        "add": add_factory,
        "link": link_factory,
        "find": find_factory,
        "organize": organize_factory,
        "archive": archive_factory,
    },
)


class CommandCreator:
    def __init__(self, args: Mapping, client: TransmissionApi):
        self.args = args
        self.client = client

    def get_command(self) -> Command:
        factory = self.__get_factory()
        argv = self.__get_subcommand_args()
        return self.__create_command(factory, argv)

    def __get_factory(self):
        # good to remember that args is a list of arguments
        # here we join together a list of the original command & args without "top-level" options
        command = self.args.get("<command>")
        return command_factories[command]

    def __get_subcommand_args(self) -> Sequence[str]:
        return [self.args["<command>"]] + self.args["<args>"]

    def __create_command(self, factory: CommandFactory, argv: Sequence[str]) -> Command:
        try:
            return factory(argv, self.client)
        except TypeError:
            return factory(argv)
