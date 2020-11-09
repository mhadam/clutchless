from pathlib import Path
from typing import Set, Sequence, Iterable

from clutchless.external.filesystem import Filesystem


class PathParser:
    def __init__(self):
        pass

    @classmethod
    def parse_paths(cls, raw_paths: Sequence[str]) -> Set[Path]:
        return {cls.parse_path(raw_path) for raw_path in raw_paths}

    @classmethod
    def parse_path(cls, raw_path: str) -> Path:
        return Path(raw_path).resolve(strict=True)


class DataDirectoryParser:
    def __init__(self, fs: Filesystem):
        self.fs = fs

    def parse(self, data_dirs: Sequence[str]) -> Set[Path]:
        def generate() -> Iterable[Path]:
            paths = [Path(data_dir) for data_dir in data_dirs]
            for path in paths:
                yield from self.__handle_path(path)
        return set(generate())

    def __handle_path(self, path: Path) -> Set[Path]:
        self.__validate_exists(path)
        self.__reject_non_dir(path)
        if self.fs.is_directory(path):
            return {path}
        return set()

    def __validate_exists(self, path: Path):
        if not self.fs.exists(path):
            raise ValueError("Supplied data path doesn't exist")

    def __reject_non_dir(self, path: Path):
        if not self.fs.is_directory(path):
            raise ValueError("Supplied data path isn't a directory")

