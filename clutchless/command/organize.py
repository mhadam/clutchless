from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import MutableMapping, Set, Sequence, MutableSequence, Mapping
from urllib.parse import urlparse

from texttable import Texttable

from clutchless.service.torrent import OrganizeService
from clutchless.command.command import Command, CommandOutput
from clutchless.external.result import QueryResult
from clutchless.external.transmission import TransmissionApi, TransmissionError


# @dataclass
# class OrganizeSuccess(CommandResultAccumulator):
#     torrent_id: int
#     new_path: Path
#     old_path: Path
#
#     def accumulate(self, result: "OrganizeCommandResult"):
#         result.successes.append(self)
#
#
# @dataclass
# class OrganizeFailure(CommandResultAccumulator):
#     torrent_id: int
#     failure: str
#
#     def accumulate(self, result: "OrganizeCommandResult"):
#         result.failures.append(self)
#
#
# @dataclass
# class OrganizeCommandResult(CommandResult):
#     successes: MutableSequence[OrganizeSuccess] = field(default_factory=list)
#     failures: MutableSequence[OrganizeFailure] = field(default_factory=list)
#
#     def output(self):
#         pass
#
#
# class OrganizeCommand(Command):
#     def __init__(self, raw_spec: str, new_path: Path, organize_service: OrganizeService):
#         self.raw_spec = raw_spec
#         self.new_path = new_path
#         self.organize_service = organize_service
#
#     def run(self) -> OrganizeCommandResult:
#         result = OrganizeCommandResult()
#         accumulators: Sequence[CommandResultAccumulator] = self.__organize()
#         for accumulator in accumulators:
#             accumulator.accumulate(result)
#         return result
#
#     def __organize(self) -> Sequence[CommandResultAccumulator]:
#         accumulators: MutableSequence[CommandResultAccumulator] = []
#         announce_url_to_folder_name: Mapping[
#             str, str
#         ] = self.__get_announce_url_to_folder_name()
#         for (torrent_id, announce_urls) in self.client.get_torrent_trackers():
#             folder_name = self.__get_folder_name(
#                 announce_urls, announce_url_to_folder_name
#             )
#             try:
#                 new_path = self.__get_new_torrent_path(folder_name)
#                 self.__move(torrent_id, new_path)
#                 old_path = self.client.get_torrent_location(torrent_id)
#                 accumulators.append(OrganizeSuccess(torrent_id, new_path, old_path))
#             except TransmissionError as e:
#                 accumulators.append(OrganizeFailure(torrent_id, e.message))
#         return accumulators
#
#     def __get_folder_name(self, urls, url_to_folder_name: Mapping[str, str]) -> str:
#         for url in urls:
#             try:
#                 return url_to_folder_name[url]
#             except KeyError:
#                 pass
#         return "other_torrents"
#
#     def __move(self, torrent_id: int, new_path: Path):
#         self.client.move_torrent_location(torrent_id, new_path)
#
#     def __get_new_torrent_path(self, folder_name: str) -> Path:
#         return Path(self.new_path, folder_name)
#
#     def __get_announce_url_to_folder_name(self) -> Mapping[str, str]:
#         spec: TrackerSpec = self.__get_spec()
#         chooser = FolderNameChooser(self.client, spec)
#         url_to_folder_name = chooser.get_announce_url_to_folder_name()
#         return url_to_folder_name
#
#     def __get_spec(self) -> TrackerSpec:
#         return TrackerSpecParser().parse(self.raw_spec)


@dataclass
class ListOrganizeCommandOutput(CommandOutput):
    announce_urls_by_folder_name: "OrderedDict[str, Sequence[str]]"

    def display(self):
        if len(self.announce_urls_by_folder_name) > 0:
            self.__print_entries()
        else:
            self.__print_if_empty()

    @staticmethod
    def __print_if_empty():
        print("No folder names to organize into (are there any torrents?).")

    def __print_entries(self):
        table = Texttable()
        table.set_deco(Texttable.HEADER)
        table.set_cols_dtype(["i", "t", "t"])
        table.set_cols_align(["l", "l", "l"])
        table.set_header_align(["l", "l", "l"])
        table.header(["ID", "Name", "Tracker"])
        for index, (folder_name, urls) in enumerate(self.announce_urls_by_folder_name.items()):
            self.__add_entry(table, index, folder_name, urls)
        table_output = table.draw()
        print(table_output, end="")

    def __add_entry(self, table, index: int, group_name: str, urls: Sequence[str]):
        first_url, *other_urls = urls
        shortened_url = self._shorten_url(first_url)
        table.add_row([index, group_name, shortened_url])
        for url in other_urls:
            shortened_url = self._shorten_url(url)
            table.add_row([index, group_name, shortened_url])

    @staticmethod
    def _shorten_url(url: str) -> str:
        if len(url) > 40:
            return url[:37] + "..."
        return url


class ListOrganizeCommand(Command):
    def __init__(self, service: OrganizeService):
        self.service = service

    def run(self) -> ListOrganizeCommandOutput:
        announce_urls_by_folder_name = self.service.get_announce_urls_by_folder_name()
        return ListOrganizeCommandOutput(announce_urls_by_folder_name)
