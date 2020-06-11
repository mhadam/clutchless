from dataclasses import dataclass, field
from pathlib import Path
from typing import Set, Sequence, Mapping, MutableSequence, Optional

from clutch.schema.user.method.torrent.action import TorrentActionMethod
from torrentool.torrent import Torrent

from clutchless.client import client
from clutchless.search import TorrentSearch, find


def get_incompletes() -> Sequence[Mapping]:
    response: Mapping = client.torrent.accessor(
        fields=["id", "name", "percent_done", "torrent_file"]
    ).dict(exclude_none=True)
    try:
        response_torrents: Sequence[Mapping] = response["arguments"]["torrents"]
        incomplete_responses = [
            torrent for torrent in response_torrents if torrent["percent_done"] == 0.0
        ]
        return incomplete_responses
    except KeyError:
        return []


@dataclass
class LinkFailure:
    name: str
    result: Optional[str] = None
    matched: bool = True


@dataclass
class LinkSuccess:
    name: str
    location: Path


@dataclass
class LinkResult:
    failures: Sequence[LinkFailure] = field(default_factory=list)
    successes: Sequence[LinkSuccess] = field(default_factory=list)
    no_incompletes: bool = False


def link(data_dirs: Set[Path], dry_run: bool) -> LinkResult:
    incomplete_responses = get_incompletes()
    responses: Mapping[str, Mapping] = {
        Torrent.from_file(torrent["torrent_file"]).info_hash: torrent
        for torrent in incomplete_responses
    }
    if len(incomplete_responses) == 0:
        return LinkResult(no_incompletes=True)

    search = TorrentSearch()
    search += [Path(torrent["torrent_file"]) for torrent in incomplete_responses]
    matches: Mapping[Torrent, Path] = find(search, data_dirs)

    matching_hashes = {match.info_hash for match in matches.keys()}
    failed_hashes = set(responses.keys()) - matching_hashes
    unmatched_names = []
    for failed_hash in failed_hashes:
        torrent = responses[failed_hash]
        torrent_file = Torrent.from_file(torrent["torrent_file"])
        unmatched_names.append(torrent_file.name)

    successes: MutableSequence[LinkSuccess] = []
    failures: MutableSequence[LinkFailure] = []
    failures.extend([LinkFailure(name, matched=False) for name in unmatched_names])
    for (torrent, path) in matches.items():
        torrent_response = responses[torrent.info_hash]
        if not dry_run:
            successes.append(LinkSuccess(torrent.name, path))
        else:
            move_response = client.torrent.move(
                ids=torrent_response["id"], location=str(path.resolve(strict=True))
            )
            if move_response.result != "success":
                failures.append(LinkFailure(torrent.name, move_response.result))
                continue
            verify_response = client.torrent.action(
                ids=torrent_response["id"], method=TorrentActionMethod.VERIFY
            )
            if verify_response.result != "success":
                failures.append(LinkFailure(torrent.name, verify_response.result))
                continue
            else:
                successes.append(LinkSuccess(torrent.name, path))
    return LinkResult(failures, successes)
