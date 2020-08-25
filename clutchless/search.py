import asyncio
import concurrent.futures
import os
from collections import defaultdict
from pathlib import Path
from threading import Event
from typing import Set, Mapping, MutableMapping, Iterable

from clutchless.torrent import TorrentFile
from clutchless.transmission import TransmissionApi, PartialTorrent
from clutchless.verify import HashCalculator, TorrentVerifier


class TorrentFileStore:
    def __init__(self):
        self.torrents: MutableMapping[str, TorrentFile] = dict()
        self.duplicates: MutableMapping[str, Set[TorrentFile]] = defaultdict(
            default_factory=set
        )

    def add(self, torrent_file: TorrentFile):
        """Takes a known torrent path, and stores it for later retrieval (stored with Torrent object)."""
        hash_string = torrent_file.hash_string
        if hash_string in self.torrents:
            self.duplicates[hash_string].add(torrent_file)
        else:
            self.torrents[hash_string] = torrent_file

    def get_torrent(self, torrent_hash: str) -> TorrentFile:
        return self.torrents[torrent_hash]

    def get_duplicates(self, torrent_hash: str) -> Set[TorrentFile]:
        return self.duplicates[torrent_hash]

    def get_torrent_and_duplicates(self, hash_string: str) -> Set[TorrentFile]:
        additional = self.duplicates[hash_string]
        try:
            return additional.union({self.torrents[hash_string]})
        except KeyError:
            return additional


class TorrentNameStore:
    """
    need a way to search through filesystem...store by name! -> corresponds to file/folder name in FS

    past version sorted? was that ever necessary?

    name -> set of hashes (could have multiple torrents with same names...assuming really rare though)
    """

    def __init__(self):
        self._names: Mapping[str, Set[str]] = defaultdict(default_factory=set)

    def add(self, torrent: TorrentFile):
        self._names[torrent.name].add(torrent.hash_string)

    def get_torrent_files(self, name: str) -> Set[str]:
        """Returns set of hash strings if found"""
        return self._names[name]


class TorrentDataMatcher:
    def __init__(
        self,
        name_store: TorrentNameStore,
        file_store: TorrentFileStore,
        client: TransmissionApi,
    ):
        self.name_store = name_store
        self.file_store = file_store
        self.client = client
        self.partial_torrents: MutableMapping[str, PartialTorrent] = {}

    async def find_matches(self, data_dirs: Set[Path]) -> Mapping[str, Path]:
        matches: MutableMapping[str, Path] = {}
        self.partial_torrents.update(**self.client.get_partial_torrents())
        for directory in data_dirs:
            found_matches = await self.__find_matches(directory)
            matches.update(found_matches)
        return matches

    async def __find_matches(self, directory: Path) -> Mapping[str, Path]:
        found: MutableMapping[str, Path] = {}
        for path, directories, files in os.walk(directory):
            search_result = await self.__search(path, files)
            found.update(search_result)
            search_result = await self.__search(path, directories)
            found.update(search_result)
        return found

    async def __search(
        self, path: Path, items: Iterable[str]
    ) -> Mapping[str, Path]:
        interrupt_event = Event()
        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            for item in items:
                for torrent_hash in self.name_store.get_torrent_files(item):
                    torrent_file = self.file_store.get_torrent(torrent_hash)
                    verifier = self.__get_torrent_verifier(interrupt_event)
                    is_verified = await loop.run_in_executor(
                        pool, verify_callback, verifier, torrent_file, path
                    )
                    if is_verified:
                        interrupt_event.set()
                        return {torrent_hash: Path(path, item)}
        return {}

    def __get_torrent_verifier(self, interrupt_event: Event) -> TorrentVerifier:
        hash_calculator = HashCalculator(interrupt_event)
        return TorrentVerifier(self.partial_torrents, hash_calculator)


def verify_callback(verifier: TorrentVerifier, torrent_file: TorrentFile, path: Path):
    return verifier.verify(torrent_file, path)
