from pathlib import Path

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
