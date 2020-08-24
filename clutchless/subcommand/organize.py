from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import MutableMapping, Set, Sequence, MutableSequence, Mapping
from urllib.parse import urlparse

from clutchless.command import Command, CommandResult, CommandResultAccumulator
from clutchless.parse.organize import TrackerSpec, TrackerSpecParser
from clutchless.transmission import TransmissionApi, TransmissionError


@dataclass
class FolderNameUrls:
    folder_name: str
    announce_urls: Set[str]


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
            return split[-2:]
        return split


class FolderNameGrouper:
    """Takes transmission client, queries for torrents and compiles a dict: formatted hostname -> announce urls"""

    def __init__(self, client: TransmissionApi):
        self.client = client

    def get_folder_name_to_announce_urls(self) -> Mapping[str, Set[str]]:
        return self.__get_folder_name_to_announce_urls()

    def get_ordered_folder_name_to_announce_urls(self) -> Sequence[FolderNameUrls]:
        trackers = self.__get_folder_name_to_announce_urls()
        sorted_trackers = OrderedDict(sorted(trackers.items()))
        tracker_list: MutableSequence[FolderNameUrls] = []
        for (folder_name, addresses) in sorted_trackers.items():
            tracker_list.append(FolderNameUrls(folder_name, set(addresses)))
        return tracker_list

    def __get_folder_name_to_announce_urls(self) -> Mapping[str, Set[str]]:
        """Maps a formatted version of netloc to tracker addresses."""
        trackers: MutableMapping[str, Set[str]] = {}
        for url in self.client.get_announce_urls():
            try:
                hostname = HostnameFormatter.format(url)
                try:
                    trackers[hostname].add(url)
                except KeyError:
                    trackers[hostname] = {url}
            except IndexError:
                pass
        return trackers


class FolderNameChooser:
    """Takes response trackers and orders them

    Takes overrides in form announce_url:folder_name
    """

    def __init__(self, client: TransmissionApi, overrides: Mapping[int, str] = None):
        self.client = client
        if not overrides:
            overrides = dict()
        self.overrides = overrides

    def get_announce_url_to_folder_name(self) -> Mapping[str, str]:
        trackers: MutableMapping[str, str] = {}  # tracker addresses to folder
        overrides: Mapping[str, str] = self.__translate_indices_to_urls()
        for url in self.client.get_announce_urls():
            hostname = HostnameFormatter.format(url)
            cached = trackers.get(url)
            override = overrides.get(url)
            if cached is not None:
                if cached != hostname and cached != override:
                    raise ValueError(
                        "duplicate tracker url url making tracker->hostname map"
                    )
            else:
                if override is not None:
                    trackers[url] = override
                else:
                    trackers[url] = hostname
        return trackers

    def __translate_indices_to_urls(self) -> Mapping[str, str]:
        """Returns map: urls to folder names"""
        result: MutableMapping[str, str] = {}
        grouper = FolderNameGrouper(self.client)
        ordered_folder_map: Sequence[
            FolderNameUrls
        ] = grouper.get_ordered_folder_name_to_announce_urls()
        for (index, entry) in enumerate(ordered_folder_map):
            for url in entry.announce_urls:
                try:
                    result[url] = self.overrides[index]
                except KeyError:
                    pass
        return result


@dataclass
class OrganizeSuccess(CommandResultAccumulator):
    torrent_id: int
    new_path: Path
    old_path: Path

    def accumulate(self, result: "OrganizeCommandResult"):
        result.successes.append(self)


@dataclass
class OrganizeFailure(CommandResultAccumulator):
    torrent_id: int
    failure: str

    def accumulate(self, result: "OrganizeCommandResult"):
        result.failures.append(self)


@dataclass
class OrganizeCommandResult(CommandResult):
    successes: MutableSequence[OrganizeSuccess] = field(default_factory=list)
    failures: MutableSequence[OrganizeFailure] = field(default_factory=list)

    def output(self):
        pass


class OrganizeCommand(Command):
    def __init__(self, raw_spec: str, new_path: Path, client: TransmissionApi):
        self.raw_spec = raw_spec
        self.client = client
        self.new_path = new_path

    def run(self) -> OrganizeCommandResult:
        result = OrganizeCommandResult()
        accumulators: Sequence[CommandResultAccumulator] = self.__organize()
        for accumulator in accumulators:
            accumulator.accumulate(result)
        return result

    def __organize(self) -> Sequence[CommandResultAccumulator]:
        accumulators: MutableSequence[CommandResultAccumulator] = []
        announce_url_to_folder_name: Mapping[
            str, str
        ] = self.__get_announce_url_to_folder_name()
        for (torrent_id, announce_urls) in self.client.get_torrent_trackers():
            folder_name = self.__get_folder_name(
                announce_urls, announce_url_to_folder_name
            )
            try:
                new_path = self.__get_new_torrent_path(folder_name)
                self.__move(torrent_id, new_path)
                old_path = self.client.get_torrent_location(torrent_id)
                accumulators.append(OrganizeSuccess(torrent_id, new_path, old_path))
            except TransmissionError as e:
                accumulators.append(OrganizeFailure(torrent_id, e.message))
        return accumulators

    def __get_folder_name(self, urls, url_to_folder_name: Mapping[str, str]) -> str:
        for url in urls:
            try:
                return url_to_folder_name[url]
            except KeyError:
                pass
        return "other_torrents"

    def __move(self, torrent_id: int, new_path: Path):
        self.client.move_torrent_location(torrent_id, new_path)

    def __get_new_torrent_path(self, folder_name: str) -> Path:
        return Path(self.new_path, folder_name)

    def __get_announce_url_to_folder_name(self) -> Mapping[str, str]:
        spec: TrackerSpec = self.__get_spec()
        chooser = FolderNameChooser(self.client, spec)
        url_to_folder_name = chooser.get_announce_url_to_folder_name()
        return url_to_folder_name

    def __get_spec(self) -> TrackerSpec:
        return TrackerSpecParser().parse(self.raw_spec)


@dataclass
class ListOrganizeCommandResult(CommandResult):
    hostname_to_trackers: Sequence[FolderNameUrls]

    def output(self):
        self.__print_if_empty()
        for entry in self.hostname_to_trackers:
            self.__print_entry(entry)

    def __print_if_empty(self):
        if len(self.hostname_to_trackers) < 1:
            print("No folder names to organize into (are there any torrents?).")

    def __print_entry(self, entry: FolderNameUrls):
        pass


class ListOrganizeCommand(Command):
    def __init__(self, client: TransmissionApi):
        self.client = client

    def run(self) -> ListOrganizeCommandResult:
        hostname_to_trackers = FolderNameGrouper(
            self.client
        ).get_ordered_folder_name_to_announce_urls()
        return ListOrganizeCommandResult(hostname_to_trackers)
