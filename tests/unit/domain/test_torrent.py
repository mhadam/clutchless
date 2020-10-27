from pathlib import Path
from typing import Iterable, Sequence, Mapping

import pytest
from pytest_mock import MockerFixture

from clutchless.domain.torrent import convert_file, TorrentFile, MetainfoFile
from clutchless.external.filesystem import Filesystem


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
    file = MetainfoFile({"info_hash": "not_equal"})

    assert hash(file) == hash("not_equal")


def test_metainfo_str_repr():
    file = MetainfoFile({"name": "some_name"})

    assert str(file) == "some_name"


def mock_info_files(paths: Iterable[Path]) -> Sequence[Mapping]:
    return [{"path": path.parts, "length": 5} for path in paths]


def test_metainfo_find(mocker):
    torrent_files = {Path("torrent_file1"), Path("folder/torrent_file2")}
    info_files = mock_info_files(torrent_files)

    fs_files = {Path("/", "root", "torrent_name", file) for file in torrent_files}

    def find(path: Path, filename: str, is_file: bool):
        if path == Path("/") and filename == "torrent_name" and not is_file:
            return Path("/", "root")

    fs = mocker.Mock(spec=Filesystem)
    fs.exists.side_effect = lambda path: path in fs_files
    fs.is_file.side_effect = lambda path: path in fs_files
    fs.find.side_effect = find

    metainfo_file = MetainfoFile(
        {"name": "torrent_name", "info": {"files": info_files}}
    )

    result = metainfo_file.find(fs, Path("/"))

    assert result


def test_verify_metainfo_location_singlefile(mocker: MockerFixture):
    fs = mocker.Mock(spec=Filesystem)
    fs.exists.side_effect = lambda path: path == Path("/root/torrent_name")
    fs.is_file.side_effect = lambda path: path == Path("/root/torrent_name")

    metainfo_file = MetainfoFile(
        {
            "name": "torrent_name",
            "info": {"length": 5},
            "files": [TorrentFile(Path("torrent_name"), 5)],
        }
    )

    result = metainfo_file.verify(fs, Path("/root"))

    fs.is_file.assert_called_once_with(Path("/root/torrent_name"))
    assert result


def test_verify_metainfo_location_multifile(mocker: MockerFixture):
    torrent_files = {Path("torrent_file1"), Path("folder/torrent_file2")}
    info_files = mock_info_files(torrent_files)

    fs_files = {Path("/", "root", "torrent_name", file) for file in torrent_files}

    fs = mocker.Mock(spec=Filesystem)
    fs.exists.side_effect = lambda path: path in fs_files
    fs.is_file.side_effect = lambda path: path in fs_files

    metainfo_file = MetainfoFile(
        {"name": "torrent_name", "info": {"files": info_files}}
    )

    result = metainfo_file.verify(fs, Path("/root"))

    assert result
