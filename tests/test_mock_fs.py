from pathlib import Path

import pytest

from clutchless.external.filesystem import CopyError
from tests.mock_fs import MockFilesystem


def test_mock_fs():
    fs = MockFilesystem({"folder": {"file"}})

    assert set(fs.children(Path("/folder"))) == {Path("/folder/file")}
    assert set(fs.children(Path("/"))) == {Path("/folder")}


def test_mock_fs_iterable():
    files = ["file1", "file2", "file3"]
    fs = MockFilesystem(files)

    assert set(fs.children(Path("/"))) == {Path("/", path) for path in files}


def test_mock_fs_mixed_abstraction_set():
    files = {"file1", "file2", "file3"}
    fs = MockFilesystem({"folder": files})

    assert set(fs.children(Path("/folder"))) == {
        Path("/folder", path) for path in files
    }


def test_mock_fs_mixed_abstraction():
    files = ["file1", "file2", "file3"]
    fs = MockFilesystem({"folder": files})

    assert set(fs.children(Path("/folder"))) == {
        Path("/folder", path) for path in files
    }


def test_mock_fs_nested_children():
    files = {"file1", "file2.torrent", "file3"}
    fs = MockFilesystem({"upper": {"testing": files}})

    result = set(fs.children(Path("/upper/testing")))

    assert result == {Path("/", "upper", "testing", file) for file in files}


def test_mock_fs_nested_complex():
    fs = MockFilesystem(
        {
            "upper": {"testing": {"file1", "file2.torrent", "file3", "file4.torrent"}},
            "multi": ["file7", {"another": ["file5", {"level3": {"file8"}}]}],
        }
    )

    assert fs.exists(Path("/multi/another/level3"))


def test_mock_fs_nested_complex_2():
    fs = MockFilesystem(
        {"data": {"torrent_name": ["torrent_file1", {"folder": "torrent_file2"}]}}
    )

    assert fs.exists(Path("/data/torrent_name/folder/torrent_file2"))


def test_mock_fs_top_level():
    fs = MockFilesystem({"test"})

    assert fs.exists(Path("/test"))


def test_copy():
    fs = MockFilesystem({"file_1", "test_path"})
    with pytest.raises(CopyError) as e:
        fs.copy(Path("/file_1"), Path("/test_path"))
    assert "destination is a file" in str(e)


def test_copy_nested():
    fs = MockFilesystem(["file_1", {"test_path": ["file_1"]}])
    with pytest.raises(CopyError) as e:
        fs.copy(Path("/file_1"), Path("/test_path"))
    assert "destination already exists" in str(e)
