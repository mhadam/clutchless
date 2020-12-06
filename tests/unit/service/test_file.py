import asyncio
from pathlib import Path

import pytest

from clutchless.external.filesystem import DefaultFileLocator
from clutchless.service.file import (
    collect_metainfo_paths,
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

    locator = DefaultFileLocator(fs)

    results = asyncio.run(collect_metainfo_files_with_timeout([locator], 1))

    assert set(results) == {
        Path("/another_path/file.torrent"),
        Path("/some_path/child1/file2.torrent"),
    }


def test_collect_with_timeout_cancel():
    fs = MockFilesystem(
        {
            "some_path": {"child1": {"file2.torrent", "file3"}},
            "another_path": {"file.torrent"},
        }
    )

    locator = DefaultFileLocator(fs)
    forever_locator = DefaultFileLocator(InfinitelyDeepFilesystem())

    results = asyncio.run(
        collect_metainfo_files_with_timeout([locator, forever_locator], 1)
    )

    assert set(results) == {
        Path("/another_path/file.torrent"),
        Path("/some_path/child1/file2.torrent"),
    }
