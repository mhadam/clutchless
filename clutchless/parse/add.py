""" Add torrents to Transmission (with or without data).

Usage:
    clutchless add [--dry-run] [--delete] [-f | --force] <torrents> ... [-d <data> ...]

Arguments:
    <torrents>  Torrent files (.torrent) to add to Transmission.

Options:
    -d <data> ...   Data to associate to torrents.
    -f, --force     Add torrents even when they're not found.
    --delete        Delete successfully added torrents (meaningless when used with --dry-run).
    --dry-run       Output what would be done instead of modifying anything.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Set

from clutchless.parse.shared import parse_torrent_files, parse_data_dirs
from clutchless.search import TorrentSearch


@dataclass
class AddArgs:
    torrent_files: Set[Path]
    data_dirs: Set[Path]
    torrent_search: TorrentSearch


def parse_add(args: Mapping) -> AddArgs:
    torrent_files = parse_torrent_files(args["<torrents>"])
    data_dirs = parse_data_dirs(args.get("-d"))

    torrent_search = TorrentSearch()
    torrent_search += torrent_files
    return AddArgs(torrent_files, data_dirs, torrent_search)
