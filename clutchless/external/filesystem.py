import glob
from pathlib import Path
from typing import Protocol, Iterable, Optional


class Filesystem(Protocol):
    def exists(self, path: Path) -> bool:
        raise NotImplementedError

    def is_directory(self, path: Path) -> bool:
        raise NotImplementedError

    def is_file(self, path: Path) -> bool:
        raise NotImplementedError

    def children(self, path: Path) -> Iterable[Path]:
        raise NotImplementedError

    def find(self, path: Path, filename: str, is_dir: bool = False) -> Optional[Path]:
        raise NotImplementedError

    def collect(self, path: Path, extension: str) -> Iterable[Path]:
        raise NotImplementedError

    def remove(self, path: Path):
        raise NotImplementedError


class DefaultFilesystem(Filesystem):
    def __init__(self):
        pass

    def exists(self, path: Path) -> bool:
        return path.exists()

    def is_directory(self, path: Path) -> bool:
        return path.is_dir()

    def is_file(self, path: Path) -> bool:
        return path.is_file()

    def children(self, path: Path) -> Iterable[Path]:
        normalized_path = str(path).rstrip("/")
        return map(Path, glob.iglob(f"{normalized_path}/*"))

    def find(self, path: Path, filename: str, is_dir: bool = False) -> Optional[Path]:
        def xnor(x: bool, y: bool) -> bool:
            return (x or not y) and (not x or y)
        def filter_wanted_type(p: Path) -> bool:
            return xnor(self.is_directory(p), is_dir)
        normalized_path = str(path).rstrip("/")
        matches = glob.iglob(f"{normalized_path}/**/{filename}", recursive=True)
        paths = map(lambda p: Path(p), matches)
        wanted_matches = filter(filter_wanted_type, paths)
        parent_of_wanted_matches = map(
            lambda p: Path(p).parent,
            wanted_matches
        )
        return next(parent_of_wanted_matches, None)

    def collect(self, path: Path, extension: str) -> Iterable[Path]:
        if path.is_file():
            raise ValueError(f"{path} is not a directory")
        normalized_path = str(path).rstrip("/")
        return map(
            Path, glob.iglob(f"{normalized_path}/**/*.{extension}", recursive=True)
        )

    def remove(self, path: Path):
        path.unlink()


class DryRunFilesystem(DefaultFilesystem):
    def remove(self, path: Path):
        pass
