import os
from dataclasses import dataclass
from typing import Set, Mapping

from clutchless.command import Command, CommandResult
from clutchless.domain.torrent import MetainfoFile
from clutchless.external.transmission import TransmissionApi


@dataclass
class DryRunPruneFolderCommandResult(CommandResult):
    pruned: Set[MetainfoFile]

    def output(self):
        if len(self.pruned) > 0:
            print("The following metainfo files would be removed:")
            for file in self.pruned:
                print(f"{file.name} at {file.path}")
        else:
            print("No metainfo files would be removed.")


class MetainfoFileClientMatcher:
    def __init__(self, client: TransmissionApi, metainfo_files: Set[MetainfoFile]):
        self.client = client
        self.metainfo_files = metainfo_files

    def get_metainfo_files_by_id(
        self,
    ) -> Mapping[int, MetainfoFile]:
        client_id_by_hash: Mapping[str, int] = self.client.get_torrent_ids_by_hash()
        metainfo_files_by_hash = self.__get_metainfo_files_by_hash()
        return {
            client_id: metainfo_files_by_hash[metainfo_hash]
            for (metainfo_hash, client_id) in client_id_by_hash.items()
            if metainfo_hash in metainfo_files_by_hash
        }

    def __get_metainfo_files_by_hash(self) -> Mapping[str, MetainfoFile]:
        return {file.info_hash: file for file in self.metainfo_files}


class DryRunPruneFolderCommand(Command):
    def __init__(self, client: TransmissionApi, metainfo_files: Set[MetainfoFile]):
        self.client = client
        self.metainfo_files = metainfo_files

    def run(self) -> DryRunPruneFolderCommandResult:
        matcher = MetainfoFileClientMatcher(self.client, self.metainfo_files)
        metainfo_files_by_id = matcher.get_metainfo_files_by_id()
        pruned = set(metainfo_files_by_id.values())
        return DryRunPruneFolderCommandResult(pruned)


@dataclass
class PruneFolderCommandResult(CommandResult):
    pruned: Set[MetainfoFile]

    def output(self):
        if len(self.pruned) > 0:
            print("The following metainfo files were removed:")
            for file in self.pruned:
                print(f"{file.name} at {file.path}")
        else:
            print("No metainfo files were removed.")


class PruneFolderCommand(Command):
    def __init__(self, client: TransmissionApi, metainfo_files: Set[MetainfoFile]):
        self.client = client
        self.metainfo_files = metainfo_files

    def run(self) -> PruneFolderCommandResult:
        matcher = MetainfoFileClientMatcher(self.client, self.metainfo_files)
        metainfo_files_by_id = matcher.get_metainfo_files_by_id()
        metainfo_files = set(metainfo_files_by_id.values())
        self.__remove_torrents(metainfo_files)
        return PruneFolderCommandResult(metainfo_files)

    def __remove_torrents(self, metainfo_files: Set[MetainfoFile]):
        paths = {file.path for file in metainfo_files}
        for path in paths:
            os.remove(path)
