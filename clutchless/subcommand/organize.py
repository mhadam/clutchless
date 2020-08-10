from collections import OrderedDict
from dataclasses import dataclass
from typing import MutableMapping, Set, Sequence, MutableSequence, Mapping
from urllib.parse import urlparse

from clutch import Client
from clutch.schema.user.response.torrent.accessor import (
    TorrentAccessorObject,
    Tracker,
)

from clutchless.command import Command, CommandResult
from clutchless.parse.organize import TrackerSpecs
from clutchless.subcommand.other import query_torrents


@dataclass
class OrganizeTracker:
    netloc: str
    addresses: Sequence[str]


class HostnameFormatter:
    def __init__(self):
        pass

    @classmethod
    def format(cls, announce_url: str) -> str:
        hostname = urlparse(announce_url).hostname
        return "".join([word.capitalize() for word in cls.split_hostname(hostname)])

    @staticmethod
    def split_hostname(hostname: str) -> Sequence[str]:
        split = hostname.split(".")
        if len(split) > 2:
            return split[1:]
        return split


class ResponseTrackers:
    def __init__(self, client: Client):
        self.torrents: Sequence[TorrentAccessorObject] = query_torrents(client, fields={"trackers"})

    def get_response_tracker_map(self) -> Mapping[str, Set[str]]:
        return self.__map_formatted_hostname_to_trackers()

    def __map_formatted_hostname_to_trackers(self) -> Mapping[str, Set[str]]:
        """Maps a formatted version of netloc to tracker addresses."""
        trackers: MutableMapping[str, Set[str]] = {}
        for torrent in self.torrents:
            for tracker in torrent.trackers:
                try:
                    announce_url = tracker.announce
                    hostname = HostnameFormatter.format(announce_url)
                    try:
                        trackers[hostname].add(tracker.announce)
                    except KeyError:
                        trackers[hostname] = {tracker.announce}
                except IndexError:
                    pass
        return trackers


class OrderedTrackerList:
    def __init__(self):
        pass

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


class OrganizeTorrent(Command):
    def __init__(self):
        pass

    def run(self) -> CommandResult:
        pass


@dataclass
class ListOrganizeCommandResult(CommandResult):
    hostname_to_trackers: Mapping[str, Set[str]]

    def output(self):
        pass


class ListOrganizeCommand(Command):
    def __init__(self, raw_spec: str):
        self.parsed_spec = TrackerSpecs(raw_spec).parse()

    def run(self) -> ListOrganizeCommandResult:

        tracker_list = get_ordered_tracker_list()
        # output message
        print_tracker_list(tracker_list)

