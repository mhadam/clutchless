from collections import OrderedDict
from pathlib import Path
from typing import (
    Iterable,
    Set,
    MutableSequence,
    Mapping,
    Tuple,
    Sequence,
    MutableMapping,
)
from urllib.parse import urlparse

from clutchless.domain.torrent import MetainfoFile
from clutchless.external.metainfo import MetainfoReader, TorrentDataLocator, TorrentData
from clutchless.external.result import QueryResult, CommandResult
from clutchless.external.transmission import TransmissionApi


class AddService:
    def __init__(self, api: TransmissionApi):
        self.api = api
        self.success: MutableSequence[Path] = []
        self.added_without_data: MutableSequence[Path] = []
        # these are added together (if linking)
        # found -> metainfo file path
        self.found: MutableSequence[Path] = []
        # link -> data location path
        self.link: MutableSequence[Path] = []

        # these are added together
        self.fail: MutableSequence[Path] = []
        self.error: MutableSequence[str] = []

    def add(self, path: Path):
        result = self.api.add_torrent(path)
        if result.success:
            self.success.append(path)
            self.added_without_data.append(path)
        else:
            self.fail.append(path)
            self.error.append(result.error)

    def add_with_data(self, metainfo_path: Path, data_path: Path):
        result = self.api.add_torrent_with_files(metainfo_path, data_path)
        if result.success:
            self.success.append(metainfo_path)
            self.found.append(metainfo_path)
            self.link.append(data_path)
        else:
            self.fail.append(metainfo_path)
            self.error.append(result.error)


class FindService:
    def __init__(self, data_locator: TorrentDataLocator):
        self.data_locator = data_locator

    def find(
        self, metainfo_files: Set[MetainfoFile]
    ) -> Tuple[Set[TorrentData], Set[MetainfoFile]]:
        def generate() -> Iterable[TorrentData]:
            for file in metainfo_files:
                data = self.data_locator.find(file)
                if data:
                    yield data

        found_metainfos = set(generate())
        found_metainfo_files: Set[MetainfoFile] = {
            data.metainfo_file for data in found_metainfos
        }
        rest: Set[MetainfoFile] = metainfo_files - found_metainfo_files
        return found_metainfos, rest


class LinkDataService:
    def __init__(self, api: TransmissionApi):
        self.api = api

    def __query_incomplete_ids(self) -> Set[int]:
        id_result: QueryResult[Set[int]] = self.api.get_incomplete_ids()
        if id_result.success:
            return id_result.value
        raise RuntimeError("failed incomplete_ids query")

    def __query_metainfo_file_by_id(
        self, incomplete_ids: Set[int]
    ) -> Mapping[int, Path]:
        query_result: QueryResult[
            Mapping[int, Path]
        ] = self.api.get_metainfo_file_paths_by_id(incomplete_ids)
        if query_result.success:
            return query_result.value
        raise RuntimeError("failed torrent_name_by_id query")

    def __get_metainfo_path_by_id(self) -> Mapping[int, Path]:
        incomplete_ids: Set[int] = self.__query_incomplete_ids()
        return self.__query_metainfo_file_by_id(incomplete_ids)

    def get_incomplete_metainfo_path_by_id(self) -> Mapping[int, Path]:
        return self.__get_metainfo_path_by_id()

    def change_location(self, torrent_id: int, new_path: Path):
        command_result: CommandResult = self.api.change_torrent_location(
            torrent_id, new_path
        )
        if not command_result.success:
            raise RuntimeError("failed to change torrent location")


class LinkService:
    def __init__(self, metainfo_reader: MetainfoReader, data_service: LinkDataService):
        self.metainfo_reader = metainfo_reader
        self.data_service = data_service

    def get_incomplete_id_by_metainfo_file(self) -> Mapping[MetainfoFile, int]:
        metainfo_path_by_id = self.data_service.get_incomplete_metainfo_path_by_id()
        return {
            self.metainfo_reader.from_path(path): torrent_id
            for (torrent_id, path) in metainfo_path_by_id.items()
        }

    def change_location(self, torrent_id: int, new_path: Path):
        self.data_service.change_location(torrent_id, new_path)


class DryRunLinkService(LinkService):
    def change_location(self, torrent_id: int, new_path: Path):
        pass


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


class OrganizeService:
    """
    Queries Transmission for all announce urls and collects a sorted map with:
    shortened and camelcase hostname -> announce urls(sorted too)
    """

    def __init__(self, client: TransmissionApi):
        self.client = client

    def get_announce_urls_by_folder_name(self) -> "OrderedDict[str, Sequence[str]]":
        query_result: QueryResult[Set[str]] = self.client.get_announce_urls()
        if not query_result.success:
            raise RuntimeError("get_announce_urls query failed")
        groups_by_name = self._get_groups_by_name(query_result.value)
        groups_sorted_by_name = self._sort_groups_by_name(groups_by_name)
        return self._sort_url_sets(groups_sorted_by_name)

    @staticmethod
    def _sort_url_sets(
        groups_by_name: Mapping[str, Set[str]]
    ) -> "OrderedDict[str, Sequence[str]]":
        result = OrderedDict()
        for (name, urls) in groups_by_name.items():
            result[name] = sorted(urls)
        return result

    @staticmethod
    def _sort_groups_by_name(
        groups: Mapping[str, Set[str]]
    ) -> "OrderedDict[str, Set[str]]":
        return OrderedDict(sorted(groups.items()))

    @staticmethod
    def _get_groups_by_name(announce_urls: Set[str]) -> Mapping[str, Set[str]]:
        """Groups announce_urls by shortened name"""
        trackers: MutableMapping[str, Set[str]] = {}
        for url in announce_urls:
            try:
                hostname = AnnounceUrl(url).formatted_hostname
                try:
                    trackers[hostname].add(url)
                except KeyError:
                    trackers[hostname] = {url}
            except IndexError:
                pass
        return trackers

    def get_folder_name_by_url(self, overrides: Mapping[int, str]) -> Mapping[str, str]:
        announce_urls_by_folder_name = self.get_announce_urls_by_folder_name()
        return self._get_folder_name_by_url(announce_urls_by_folder_name, overrides)

    @staticmethod
    def _get_folder_name_by_url(
        announce_urls_by_folder_name: "OrderedDict[str, Sequence[str]]",
        overrides: Mapping[int, str],
    ) -> Mapping[str, str]:
        """Returns map: folder name by url"""
        result: MutableMapping[str, str] = {}
        for (index, (folder_name, urls)) in enumerate(
            announce_urls_by_folder_name.items()
        ):
            for url in urls:
                try:
                    result[url] = overrides[index]
                except KeyError:
                    result[url] = folder_name
        return result

    def get_announce_urls_by_torrent_id(self) -> Mapping[int, Set[str]]:
        result: QueryResult[Mapping[int, Set[str]]] = self.client.get_torrent_trackers()
        if not result.success:
            raise RuntimeError("get_torrent_trackers query failed")
        return result.value

    def move_location(self, torrent_id: int, new_path: Path):
        command_result: CommandResult = self.client.move_torrent_location(
            torrent_id, new_path
        )
        if not command_result.success:
            raise RuntimeError("failed to change torrent location")

    def get_torrent_location(self, torrent_id: int) -> Path:
        result: QueryResult[Path] = self.client.get_torrent_location(torrent_id)
        if not result.success:
            raise RuntimeError("get_torrent_location query failed")
        return result.value
