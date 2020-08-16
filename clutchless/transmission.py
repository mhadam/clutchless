from pathlib import Path
from typing import Mapping, Sequence, Set, Union, MutableMapping

from clutch import Client
from clutch.network.rpc.message import Response
from clutch.schema.user.response.torrent.accessor import TorrentAccessorResponse, TorrentAccessorObject

IdsArg = Union[int, Set[int]]


def clutch_factory(args: Mapping) -> Client:
    address = args.get("--address")
    # clutchless --address http://transmission:9091/transmission/rpc add /app/resources/torrents/ -d /app/resources/data/
    client = Client()
    if address:
        client.set_connection(address=address)
    return client


class TransmissionError(Exception):
    def __init__(self, message):
        self.message = message


class TransmissionApi:
    def __init__(self, client: Client):
        self.client = client

    def get_incomplete_ids(self) -> Set[int]:
        response: Response[TorrentAccessorResponse] = self.client.torrent.accessor(
            fields=["id", "percent_done"]
        )
        response_torrents: Sequence[TorrentAccessorObject] = response.arguments.torrents
        return {
            torrent.id
            for torrent in response_torrents
            if torrent.percent_done == 0.0
        }

    def get_incomplete_torrent_files(self) -> Set[Path]:
        response: Response[TorrentAccessorResponse] = self.client.torrent.accessor(
            fields=["torrent_file", "percent_done"]
        )
        response_torrents: Sequence[TorrentAccessorObject] = response.arguments.torrents
        return {
            torrent.torrent_file
            for torrent in response_torrents
            if torrent.percent_done == 0.0
        }

    def get_torrents(self, ids: IdsArg, fields: Set[str] = None) -> Mapping:
        if fields is None:
            fields = frozenset()
        return self.client.torrent.accessor(ids, fields)

    def get_announce_urls(self) -> Set[str]:
        response: Response[TorrentAccessorResponse] = self.client.torrent.accessor(
            fields=["trackers"]
        )
        return {
            tracker.announce
            for torrent in response.arguments.torrents
            for tracker in torrent.trackers
        }

    def get_torrent_trackers(self) -> Mapping[int, Set[str]]:
        def get_announce_urls(torrent) -> Set[str]:
            return {tracker.announce for tracker in torrent.trackers}

        response: Response[TorrentAccessorResponse] = self.client.torrent.accessor(
            fields=["trackers"]
        )
        return {
            torrent.id: get_announce_urls(torrent)
            for torrent in response.arguments.torrents
        }

    def move_torrent_location(self, torrent_id: int, new_path: Path):
        response: Response = self.client.torrent.move(
            ids=torrent_id,
            location=str(new_path),
            move=True
        )
        if response.result != "success":
            raise TransmissionError(f"clutch failure: {response.result}")

    def change_torrent_location(self, torrent_id: int, new_path: Path):
        response: Response = self.client.torrent.move(
            ids=torrent_id,
            location=str(new_path),
            move=False
        )
        if response.result != "success":
            raise TransmissionError(f"clutch failure: {response.result}")

    def get_torrent_location(self, torrent_id: int) -> Path:
        response: Response[TorrentAccessorResponse] = self.client.torrent.accessor(
            fields=["download_dir"],
            ids=torrent_id
        )
        if response.result != "success":
            raise TransmissionError(f"clutch failure: {response.result}")
        torrents = response.arguments.torrents
        if len(torrents) != 1:
            raise TransmissionError(f"torrent with id {torrent_id} not returned in result")
        else:
            return Path(torrents[0].download_dir)

    def get_torrent_files_by_id(self) -> Mapping[int, Path]:
        result: MutableMapping[int, Path] = {}
        response: Response[TorrentAccessorResponse] = self.client.torrent.accessor(
            fields=["id", "torrent_file"]
        )
        for torrent in response.arguments.torrents:
            result[torrent.id] = Path(torrent.torrent_file)
        return result
