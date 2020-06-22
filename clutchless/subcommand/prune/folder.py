import os
from pathlib import Path
from typing import Sequence, Set

from clutch.network.rpc.message import Response
from clutch.schema.user.response.torrent.accessor import TorrentAccessorResponse

from clutchless.client import client
from clutchless.parse.shared import parse_torrent_files
from clutchless.search import TorrentSearch


def prune_folders(folders: Sequence[str], dry_run: bool) -> Set[Path]:
    response: Response[TorrentAccessorResponse] = client.torrent.accessor(
        fields=["id", "hash_string"]
    )
    torrent_files: Set[Path] = parse_torrent_files(folders)
    torrents = TorrentSearch()
    torrents += torrent_files
    hash_strings = {torrent.hash_string for torrent in response.arguments.torrents}
    removed: Set[Path] = set()
    for hash_string in hash_strings:
        try:
            paths = torrents.locations[hash_string]
            for path in paths:
                if not dry_run:
                    os.remove(path)
                removed.add(path)
        except KeyError:
            pass
    return removed
