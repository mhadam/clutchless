from pathlib import Path
from typing import Set, Sequence

from clutchless.search import get_torrent_files


def convert_to_paths(raw_paths: Sequence[str]) -> Set[Path]:
    return {Path(raw_path).resolve(strict=False) for raw_path in raw_paths}


def find_torrent_files(paths: Set[Path]) -> Set[Path]:
    torrent_dirs = set()
    torrent_files = set()
    for path in paths:
        if not path.exists():
            raise ValueError("Supplied torrent path doesn't exist")
        elif path.is_dir():
            torrent_dirs.add(path)
        elif path.is_file():
            torrent_files.add(path)
        else:
            raise ValueError("Invalid torrent path")

    for directory in torrent_dirs:
        torrent_files.update(get_torrent_files(directory))
    return torrent_files


def parse_data_dirs(dirs: Sequence[str]) -> Set[Path]:
    data_paths = [Path(data_dir) for data_dir in dirs]
    data_dirs = set()
    for path in data_paths:
        if not path.exists():
            raise ValueError("Supplied data path doesn't exist.")
        elif path.is_dir():
            data_dirs.add(path)
        else:
            raise ValueError("Invalid.")
    return data_dirs
