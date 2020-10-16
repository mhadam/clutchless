from dataclasses import dataclass, field
from pathlib import Path
from shutil import copy
from typing import Mapping, MutableMapping, MutableSequence, Sequence

from clutchless.command.command import Command, CommandResult, CommandResultAccumulator
from clutchless.external.transmission import TransmissionApi


@dataclass
class ArchiveCount:
    archived: int
    existing: int


@dataclass
class ArchiveResult(CommandResult):
    copied: MutableMapping[int, Path] = field(default_factory=dict)
    already_exist: MutableSequence["ArchiveAlreadyExists"] = field(default_factory=list)

    def output(self):
        for (torrent_id, path) in self.copied.items():
            print(f"Copied {torrent_id} to {path}")
        for event in self.already_exist:
            print(
                f"Already exists {event.torrent_id} at {event.copied_path} because {event.error}"
            )


@dataclass
class ArchiveCopied(CommandResultAccumulator):
    torrent_id: int
    copied_path: Path

    def accumulate(self, result: ArchiveResult):
        result.copied[self.torrent_id] = self.copied_path


@dataclass
class ArchiveAlreadyExists(CommandResultAccumulator):
    torrent_id: int
    copied_path: Path
    error: str

    def accumulate(self, result: ArchiveResult):
        result.already_exist.append(self)


class CopyError(Exception):
    pass


class ArchiveCommand(Command):
    def __init__(self, archive_path: Path, client: TransmissionApi):
        self.client = client
        self.archive_path = archive_path

    def run(self) -> CommandResult:
        result = ArchiveResult()
        for accumulator in self.__collect_accumulators():
            accumulator.accumulate(result)
        return result

    def __collect_accumulators(self) -> Sequence[CommandResultAccumulator]:
        accumulators: MutableSequence[CommandResultAccumulator] = []
        torrent_files_by_id = self.__get_torrent_files_by_id()
        for (torrent_id, torrent_file) in torrent_files_by_id.items():
            new_path: Path = self.__get_new_path(torrent_file)
            try:
                self.__copy_torrent_file(torrent_file, new_path)
                accumulators.append(ArchiveCopied(torrent_id, new_path))
            except CopyError as e:
                accumulators.append(ArchiveAlreadyExists(torrent_id, new_path, str(e)))
        return accumulators

    def __get_torrent_files_by_id(self) -> Mapping[int, Path]:
        return self.client.get_torrent_files_by_id()

    def __get_new_path(self, torrent_file: Path) -> Path:
        file_part = torrent_file.name
        return Path(self.archive_path, file_part)

    def __copy_torrent_file(self, torrent_file: Path, new_path: Path):
        if new_path.exists():
            raise CopyError(f"{new_path} already exists")
        copy(torrent_file, new_path)

    def __create_archive_path(self):
        path = self.archive_path
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
