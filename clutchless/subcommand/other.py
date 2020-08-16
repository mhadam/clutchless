from dataclasses import dataclass
from pathlib import Path

from clutch import Client
from clutch.network.rpc.message import Response
from clutch.schema.user.method.torrent.action import TorrentActionMethod
from torrentool.torrent import Torrent

from clutchless.command import CommandResult, Command


class MissingCommandResult(CommandResult):
    def output(self):
        print(
            "Empty command! This is probably a bug. Be ambitious, investigate it and fix it!"
        )


class MissingCommand(Command):
    def run(self) -> CommandResult:
        return MissingCommandResult()


@dataclass
class ClutchLink:  # rename to NewClutchDirectory???
    torrent_id: int
    torrent: Torrent
    found_path: Path


class ClutchError(Exception):
    def __init__(self, clutch_link: ClutchLink, message: str):
        self.clutch_link = clutch_link
        self.message = message


class MoveTorrent:
    def __init__(self, clutch_link: ClutchLink, client: Client):
        self.clutch_link = clutch_link
        self.client = client

    def execute(self):
        response = self.__move_torrent()
        if response.result != "success":
            raise ClutchError(self.clutch_link, response.result)

    def __move_torrent(self) -> Response:
        location = str(self.clutch_link.found_path.resolve(strict=True))
        return self.client.torrent.move(
            ids=self.clutch_link.torrent_id, location=location
        )


class VerifyTorrent:
    def __init__(self, clutch_link: ClutchLink, client: Client):
        self.clutch_link = clutch_link
        self.client = client

    def execute(self):
        response: Response = self.__verify_link()
        self.__handle_verify_response(response)

    def __verify_link(self) -> Response:
        return self.client.torrent.action(
            ids=self.clutch_link.torrent_id, method=TorrentActionMethod.VERIFY
        )

    def __handle_verify_response(self, verify_response: Response):
        if verify_response.result != "success":
            raise ClutchError(self.clutch_link, verify_response.result)
