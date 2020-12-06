import asyncio
from itertools import chain
from pathlib import Path
from typing import Iterable, Set, Tuple, AsyncIterable

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


async def _collect_metainfos_in_dirs(
    locators: Iterable[FileLocator],
) -> AsyncIterable[Path]:
    for locator in locators:
        async for metainfo in locator.collect(".torrent"):
            yield metainfo


def _validate_metainfo_files(metainfos: Iterable[Path]) -> Iterable[Path]:
    for file in metainfos:
        if file.suffix == ".torrent":
            yield file
        else:
            raise ValueError(f"{file} is a valid path")


async def collect_metainfo_paths(
    fs: Filesystem, paths: Set[Path]
) -> AsyncIterable[Path]:
    dirs, files = _sort_into_dirs_and_files(fs, paths)
    locators = {DefaultFileLocator(fs, path) for path in dirs}
    async for path in _collect_metainfos_in_dirs(locators):
        yield path
    for path in _validate_metainfo_files(files):
        yield path


def get_metainfo_files(
    reader: MetainfoReader, paths: Iterable[Path]
) -> Set[MetainfoFile]:
    return {reader.from_path(path) for path in paths}


async def collect_metainfo_files_with_timeout(
    locators: Iterable[FileLocator], timeout: int
) -> Iterable[Path]:
    async def _callback(locator: FileLocator):
        results = set()
        async for collected in locator.collect(".torrent"):
            results.add(collected)
        return results

    futures = {asyncio.create_task(_callback(locator)): locator for locator in locators}
    done, pending = await asyncio.wait(futures.keys(), timeout=timeout)
    done_results = [d.result() for d in done]
    if len(pending) > 0:
        for t in pending:
            locator: FileLocator = futures[t]
            print(f"timed out trying to search {set(locator.roots())}")
            t.cancel()
        cancelled_done, pending = await asyncio.wait(pending)
        cancelled_done_results = [d.result() for d in cancelled_done]
        return chain(
            chain.from_iterable(done_results),
            chain.from_iterable(cancelled_done_results),
        )
    return chain.from_iterable(done_results)
