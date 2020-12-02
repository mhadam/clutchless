import asyncio
from asyncio import QueueEmpty, Future
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Optional, Set, Tuple, Deque, AsyncIterable

from torrentool.torrent import Torrent as ExternalTorrent

from clutchless.domain.torrent import MetainfoFile
from clutchless.external.filesystem import Filesystem, FileLocator, DefaultFileLocator


class MetainfoReader(Protocol):
    def from_path(self, path: Path) -> MetainfoFile:
        raise NotImplementedError


class DefaultMetainfoReader(MetainfoReader):
    def from_path(self, path: Path) -> MetainfoFile:
        external_torrent = ExternalTorrent.from_file(str(path))
        properties = {
            prop: getattr(external_torrent, prop) for prop in MetainfoFile.PROPERTIES
        }
        properties["info"] = external_torrent._struct.get("info") or dict()
        return MetainfoFile(properties, path)


class TorrentDataReader(Protocol):
    def verify(self, path: Path, file: MetainfoFile) -> bool:
        raise NotImplementedError


class DefaultTorrentDataReader(TorrentDataReader):
    def __init__(self, fs: Filesystem):
        self.fs = fs

    def verify(self, path: Path, metainfo_file: MetainfoFile) -> bool:
        files = set(metainfo_file.needed_files(path))
        return len(files) > 0 and all(self.fs.exists(file) for file in files)


@dataclass(frozen=True)
class TorrentData:
    metainfo_file: MetainfoFile
    location: Optional[Path] = None


class TorrentDataLocator(Protocol):
    def find(self, file: MetainfoFile) -> TorrentData:
        """Returns parent path that contains file/directory named by metainfo name property."""
        raise NotImplementedError


class AsyncTorrentDataLocator:
    def __init__(self, fs: Filesystem, paths: Set[Path] = None):
        self.fs = fs
        if paths is None:
            paths = set()
        self.paths = paths

    async def _worker(self, file: MetainfoFile) -> Tuple[TorrentData, Deque[Path]]:
        queue: Deque[Path] = deque()
        queue.extend(self.paths)
        while len(queue) > 0:
            try:
                await asyncio.sleep(0)
            except asyncio.CancelledError:
                return TorrentData(file), queue
            try:
                item = queue.pop()
            except QueueEmpty:
                return TorrentData(file), queue
            needed: Set[Path] = set(file.needed_files(item))
            children = set(self.fs.children(item))
            if len(needed) > 0 and file.root(item) in children:
                is_all_files_exist = all(self.fs.is_file(path) for path in needed)
                if is_all_files_exist:
                    return TorrentData(file, item), queue
            queue.extendleft(children)
        return TorrentData(file), queue

    @staticmethod
    async def _cancel(futures: Set[Future]) -> Set[Future]:
        for p in futures:
            p.cancel()
        if len(futures) > 0:
            cancel_done, _ = await asyncio.wait(futures)
            return cancel_done
        else:
            return set()

    async def find(
        self, files: Set[MetainfoFile]
    ) -> Tuple[Set[TorrentData], Set[MetainfoFile]]:
        workers = {self._worker(file) for file in files}
        done, pending = await asyncio.wait(workers, timeout=5)
        cancelled = await self._cancel(pending)
        results: Set[TorrentData] = {
            future.result()[0] for future in done.union(cancelled)
        }
        linked: Set[TorrentData] = {
            data for data in results if data.location is not None
        }
        return linked, {data.metainfo_file for data in results - linked}


class DefaultTorrentDataLocator(TorrentDataLocator):
    def __init__(self, fs: Filesystem, path: Path = None):
        file_locator = DefaultFileLocator(fs, path)
        data_reader = DefaultTorrentDataReader(fs)
        self.custom_locator = CustomTorrentDataLocator(file_locator, data_reader)

    def find(self, file: MetainfoFile) -> Optional[TorrentData]:
        return self.custom_locator.find(file)


class CustomTorrentDataLocator(TorrentDataLocator):
    def __init__(self, file_locator: FileLocator, data_reader: TorrentDataReader):
        self.file_locator = file_locator
        self.data_reader = data_reader

    def find(self, file: MetainfoFile) -> Optional[TorrentData]:
        found = self.file_locator.locate(file.name, file.is_multifile)
        if found is not None:
            if self.data_reader.verify(found, file):
                return TorrentData(file, found)
        return None
