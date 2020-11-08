from dataclasses import dataclass, field
from pathlib import Path
from typing import MutableMapping, MutableSequence, Set, Tuple, Sequence

from clutchless.command.command import Command, CommandOutput
from clutchless.domain.torrent import MetainfoFile, LinkedMetainfo
from clutchless.external.filesystem import Filesystem
from clutchless.service.torrent import AddService, LinkService


@dataclass
class AddOutput(CommandOutput):
    added_torrents: MutableSequence[Path] = field(default_factory=list)
    failed_torrents: MutableMapping[Path, str] = field(default_factory=dict)
    duplicated_torrents: MutableMapping[Path, str] = field(default_factory=dict)
    deleted_torrents: MutableSequence[Path] = field(default_factory=list)

    def display(self):
        pass


@dataclass
class LinkingAddOutput(CommandOutput):
    linked_torrents: MutableMapping[Path, Path] = field(default_factory=dict)
    added_torrents: MutableSequence[Path] = field(default_factory=list)

    failed_torrents: MutableMapping[Path, str] = field(default_factory=dict)
    duplicated_torrents: MutableMapping[Path, str] = field(default_factory=dict)
    deleted_torrents: MutableSequence[Path] = field(default_factory=list)

    def add_failed(self, failures: Sequence[Path], errors: Sequence[str]):
        # handle failures
        for (path, error) in zip(failures, errors):
            if "duplicate" in error:
                self.duplicated_torrents[path] = error
            else:
                self.failed_torrents[path] = error

    def add_no_link_succeses(self, successes: Sequence[Path]):
        # handle success (overlap with linked)
        for path in successes:
            self.added_torrents.append(path)
            # related to fs.remove
            self.deleted_torrents.append(path)

    def add_linked_successes(self, metainfo_path: Sequence[Path], data_path: Sequence[Path]):
        # handle linked
        for (metainfo_path, data_path) in zip(metainfo_path, data_path):
            self.linked_torrents[metainfo_path] = data_path

    def display(self):
        pass


class AddCommand(Command):
    def __init__(self, service: AddService, fs: Filesystem, metainfo_paths: Set[Path]):
        self.service = service
        self.fs = fs
        self.metainfo_paths = metainfo_paths

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
        for path in self.metainfo_paths:
            self.service.add(path)
        for path in self.service.success:
            self.fs.remove(path)
        return self.__make_output()


class LinkingAddCommand(Command):
    def __init__(self, link_service: LinkService, add_service: AddService, fs: Filesystem, metainfo_files: Set[MetainfoFile]):
        self.link_service = link_service
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
        linked, rest = self.link_service.find(self.metainfo_files)
        for file in linked:
            self.add_service.add_with_data(file.metainfo_file.path, file.data)
        for file in rest:
            self.add_service.add(file.path)
        for path in self.add_service.success:
            self.fs.remove(path)
        return self.__make_output()