from pathlib import Path

from pytest_mock import MockerFixture

from clutchless.command.find import FindCommand
from clutchless.domain.torrent import MetainfoFile
from clutchless.external.filesystem import Filesystem
from clutchless.external.metainfo import (
    TorrentData,
    TorrentDataLocator,
    MetainfoReader,
)
from clutchless.service.torrent import FindService


def test_find_found(mocker: MockerFixture):
    metainfo_path = Path("/", "metainfo.torrent")
    search_path = Path("/", "data")
    properties = {
        "info_hash": "meaningless and necessary",
        "name": "test_name",
        "info": {"length": 0},
    }
    metainfo_file = MetainfoFile(properties, metainfo_path)
    fs = mocker.Mock(spec=Filesystem)
    reader = mocker.Mock(spec=MetainfoReader)
    reader.from_path.return_value = metainfo_file

    locator = mocker.Mock(spec=TorrentDataLocator)
    locator.find.return_value = TorrentData(metainfo_file, Path("/", "data"))
    find_service = FindService(locator)

    command = FindCommand(find_service, {metainfo_file})
    output = command.run()

    assert output.found == {TorrentData(metainfo_file, search_path)}


def test_find_missing(mocker: MockerFixture):
    metainfo_path = Path("/", "metainfo.torrent")
    properties = {
        "info_hash": "meaningless and necessary",
        "name": "test_name",
        "info": {"length": 0},
    }
    metainfo_file = MetainfoFile(properties, metainfo_path)
    reader = mocker.Mock(spec=MetainfoReader)
    reader.from_path.return_value = metainfo_file

    locator = mocker.Mock(spec=TorrentDataLocator)
    locator.find.return_value = None
    find_service = FindService(locator)

    command = FindCommand(find_service, {metainfo_file})
    output = command.run()

    assert output.found == set()
    assert output.missing == {metainfo_file}
