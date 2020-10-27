from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Mapping, MutableMapping, Optional

from torrentool.torrent import Torrent as ExternalTorrent

from clutchless.external.filesystem import Filesystem


@dataclass
class TorrentFile:
    path: Path
    length: int


def convert_file(file: Mapping) -> TorrentFile:
    """Takes a mapping from a list in 'info' and converts into TorrentFile"""
    return TorrentFile(Path(*file["path"]), file["length"])


class MetainfoFile:

    PROPERTIES = ["name", "info_hash"]

    def __init__(self, properties: MutableMapping):
        self._properties = properties

    @classmethod
    def from_path(cls, path: Path) -> "MetainfoFile":
        external_torrent = ExternalTorrent.from_file(str(path))
        torrent_file = MetainfoFile({})
        for prop in cls.PROPERTIES:
            torrent_file._properties[prop] = getattr(external_torrent, prop)
        torrent_file._properties["info"] = (
            external_torrent._struct.get("info") or dict()
        )
        return torrent_file

    @property
    def name(self) -> str:
        return self._properties["name"]

    @property
    def info_hash(self) -> str:
        return self._properties["info_hash"]

    @property
    def files(self) -> Sequence[TorrentFile]:
        files = self.info.get("files")
        return [convert_file(file) for file in files]

    @property
    def info(self) -> Mapping:
        return self._properties["info"]

    @property
    def is_single_file(self) -> bool:
        """Returns whether a torrent is a single-file (flat file structure) torrent.
        reference: https://www.bittorrent.org/beps/bep_0003.html
        """
        is_length_present = "length" in self.info
        is_files_present = "files" in self.info
        self.__validate_file_torrent_check(is_length_present, is_files_present)
        return is_length_present

    @staticmethod
    def __validate_file_torrent_check(is_length_present: bool, is_files_present: bool):
        def xnor(a: bool, b: bool) -> bool:
            return a and b or not a and not b

        if xnor(is_length_present, is_files_present):
            raise ValueError(
                "must contain either length key or files key, not both or neither"
            )

    def verify(self, fs: Filesystem, path: Path) -> bool:
        if self.is_single_file:
            filepath = path / self.name
            return fs.is_file(filepath)
        else:

            def verify(file: TorrentFile) -> bool:
                return fs.is_file(path / self.name / file.path)

            verifieds = [verify(file) for file in self.files]
            return all(verifieds)

    def find(self, fs: Filesystem, path: Path) -> Optional[Path]:
        is_file = self.is_single_file
        found = fs.find(path, self.name, is_file)
        if found and self.verify(fs, found):
            return path

    def __str__(self):
        return f"{self.name}"

    def __eq__(self, other):
        """
        There's an assumption about temporality here - namely that a file won't be updated at some point.

        Creating a MetainfoFile from the same path, that yielded the same hash_string but different metainfo would be an
        issue.
        """
        if isinstance(other, MetainfoFile):
            return other.info_hash == self.info_hash
        else:
            return False

    def __hash__(self):
        return hash(self.info_hash)
