from pathlib import Path
from typing import Iterable, Set, MutableSequence, Mapping, Tuple

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

    def find(self, metainfo_files: Set[MetainfoFile]) -> Tuple[Set[TorrentData], Set[MetainfoFile]]:
        def generate() -> Iterable[TorrentData]:
            for file in metainfo_files:
                data = self.data_locator.find(file)
                if data:
                    yield data

        found_metainfos = set(generate())
        found_metainfo_files: Set[MetainfoFile] = {data.metainfo_file for data in found_metainfos}
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

    def __query_metainfo_file_by_id(self, incomplete_ids: Set[int]) -> Mapping[int, Path]:
        query_result: QueryResult[Mapping[int, Path]] = self.api.get_metainfo_file_paths_by_id(incomplete_ids)
        if query_result.success:
            return query_result.value
        raise RuntimeError("failed torrent_name_by_id query")

    def __get_metainfo_path_by_id(self) -> Mapping[int, Path]:
        incomplete_ids: Set[int] = self.__query_incomplete_ids()
        return self.__query_metainfo_file_by_id(incomplete_ids)

    def get_incomplete_metainfo_path_by_id(self) -> Mapping[int, Path]:
        return self.__get_metainfo_path_by_id()

    def change_location(self, torrent_id: int, new_path: Path):
        command_result: CommandResult = self.api.change_torrent_location(torrent_id, new_path)
        if not command_result.success:
            raise RuntimeError("failed to change torrent location")


class LinkService:
    def __init__(self, metainfo_reader: MetainfoReader, data_service: LinkDataService):
        self.metainfo_reader = metainfo_reader
        self.data_service = data_service

    def get_incomplete_id_by_metainfo_file(self) -> Mapping[MetainfoFile, int]:
        metainfo_path_by_id = self.data_service.get_incomplete_metainfo_path_by_id()
        return {
            self.metainfo_reader.from_path(path): torrent_id for
            (torrent_id, path) in metainfo_path_by_id.items()
        }

    def change_location(self, torrent_id: int, new_path: Path):
        self.data_service.change_location(torrent_id, new_path)


class DryRunLinkService(LinkService):
    def change_location(self, torrent_id: int, new_path: Path):
        pass
