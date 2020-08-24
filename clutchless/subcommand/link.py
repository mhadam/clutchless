from dataclasses import dataclass, field
from pathlib import Path
from typing import Set, Mapping, MutableSequence, MutableMapping, Sequence

from clutch import Client
from clutch.network.rpc.message import Response
from clutch.schema.user.response.torrent.accessor import TorrentAccessorObject
from torrentool.torrent import Torrent

from clutchless.command import CommandResultAccumulator, CommandResult, Command
from clutchless.search import TorrentTuple
from clutchless.subcommand.find import TorrentFinder, SearchResult
from clutchless.subcommand.other import (
    ClutchLink,
    ClutchError,
    MoveTorrent,
    VerifyTorrent,
)
from clutchless.transmission import TransmissionApi


@dataclass
class LinkFailure(CommandResultAccumulator):
    name: str
    found_location: Path
    result: str

    def read(self, response: Response, torrent: Torrent, found_location: Path):
        self.result = response.result
        self.name = torrent.name
        self.found_location = found_location

    def accumulate(self, result: "LinkCommandResult"):
        result.failed.append(self)


@dataclass
class LinkUnmatched(CommandResultAccumulator):
    name: str

    def accumulate(self, result: "LinkCommandResult"):
        result.unmatched.append(self)


@dataclass
class LinkSuccess(CommandResultAccumulator):
    name: str
    found_location: Path

    def accumulate(self, result: "LinkCommandResult"):
        result.successes.append(self)


@dataclass
class LinkCommandResult(CommandResult):
    unmatched: MutableSequence[LinkUnmatched] = field(default_factory=list)
    failed: MutableSequence[LinkFailure] = field(default_factory=list)
    successes: MutableSequence[LinkSuccess] = field(default_factory=list)

    def output(self):
        pass


@dataclass
class DryRunLinkCommandResult(CommandResult):
    unmatched: MutableSequence[LinkUnmatched] = field(default_factory=list)
    failed: MutableSequence[LinkFailure] = field(default_factory=list)
    successes: MutableSequence[LinkSuccess] = field(default_factory=list)

    def output(self):
        pass


class LinkTorrent:
    def __init__(self, clutch_link: ClutchLink, client: Client):
        self.clutch_link = clutch_link
        self.client = client

    def execute(self) -> CommandResultAccumulator:
        for operation in [MoveTorrent, VerifyTorrent]:
            name = self.clutch_link.torrent.name
            found_path = self.clutch_link.found_path
            try:
                operation(self.clutch_link, self.client).execute()
            except ClutchError as e:
                return LinkFailure(name, found_path, e.message)
            return LinkSuccess(name, found_path)


class LinkCommand(Command):
    def __init__(
        self, data_dirs: Set[Path], torrent_files: Set[Path], client: TransmissionApi
    ):
        self.client = client
        self.finder = TorrentFinder(data_dirs, torrent_files)
        self.search_result: SearchResult = self.finder.find()

    def __get_incomplete_hashes(self) -> Set[str]:
        return self.incomplete_response.keys()

    def run(self) -> LinkCommandResult:
        result = LinkCommandResult()
        for accumulator in self.__link_matched():
            accumulator.accumulate(result)

        return result

    def __link_matched(self) -> Sequence[CommandResultAccumulator]:
        accumulators: MutableSequence[CommandResultAccumulator] = []
        for (torrent, found_path) in self.__get_matches().items():
            torrent_id = self.__get_client_id(torrent.hash_string)
            clutch_link = ClutchLink(torrent_id, torrent, found_path)
            accumulator = LinkTorrent(clutch_link, self.client).execute()
            accumulators.append(accumulator)
        return accumulators

    def __get_client_id(self, torrent_hash: str) -> int:
        return self.incomplete_response[torrent_hash].id

    def __get_matches(self) -> Mapping[Torrent, Path]:
        result: MutableMapping[Torrent, Path] = {}
        for matching_hash in self.__get_matching_hashes():
            torrent_tuple: TorrentTuple = self.finder.register.get_selected(
                matching_hash
            )
            result[torrent_tuple.torrent] = self.search_result.matches[matching_hash]
        return result

    def __get_matching_hashes(self) -> Set[str]:
        return self.search_result.matches.keys()

    def __get_unmatched_hashes(self) -> Set[str]:
        return self.search_result.misses.keys()


class DryRunLinkCommand(LinkCommand):
    def __link_matched(self) -> LinkCommandResult:
        command_result: LinkCommandResult = LinkCommandResult()
        accumulators: MutableSequence[CommandResultAccumulator] = []
        for (torrent, found_path) in self.__get_matches().items():
            accumulators.append(LinkSuccess(torrent.name, found_path))
        return command_result


@dataclass
class LinkListCommandResult(CommandResult):
    incompletes: Mapping[str, TorrentAccessorObject]

    def output(self):
        if len(self.incompletes) > 0:
            for (hash_string, torrent) in self.incompletes.items():
                print(f"{torrent.name}: {torrent.download_dir}")


class ListLinkCommand(Command):
    def __init__(self, client: TransmissionApi):
        self.client = client
        self.incomplete_response: Mapping[
            str, TorrentAccessorObject
        ] = IncompleteTorrents(client).get_responses()

    def run(self) -> LinkListCommandResult:
        return LinkListCommandResult(self.incomplete_response)
