from dataclasses import dataclass
from pathlib import Path
from shutil import copy

from clutch.network.rpc.message import Request
from clutch.schema.user.response.torrent.accessor import TorrentAccessorResponse

from clutchless.client import client


@dataclass
class ArchiveCount:
    archived: int
    existing: int


def archive(destination: Path) -> ArchiveCount:
    response: Request[TorrentAccessorResponse] = client.torrent.accessor(
        fields=["torrent_file"]
    )

    def files():
        try:
            torrents = response.dict(exclude_none=True)["arguments"]["torrents"]
            for torrent in torrents:
                yield Path(torrent["torrent_file"])
        except KeyError:
            pass

    if not destination.exists():
        destination.mkdir(parents=True, exist_ok=True)

    existing_count = 0
    copy_count = 0
    for file in iter(files()):
        if Path(destination, file.name).exists():
            existing_count += 1
            continue
        else:
            copy(file, destination)
            copy_count += 1
    return ArchiveCount(copy_count, existing_count)
