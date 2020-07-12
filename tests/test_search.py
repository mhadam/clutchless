from pathlib import Path
from unittest.mock import MagicMock, Mock, PropertyMock


def test_parse_directories():
    path = "dir1/dir2/file.mkv"

    result = parse_directories(path)

    assert len(result) == 2
    assert result == {"dir1", "dir2"}


def test_no_directories_from_a_file():
    path = "a_file.mkv"

    result = parse_directories(path)

    assert not bool(result)


def test_matching_file():
    Path.is_file = Mock(return_value=True)
    match_path = Path("/torrents/little_women/little_women.txt")
    torrent_file_path = Path("little_women/little_women.txt")

    result = match(match_path, torrent_file_path)

    assert result


def test_matching_dir():
    Path.is_file = Mock(return_value=False)
    Path.is_dir = Mock(return_value=True)
    match_path = Path("/app/resources/data/nested_example/another/little_women")
    torrent_file_path = Path("little_women/little_women.txt")

    result = match(match_path, torrent_file_path)

    assert result


def test_matching_single_file():
    Path.is_file = Mock(return_value=True)
    match_path = Path("/app/resources/data/ion.txt")
    torrent_file_path = Path("ion.txt")

    result = match(match_path, torrent_file_path)

    assert result
