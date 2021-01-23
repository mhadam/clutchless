from pathlib import Path
from typing import Iterable, Sequence, Mapping

import pytest
from pytest_mock import MockerFixture

from clutchless.domain.torrent import convert_file, TorrentFile, MetainfoFile
from clutchless.external.filesystem import Filesystem
from clutchless.external.metainfo import TorrentDataLocator, DefaultTorrentDataLocator


def test_convert_file():
    file_dir = "some_dir"
    file_name = "some_name"
    file_length = 128
    file = {"length": file_length, "path": [file_dir, file_name]}

    result = convert_file(file)

    assert isinstance(result, TorrentFile)
    assert result.path == Path("some_dir/some_name")
    assert result.length == file_length


def test_metainfo():
    files = [TorrentFile(Path("/"), 1)]
    info = {"files": [{"path": "/", "length": 1}]}
    data = {"name": "test_name", "info_hash": "test_hash", "info": info}
    file = MetainfoFile(data)

    assert file.name == "test_name"
    assert file.info == info
    assert file.info_hash == "test_hash"
    assert file.files == files


def test_metainfo_single_file():
    properties = {"info": {"length": 10}}
    file = MetainfoFile(properties)

    assert file.is_single_file


def test_metainfo_not_single():
    properties = {"info": {"files": []}}
    file = MetainfoFile(properties)

    assert not file.is_single_file


def test_metainfo_invalid():
    properties = {"info": {}}
    file = MetainfoFile(properties)

    with pytest.raises(ValueError) as e:
        _ = file.is_single_file
    assert str(e.value).startswith("must contain either length key")


def test_metainfo_equal():
    first_file = MetainfoFile({"info_hash": "test"})
    second_file = MetainfoFile({"info_hash": "test"})

    assert first_file == second_file
    assert first_file == first_file
    assert first_file is not second_file


def test_metainfo_unequal():
    first_file = MetainfoFile({"info_hash": "not_equal"})
    second_file = MetainfoFile({"info_hash": "test"})

    assert first_file != 5
    assert first_file != second_file
    assert first_file is not second_file


def test_metainfo_hash():
    file = MetainfoFile({"info_hash": "not_equal"}, path=Path(""))

    assert hash(file) == hash(("not_equal", Path("")))


def test_metainfo_str_repr():
    file = MetainfoFile({"name": "some_name"})

    assert str(file) == "some_name"
