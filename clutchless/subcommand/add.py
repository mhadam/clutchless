from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, MutableMapping, Set, Optional

from clutch.network.rpc.message import Response
from clutch.schema.user.method.torrent.add import TorrentAddArguments
from clutch.schema.user.response.torrent.add import (
    Torrent as ResponseTorrent,
    TorrentAdd,
)
from torrentool.torrent import Torrent

from clutchless.client import client
from clutchless.search import TorrentSearch, find


@dataclass
class AddResult:
    added_torrents: Mapping[Torrent, ResponseTorrent]
    failed_torrents: Mapping[Torrent, str]
    duplicated_torrents: Mapping[Torrent, ResponseTorrent]
    matches: Mapping[Torrent, Path]


def add(torrent_search: TorrentSearch, data_dirs: Set[Path], force: bool) -> AddResult:
    added_torrents: MutableMapping[Torrent, ResponseTorrent] = {}
    duplicated_torrents: MutableMapping[Torrent, ResponseTorrent] = {}
    failed_torrents: MutableMapping[Torrent, str] = {}

    matches: Mapping[Torrent, Path] = find(torrent_search, data_dirs)
    unmatched: Set[Torrent] = torrent_search.torrents.keys() - matches.keys()
    to_add: MutableMapping[Torrent, Optional[Path]] = dict(matches)
    if force:
        to_add.update({key: None for key in unmatched})
    for (torrent, download_dir) in to_add.items():
        response = add_torrent(torrent_search.torrents[torrent], download_dir)
        torrent_added: ResponseTorrent = response.arguments.torrent_added
        torrent_duplicated: ResponseTorrent = response.arguments.torrent_duplicate
        if response.result == "success":
            if torrent_added is not None and len(torrent_added.dict().items()) > 0:
                added_torrents[torrent] = torrent_added
            elif (
                torrent_duplicated is not None
                and len(torrent_duplicated.dict().items()) > 0
            ):
                duplicated_torrents[torrent] = torrent_duplicated
        else:
            failed_torrents[torrent] = response.result
    return AddResult(added_torrents, failed_torrents, duplicated_torrents, matches)


def add_torrent(torrent: Path, download_dir: Path = None) -> Response[TorrentAdd]:
    arguments: TorrentAddArguments = {
        "filename": str(torrent.resolve(strict=True)),
        "paused": True,
    }
    if download_dir:
        arguments["download_dir"] = str(download_dir.resolve(strict=True))
    return client.torrent.add(arguments)
