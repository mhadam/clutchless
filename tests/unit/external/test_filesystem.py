import asyncio
from pathlib import Path
from typing import Iterable, Sequence, Mapping

import pytest
from pytest_mock import MockerFixture

from clutchless.domain.torrent import MetainfoFile
from clutchless.external.filesystem import DefaultFileLocator, Filesystem, FileLocator
from clutchless.external.metainfo import (
    TorrentDataLocator,
    DefaultTorrentDataReader,
    TorrentDataReader,
    CustomTorrentDataLocator,
)
from tests.mock_fs import MockFilesystem, InfinitelyDeepFilesystem


def test_get_parent_of_wanted_matches_dirs():
    is_dir_pairs = [(Path(), True)]

    result = DefaultFileLocator._get_parent_of_wanted_matches(is_dir_pairs, True)

    assert result == Path()


def test_get_parent_of_wanted_matches_files():
    is_dir_pairs = [(Path(), False)]

    result = DefaultFileLocator._get_parent_of_wanted_matches(is_dir_pairs, False)

    assert result == Path()


def mock_info_files(paths: Iterable[Path]) -> Sequence[Mapping]:
    return [{"path": path.parts, "length": 5} for path in paths]


def test_metainfo_find():
    torrent_files = {Path("torrent_file1"), Path("folder/torrent_file2")}
    info_files = mock_info_files(torrent_files)

    fs = MockFilesystem({"data": ["torrent_file1", {"folder": "torrent_file2"}]})

    metainfo_file = MetainfoFile(
        {"name": "torrent_name", "info": {"files": info_files}}
    )

    file_locator = DefaultFileLocator(fs)
    data_reader = DefaultTorrentDataReader(fs)
    data_locator: TorrentDataLocator = CustomTorrentDataLocator(
        file_locator, data_reader
    )

    result = data_locator.find(metainfo_file)

    assert result


def test_default_torrent_reader_verify_single_file(mocker: MockerFixture):
    fs = mocker.Mock(spec=Filesystem)
    fs.exists.side_effect = lambda path: path == Path("/root/torrent_name")

    path = Path("/root")
    metainfo_file = MetainfoFile(
        {
            "name": "torrent_name",
            "info": {"length": 5},
        }
    )

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

    locator = DefaultFileLocator(fs, Path("/upper/testing"))

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
    locator = DefaultFileLocator(fs, Path("/"))

    async def _main():
        results = set()
        async for path in locator.collect(".torrent"):
            results.add(path)
        return results

    task = asyncio.create_task(_main())

    try:
        _ = await asyncio.wait_for(task, 0.001)
    except asyncio.TimeoutError:
        assert task.result() == set()
