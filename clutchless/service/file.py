import asyncio
from pathlib import Path
from typing import Iterable, Set, Tuple, AsyncIterable

from clutchless.domain.torrent import MetainfoFile
from clutchless.external.filesystem import (
    FileLocator,
    Filesystem,
    SingleDirectoryFileLocator,
    AggregateFileLocator,
)
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


def _sort_into_dirs_and_files(
    fs: Filesystem, paths: Set[Path]
) -> Tuple[Set[Path], Set[Path]]:
    dirs: Set[Path] = set()
    files: Set[Path] = set()
    for path in paths:
        if fs.is_file(path):
            files.add(path)
        elif fs.is_directory(path):
            dirs.add(path)
        else:
            raise ValueError(f"{path} is a weird path", path)
    return dirs, files


def _validate_metainfo_files(metainfos: Iterable[Path]) -> Iterable[Path]:
    for file in metainfos:
        if file.suffix == ".torrent":
            yield file
        else:
            # raise ValueError(f"{file} is not a valid path")
            pass


async def collect_from_aggregate(
    fs: Filesystem, locators: Iterable[FileLocator]
) -> AsyncIterable[Path]:
    locator = AggregateFileLocator(locators, fs)
    async for result in locator.collect(".torrent"):
        yield result


async def collect_metainfo_paths(
    fs: Filesystem, paths: Iterable[Path]
) -> AsyncIterable[Path]:
    dirs, files = _sort_into_dirs_and_files(fs, set(paths))
    for result in _validate_metainfo_files(files):
        yield result
    locators = (SingleDirectoryFileLocator(fs, directory) for directory in dirs)
    async for result in collect_from_aggregate(fs, locators):
        yield result


def get_metainfo_files(
    reader: MetainfoReader, paths: Iterable[Path]
) -> Set[MetainfoFile]:
    return {reader.from_path(path) for path in paths}


async def collect_metainfo_paths_with_timeout(
    fs: Filesystem, paths: Iterable[Path], timeout: float
) -> Iterable[Path]:
    async def _callback():
        results = []
        async for result in collect_metainfo_paths(fs, paths):
            results.append(result)
        return results

    task = asyncio.create_task(_callback())
    await asyncio.sleep(timeout)
    try:
        found = task.result()
    except asyncio.InvalidStateError:
        task.cancel()
        await task
        found = task.result()
    return found


async def collect_metainfo_files_with_timeout(
    fs: Filesystem, reader: MetainfoReader, paths: Iterable[Path], timeout: float
) -> Iterable[MetainfoFile]:
    found = await collect_metainfo_paths_with_timeout(fs, paths, timeout)
    return get_metainfo_files(reader, found)
