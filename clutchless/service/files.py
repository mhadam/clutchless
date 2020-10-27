from pathlib import Path
from typing import Iterable, Set

from clutchless.external.filesystem import Filesystem


def collect_metainfo_files(fs: Filesystem, raw_paths: Set[str]) -> Set[Path]:
    def generate_paths() -> Iterable[Path]:
        for raw_path in raw_paths:
            path = Path(raw_path)
            if fs.is_file(path) and path.suffix == ".torrent":
                yield path
            elif fs.is_directory(path):
                yield from fs.collect(path, '.torrent')

    return set(generate_paths())
