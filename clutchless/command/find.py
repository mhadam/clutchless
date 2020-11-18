from typing import Set

from colorama import init, deinit, Fore

from clutchless.command.command import Command, CommandOutput
from clutchless.domain.torrent import MetainfoFile
from clutchless.external.metainfo import TorrentData
from clutchless.service.torrent import FindService
from clutchless.spec.find import FindArgs


class FindOutput(CommandOutput):
    def __init__(self, found: Set[TorrentData], missing: Set[MetainfoFile]):
        self.found = found
        self.missing = missing

    @staticmethod
    def print_found(found: TorrentData):
        name = found.metainfo_file.name
        path = found.metainfo_file.path
        print(Fore.GREEN + f"\N{check mark} {name} at {path}")

    @staticmethod
    def print_missing(torrent: MetainfoFile):
        print(Fore.RED + f"\N{ballot x} {torrent.name}")

    def display(self):
        init()
        matches_count = len(self.found)
        if matches_count > 0:
            print(Fore.LIGHTWHITE_EX + f"Found {matches_count} torrents:")
            for linked in self.found:
                self.print_found(linked)
        misses_count = len(self.missing)
        if misses_count > 0:
            print(Fore.LIGHTWHITE_EX + f"Did not find {misses_count} torrents:")
            for file in self.missing:
                self.print_missing(file)
        deinit()


class FindCommand(Command):
    def __init__(
        self,
        find_service: FindService,
        metainfo_files: Set[MetainfoFile],
    ):
        self.find_service = find_service
        self.metainfo_files = metainfo_files

    def run(self) -> FindOutput:
        linked, rest = self.find_service.find(self.metainfo_files)
        output = FindOutput(linked, rest)
        return output
