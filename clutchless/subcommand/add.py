import os
from dataclasses import dataclass, fields, field
from pathlib import Path
from typing import Mapping, MutableMapping, Set, Optional, Sequence, MutableSequence

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
    added_torrents: Mapping[Torrent, str]  # Torrent:rpc_name
    matches: Mapping[Torrent, Path]
    failed_torrents: Optional[Mapping[Torrent, str]] = field(default_factory=dict)
    duplicated_torrents: Optional[Mapping[Torrent, str]] = field(default_factory=dict)
    deleted_torrents: Sequence[Path] = field(default_factory=list)


def add(
    torrent_search: TorrentSearch,
    data_dirs: Set[Path],
    force: bool,
    dry_run: bool,
    delete_added: bool,
) -> AddResult:
    added_torrents: MutableMapping[Torrent, str] = {}
    duplicated_torrents: MutableMapping[Torrent, str] = {}
    failed_torrents: MutableMapping[Torrent, str] = {}
    deleted_torrents: MutableSequence[Path] = []

    matches: Mapping[Torrent, Path] = find(torrent_search, data_dirs)
    unmatched: Set[Torrent] = torrent_search.torrents.keys() - matches.keys()
    to_add: MutableMapping[Torrent, Optional[Path]] = dict(matches)
    if force:
        # add the unmatched - without a download_dir - it'll be default
        to_add.update({key: None for key in unmatched})
    if dry_run:
        fake_added = {torrent: torrent.name for (torrent, path) in to_add.items()}
        add_result = AddResult(added_torrents=fake_added, matches=matches)
        return add_result
    for (torrent, download_dir) in to_add.items():
        response = add_torrent(torrent_search.torrents[torrent], download_dir)
        torrent_added: ResponseTorrent = response.arguments.torrent_added
        torrent_duplicated: ResponseTorrent = response.arguments.torrent_duplicate
        if response.result == "success":
            if torrent_added is not None and len(torrent_added.dict().items()) > 0:
                added_torrents[torrent] = torrent_added.name
                # delete added torrent
                if delete_added:
                    torrent_path = torrent_search.torrents[torrent]
                    os.remove(torrent_path)
                    deleted_torrents.append(torrent_path)
            elif (
                torrent_duplicated is not None
                and len(torrent_duplicated.dict().items()) > 0
            ):
                duplicated_torrents[torrent] = torrent_duplicated.name
        else:
            failed_torrents[torrent] = response.result
    return AddResult(
        added_torrents=added_torrents,
        failed_torrents=failed_torrents,
        duplicated_torrents=duplicated_torrents,
        matches=matches,
        deleted_torrents=deleted_torrents,
    )


def add_torrent(torrent: Path, download_dir: Path = None) -> Response[TorrentAdd]:
    arguments: TorrentAddArguments = {
        "filename": str(torrent.resolve(strict=True)),
        "paused": True,
    }
    if download_dir:
        arguments["download_dir"] = str(download_dir.resolve(strict=True))
    return client.torrent.add(arguments)
