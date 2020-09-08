import asyncio
import concurrent.futures
import logging
import os
from asyncio import FIRST_COMPLETED
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Set, Mapping, MutableMapping, Awaitable, Sequence

from clutchless.torrent import MetainfoFile
from clutchless.transmission import TransmissionApi, PartialTorrent
from clutchless.verify import HashCalculator, TorrentVerifier


logger = logging.getLogger()


class TorrentFileStore:
    def __init__(self):
        self.torrents: MutableMapping[str, MetainfoFile] = dict()
        self.duplicates: MutableMapping[str, Set[MetainfoFile]] = defaultdict(set)

    def add(self, torrent_file: MetainfoFile):
        """Takes a known torrent path, and stores it for later retrieval (stored with Torrent object)."""
        hash_string = torrent_file.hash_string
        if hash_string in self.torrents:
            self.duplicates[hash_string].add(torrent_file)
        else:
            self.torrents[hash_string] = torrent_file

    def get_torrent(self, torrent_hash: str) -> MetainfoFile:
        return self.torrents[torrent_hash]

    def get_duplicates(self, torrent_hash: str) -> Set[MetainfoFile]:
        return self.duplicates[torrent_hash]

    def get_torrent_and_duplicates(self, hash_string: str) -> Set[MetainfoFile]:
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
        self._names: Mapping[str, Set[str]] = defaultdict(set)

    def add(self, torrent: MetainfoFile):
        self._names[torrent.name].add(torrent.hash_string)

    def get_torrent_files(self, name: str) -> Set[str]:
        """Returns set of hash strings if found"""
        return self._names[name]


class MissingDataError(Exception):
    pass


class TorrentPathFinder:
    def __init__(self, client: TransmissionApi, data_dirs: Set[Path]):
        self.client = client
        self.data_dirs = data_dirs
        self.partial_torrents: MutableMapping[str, PartialTorrent] = {}

    def find_matching_path_from_dirs(self, torrent_file: MetainfoFile) -> Path:
        for directory in self.data_dirs:
            try:
                return self.__find_match_in_dir(directory, torrent_file)
            except MissingDataError as e:
                pass
        raise MissingDataError()

    def __find_match_in_dir(self, directory: Path, torrent_file: MetainfoFile) -> Path:
        for path, directories, files in os.walk(directory):
            try:
                return self.__find_matching_part(path, files, torrent_file)
            except MissingDataError:
                pass
            try:
                return self.__find_matching_part(path, directories, torrent_file)
            except MissingDataError:
                pass
        raise MissingDataError()

    def __find_matching_part(
        self, path: str, parts: Sequence[str], torrent_file: MetainfoFile
    ) -> Path:
        """Takes a list of parts (folders or files) and returns a verified path."""
        for part in parts:
            if self.__match_path(path, part, torrent_file):
                return Path(path)
        raise MissingDataError()

    def __match_path(self, path: str, part: str, torrent_file: MetainfoFile) -> bool:
        return torrent_file.name == part and torrent_file.is_located_at_path(Path(path))


def __get_torrent_verifier(self) -> TorrentVerifier:
    hash_calculator = HashCalculator()
    return TorrentVerifier(self.partial_torrents, hash_calculator)


@dataclass
class SearchResult:
    found: Mapping[str, Path]
    not_found: Set[str]
    file_store: TorrentFileStore


def search_task(
    client: TransmissionApi, search_dirs: Set[Path], torrent_file: MetainfoFile
) -> Path:
    matcher = TorrentPathFinder(client, search_dirs)
    return matcher.find_matching_path_from_dirs(torrent_file)


class VerifyingTorrentSearcher:
    def __init__(self, client: TransmissionApi):
        self.client = client

    async def get_matches(
        self, torrent_files: Set[MetainfoFile], search_dirs: Set[Path]
    ) -> SearchResult:
        executor = concurrent.futures.ProcessPoolExecutor(max_workers=1)
        futures: MutableMapping[Awaitable, MetainfoFile] = {}
        result: MutableMapping[str, Path] = {}
        for torrent_file in torrent_files:
            future: Awaitable = self.__submit_to_executor(
                executor, search_dirs, torrent_file
            )
            futures[future] = torrent_file
            logger.info(f"task added to queue:{id(future)}")
        task_list = list(futures.keys())
        while task_list:
            done, pending = await asyncio.wait(
                task_list, timeout=1, return_when=FIRST_COMPLETED
            )
            task_list[:] = pending
            for done_task in done:
                try:
                    torrent_file = futures[done_task]
                    task_result = await done_task
                    result[torrent_file.hash_string] = task_result
                    logger.info(
                        f"finished task with id:{id(done_task)}, result:{task_result}"
                    )
                except MissingDataError as e:
                    torrent_file = futures[done_task]
                    logger.error(
                        f"task failed with id:{id(done_task)}, torrent file:{torrent_file}, error:{e}"
                    )
                except KeyError as e:
                    logger.error(
                        f"could not find task with id:{id(done_task)}, error:{e}"
                    )
        return self.__make_search_result(result, torrent_files)

    def __submit_to_executor(
        self, executor, search_dirs: Set[Path], torrent_file: MetainfoFile
    ) -> Awaitable[Path]:
        loop = asyncio.get_running_loop()
        return loop.run_in_executor(
            executor, search_task, self.client, search_dirs, torrent_file
        )

    def __make_search_result(
        self, matches: Mapping[str, Path], torrent_files: Set[MetainfoFile]
    ) -> SearchResult:
        not_found = self.__get_all_hashes(torrent_files) - matches.keys()
        file_store = TorrentFileStore()
        for file in torrent_files:
            file_store.add(file)
        return SearchResult(matches, not_found, file_store)

    def __get_all_hashes(self, torrent_files: Set[MetainfoFile]) -> Set[str]:
        return {torrent.hash_string for torrent in torrent_files}


def name_matching_search_task(
    client: TransmissionApi, search_dirs: Set[Path], torrent_file: MetainfoFile
) -> Path:
    return TorrentPathFinder(client, search_dirs).find_matching_path_from_dirs(
        torrent_file
    )


class NameMatchingTorrentSearcher:
    def __init__(self, client: TransmissionApi):
        self.client = client

    async def get_matches(
        self, torrent_files: Set[MetainfoFile], search_dirs: Set[Path]
    ) -> SearchResult:
        executor = concurrent.futures.ProcessPoolExecutor(max_workers=1)
        futures: MutableMapping[Awaitable, MetainfoFile] = {}
        result: MutableMapping[str, Path] = {}
        for torrent_file in torrent_files:
            future: Awaitable = self.__submit_to_executor(
                executor, search_dirs, torrent_file
            )
            futures[future] = torrent_file
            logger.info(f"task added to queue:{id(future)}")
        task_list = list(futures.keys())
        while task_list:
            done, pending = await asyncio.wait(
                task_list, timeout=1, return_when=FIRST_COMPLETED
            )
            task_list[:] = pending
            for done_task in done:
                try:
                    torrent_file = futures[done_task]
                    task_result = await done_task
                    result[torrent_file.hash_string] = task_result
                    logger.info(
                        f"finished task with id:{id(done_task)}, result:{task_result}"
                    )
                except MissingDataError as e:
                    torrent_file = futures[done_task]
                    logger.error(
                        f"task failed with id:{id(done_task)}, torrent file:{torrent_file}, error:{e}"
                    )
                except KeyError as e:
                    logger.error(
                        f"could not find task with id:{id(done_task)}, error:{e}"
                    )
        return self.__make_search_result(result, torrent_files)

    def __submit_to_executor(
        self, executor, search_dirs: Set[Path], torrent_file: MetainfoFile
    ) -> Awaitable[Path]:
        loop = asyncio.get_running_loop()
        return loop.run_in_executor(
            executor, search_task, self.client, search_dirs, torrent_file
        )

    def __make_search_result(
        self, matches: Mapping[str, Path], torrent_files: Set[MetainfoFile]
    ) -> SearchResult:
        not_found = self.__get_all_hashes(torrent_files) - matches.keys()
        file_store = TorrentFileStore()
        for file in torrent_files:
            file_store.add(file)
        return SearchResult(matches, not_found, file_store)

    def __get_all_hashes(self, torrent_files: Set[MetainfoFile]) -> Set[str]:
        return {torrent.hash_string for torrent in torrent_files}
