from dataclasses import dataclass, field
from typing import Iterable, Mapping, MutableMapping

from clutchless.command.command import Command, CommandOutput
from clutchless.domain.torrent import MetainfoFile
from clutchless.external.filesystem import Filesystem


@dataclass
class RenameOutput(CommandOutput):
    new_names_by_file: Mapping[MetainfoFile, str] = field(default_factory=dict)

    def dry_run_display(self):
        names_count = len(self.new_names_by_file)
        if names_count > 0:
            print(f"Found {names_count} metainfo files to rename:")
            for file, new_name in self.new_names_by_file.items():
                print(f"{file.path} to {new_name}")
        else:
            print("No files found to rename.")

    def display(self):
        names_count = len(self.new_names_by_file)
        if names_count > 0:
            print(f"Renamed {names_count} metainfo files:")
            for file, new_name in self.new_names_by_file.items():
                print(f"{file.path} to {new_name}")
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

    def dry_run(self) -> CommandOutput:
        new_names_by_file = self.get_new_names_by_file()
        return RenameOutput(new_names_by_file)

    def run(self) -> CommandOutput:
        new_names_by_file = self.get_new_names_by_file()
        for file, new_name in new_names_by_file:
            self.fs.rename(file.path, new_name)
        return RenameOutput(new_names_by_file)
