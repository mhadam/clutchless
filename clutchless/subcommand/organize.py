from collections import OrderedDict
from dataclasses import dataclass
from typing import MutableMapping, Set, Sequence, MutableSequence
from urllib.parse import urlparse

from clutch import Client
from clutch.network.rpc.message import Request
from clutch.schema.user.response.torrent.accessor import (
    TorrentAccessorResponse,
    TorrentAccessorObject,
)


@dataclass
class OrganizeTracker:
    index: int
    netloc: str
    addresses: Sequence[str]


def get_ordered_tracker_list() -> Sequence[OrganizeTracker]:
    client = Client()
    trackers: MutableMapping[str, Set[str]] = {}  # maps netloc to tracker addresses
    response: Request[TorrentAccessorResponse] = client.torrent.accessor(
        fields=["id", "name", "trackers"]
    )
    torrents: Sequence[TorrentAccessorObject] = response.arguments.torrents
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

    sorted_trackers = OrderedDict()
    for key in sorted(trackers, reverse=True):
        sorted_trackers[key] = trackers[key]

    tracker_list: MutableSequence[OrganizeTracker] = []
    for (index, (netloc, addresses)) in enumerate(sorted_trackers.items()):
        tracker_list.append(OrganizeTracker(index, netloc, addresses))
    return tracker_list
