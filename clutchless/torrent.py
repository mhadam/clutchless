from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Mapping, MutableMapping

from torrentool.torrent import Torrent as ExternalTorrent


@dataclass
class TorrentFile:
    path: str
    length: int


def convert_file(file: Mapping) -> TorrentFile:
    return TorrentFile(Path(*file["path"]), file["length"])


class MetainfoFile:

    PROPERTIES = ["name", "info_hash"]

    def __init__(self, path: Path, properties: MutableMapping):
        self.path = path
        self._properties = properties

    @classmethod
    def from_path(cls, path: Path) -> "MetainfoFile":
        external_torrent = ExternalTorrent.from_file(str(path))
        torrent_file = MetainfoFile(path, {})
        for prop in cls.PROPERTIES:
            torrent_file._properties[prop] = getattr(external_torrent, prop)
        torrent_file._properties["info"] = (
            external_torrent._struct.get("info") or dict()
        )
        external_files = external_torrent._struct.get("info", {}).get("files") or list()
        torrent_file._properties["files"] = cls.__coerce_files(external_files)
        return torrent_file

    @property
    def name(self) -> str:
        return self._properties["name"]

    @property
    def hash_string(self) -> str:
        return self._properties["info_hash"]

    @property
    def files(self) -> Sequence[TorrentFile]:
        return self._properties["files"]

    @classmethod
    def __coerce_files(cls, files: Sequence) -> Sequence[TorrentFile]:
        return [convert_file(file) for file in files]

    @property
    def info(self) -> Mapping:
        return self._properties["info"]

    @property
    def is_single_file(self) -> bool:
        """Returns whether a torrent is a single-file (flat file structure) torrent."""
        # return len(self.files) == 1 and len(Path(self.files[0].path).parts) == 1
        is_length_present = "length" in self.info
        is_files_present = "files" in self.info
        self.__validate_file_torrent_check(is_length_present, is_files_present)
        return is_length_present

    @staticmethod
    def __validate_file_torrent_check(is_length_present: bool, is_files_present: bool):
        if (
            is_length_present
            and is_files_present
            or not is_length_present
            and not is_files_present
        ):
            raise ValueError(
                "must contain either length key or files key, not both or neither"
            )

    def __str__(self):
        return f"{self.path}"

    def is_located_at_path(self, path: Path) -> bool:
        for file in self.files:
            if not Path(path, self.name, file.path).exists():
                return False
        return True
