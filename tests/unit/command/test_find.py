from pathlib import Path

from clutchless.command.find import FindCommand
from clutchless.domain.torrent import MetainfoFile
from clutchless.external.metainfo import (
    TorrentData,
    DefaultTorrentDataLocator,
)
from clutchless.service.torrent import FindService
from tests.mock_fs import MockFilesystem


def test_find_found():
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
    fs = MockFilesystem({"data": {"test_name": {"file1", "file2"}}})
    locator = DefaultTorrentDataLocator(fs)
    find_service = FindService(locator)

    command = FindCommand(find_service, {metainfo_file})
    output = command.run()

    assert output.found == {TorrentData(metainfo_file, search_path)}


def test_find_missing():
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
    fs = MockFilesystem({"data"})

    locator = DefaultTorrentDataLocator(fs)
    find_service = FindService(locator)

    command = FindCommand(find_service, {metainfo_file})
    output = command.run()

    assert output.found == set()
    assert output.missing == {metainfo_file}


def test_find_run_output(capsys):
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

    missing_properties = {
        "info_hash": "meaningless and necessary",
        "name": "another_name",
        "info": {
            "files": [
                {"path": ["file3"], "length": 0},
                {"path": ["file4"], "length": 0},
            ]
        },
    }
    missing_metainfo_file = MetainfoFile(missing_properties, Path("/missing.torrent"))
    fs = MockFilesystem({"data": {"test_name": {"file1", "file2"}}})

    locator = DefaultTorrentDataLocator(fs)
    find_service = FindService(locator)

    command = FindCommand(find_service, {metainfo_file, missing_metainfo_file})
    output = command.run()
    output.display()

    result = capsys.readouterr().out
    assert (
        result
        == "\n".join(
            [
                "Starting search - press Ctrl+C to cancel",
                "1/2 test_name found at /data",
                "Found 1 torrents:",
                "\x1b[32m✓ test_name at /data",
                "Did not find 1 torrents:",
                "\x1b[31m✗ another_name",
            ]
        )
        + "\n"
    )
