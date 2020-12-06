from pathlib import Path

import pytest

from clutchless.external.filesystem import (
    DefaultFilesystem,
    FileLocator,
    DefaultFileLocator,
)


def test_default_filesystem_file(tmp_path):
    file: Path = tmp_path / "testfile"
    file.touch()

    fs = DefaultFilesystem()

    assert fs.exists(file)
    assert fs.is_file(file)


def test_default_filesystem_dir(tmp_path):
    fs = DefaultFilesystem()

    assert fs.exists(tmp_path)
    assert fs.is_directory(tmp_path)


def test_default_filesystem_children(tmp_path):
    expected_children = set()
    for name in range(10):
        file = tmp_path / str(name)
        file.touch()
        expected_children.add(file)
    fs = DefaultFilesystem()

    children = fs.children(tmp_path)

    assert set(children) == expected_children


@pytest.mark.asyncio
async def test_default_locator_find_file(tmp_path):
    file = tmp_path / "test_file"
    file.touch()
    fs = DefaultFilesystem()
    locator: FileLocator = DefaultFileLocator(fs, tmp_path)

    result = await locator.locate_file("test_file")

    assert result == tmp_path


@pytest.mark.asyncio
async def test_default_filesystem_find_directory(tmp_path):
    file = tmp_path / "test_dir"
    file.mkdir(parents=True)
    fs = DefaultFilesystem()
    locator: FileLocator = DefaultFileLocator(fs, tmp_path)

    result = await locator.locate_directory("test_dir")

    assert result == tmp_path
