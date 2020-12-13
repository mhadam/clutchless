import asyncio
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from clutchless.domain.torrent import MetainfoFile
from clutchless.external.filesystem import SingleDirectoryFileLocator
from clutchless.external.metainfo import MetainfoReader
from clutchless.service.file import (
    collect_metainfo_paths,
    collect_metainfo_paths_with_timeout,
    collect_from_aggregate,
    collect_metainfo_files_with_timeout,
)
from tests.mock_fs import MockFilesystem, InfinitelyDeepFilesystem


@pytest.mark.asyncio
async def test_collect_metainfo_files():
    raw_paths = {
        Path("/some_path"),
        Path("/another_path/file.torrent"),
    }

    filesystem = MockFilesystem(
        {
            "some_path": {"child1": {"file2.torrent", "file3"}},
            "another_path": {"file.torrent"},
        }
    )

    results = set()
    async for path in collect_metainfo_paths(filesystem, raw_paths):
        results.add(path)

    assert set(results) == {
        Path("/another_path/file.torrent"),
        Path("/some_path/child1/file2.torrent"),
    }


def test_collect_with_timeout():
    fs = MockFilesystem(
        {
            "some_path": {"child1": {"file2.torrent", "file3"}},
            "another_path": {"file.torrent"},
        }
    )

    paths = {Path("/some_path")}
    results = asyncio.run(collect_metainfo_paths_with_timeout(fs, paths, 0.001))

    assert set(results) == {
        Path("/some_path/child1/file2.torrent"),
    }


def test_aggregate_with_timeout_cancel():
    fs = MockFilesystem(
        {
            "some_path": {"child1": {"file2.torrent", "file3"}},
            "another_path": {"file.torrent"},
        }
    )

    locator = SingleDirectoryFileLocator(fs)
    forever_locator = SingleDirectoryFileLocator(InfinitelyDeepFilesystem())
    locators = [locator, forever_locator]

    async def _callback():
        paths = set()
        async for result in collect_from_aggregate(fs, locators):
            paths.add(result)
        return paths

    async def _timed():
        task = asyncio.create_task(_callback())
        await asyncio.sleep(0.001)
        task.cancel()
        await asyncio.sleep(0.001)
        return await task

    results = asyncio.run(_timed())

    assert set(results) == {
        Path("/another_path/file.torrent"),
        Path("/some_path/child1/file2.torrent"),
    }


def test_collect_metainfo_paths_with_timeout():
    fs = MockFilesystem(
        {
            "some_path": {"child1": {"file2.torrent", "file3"}},
            "another_path": {"file.torrent"},
        }
    )

    paths = {Path("/")}

    coro = collect_metainfo_paths_with_timeout(fs, paths, 0.001)

    result = asyncio.run(coro)

    assert set(result) == {
        Path("/another_path/file.torrent"),
        Path("/some_path/child1/file2.torrent"),
    }


def test_collect_metainfo_files_with_timeout(mocker: MockerFixture):
    fs = MockFilesystem(
        {
            "some_path": {"child1": {"file2.torrent", "file3"}},
            "another_path": {"file.torrent"},
        }
    )

    paths = {Path("/")}
    reader = mocker.Mock(spec=MetainfoReader)

    def from_path(path: Path):
        return MetainfoFile({"info_hash": str(path)})

    reader.from_path.side_effect = from_path

    coro = collect_metainfo_files_with_timeout(fs, reader, paths, 0.001)

    result = set(asyncio.run(coro))

    assert result == {
        from_path(Path("/some_path/child1/file2.torrent")),
        from_path(Path("/another_path/file.torrent")),
    }
