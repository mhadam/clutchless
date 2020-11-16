from pathlib import Path

from pytest_mock import MockerFixture

from clutchless.command.add import AddCommand, AddOutput, LinkingAddCommand, LinkingAddOutput
from clutchless.domain.torrent import MetainfoFile
from clutchless.external.filesystem import Filesystem
from clutchless.external.metainfo import TorrentDataLocator, DefaultTorrentDataLocator
from clutchless.external.result import CommandResult
from clutchless.external.transmission import TransmissionApi
from clutchless.service.torrent import AddService, FindService


def test_add_run_success(mocker: MockerFixture):
    api = mocker.Mock(spec=TransmissionApi)
    api.add_torrent.return_value = CommandResult()
    service = AddService(api)
    fs = mocker.Mock(spec=Filesystem)
    metainfo_paths = {Path('/', 'test_path', str(n)) for n in range(10)}
    command = AddCommand(service, fs, metainfo_paths)

    output: AddOutput = command.run()

    for path in metainfo_paths:
        fs.remove.assert_any_call(path)

    for path in metainfo_paths:
        assert path in output.added_torrents


def test_add_run_duplicate(mocker: MockerFixture):
    api = mocker.Mock(spec=TransmissionApi)
    api.add_torrent.return_value = CommandResult(error="duplicate", success=False)
    service = AddService(api)
    fs = mocker.Mock(spec=Filesystem)
    metainfo_path = Path('/', 'test_path')
    command = AddCommand(service, fs, {metainfo_path})

    output: AddOutput = command.run()

    fs.remove.assert_not_called()
    assert metainfo_path in output.duplicated_torrents


def test_add_run_unknown(mocker: MockerFixture):
    api = mocker.Mock(spec=TransmissionApi)
    api.add_torrent.return_value = CommandResult(error="unknown", success=False)
    service = AddService(api)
    fs = mocker.Mock(spec=Filesystem)
    metainfo_path = Path('/', 'test_path')
    command = AddCommand(service, fs, {metainfo_path})

    output: AddOutput = command.run()

    fs.remove.assert_not_called()
    assert output.failed_torrents[metainfo_path] == "unknown"


def test_add_linking_unknown(mocker: MockerFixture):
    api = mocker.Mock(spec=TransmissionApi)
    api.add_torrent_with_files.return_value = CommandResult(error="unknown", success=False)
    api.add_torrent.return_value = CommandResult(error="unknown", success=False)
    add_service = AddService(api)

    fs = mocker.Mock(spec=Filesystem)
    locator: TorrentDataLocator = DefaultTorrentDataLocator(fs)
    find_service = FindService(locator)
    metainfo_path = Path('/', 'test_path')
    metainfo_file = MetainfoFile({
        'name': 'meaningless',
        'info_hash': 'meaningless and necessary',
        'info': {
            'length': 5
        }
    }, metainfo_path)
    command = LinkingAddCommand(find_service, add_service, fs, {metainfo_file})

    output: LinkingAddOutput = command.run()

    fs.remove.assert_not_called()

    assert output.failed_torrents == {metainfo_path: 'unknown'}


def test_add_linking_success(mocker: MockerFixture):
    api = mocker.Mock(spec=TransmissionApi)
    api.add_torrent_with_files.return_value = CommandResult(success=True)
    api.add_torrent.return_value = CommandResult(success=True)
    add_service = AddService(api)

    fs = mocker.Mock(spec=Filesystem)
    locator: TorrentDataLocator = DefaultTorrentDataLocator(fs)
    find_service = FindService(locator)
    metainfo_path = Path('/', 'test_path')
    metainfo_file = MetainfoFile(
        {
            'name': 'meaningless',
            'info_hash': 'meaningless and necessary',
            'info': {
                'length': 5
            }
        },
        metainfo_path
    )
    command = LinkingAddCommand(find_service, add_service, fs, {metainfo_file})

    output: LinkingAddOutput = command.run()

    fs.remove.assert_any_call(metainfo_path)

    assert output.added_torrents == [metainfo_path]


def test_add_linking_duplicate(mocker: MockerFixture):
    api = mocker.Mock(spec=TransmissionApi)
    api.add_torrent_with_files.return_value = CommandResult(success=False, error="duplicate")
    api.add_torrent.return_value = CommandResult(success=False, error="duplicate")
    add_service = AddService(api)

    fs = mocker.Mock(spec=Filesystem)
    locator: TorrentDataLocator = DefaultTorrentDataLocator(fs)
    find_service = FindService(locator)
    metainfo_path = Path('/', 'test_path')
    metainfo_file = MetainfoFile({
        'name': 'meaningless',
        'info_hash': 'meaningless and necessary',
        'info': {
            'length': 5
        }
    }, metainfo_path)
    command = LinkingAddCommand(find_service, add_service, fs, {metainfo_file})

    output: LinkingAddOutput = command.run()

    fs.remove.assert_not_called()

    assert output.duplicated_torrents == {metainfo_path: "duplicate"}
