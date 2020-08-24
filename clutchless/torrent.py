from pathlib import Path
from typing import Sequence, Mapping

from torrentool.torrent import Torrent as ExternalTorrent


class TorrentFile:

    PROPERTIES = ["name", "info_hash", "files", "info", "wanted"]

    def __init__(self, path: Path):
        self.path = path
        self._properties = {}

    @classmethod
    def from_path(cls, path: Path) -> "TorrentFile":
        external_torrent = ExternalTorrent.from_file(str(path))
        torrent_file = TorrentFile(path)
        for prop in cls.PROPERTIES:
            torrent_file._properties[prop] = getattr(external_torrent, prop)
        return torrent_file

    @property
    def name(self) -> str:
        return self._properties["name"]

    @property
    def hash_string(self) -> str:
        return self._properties["info_hash"]

    @property
    def files(self) -> Sequence:
        return self._properties["files"]

    @property
    def info(self) -> Mapping:
        return self._properties["info"]

    @property
    def is_file_torrent(self) -> bool:
        """Returns whether a torrent is a single-file (flat file structure) torrent."""
        return len(self.files) == 1 and len(Path(self.files[0].name).parts) == 1
