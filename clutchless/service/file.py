from pathlib import Path
from typing import Iterable, Set

from clutchless.domain.torrent import MetainfoFile
from clutchless.external.filesystem import FileLocator, Filesystem, DefaultFileLocator
from clutchless.external.metainfo import MetainfoReader


def validate_exists(fs: Filesystem, path: Path):
    if not fs.exists(path):
        raise ValueError(f"supplied path does not exist: {path}")


def validate_files(fs: Filesystem, paths: Iterable[Path]):
    def validate_path(path: Path):
        validate_exists(fs, path)
        reject_non_file(path)

    def reject_non_file(path: Path):
        if not fs.is_file(path):
            raise ValueError(f"supplied path is not a file: {path}")

    for p in paths:
        validate_path(p)


def validate_directories(fs: Filesystem, paths: Iterable[Path]):
    def validate_path(path: Path):
        validate_exists(fs, path)
        reject_non_dir(path)

    def reject_non_dir(path: Path):
        if not fs.is_directory(path):
            raise ValueError(f"supplied path is not a directory: {path}")

    for p in paths:
        validate_path(p)


def parse_path(fs: Filesystem, value: str) -> Path:
    return fs.absolute(Path(value))


def get_valid_directories(fs: Filesystem, values: Iterable[str]) -> Set[Path]:
    paths = {parse_path(fs, value) for value in values}
    validate_directories(fs, paths)
    return paths


def get_valid_files(fs: Filesystem, values: Iterable[str]) -> Set[Path]:
    paths = {parse_path(fs, value) for value in values}
    validate_files(fs, paths)
    return paths


def get_valid_paths(fs: Filesystem, values: Iterable[str]) -> Set[Path]:
    paths = {parse_path(fs, value) for value in values}
    for path in paths:
        validate_exists(fs, path)
    return paths


def collect_metainfo_paths(fs: Filesystem, paths: Set[Path]) -> Set[Path]:
    def generate_paths() -> Iterable[Path]:
        for path in paths:
            if fs.is_file(path) and path.suffix == ".torrent":
                yield path
            elif fs.is_directory(path):
                yield from DefaultFileLocator(fs, path).collect(".torrent")

    return set(generate_paths())


def collect_metainfo_files(
    fs: Filesystem, paths: Set[Path], reader: MetainfoReader
) -> Set[MetainfoFile]:
    metainfo_paths = collect_metainfo_paths(fs, paths)
    return {reader.from_path(path) for path in metainfo_paths}
