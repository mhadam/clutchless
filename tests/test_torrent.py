from collections import namedtuple

from clutchless.torrent import convert_file_tuple, TorrentFile


def test_convert_file_tuple():
    file_name = 'some_name'
    file_length = 128
    File = namedtuple('file', ['name', 'length'])
    file = File(file_name, file_length)

    result = convert_file_tuple(file)

    assert isinstance(result, TorrentFile)
    assert result.path == file_name
    assert result.length == file_length
