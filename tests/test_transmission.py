import pathlib

from clutchless.torrent import MetainfoFile
from clutchless.transmission import PartialTorrent


def test_verify_partial_torrent(mocker):
    mocker.patch.object(pathlib.Path, "exists", lambda self: True)
    partial_torrent = PartialTorrent("some_name", {"books/book1.txt"})

    torrent_file = MetainfoFile(pathlib.Path("some_location"))
    torrent_file._properties = {"files": ["books/book1.txt", "books/book2.txt"]}

    path = pathlib.Path("some_location")

    result = partial_torrent.verify(torrent_file, path)

    assert result


def test_verify_partial_torrent_when_fail(mocker):
    mocker.patch.object(pathlib.Path, "exists", lambda self: False)
    partial_torrent = PartialTorrent("some_name", {"books/book1.txt"})

    torrent_file = MetainfoFile(pathlib.Path("some_location"))
    torrent_file._properties = {"files": ["books/book1.txt", "books/book2.txt"]}

    path = pathlib.Path("some_location")

    result = partial_torrent.verify(torrent_file, path)

    assert not result
