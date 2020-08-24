from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from colorama import init, deinit, Fore
from torrentool.torrent import Torrent

from clutchless.console import Command, CommandResult
from clutchless.parse.find import FindArgs


@dataclass
class SearchResult:
    """Hash to found location"""

    matches: Mapping[str, Path]
    misses: Mapping[str, Path]


class FindResult(CommandResult):
    def __init__(self, result: SearchResult, finder: TorrentFinder):
        self.result: SearchResult = result
        self.finder: TorrentFinder = finder

    @staticmethod
    def print_found(torrent: Torrent, path: Path):
        print(
            Fore.GREEN + f"\N{check mark} {torrent.name} at {path.resolve(strict=True)}"
        )

    @staticmethod
    def print_missing(torrent: Torrent):
        print(Fore.RED + f"\N{ballot x} {torrent.name}")

    def output(self):
        init()
        matches_count = len(self.result.matches)
        if matches_count > 0:
            print(Fore.LIGHTWHITE_EX + f"Found {matches_count} torrents:")
            for (torrent_hash, path) in self.result.matches.items():
                torrent = self.finder.get_selected(torrent_hash).torrent
                self.print_found(torrent, path)
        misses_count = len(self.result.misses)
        if misses_count > 0:
            print(Fore.LIGHTWHITE_EX + f"Did not find {misses_count} torrents:")
            for torrent_hash in self.result.misses:
                torrent = self.finder.get_selected(torrent_hash).torrent
                self.print_missing(torrent)
        deinit()


class FindCommand(Command):
    def __init__(self, find_args: FindArgs):
        self.data_dirs = find_args.data_dirs
        self.torrent_files = find_args.torrent_files
        # TODO: How should this be simplified, does torrent register belong in sorter? Do we need *one* register shared?
        self.register: TorrentRegister = TorrentRegister(self.torrent_files)
        self.sorter: TorrentSorter = TorrentSorter(self.register.get_selected_map())
        self.finder = TorrentFinder(self.data_dirs, self.torrent_files)

    def run(self) -> FindResult:
        return FindResult(self.finder.find(), self.finder)
