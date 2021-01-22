import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, MutableMapping

from clutchless.command.command import Command, CommandOutput
from clutchless.domain.torrent import MetainfoFile
from clutchless.external.filesystem import Filesystem

logger = logging.getLogger(__name__)


@dataclass
class RenameOutput(CommandOutput):
    new_names_by_file: Mapping[MetainfoFile, str] = field(default_factory=dict)
    already_exists: Mapping[MetainfoFile, Path] = field(default=dict)

    def dry_run_display(self):
        names_count = len(self.new_names_by_file)
        already_exists_count = len(self.already_exists)
        if names_count + already_exists_count > 0:
            if names_count > 0:
                print(f"Found {names_count} metainfo files to rename:")
                for file, new_name in self.new_names_by_file.items():
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
        names_count = len(self.new_names_by_file)
        already_exists_count = len(self.already_exists)
        if names_count + already_exists_count > 0:
            if names_count > 0:
                print(f"Renamed {names_count} metainfo files:")
                for file, new_name in self.new_names_by_file.items():
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

    def get_actionable(
        self,
        new_names_by_file: Mapping[MetainfoFile, str],
        already_exists: MutableMapping[MetainfoFile, Path],
    ) -> MutableMapping[MetainfoFile, str]:
        return {
            file: new_name
            for file, new_name in new_names_by_file.items()
            if file not in already_exists
        }

    def dry_run(self) -> CommandOutput:
        new_names_by_file = self.get_new_names_by_file()
        already_exists = self.get_already_exists(new_names_by_file)
        actionable = self.get_actionable(new_names_by_file, already_exists)
        return RenameOutput(actionable, already_exists)

    def run(self) -> CommandOutput:
        new_names_by_file = self.get_new_names_by_file()
        already_exists = self.get_already_exists(new_names_by_file)
        actionable = self.get_actionable(new_names_by_file, already_exists)
        for file, new_name in new_names_by_file.items():
            if file not in already_exists:
                logger.debug(f"renaming {file.path} to {new_name}")
                self.fs.rename(file.path, new_name)
        return RenameOutput(actionable, already_exists)
