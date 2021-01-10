import logging
from typing import Set

from colorama import Fore

from clutchless.command.command import Command, CommandOutput
from clutchless.domain.torrent import MetainfoFile
from clutchless.external.metainfo import TorrentData
from clutchless.service.torrent import FindService

logger = logging.getLogger(__name__)


class FindOutput(CommandOutput):
    def __init__(self, found: Set[TorrentData], missing: Set[MetainfoFile]):
        self.found = found
        self.missing = missing

    @staticmethod
    def print_found(found: TorrentData):
        name = found.metainfo_file.name
        path = found.location
        print(Fore.GREEN + f"\N{check mark} {name} at {path}")

    @staticmethod
    def print_missing(torrent: MetainfoFile):
        print(Fore.RED + f"\N{ballot x} {torrent.name}")

    def display(self):
        matches_count = len(self.found)
        if matches_count > 0:
            print(f"Found {matches_count} torrents:")
            for linked in self.found:
                self.print_found(linked)
        misses_count = len(self.missing)
        if misses_count > 0:
            print(f"Did not find {misses_count} torrents:")
            for file in self.missing:
                self.print_missing(file)

    def dry_run_display(self):
        raise NotImplementedError


class FindCommand(Command):
    def __init__(
        self,
        find_service: FindService,
        metainfo_files: Set[MetainfoFile],
    ):
        self.find_service = find_service
        self.metainfo_files = metainfo_files

    def run(self) -> FindOutput:
        results = self.find_service.find(self.metainfo_files)
        found = {result for result in results if result.location is not None}
        rest = {result.metainfo_file for result in results if result.location is None}
        logger.info(f"finished with results {found, rest}")
        output = FindOutput(found, rest)
        return output

    def dry_run(self) -> CommandOutput:
        raise NotImplementedError
