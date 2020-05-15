import os
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Set, Dict, Mapping, MutableMapping

from torrentool.torrent import Torrent

from clutchless.verify import calculate_hash


class PathType(Enum):
    FILE = auto()
    DIRECTORY = auto()


@dataclass
class SearchItem:
    path_type: PathType
    value: str


@dataclass
class TorrentSearch:
    file: Dict[str, Set[Torrent]] = field(default_factory=dict)
    folder: Dict[str, Set[Torrent]] = field(default_factory=dict)
    torrents: Dict[Torrent, Path] = field(default_factory=dict)
    torrent_hashes: Set[Torrent] = field(default_factory=set)

    def __iadd__(self, other):
        if isinstance(other, Path):
            torrent = Torrent.from_file(str(other))
            if torrent.info_hash in self.torrent_hashes:
                return self
            self.torrent_hashes.add(torrent.info_hash)
            self.torrents[torrent] = other
            name = torrent.name
            if is_file_torrent(torrent):
                if name in self.file:
                    self.file[name].add(torrent)
                else:
                    self.file[name] = {torrent}
            else:
                if name in self.folder:
                    self.folder[name].add(torrent)
                else:
                    self.folder[name] = {torrent}
        elif isinstance(other, list) or isinstance(other, set):
            for item in other:
                self.__iadd__(item)
        else:
            raise TypeError(
                f"Cannot assign to {type(self).__name__} with type {type(other).__name__}"
            )
        return self

    def __contains__(self, item) -> bool:
        try:
            return self[item] is not None
        except KeyError:
            return False

    def __getitem__(self, item) -> Set[Torrent]:
        if isinstance(item, SearchItem):
            if item.path_type == PathType.FILE:
                return self.file[item.value]
            if item.path_type == PathType.DIRECTORY:
                return self.folder[item.value]
        else:
            raise KeyError(f"Must access {type(self).__name__} with SearchItem")


def find(torrents: TorrentSearch, data_dirs: Set[Path]) -> Mapping[Torrent, Path]:
    matches: MutableMapping[Torrent, Path] = {}
    for directory in data_dirs:
        matches.update(find_matches(torrents, directory))
    return matches


def find_matches(torrents: TorrentSearch, directory: Path) -> Mapping[Torrent, Path]:
    found: MutableMapping[Torrent, Path] = {}
    for path, directories, files in os.walk(directory):
        for directory in directories:
            try:
                for torrent in torrents[SearchItem(PathType.DIRECTORY, directory)]:
                    if torrent not in found and verify(torrent, path):
                        found[torrent] = Path(path)
            except KeyError:
                pass
        for file in files:
            try:
                for torrent in torrents[SearchItem(PathType.FILE, file)]:
                    if torrent not in found and verify(torrent, path):
                        found[torrent] = Path(path)
            except KeyError:
                pass
    return found


def verify(torrent: Torrent, path: Path) -> bool:
    try:
        hash_string = calculate_hash(torrent, path)
        pieces = torrent._struct["info"]["pieces"]
        return hash_string == pieces
    except KeyError:
        return False


def is_file_torrent(torrent: Torrent) -> bool:
    """Returns whether a torrent is a single-file (flat file structure) torrent."""
    return len(torrent.files) == 1 and len(Path(torrent.files[0].name).parts) == 1


def get_torrent_files(torrent_dir: Path) -> Set[Path]:
    result: Set[Path] = set()
    for root, directories, files in os.walk(torrent_dir.resolve(strict=True)):
        for file in files:
            file_path = Path(root, file)
            if file_path.suffix == ".torrent":
                result.add(file_path)
    return result
