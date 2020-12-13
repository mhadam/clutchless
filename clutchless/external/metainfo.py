import asyncio
from asyncio import FIRST_COMPLETED
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Optional, AsyncIterable, Iterable

from torrentool.torrent import Torrent as ExternalTorrent

from clutchless.domain.torrent import MetainfoFile
from clutchless.external.filesystem import (
    Filesystem,
    FileLocator,
    SingleDirectoryFileLocator,
)


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
    async def find(self, file: MetainfoFile) -> TorrentData:
        """Returns parent path that contains file/directory named by metainfo name property."""
        raise NotImplementedError

    async def find_many(
        self, files: Iterable[MetainfoFile]
    ) -> AsyncIterable[TorrentData]:
        raise NotImplementedError


class CustomTorrentDataLocator(TorrentDataLocator):
    def __init__(self, locator: FileLocator, reader: TorrentDataReader):
        self.locator = locator
        self.reader = reader

    async def find_many(
        self, files: Iterable[MetainfoFile]
    ) -> AsyncIterable[TorrentData]:
        pending = {self.find(file) for file in files}
        while pending:
            done, pending = await asyncio.wait(pending, return_when=FIRST_COMPLETED)
            for d in done:
                yield d.result()

    async def find(self, file: MetainfoFile) -> TorrentData:
        if file.is_multifile:
            found = await self.locator.locate_directory(file.name)
        else:
            found = await self.locator.locate_file(file.name)
        if found is not None:
            if self.reader.verify(found, file):
                return TorrentData(file, found)
        return TorrentData(file)


class DefaultTorrentDataLocator(CustomTorrentDataLocator):
    def __init__(self, fs: Filesystem, path: Path = None):
        self.path = path
        reader = DefaultTorrentDataReader(fs)
        locator = SingleDirectoryFileLocator(fs, path)
        super().__init__(locator, reader)

    async def find(self, file: MetainfoFile) -> TorrentData:
        return await super().find(file)

    async def find_many(
        self, files: Iterable[MetainfoFile]
    ) -> AsyncIterable[TorrentData]:
        async for result in super().find_many(files):
            yield result
