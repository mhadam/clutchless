import asyncio
import logging
import os
from asyncio import Task
from collections import deque
from itertools import chain
from pathlib import Path
from shutil import copy, SameFileError
from typing import (
    Protocol,
    Iterable,
    Optional,
    Tuple,
    Deque,
    AsyncGenerator,
)

from clutchless.stream import combine

logger = logging.getLogger(__name__)


class Filesystem(Protocol):
    def touch(self, path: Path):
        raise NotImplementedError

    def root(self) -> Path:
        raise NotImplementedError

    def create_dir(self, path: Path):
        raise NotImplementedError

    def copy(self, source: Path, destination: Path):
        raise NotImplementedError

    def exists(self, path: Path) -> bool:
        raise NotImplementedError

    def is_directory(self, path: Path) -> bool:
        raise NotImplementedError

    def is_file(self, path: Path) -> bool:
        raise NotImplementedError

    def children(self, path: Path) -> Iterable[Path]:
        raise NotImplementedError

    def remove(self, path: Path):
        raise NotImplementedError

    def absolute(self, path: Path) -> Path:
        raise NotImplementedError


class CopyError(Exception):
    pass


class DefaultFilesystem(Filesystem):
    def __init__(self):
        pass

    def touch(self, path: Path):
        path.touch(exist_ok=True)

    def root(self) -> Path:
        return Path(Path().anchor)

    def create_dir(self, path: Path):
        path.mkdir(parents=True, exist_ok=True)

    def copy(self, source: Path, destination: Path):
        if (destination / source.name).exists():
            raise CopyError("destination already exists")
        try:
            copy(source, destination)
        except SameFileError:
            raise CopyError("source same as destination")

    def exists(self, path: Path) -> bool:
        return path.exists()

    def is_directory(self, path: Path) -> bool:
        return path.is_dir()

    def is_file(self, path: Path) -> bool:
        return path.is_file()

    def children(self, path: Path) -> Iterable[Path]:
        try:
            if self.is_directory(path):
                entries = os.listdir(path)
                for entry in entries:
                    full_entry = path / entry
                    if self.exists(full_entry):
                        yield full_entry
        except PermissionError:
            pass

    def remove(self, path: Path):
        path.unlink()

    def absolute(self, path: Path) -> Path:
        return path.resolve(strict=True)


class DryRunFilesystem(DefaultFilesystem):
    def remove(self, path: Path):
        pass


class FileLocator(Protocol):
    def roots(self) -> Iterable[Path]:
        raise NotImplementedError

    async def locate_file(self, name: str) -> Optional[Path]:
        raise NotImplementedError

    async def locate_directory(self, name: str) -> Optional[Path]:
        """When successful, returns parent path that holds directory 'name'."""
        raise NotImplementedError

    async def collect(self, extension: str) -> AsyncGenerator[Path, None]:
        raise NotImplementedError


class SingleDirectoryFileLocator(FileLocator):
    def __init__(self, fs: Filesystem, path: Path = None):
        self.fs = fs
        if path is None:
            path = fs.root()
        if fs.is_file(path):
            raise ValueError(f"path {path} must be a directory")
        self.path = path

    def roots(self) -> Iterable[Path]:
        yield self.path

    @staticmethod
    def _get_parent_of_wanted_matches(
        is_dir_pairs: Iterable[Tuple[Path, bool]], want_dir: bool
    ) -> Optional[Path]:
        def xnor(x: bool, y: bool) -> bool:
            return (x or not y) and (not x or y)

        def filter_wanted_type(pair: Tuple[Path, bool]) -> bool:
            is_dir = pair[1]
            print(pair[0])
            return xnor(is_dir, want_dir)

        wanted_pairs = filter(filter_wanted_type, is_dir_pairs)
        parents_of_wanted_paths = map(lambda pair: Path(pair[0]).parent, wanted_pairs)
        return next(parents_of_wanted_paths, None)

    async def locate_directory(self, name: str) -> Optional[Path]:
        queue: Deque[Path] = deque()
        queue.append(self.path)
        while len(queue) > 0:
            try:
                await asyncio.sleep(0)
            except asyncio.CancelledError:
                return None
            item = queue.pop()
            child_directories = (
                child for child in self.fs.children(item) if self.fs.is_directory(child)
            )
            for directory_path in child_directories:
                if directory_path.name == name:
                    return item
                queue.appendleft(directory_path)
        return None

    async def locate_file(self, name: str) -> Optional[Path]:
        queue: Deque[Path] = deque()
        queue.append(self.path)
        while len(queue) > 0:
            try:
                await asyncio.sleep(0)
            except asyncio.CancelledError:
                return None
            item = queue.pop()
            for child_path in self.fs.children(item):
                if self.fs.is_file(child_path) and child_path.name == name:
                    return item
                elif self.fs.is_directory(child_path):
                    queue.appendleft(child_path)
        return None

    async def collect(self, extension: str) -> AsyncGenerator[Path, None]:
        queue: Deque[Path] = deque()
        queue.append(self.path)
        while len(queue) > 0:
            await asyncio.sleep(0)
            item = queue.pop()
            for child_path in self.fs.children(item):
                if self.fs.is_file(child_path) and child_path.suffix == extension:
                    yield child_path
                elif self.fs.is_directory(child_path):
                    queue.appendleft(child_path)


class AggregateFileLocator(FileLocator):
    def __init__(self, locators: Iterable[FileLocator], fs: Filesystem):
        self.fs = fs
        self.locators = set(locators)

    def roots(self) -> Iterable[Path]:
        return chain.from_iterable(locator.roots() for locator in self.locators)

    @staticmethod
    async def _locate(tasks: Iterable[Task]) -> Optional[Path]:
        try:
            gather_results = await asyncio.gather(*tasks)
            return next(
                (result for result in gather_results if result is not None), None
            )
        except asyncio.CancelledError:
            for task in tasks:
                try:
                    result = task.result()
                    if result is not None:
                        return result
                except asyncio.CancelledError:
                    pass
        logger.info("exiting aggregate locator")
        return

    async def locate_file(self, name: str) -> Optional[Path]:
        tasks = [
            asyncio.create_task(locator.locate_file(name)) for locator in self.locators
        ]
        try:
            return await self._locate(tasks)
        except asyncio.CancelledError:
            pass

    async def locate_directory(self, name: str) -> Optional[Path]:
        tasks = [
            asyncio.create_task(locator.locate_directory(name))
            for locator in self.locators
        ]
        try:
            return await self._locate(tasks)
        except asyncio.CancelledError:
            pass

    async def collect(self, extension: str) -> AsyncGenerator[Path, None]:
        async for item in combine(
            locator.collect(".torrent") for locator in self.locators
        ):
            yield item


class MultipleDirectoryFileLocator(AggregateFileLocator):
    def __init__(self, directories: Iterable[Path], fs: Filesystem):
        self.directories = set(directories)
        locators = (
            SingleDirectoryFileLocator(fs, directory) for directory in directories
        )
        super().__init__(locators, fs)
