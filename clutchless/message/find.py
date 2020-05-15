from pathlib import Path
from typing import Set, Mapping

from colorama import init, deinit, Fore
from torrentool.torrent import Torrent


def print_find(matches: Mapping[Torrent, Path], misses: Set[Torrent]):
    init()
    matches_count = len(matches)
    if matches_count > 0:
        print(Fore.LIGHTWHITE_EX + f"Found {matches_count} torrents:")
        for (torrent, path) in matches.items():
            print_found(torrent, path)
    misses_count = len(misses)
    if misses_count > 0:
        print(Fore.LIGHTWHITE_EX + f"Did not find {misses_count} torrents:")
        for torrent in misses:
            print_missing(torrent)
    deinit()


def print_found(torrent: Torrent, path: Path):
    print(Fore.GREEN + f"\N{check mark} {torrent.name} at {path.resolve(strict=True)}")


def print_missing(torrent: Torrent):
    print(Fore.RED + f"\N{ballot x} {torrent.name}")
