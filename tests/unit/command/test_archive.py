from pathlib import Path
from typing import Mapping

from pytest_mock import MockerFixture

from clutchless.command.archive import ArchiveCommand, ArchiveOutput, ArchiveAction, create_archive_actions, \
    handle_action
from clutchless.external.filesystem import Filesystem, CopyError
from clutchless.external.result import QueryResult
from clutchless.external.transmission import TransmissionApi


def test_create_actions():
    torrent_file_by_id: Mapping[int, Path] = {1: Path('/', 'test_path')}
    torrent_name_by_id: Mapping[int, str] = {1: 'test_name'}

    actions = create_archive_actions(torrent_file_by_id, torrent_name_by_id)

    assert actions == [ArchiveAction(1, 'test_name', Path('/', 'test_path'))]


def test_handle_action_success(mocker: MockerFixture):
    fs = mocker.Mock(spec=Filesystem)
    output = ArchiveOutput()
    action = ArchiveAction(1, 'test_name', Path('/', 'test_path'))

    new_output = handle_action(fs, Path('/', 'archive'), output, action)

    assert new_output == ArchiveOutput(copied={1})


def test_handle_action_fail(mocker: MockerFixture):
    fs = mocker.Mock(spec=Filesystem)
    fs.copy.side_effect = CopyError('test_error')
    output = ArchiveOutput()
    action = ArchiveAction(1, 'test_name', Path('/', 'test_path'))

    new_output = handle_action(fs, Path('/', 'archive'), output, action)

    assert new_output == ArchiveOutput(copy_failure={1: 'test_error'})


def test_archive_success(mocker: MockerFixture):
    archive_path = Path("/", "test_path")
    fs = mocker.Mock(spec=Filesystem)
    client = mocker.Mock(spec=TransmissionApi)
    client.get_torrent_files_by_id.return_value = QueryResult({1: Path('/', 'file_1')})
    client.get_torrent_name_by_id.return_value = QueryResult({1: 'test_name'})
    command = ArchiveCommand(archive_path, fs, client)

    result: ArchiveOutput = command.run()

    assert result.copied == {1}
    assert result.actions == [ArchiveAction(1, 'test_name', Path('/', 'file_1'))]
    fs.create_dir.assert_called_once_with(Path("/", "test_path"))
    fs.copy.assert_called_once_with(Path("/", "file_1"), Path("/", "test_path"))


def test_archive_first_query_failure(mocker: MockerFixture):
    archive_path = Path("/", "test_path")
    fs = mocker.Mock(spec=Filesystem)
    client = mocker.Mock(spec=TransmissionApi)
    client.get_torrent_files_by_id.return_value = QueryResult(error="some_error", success=False)
    client.get_torrent_name_by_id.return_value = QueryResult({1: 'test_name'})
    command = ArchiveCommand(archive_path, fs, client)

    result: ArchiveOutput = command.run()

    assert result.query_failure == "query failed: get_torrent_files_by_id"


def test_archive_second_query_failure(mocker: MockerFixture):
    archive_path = Path("/", "test_path")
    fs = mocker.Mock(spec=Filesystem)
    client = mocker.Mock(spec=TransmissionApi)
    client.get_torrent_files_by_id.return_value = QueryResult({1: Path('/', 'file_1')})
    client.get_torrent_name_by_id.return_value = QueryResult(error="some_error", success=False)
    command = ArchiveCommand(archive_path, fs, client)

    result: ArchiveOutput = command.run()

    assert result.query_failure == "query failed: get_torrent_name_by_id"
