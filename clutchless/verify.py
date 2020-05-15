from hashlib import sha1
from io import RawIOBase, BufferedReader
from pathlib import Path
from typing import Optional, Sequence

from torrentool.torrent import Torrent


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


def calculate_hash(torrent: Torrent, path: Path) -> bytes:
    result = b""
    piece_length = torrent._struct["info"]["piece length"]
    reader = BufferedReader(
        FilesStream([Path(path, file.name) for file in torrent.files])
    )
    read: bytes = reader.read(piece_length)
    while read != b"":
        result += sha1(read).digest()
        read = reader.read(piece_length)
    return result
