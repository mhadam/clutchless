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
        normalized_path = str(path).rstrip('/')
        return map(Path, glob.iglob(f'{normalized_path}/*'))

    def find(self, path: Path, filename: str, is_file: bool = True) -> Optional[Path]:
        normalized_path = str(path).rstrip('/')
        termination = "" if is_file else "/"
        result = map(lambda p: Path(p).parent, glob.iglob(f'{normalized_path}/**/{filename}{termination}', recursive=True))
        return next(result, None)

    def collect(self, path: Path, extension: str) -> Iterable[Path]:
        if path.is_file():
            raise ValueError(f'{path} is not a directory')
        normalized_path = str(path).rstrip('/')
        return map(Path, glob.iglob(f'{normalized_path}/**/*.{extension}', recursive=True))
