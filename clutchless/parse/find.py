""" Locate data that belongs to torrent files.

Usage:
    clutchless find <torrents> ... (-d <data> ...)

Arguments:
    <torrents> ...  Filepath of torrent files or directories to search for torrent files.

Options:
    -d <data> ...  Folder(s) to search for data that belongs to the specified torrent files.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Set

from clutchless.parse.shared import parse_torrent_files, parse_data_dirs
from clutchless.search import TorrentSearch


@dataclass
class FindArgs:
    torrent_files: Set[Path]
    data_dirs: Set[Path]
    torrent_search: TorrentSearch


def parse_find(args: Mapping) -> FindArgs:
    torrent_files = parse_torrent_files(args["<torrents>"])
    data_dirs = parse_data_dirs(args["-d"])

    torrent_search = TorrentSearch()
    torrent_search += torrent_files
    return FindArgs(torrent_files, data_dirs, torrent_search)
