import logging
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Mapping, Set, Optional, Tuple

from colorama import Fore

from clutchless.command.command import Command, CommandOutput
from clutchless.external.filesystem import Filesystem, CopyError
from clutchless.external.result import QueryResult
from clutchless.external.transmission import TransmissionApi

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ArchiveAction:
    torrent_id: int
    name: str
    source: Path
    client_error: Optional[Tuple[int, str]]


@dataclass
class ArchiveOutput(CommandOutput):
    # set in creation
    destination: Path
    # set conditionally in creation
    query_failure: Optional[str] = None
    # set during action handling
    local_errors: Set[ArchiveAction] = field(default_factory=set)
    tracker_errors: Set[ArchiveAction] = field(default_factory=set)
    already_exists: Set[ArchiveAction] = field(default_factory=set)
    copied: Set[ArchiveAction] = field(default_factory=set)
    copy_failure: Mapping[ArchiveAction, str] = field(default_factory=dict)

    def dry_run_display(self):
        logger.debug(f"dry-run archive already_exists:{self.already_exists}")
        if self.local_errors:
            print(f"Found {len(self.local_errors)} torrent local errors:")
            for action in self.local_errors:
                print(f'{action.name} with error "{action.client_error[1]}"')
        if self.tracker_errors:
            print(f"Found {len(self.tracker_errors)} torrent tracker errors:")
            for action in self.tracker_errors:
                print(f'{action.name} with error "{action.client_error[1]}"')
        if self.already_exists:
            print(f"Found {len(self.already_exists)} duplicate metainfo files")
        copied_count = len(self.copied)
        if copied_count > 0:
            copied_local_error = {
                action for action in self.local_errors if action in self.copied
            }
            if copied_local_error:
                print(
                    f"Will move {len(copied_local_error)} metainfo files to {self.destination / 'tracker_error'}"
                )
                for action in copied_local_error:
                    print(f"{action.name}")
            copied_tracker_error = {
                action for action in self.tracker_errors if action in self.copied
            }
            if copied_tracker_error:
                print(
                    f"Will move {len(copied_tracker_error)} metainfo files to {self.destination / 'local_error'}"
                )
                for action in copied_tracker_error:
                    print(f"{action.name}")
            rest = self.copied - copied_local_error - copied_tracker_error
            if rest:
                print(f"Will move {len(rest)} metainfo files to {self.destination}:")
                for action in rest:
                    print(f"{action.source}")
        else:
            print(f"No metainfo files to move")

    def display(self):
        if self.query_failure is not None:
            print(f"Query failed: {self.query_failure}")
        else:
            if self.local_errors:
                print(f"Found {len(self.local_errors)} torrent local errors:")
                for action in self.local_errors:
                    print(f'{action.name} with error "{action.client_error[1]}"')
            if self.tracker_errors:
                print(f"Found {len(self.tracker_errors)} torrent tracker errors:")
                for action in self.tracker_errors:
                    print(f'{action.name} with error "{action.client_error[1]}"')
            if self.already_exists:
                print(f"Found {len(self.already_exists)} duplicate metainfo files")
            copied_count = len(self.copied)
            if copied_count > 0:
                copied_local_error = {
                    action for action in self.local_errors if action in self.copied
                }
                if copied_local_error:
                    print(
                        f"Moved {len(copied_local_error)} metainfo files to {self.destination / 'tracker_error'}"
                    )
                    for action in copied_local_error:
                        print(Fore.GREEN + f"\N{check mark} {action.name}")
                copied_tracker_error = {
                    action for action in self.tracker_errors if action in self.copied
                }
                if copied_tracker_error:
                    print(
                        f"Moved {len(copied_tracker_error)} metainfo files to {self.destination / 'local_error'}"
                    )
                    for action in copied_tracker_error:
                        print(Fore.GREEN + f"\N{check mark} {action.name}")
                rest = self.copied - copied_local_error - copied_tracker_error
                if rest:
                    print(f"Moved {len(rest)} metainfo files to {self.destination}:")
                    for action in rest:
                        print(Fore.GREEN + f"\N{check mark} {action.name}")
            if self.copy_failure:
                print(f"Failed to move {len(self.copy_failure)} metainfo files:")
                for action, error_string in self.copy_failure.items():
                    print(
                        Fore.RED
                        + f"\N{ballot x} failed to move {action.source} because:{error_string}"
                    )
            else:
                print(f"No metainfo files moved")


def create_archive_actions(
    torrent_file_by_id: Mapping[int, Path],
    torrent_name_by_id: Mapping[int, str],
    errors_by_id: Optional[Mapping[int, Tuple[int, str]]] = None,
) -> Set[ArchiveAction]:
    if errors_by_id is None:
        errors_by_id = {}
    result: Set[ArchiveAction] = set()
    for (torrent_id, source) in torrent_file_by_id.items():
        name = torrent_name_by_id[torrent_id]
        error = errors_by_id.get(torrent_id)
        result.add(ArchiveAction(torrent_id, name, source, error))
    return result


def handle_action(
    fs: Filesystem, archive_path: Path, output: ArchiveOutput, action: ArchiveAction
) -> ArchiveOutput:
    try:
        if action.client_error:
            error_code = action.client_error[0]
            if error_code == 1 or error_code == 2:
                fs.create_dir(archive_path / "tracker_error")
                fs.copy(action.source, archive_path / "tracker_error")
            elif error_code == 3:
                fs.create_dir(archive_path / "local_error")
                fs.copy(action.source, archive_path / "local_error")
        else:
            fs.copy(action.source, archive_path)
        return replace(output, copied={*output.copied, action})
    except CopyError as e:
        logger.debug(f"copy error in handle_action {str(e)}")
        if "destination already exists" in str(e):
            return replace(output, already_exists={*output.already_exists, action})
        return replace(output, copy_failure={**output.copy_failure, action: str(e)})


@dataclass
class ArchiveQueryResult:
    metainfo_path: Path
    metainfo_name: str
    torrent_error_code: int
    torrent_error: str


def sort_errors(
    actions: Set[ArchiveAction],
) -> Tuple[Set[ArchiveAction], Set[ArchiveAction]]:
    local_errors = set()
    tracker_errors = set()
    for action in actions:
        try:
            error_code = action.client_error[0]
            if error_code == 1 or error_code == 2:
                tracker_errors.add(action)
            elif error_code == 3:
                local_errors.add(action)
        except TypeError:
            pass
    return local_errors, tracker_errors


def handle_data(
    fs: Filesystem,
    archive_path: Path,
    torrent_file_by_id: Mapping[int, Path],
    torrent_name_by_id: Mapping[int, str],
    errors_by_id: Optional[Mapping[int, Tuple[int, str]]] = None,
) -> ArchiveOutput:
    if errors_by_id is None:
        errors_by_id = {}
    actions = create_archive_actions(
        torrent_file_by_id, torrent_name_by_id, errors_by_id
    )
    local_errors, tracker_errors = sort_errors(actions)
    output = ArchiveOutput(
        destination=archive_path,
        local_errors=local_errors,
        tracker_errors=tracker_errors,
    )
    for action in actions:
        output = handle_action(fs, archive_path, output, action)
    return output


class ErrorArchiveCommand(Command):
    def __init__(self, archive_path: Path, fs: Filesystem, client: TransmissionApi):
        self.client = client
        self.fs = fs
        self.archive_path = archive_path

    def _get_errors_by_id(self, ids: Set[int]) -> Mapping[int, Tuple[int, str]]:
        query_result: QueryResult[
            Mapping[int, Tuple[int, str]]
        ] = self.client.get_errors_by_id(ids)
        if query_result.success:
            logger.debug(f"errors_by_id query result {query_result.value}")
            return query_result.value or dict()
        raise RuntimeError("query failed: get_errors_by_id")

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
            errors_by_id: Mapping[int, Tuple[int, str]] = self._get_errors_by_id(ids)
        except RuntimeError as e:
            return ArchiveOutput(self.archive_path, query_failure=str(e))
        self.fs.create_dir(self.archive_path)
        return handle_data(
            self.fs,
            self.archive_path,
            torrent_file_by_id,
            torrent_name_by_id,
            errors_by_id,
        )

    def _get_already_exists(
        self, actions: Set[ArchiveAction], torrent_file_by_id: Mapping[int, Path]
    ) -> Set[ArchiveAction]:
        result: Set[ArchiveAction] = set()
        for action in actions:
            new_filename = torrent_file_by_id[action.torrent_id].name
            if action.client_error:  # todo: try-except this
                code = action.client_error[0]
                if code == 1 or code == 2:
                    error_folder = "tracker_error"
                elif code == 3:
                    error_folder = "local_error"
                else:
                    code, message = action.client_error
                    logger.warning(
                        f"some other torrent error occurred with code:{code}, message:{message}"
                    )
                    continue
                new_path = self.archive_path / error_folder / new_filename
            else:
                new_path = self.archive_path / new_filename
            logger.debug(f"checking for {new_path}")
            if self.fs.exists(new_path):
                result.add(action)
        return result

    def dry_run(self) -> CommandOutput:
        try:
            torrent_file_by_id = self.__get_torrent_file_by_id()
            ids = set(torrent_file_by_id.keys())
            torrent_name_by_id = self.__get_torrent_name_by_id(ids)
            errors_by_id: Mapping[int, Tuple[int, str]] = self._get_errors_by_id(ids)
        except RuntimeError as e:
            return ArchiveOutput(self.archive_path, query_failure=str(e))
        actions = create_archive_actions(
            torrent_file_by_id, torrent_name_by_id, errors_by_id
        )
        already_exists = self._get_already_exists(actions, torrent_file_by_id)
        copied = actions - already_exists
        local_errors, tracker_errors = sort_errors(actions)
        return ArchiveOutput(
            self.archive_path,
            copied=copied,
            tracker_errors=tracker_errors,
            local_errors=local_errors,
            already_exists=already_exists,
        )


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
            self.fs,
            self.archive_path,
            torrent_file_by_id,
            torrent_name_by_id,
        )

    def _get_already_exists(
        self, actions: Set[ArchiveAction], torrent_file_by_id: Mapping[int, Path]
    ) -> Set[ArchiveAction]:
        result: Set[ArchiveAction] = set()
        for action in actions:
            new_filename = torrent_file_by_id[action.torrent_id].name
            new_path = self.archive_path / new_filename
            logger.debug(f"checking for {new_path}")
            if self.fs.exists(new_path):
                result.add(action)
        return result

    def dry_run(self) -> CommandOutput:
        try:
            torrent_file_by_id = self.__get_torrent_file_by_id()
            ids = set(torrent_file_by_id.keys())
            torrent_name_by_id = self.__get_torrent_name_by_id(ids)
        except RuntimeError as e:
            return ArchiveOutput(self.archive_path, query_failure=str(e))
        actions = create_archive_actions(torrent_file_by_id, torrent_name_by_id)
        already_exists = self._get_already_exists(actions, torrent_file_by_id)
        copied = actions - already_exists
        return ArchiveOutput(
            self.archive_path,
            copied=copied,
            already_exists=already_exists,
        )
