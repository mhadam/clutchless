from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import MutableMapping, Set, Sequence, MutableSequence, Mapping, Optional
from urllib.parse import urlparse

from clutch.network.rpc.message import Request, Response
from clutch.schema.user.response.torrent.accessor import (
    TorrentAccessorResponse,
    TorrentAccessorObject,
    Tracker,
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


def map_formatted_hostname_to_trackers(
    torrents: Sequence[TorrentAccessorObject],
) -> Mapping[str, Set[str]]:
    """Maps a formatted version of netloc to tracker addresses."""
    trackers: MutableMapping[str, Set[str]] = {}
    for torrent in torrents:
        for tracker in torrent.trackers:
            try:
                hostname = format_hostname(tracker)
                try:
                    trackers[hostname].add(tracker.announce)
                except KeyError:
                    trackers[hostname] = {tracker.announce}
            except IndexError:
                pass
    return trackers


def format_hostname(tracker: Tracker) -> str:
    hostname = urlparse(tracker.announce).hostname
    split_hostname = hostname.split(".")
    if len(split_hostname) > 2:
        split_hostname = hostname.split(".")[1:]
    return "".join([word.capitalize() for word in split_hostname])


def get_ordered_tracker_list() -> Sequence[OrganizeTracker]:
    trackers = get_tracker_list_map()
    sorted_trackers = OrderedDict(sorted(trackers.items()))
    tracker_list: MutableSequence[OrganizeTracker] = []
    for (netloc, addresses) in sorted_trackers.items():
        tracker_list.append(OrganizeTracker(netloc, list(addresses)))
    return tracker_list


def get_tracker_list_map() -> Mapping[str, Set[str]]:
    """Gets formatted_hostname:Set[announce_url] map"""
    torrents: Sequence[TorrentAccessorObject] = query_torrents()
    return map_formatted_hostname_to_trackers(torrents)


def get_tracker_folder_map(overrides: Mapping[str, str] = None) -> Mapping[str, str]:
    """Takes overrides in form announce_url:folder_name"""
    # tracker to folder map (announce URL)
    if overrides is None:
        overrides = {}
    torrents: Sequence[TorrentAccessorObject] = query_torrents()
    trackers: MutableMapping[str, str] = {}  # tracker addresses to folder
    for torrent in torrents:
        for tracker in torrent.trackers:
            hostname = format_hostname(tracker)
            cached = trackers.get(tracker.announce)
            override = overrides.get(tracker.announce)
            if cached is not None:
                if cached != hostname and cached != override:
                    raise ValueError(
                        "duplicate tracker announce url making tracker->hostname map"
                    )
            else:
                if override is not None:
                    trackers[tracker.announce] = override
                else:
                    trackers[tracker.announce] = hostname
    return trackers


def get_overrides(tracker_specs: Mapping[int, str]) -> Mapping[str, str]:
    """Takes index:folder_name and outputs announce_url:folder_name"""
    output: MutableMapping[str, str] = {}
    trackers = get_ordered_tracker_list()
    for (index, spec) in tracker_specs.items():
        tracker: OrganizeTracker = trackers[index]
        for announce_url in tracker.addresses:
            output[announce_url] = spec
    return output


def move_torrent(torrent: TorrentAccessorObject, new_location: Path):
    # print(torrent.name, new_location.resolve(strict=False), torrent.download_dir)
    response: Response = client.torrent.move(
        ids=[torrent.id], location=str(new_location), move=True
    )
    if response.result == "success":
        print(f"Succeeded moving torrent id:{torrent.id} to: {str(new_location)}")
    else:
        print(
            f"Failed moving torrent id:{torrent.id} to:{str(new_location)} error:{response.result}"
        )
