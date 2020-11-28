from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Set, Sequence, Mapping, Iterable, Tuple

from texttable import Texttable

from clutchless.command.command import Command, CommandOutput
from clutchless.domain.torrent import MetainfoFile
from clutchless.service.torrent import OrganizeService
from clutchless.spec.organize import TrackerSpec


@dataclass
class OrganizeSuccess:
    torrent_id: int
    metainfo_file: MetainfoFile
    new_path: Path
    old_path: Path


@dataclass
class OrganizeFailure:
    torrent_id: int
    metainfo_file: MetainfoFile
    failure: str


@dataclass
class OrganizeAction:
    new_path: Path
    torrent_id: int


@dataclass
class OrganizeCommandOutput(CommandOutput):
    files: Mapping[int, MetainfoFile] = field(default_factory=dict)
    actions: Sequence[OrganizeAction] = field(default_factory=list)
    success: Sequence[OrganizeSuccess] = field(default_factory=list)
    failure: Sequence[OrganizeFailure] = field(default_factory=list)

    def display(self):
        success_count = len(self.success)
        failure_count = len(self.failure)
        if success_count > 0:
            print("Organized these torrents:")
            for success in self.success:
                metainfo = success.metainfo_file
                print(
                    f"{metainfo.name} moved from {success.old_path} to {success.new_path}"
                )
        if failure_count > 0:
            print("Failed to organize these torrents:")
            for failure in self.failure:
                metainfo = failure.metainfo_file
                print(f"{metainfo.name} because of: {failure.failure}")

    def dry_run_display(self):
        if len(self.actions) > 0:
            print(f"Would organize the following torrents:")
            for action in self.actions:
                file = self.files[action.torrent_id]
                print(f"{file.name} to {action.new_path}")
        else:
            "Nothing to do."


class OrganizeCommand(Command):
    def __init__(
        self, raw_spec: str, new_path: Path, organize_service: OrganizeService
    ):
        self.raw_spec = raw_spec
        self.new_path = new_path
        self.organize_service = organize_service

    def _get_files(self, ids: Set[int]) -> Mapping[int, MetainfoFile]:
        result = dict()
        for torrent_id in ids:
            result[torrent_id] = self.organize_service.get_metainfo_file(torrent_id)
        return result

    def run(self) -> OrganizeCommandOutput:
        overrides = TrackerSpec(self.raw_spec)
        announce_url_to_folder_name = self.organize_service.get_folder_name_by_url(
            overrides
        )
        announce_urls_by_torrent_id = (
            self.organize_service.get_announce_urls_by_torrent_id()
        )
        actions = self._make_actions(
            announce_url_to_folder_name, announce_urls_by_torrent_id
        )
        success, fail = self._handle(actions)
        return OrganizeCommandOutput(success=success, failure=fail)

    def dry_run(self) -> CommandOutput:
        overrides = TrackerSpec(self.raw_spec)
        announce_url_to_folder_name = self.organize_service.get_folder_name_by_url(
            overrides
        )
        announce_urls_by_torrent_id = (
            self.organize_service.get_announce_urls_by_torrent_id()
        )
        actions = self._make_actions(
            announce_url_to_folder_name, announce_urls_by_torrent_id
        )
        files = self._get_files({action.torrent_id for action in actions})
        return OrganizeCommandOutput(files, list(actions))

    def _make_actions(
        self,
        folder_name_by_announce_url: Mapping[str, str],
        announce_urls_by_torrent_id: Mapping[int, Set[str]],
    ) -> Iterable[OrganizeAction]:
        for (torrent_id, announce_urls) in announce_urls_by_torrent_id.items():
            folder_name = self._get_folder_name(
                announce_urls, folder_name_by_announce_url
            )
            new_path = Path(self.new_path, folder_name)
            yield OrganizeAction(new_path, torrent_id)

    @staticmethod
    def _get_folder_name(
        urls: Iterable[str], folder_name_by_announce_url: Mapping[str, str]
    ) -> str:
        for url in urls:
            try:
                return folder_name_by_announce_url[url]
            except KeyError:
                pass
        return "other_torrents"

    def _handle(
        self, actions: Iterable[OrganizeAction]
    ) -> Tuple[Sequence[OrganizeSuccess], Sequence[OrganizeFailure]]:
        success = []
        failure = []
        for action in actions:
            torrent_id = action.torrent_id
            new_path = action.new_path
            metainfo_file = self.organize_service.get_metainfo_file(torrent_id)
            try:
                old_path = self.organize_service.get_torrent_location(torrent_id)
                self.organize_service.move_location(torrent_id, new_path)
                success.append(
                    OrganizeSuccess(torrent_id, metainfo_file, new_path, old_path)
                )
            except RuntimeError as e:
                failure.append(OrganizeFailure(torrent_id, metainfo_file, str(e)))
        return success, failure


@dataclass
class ListOrganizeCommandOutput(CommandOutput):
    announce_urls_by_folder_name: "OrderedDict[str, Sequence[str]]"

    def display(self):
        if len(self.announce_urls_by_folder_name) > 0:
            self.__print_entries()
        else:
            self.__print_if_empty()

    def dry_run_display(self):
        raise NotImplementedError

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
        for index, (folder_name, urls) in enumerate(
            self.announce_urls_by_folder_name.items()
        ):
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

    def dry_run(self) -> CommandOutput:
        raise NotImplementedError
