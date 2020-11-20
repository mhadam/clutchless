from collections import defaultdict
from pathlib import Path
from typing import Sequence, Set, Mapping, Any, DefaultDict, Callable

from docopt import docopt

from clutchless.command.add import AddCommand
from clutchless.command.archive import ArchiveCommand
from clutchless.command.command import (
    Command,
    CommandFactory,
)
from clutchless.command.find import FindCommand
from clutchless.command.link import LinkCommand, ListLinkCommand, DryRunLinkCommand
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
from clutchless.domain.torrent import MetainfoFile
from clutchless.external.filesystem import (
    Filesystem,
    DefaultFileLocator,
    FileLocator,
    MultipleDirectoryFileLocator,
)
from clutchless.external.metainfo import (
    TorrentDataLocator,
    CustomTorrentDataLocator,
    DefaultTorrentDataReader,
)
from clutchless.service.file import collect_metainfo_files, collect_metainfo_paths
from clutchless.service.torrent import (
    AddService,
    LinkService,
    LinkDataService,
    FindService,
    OrganizeService,
    PruneService,
)
from clutchless.spec.add import AddArgs, AddFlags
from clutchless.spec.find import FindArgs
from clutchless.spec.shared import PathParser, DataDirectoryParser


def add_factory(argv: Sequence[str], dependencies: Mapping) -> AddCommand:
    fs: Filesystem = dependencies["fs"]
    client = dependencies["client"]

    # parse arguments
    from clutchless.spec import add as add_command

    args = docopt(doc=add_command.__doc__, argv=argv)
    add_args = AddArgs.parse(args)
    add_flags = AddFlags.parse(args)  # todo: fix this; use it?

    locator = DefaultFileLocator(fs)
    metainfo_file_paths: Set[Path] = collect_metainfo_paths(
        fs, locator, add_args.metainfo_files
    )
    add_service = AddService(client)

    # action
    return AddCommand(add_service, fs, metainfo_file_paths)


def link_factory(argv: Sequence[str], dependencies: Mapping) -> Command:
    reader = dependencies["metainfo_reader"]
    client = dependencies["client"]
    fs = dependencies["fs"]

    data_service = LinkDataService(client)
    link_service = LinkService(reader, data_service)

    # parse
    from clutchless.spec import link as link_command

    link_args = docopt(doc=link_command.__doc__, argv=argv)

    data_dirs: Set[Path] = DataDirectoryParser(fs).parse(link_args.get("<data>"))
    file_locator = MultipleDirectoryFileLocator(data_dirs, fs)
    data_reader = DefaultTorrentDataReader(fs)
    data_locator: TorrentDataLocator = CustomTorrentDataLocator(
        file_locator, data_reader
    )
    find_service = FindService(data_locator)

    if link_args.get("--list"):
        return ListLinkCommand(link_service, find_service)

    # data_dirs: Set[Path] = set()
    dry_run = link_args.get("--dry-run")
    if dry_run:
        return DryRunLinkCommand(link_service, find_service)
    return LinkCommand(link_service, find_service)


def find_factory(argv: Sequence[str], dependencies: Mapping) -> Command:
    reader = dependencies["metainfo_reader"]
    fs: Filesystem = dependencies["fs"]
    locator: FileLocator = dependencies["locator"]

    # parse arguments
    from clutchless.spec import find as find_command

    args = docopt(doc=find_command.__doc__, argv=argv)
    find_args = FindArgs(args, reader, fs, locator)

    file_locator = MultipleDirectoryFileLocator(find_args.get_data_dirs(), fs)
    data_reader = DefaultTorrentDataReader(fs)
    data_locator: TorrentDataLocator = CustomTorrentDataLocator(
        file_locator, data_reader
    )
    service = FindService(data_locator)

    return FindCommand(service, find_args.get_torrent_files())


def organize_factory(argv: Sequence[str], dependencies: Mapping) -> Command:
    client = dependencies["client"]
    reader = dependencies["metainfo_reader"]
    service = OrganizeService(client, reader)
    # parse
    from clutchless.spec import organize as organize_command

    org_args = docopt(doc=organize_command.__doc__, argv=argv)
    # action
    if org_args.get("--list"):
        return ListOrganizeCommand(service)
    else:
        # # clutchless --address http://transmission:9091/transmission/rpc organize --list
        # # clutchless --address http://transmission:9091/transmission/rpc add /app/resources/torrents/ -d /app/resources/data/
        # # clutchless --address http://transmission:9091/transmission/rpc organize /app/resources/new -t "0=Testing"
        raw_spec = org_args.get("-t")
        new_path = Path(org_args.get("<location>")).resolve(strict=False)
        return OrganizeCommand(raw_spec, new_path, service)


def archive_factory(argv: Sequence[str], dependencies: Mapping) -> Command:
    client = dependencies["client"]
    fs = dependencies["fs"]
    # parse
    from clutchless.spec import archive as archive_command

    archive_args = docopt(doc=archive_command.__doc__, argv=argv)
    location = Path(archive_args.get("<location>"))
    if location:
        print("returning archive command")
        return ArchiveCommand(location, fs, client)
    return MissingCommand()


def prune_folder_factory(argv: Sequence[str], dependencies: Mapping) -> Command:
    client = dependencies["client"]
    fs = dependencies["fs"]
    locator = dependencies["locator"]
    reader = dependencies["metainfo_reader"]
    service = PruneService(client)
    from clutchless.spec.prune import folder as prune_folder_command

    prune_args = docopt(doc=prune_folder_command.__doc__, argv=argv)
    dry_run: bool = prune_args.get("--dry-run")
    raw_folders: Sequence[str] = prune_args.get("<folders>")
    folder_paths: Set[Path] = PathParser.parse_paths(raw_folders)
    metainfo_files: Set[MetainfoFile] = collect_metainfo_files(
        fs, locator, folder_paths, reader
    )
    if dry_run:
        return DryRunPruneFolderCommand(service, metainfo_files)
    return PruneFolderCommand(service, fs, metainfo_files)


def prune_client_factory(argv: Sequence[str], dependencies: Mapping) -> Command:
    client = dependencies["client"]
    service = PruneService(client)
    from clutchless.spec.prune import client as prune_client_command

    prune_args = docopt(doc=prune_client_command.__doc__, argv=argv)
    dry_run: bool = prune_args.get("--dry-run")
    if dry_run:
        return DryRunPruneClientCommand(service)
    return PruneClientCommand(service)


def prune_factory(argv: Sequence[str], dependencies: Mapping) -> Command:
    from clutchless.spec.prune import main as prune_command

    args = docopt(doc=prune_command.__doc__, options_first=True, argv=argv)
    prune_subcommand = args.get("<command>")
    if prune_subcommand == "folder":
        return prune_folder_factory(argv, dependencies)
    elif prune_subcommand == "client":
        return prune_client_factory(argv, dependencies)
    else:
        # print("Invalid prune subcommand: requires <folder|client>")
        return MissingCommand()


class InvalidCommandFactory(CommandFactory):
    def __call__(self, argv: Sequence[str], dependencies: Mapping[str, Any]) -> Command:
        return InvalidCommand()


invalid_factory: Callable[[], CommandFactory] = InvalidCommandFactory


command_factories: DefaultDict[Any, CommandFactory] = defaultdict(
    invalid_factory,
    {
        "add": add_factory,
        "link": link_factory,
        "find": find_factory,
        "organize": organize_factory,
        "archive": archive_factory,
        "prune": prune_factory,
    },
)


class CommandCreator:
    def __init__(
        self,
        dependencies: Mapping[str, Any],
        factories: Mapping[str, CommandFactory],
    ):
        self.dependencies = dependencies
        self.factories = factories

    def get_command(self, args: Mapping) -> Command:
        # good to remember that args is a list of arguments
        # here we join together a list of the original command & args without "top-level" options
        command = args.get("<command>")
        factory = command_factories[command]
        argv = [args["<command>"]] + args["<args>"]
        return factory(argv, self.dependencies)
