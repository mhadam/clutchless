import os
from collections import defaultdict, UserDict
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import Set, Mapping, MutableMapping, MutableSet, Sequence, Iterable

from clutch.network.rpc.message import Request
from clutch.schema.user.response.torrent.accessor import (
    TorrentAccessorResponse,
    TorrentAccessorObject,
)
from torrentool.torrent import Torrent

from clutchless.verify import calculate_hash


@dataclass
class WantedFile:
    name: str
    wanted: bool


class PartialTorrents:
    def __init__(self):
        self.hashes: MutableMapping[str, str] = {}  # hash_string, name
        self.responses: MutableMapping[
            str, Sequence[WantedFile]
        ] = {}  # maps hash_string to wanted/files sequence
        request: Sequence[TorrentAccessorObject] = self.request()
        self.process(request)

    def process(self, request: Sequence[TorrentAccessorObject]):
        for torrent in request:
            self.hashes[torrent.name] = torrent.hash_string
            self.responses[torrent.hash_string] = self.collect_wanted(torrent)

    @staticmethod
    def collect_wanted(torrent: TorrentAccessorObject) -> Sequence[WantedFile]:
        wanted_files = []
        for (file, wanted) in zip(torrent.files, torrent.wanted):
            wanted_files.append(WantedFile(file.name, wanted))
        return wanted_files

    @staticmethod
    def request() -> Sequence[TorrentAccessorObject]:
        response: Request[TorrentAccessorResponse] = client.torrent.accessor(
            fields=["files", "wanted", "hash_string"]
        )
        return response.arguments.torrents

    @staticmethod
    def is_incomplete(file: WantedFile, location: Path):
        return file.wanted and not Path(location, file.name).exists()

    def verify(self, torrent: Torrent, location: Path) -> bool:
        try:
            if self.hashes[torrent.info_hash] == torrent.name:
                is_incomplete = partial(self.is_incomplete, location=location)
                return any(filter(is_incomplete, self.responses[torrent.info_hash]))
        except KeyError:
            return False


@dataclass
class TorrentTuple:
    path: Path
    torrent: Torrent


@dataclass
class TorrentRegisterEntry:
    """An entry in the TorrentRegister - stores all found copies of a .torrent file and one is selected.

    The set of torrents in the `torrents` field includes `selected`.
    """

    selected: TorrentTuple
    torrents: MutableSet[TorrentTuple] = field(default_factory=set)


class TorrentRegister(UserDict, MutableMapping[str, TorrentRegisterEntry]):
    def __init__(self, torrents: Set[Path]):
        super().__init__()
        for torrent in torrents:
            self.__register(torrent)

    def __register(self, path: Path):
        """Takes a known torrent path, and stores it for later retrieval (stored with Torrent object)."""
        torrent = Torrent.from_file(str(path))
        torrent_tuple = TorrentTuple(path, torrent)
        self[torrent.info_hash] = TorrentRegisterEntry(torrent_tuple, {torrent_tuple})

    def get_selected(self, torrent_hash: str) -> TorrentTuple:
        return self[torrent_hash].selected

    def get_selected_map(self) -> Mapping[str, TorrentTuple]:
        return {torrent_hash: entry.selected for torrent_hash, entry in self.items()}

    def get_selected_paths(self, torrent_hashes: Set[str]) -> Mapping[str, Path]:
        return {
            torrent_hash: entry.selected.path
            for torrent_hash, entry in self.items()
            if torrent_hash in torrent_hashes
        }


class TorrentSorter:
    """Sorts torrents as either file or folder torrents.

    This is useful for searching. Name of file/folder can be used to return torrent hash.
    Torrent name should correspond to upper level folder or single file name depending on torrent type.
    file_torrents: torrent name -> set[torrent hash]
    folder_torrents: torrent name -> set[torrent hash]
    `{file, folder}_torrents` are defaultdicts so that they return empty sets during search iterations.
    Alternatively could have been handled by EAFP.

    `torrent_entries` should be derived from selected
    """

    def __init__(self, torrent_entries: Mapping[str, TorrentTuple]):
        self.file_torrents: MutableMapping[str, Set[str]] = defaultdict(set)
        self.folder_torrents: MutableMapping[str, Set[str]] = defaultdict(set)
        self.torrent_entries = torrent_entries

    # TODO: Why is this here?
    def __handle(self, torrent_entries: Mapping[str, TorrentTuple]):
        for torrent_hash in torrent_entries.keys():
            torrent = torrent_entries[torrent_hash].torrent
            self.__sort(torrent)

    def __sort(self, torrent: Torrent):
        name = torrent.name
        if is_file_torrent(torrent):
            self.file_torrents[name].add(torrent.info_hash)
        else:
            self.folder_torrents[name].add(torrent.info_hash)

    def find_matches(self, data_dirs: Set[Path]) -> Mapping[str, Path]:
        matches: MutableMapping[str, Path] = {}
        for directory in data_dirs:
            matches.update(self.__find_matches(directory))
        return matches

    def __find_matches(self, directory: Path) -> Mapping[str, Path]:
        found: MutableMapping[str, Path] = {}
        # queue: Queue = Queue(maxsize=10)
        for path, directories, files in os.walk(directory):
            found.update(self.__search(path, files, self.file_torrents))
            found.update(self.__search(path, directories, self.folder_torrents))
        return found

    def __search(
        self, path: Path, items: Iterable, torrents: MutableMapping[str, Set[str]]
    ) -> Mapping[str, Path]:
        found: MutableMapping[str, Path] = {}
        for item in items:
            for torrent_hash in torrents[item]:
                torrent = self.torrent_entries[torrent_hash].torrent
                if torrent_hash not in found and verify(torrent, path):
                    found[torrent_hash] = path
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
