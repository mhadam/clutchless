from collections import OrderedDict
from dataclasses import dataclass
from typing import MutableMapping, Set, Sequence, MutableSequence, Mapping
from urllib.parse import urlparse

from clutch.network.rpc.message import Request
from clutch.schema.user.response.torrent.accessor import (
    TorrentAccessorResponse,
    TorrentAccessorObject,
)

from clutchless.client import client


@dataclass
class OrganizeTracker:
    netloc: str
    addresses: Sequence[str]


def query_torrents() -> Sequence[TorrentAccessorObject]:
    response: Request[TorrentAccessorResponse] = client.torrent.accessor(
        fields=["id", "name", "trackers"]
    )
    return response.arguments.torrents


def map_netloc_to_trackers(
    torrents: Sequence[TorrentAccessorObject],
) -> Mapping[str, Set[str]]:
    trackers: MutableMapping[str, Set[str]] = {}  # maps netloc to tracker addresses
    for torrent in torrents:
        for tracker in torrent.trackers:
            hostname = urlparse(tracker.announce).hostname
            try:
                split_hostname = hostname.split(".")
                if len(split_hostname) > 2:
                    split_hostname = hostname.split(".")[1:]
                formatted_hostname = "".join(
                    [word.capitalize() for word in split_hostname]
                )
                try:
                    trackers[formatted_hostname].add(tracker.announce)
                except KeyError:
                    trackers[formatted_hostname] = {tracker.announce}
            except IndexError:
                pass
    return trackers


def get_ordered_tracker_list() -> Sequence[OrganizeTracker]:
    torrents: Sequence[TorrentAccessorObject] = query_torrents()
    trackers: Mapping[str, Set[str]] = map_netloc_to_trackers(torrents)
    sorted_trackers = OrderedDict(sorted(trackers.items()))
    tracker_list: MutableSequence[OrganizeTracker] = []
    for (netloc, addresses) in sorted_trackers.items():
        tracker_list.append(OrganizeTracker(netloc, list(addresses)))
    return tracker_list
