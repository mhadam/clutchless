from pathlib import Path

from clutchless.torrent import convert_file, TorrentFile


def test_convert_file():
    file_dir = 'some_dir'
    file_name = 'some_name'
    file_length = 128
    file = {
        'length': file_length,
        'path': [file_dir, file_name]
    }

    result = convert_file(file)

    assert isinstance(result, TorrentFile)
    assert result.path == Path(file_dir, file_name)
    assert result.length == file_length
