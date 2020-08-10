from pathlib import Path
from typing import Mapping, Sequence, Set, Union

from clutch import Client
from clutch.network.rpc.message import Response
from clutch.schema.user.response.torrent.accessor import TorrentAccessorResponse, TorrentAccessorObject

IdsArg = Union[int, Set[int]]


class TransmissionApi:
    def __init__(self, args: Mapping):
        address = args.get("--address")
        # clutchless --address http://transmission:9091/transmission/rpc add /app/resources/torrents/ -d /app/resources/data/
        self.client = Client()
        if address:
            self.client.set_connection(address=address)

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
