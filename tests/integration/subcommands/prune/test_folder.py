import os
from os.path import abspath
from pathlib import Path
from typing import Set

from pytest_mock import MockerFixture

from clutchless.subcommand.prune.folder import DryRunPruneFolderCommand, DryRunPruneFolderCommandResult, \
    MetainfoFileClientMatcher, PruneFolderCommand, PruneFolderCommandResult
from clutchless.torrent import MetainfoFile
from clutchless.transmission import TransmissionApi


def test_metainfo_client_matcher(mocker: MockerFixture):
    client = mocker.Mock(spec=TransmissionApi)
    client.get_torrent_ids_by_hash.return_value = {
        '4003b4b4fceffabf93e95045f12334056a7d4cb8': 1
    }

    integration_package_path = Path(abspath(__file__)).parent.parent.parent
    torrent_path_one = Path(integration_package_path, 'assets/being_earnest.torrent')
    torrent_path_two = Path(integration_package_path, 'assets/ion.torrent')
    metainfo_one = MetainfoFile.from_path(torrent_path_one)
    metainfo_two = MetainfoFile.from_path(torrent_path_two)
    metainfo_files: Set[MetainfoFile] = {metainfo_one, metainfo_two}
    matcher = MetainfoFileClientMatcher(client, metainfo_files)

    result = matcher.get_metainfo_files_by_id()

    assert result == {
        1: metainfo_one
    }


def test_dryrun_prune_folder(mocker: MockerFixture):
    client = mocker.Mock(spec=TransmissionApi)
    client.get_torrent_ids_by_hash.return_value = {
        '4003b4b4fceffabf93e95045f12334056a7d4cb8': 1
    }

    integration_package_path = Path(abspath(__file__)).parent.parent.parent
    torrent_path_one = Path(integration_package_path, 'assets/being_earnest.torrent')
    torrent_path_two = Path(integration_package_path, 'assets/ion.torrent')
    metainfo_one = MetainfoFile.from_path(torrent_path_one)
    metainfo_two = MetainfoFile.from_path(torrent_path_two)
    metainfo_files: Set[MetainfoFile] = {metainfo_one, metainfo_two}
    command = DryRunPruneFolderCommand(client, metainfo_files)

    result: DryRunPruneFolderCommandResult = command.run()

    assert result.pruned == {metainfo_one}


def test_prune_folder(mocker: MockerFixture):
    mocker.patch('os.remove')
    client = mocker.Mock(spec=TransmissionApi)
    client.get_torrent_ids_by_hash.return_value = {
        '4003b4b4fceffabf93e95045f12334056a7d4cb8': 1
    }

    integration_package_path = Path(abspath(__file__)).parent.parent.parent
    torrent_path_one = Path(integration_package_path, 'assets/being_earnest.torrent')
    torrent_path_two = Path(integration_package_path, 'assets/ion.torrent')
    metainfo_one = MetainfoFile.from_path(torrent_path_one)
    metainfo_two = MetainfoFile.from_path(torrent_path_two)
    metainfo_files: Set[MetainfoFile] = {metainfo_one, metainfo_two}
    command = PruneFolderCommand(client, metainfo_files)

    result: PruneFolderCommandResult = command.run()

    os.remove.assert_called_once_with(torrent_path_one)
    assert result.pruned == {metainfo_one}
