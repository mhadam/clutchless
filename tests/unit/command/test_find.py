from pathlib import Path

from pytest_mock import MockerFixture

from clutchless.command.find import FindCommand
from clutchless.domain.torrent import MetainfoFile
from clutchless.external.metainfo import (
    TorrentData,
    TorrentDataLocator,
    MetainfoReader,
    DefaultTorrentDataLocator,
)
from clutchless.service.torrent import FindService
from tests.mock_fs import MockFilesystem


def test_find_found(mocker: MockerFixture):
    metainfo_path = Path("/", "metainfo.torrent")
    search_path = Path("/", "data")
    properties = {
        "info_hash": "meaningless and necessary",
        "name": "test_name",
        "info": {
            "files": [
                {"path": ["file1"], "length": 0},
                {"path": ["file2"], "length": 0},
            ]
        },
    }
    metainfo_file = MetainfoFile(properties, metainfo_path)
    reader = mocker.Mock(spec=MetainfoReader)
    reader.from_path.return_value = metainfo_file

    fs = MockFilesystem({"data": {"test_name": {"file1", "file2"}}})

    locator = DefaultTorrentDataLocator(fs)
    find_service = FindService(locator)

    command = FindCommand(find_service, {metainfo_file})
    output = command.run()

    assert output.found == {TorrentData(metainfo_file, search_path)}


def test_find_missing(mocker: MockerFixture):
    metainfo_path = Path("/", "metainfo.torrent")
    properties = {
        "info_hash": "meaningless and necessary",
        "name": "test_name",
        "info": {
            "files": [
                {"path": ["file1"], "length": 0},
                {"path": ["file2"], "length": 0},
            ]
        },
    }
    metainfo_file = MetainfoFile(properties, metainfo_path)
    reader = mocker.Mock(spec=MetainfoReader)
    reader.from_path.return_value = metainfo_file

    fs = MockFilesystem({"data"})

    locator = DefaultTorrentDataLocator(fs)
    find_service = FindService(locator)

    command = FindCommand(find_service, {metainfo_file})
    output = command.run()

    assert output.found == set()
    assert output.missing == {metainfo_file}
