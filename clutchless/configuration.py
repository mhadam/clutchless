import logging
from collections import defaultdict
from pathlib import Path
from typing import Sequence, Set, Mapping, Any, DefaultDict, Callable, Iterable

from docopt import docopt

from clutchless.command.add import AddCommand, LinkingAddCommand
from clutchless.command.archive import ArchiveCommand, ErrorArchiveCommand
from clutchless.command.command import (
    CommandFactory,
    CommandFactoryResult,
    Command,
)
from clutchless.command.dedupe import DedupeCommand
from clutchless.command.find import FindCommand
from clutchless.command.link import LinkCommand, ListLinkCommand
from clutchless.command.organize import (
    ListOrganizeCommand,
    OrganizeCommand,
)
from clutchless.command.other import MissingCommand, InvalidCommand
from clutchless.command.prune.client import PruneClientCommand
from clutchless.command.prune.folder import PruneFolderCommand
from clutchless.domain.torrent import MetainfoFile
from clutchless.external.filesystem import (
    Filesystem,
    FileLocator,
    DryRunFilesystem,
    MultipleDirectoryFileLocator,
)
from clutchless.external.metainfo import (
    MetainfoReader,
    CustomTorrentDataLocator,
    DefaultTorrentDataReader,
    TorrentData,
)
from clutchless.service.file import (
    get_valid_directories,
    collect_metainfo_files,
    collect_metainfo_paths,
)
from clutchless.service.torrent import (
    AddService,
    LinkService,
    LinkDataService,
    FindService,
    OrganizeService,
    PruneService,
    LinkOnlyAddService,
)
from clutchless.spec.find import FindArgs


logger = logging.getLogger(__name__)


def add_factory(argv: Sequence[str], dependencies: Mapping) -> CommandFactoryResult:
    client = dependencies["client"]
    reader: MetainfoReader = dependencies["metainfo_reader"]

    # parse arguments
    from clutchless.spec import add as add_command

    args = docopt(doc=add_command.__doc__, argv=argv)
    fs: Filesystem = dependencies["fs"]
    if not args["--delete"]:
        fs = DryRunFilesystem()

    metainfo_file_paths = collect_metainfo_paths(fs, args["<metainfo>"])
    metainfo_files = {reader.from_path(path) for path in metainfo_file_paths}

    data_directories = get_valid_directories(fs, args["-d"])
    file_locator = MultipleDirectoryFileLocator(data_directories, fs)
    data_reader = DefaultTorrentDataReader(fs)
    data_locator = CustomTorrentDataLocator(file_locator, data_reader)

    add_service = AddService(client)

    # action
    command: Command = AddCommand(add_service, fs, metainfo_files)
    if len(data_directories) > 0:
        find_service = FindService(data_locator)
        if not args["--force"]:
            add_service = LinkOnlyAddService(client)

        torrent_data: Iterable[TorrentData] = find_service.find(metainfo_files)
        response = input("Continue? [Y/N]:")
        if response.strip().lower() != "y":
            raise RuntimeError("User decided not to continue")

        command = LinkingAddCommand(find_service, add_service, fs, torrent_data)
    return command, args


def link_factory(argv: Sequence[str], dependencies: Mapping) -> CommandFactoryResult:
    reader = dependencies["metainfo_reader"]
    client = dependencies["client"]
    fs = dependencies["fs"]

    data_service = LinkDataService(client)
    link_service = LinkService(reader, data_service)

    # parse
    from clutchless.spec import link as link_command

    link_args = docopt(doc=link_command.__doc__, argv=argv)

    data_dirs: Set[Path] = get_valid_directories(fs, link_args.get("<data>"))
    file_locator = MultipleDirectoryFileLocator(data_dirs, fs)
    data_locator = CustomTorrentDataLocator(file_locator, reader)
    find_service = FindService(data_locator)

    if link_args.get("--list"):
        return ListLinkCommand(link_service, find_service), link_args
    return LinkCommand(link_service, find_service), link_args


def find_factory(argv: Sequence[str], dependencies: Mapping) -> CommandFactoryResult:
    reader = dependencies["metainfo_reader"]
    fs: Filesystem = dependencies["fs"]
    locator: FileLocator = dependencies["locator"]

    # parse arguments
    from clutchless.spec import find as find_command

    args = docopt(doc=find_command.__doc__, argv=argv)
    find_args = FindArgs(args, reader, fs, locator)

    data_directories = find_args.get_data_dirs()
    file_locator = MultipleDirectoryFileLocator(data_directories, fs)
    data_reader = DefaultTorrentDataReader(fs)
    data_locator = CustomTorrentDataLocator(file_locator, data_reader)
    service = FindService(data_locator)

    metainfo_files = find_args.get_torrent_files()
    if not metainfo_files:
        raise RuntimeError("Did not find any metainfo files")
    else:
        print(f"Found {len(metainfo_files)} metainfo files:")
        for file in metainfo_files:
            print(f"{file.name} at {file.path.parent}")
    return FindCommand(service, metainfo_files), args


def organize_factory(
    argv: Sequence[str], dependencies: Mapping
) -> CommandFactoryResult:
    client = dependencies["client"]
    reader = dependencies["metainfo_reader"]
    service = OrganizeService(client, reader)
    # parse
    from clutchless.spec import organize as organize_command

    org_args = docopt(doc=organize_command.__doc__, argv=argv)
    # action
    if org_args.get("--list"):
        return ListOrganizeCommand(service), org_args
    else:
        # # clutchless --address http://transmission:9091/transmission/rpc organize --list
        # # clutchless --address http://transmission:9091/transmission/rpc add /app/resources/torrents/ -d /app/resources/data/
        # # clutchless --address http://transmission:9091/transmission/rpc organize /app/resources/new -t "0=Testing"
        raw_spec = org_args.get("-t")
        new_path = Path(org_args.get("<destination>")).resolve(strict=False)
        return OrganizeCommand(raw_spec, new_path, service), org_args


def archive_factory(argv: Sequence[str], dependencies: Mapping) -> CommandFactoryResult:
    client = dependencies["client"]
    fs = dependencies["fs"]
    # parse
    from clutchless.spec import archive as archive_command

    archive_args = docopt(doc=archive_command.__doc__, argv=argv)
    location = Path(archive_args.get("<destination>"))
    errors_option = archive_args.get("--errors")
    if location:
        if errors_option:
            return ErrorArchiveCommand(location, fs, client), archive_args
        else:
            return ArchiveCommand(location, fs, client), archive_args
    return MissingCommand(), archive_args


def dedupe_factory(argv: Sequence[str], dependencies: Mapping) -> CommandFactoryResult:
    fs = dependencies["fs"]
    reader = dependencies["metainfo_reader"]
    # parse
    from clutchless.spec import dedupe as dedupe_command

    dedupe_args = docopt(doc=dedupe_command.__doc__, argv=argv)
    raw_folders = dedupe_args.get("<metainfo>")
    files: Sequence[MetainfoFile] = list(
        collect_metainfo_files(reader, fs, raw_folders)
    )
    if files:
        logger.debug(f"dedupe factory files passed to command {files}")
        return DedupeCommand(fs, files), dedupe_args
    return MissingCommand(), dedupe_args


def prune_folder_factory(
    argv: Sequence[str], dependencies: Mapping
) -> CommandFactoryResult:
    client = dependencies["client"]
    fs = dependencies["fs"]
    reader = dependencies["metainfo_reader"]
    service = PruneService(client)
    from clutchless.spec.prune import folder as prune_folder_command

    prune_args = docopt(doc=prune_folder_command.__doc__, argv=argv)
    raw_folders: Sequence[str] = prune_args.get("<metainfo>")

    metainfo_files: Set[MetainfoFile] = collect_metainfo_files(reader, fs, raw_folders)
    return PruneFolderCommand(service, fs, metainfo_files), prune_args


def prune_client_factory(
    argv: Sequence[str], dependencies: Mapping
) -> CommandFactoryResult:
    client = dependencies["client"]
    service = PruneService(client)
    from clutchless.spec.prune import client as prune_client_command

    prune_args = docopt(doc=prune_client_command.__doc__, argv=argv)
    return PruneClientCommand(service), prune_args


def prune_factory(argv: Sequence[str], dependencies: Mapping) -> CommandFactoryResult:
    from clutchless.spec.prune import main as prune_command

    args = docopt(doc=prune_command.__doc__, options_first=True, argv=argv)
    prune_subcommand = args.get("<command>")
    if prune_subcommand == "folder":
        return prune_folder_factory(argv, dependencies)
    elif prune_subcommand == "client":
        return prune_client_factory(argv, dependencies)
    else:
        # print("Invalid prune subcommand: requires <folder|client>")
        return MissingCommand(), args


class InvalidCommandFactory(CommandFactory):
    def __call__(
        self, argv: Sequence[str], dependencies: Mapping[str, Any]
    ) -> CommandFactoryResult:
        return InvalidCommand(), dict()


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
        "dedupe": dedupe_factory,
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

    def get_command(self, args: Mapping) -> CommandFactoryResult:
        # good to remember that args is a list of arguments
        # here we join together a list of the original command & args without "top-level" options
        command = args.get("<command>")
        factory = command_factories[command]
        argv = [args["<command>"]] + args["<args>"]
        return factory(argv, self.dependencies)
