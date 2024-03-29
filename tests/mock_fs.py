from collections import deque
from pathlib import Path
from typing import Mapping, Iterable, Deque, Set, Tuple

from clutchless.external.filesystem import Filesystem, CopyError


def _get_paths(spec: Iterable) -> Tuple[Set[Path], Set[Path]]:
    queue: Deque = deque()
    queue.append(("/", spec))
    files: Set[Path] = set()
    directories: Set[Path] = {Path("/")}
    while len(queue) > 0:
        path, item = queue.pop()
        if isinstance(item, Mapping):
            for (child_name, child_value) in item.items():
                directories.add(Path(path, child_name))
                if path == "/":
                    queue.appendleft(("/" + child_name, child_value))
                else:
                    queue.appendleft((path + "/" + child_name, child_value))
        elif isinstance(item, str):
            if item.endswith("/"):
                directories.add(Path(path, item))
            else:
                files.add(Path(path, item))
        elif isinstance(item, Iterable):
            for value in item:
                queue.appendleft((path, value))
    return files, directories


class MockFilesystem(Filesystem):
    def __init__(self, spec: Iterable):
        self.spec = spec
        files, directories = _get_paths(spec)
        self.files = files
        self.directories = directories

    def rename(self, path: Path, name: str):
        if self.exists(path):
            if self.is_file(path):
                self.remove(path)
                self.files.add(path.parent / name)
            else:
                for file in self.files:
                    if path in file.parents:
                        self.files.remove(file)
                        self.files.add(path.parent / name / file.relative_to(path))
                for directory in self.directories:
                    if path in directory.parent:
                        self.directories.remove(directory)
                        self.directories.add(
                            path.parent / name / directory.relative_to(path)
                        )
                if path in self.directories:
                    self.directories.remove(path)
                    self.directories.add(path.parent / name)

    def touch(self, path: Path):
        if not set(path.parents).issubset(self.directories):
            raise NotADirectoryError(path.parent)
        self.files.add(path)

    def root(self) -> Path:
        return Path("/")

    def create_dir(self, path: Path):
        self.directories.update(set(path.parents))

    def copy(self, source: Path, destination: Path):
        if self.is_file(destination):
            raise CopyError("destination is a file")
        elif self.exists(destination / source.name):
            raise CopyError("destination already exists")
        if not self.exists(source):
            raise FileNotFoundError(source)
        elif self.is_file(source):
            self.files.add(destination)
        elif self.is_directory(source):
            self.directories.add(destination)

    def exists(self, path: Path) -> bool:
        return path in self.directories or path in self.files

    def is_directory(self, path: Path) -> bool:
        return path in self.directories

    def is_file(self, path: Path) -> bool:
        return path in self.files

    def children(self, path: Path) -> Iterable[Path]:
        if path in self.directories:
            matching_dirs = {
                p for p in self.directories if p != Path("/") and p.parent == path
            }
            matching_files = {p for p in self.files if p.parent == path}
            yield from matching_dirs
            yield from matching_files

    def remove(self, path: Path):
        if not self.exists(path):
            raise FileNotFoundError(path)
        queue = deque()
        queue.append(path)
        while len(queue) > 0:
            item = queue.pop()
            if self.is_file(item):
                self.files.remove(item)
            else:
                self.directories.remove(item)
                queue.extend(self.children(item))

    def absolute(self, path: Path) -> Path:
        return path


class InfinitelyDeepFilesystem(MockFilesystem):
    def __init__(self):
        super().__init__({})

    def children(self, path: Path) -> Iterable[Path]:
        yield path.parent
