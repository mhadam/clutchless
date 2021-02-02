import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Set, Mapping, MutableMapping, Sequence

from clutchless.command.command import CommandOutput, Command
from clutchless.domain.torrent import MetainfoFile
from clutchless.external.filesystem import Filesystem

logger = logging.getLogger(__name__)


@dataclass
class DedupeOutput(CommandOutput):
    deleted_files_by_hash: Mapping[str, Set[MetainfoFile]] = field(default_factory=set)
    remaining_files: Set[MetainfoFile] = field(default_factory=map)

    def display(self):
        duplicate_count = sum(
            [len(dupes) for _, dupes in self.deleted_files_by_hash.items()]
        )
        if duplicate_count > 0:
            print(f"Deleted {duplicate_count} duplicate files:")
            for (info_hash, files) in self.deleted_files_by_hash.items():
                first_file: MetainfoFile = next(iter(files))
                print(f"\N{triangular bullet} {first_file.name}:")
                for file in files:
                    print(f"\N{hyphen bullet} {file.path}")
        else:
            print(f"No duplicates found")

    def dry_run_display(self):
        duplicate_count = sum(
            [len(dupes) for _, dupes in self.deleted_files_by_hash.items()]
        )
        if duplicate_count > 0:
            print(f"Would delete {duplicate_count} duplicate files:")
            for (info_hash, files) in self.deleted_files_by_hash.items():
                first_file: MetainfoFile = next(iter(files))
                print(f"\N{triangular bullet} {first_file.name}:")
                for file in files:
                    print(f"\N{hyphen bullet} {file.path}")
        else:
            print(f"No duplicates found")


def _split_first(s):
    iterator = iter(sorted(s))
    return next(iterator), set(iterator)


@dataclass
class DedupeCommand(Command):
    def __init__(self, fs: Filesystem, files: Sequence[MetainfoFile]):
        self.fs = fs
        self.files = files

    def _join_paths(self) -> Mapping[str, Set[MetainfoFile]]:
        result = defaultdict(set)
        for file in self.files:
            result[file.info_hash].add(file)
        return result

    def _delete(self, files: Set[MetainfoFile]):
        for file in files:
            self.fs.remove(file.path)

    def dry_run(self) -> DedupeOutput:
        for file in self.files:
            logger.debug(f"{file.name}")
        deleted_files_by_hash: MutableMapping[str, Set[MetainfoFile]] = {}
        remaining_files: Set[MetainfoFile] = set()
        paths_by_file = self._join_paths()
        for (info_hash, files) in paths_by_file.items():
            logger.debug(f"{info_hash} and files {files}")
            selected, rest = _split_first(files)
            remaining_files.add(selected)
            if rest:
                deleted_files_by_hash[info_hash] = rest
        return DedupeOutput(deleted_files_by_hash, remaining_files)

    def run(self) -> DedupeOutput:
        deleted_files_by_hash: MutableMapping[str, Set[MetainfoFile]] = {}
        remaining_files: Set[MetainfoFile] = set()
        paths_by_file = self._join_paths()
        for (info_hash, files) in paths_by_file.items():
            logger.debug(f"{info_hash} and files {files}")
            selected, rest = _split_first(files)
            remaining_files.add(selected)
            if rest:
                self._delete(rest)
                deleted_files_by_hash[info_hash] = rest
        return DedupeOutput(deleted_files_by_hash, remaining_files)
