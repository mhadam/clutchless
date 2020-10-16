from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import MutableMapping, Set, Sequence, MutableSequence, Mapping
from urllib.parse import urlparse

from texttable import Texttable

from clutchless.command import Command, CommandResult, CommandResultAccumulator
from clutchless.parse.organize import TrackerSpec, TrackerSpecParser
from clutchless.external.transmission import TransmissionApi, TransmissionError


class AnnounceUrl:
    def __init__(self, announce_url: str):
        self.announce_url = announce_url

    @property
    def formatted_hostname(self) -> str:
        hostname = urlparse(self.announce_url).hostname
        return "".join([word.capitalize() for word in self.split_hostname(hostname)])

    @staticmethod
    def split_hostname(hostname: str) -> Sequence[str]:
        split = hostname.split(".")
        if len(split) > 2:
            return split[-2:]
        return split


class AnnounceUrlGrouper:
    """
    Queries Transmission for all announce urls and collects a sorted map with:
    shortened and camelcase hostname -> announce urls(sorted too)
    """

    def __init__(self, client: TransmissionApi):
        self.client = client

    def get_announce_urls_by_group_name(self) -> 'OrderedDict[str, Sequence[str]]':
        groups_by_name = self.__get_groups_by_name()
        groups_sorted_by_name = self.__sort_groups_by_name(groups_by_name)
        return self.__sort_url_sets(groups_sorted_by_name)

    @staticmethod
    def __sort_url_sets(groups_by_name: 'OrderedDict[str, Set[str]]') -> 'OrderedDict[str, Sequence[str]]':
        result = OrderedDict()
        for (name, urls) in groups_by_name.items():
            result[name] = sorted(urls)
        return result

    @staticmethod
    def __sort_groups_by_name(groups: Mapping[str, Set[str]]) -> 'OrderedDict[str, Set[str]]':
        return OrderedDict(sorted(groups.items()))

    def __get_groups_by_name(self) -> Mapping[str, Set[str]]:
        """Groups announce_urls by shortened name"""
        trackers: MutableMapping[str, Set[str]] = {}
        for url in self.client.get_announce_urls():
            try:
                hostname = AnnounceUrl(url).formatted_hostname
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
            hostname = AnnounceUrl(url).formatted_hostname
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
        grouper = AnnounceUrlGrouper(self.client)
        announce_urls_by_group_name: 'OrderedDict[str, Sequence[str]]' = grouper.get_announce_urls_by_group_name()
        for (index, (group_name, urls)) in enumerate(announce_urls_by_group_name.items()):
            for url in urls:
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
    hostname_to_trackers: 'OrderedDict[str, Sequence[str]]'

    def output(self):
        if len(self.hostname_to_trackers) > 0:
            self.__print_entries()
        else:
            self.__print_if_empty()

    def __print_if_empty(self):
        print("No folder names to organize into (are there any torrents?).")

    def __print_entries(self):
        table = Texttable()
        table.set_deco(Texttable.HEADER)
        table.set_cols_dtype(['i', 't', 't'])
        table.set_cols_align(['l', 'l', 'l'])
        table.set_header_align(['l', 'l', 'l'])
        table.header(['ID', 'Name', 'Tracker'])
        for index, (group_name, urls) in enumerate(self.hostname_to_trackers.items()):
            self.__add_entry(table, index, group_name, urls)
        table_output = table.draw()
        print(table_output, end="")

    def __add_entry(self, table, index: int, group_name: str, urls: Sequence[str]):
        first_url, *other_urls = urls
        shortened_url = self.__shorten_url(first_url)
        table.add_row([index, group_name, shortened_url])
        for url in other_urls:
            shortened_url = self.__shorten_url(url)
            table.add_row([index, group_name, shortened_url])

    def __shorten_url(self, url: str) -> str:
        if len(url) > 40:
            return url[:37] + '...'
        return url


class ListOrganizeCommand(Command):
    def __init__(self, client: TransmissionApi):
        self.client = client

    def run(self) -> ListOrganizeCommandResult:
        hostname_to_trackers = AnnounceUrlGrouper(
            self.client
        ).get_announce_urls_by_group_name()
        return ListOrganizeCommandResult(hostname_to_trackers)
