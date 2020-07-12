from dataclasses import dataclass
from pathlib import Path
from typing import Set, Mapping, KeysView

from colorama import init, deinit, Fore
from torrentool.torrent import Torrent

from clutchless.console import Command, CommandResult
from clutchless.parse.find import FindArgs
from clutchless.search import TorrentSorter, TorrentRegister


@dataclass
class SearchResult:
    matches: Mapping[str, Path]
    misses: Mapping[str, Path]


class FindResult(CommandResult):
    def __init__(self, result: SearchResult, register: TorrentRegister):
        self.result: SearchResult = result
        self.register = register

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
                torrent = self.register.get_selected(torrent_hash).torrent
                self.print_found(torrent, path)
        misses_count = len(self.result.misses)
        if misses_count > 0:
            print(Fore.LIGHTWHITE_EX + f"Did not find {misses_count} torrents:")
            for torrent_hash in self.result.misses:
                torrent = self.register.get_selected(torrent_hash).torrent
                self.print_missing(torrent)
        deinit()


class TorrentFinder:
    def __init__(self, data_dirs: Set[Path], torrent_files: Set[Path]):
        self.data_dirs = data_dirs
        self.torrent_files = torrent_files
        self.sorter: TorrentSorter = TorrentSorter(torrent_files)

    def find(self) -> SearchResult:
        matches: Mapping[str, Path] = self.sorter.find_matches(self.data_dirs)
        register = self.sorter.register
        all_hashes = register.keys()
        missed_keys: Set[str] = all_hashes - matches.keys()
        missed_torrents = {k: v for k, v in register.items() if k in missed_keys}
        return SearchResult(matches, missed_torrents)


class FindCommand(Command):
    def __init__(self, find_args: FindArgs):
        self.data_dirs = find_args.data_dirs
        self.torrent_files = find_args.torrent_files
        self.sorter: TorrentSorter = TorrentSorter(self.torrent_files)
        self.finder = TorrentFinder(self.data_dirs, self.torrent_files)

    def run(self) -> FindResult:
        return FindResult(self.finder.find(), self.sorter.register)
