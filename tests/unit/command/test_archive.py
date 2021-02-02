from pathlib import Path
from typing import Mapping

from pytest_mock import MockerFixture

from clutchless.command.archive import (
    ArchiveCommand,
    ArchiveOutput,
    ArchiveAction,
    create_archive_actions,
    handle_action, ErrorArchiveCommand,
)
from clutchless.external.filesystem import Filesystem, CopyError
from clutchless.external.result import QueryResult
from clutchless.external.transmission import TransmissionApi


def test_create_actions():
    torrent_file_by_id: Mapping[int, Path] = {1: Path("/", "test_path")}
    torrent_name_by_id: Mapping[int, str] = {1: "test_name"}

    actions = create_archive_actions(torrent_file_by_id, torrent_name_by_id)

    assert actions == {ArchiveAction(1, "test_name", Path("/", "test_path"))}


def test_handle_action_success(mocker: MockerFixture):
    fs = mocker.Mock(spec=Filesystem)
    output = ArchiveOutput(Path("/", "archive"))
    action = ArchiveAction(1, "test_name", Path("/", "test_path"))

    new_output = handle_action(fs, Path("/", "archive"), output, action)

    assert new_output == ArchiveOutput(Path("/", "archive"), copied={action})


def test_handle_action_fail(mocker: MockerFixture):
    fs = mocker.Mock(spec=Filesystem)
    fs.copy.side_effect = CopyError("test_error")
    output = ArchiveOutput(Path("/", "archive"))
    action = ArchiveAction(1, "test_name", Path("/", "test_path"))

    new_output = handle_action(fs, Path("/", "archive"), output, action)

    assert new_output == ArchiveOutput(
        Path("/", "archive"), copy_failure={action: "test_error"}
    )


def test_archive_success(mocker: MockerFixture):
    archive_path = Path("/", "test_path")
    fs = mocker.Mock(spec=Filesystem)
    client = mocker.Mock(spec=TransmissionApi)
    client.get_torrent_files_by_id.return_value = QueryResult({1: Path("/", "file_1")})
    client.get_torrent_name_by_id.return_value = QueryResult({1: "test_name"})
    command = ArchiveCommand(archive_path, fs, client)

    result: ArchiveOutput = command.run()

    assert result.copied == {ArchiveAction(1, "test_name", Path("/", "file_1"))}
    fs.create_dir.assert_called_once_with(Path("/", "test_path"))
    fs.copy.assert_called_once_with(Path("/", "file_1"), Path("/", "test_path"))


def test_archive_first_query_failure(mocker: MockerFixture):
    archive_path = Path("/", "test_path")
    fs = mocker.Mock(spec=Filesystem)
    client = mocker.Mock(spec=TransmissionApi)
    client.get_torrent_files_by_id.return_value = QueryResult(
        error="some_error", success=False
    )
    client.get_torrent_name_by_id.return_value = QueryResult({1: "test_name"})
    command = ArchiveCommand(archive_path, fs, client)

    result: ArchiveOutput = command.run()

    assert result.query_failure == "query failed: get_torrent_files_by_id"


def test_archive_second_query_failure(mocker: MockerFixture):
    archive_path = Path("/", "test_path")
    fs = mocker.Mock(spec=Filesystem)
    client = mocker.Mock(spec=TransmissionApi)
    client.get_torrent_files_by_id.return_value = QueryResult({1: Path("/", "file_1")})
    client.get_torrent_name_by_id.return_value = QueryResult(
        error="some_error", success=False
    )
    command = ArchiveCommand(archive_path, fs, client)

    result: ArchiveOutput = command.run()

    assert result.query_failure == "query failed: get_torrent_name_by_id"


def test_error_archive_run(mocker: MockerFixture):
    archive_path = Path("/", "test_path")
    fs = mocker.Mock(spec=Filesystem)
    client = mocker.Mock(spec=TransmissionApi)
    client.get_errors_by_id.return_value = QueryResult({1: (1, "some tracker error"), 2: (3, "some local error")})
    client.get_torrent_files_by_id.return_value = QueryResult({1: Path("/some/path"), 2: Path("/some/path2")})
    client.get_torrent_name_by_id.return_value = QueryResult({1: "some_name", 2: "another_name"})
    command = ErrorArchiveCommand(archive_path, fs, client)

    result = command.run()

    assert result.local_errors == {ArchiveAction(2, 'another_name', Path('/some/path2'), client_error=(3, 'some local error'))}
    assert result.tracker_errors == {ArchiveAction(1, 'some_name', Path('/some/path'), client_error=(1, 'some tracker error'))}


def test_error_archive_dry_run(mocker: MockerFixture):
    archive_path = Path("/", "test_path")
    fs = mocker.Mock(spec=Filesystem)
    client = mocker.Mock(spec=TransmissionApi)
    client.get_errors_by_id.return_value = QueryResult({1: (1, "some tracker error"), 2: (3, "some local error")})
    client.get_torrent_files_by_id.return_value = QueryResult({1: Path("/some/path"), 2: Path("/some/path2")})
    client.get_torrent_name_by_id.return_value = QueryResult({1: "some_name", 2: "another_name"})
    command = ErrorArchiveCommand(archive_path, fs, client)

    result = command.dry_run()

    assert result.local_errors == {ArchiveAction(2, 'another_name', Path('/some/path2'), client_error=(3, 'some local error'))}
    assert result.tracker_errors == {ArchiveAction(1, 'some_name', Path('/some/path'), client_error=(1, 'some tracker error'))}


def test_dry_run_display(mocker: MockerFixture, capsys):
    archive_path = Path("/", "test_path")
    fs = mocker.Mock(spec=Filesystem)
    client = mocker.Mock(spec=TransmissionApi)
    client.get_torrent_files_by_id.return_value = QueryResult({1: Path("/", "file_1")})
    client.get_torrent_name_by_id.return_value = QueryResult({1: "test_name"})
    command = ArchiveCommand(archive_path, fs, client)

    output: ArchiveOutput = command.dry_run()
    output.display()

    result = capsys.readouterr().out
    assert result == "\n".join([
        "Found 1 duplicate metainfo files",
        "No metainfo files moved"
    ]) + "\n"


def test_display(mocker: MockerFixture, capsys):
    archive_path = Path("/", "test_path")
    fs = mocker.Mock(spec=Filesystem)
    client = mocker.Mock(spec=TransmissionApi)
    client.get_torrent_files_by_id.return_value = QueryResult({1: Path("/", "file_1")})
    client.get_torrent_name_by_id.return_value = QueryResult({1: "test_name"})
    command = ArchiveCommand(archive_path, fs, client)

    output: ArchiveOutput = command.run()
    output.dry_run_display()

    result = capsys.readouterr().out
    assert result == "\n".join([
        "Will move 1 metainfo files to /test_path:",
        "/file_1"
    ]) + "\n"
