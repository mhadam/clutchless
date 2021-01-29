import itertools
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable, Mapping, MutableMapping, Set, Tuple

from clutchless.command.command import Command, CommandOutput
from clutchless.domain.torrent import MetainfoFile
from clutchless.external.filesystem import Filesystem

logger = logging.getLogger(__name__)


@dataclass
class RenameOutput(CommandOutput):
    new_name_by_actionable_file: Mapping[MetainfoFile, str] = field(
        default_factory=dict
    )
    new_name_by_existing_file: Mapping[MetainfoFile, str] = field(default=dict)
    others_by_selected: Mapping[MetainfoFile, Set[MetainfoFile]] = field(default=dict)

    def dry_run_display(self):
        actionable_count = len(self.new_name_by_actionable_file)
        already_exists_count = len(self.new_name_by_existing_file)
        selected_count = len(self.others_by_selected)
        if actionable_count + already_exists_count + selected_count > 0:
            if selected_count > 0:
                print(f"Found {selected_count} clashing renames:")
                for file, others in self.others_by_selected.items():
                    print(f"\N{triangular bullet} {file.name} has dupes:")
                    print(f"\N{hyphen bullet} {file.path} (selected)")
                    for other in others:
                        print(f"\N{hyphen bullet} {other.path}")
            if actionable_count > 0:
                print(f"Found {actionable_count} metainfo files to rename:")
                for file, new_name in self.new_name_by_actionable_file.items():
                    print(f"{file.path} to {new_name}")
            if already_exists_count > 0:
                print(
                    f"Found {already_exists_count} metainfo files with new names that already exist:"
                )
                for file, new_name in self.new_name_by_existing_file.items():
                    print(f"{file.path} with new name {new_name}")
        else:
            print("No files found to rename.")

    def display(self):
        actionable_count = len(self.new_name_by_actionable_file)
        already_exists_count = len(self.new_name_by_existing_file)
        selected_count = len(self.others_by_selected)
        if actionable_count + already_exists_count + selected_count > 0:
            if selected_count > 0:
                print(f"Found {selected_count} clashing renames:")
                for file, others in self.others_by_selected.items():
                    print(f"\N{triangular bullet} {file.name} has dupes:")
                    print(f"\N{hyphen bullet} {file.path} (selected)")
                    for other in others:
                        print(f"\N{hyphen bullet} {other.path}")
            if actionable_count > 0:
                print(f"Renamed {actionable_count} metainfo files:")
                for file, new_name in self.new_name_by_actionable_file.items():
                    print(f"{file.path} to {new_name}")
            if already_exists_count > 0:
                print(
                    f"Found {already_exists_count} metainfo files with new names that already exist:"
                )
                for file, new_path in self.new_name_by_existing_file.items():
                    print(f"{file.path} with new name {new_path}")
        else:
            print("No files found to rename.")


def get_new_name(file: MetainfoFile) -> str:
    return file.name + "." + file.info_hash[:16] + ".torrent"


def get_hash(s: Set[MetainfoFile]):
    def first(i):
        for e in i:
            break
        return e

    return first(s).info_hash


def get_clashing_renames(
    files: Iterable[MetainfoFile],
) -> Tuple[Mapping[str, Set[MetainfoFile]], Set[MetainfoFile]]:
    seen = defaultdict(set)
    for file in files:
        name = get_new_name(file)
        new_path = file.path.parent / name
        seen[new_path].add(file)
    clashing: MutableMapping[str, Set[MetainfoFile]] = {}
    not_clashing: Set[MetainfoFile] = set()
    for path, files in seen.items():
        if len(files) > 1:
            clashing[get_hash(files)] = files
        else:
            for file in files:
                not_clashing.add(file)
    return clashing, not_clashing


def select(
    clashing: Mapping[str, Set[MetainfoFile]]
) -> Mapping[MetainfoFile, Set[MetainfoFile]]:
    # todo: how do we ensure that this doesn't change? is Set iteration sorted?
    def split_first(s):
        iterator = iter(sorted(s))
        return next(iterator), set(iterator)

    result: MutableMapping[MetainfoFile, Set[MetainfoFile]] = {}
    for info_hash, files in clashing.items():
        first, others = split_first(files)
        result[first] = others
    return result


class RenameCommand(Command):
    def __init__(self, fs: Filesystem, files: Iterable[MetainfoFile]):
        self.fs = fs
        self.files = set(files)

    def get_proper_and_improper_files(
        self,
    ) -> Tuple[Set[MetainfoFile], Set[MetainfoFile]]:
        """This sorts them into files with same/different new file name based on metainfo"""
        proper = set()
        improper = set()
        for file in self.files:
            new_name = get_new_name(file)
            if new_name != file.path.name:
                improper.add(file)
            else:
                proper.add(file)
        return proper, improper

    def get_actionable_and_already_exists(
        self,
        others_by_selected: Mapping[MetainfoFile, Set[MetainfoFile]],
        not_clashing: Set[MetainfoFile],
    ) -> Tuple[Mapping[MetainfoFile, str], Mapping[MetainfoFile, str]]:
        already_exists = {}
        actionable = {}
        for selected, others in others_by_selected.items():
            new_name = get_new_name(selected)
            new_file = selected.path.parent / new_name
            if self.fs.exists(new_file):
                already_exists[selected] = new_name
            else:
                actionable[selected] = new_name
        for file in not_clashing:
            new_name = get_new_name(file)
            new_file = file.path.parent / new_name
            if self.fs.exists(new_file):
                already_exists[file] = new_name
            else:
                actionable[file] = new_name
        return actionable, already_exists

    def dry_run(self) -> RenameOutput:
        proper, improper = self.get_proper_and_improper_files()
        clashing, not_clashing = get_clashing_renames(improper)
        others_by_selected: Mapping[MetainfoFile, Set[MetainfoFile]] = select(clashing)
        actionable, already_exists = self.get_actionable_and_already_exists(
            others_by_selected, not_clashing
        )
        return RenameOutput(actionable, already_exists, others_by_selected)

    def run(self) -> RenameOutput:
        proper, improper = self.get_proper_and_improper_files()
        clashing, not_clashing = get_clashing_renames(improper)
        others_by_selected: Mapping[MetainfoFile, Set[MetainfoFile]] = select(clashing)
        actionable, already_exists = self.get_actionable_and_already_exists(
            others_by_selected, not_clashing
        )
        for file, new_name in actionable.items():
            logger.debug(f"renaming {file.path} to {new_name}")
            self.fs.rename(file.path, new_name)
        return RenameOutput(actionable, already_exists, others_by_selected)
