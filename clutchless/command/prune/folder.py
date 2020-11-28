from dataclasses import dataclass
from typing import Set

from clutchless.command.command import CommandOutput, Command
from clutchless.domain.torrent import MetainfoFile
from clutchless.external.filesystem import Filesystem
from clutchless.service.torrent import PruneService


@dataclass
class PruneFolderCommandOutput(CommandOutput):
    pruned: Set[MetainfoFile]

    def dry_run_display(self):
        if len(self.pruned) > 0:
            print("The following metainfo files would be removed:")
            for file in self.pruned:
                print(f"{file.name} at {file.path}")
        else:
            print("No metainfo files would be removed.")

    def display(self):
        if len(self.pruned) > 0:
            print("The following metainfo files were removed:")
            for file in self.pruned:
                print(f"{file.name} at {file.path}")
        else:
            print("No metainfo files were removed.")


class PruneFolderCommand(Command):
    def __init__(
        self, service: PruneService, fs: Filesystem, metainfo_files: Set[MetainfoFile]
    ):
        self.metainfo_files = metainfo_files
        self.fs = fs
        self.service = service

    def run(self) -> PruneFolderCommandOutput:
        hashes: Set[str] = self.service.get_torrent_hashes()
        matches = {file for file in self.metainfo_files if file.info_hash in hashes}
        self.__remove_torrents(matches)
        return PruneFolderCommandOutput(matches)

    def __remove_torrents(self, metainfo_files: Set[MetainfoFile]):
        paths = {file.path for file in metainfo_files}
        for path in paths:
            if path is not None:
                self.fs.remove(path)

    def dry_run(self) -> CommandOutput:
        hashes: Set[str] = self.service.get_torrent_hashes()
        pruned = {file for file in self.metainfo_files if file.info_hash in hashes}
        return PruneFolderCommandOutput(pruned)
