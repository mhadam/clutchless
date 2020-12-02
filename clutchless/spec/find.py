""" Locate data that belongs to metainfo files.

Usage:
    clutchless find (<metainfo> ...) (-d <data> ...)

Arguments:
    <metainfo> ...  Filepaths of metainfo files or directories to search for metainfo files.

Options:
    -d <data> ...   Folder(s) to search for data that belongs to the specified metainfo files.
"""

from pathlib import Path
from typing import Mapping, Set

from clutchless.domain.torrent import MetainfoFile
from clutchless.external.filesystem import Filesystem, FileLocator
from clutchless.external.metainfo import MetainfoReader
from clutchless.service.file import (
    collect_metainfo_files,
    collect_metainfo_paths,
    get_valid_directories,
)


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
        return get_valid_directories(self.fs, raw_data_directories)

    def get_torrent_files_paths(self) -> Set[Path]:
        raw_torrents_paths = set(self.args["<metainfo>"])
        paths = {Path(path) for path in raw_torrents_paths}
        return collect_metainfo_paths(self.fs, paths)

    def get_torrent_files(self) -> Set[MetainfoFile]:
        raw_torrents_paths = set(self.args["<metainfo>"])
        paths = {Path(path) for path in raw_torrents_paths}
        return collect_metainfo_files(self.fs, paths, self.reader)
