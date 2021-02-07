from pathlib import Path

from pytest_mock import MockerFixture

from clutchless.command.prune.folder import PruneFolderCommand
from clutchless.domain.torrent import MetainfoFile
from clutchless.service.torrent import PruneService
from tests.mock_fs import MockFilesystem


def test_prune_folder_run(mocker: MockerFixture):
    fs = MockFilesystem({"some_path"})
    files = {
        MetainfoFile({"info_hash": "aaa", "name": "some_name"}, Path("/some_path"))
    }
    service: PruneService = mocker.Mock(spec=PruneService)
    service.get_torrent_hashes.return_value = {"aaa", "bbb"}
    command = PruneFolderCommand(service, fs, files)

    command.run()

    assert not fs.exists(Path("/some_path"))


def test_prune_folder_dry_run(mocker: MockerFixture):
    fs = MockFilesystem({"some_path"})
    files = {
        MetainfoFile({"info_hash": "aaa", "name": "some_name"}, Path("/some_path"))
    }
    service: PruneService = mocker.Mock(spec=PruneService)
    service.get_torrent_hashes.return_value = {"aaa", "bbb"}
    command = PruneFolderCommand(service, fs, files)

    command.dry_run()

    assert fs.exists(Path("/some_path"))


def test_prune_folder_run_output(mocker: MockerFixture, capsys):
    fs = MockFilesystem({"some_path"})
    files = {
        MetainfoFile({"info_hash": "aaa", "name": "some_name"}, Path("/some_path"))
    }
    service: PruneService = mocker.Mock(spec=PruneService)
    service.get_torrent_hashes.return_value = {"aaa", "bbb"}
    command = PruneFolderCommand(service, fs, files)

    output = command.run()
    output.display()
    result = capsys.readouterr().out

    assert (
        result
        == "\n".join(
            ["The following metainfo files were removed:", "some_name at /some_path"]
        )
        + "\n"
    )


def test_prune_folder_run_empty_output(mocker: MockerFixture, capsys):
    fs = MockFilesystem({"some_path"})
    files = {
        MetainfoFile({"info_hash": "ccc", "name": "some_name"}, Path("/some_path"))
    }
    service: PruneService = mocker.Mock(spec=PruneService)
    service.get_torrent_hashes.return_value = {"aaa", "bbb"}
    command = PruneFolderCommand(service, fs, files)

    output = command.run()
    output.display()
    result = capsys.readouterr().out

    assert result == "No metainfo files were removed.\n"


def test_prune_folder_dry_run_output(mocker: MockerFixture, capsys):
    fs = MockFilesystem({"some_path"})
    files = {
        MetainfoFile({"info_hash": "aaa", "name": "some_name"}, Path("/some_path"))
    }
    service: PruneService = mocker.Mock(spec=PruneService)
    service.get_torrent_hashes.return_value = {"aaa", "bbb"}
    command = PruneFolderCommand(service, fs, files)

    output = command.dry_run()
    output.dry_run_display()
    result = capsys.readouterr().out

    assert (
        result
        == "\n".join(
            [
                "The following metainfo files would be removed:",
                "some_name at /some_path",
            ]
        )
        + "\n"
    )


def test_prune_folder_dry_run_empty_output(mocker: MockerFixture, capsys):
    fs = MockFilesystem({"some_path"})
    files = {
        MetainfoFile({"info_hash": "ccc", "name": "some_name"}, Path("/some_path"))
    }
    service: PruneService = mocker.Mock(spec=PruneService)
    service.get_torrent_hashes.return_value = {"aaa", "bbb"}
    command = PruneFolderCommand(service, fs, files)

    output = command.dry_run()
    output.dry_run_display()
    result = capsys.readouterr().out

    assert result == "No metainfo files would be removed.\n"
