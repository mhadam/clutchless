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

from clutchless.domain.torrent import MetainfoFile
from clutchless.external.filesystem import Filesystem, FileLocator
from clutchless.external.metainfo import MetainfoReader
from clutchless.service.file import collect_metainfo_files, collect_metainfo_paths
from clutchless.spec.shared import DataDirectoryParser


class FindArgs:
    def __init__(
        self,
        args: Mapping,
        reader: MetainfoReader,
        fs: Filesystem,
        locator: FileLocator,
    ):
        self.args = args
        self.reader = reader
        self.fs = fs
        self.locator = locator

    def get_data_dirs(self) -> Set[Path]:
        raw_data_directories = self.args["-d"]
        parser = DataDirectoryParser(self.fs)
        return parser.parse(raw_data_directories)

    def get_torrent_files_paths(self) -> Set[Path]:
        raw_torrents_paths = set(self.args["<torrents>"])
        return collect_metainfo_paths(self.fs, self.locator, raw_torrents_paths)

    def get_torrent_files(self) -> Set[MetainfoFile]:
        raw_torrents_paths = set(self.args["<torrents>"])
        return collect_metainfo_files(
            self.fs, self.locator, raw_torrents_paths, self.reader
        )
