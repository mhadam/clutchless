""" Add torrents to Transmission (with or without data).

Usage:
    clutchless add [--dry-run] [--delete] [-f | --force] <torrents> ... [-d <data> ...]

Arguments:
    <torrents>  Torrent files (.torrent) to add to Transmission.

Options:
    -d <data> ...   Data to associate to torrents.
    -f, --force     Add torrents even when they're not found.
    --delete        Delete successfully added torrents (meaningless when used with --dry-run).
    --dry-run       Output what would be done instead of modifying anything.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Set

from clutchless.parse.shared import TorrentFileCrawler, DataDirectoryParser


@dataclass
class AddArgs:
    torrent_files: Set[Path]
    data_dirs: Set[Path]

    @staticmethod
    def parse(args: Mapping) -> "AddArgs":
        crawler = TorrentFileCrawler()
        torrent_files = crawler.crawl(args["<torrents>"])
        parser = DataDirectoryParser()
        data_dirs = parser.parse(args.get("-d"))
        return AddArgs(torrent_files, data_dirs)


@dataclass
class AddFlags:
    force: bool
    dry_run: bool
    delete_added: bool

    @staticmethod
    def parse(args: Mapping) -> "AddFlags":
        return AddFlags(
            force=args.get("--force") or len(args.get("<data>")) == 0,
            dry_run=args.get("--dry-run"),
            delete_added=args.get("--delete"),
        )
