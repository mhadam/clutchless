from pathlib import Path

from colorama import init, deinit, Fore, Style
from torrentool.torrent import Torrent

from clutchless.subcommand.add import AddResult


def print_add(add_result: AddResult, dry_run: bool = False):
    init()
    if dry_run:
        print(f"These are dry-run results.")
    added_count = len(add_result.added_torrents)
    if added_count > 0:
        print(Fore.LIGHTWHITE_EX + f"Added {added_count} torrents:")
        for (torrent, name) in add_result.added_torrents.items():
            try:
                path: Path = add_result.matches[torrent]
                print_added(name, path)
            except KeyError:
                print_added(name)
    duplicated_count = len(add_result.duplicated_torrents)
    if duplicated_count > 0:
        print(
            Fore.LIGHTWHITE_EX
            + f"There are {duplicated_count} torrents already in Transmission:"
        )
        for (torrent, _) in add_result.duplicated_torrents.items():
            try:
                path: Path = add_result.matches[torrent]
                print_duplicate(torrent, path)
            except KeyError:
                print_duplicate(torrent)
    failed_count = len(add_result.failed_torrents)
    if failed_count > 0:
        print(Fore.LIGHTWHITE_EX + f"Cannot locate {failed_count} torrents:")
        for (torrent, failure_reason) in add_result.failed_torrents.items():
            print_missed(torrent, failure_reason)
    if len(add_result.deleted_torrents) > 0:
        print(Fore.LIGHTWHITE_EX + f"Deleted the following torrents:")
        for deletion in add_result.deleted_torrents:
            print(Fore.LIGHTWHITE_EX + f"{deletion.resolve(strict=True)}")
    if added_count + duplicated_count + failed_count == 0:
        print("Nothing found to add.")
    deinit()


def print_missed(torrent: Torrent, reason: str):
    print(Fore.RED + f"\N{ballot x} {torrent.name} because: {reason}")


def print_added(name: str, path: Path = None):
    if path:
        print(Fore.GREEN + f"\N{check mark} {name} at {path.resolve(strict=True)}")
    else:
        print(Fore.GREEN + f"\N{check mark} {name}")


def print_duplicate(torrent: Torrent, path: Path = None):
    if path:
        print(Fore.RED + f"\N{ballot x} {torrent.name} at {path.resolve(strict=True)}")
    else:
        print(Fore.RED + f"\N{ballot x} {torrent.name}")
