from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Mapping, MutableMapping, Iterable


@dataclass
class TorrentFile:
    path: Path
    length: int


def convert_file(file: Mapping) -> TorrentFile:
    """Takes a mapping from a list in 'info' and converts into TorrentFile"""
    return TorrentFile(Path(*file["path"]), file["length"])


class MetainfoFile:
    PROPERTIES = ["name", "info_hash"]

    def __init__(self, properties: MutableMapping, path: Path = None):
        self.path = path
        self._properties = properties

    @property
    def name(self) -> str:
        return self._properties["name"]

    @property
    def info_hash(self) -> str:
        return self._properties["info_hash"]

    @property
    def files(self) -> Sequence[TorrentFile]:
        """These are defined relative a directory named by 'name' property, i.e. data_location/torrent_name/{file...}"""
        files = self.info.get("files", list())
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

    @property
    def is_multifile(self) -> bool:
        return not self.is_single_file

    @staticmethod
    def __validate_file_torrent_check(is_length_present: bool, is_files_present: bool):
        def xnor(a: bool, b: bool) -> bool:
            return a and b or not a and not b

        if xnor(is_length_present, is_files_present):
            raise ValueError(
                "must contain either length key or files key, not both or neither"
            )

    def root(self, path: Path) -> Path:
        """Returns name appended to a path.
        This would either be a dir/file that contains/is the torrent data.
        """
        return path / self.name

    def needed_files(self, path: Path) -> Iterable[Path]:
        filepath = path / self.name
        if self.is_single_file:
            yield filepath
        else:
            yield from (filepath / file.path for file in self.files)

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
