import os
from pathlib import Path
from typing import Set

from clutchless.command import Command, CommandResult
from clutchless.transmission import TransmissionApi


class DryRunPruneFolderCommand(Command):
    pass


class PruneFolderCommand(Command):
    def __init__(self, torrent_files: Set[Path], client: TransmissionApi):
        self.client = client
        self.torrent_files = torrent_files

    def run(self) -> CommandResult:
        pass

    def __get_(self):
        hashes_by_id = self.client.get_torrent_hashes_by_id()

    def __prune_torrents(self):
        removed: Set[Path] = set()
        for hash_string in hash_strings:
            try:
                paths = torrents.locations[hash_string]
                for path in paths:
                    if not dry_run:
                        os.remove(path)
                    removed.add(path)
            except KeyError:
                pass
        return removed
