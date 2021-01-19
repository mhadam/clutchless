import logging
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Set, Mapping, MutableMapping, Sequence

from clutchless.command.command import CommandOutput, Command
from clutchless.domain.torrent import MetainfoFile
from clutchless.external.filesystem import Filesystem

logger = logging.getLogger(__name__)


@dataclass
class DedupeOutput(CommandOutput):
    deleted_paths_by_file: Mapping[MetainfoFile, Set[Path]] = field(default_factory=set)
    remaining_path_by_file: Mapping[MetainfoFile, Path] = field(default_factory=map)

    def display(self):
        duplicate_count = sum(
            [len(dupes) for dupes in self.deleted_paths_by_file.values()]
        )
        if duplicate_count > 0:
            print(f"Deleted {duplicate_count} duplicate files:")
            for (file, dupes) in self.deleted_paths_by_file.items():
                print(f"duplicates of {file.name}:")
                for dupe in dupes:
                    print(f"{dupe}")
        else:
            print(f"No duplicates found")

    def dry_run_display(self):
        duplicate_count = sum(
            [len(dupes) for dupes in self.deleted_paths_by_file.values()]
        )
        if duplicate_count > 0:
            print(f"Would delete {duplicate_count} duplicate files:")
            for (file, dupes) in self.deleted_paths_by_file.items():
                print(f"\N{triangular bullet} {file.name}:")
                for dupe in dupes:
                    print(f"\N{hyphen bullet} {dupe}")
        else:
            print(f"No duplicates found")


@dataclass
class DedupeCommand(Command):
    def __init__(self, fs: Filesystem, files: Sequence[MetainfoFile]):
        self.fs = fs
        self.files = files

    def _join_paths(self) -> Mapping[MetainfoFile, Set[Path]]:
        result = defaultdict(set)
        for file in self.files:
            result[file].add(file.path)
        return result

    def _delete(self, paths: Set[Path]):
        for path in paths:
            self.fs.remove(path)

    def dry_run(self) -> CommandOutput:
        logger.debug(f"{[file.name for file in self.files]}")
        deleted_paths_by_file: MutableMapping[MetainfoFile, Set[Path]] = {}
        remaining_path_by_file: MutableMapping[MetainfoFile, Path] = {}
        paths_by_file = self._join_paths()
        logger.debug(f"paths_by_file {paths_by_file}")
        for (metainfo_file, paths) in paths_by_file.items():
            remaining_path_by_file[metainfo_file] = paths.pop()
            if paths:
                deleted_paths_by_file[metainfo_file] = paths
        return DedupeOutput(deleted_paths_by_file, remaining_path_by_file)

    def run(self) -> CommandOutput:
        deleted_paths_by_file: MutableMapping[MetainfoFile, Set[Path]] = {}
        remaining_path_by_file: MutableMapping[MetainfoFile, Path] = {}
        paths_by_file = self._join_paths()
        for (metainfo_file, paths) in paths_by_file.items():
            remaining_path_by_file[metainfo_file] = paths.pop()
            if paths:
                self._delete(paths)
                deleted_paths_by_file[metainfo_file] = paths
        return DedupeOutput(deleted_paths_by_file, remaining_path_by_file)
