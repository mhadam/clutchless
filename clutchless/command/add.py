from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, MutableMapping, Optional, MutableSequence

from clutch.network.rpc.message import Response
from clutch.schema.user.method.torrent.add import TorrentAddArguments
from clutch.schema.user.response.torrent.add import (
    Torrent as ResponseTorrent,
    TorrentAdd,
)

from clutchless.command.command import Command, CommandResult
from clutchless.spec.add import AddArgs, AddFlags
from clutchless.external.transmission import TransmissionApi


@dataclass
class AddResult(CommandResult):
    added_torrents: MutableMapping[str, str] = field(
        default_factory=dict
    )  # hash_string:rpc_name
    matches: MutableMapping[str, Path] = field(default_factory=dict)
    failed_torrents: MutableMapping[str, str] = field(default_factory=dict)
    duplicated_torrents: MutableMapping[str, str] = field(default_factory=dict)
    deleted_torrents: MutableSequence[Path] = field(default_factory=list)

    def output(self):
        pass


@dataclass
class DryAddResult(CommandResult):
    added_torrents: Mapping[str, Path]
    matches: Mapping[str, Path]

    def output(self):
        pass


class DryRunAddCommand(Command):
    def __init__(self, args: AddArgs, flags: AddFlags):
        self.args = args
        self.flags = flags
        # self.finder = TorrentFinder(args.data_dirs, args.torrent_files)

    def run(self) -> DryAddResult:
        fake_added = self.__get_to_add()
        return DryAddResult(
            added_torrents=fake_added, matches=dict(self.finder.search_result.matches)
        )

    def __force_misses(self, to_add: MutableMapping[str, Path]) -> Mapping[str, Path]:
        if self.flags.force:
            # add the unmatched (without a download_dir) - it'll be default
            to_add.update({key: None for key in self.finder.search_result.misses})
        return to_add

    def __get_to_add(self) -> Mapping[str, Path]:
        to_add: MutableMapping[str, Optional[Path]] = dict(
            self.finder.search_result.matches
        )
        to_add.update({torrent: torrent.name for (torrent, path) in to_add.items()})
        return self.__force_misses(to_add)


class AddCommand(Command):
    pass


class OldAddCommand(Command):
    def __init__(self, args: AddArgs, flags: AddFlags, client: TransmissionApi):
        self.args = args
        self.flags = flags
        self.client = client

    def __add_torrent(
        self, torrent: Path, download_dir: Path = None
    ) -> Response[TorrentAdd]:
        arguments: TorrentAddArguments = {
            "filename": str(torrent.resolve(strict=True)),
            "paused": True,
        }
        AddCommand.__add_download_dir(download_dir, arguments)
        # return self.client.add(arguments)
        return Response()

    @staticmethod
    def __add_download_dir(download_dir: Path, arguments: TorrentAddArguments):
        if download_dir:
            arguments["download_dir"] = str(download_dir.resolve(strict=True))

    def __get_to_add(self) -> Mapping[str, Path]:
        to_add: MutableMapping[str, Optional[Path]] = dict(
            # self.finder.search_result.matches
        )
        return self.__force_misses(to_add)

    def __force_misses(self, to_add: MutableMapping[str, Path]) -> Mapping[str, Path]:
        if self.flags.force:
            # add the unmatched (without a download_dir) - it'll be default
            # to_add.update({key: None for key in self.finder.search_result.misses})
            pass
        return to_add

    def run(self) -> AddResult:
        return self.__add()

    def __add(self) -> AddResult:
        add_result = AddResult()
        to_add: Mapping[str, Path] = self.__get_to_add()
        for (torrent_hash, download_dir) in to_add.items():
            self.__handle_torrent(torrent_hash, download_dir, add_result)
        return add_result

    def __handle_torrent(
        self, torrent_hash: str, download_dir: Path, add_result: AddResult
    ):
        response = self.__add_torrent(
            # self.finder.get_selected_path(torrent_hash), download_dir
        )
        self.__handle_add_response(response, add_result, torrent_hash)

    def __handle_add_response(
        self, response: Response[TorrentAdd], add_result: AddResult, torrent_hash: str
    ):
        if response.result == "success":
            torrent_added: ResponseTorrent = response.arguments.torrent_added
            torrent_duplicated: ResponseTorrent = response.arguments.torrent_duplicate
            if torrent_added is not None and len(torrent_added.dict().items()) > 0:
                add_result.added_torrents[torrent_hash] = torrent_added.name
                # delete added torrent
                if self.flags.delete_added:
                    # torrent_path = self.finder.get_selected_path(torrent_hash)
                    # os.remove(torrent_path)
                    # add_result.deleted_torrents.append(torrent_path)
                    pass
            elif (
                torrent_duplicated is not None
                and len(torrent_duplicated.dict().items()) > 0
            ):
                add_result.duplicated_torrents[torrent_hash] = torrent_duplicated.name
        else:
            add_result.failed_torrents[torrent_hash] = response.result
