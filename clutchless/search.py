import os
from asyncio import Queue
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Set, Mapping, MutableMapping, MutableSet, Sequence

from clutch.network.rpc.message import Request
from clutch.schema.user.response.torrent.accessor import (
    TorrentAccessorResponse,
    TorrentAccessorObject,
)
from torrentool.torrent import Torrent

from clutchless.client import client
from clutchless.verify import calculate_hash


@dataclass
class WantedFile:
    name: str
    wanted: bool


@dataclass
class PartialTorrents:
    # hash_string, name
    hashes: MutableMapping[str, str] = field(default_factory=dict)
    # maps hash to wanted/files sequence
    responses: MutableMapping[str, Sequence[WantedFile]] = field(default_factory=dict)

    def __post_init__(self):
        response: Request[TorrentAccessorResponse] = client.torrent.accessor(
            fields=["files", "wanted", "hash_string"]
        )
        torrents: Sequence[TorrentAccessorObject] = response.arguments.torrents
        for torrent in torrents:
            self.hashes[torrent.name] = torrent.hash_string
            wanted_files = []
            for (file, wanted) in zip(torrent.files, torrent.wanted):
                wanted_files.append(WantedFile(file.name, wanted))
            self.responses[torrent.hash_string] = wanted_files

    def verify(self, torrent: Torrent, location: Path) -> bool:
        try:
            if self.hashes[torrent.info_hash] == torrent.name:
                for file in self.responses[torrent.info_hash]:
                    if file.wanted and not Path(location, file.name).exists():
                        return False
        except KeyError:
            return False
        return True


# partial_torrents: PartialTorrents = PartialTorrents()


class PathType(Enum):
    FILE = auto()
    DIRECTORY = auto()


@dataclass
class SearchItem:
    path_type: PathType
    value: str


@dataclass
class TorrentSearch:
    file: MutableMapping[str, Set[Torrent]] = field(default_factory=dict)
    folder: MutableMapping[str, Set[Torrent]] = field(default_factory=dict)
    torrents: MutableMapping[Torrent, Path] = field(default_factory=dict)
    torrent_hashes: MutableSet[str] = field(default_factory=set)
    locations: MutableMapping[str, Set[Path]] = field(default_factory=dict)

    def __iadd__(self, other):
        if isinstance(other, Path):
            torrent = Torrent.from_file(str(other))
            self.torrent_hashes.add(torrent.info_hash)
            try:
                self.locations[torrent.info_hash].add(other)
            except KeyError:
                self.locations[torrent.info_hash] = {other}
            if torrent.info_hash in self.torrent_hashes:
                return self
            self.torrents[torrent] = other
            name = torrent.name
            if is_file_torrent(torrent):
                try:
                    self.file[name].add(torrent)
                except KeyError:
                    self.file[name] = {torrent}
            else:
                try:
                    self.folder[name].add(torrent)
                except KeyError:
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
    queue: Queue = Queue(maxsize=10)
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
    except FileNotFoundError:
        return PartialTorrents().verify(torrent, path)


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
