from dataclasses import dataclass, field
from pathlib import Path
from typing import MutableMapping, MutableSequence, Set, Sequence

from clutchless.command.command import Command, CommandOutput
from clutchless.domain.torrent import MetainfoFile
from clutchless.external.filesystem import Filesystem
from clutchless.service.torrent import AddService, FindService


@dataclass
class AddOutput(CommandOutput):
    added_torrents: MutableSequence[MetainfoFile] = field(default_factory=list)
    failed_torrents: MutableMapping[MetainfoFile, str] = field(default_factory=dict)
    duplicated_torrents: MutableMapping[MetainfoFile, str] = field(default_factory=dict)
    deleted_torrents: MutableSequence[MetainfoFile] = field(default_factory=list)

    def display(self):
        added_count = len(self.added_torrents)
        failed_count = len(self.failed_torrents)
        duplicated_count = len(self.duplicated_torrents)
        deleted_count = len(self.deleted_torrents)
        if added_count > 0:
            print("Added the following torrents:")
            for added in self.added_torrents:
                print(f"{added.name}")
        if failed_count > 0:
            print("The following torrents failed:")
            for (failed_file, error) in self.failed_torrents.items():
                print(f"{failed_file.name} because: {error}")
        if duplicated_count > 0:
            print("The following torrents are duplicates:")
            for (duplicate_file, error) in self.duplicated_torrents.items():
                print(f"{duplicate_file.name}")
        if deleted_count > 0:
            print("The following torrents were deleted:")
            for deleted_file in self.deleted_torrents:
                print(f"{deleted_file.name} at {deleted_file.path}")

    def dry_run_display(self):
        added_count = len(self.added_torrents)
        if added_count > 0:
            print("The following torrents would be added and deleted:")
            for file in self.added_torrents:
                print(f"{file.name} at {file.path}")


@dataclass
class LinkingAddOutput(CommandOutput):

    linked_torrents: MutableMapping[MetainfoFile, Path] = field(default_factory=dict)
    added_torrents: MutableSequence[MetainfoFile] = field(default_factory=list)

    failed_torrents: MutableMapping[MetainfoFile, str] = field(default_factory=dict)
    duplicated_torrents: MutableMapping[MetainfoFile, str] = field(default_factory=dict)
    deleted_torrents: MutableSequence[MetainfoFile] = field(default_factory=list)

    def add_failed(self, failures: Sequence[MetainfoFile], errors: Sequence[str]):
        # handle failures
        for (path, error) in zip(failures, errors):
            if "duplicate" in error:
                self.duplicated_torrents[path] = error
            else:
                self.failed_torrents[path] = error

    def add_no_link_succeses(self, successes: Sequence[MetainfoFile]):
        # handle success (overlap with linked)
        for path in successes:
            self.added_torrents.append(path)
            # related to fs.remove
            self.deleted_torrents.append(path)

    def add_linked_successes(
        self, metainfo_paths: Sequence[MetainfoFile], data_paths: Sequence[Path]
    ):
        # handle linked
        for (metainfo_path, data_path) in zip(metainfo_paths, data_paths):
            self.linked_torrents[metainfo_path] = data_path

    def display(self):
        linked_count = len(self.linked_torrents)
        added_count = len(self.added_torrents)
        failed_count = len(self.failed_torrents)
        duplicated_count = len(self.duplicated_torrents)
        deleted_count = len(self.deleted_torrents)
        if linked_count > 0:
            print("Linked the following torrents:")
            for (linked_file, linked_path) in self.linked_torrents.items():
                print(f"{linked_file.name} at {linked_path}")
        if added_count > 0:
            print("Added the following torrents:")
            for added in self.added_torrents:
                print(f"{added.name}")
        if failed_count > 0:
            print("The following torrents failed:")
            for (failed_file, error) in self.failed_torrents.items():
                print(f"{failed_file.name} because: {error}")
        if duplicated_count > 0:
            print("The following torrents are duplicates:")
            for (duplicate_file, error) in self.duplicated_torrents.items():
                print(f"{duplicate_file.name}")
        if deleted_count > 0:
            print("The following torrents were deleted:")
            for deleted_file in self.deleted_torrents:
                print(f"{deleted_file.name} at {deleted_file.path}")

    def dry_run_display(self):
        linked_count = len(self.linked_torrents)
        added_count = len(self.added_torrents)
        if linked_count > 0:
            print("Will add the following torrents with data:")
            for (linked_file, linked_path) in self.linked_torrents.items():
                print(f"{linked_file.name} at {linked_path}")
        if added_count > 0:
            print("Will add the following torrents without data:")
            for added in self.added_torrents:
                print(f"{added.name}")


class AddCommand(Command):
    def __init__(
        self, service: AddService, fs: Filesystem, metainfo_files: Set[MetainfoFile]
    ):
        self.service = service
        self.fs = fs
        self.metainfo_files = metainfo_files

    def __make_output(self) -> AddOutput:
        output = AddOutput()
        for (path, error) in zip(self.service.fail, self.service.error):
            if "duplicate" in error:
                output.duplicated_torrents[path] = error
            else:
                output.failed_torrents[path] = error
        for path in self.service.success:
            output.added_torrents.append(path)
            output.deleted_torrents.append(path)
        return output

    def run(self) -> AddOutput:
        for file in self.metainfo_files:
            if file.path is not None:
                self.service.add(file)
            else:
                pass  # todo: log here perhaps
        for file in self.service.success:
            self.fs.remove(file.path)
        return self.__make_output()

    def dry_run(self) -> AddOutput:
        output = AddOutput()
        output.added_torrents = set(self.metainfo_files)
        return output


class LinkingAddCommand(Command):
    def __init__(
        self,
        find_service: FindService,
        add_service: AddService,
        fs: Filesystem,
        metainfo_files: Set[MetainfoFile],
    ):
        self.find_service = find_service
        self.add_service = add_service
        self.fs = fs
        self.metainfo_files = metainfo_files

    def __make_output(self) -> LinkingAddOutput:
        output = LinkingAddOutput()
        output.add_failed(self.add_service.fail, self.add_service.error)
        output.add_no_link_succeses(self.add_service.added_without_data)
        output.add_linked_successes(self.add_service.found, self.add_service.link)
        return output

    def run(self) -> LinkingAddOutput:
        linked, rest = self.find_service.find(self.metainfo_files)
        for linked_file in linked:
            metainfo_file = linked_file.metainfo_file
            if metainfo_file.path is not None:
                self.add_service.add_with_data(metainfo_file, linked_file.location)
        for rest_file in rest:
            if rest_file.path is not None:
                self.add_service.add(rest_file)
        for success in self.add_service.success:
            if success.path:
                self.fs.remove(success.path)
        return self.__make_output()

    def dry_run(self) -> LinkingAddOutput:
        output = LinkingAddOutput()
        linked, rest = self.find_service.find(self.metainfo_files)
        for linked_file in linked:
            output.linked_torrents[linked_file.metainfo_file] = linked_file.location
        for rest_file in rest:
            output.added_torrents.append(rest_file)
        return output
