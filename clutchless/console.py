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

See 'clutchless help <command>' for more information on a specific command.

"""
from pathlib import Path
from pprint import pprint
from typing import Set, KeysView, Sequence, Mapping

from docopt import docopt
from torrentool.torrent import Torrent

from clutchless.client import client
from clutchless.message.add import print_add
from clutchless.message.archive import print_archive_count
from clutchless.message.find import print_find
from clutchless.message.link import print_incompletes, print_linked
from clutchless.message.organize import print_tracker_list
from clutchless.parse.add import parse_add
from clutchless.parse.find import parse_find
from clutchless.parse.organize import get_tracker_specs
from clutchless.parse.shared import parse_data_dirs
from clutchless.subcommand.add import AddResult, add
from clutchless.subcommand.archive import archive
from clutchless.subcommand.find import find
from clutchless.subcommand.link import link, get_incompletes, LinkResult
from clutchless.subcommand.organize import get_ordered_tracker_list


def main():
    args = docopt(__doc__, options_first=True)
    # good to remember that argv is a list of arguments
    # here we join together a list of the original command & args without "top-level" options
    argv = [args["<command>"]] + args["<args>"]
    print("args:")
    pprint(args)
    print("argv:")
    pprint(argv)
    command = args.get("<command>")
    address = args.get("--address")
    # clutchless --address http://transmission:9091/transmission/rpc add /app/resources/torrents/ -d /app/resources/data/
    client.set_connection(address=address)
    if command == "add":
        # parse arguments
        from clutchless.parse import add as add_command

        args = docopt(doc=add_command.__doc__, argv=argv)
        print(args)
        add_args = parse_add(args)
        torrent_search, data_dirs = add_args.torrent_search, add_args.data_dirs
        # action
        force = args.get("--force") or len(args.get("-d")) == 0
        add_result: AddResult = add(torrent_search, data_dirs, force)
        # output message
        print_add(add_result)
    elif command == "link":
        # parse
        from clutchless.parse import link as link_command

        link_args = docopt(doc=link_command.__doc__, argv=argv)
        if link_args.get("--list"):
            response: Sequence[Mapping] = get_incompletes()
            print_incompletes(response)
            return
        print("link args")
        print(link_args)
        data_dirs: Set[Path] = parse_data_dirs(link_args.get("<data>"))
        result: LinkResult = link(data_dirs)
        print_linked(result)
    elif command == "find":
        try:
            # parse arguments
            from clutchless.parse import find as find_command

            find_args = parse_find(docopt(doc=find_command.__doc__, argv=argv))
            torrent_search, data_dirs = find_args.torrent_search, find_args.data_dirs
            # action
            matches = find(torrent_search, data_dirs)
            # output message
            torrents: KeysView[Torrent] = find_args.torrent_search.torrents.keys()
            missed: Set[Torrent] = torrents - matches.keys()
            print_find(matches, missed)
        except KeyError as e:
            print(f"failed:{e}")
        except ValueError as e:
            print(f"invalid argument(s):{e}")
    elif command == "organize":
        # parse
        from clutchless.parse import organize as organize_command

        org_args = docopt(doc=organize_command.__doc__, argv=argv)
        print("organize args:")
        pprint(org_args)
        # action
        if org_args.get("--list"):
            tracker_list = get_ordered_tracker_list()
            # output message
            print_tracker_list(tracker_list)
        else:
            trackers_option = org_args.get("-t")
            if trackers_option:
                print(trackers_option)
                try:
                    print(get_tracker_specs(trackers_option))
                except ValueError as e:
                    print(e)
                except IndexError as e:
                    print(f"Invalid formatted tracker spec: {e}")
                # organize()
            else:
                pass
                # organize()
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
