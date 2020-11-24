from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Optional

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
    location: Path


class TorrentDataLocator(Protocol):
    def find(self, file: MetainfoFile) -> Optional[TorrentData]:
        """Returns parent path that contains file/directory named by metainfo name property."""
        raise NotImplementedError


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
