from pathlib import Path

from clutchless.external.filesystem import DefaultFilesystem
from clutchless.service.file import make_absolute, parse_path


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
    fs.touch(tmp_path / 'test_file')

    value = str(tmp_path / 'test_file' / '..')

    result = parse_path(fs, value)

    assert result == tmp_path


def test_make_absolute(tmp_path):
    fs = DefaultFilesystem()
    fs.touch(tmp_path / 'test_file')

    values = {str(tmp_path / 'test_file' / '..')}

    result = make_absolute(fs, values)

    assert str(result.pop()) == str(tmp_path)

