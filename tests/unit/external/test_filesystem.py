import asyncio
from pathlib import Path
from typing import Iterable, Sequence, Mapping

import pytest
from pytest_mock import MockerFixture

from clutchless.domain.torrent import MetainfoFile
from clutchless.external.filesystem import (
    SingleDirectoryFileLocator,
    Filesystem,
    FileLocator,
    MultipleDirectoryFileLocator,
)
from clutchless.external.metainfo import (
    TorrentDataLocator,
    DefaultTorrentDataReader,
    TorrentDataReader,
    CustomTorrentDataLocator,
)
from tests.mock_fs import MockFilesystem, InfinitelyDeepFilesystem


def test_get_parent_of_wanted_matches_dirs():
    is_dir_pairs = [(Path(), True)]

    result = SingleDirectoryFileLocator._get_parent_of_wanted_matches(
        is_dir_pairs, True
    )

    assert result == Path()


def test_get_parent_of_wanted_matches_files():
    is_dir_pairs = [(Path(), False)]

    result = SingleDirectoryFileLocator._get_parent_of_wanted_matches(
        is_dir_pairs, False
    )

    assert result == Path()


def mock_info_files(paths: Iterable[Path]) -> Sequence[Mapping]:
    return [{"path": path.parts, "length": 5} for path in paths]


@pytest.mark.asyncio
async def test_metainfo_find():
    torrent_files = {Path("torrent_file1"), Path("folder/torrent_file2")}
    info_files = mock_info_files(torrent_files)

    fs = MockFilesystem(
        {"data": {"torrent_name": ["torrent_file1", {"folder": "torrent_file2"}]}}
    )

    metainfo_file = MetainfoFile(
        {"name": "torrent_name", "info": {"files": info_files}}
    )

    data_locator: TorrentDataLocator = CustomTorrentDataLocator(
        SingleDirectoryFileLocator(fs), DefaultTorrentDataReader(fs)
    )

    result = await data_locator.find(metainfo_file)

    assert result.location


def test_default_torrent_reader_verify_single_file(mocker: MockerFixture):
    fs = mocker.Mock(spec=Filesystem)
    fs.exists.side_effect = lambda path: path == Path("/root/torrent_name")

    path = Path("/root")
    metainfo_file = MetainfoFile({"name": "torrent_name", "info": {"length": 5},})

    reader: TorrentDataReader = DefaultTorrentDataReader(fs)

    result = reader.verify(path, metainfo_file)

    fs.exists.assert_called_once_with(Path("/root/torrent_name"))
    assert result


def test_default_torrent_reader_verify_multiple_file(mocker: MockerFixture):
    fs = mocker.Mock(spec=Filesystem)
    fs.exists.side_effect = lambda path: path == Path("/root/torrent_name/file1")

    path = Path("/root")
    metainfo_file = MetainfoFile(
        {"name": "torrent_name", "info": {"files": [{"path": ["file1"], "length": 5}]}}
    )

    reader: TorrentDataReader = DefaultTorrentDataReader(fs)

    result = reader.verify(path, metainfo_file)

    fs.exists.assert_called_once_with(Path("/root/torrent_name/file1"))
    assert result


@pytest.mark.asyncio
async def test_locate_torrents():
    fs = MockFilesystem(
        {"upper": {"testing": {"file1", "file2.torrent", "file3", "file4.torrent"}}}
    )

    locator = SingleDirectoryFileLocator(fs, Path("/upper/testing"))

    results = set()
    async for path in locator.collect(".torrent"):
        results.add(path)

    assert results == {
        Path("/upper/testing/file2.torrent"),
        Path("/upper/testing/file4.torrent"),
    }


@pytest.mark.asyncio
async def test_locate_torrents_cancelled():
    fs = InfinitelyDeepFilesystem()
    locator = SingleDirectoryFileLocator(fs, Path("/"))

    async def _main():
        results = set()
        async for path in locator.collect(".torrent"):
            results.add(path)
        return results

    task = asyncio.create_task(_main())

    with pytest.raises(asyncio.TimeoutError):
        _ = await asyncio.wait_for(task, 0.001)
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "name,expected",
    [
        ("file1", "/upper/testing"),
        ("file2.torrent", "/upper/testing"),
        ("file3", "/upper/testing"),
        ("file7", "/multi"),
        ("file8", "/multi/another/level3"),
    ],
)
async def test_single_directory_filesystem_locate_file_complex_nested(name, expected):
    fs = MockFilesystem(
        {
            "upper": {"testing": {"file1", "file2.torrent", "file3", "file4.torrent"}},
            "multi": ["file7", {"another": ["file5", {"level3": {"file8"}}]}],
        }
    )
    locator = SingleDirectoryFileLocator(fs)

    result = await locator.locate_file(name)

    assert result == Path(expected)


@pytest.mark.asyncio
async def test_multiple_directory_filesystem_locate_file():
    location = Path("/multi/another/level3")
    fs = MockFilesystem(
        {
            "upper": {"testing": {"file1", "file2.torrent", "file3", "file4.torrent"}},
            "multi": ["file7", {"another": ["file5", {"level3": {"file8"}}]}],
        }
    )

    directories = [Path("/upper"), Path("/multi/another")]
    locator = MultipleDirectoryFileLocator(directories, fs)

    result = await locator.locate_file("file8")

    assert result == location


@pytest.mark.asyncio
async def test_multiple_directory_filesystem():
    fs = MockFilesystem(
        {
            "upper": {"testing": {"file1", "file2.torrent", "file3", "file4.torrent"}},
            "multi": [
                "file7",
                {"another": ["file5", {"level3": {"file8", "file10.torrent"}}]},
            ],
        }
    )

    directories = [Path("/upper"), Path("/multi")]
    locator = MultipleDirectoryFileLocator(directories, fs)

    results = set()
    async for path in locator.collect(".torrent"):
        results.add(path)

    assert results == {
        Path("/multi/another/level3/file10.torrent"),
        Path("/upper/testing/file2.torrent"),
        Path("/upper/testing/file4.torrent"),
    }
