from pathlib import Path
from typing import Iterable, Set

from clutchless.domain.torrent import MetainfoFile
from clutchless.external.filesystem import FileLocator, Filesystem
from clutchless.external.metainfo import MetainfoReader


def collect_metainfo_paths(
    fs: Filesystem, locator: FileLocator, paths: Set[Path]
) -> Set[Path]:
    def generate_paths() -> Iterable[Path]:
        for path in paths:
            if fs.is_file(path) and path.suffix == ".torrent":
                yield path
            elif fs.is_directory(path):
                yield from locator.collect(".torrent")

    return set(generate_paths())


def collect_metainfo_files(
    fs: Filesystem, locator: FileLocator, paths: Set[Path], reader: MetainfoReader
) -> Set[MetainfoFile]:
    metainfo_paths = collect_metainfo_paths(fs, locator, paths)
    return {reader.from_path(path) for path in metainfo_paths}
