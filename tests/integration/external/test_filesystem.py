from pathlib import Path

from clutchless.external.filesystem import DefaultFilesystem


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


def test_default_filesystem_find_file(tmp_path):
    file = tmp_path / "test_file"
    file.touch()
    fs = DefaultFilesystem()

    result = fs.find(tmp_path, "test_file", True)

    assert result == tmp_path


def test_default_filesystem_find_directory(tmp_path):
    file = tmp_path / "test_dir"
    file.mkdir(parents=True)
    fs = DefaultFilesystem()

    result = fs.find(tmp_path, "test_dir", False)

    assert result == tmp_path
