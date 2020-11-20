import glob
from pathlib import Path
from shutil import copy, SameFileError
from typing import Protocol, Iterable, Optional, Set, Mapping, Tuple


class Filesystem(Protocol):
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


class CopyError(Exception):
    pass


class DefaultFilesystem(Filesystem):
    def __init__(self):
        pass

    def root(self) -> Path:
        return Path(Path().anchor)

    def create_dir(self, path: Path):
        path.mkdir(parents=True, exist_ok=True)

    def copy(self, source: Path, destination: Path):
        if source.exists():
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
        normalized_path = str(path).rstrip("/")
        return map(Path, glob.iglob(f"{normalized_path}/*"))

    def remove(self, path: Path):
        path.unlink()


class DryRunFilesystem(DefaultFilesystem):
    def remove(self, path: Path):
        pass


class FileLocator(Protocol):
    def locate(self, filename: str, is_dir: bool = False) -> Optional[Path]:
        """When successful, returns parent path that holds 'filename'."""
        raise NotImplementedError

    def collect(self, extension: str) -> Iterable[Path]:
        raise NotImplementedError


class DefaultFileLocator(FileLocator):
    def __init__(self, fs: Filesystem, path: Path = None):
        self.fs = fs
        if path is not None:
            self.path = path
        else:
            self.path = fs.root()

    @staticmethod
    def _get_parent_of_wanted_matches(
        is_dir_pairs: Iterable[Tuple[Path, bool]], want_dir: bool
    ) -> Optional[Path]:
        def xnor(x: bool, y: bool) -> bool:
            return (x or not y) and (not x or y)

        def filter_wanted_type(pair: Iterable[Tuple[Path, bool]]) -> bool:
            _, is_dir = pair
            return xnor(is_dir, want_dir)

        wanted_pairs = filter(filter_wanted_type, is_dir_pairs)
        parents_of_wanted_paths = map(lambda pair: Path(pair[0]).parent, wanted_pairs)
        return next(parents_of_wanted_paths, None)

    def locate(self, filename: str, is_dir: bool = False) -> Optional[Path]:
        normalized_path = str(self.path).rstrip("/")
        escaped_pathname = glob.escape(f"{normalized_path}/**/{filename}")
        matches = glob.iglob(escaped_pathname, recursive=True)
        paths = (Path(match) for match in matches)
        is_dir_pairs = ((path, self.fs.is_directory(path)) for path in paths)
        return self._get_parent_of_wanted_matches(is_dir_pairs, is_dir)

    def collect(self, extension: str) -> Iterable[Path]:
        if self.fs.is_file(self.path):
            raise ValueError(f"{self.path} is not a directory")
        normalized_path = str(self.path).rstrip("/")
        escaped_pathname = glob.escape(f"{normalized_path}/**/*{extension}")
        return map(
            Path, glob.iglob(escaped_pathname, recursive=True)
        )


class MultipleDirectoryFileLocator(FileLocator):
    def __init__(self, directories: Set[Path], fs: Filesystem):
        self.directories = directories
        self.fs = fs
        self.locators: Mapping[Path, FileLocator] = {
            directory: DefaultFileLocator(fs, directory) for directory in directories
        }

    def locate(self, filename: str, is_dir: bool = False) -> Optional[Path]:
        for _, locator in self.locators.items():
            result = locator.locate(filename, is_dir)
            if result is not None:
                return result

    def collect(self, extension: str) -> Iterable[Path]:
        for _, locator in self.locators.items():
            yield from locator.collect(extension)
