""" Locate data that belongs to torrent files.

Usage:
    clutchless find (<torrents> ...) (-d <data> ...)

Arguments:
    <torrents> ...  Filepath of torrent files or directories to search for torrent files.

Options:
    -d <data> ...  Folder(s) to search for data that belongs to the specified torrent files.
"""

from pathlib import Path
from typing import Mapping, Set

from clutchless.spec.shared import DataDirectoryParser, MetainfoFileCrawler
from clutchless.search import VerifyingTorrentSearcher, NameMatchingTorrentSearcher
from clutchless.domain.torrent import MetainfoFile
from clutchless.external.transmission import TransmissionApi


class FindArgs:
    def __init__(self, args: Mapping, client: TransmissionApi):
        self.args = args
        self.client = client

    def get_verifying_searcher(self) -> VerifyingTorrentSearcher:
        return TorrentSearcher(self.client)

    def get_name_matching_searcher(self) -> NameMatchingTorrentSearcher:
        return NameMatchingTorrentSearcher(self.client)

    def get_data_dirs(self) -> Set[Path]:
        raw_data_directories = self.args["-d"]
        parser = DataDirectoryParser()
        return parser.parse(raw_data_directories)

    def get_torrent_files_paths(self) -> Set[Path]:
        raw_torrents_paths = self.args["<torrents>"]
        crawler = MetainfoFileCrawler()
        return crawler.crawl(raw_torrents_paths)

    def get_torrent_files(self) -> Set[MetainfoFile]:
        torrent_file_paths = self.get_torrent_files_paths()
        return {
            MetainfoFile.from_path(torrent_file) for torrent_file in torrent_file_paths
        }
