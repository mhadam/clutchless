import itertools
from pathlib import Path
from typing import Mapping, Sequence, Set, Union, MutableMapping, Protocol

from clutch import Client
from clutch.network.rpc.message import Response
from clutch.schema.user.method.torrent.add import TorrentAddArguments
from clutch.schema.user.response.torrent.accessor import (
    TorrentAccessorResponse,
    TorrentAccessorObject,
)
from clutch.schema.user.response.torrent.add import TorrentAdd

from clutchless.domain.torrent import MetainfoFile
from clutchless.external.result import QueryResult, CommandResult

IdsArg = Union[int, Set[int]]


def clutch_factory(args: Mapping) -> Client:
    address = args.get("--address")
    # clutchless --address http://transmission:9091/transmission/rpc add /app/resources/torrents/ -d /app/resources/data/
    client = Client()
    if address:
        client.set_connection(address=address)
    return client


class PartialTorrent:
    def __init__(self, name: str, wanted_files: Set[str]):
        self.name = name
        self.wanted_files: Set[str] = wanted_files

    def __is_wanted_file_missing(self, file: str, location: Path) -> bool:
        return file in self.wanted_files and not Path(location, file).exists()

    def verify(self, torrent: MetainfoFile, location: Path) -> bool:
        return not any(
            [
                self.__is_wanted_file_missing(str(file.path), location)
                for file in torrent.files
            ]
        )


class TransmissionError(Exception):
    def __init__(self, message):
        self.message = message


class TransmissionApi(Protocol):
    def add_torrent(self, file: Path) -> CommandResult:
        raise NotImplementedError

    def add_torrent_with_files(self, file: Path, download_dir: Path) -> CommandResult:
        raise NotImplementedError

    def get_torrent_name_by_id(self, ids: Set[int]) -> QueryResult[Mapping[int, str]]:
        raise NotImplementedError

    def get_partial_torrents(self) -> QueryResult[Mapping[str, PartialTorrent]]:
        raise NotImplementedError

    def get_incomplete_ids(self) -> QueryResult[Set[int]]:
        raise NotImplementedError

    def get_metainfo_file_paths_by_id(self, ids: Set[int]) -> QueryResult[Mapping[int, Path]]:
        raise NotImplementedError

    def get_incomplete_torrent_files(self) -> QueryResult[Set[Path]]:
        raise NotImplementedError

    def get_torrents(self, ids, fields) -> QueryResult[Mapping]:
        raise NotImplementedError

    def get_announce_urls(self) -> QueryResult[Set[str]]:
        raise NotImplementedError

    def get_torrent_trackers(self) -> QueryResult[Mapping[int, Set[str]]]:
        raise NotImplementedError

    def move_torrent_location(self, torrent_id, new_path) -> CommandResult:
        raise NotImplementedError

    def change_torrent_location(self, torrent_id, new_path) -> CommandResult:
        raise NotImplementedError

    def get_torrent_location(self, torrent_id) -> QueryResult[Path]:
        raise NotImplementedError

    def get_torrent_files_by_id(self) -> QueryResult[Mapping[int, Path]]:
        raise NotImplementedError

    def get_torrent_hashes_by_id(self) -> QueryResult[Mapping[int, str]]:
        raise NotImplementedError

    def get_torrent_ids_by_hash(self) -> QueryResult[Mapping[str, int]]:
        raise NotImplementedError

    def get_torrent_names_by_id_with_missing_data(self) -> QueryResult[Mapping[int, str]]:
        raise NotImplementedError

    def remove_torrent_keeping_data(self, torrent_id) -> CommandResult:
        raise NotImplementedError


class ClutchApi(TransmissionApi):
    def __init__(self, client: Client):
        self.client = client

    def add_torrent(self, file: Path) -> CommandResult:
        arguments: TorrentAddArguments = {
            "filename": str(file),
            "paused": True,
        }
        response: Response[TorrentAdd] = self.client.torrent.add(arguments)
        if response.result != "success":
            return CommandResult(error=response.result, success=False)
        if response.arguments.torrent_added:
            return CommandResult()
        elif response.arguments.torrent_duplicate:
            return CommandResult(error="duplicate torrent", success=False)
        return CommandResult(error="unknown error", success=False)

    def add_torrent_with_files(self, file: Path, download_dir: Path):
        arguments: TorrentAddArguments = {
            "filename": str(file),
            "download_dir": str(download_dir),
            "paused": True,
        }
        response: Response[TorrentAdd] = self.client.torrent.add(arguments)
        if response.result != "success":
            return CommandResult(error=response.result, success=False)
        if response.arguments.torrent_added:
            return CommandResult()
        elif response.arguments.torrent_duplicate:
            return CommandResult(error="duplicate torrent", success=False)
        return CommandResult(error="unknown error", success=False)

    def get_torrent_name_by_id(self, ids: Set[int]) -> QueryResult[Mapping[int, str]]:
        response: Response[TorrentAccessorResponse] = self.client.torrent.accessor(
            fields=["id", "percent_done", "name"],
            ids=ids
        )
        if response.result != "success":
            return QueryResult(success=False, error=response.result)
        return QueryResult({torrent.id: torrent.name for torrent in response.arguments.torrents})

    def get_partial_torrents(self) -> QueryResult[Mapping[str, PartialTorrent]]:
        response: Response[TorrentAccessorResponse] = self.client.torrent.accessor(
            fields=["hash_string", "wanted", "files"]
        )
        if response.result != "success":
            return QueryResult(success=False, error=response.result)
        partial_torrents: MutableMapping[str, PartialTorrent] = {}
        for torrent in response.arguments.torrents:
            wanted_files = {file for file in torrent.wanted}
            file_names = {file.name for file in torrent.files}
            wanted_file_names = set(itertools.compress(file_names, wanted_files))

            partial_torrents[torrent.hash_string] = PartialTorrent(
                torrent.name, wanted_file_names
            )
        return QueryResult(value=partial_torrents)

    def get_incomplete_ids(self) -> QueryResult[Set[int]]:
        response: Response[TorrentAccessorResponse] = self.client.torrent.accessor(
            fields=["id", "percent_done"]
        )
        response_torrents: Sequence[TorrentAccessorObject] = response.arguments.torrents
        return QueryResult(
            value={
                torrent.id for torrent in response_torrents if torrent.percent_done == 0.0
            }
        )

    def get_metainfo_file_paths_by_id(self, ids: Set[int]) -> QueryResult[Mapping[int, Path]]:
        response: Response[TorrentAccessorResponse] = self.client.torrent.accessor(
            fields=["torrent_file", "percent_done"]
        )
        response_torrents: Sequence[TorrentAccessorObject] = response.arguments.torrents
        return QueryResult(
            value={
                torrent.id: torrent.torrent_file
                for torrent in response_torrents
            }
        )

    def get_incomplete_torrent_files(self) -> QueryResult[Set[Path]]:
        response: Response[TorrentAccessorResponse] = self.client.torrent.accessor(
            fields=["torrent_file", "percent_done"]
        )
        response_torrents: Sequence[TorrentAccessorObject] = response.arguments.torrents
        return QueryResult(
            value={
                torrent.torrent_file
                for torrent in response_torrents
                if torrent.percent_done == 0.0
            }
        )

    def get_torrents(self, ids: IdsArg, fields: Set[str] = None) -> QueryResult[Mapping]:
        if fields is None:
            fields = frozenset()
        return self.client.torrent.accessor(ids, fields)

    def get_announce_urls(self) -> QueryResult[Set[str]]:
        response: Response[TorrentAccessorResponse] = self.client.torrent.accessor(
            fields=["trackers"]
        )
        return QueryResult(
            value={
                tracker.announce
                for torrent in response.arguments.torrents
                for tracker in torrent.trackers
            }
        )

    def get_torrent_trackers(self) -> QueryResult[Mapping[int, Set[str]]]:
        def get_announce_urls(torrent) -> Set[str]:
            return {tracker.announce for tracker in torrent.trackers}

        response: Response[TorrentAccessorResponse] = self.client.torrent.accessor(
            fields=["trackers"]
        )
        return QueryResult(
            value={
                torrent.id: get_announce_urls(torrent)
                for torrent in response.arguments.torrents
            }
        )

    def move_torrent_location(self, torrent_id: int, new_path: Path) -> CommandResult:
        response: Response = self.client.torrent.move(
            ids=torrent_id, location=str(new_path), move=True
        )
        if response.result != "success":
            return CommandResult(success=False, error=response.result)
        return CommandResult()

    def change_torrent_location(self, torrent_id: int, new_path: Path) -> CommandResult:
        response: Response = self.client.torrent.move(
            ids=torrent_id, location=str(new_path), move=False
        )
        if response.result != "success":
            return CommandResult(success=False)
        return CommandResult()

    def get_torrent_location(self, torrent_id: int) -> QueryResult[Path]:
        response: Response[TorrentAccessorResponse] = self.client.torrent.accessor(
            fields=["download_dir"], ids=torrent_id
        )
        if response.result != "success":
            raise TransmissionError(f"clutch failure: {response.result}")
        torrents = response.arguments.torrents
        if len(torrents) != 1:
            raise TransmissionError(
                f"torrent with id {torrent_id} not returned in result"
            )
        else:
            return Path(torrents[0].download_dir)

    def get_torrent_files_by_id(self) -> QueryResult[Mapping[int, Path]]:
        response: Response[TorrentAccessorResponse] = self.client.torrent.accessor(
            fields=["id", "torrent_file"]
        )
        if response.result != "success":
            QueryResult(success=False, error=response.result)
        return QueryResult(value={torrent.id: torrent.torrent_file for torrent in response.arguments.torrents})

    def get_torrent_hashes_by_id(self) -> QueryResult[Mapping[int, str]]:
        response: Response[TorrentAccessorResponse] = self.client.torrent.accessor(
            fields=["id", "hash_string"]
        )
        if response.result != "success":
            return QueryResult(success=False, error=response.result)
        return QueryResult(value={torrent.id: torrent.hash_string for torrent in response.arguments.torrents})

    def get_torrent_ids_by_hash(self) -> QueryResult[Mapping[str, int]]:
        response: Response[TorrentAccessorResponse] = self.client.torrent.accessor(
            fields=["id", "hash_string"]
        )
        if response.result != "success":
            return QueryResult(success=False, error=response.result)
        return QueryResult(value={torrent.hash_string : torrent.id for torrent in response.arguments.torrents})

    def get_torrent_names_by_id_with_missing_data(self) -> QueryResult[Mapping[int, str]]:
        response: Response[TorrentAccessorResponse] = self.client.torrent.accessor(
            fields=["id", "error_string", "error", "name"]
        )
        if response.result != "success":
            return QueryResult(error=response.result, success=False)
        result: MutableMapping[int, str] = {}
        for torrent in response.arguments.torrents:
            if torrent.error == 3:
                result[torrent.id] = torrent.name
        return QueryResult(value=result)

    def remove_torrent_keeping_data(self, torrent_id: int) -> CommandResult:
        response: Response[TorrentAccessorResponse] = self.client.torrent.remove(
            torrent_id, delete_local_data=False
        )
        if response.result != "success":
            return CommandResult(error=response.result, success=False)
        return CommandResult()
