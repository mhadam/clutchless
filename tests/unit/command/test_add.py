from pathlib import Path

from pytest_mock import MockerFixture

from clutchless.command.add import (
    AddCommand,
    AddOutput,
    LinkingAddCommand,
    LinkingAddOutput,
)
from clutchless.domain.torrent import MetainfoFile
from clutchless.external.filesystem import Filesystem
from clutchless.external.metainfo import (
    TorrentDataLocator,
    DefaultTorrentDataLocator,
    TorrentData,
)
from clutchless.external.result import CommandResult
from clutchless.external.transmission import TransmissionApi
from clutchless.service.torrent import AddService, FindService
from tests.mock_fs import MockFilesystem


def test_add_run_success(mocker: MockerFixture):
    api = mocker.Mock(spec=TransmissionApi)
    api.add_torrent.return_value = CommandResult()
    service = AddService(api)
    fs = mocker.Mock(spec=Filesystem)
    metainfo_paths = {Path("/", "test_path", str(n)) for n in range(10)}
    metainfo_files = {
        MetainfoFile({"info_hash": path}, path) for path in metainfo_paths
    }
    command = AddCommand(service, fs, metainfo_files)

    output: AddOutput = command.run()

    for path in metainfo_paths:
        fs.remove.assert_any_call(path)

    added_paths = {torrent.path for torrent in output.added_torrents}
    for path in metainfo_paths:
        assert path in added_paths


def test_add_run_duplicate(mocker: MockerFixture):
    api = mocker.Mock(spec=TransmissionApi)
    api.add_torrent.return_value = CommandResult(error="duplicate", success=False)
    service = AddService(api)
    fs = mocker.Mock(spec=Filesystem)
    metainfo_path = Path("/", "test_path")
    metainfo_file = MetainfoFile({"info_hash": "arbitrary"}, metainfo_path)

    command = AddCommand(service, fs, {metainfo_file})

    output: AddOutput = command.run()

    fs.remove.assert_not_called()
    assert metainfo_file in output.duplicated_torrents


def test_add_run_unknown(mocker: MockerFixture):
    api = mocker.Mock(spec=TransmissionApi)
    api.add_torrent.return_value = CommandResult(error="unknown", success=False)
    service = AddService(api)
    fs = mocker.Mock(spec=Filesystem)
    metainfo_path = Path("/", "test_path")
    metainfo_file = MetainfoFile({"info_hash": "arbitrary"}, metainfo_path)
    command = AddCommand(service, fs, {metainfo_file})

    output: AddOutput = command.run()

    fs.remove.assert_not_called()
    assert output.failed_torrents[metainfo_file] == "unknown"


def test_add_linking_unknown(mocker: MockerFixture):
    api = mocker.Mock(spec=TransmissionApi)
    api.add_torrent_with_files.return_value = CommandResult(
        error="unknown", success=False
    )
    api.add_torrent.return_value = CommandResult(error="unknown", success=False)
    add_service = AddService(api)

    fs = MockFilesystem({"test_path"})
    path = Path("/", "test_path")
    file = MetainfoFile(
        {
            "name": "meaningless",
            "info_hash": "meaningless and necessary",
            "info": {"length": 5},
        },
        path,
    )
    command = LinkingAddCommand(
        add_service, fs, {TorrentData(file, Path("/some/place"))}
    )

    output: LinkingAddOutput = command.run()

    assert fs.exists(path)
    assert output.failed_torrents == {file: "unknown"}


def test_add_linking_success(mocker: MockerFixture):
    api = mocker.Mock(spec=TransmissionApi)
    api.add_torrent_with_files.return_value = CommandResult(success=True)
    api.add_torrent.return_value = CommandResult(success=True)
    add_service = AddService(api)

    fs = MockFilesystem({"test_path"})
    locator: TorrentDataLocator = DefaultTorrentDataLocator(fs)
    find_service = FindService(locator)
    path = Path("/", "test_path")
    file = MetainfoFile(
        {
            "name": "meaningless",
            "info_hash": "meaningless and necessary",
            "info": {"length": 5},
        },
        path,
    )
    command = LinkingAddCommand(
        add_service, fs, {TorrentData(file, Path("/some/place"))}
    )

    output: LinkingAddOutput = command.run()

    assert not fs.exists(path)
    assert output.linked_torrents == {file: Path("/some/place")}


def test_add_linking_duplicate(mocker: MockerFixture):
    api = mocker.Mock(spec=TransmissionApi)
    api.add_torrent_with_files.return_value = CommandResult(
        success=False, error="duplicate"
    )
    api.add_torrent.return_value = CommandResult(success=False, error="duplicate")
    add_service = AddService(api)

    fs = MockFilesystem({"test_path"})
    path = Path("/", "test_path")
    file = MetainfoFile(
        {
            "name": "meaningless",
            "info_hash": "meaningless and necessary",
            "info": {"length": 5},
        },
        path,
    )
    command = LinkingAddCommand(
        add_service, fs, {TorrentData(file, Path("/some/place"))}
    )

    output: LinkingAddOutput = command.run()

    assert fs.exists(path)
    assert output.duplicated_torrents == {file: "duplicate"}


def test_add_run_display(mocker: MockerFixture, capsys):
    api = mocker.Mock(spec=TransmissionApi)
    api.add_torrent.return_value = CommandResult()
    service = AddService(api)
    fs = mocker.Mock(spec=Filesystem)
    metainfo_paths = {Path("/", "test_path", str(n)) for n in range(2)}
    metainfo_files = {
        MetainfoFile({"info_hash": path, "name": "some_name"}, path)
        for path in metainfo_paths
    }
    command = AddCommand(service, fs, metainfo_files)
    output: AddOutput = command.run()
    output.display()

    result = capsys.readouterr().out

    assert (
        result
        == "\n".join(
            [
                "2 torrents were added:",
                "some_name",
                "some_name",
                "2 torrents were deleted:",
                "some_name at /test_path/0",
                "some_name at /test_path/1",
            ]
        )
        + "\n"
    )


def test_add_run_display_duplicated(mocker: MockerFixture, capsys):
    api = mocker.Mock(spec=TransmissionApi)
    api.add_torrent.return_value = CommandResult(error="duplicate", success=False)
    service = AddService(api)
    fs = mocker.Mock(spec=Filesystem)
    metainfo_path = Path("/", "test_path")
    metainfo_file = MetainfoFile(
        {"info_hash": "arbitrary", "name": "some_name"}, metainfo_path
    )

    command = AddCommand(service, fs, {metainfo_file})

    output: AddOutput = command.run()
    output.display()

    result = capsys.readouterr().out

    assert (
        result
        == "\n".join(
            [
                "1 torrents are duplicates:",
                "some_name",
            ]
        )
        + "\n"
    )


def test_add_run_display_failed(mocker: MockerFixture, capsys):
    api = mocker.Mock(spec=TransmissionApi)
    api.add_torrent.return_value = CommandResult(error="unknown", success=False)
    service = AddService(api)
    fs = mocker.Mock(spec=Filesystem)
    metainfo_path = Path("/", "test_path")
    metainfo_file = MetainfoFile(
        {"info_hash": "arbitrary", "name": "some_name"}, metainfo_path
    )
    command = AddCommand(service, fs, {metainfo_file})

    output: AddOutput = command.run()
    output.display()

    result = capsys.readouterr().out

    assert (
        result
        == "\n".join(
            [
                "1 torrents failed:",
                "some_name because: unknown",
            ]
        )
        + "\n"
    )


def test_add_dry_run_display(mocker: MockerFixture, capsys):
    api = mocker.Mock(spec=TransmissionApi)
    api.add_torrent.return_value = CommandResult()
    service = AddService(api)
    fs = mocker.Mock(spec=Filesystem)
    metainfo_paths = {Path("/", "test_path", str(n)) for n in range(2)}
    metainfo_files = {
        MetainfoFile({"info_hash": path, "name": "some_name"}, path)
        for path in metainfo_paths
    }
    command = AddCommand(service, fs, metainfo_files)
    output: AddOutput = command.dry_run()
    output.dry_run_display()

    result = capsys.readouterr().out

    assert (
        result
        == "\n".join(
            [
                "2 torrents would be added and deleted:",
                "some_name at /test_path/0",
                "some_name at /test_path/1",
            ]
        )
        + "\n"
    )


def test_linking_add_run_display(mocker: MockerFixture, capsys):
    api = mocker.Mock(spec=TransmissionApi)
    api.add_torrent_with_files.return_value = CommandResult(success=True)
    api.add_torrent.return_value = CommandResult(success=True)
    add_service = AddService(api)

    fs = MockFilesystem({"test_path", "test_path2"})
    file_one = MetainfoFile(
        {
            "name": "meaningless",
            "info_hash": "meaningless and necessary",
            "info": {"length": 5},
        },
        Path("/", "test_path"),
    )
    file_two = MetainfoFile(
        {
            "name": "meaningless",
            "info_hash": "meaningless and necessary",
            "info": {"length": 5},
        },
        Path("/", "test_path2"),
    )
    torrent_data = {
        TorrentData(file_one, Path("/some/place")),
        TorrentData(file_two),
    }
    command = LinkingAddCommand(add_service, fs, torrent_data)

    output: LinkingAddOutput = command.run()
    output.display()

    result = capsys.readouterr().out

    assert (
        result
        == "\n".join(
            [
                "Linked 1 torrents:",
                "meaningless at /some/place",
                "Added 1 torrents:",
                "meaningless",
                "2 torrents were deleted:",
                "meaningless at /test_path2",
                "meaningless at /test_path",
            ]
        )
        + "\n"
    )


def test_linking_add_run_display_duplicated(mocker: MockerFixture, capsys):
    api = mocker.Mock(spec=TransmissionApi)
    api.add_torrent_with_files.return_value = CommandResult(
        success=False, error="duplicate"
    )
    api.add_torrent.return_value = CommandResult(success=False, error="duplicate")
    add_service = AddService(api)

    fs = MockFilesystem({"test_path"})
    path = Path("/", "test_path")
    file = MetainfoFile(
        {
            "name": "meaningless",
            "info_hash": "meaningless and necessary",
            "info": {"length": 5},
        },
        path,
    )
    command = LinkingAddCommand(
        add_service, fs, {TorrentData(file, Path("/some/place"))}
    )

    output: LinkingAddOutput = command.run()
    output.display()

    result = capsys.readouterr().out

    assert result == "\n".join(["There are 1 duplicates:", "meaningless"]) + "\n"


def test_linking_add_run_display_failed(mocker: MockerFixture, capsys):
    api = mocker.Mock(spec=TransmissionApi)
    api.add_torrent_with_files.return_value = CommandResult(
        error="unknown", success=False
    )
    api.add_torrent.return_value = CommandResult(error="unknown", success=False)
    add_service = AddService(api)

    fs = MockFilesystem({"test_path"})
    locator: TorrentDataLocator = DefaultTorrentDataLocator(fs)
    find_service = FindService(locator)
    path = Path("/", "test_path")
    file = MetainfoFile(
        {
            "name": "meaningless",
            "info_hash": "meaningless and necessary",
            "info": {"length": 5},
        },
        path,
    )
    command = LinkingAddCommand(
        add_service, fs, {TorrentData(file, Path("/some/place"))}
    )

    output: LinkingAddOutput = command.run()
    output.display()

    result = capsys.readouterr().out

    assert result == "\n".join(["1 failed:", "meaningless because: unknown"]) + "\n"


def test_linking_add_dry_run_display(mocker: MockerFixture, capsys):
    api = mocker.Mock(spec=TransmissionApi)
    api.add_torrent_with_files.return_value = CommandResult(success=True)
    api.add_torrent.return_value = CommandResult(success=True)
    add_service = AddService(api)

    fs = MockFilesystem({"test_path"})
    path = Path("/", "test_path")
    file = MetainfoFile(
        {
            "name": "meaningless",
            "info_hash": "meaningless and necessary",
            "info": {"length": 5},
        },
        path,
    )
    torrent_data = {TorrentData(file, Path("/some/place")), TorrentData(file)}
    command = LinkingAddCommand(add_service, fs, torrent_data)

    output: LinkingAddOutput = command.dry_run()
    output.dry_run_display()

    result = capsys.readouterr().out

    assert (
        result
        == "\n".join(
            [
                "Would add 1 torrents with data:",
                "meaningless at /some/place",
                "Would add 1 torrents without data:",
                "meaningless",
            ]
        )
        + "\n"
    )
