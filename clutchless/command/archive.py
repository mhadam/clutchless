from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Mapping, MutableMapping, Set, MutableSequence, Optional, Sequence

from colorama import Fore

from clutchless.command.command import Command, CommandOutput
from clutchless.external.filesystem import Filesystem, CopyError
from clutchless.external.result import QueryResult
from clutchless.external.transmission import TransmissionApi


@dataclass(frozen=True)
class ArchiveAction:
    torrent_id: int
    name: str
    source: Path


@dataclass
class ArchiveOutput(CommandOutput):
    destination: Path
    actions: Sequence[ArchiveAction] = field(default_factory=list)
    copied: Set[int] = field(default_factory=set)
    copy_failure: MutableMapping[int, str] = field(default_factory=dict)
    query_failure: Optional[str] = None

    def dry_run_display(self):
        actions_count = len(self.actions)
        if actions_count > 0:
            print(f"Will move {actions_count} metainfo files to {self.destination}:")
            for action in self.actions:
                print(f"{action.source}")
        else:
            print(f"No metainfo files to move")

    def display(self):
        if self.query_failure is not None:
            print(f"Query failed: {self.query_failure}")
        else:
            actions_count = len(self.actions)
            if actions_count > 0:
                print(f"Copied {actions_count} metainfo files to {self.destination}:")
                for action in self.actions:
                    if action.torrent_id in self.copied:
                        print(
                            Fore.GREEN
                            + f"\N{check mark} {action.name} from {action.source}"
                        )
                    if action.torrent_id in self.copy_failure:
                        error = self.copy_failure[action.torrent_id]
                        print(
                            Fore.RED
                            + f"\N{ballot x} failed to move {action.source} because: {error}"
                        )
            else:
                print(f"No metainfo files to move")


def create_archive_actions(
    torrent_file_by_id: Mapping[int, Path], torrent_name_by_id: Mapping[int, str]
) -> Sequence[ArchiveAction]:
    result: MutableSequence[ArchiveAction] = []
    for (torrent_id, source) in torrent_file_by_id.items():
        name = torrent_name_by_id[torrent_id]
        result.append(ArchiveAction(torrent_id, name, source))
    return result


def handle_action(
    fs: Filesystem, archive_path: Path, output: ArchiveOutput, action: ArchiveAction
) -> ArchiveOutput:
    try:
        fs.copy(action.source, archive_path)
        return replace(output, copied={*output.copied, action.torrent_id})
    except CopyError as e:
        return replace(
            output, copy_failure={**output.copy_failure, action.torrent_id: str(e)}
        )


def handle_data(
    fs: Filesystem,
    archive_path: Path,
    torrent_file_by_id: Mapping[int, Path],
    torrent_name_by_id: Mapping[int, str],
) -> ArchiveOutput:
    actions = create_archive_actions(torrent_file_by_id, torrent_name_by_id)
    output = ArchiveOutput(destination=archive_path, actions=actions)
    for action in actions:
        output = handle_action(fs, archive_path, output, action)
    return output


class ArchiveCommand(Command):
    def __init__(self, archive_path: Path, fs: Filesystem, client: TransmissionApi):
        self.client = client
        self.fs = fs
        self.archive_path = archive_path

    def __get_torrent_file_by_id(self) -> Mapping[int, Path]:
        query_result: QueryResult[
            Mapping[int, Path]
        ] = self.client.get_torrent_files_by_id()
        if query_result.success:
            return query_result.value or dict()
        raise RuntimeError("query failed: get_torrent_files_by_id")

    def __get_torrent_name_by_id(self, ids: Set[int]) -> Mapping[int, str]:
        query_result: QueryResult[
            Mapping[int, str]
        ] = self.client.get_torrent_name_by_id(ids)
        if query_result.success:
            return query_result.value or dict()
        raise RuntimeError("query failed: get_torrent_name_by_id")

    def run(self) -> ArchiveOutput:
        try:
            torrent_file_by_id = self.__get_torrent_file_by_id()
            ids = set(torrent_file_by_id.keys())
            torrent_name_by_id = self.__get_torrent_name_by_id(ids)
        except RuntimeError as e:
            return ArchiveOutput(self.archive_path, query_failure=str(e))
        self.fs.create_dir(self.archive_path)
        return handle_data(
            self.fs, self.archive_path, torrent_file_by_id, torrent_name_by_id
        )

    def dry_run(self) -> CommandOutput:
        try:
            torrent_file_by_id = self.__get_torrent_file_by_id()
            ids = set(torrent_file_by_id.keys())
            torrent_name_by_id = self.__get_torrent_name_by_id(ids)
        except RuntimeError as e:
            return ArchiveOutput(self.archive_path, query_failure=str(e))
        actions = create_archive_actions(torrent_file_by_id, torrent_name_by_id)
        return ArchiveOutput(self.archive_path, actions)
