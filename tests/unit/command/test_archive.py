from pathlib import Path
from typing import Mapping

from pytest_mock import MockerFixture

from clutchless.command.archive import (
    ArchiveCommand,
    ArchiveOutput,
    ArchiveAction,
    create_archive_actions,
    handle_action,
    ErrorArchiveCommand,
)
from clutchless.external.filesystem import Filesystem, CopyError
from clutchless.external.result import QueryResult
from clutchless.external.transmission import TransmissionApi
from tests.mock_fs import MockFilesystem


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
    client.get_errors_by_id.return_value = QueryResult(
        {1: (1, "some tracker error"), 2: (3, "some local error")}
    )
    client.get_torrent_files_by_id.return_value = QueryResult(
        {1: Path("/some/path"), 2: Path("/some/path2")}
    )
    client.get_torrent_name_by_id.return_value = QueryResult(
        {1: "some_name", 2: "another_name"}
    )
    command = ErrorArchiveCommand(archive_path, fs, client)

    result = command.run()

    assert result.local_errors == {
        ArchiveAction(
            2, "another_name", Path("/some/path2"), client_error=(3, "some local error")
        )
    }
    assert result.tracker_errors == {
        ArchiveAction(
            1, "some_name", Path("/some/path"), client_error=(1, "some tracker error")
        )
    }


def test_error_archive_dry_run(mocker: MockerFixture):
    archive_path = Path("/", "test_path")
    fs = mocker.Mock(spec=Filesystem)
    client = mocker.Mock(spec=TransmissionApi)
    client.get_errors_by_id.return_value = QueryResult(
        {1: (1, "some tracker error"), 2: (3, "some local error")}
    )
    client.get_torrent_files_by_id.return_value = QueryResult(
        {1: Path("/some/path"), 2: Path("/some/path2")}
    )
    client.get_torrent_name_by_id.return_value = QueryResult(
        {1: "some_name", 2: "another_name"}
    )
    command = ErrorArchiveCommand(archive_path, fs, client)

    result = command.dry_run()

    assert result.local_errors == {
        ArchiveAction(
            2, "another_name", Path("/some/path2"), client_error=(3, "some local error")
        )
    }
    assert result.tracker_errors == {
        ArchiveAction(
            1, "some_name", Path("/some/path"), client_error=(1, "some tracker error")
        )
    }


def test_dry_run_display(mocker: MockerFixture, capsys):
    archive_path = Path("/", "test_path")
    fs = mocker.Mock(spec=Filesystem)
    client = mocker.Mock(spec=TransmissionApi)
    client.get_torrent_files_by_id.return_value = QueryResult({1: Path("/", "file_1")})
    client.get_torrent_name_by_id.return_value = QueryResult({1: "test_name"})
    command = ArchiveCommand(archive_path, fs, client)

    output: ArchiveOutput = command.dry_run()
    output.dry_run_display()

    result = capsys.readouterr().out
    assert (
        result
        == "\n".join(["Found 1 duplicate metainfo files", "No metainfo files to move"])
        + "\n"
    )


def test_dry_run_display_errors(mocker: MockerFixture, capsys):
    archive_path = Path("/", "test_path")
    fs = mocker.Mock(spec=Filesystem)
    client = mocker.Mock(spec=TransmissionApi)
    client.get_errors_by_id.return_value = QueryResult(
        {1: (1, "some tracker error"), 2: (3, "some local error")}
    )
    client.get_torrent_files_by_id.return_value = QueryResult(
        {1: Path("/some/path"), 2: Path("/some/path2")}
    )
    client.get_torrent_name_by_id.return_value = QueryResult(
        {1: "some_name", 2: "another_name"}
    )
    command = ErrorArchiveCommand(archive_path, fs, client)

    output = command.dry_run()
    output.dry_run_display()

    result = capsys.readouterr().out
    assert (
        result
        == "\n".join(
            [
                "Found 1 torrent local errors:",
                'another_name with error "some local error"',
                "Found 1 torrent tracker errors:",
                'some_name with error "some tracker error"',
                "Found 2 duplicate metainfo files",
                "No metainfo files to move",
            ]
        )
        + "\n"
    )


def test_display(mocker: MockerFixture, capsys):
    archive_path = Path("/", "test_path")
    fs = mocker.Mock(spec=Filesystem)
    client = mocker.Mock(spec=TransmissionApi)
    client.get_torrent_files_by_id.return_value = QueryResult({1: Path("/", "file_1")})
    client.get_torrent_name_by_id.return_value = QueryResult({1: "test_name"})
    command = ArchiveCommand(archive_path, fs, client)

    output: ArchiveOutput = command.run()
    output.display()

    result = capsys.readouterr().out
    assert (
        result
        == "\n".join(
            [
                "Moved 1 metainfo files to /test_path:",
                "\x1b[32m✓ test_name",
            ]
        )
        + "\n"
    )


def test_display_errors(mocker: MockerFixture, capsys):
    archive_path = Path("/", "test_path")
    fs = mocker.Mock(spec=Filesystem)
    client = mocker.Mock(spec=TransmissionApi)
    client.get_errors_by_id.return_value = QueryResult(
        {1: (1, "some tracker error"), 2: (3, "some local error")}
    )
    client.get_torrent_files_by_id.return_value = QueryResult(
        {1: Path("/some/path"), 2: Path("/some/path2")}
    )
    client.get_torrent_name_by_id.return_value = QueryResult(
        {1: "some_name", 2: "another_name"}
    )
    command = ErrorArchiveCommand(archive_path, fs, client)

    output = command.run()
    output.display()

    result = capsys.readouterr().out
    assert (
        result
        == "\n".join(
            [
                "Found 1 torrent local errors:",
                'another_name with error "some local error"',
                "Found 1 torrent tracker errors:",
                'some_name with error "some tracker error"',
                "Moved 1 metainfo files to /test_path/tracker_error",
                "\x1b[32m✓ another_name",
                "Moved 1 metainfo files to /test_path/local_error",
                "\x1b[32m✓ some_name",
            ]
        )
        + "\n"
    )


def test_dry_run_display_copied(mocker: MockerFixture, capsys):
    archive_path = Path("/", "test_path")
    fs = MockFilesystem({})
    client = mocker.Mock(spec=TransmissionApi)
    client.get_errors_by_id.return_value = QueryResult(
        {1: (1, "some tracker error"), 2: (3, "some local error")}
    )
    client.get_torrent_files_by_id.return_value = QueryResult(
        {1: Path("/some/path"), 2: Path("/some/path2"), 3: Path("/some/path3")}
    )
    client.get_torrent_name_by_id.return_value = QueryResult(
        {1: "some_name", 2: "another_name", 3: "third_name"}
    )
    command = ErrorArchiveCommand(archive_path, fs, client)

    output = command.dry_run()
    output.dry_run_display()

    result = capsys.readouterr().out
    assert (
        result
        == "\n".join(
            [
                "Found 1 torrent local errors:",
                'another_name with error "some local error"',
                "Found 1 torrent tracker errors:",
                'some_name with error "some tracker error"',
                "Will move 1 metainfo files to /test_path/tracker_error",
                "another_name",
                "Will move 1 metainfo files to /test_path/local_error",
                "some_name",
                "Will move 1 metainfo files to /test_path:",
                "/some/path3",
            ]
        )
        + "\n"
    )


def test_run_display_copy_failure(mocker: MockerFixture, capsys):
    archive_path = Path("/", "test_path")
    fs = MockFilesystem({"file_1", "test_path"})
    client = mocker.Mock(spec=TransmissionApi)
    client.get_torrent_files_by_id.return_value = QueryResult({1: Path("/", "file_1")})
    client.get_torrent_name_by_id.return_value = QueryResult({1: "test_name"})
    command = ArchiveCommand(archive_path, fs, client)

    output: ArchiveOutput = command.run()
    output.display()

    result = capsys.readouterr().out
    assert (
        result
        == "\n".join(
            [
                "Failed to move 1 metainfo files:",
                "\x1b[31m✗ failed to move /file_1 because:destination is a file",
            ]
        )
        + "\n"
    )


def test_run_display_already_exists(mocker: MockerFixture, capsys):
    archive_path = Path("/", "test_path")
    fs = MockFilesystem(["file_1", {"test_path": ["file_1"]}])
    client = mocker.Mock(spec=TransmissionApi)
    client.get_torrent_files_by_id.return_value = QueryResult({1: Path("/", "file_1")})
    client.get_torrent_name_by_id.return_value = QueryResult({1: "test_name"})
    command = ArchiveCommand(archive_path, fs, client)

    output: ArchiveOutput = command.run()
    output.display()

    result = capsys.readouterr().out
    assert (
        result
        == "\n".join(
            [
                "Found 1 duplicate metainfo files:",
                "test_name",
                "No metainfo files moved",
            ]
        )
        + "\n"
    )


def test_query_failure_output(mocker: MockerFixture, capsys):
    archive_path = Path("/", "test_path")
    fs = MockFilesystem({})
    client = mocker.Mock(spec=TransmissionApi)
    client.get_torrent_files_by_id.return_value = QueryResult(
        error="some_error", success=False
    )
    client.get_torrent_name_by_id.return_value = QueryResult({1: "test_name"})
    command = ArchiveCommand(archive_path, fs, client)

    output: ArchiveOutput = command.run()
    output.display()

    result = capsys.readouterr().out
    assert result == "Query failed: get_torrent_files_by_id\n"
