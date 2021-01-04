import asyncio
import logging
import signal
from asyncio import FIRST_COMPLETED
from collections import OrderedDict
from pathlib import Path
from typing import (
    Set,
    MutableSequence,
    Mapping,
    Tuple,
    Sequence,
    MutableMapping,
    Optional,
    cast,
    Iterable,
    AsyncGenerator,
)
from urllib.parse import urlparse

from clutchless.domain.torrent import MetainfoFile
from clutchless.external.metainfo import (
    MetainfoReader,
    TorrentData,
    TorrentDataLocator,
)
from clutchless.external.result import QueryResult, CommandResult
from clutchless.external.transmission import TransmissionApi

logger = logging.getLogger(__name__)


class AddService:
    def __init__(self, api: TransmissionApi):
        self.api = api
        self.success: MutableSequence[MetainfoFile] = []
        self.added_without_data: MutableSequence[MetainfoFile] = []
        # these are added together (if linking)
        # found -> metainfo file path
        self.found: MutableSequence[MetainfoFile] = []
        # link -> data location path
        self.link: MutableSequence[Path] = []

        # these are added together
        self.fail: MutableSequence[MetainfoFile] = []
        self.error: MutableSequence[str] = []

    def add(self, file: MetainfoFile):
        path = cast(Path, file.path)
        result = self.api.add_torrent(path)
        if result.success:
            self.success.append(file)
            self.added_without_data.append(file)
        else:
            self.fail.append(file)
            self.error.append(result.error or "empty error string")

    def add_with_data(self, file: MetainfoFile, data_path: Path):
        path = cast(Path, file.path)
        result = self.api.add_torrent_with_files(path, data_path)
        if result.success:
            self.success.append(file)
            self.found.append(file)
            self.link.append(data_path)
        else:
            self.fail.append(file)
            self.error.append(result.error or "empty error string")


class LinkOnlyAddService(AddService):
    def add(self, path: Path):
        pass


class FindService:
    def __init__(self, data_locator: TorrentDataLocator):
        self.data_locator = data_locator

    async def find_async(
        self, files: Set[MetainfoFile]
    ) -> AsyncGenerator[TorrentData, None]:
        pending = {asyncio.create_task(self.data_locator.find(file)) for file in files}
        logger.info(f"{pending}")
        while pending:
            try:
                logger.info(f"pre-await {pending}")
                done, pending = await asyncio.wait(pending, return_when=FIRST_COMPLETED)
                logger.info(f"post-wait {done, pending}")
                while done:
                    d = done.pop()
                    logger.info(f"yielding result {d}")
                    yield d.result()
            except (GeneratorExit, asyncio.CancelledError) as e:
                logger.info(f"exiting find_async {type(e)}")
                for task in pending:
                    task.cancel()
                for task in pending:
                    await task
                    yield task.result()
                break

    def find_blocking(
        self, files: Set[MetainfoFile], timeout: float
    ) -> Iterable[TorrentData]:
        async def _wait():
            coros = [self.data_locator.find(file) for file in files]
            done, pending = await asyncio.wait(coros, timeout=timeout)
            logger.info(f"finished asyncio.wait in find service")
            for task in pending:
                task.cancel()
            for task in pending:
                await task
            return [task.result() for task in done | pending]

        return asyncio.run(_wait())

    def find(self, metainfo_files: Iterable[MetainfoFile]) -> Iterable[TorrentData]:
        metainfo_files = set(metainfo_files)

        async def _find_subroutine():
            collected: MutableSequence[TorrentData] = []
            completion_count = len(metainfo_files)
            found_count = 0
            generator = self.find_async(metainfo_files)
            while True:
                try:
                    result = await generator.__anext__()
                    collected.append(result)
                    logger.info(f"found {result}")
                    if result.location:
                        found_count += 1
                        print(
                            f"{found_count}/{completion_count} {result.metainfo_file} found at {result.location}"
                        )
                except StopAsyncIteration:
                    logger.info(f"generator exit")
                    break
                except asyncio.CancelledError:
                    logger.info(f"closing generator")
                    await generator.aclose()
            logger.info(f"finished find subroutine collecting {collected}")
            return collected

        async def _main():
            print(f"Starting search - press Ctrl+C to cancel")
            find_task = asyncio.create_task(_find_subroutine())
            loop = asyncio.get_event_loop()

            def _interrupt():
                find_task.cancel()

            loop.add_signal_handler(signal.SIGINT, _interrupt)
            results = await find_task
            return results

        return asyncio.run(_main())


class ExcludingFindService(FindService):
    def find(
        self, metainfo_files: Set[MetainfoFile]
    ) -> Tuple[Set[TorrentData], Set[MetainfoFile]]:
        found, rest = super(ExcludingFindService, self).find(metainfo_files)
        return found, set()


class LinkDataService:
    def __init__(self, api: TransmissionApi):
        self.api = api

    def __query_incomplete_ids(self) -> Set[int]:
        id_result: QueryResult[Set[int]] = self.api.get_incomplete_ids()
        if id_result.success:
            return id_result.value or set()
        raise RuntimeError("failed incomplete_ids query")

    def __query_metainfo_file_by_id(
        self, incomplete_ids: Set[int]
    ) -> Mapping[int, Path]:
        query_result: QueryResult[
            Mapping[int, Path]
        ] = self.api.get_metainfo_file_paths_by_id(incomplete_ids)
        if query_result.success:
            return query_result.value or dict()
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
    def formatted_hostname(self) -> Optional[str]:
        hostname = urlparse(self.announce_url).hostname
        if hostname is None:
            return None
        return "".join([word.capitalize() for word in self.split_hostname(hostname)])

    @staticmethod
    def split_hostname(hostname: str) -> Sequence[str]:
        split = hostname.split(".")
        if len(split) > 2:
            return split[-2:]
        return split


class PruneService:
    def __init__(self, client: TransmissionApi):
        self.client = client

    def get_torrent_hashes(self) -> Set[str]:
        query: QueryResult[Mapping[str, int]] = self.client.get_torrent_ids_by_hash()
        if not query.success:
            raise RuntimeError("get_torrent_ids_by_hash query failed")
        value = query.value or dict()
        return set(value.keys())

    def get_torrent_name_by_id_with_missing_data(self) -> Mapping[int, str]:
        query: QueryResult[
            Mapping[int, str]
        ] = self.client.get_torrent_names_by_id_with_missing_data()
        if not query.success:
            raise RuntimeError("get_torrent_names_by_id_with_missing_data query failed")
        return query.value or dict()

    def remove_torrent(self, torrent_id: int):
        result: CommandResult = self.client.remove_torrent_keeping_data(torrent_id)
        if not result.success:
            raise RuntimeError("failed remove_torrent command", result)


class OrganizeService:
    """
    Queries Transmission for all announce urls and collects a sorted map with:
    shortened and camelcase hostname -> announce urls(sorted too)
    """

    def __init__(self, client: TransmissionApi, metainfo_reader: MetainfoReader):
        self.client = client
        self.metainfo_reader = metainfo_reader

    def get_announce_urls_by_folder_name(self) -> "OrderedDict[str, Sequence[str]]":
        query_result: QueryResult[Set[str]] = self.client.get_announce_urls()
        if not query_result.success:
            raise RuntimeError("get_announce_urls query failed")
        groups_by_name = self._get_groups_by_name(query_result.value or set())
        groups_sorted_by_name = self._sort_groups_by_name(groups_by_name)
        return self._sort_url_sets(groups_sorted_by_name)

    @staticmethod
    def _sort_url_sets(
        groups_by_name: Mapping[str, Set[str]]
    ) -> "OrderedDict[str, Sequence[str]]":
        result: "OrderedDict[str, Sequence[str]]" = OrderedDict()
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
                if hostname is None:
                    continue
                try:
                    trackers[hostname].add(url)
                except KeyError:
                    trackers[hostname] = {url}
            except IndexError:
                continue
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
        return result.value or dict()

    def move_location(self, torrent_id: int, new_path: Path):
        command_result: CommandResult = self.client.move_torrent_location(
            torrent_id, new_path
        )
        if not command_result.success:
            raise RuntimeError("failed to change torrent location")

    def get_torrent_location(self, torrent_id: int) -> Path:
        result: QueryResult[Path] = self.client.get_torrent_location(torrent_id)
        if not result.success or result.value is None:
            raise RuntimeError("get_torrent_location query failed")
        return result.value

    def get_metainfo_file(self, torrent_id: int) -> MetainfoFile:
        result: QueryResult[Path] = self.client.get_metainfo_file_path(torrent_id)
        if not result.success or result.value is None:
            raise RuntimeError("get_torrent_location query failed")
        return self.metainfo_reader.from_path(result.value)
