import pathlib
from typing import Mapping

from pytest_mock import MockerFixture

from clutchless.search import verify_callback
from clutchless.torrent import TorrentFile
from clutchless.transmission import PartialTorrent
from clutchless.verify import TorrentVerifier, HashCalculator


def test_verify(mocker: MockerFixture):
    mocker.patch.object(pathlib.Path, "exists", lambda self: False)

    test_hash = "dac9630aec642a428cd73f4be0a03569"
    partial_torrents: Mapping[str, PartialTorrent] = {
        test_hash: PartialTorrent("some_name", {"books/book1.txt"})
    }

    torrent_file = TorrentFile(pathlib.Path("some_location"))
    torrent_file._properties = {
        "files": ["books/book1.txt", "books/book2.txt"],
        "info": {"pieces": bytes(test_hash, "utf-8")},
    }
    path = pathlib.Path("something")
    hash_calculator = mocker.MagicMock(HashCalculator)
    hash_calculator.calculate.return_value = b"dac9630aec642a428cd73f4be0a03569"
    verifier = TorrentVerifier(partial_torrents, hash_calculator)
    result = verify_callback(verifier, torrent_file, path)

    assert result


def test_verify_mismatch(mocker: MockerFixture):
    mocker.patch.object(pathlib.Path, "exists", lambda self: False)

    test_hash = "nope!"
    partial_torrents: Mapping[str, PartialTorrent] = {
        test_hash: PartialTorrent("some_name", {"books/book1.txt"})
    }

    torrent_file = TorrentFile(pathlib.Path("some_location"))
    torrent_file._properties = {
        "files": ["books/book1.txt", "books/book2.txt"],
        "info": {"pieces": bytes(test_hash, "utf-8")},
    }
    path = pathlib.Path("something")
    hash_calculator = mocker.MagicMock(HashCalculator)
    hash_calculator.calculate.return_value = b"dac9630aec642a428cd73f4be0a03569"
    verifier = TorrentVerifier(partial_torrents, hash_calculator)
    result = verify_callback(verifier, torrent_file, path)

    assert not result
