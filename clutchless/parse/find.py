""" Locate data that belongs to torrent files.

Usage:
    clutchless find <torrents> ... (-d <data> ...)

Arguments:
    <torrents> ...  Filepath of torrent files or directories to search for torrent files.

Options:
    -d <data> ...  Folder(s) to search for data that belongs to the specified torrent files.
"""

from pathlib import Path
from typing import Mapping, Set

from clutchless.parse.shared import DataDirectoryParser, TorrentFileCrawler
from clutchless.search import TorrentDataMatcher, TorrentNameStore, TorrentFileStore
from clutchless.torrent import TorrentFile
from clutchless.transmission import TransmissionApi


class FindArgs:
    def __init__(self):
        pass

    @classmethod
    def get_matcher(cls, args: Mapping, client: TransmissionApi) -> TorrentDataMatcher:
        name_store = TorrentNameStore()
        file_store = TorrentFileStore()
        for path in cls.get_torrent_files(args):
            torrent_file = TorrentFile.from_path(path)
            name_store.add(torrent_file)
            file_store.add(torrent_file)
        return TorrentDataMatcher(name_store, file_store, client)

    @classmethod
    def get_data_dirs(cls, args: Mapping) -> Set[Path]:
        raw_data_directories = args["-d"]
        parser = DataDirectoryParser()
        return parser.parse(raw_data_directories)

    @classmethod
    def get_torrent_files(cls, args: Mapping) -> Set[Path]:
        raw_torrents_paths = args["<torrents>"]
        crawler = TorrentFileCrawler()
        return crawler.crawl(raw_torrents_paths)
