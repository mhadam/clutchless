from pathlib import Path

import pytest

from clutchless.external.filesystem import DefaultFilesystem
from clutchless.service.file import (
    parse_path,
    validate_files,
    validate_directories,
    validate_exists,
    get_valid_files,
    get_valid_directories,
    get_valid_paths,
)


def test_validate_path_directory(tmp_path):
    fs = DefaultFilesystem()

    path = tmp_path / "test_file"
    fs.touch(path)
    paths = {path}

    with pytest.raises(Exception) as e:
        validate_directories(fs, paths)

    assert "is not a directory" in str(e.value)


def test_validate_files(tmp_path):
    fs = DefaultFilesystem()

    path = tmp_path / "test_directory"
    fs.create_dir(path)
    paths = {path}

    with pytest.raises(Exception) as e:
        validate_files(fs, paths)

    assert "is not a file" in str(e.value)


def test_validate_exists(tmp_path):
    fs = DefaultFilesystem()

    path = tmp_path / "test_file"

    with pytest.raises(Exception) as e:
        validate_exists(fs, path)

    assert "path does not exist" in str(e.value)


def test_path_absolute_differences(tmp_path):
    absolute_str = str(tmp_path)
    absolute_path = Path(absolute_str)

    test_file = Path(tmp_path, "test_file")
    test_file.touch()
    indirect_path = Path(test_file, "..")

    assert test_file.exists()
    assert absolute_path != Path(indirect_path)
    assert absolute_path == Path(indirect_path).resolve()


def test_parse_path(tmp_path):
    fs = DefaultFilesystem()
    fs.touch(tmp_path / "test_file")

    value = str(tmp_path / "test_file" / "..")

    result = parse_path(fs, value)

    assert result == tmp_path


def test_get_valid_directories(tmp_path):
    fs = DefaultFilesystem()
    fs.touch(tmp_path / "test_file")

    values = {str(tmp_path / "test_file" / "..")}

    result = get_valid_directories(fs, values)

    assert str(result.pop()) == str(tmp_path)


def test_get_valid_files(tmp_path):
    fs = DefaultFilesystem()
    fs.create_dir(tmp_path / "test_dir")
    fs.touch(tmp_path / "test_file")

    values = {str(tmp_path / "test_dir" / ".." / "test_file")}

    result = get_valid_files(fs, values)

    assert str(result.pop()) == str(tmp_path / "test_file")


def test_get_valid_paths(tmp_path):
    fs = DefaultFilesystem()
    fs.create_dir(tmp_path / "test_dir")
    fs.touch(tmp_path / "test_file")

    values = {
        str(tmp_path / "test_dir" / ".." / "test_file"),
        str(tmp_path / "test_dir" / ".." / "test_dir"),
    }

    result = get_valid_paths(fs, values)

    assert result == {tmp_path / "test_dir", tmp_path / "test_file"}
