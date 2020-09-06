from hashlib import sha1
from io import RawIOBase, BufferedReader
from pathlib import Path
from threading import Event
from typing import Optional, Sequence, Mapping

from clutchless.torrent import MetainfoFile


# todo: refactor with alternate constructor
from clutchless.transmission import PartialTorrent


class FilesStream(RawIOBase):
    def __init__(self, files: Sequence[Path]):
        def get_streams():
            for file in files:
                yield open(str(file), "rb")

        self.file_iter = iter(get_streams())
        try:
            self.file = next(self.file_iter)
        except StopIteration:
            self.file = None

    def readable(self) -> bool:
        return True

    def _read_from_stream(self, max_size) -> bytes:
        if self.file is not None:
            return self.file.read(max_size)
        else:
            return b""

    def readinto(self, __buffer: bytearray) -> Optional[int]:
        buffer_length = len(__buffer)
        read = self._read_from_stream(buffer_length)
        while read == b"":
            if self.file is not None:
                self.file.close()
            try:
                self.file = next(self.file_iter)
                read = self._read_from_stream(buffer_length)
            except StopIteration:
                self.file = None
                return 0
        result = read[:buffer_length]
        __buffer[: len(result)] = result
        return len(result)


class HashCalculator:
    def __init__(self):
        pass

    def calculate(self, torrent: MetainfoFile, path: Path) -> bytes:
        result = b""
        piece_length = torrent.info["piece length"]
        reader = BufferedReader(
            FilesStream([Path(path, file.path) for file in torrent.files])
        )
        read: bytes = reader.read(piece_length)
        while read != b"":
            result += sha1(read).digest()
            read = reader.read(piece_length)
        return result


class TorrentVerifier:
    def __init__(
        self,
        partial_torrents: Mapping[str, PartialTorrent],
        hash_calculator: HashCalculator,
    ):
        self.partial_torrents = partial_torrents
        self.hash_calculator = hash_calculator

    def verify(self, torrent: MetainfoFile, path: Path) -> bool:
        try:
            hash_string = self.hash_calculator.calculate(torrent, path)
            pieces = torrent.info["pieces"]
            return hash_string is not None and hash_string == pieces
        except KeyError:
            return False
        except FileNotFoundError:
            try:
                partial_torrent = self.partial_torrents[torrent.hash_string]
                return partial_torrent.verify(torrent, path)
            except KeyError:
                pass
