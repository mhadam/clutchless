from pathlib import Path
from typing import Iterable, Sequence, Mapping

from pytest_mock import MockerFixture

from clutchless.domain.torrent import MetainfoFile, TorrentFile
from clutchless.external.filesystem import DefaultFileLocator, Filesystem, FileLocator
from clutchless.external.metainfo import TorrentDataLocator, DefaultTorrentDataLocator, DefaultTorrentDataReader, \
    TorrentDataReader, CustomTorrentDataLocator, TorrentData


def test_get_parent_of_wanted_matches_dirs():
    is_dir_pairs = [(Path(), True)]

    result = DefaultFileLocator.get_parent_of_wanted_matches(is_dir_pairs, True)

    assert result == Path()


def test_get_parent_of_wanted_matches_files():
    is_dir_pairs = [(Path(), False)]

    result = DefaultFileLocator.get_parent_of_wanted_matches(is_dir_pairs, False)

    assert result == Path()


def mock_info_files(paths: Iterable[Path]) -> Sequence[Mapping]:
    return [{"path": path.parts, "length": 5} for path in paths]


def test_metainfo_find(mocker):
    torrent_files = {Path("torrent_file1"), Path("folder/torrent_file2")}
    info_files = mock_info_files(torrent_files)

    fs_files = {Path("/", "root", "torrent_name", file) for file in torrent_files}

    def find(path: Path, filename: str, is_file: bool):
        if path == Path("/") and filename == "torrent_name" and is_file:
            return Path("/", "root")

    fs = mocker.Mock(spec=Filesystem)
    fs.exists.side_effect = lambda path: path in fs_files
    fs.is_file.side_effect = lambda path: path in fs_files

    metainfo_file = MetainfoFile(
        {"name": "torrent_name", "info": {"files": info_files}}
    )

    file_locator = mocker.Mock(spec=FileLocator)
    file_locator.locate.return_value = Path('/root')
    data_reader = DefaultTorrentDataReader(fs)
    data_locator: TorrentDataLocator = CustomTorrentDataLocator(file_locator, data_reader)

    result = data_locator.find(metainfo_file)

    assert result


def test_default_torrent_reader_verify_single_file(mocker: MockerFixture):
    fs = mocker.Mock(spec=Filesystem)
    fs.exists.side_effect = lambda path: path == Path("/root/torrent_name")

    path = Path('/root')
    metainfo_file = MetainfoFile(
        {
            "name": "torrent_name",
            "info": {"length": 5},
        }
    )

    reader: TorrentDataReader = DefaultTorrentDataReader(fs)

    result = reader.verify(path, metainfo_file)

    fs.exists.assert_called_once_with(Path("/root/torrent_name"))
    assert result


def test_default_torrent_reader_verify_multiple_file(mocker: MockerFixture):
    fs = mocker.Mock(spec=Filesystem)
    fs.exists.side_effect = lambda path: path == Path("/root/torrent_name/file1")

    path = Path('/root')
    metainfo_file = MetainfoFile(
        {
            "name": "torrent_name",
            "info": {
                "files": [{"path": ["file1"], "length": 5}]
            }
        }
    )

    reader: TorrentDataReader = DefaultTorrentDataReader(fs)

    result = reader.verify(path, metainfo_file)

    fs.exists.assert_called_once_with(Path("/root/torrent_name/file1"))
    assert result
