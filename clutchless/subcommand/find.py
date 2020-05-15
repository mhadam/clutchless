from pathlib import Path
from typing import Set, Mapping, MutableMapping

from torrentool.torrent import Torrent

from clutchless.search import TorrentSearch, find_matches


def find(torrent_search: TorrentSearch, data_dirs: Set[Path]) -> Mapping[Torrent, Path]:
    matches: MutableMapping[Torrent, Path] = {}
    for directory in data_dirs:
        matches.update(find_matches(torrent_search, directory))
    return matches
