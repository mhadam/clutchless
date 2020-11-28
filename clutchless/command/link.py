from dataclasses import dataclass, field
from typing import Set, Mapping, MutableSequence, Tuple, Sequence

from clutchless.command.command import Command, CommandOutput
from clutchless.domain.torrent import MetainfoFile
from clutchless.external.metainfo import TorrentData
from clutchless.service.torrent import FindService, LinkService


@dataclass
class LinkFailure:
    torrent_data: TorrentData
    error: str


@dataclass
class LinkCommandOutput(CommandOutput):
    no_matching_data: Set[MetainfoFile] = field(default_factory=set)
    fail: Sequence[LinkFailure] = field(default_factory=list)
    success: Sequence[TorrentData] = field(default_factory=list)

    def display(self):
        success_count = len(self.success)
        fail_count = len(self.fail)
        no_matching_data_count = len(self.no_matching_data)
        if success_count > 0:
            print(f"Linked the following torrents:")
            for linked in self.success:
                name = linked.metainfo_file.name
                print(f"{name} at {linked.location}")
        if no_matching_data_count > 0:
            print(f"Couldn't find the data for the following torrents:")
            for unmatched in self.no_matching_data:
                print(f"{unmatched.name}")
        if fail_count > 0:
            print(f"Failed to link the following torrents:")
            for fail in self.fail:
                name = fail.torrent_data.metainfo_file.name
                print(f"{name} because: {fail.error}")

    def dry_run_display(self):
        found_count = len(self.success)
        no_matching_data_count = len(self.no_matching_data)
        if found_count > 0:
            print(f"Found the following torrents:")
            for linked in self.success:
                name = linked.metainfo_file.name
                print(f"{name} at {linked.location}")
        if no_matching_data_count > 0:
            print(f"Couldn't find data for the following torrents:")
            for unmatched in self.no_matching_data:
                print(f"{unmatched.name}")


class LinkCommand(Command):
    def __init__(self, link_service: LinkService, find_service: FindService):
        self.link_service = link_service
        self.find_service = find_service

    def change_location(
        self,
        torrent_id_by_metainfo_file: Mapping[MetainfoFile, int],
        torrent_data: TorrentData,
    ):
        torrent_id = torrent_id_by_metainfo_file[torrent_data.metainfo_file]
        new_path = torrent_data.location
        self.link_service.change_location(torrent_id, new_path)

    def handle_found(
        self,
        found: Set[TorrentData],
        torrent_id_by_metainfo_file: Mapping[MetainfoFile, int],
    ) -> Tuple[Sequence[TorrentData], Sequence[LinkFailure]]:
        success: MutableSequence[TorrentData] = []
        error: MutableSequence[LinkFailure] = []
        for torrent_data in found:
            try:
                self.change_location(torrent_id_by_metainfo_file, torrent_data)
                success.append(torrent_data)
            except RuntimeError as e:
                error.append(LinkFailure(torrent_data, str(e)))
        return success, error

    def run(self) -> LinkCommandOutput:
        torrent_id_by_metainfo_file = (
            self.link_service.get_incomplete_id_by_metainfo_file()
        )
        metainfo_files: Set[MetainfoFile] = set(torrent_id_by_metainfo_file.keys())
        found, rest = self.find_service.find(metainfo_files)
        success, failure = self.handle_found(found, torrent_id_by_metainfo_file)
        return LinkCommandOutput(rest, failure, success)

    def dry_run(self) -> LinkCommandOutput:
        torrent_id_by_metainfo_file = (
            self.link_service.get_incomplete_id_by_metainfo_file()
        )
        metainfo_files: Set[MetainfoFile] = set(torrent_id_by_metainfo_file.keys())
        found, rest = self.find_service.find(metainfo_files)
        return LinkCommandOutput(success=list(found), no_matching_data=rest)


@dataclass
class LinkListCommandResult(CommandOutput):
    found: Set[TorrentData]
    rest: Set[MetainfoFile]

    def display(self):
        is_any_found = len(self.found) > 0
        is_any_rest = len(self.rest) > 0
        if is_any_found:
            print("Found following missing data torrents:")
            for torrent_data in self.found:
                name = torrent_data.metainfo_file.name
                print(f"{name} at {torrent_data.location}")

        if is_any_rest:
            print("Following missing data torrents could not be located:")
            for metainfo_file in self.rest:
                print(f"{metainfo_file.name}")

        if not (is_any_found or is_any_rest):
            print("No missing data torrents found.")

    def dry_run_display(self):
        raise NotImplementedError


class ListLinkCommand(Command):
    def __init__(self, link_service: LinkService, find_service: FindService):
        self.link_service = link_service
        self.find_service = find_service

    def run(self) -> LinkListCommandResult:
        torrent_id_by_metainfo_file = (
            self.link_service.get_incomplete_id_by_metainfo_file()
        )
        metainfo_files: Set[MetainfoFile] = set(torrent_id_by_metainfo_file.keys())
        found, rest = self.find_service.find(metainfo_files)
        return LinkListCommandResult(found, rest)

    def dry_run(self) -> CommandOutput:
        raise NotImplementedError
