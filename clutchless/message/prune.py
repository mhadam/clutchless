from pathlib import Path
from typing import Set

from colorama import Fore, init, deinit

from clutchless.subcommand.prune.client import PrunedResult


def print_pruned(result: PrunedResult, dry_run: bool):
    init()
    if dry_run:
        print("These are dry-run results.")
    if len(result.successes) > 0:
        print("Following torrents have been pruned:")
        for success in result.successes:
            print(Fore.GREEN + f"\N{check mark} {success.name}")
    if len(result.failures) > 0:
        print("Following torrents have failed to be pruned:")
        for failure in result.failures:
            print(
                Fore.RED
                + f"\N{ballot x} {failure.name} failed to be pruned because: {failure.error_string}."
            )
    if len(result.successes) + len(result.failures) == 0:
        print("No torrents in Transmission found to prune.")
    deinit()


def print_pruned_files(files: Set[Path]):
    init()
    if len(files) > 0:
        print("Pruned these files:")
        for file in files:
            print(Fore.GREEN + f"\N{check mark} {file}")
    else:
        print("No files found to prune.")
    deinit()
