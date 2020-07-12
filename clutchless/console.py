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
from pathlib import Path
from typing import Set, KeysView, Sequence, Mapping, Protocol, Any

from clutch.network.rpc.message import Response
from clutch.schema.user.response.torrent.accessor import TorrentAccessorResponse
from docopt import docopt
from torrentool.torrent import Torrent

from clutchless.client import client
from clutchless.message.add import print_add
from clutchless.message.archive import print_archive_count
from clutchless.message.find import print_find
from clutchless.message.link import print_incompletes, print_linked
from clutchless.message.organize import print_tracker_list
from clutchless.message.prune import print_pruned, print_pruned_files
from clutchless.parse.add import parse_add_flags, parse_add_arguments
from clutchless.parse.find import parse_find, FindArgs
from clutchless.parse.organize import get_tracker_specs, SpecError
from clutchless.parse.shared import parse_data_dirs
from clutchless.subcommand.add import AddResult, AddCommand
from clutchless.subcommand.archive import archive
from clutchless.subcommand.find import FindCommand, FindResult
from clutchless.subcommand.link import link, get_incompletes, LinkResult
from clutchless.subcommand.organize import (
    get_ordered_tracker_list,
    get_tracker_folder_map,
    get_overrides,
    move_torrent,
)
from clutchless.subcommand.prune.client import prune_client, PrunedResult
from clutchless.subcommand.prune.folder import prune_folders


class CommandResult(Protocol):
    """Protocol for command result."""

    def output(self):
        raise NotImplementedError


class Command(Protocol):
    """Protocol for commands."""

    def run(self) -> CommandResult:
        raise NotImplementedError


def main():
    args = docopt(__doc__, options_first=True)
    # good to remember that argv is a list of arguments
    # here we join together a list of the original command & args without "top-level" options
    argv = [args["<command>"]] + args["<args>"]
    command = args.get("<command>")
    address = args.get("--address")
    # clutchless --address http://transmission:9091/transmission/rpc add /app/resources/torrents/ -d /app/resources/data/
    if address:
        client.set_connection(address=address)
    if command == "add":
        # parse arguments
        from clutchless.parse import add as add_command

        args = docopt(doc=add_command.__doc__, argv=argv)
        add_args = parse_add_arguments(args)
        add_flags = parse_add_flags(args)

        # action
        add_command = AddCommand(add_args, add_flags)
        add_result: AddResult = add_command.run()
        add_result.output()
    elif command == "link":
        # parse
        from clutchless.parse import link as link_command

        link_args = docopt(doc=link_command.__doc__, argv=argv)
        if link_args.get("--list"):
            response: Sequence[Mapping] = get_incompletes()
            print_incompletes(response)
            return
        dry_run = link_args.get("--dry-run")
        if dry_run:
            print("These are dry-run results.")
        data_dirs: Set[Path] = parse_data_dirs(link_args.get("<data>"))
        result: LinkResult = link(data_dirs, dry_run)
        print_linked(result)
    elif command == "find":
        try:
            # parse arguments
            from clutchless.parse import find as find_command

            find_args: FindArgs = parse_find(
                docopt(doc=find_command.__doc__, argv=argv)
            )
            command = FindCommand(find_args)
            find_result: FindResult = command.run()
            find_result.output()
        except KeyError as e:
            print(f"failed:{e}")
        except ValueError as e:
            print(f"invalid argument(s):{e}")
    elif command == "organize":
        # parse
        from clutchless.parse import organize as organize_command

        org_args = docopt(doc=organize_command.__doc__, argv=argv)
        # action
        if org_args.get("--list"):
            tracker_list = get_ordered_tracker_list()
            # output message
            print_tracker_list(tracker_list)
        else:
            trackers_option = org_args.get("-t")
            if trackers_option:
                try:
                    tracker_specs = get_tracker_specs(trackers_option)
                except SpecError as e:
                    print(f"Invalid formatted tracker spec: {e}")
                    return
                overrides = get_overrides(tracker_specs)
                tracker_folder_map = get_tracker_folder_map(overrides)
            else:
                tracker_folder_map = get_tracker_folder_map()

            response: Response[TorrentAccessorResponse] = client.torrent.accessor(
                fields=["id", "trackers", "name", "download_dir"]
            )
            # clutchless --address http://transmission:9091/transmission/rpc organize --list
            # clutchless --address http://transmission:9091/transmission/rpc add /app/resources/torrents/ -d /app/resources/data/
            # clutchless --address http://transmission:9091/transmission/rpc organize /app/resources/new -t "0=Testing"
            org_location = org_args.get("<location>")
            for torrent in response.arguments.torrents:
                # organize the torrent when any tracker is found to be mapped to
                found_folder = next(
                    (
                        tracker_folder_map.get(tracker.announce)
                        for tracker in torrent.trackers
                    ),
                    None,
                )
                if found_folder is None:
                    found_folder = org_args.get("-d")
                if found_folder:
                    new_location = Path(org_location, found_folder).resolve(
                        strict=False
                    )
                    if Path(torrent.download_dir) != new_location:
                        move_torrent(torrent, new_location)
                    else:
                        print(
                            f"Already same dir for id:{torrent.id} name:{torrent.name}, ignoring"
                        )
                else:
                    print(
                        f"Didn't move torrent with id:{torrent.id} name:{torrent.name}"
                    )
    elif command == "archive":
        # parse
        from clutchless.parse import archive as archive_command

        archive_args = docopt(doc=archive_command.__doc__, argv=argv)
        location = Path(archive_args.get("<location>"))
        if location:
            # action
            count = archive(Path(location))
            # output message
            print_archive_count(count, location)
    elif command == "prune":
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
            return
