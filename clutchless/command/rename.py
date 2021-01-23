import logging
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, MutableMapping, Set

from clutchless.command.command import Command, CommandOutput
from clutchless.domain.torrent import MetainfoFile
from clutchless.external.filesystem import Filesystem

logger = logging.getLogger(__name__)


@dataclass
class RenameOutput(CommandOutput):
    actionable: Mapping[MetainfoFile, str] = field(default_factory=dict)
    already_exists: Mapping[MetainfoFile, Path] = field(default=dict)
    selected: Mapping[MetainfoFile, Set[MetainfoFile]] = field(default=dict)

    def dry_run_display(self):
        actionable_count = len(self.actionable)
        already_exists_count = len(self.already_exists)
        selected_count = len(self.selected)
        if actionable_count + already_exists_count + selected_count > 0:
            if selected_count > 0:
                print(f"Found {selected_count} clashing renames:")
                for file, others in self.selected.items():
                    print(f"\N{triangular bullet} {file.name} has dupes:")
                    for other in others:
                        print(f"\N{hyphen bullet} {other}")
            if actionable_count > 0:
                print(f"Found {actionable_count} metainfo files to rename:")
                for file, new_name in self.actionable.items():
                    print(f"{file.path} to {new_name}")
            if already_exists_count > 0:
                print(
                    f"Found {already_exists_count} metainfo files with new names that already exist:"
                )
                for file, new_path in self.already_exists.items():
                    print(f"{file.path} with new name {new_path.name}")
        else:
            print("No files found to rename.")

    def display(self):
        actionable_count = len(self.actionable)
        already_exists_count = len(self.already_exists)
        selected_count = len(self.selected)
        if actionable_count + already_exists_count + selected_count > 0:
            if selected_count > 0:
                print(f"Found {selected_count} clashing renames:")
                for file, others in self.selected.items():
                    print(f"\N{triangular bullet} {file.name} has dupes:")
                    for other in others:
                        print(f"\N{hyphen bullet} {other}")
            if actionable_count > 0:
                print(f"Renamed {actionable_count} metainfo files:")
                for file, new_name in self.actionable.items():
                    print(f"{file.path} to {new_name}")
            if already_exists_count > 0:
                print(
                    f"Found {already_exists_count} metainfo files with new names that already exist:"
                )
                for file, new_path in self.already_exists.items():
                    print(f"{file.path} with new name {new_path.name}")
        else:
            print("No files found to rename.")


def get_new_name(file: MetainfoFile) -> str:
    return file.name + "." + file.info_hash[:16] + ".torrent"


def get_competing_renames(
    new_names_by_file: Mapping[MetainfoFile, str]
) -> Mapping[Path, Set[MetainfoFile]]:
    seen = defaultdict(set)
    for file, name in new_names_by_file.items():
        new_path = file.path.parent / name
        seen[new_path].add(file)
    return {path: files for path, files in seen.items() if len(files) > 1}


def select(
    dupes: Mapping[Path, Set[MetainfoFile]]
) -> Mapping[MetainfoFile, Set[MetainfoFile]]:
    # todo: how do we ensure that this doesn't change? is Set iteration sorted?
    def split_first(s):
        iterator = iter(s)
        return next(iterator), set(iterator)

    result: MutableMapping[MetainfoFile, Set[MetainfoFile]] = {}
    for path, files in dupes.items():
        first, others = split_first(files)
        result[first] = others
    return result


def get_actionable(
    new_names_by_file: Mapping[MetainfoFile, str],
    already_exists: Mapping[MetainfoFile, Path],
    selected: Mapping[MetainfoFile, Set[MetainfoFile]],
) -> Mapping[MetainfoFile, str]:
    return {
        file: new_name
        for file, new_name in new_names_by_file.items()
        if file not in already_exists and file in selected
    }


class RenameCommand(Command):
    def __init__(self, fs: Filesystem, files: Iterable[MetainfoFile]):
        self.fs = fs
        self.files = set(files)

    def get_new_names_by_file(self) -> MutableMapping[MetainfoFile, str]:
        new_names_by_file: MutableMapping[MetainfoFile, str] = {}
        for file in self.files:
            new_name = get_new_name(file)
            if new_name != file.path.name:
                new_names_by_file[file] = new_name
        return new_names_by_file

    def get_already_exists(
        self, new_names_by_file: Mapping[MetainfoFile, str]
    ) -> MutableMapping[MetainfoFile, Path]:
        already_exists = {}
        for file, new_name in new_names_by_file.items():
            new_file = file.path.parent / new_name
            if self.fs.exists(new_file):
                already_exists[file] = new_file
        return already_exists

    def dry_run(self) -> CommandOutput:
        new_names_by_file = self.get_new_names_by_file()
        already_exists = self.get_already_exists(new_names_by_file)
        competing = get_competing_renames(new_names_by_file)
        selected = select(competing)
        actionable = get_actionable(new_names_by_file, already_exists, selected)
        return RenameOutput(actionable, already_exists, selected)

    def run(self) -> CommandOutput:
        new_names_by_file = self.get_new_names_by_file()
        already_exists = self.get_already_exists(new_names_by_file)
        competing = get_competing_renames(new_names_by_file)
        selected = select(competing)
        actionable = get_actionable(new_names_by_file, already_exists, selected)
        for file, new_name in actionable.items():
            logger.debug(f"renaming {file.path} to {new_name}")
            self.fs.rename(file.path, new_name)
        return RenameOutput(actionable, already_exists, selected)
