from dataclasses import dataclass, field
from pathlib import Path
from typing import MutableMapping, MutableSequence, Set, Tuple

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
        # handle failures
        for (path, error) in zip(self.add_service.fail, self.add_service.error):
            if "duplicate" in error:
                output.duplicated_torrents[path] = error
            else:
                output.failed_torrents[path] = error
        # handle success (overlap with linked)
        for path in self.add_service.added_without_data:
            output.added_torrents.append(path)
            # related to fs.remove
            output.deleted_torrents.append(path)
        # handle linked
        for (metainfo_path, data_path) in zip(self.add_service.found, self.add_service.link):
            output.linked_torrents[metainfo_path] = data_path
        return output

    def __get_linked_and_rest(self) -> Tuple[Set[LinkedMetainfo], Set[MetainfoFile]]:
        linked_metainfos: Set[LinkedMetainfo] = self.link_service.find(self.metainfo_files)
        linked_metainfo_files: Set[MetainfoFile] = {metainfo.metainfo_file for metainfo in linked_metainfos}
        rest: Set[MetainfoFile] = self.metainfo_files - linked_metainfo_files
        return linked_metainfos, rest

    def run(self) -> LinkingAddOutput:
        linked, rest = self.__get_linked_and_rest()
        for file in linked:
            self.add_service.add_with_data(file.metainfo_file.path, file.data)
        for file in rest:
            self.add_service.add(file.path)
        for path in self.add_service.success:
            self.fs.remove(path)
        return self.__make_output()
