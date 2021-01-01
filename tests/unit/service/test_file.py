import asyncio
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from clutchless.domain.torrent import MetainfoFile
from clutchless.external.filesystem import SingleDirectoryFileLocator
from clutchless.external.metainfo import MetainfoReader
from clutchless.service.file import (
    collect_from_aggregate,
    collect_metainfo_paths,
    _collect,
    collect_metainfo_files,
)
from tests.mock_fs import MockFilesystem, InfinitelyDeepFilesystem


def test_collect_metainfo_paths():
    raw_paths = {
        "/some_path",
        "/another_path/file.torrent",
    }

    fs = MockFilesystem(
        {
            "some_path": {"child1": {"file2.torrent", "file3"}},
            "another_path": {"file.torrent"},
        }
    )

    results = collect_metainfo_paths(fs, raw_paths)

    assert set(results) == {
        Path("/another_path/file.torrent"),
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

    with pytest.raises(asyncio.CancelledError):
        _ = asyncio.run(_timed())


@pytest.mark.asyncio
async def test_collect_task_cancel():
    fs = MockFilesystem(
        {
            "some_path": {"child1": {"file2.torrent", "file3"}},
            "another_path": {"file.torrent"},
        }
    )

    paths = {Path("/")}

    task = asyncio.create_task(_collect(fs, paths))
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_collect_task_hanging_cancel():
    fs = InfinitelyDeepFilesystem()

    paths = {Path("/")}

    task = asyncio.create_task(_collect(fs, paths))
    # needs a pause otherwise will immediately cancel without executing task
    await asyncio.sleep(0.01)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


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

    result = collect_metainfo_files(reader, fs, paths)

    assert result == {
        from_path(Path("/some_path/child1/file2.torrent")),
        from_path(Path("/another_path/file.torrent")),
    }
