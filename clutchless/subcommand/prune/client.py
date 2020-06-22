from dataclasses import dataclass, field
from typing import Sequence, MutableSequence

from clutch.network.rpc.message import Response
from clutch.schema.user.response.torrent.accessor import TorrentAccessorResponse

from clutchless.client import client


@dataclass
class PrunedTorrent:
    error: int
    error_string: str
    id: int
    name: str


@dataclass
class PrunedResult:
    failures: Sequence[PrunedTorrent] = field(default_factory=list)
    successes: Sequence[PrunedTorrent] = field(default_factory=list)


def prune_client(dry_run: bool) -> PrunedResult:
    response: Response[TorrentAccessorResponse] = client.torrent.accessor(
        fields=["id", "error_string", "error", "name"]
    )
    error_torrents = [
        torrent for torrent in response.arguments.torrents if torrent.error == 3
    ]
    failures: MutableSequence[PrunedTorrent] = []
    successes: MutableSequence[PrunedTorrent] = []
    if dry_run:
        for torrent in error_torrents:
            successes.append(
                PrunedTorrent(
                    error=torrent.error,
                    error_string=torrent.error_string,
                    id=torrent.id,
                    name=torrent.name,
                )
            )
    else:
        for torrent in error_torrents:
            remove_response: Response = client.torrent.remove(ids=torrent.id)
            if remove_response.result == "success":
                successes.append(
                    PrunedTorrent(
                        error=torrent.error,
                        error_string=torrent.error_string,
                        id=torrent.id,
                        name=torrent.name,
                    )
                )
            else:
                failures.append(
                    PrunedTorrent(
                        error=torrent.error,
                        error_string=remove_response.result,
                        id=torrent.id,
                        name=torrent.name,
                    )
                )
    return PrunedResult(failures=failures, successes=successes)
